"""Revision migration for legacy text-capacity tags and table-cell settings."""

from __future__ import annotations

import json
from collections.abc import Mapping
from math import ceil

from .errors import TemplateContractMigrationError

_COMPONENT_TYPE = "efficio_component_type"
_TABLE_CONFIG = "efficio_table_config"
_MAX_SAFE_INTEGER = 9_007_199_254_740_991
_TEXT_FORMATS = frozenset({"plain", "paragraph", "bullets", "numbered_list"})
_MAX_LINES = "efficio_max_lines"
_CHARS_PER_LINE = "efficio_estimated_chars_per_line"
_MIN_ITEMS = "efficio_min_items"
_MAX_ITEMS = "efficio_max_items"
_TARGET_ITEMS = "efficio_target_items"

_RETIRED_TEXT_FIELDS = (
    "efficio_max_chars",
    "efficio_target_chars",
    "efficio_min_chars_per_item",
    "efficio_max_chars_per_item",
    "efficio_target_chars_per_item",
    "efficio_max_chars_per_line",
)
_TABLE_RETIRED_FIELDS = tuple(field.removeprefix("efficio_") for field in _RETIRED_TEXT_FIELDS)
_TABLE_CAPACITY_FIELDS = frozenset(
    {
        "max_lines",
        "estimated_chars_per_line",
        "min_items",
        "max_items",
        "target_items",
        *_TABLE_RETIRED_FIELDS,
    }
)
_TABLE_CELL_FIELDS = frozenset(
    {
        "row",
        "col",
        "render_action",
        "text_format",
        "instruction",
        *_TABLE_CAPACITY_FIELDS,
    }
)


def migrate_text_capacity(tags: dict[str, str]) -> None:
    """Migrate one copied shape-tag map in place."""
    component_type = tags.get(_COMPONENT_TYPE)
    if component_type == "text":
        _migrate_text_tags(tags)
    elif component_type == "table":
        _migrate_table_config(tags)


def retired_text_capacity_tags() -> tuple[str, ...]:
    """Return scalar tags that must not remain on a current-revision template."""
    return _RETIRED_TEXT_FIELDS


def contains_retired_table_capacity_fields(tags: Mapping[str, str]) -> bool:
    """Return whether a table config still contains a retired cell field."""
    if tags.get(_COMPONENT_TYPE) != "table":
        return False
    raw = tags.get(_TABLE_CONFIG)
    if raw is None:
        return False
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, dict) or not isinstance(parsed.get("cells"), list):
        return False
    return any(
        isinstance(cell, dict) and bool(set(cell).intersection(_TABLE_RETIRED_FIELDS))
        for cell in parsed["cells"]
    )


def _migrate_text_tags(tags: dict[str, str]) -> None:
    values = {name: _optional_tag_integer(tags, name) for name in _text_capacity_inputs()}
    max_lines = values[_MAX_LINES] or values[_MAX_ITEMS]
    if max_lines is None:
        raise _error("text component has no value from which max_lines can be migrated")

    chars_per_line = _resolve_chars_per_line(
        current=values[_CHARS_PER_LINE],
        legacy=values["efficio_max_chars_per_line"],
        max_chars=values["efficio_max_chars"],
        max_chars_per_item=values["efficio_max_chars_per_item"],
        max_lines=max_lines,
        subject="text component",
    )
    text_format = tags.get("efficio_text_format", "plain")
    if text_format not in _TEXT_FORMATS:
        raise _error("text component text format is invalid")
    is_plain = text_format == "plain"
    min_items = 1 if is_plain else values[_MIN_ITEMS] or 1
    max_items = 1 if is_plain else values[_MAX_ITEMS] or max_lines
    target_items = None if is_plain else values[_TARGET_ITEMS]
    _validate_item_limits(text_format, min_items, max_items, target_items, max_lines, "text component")

    tags[_MAX_LINES] = str(max_lines)
    tags[_CHARS_PER_LINE] = str(chars_per_line)
    tags[_MIN_ITEMS] = str(min_items)
    tags[_MAX_ITEMS] = str(max_items)
    if target_items is None:
        tags.pop(_TARGET_ITEMS, None)
    else:
        tags[_TARGET_ITEMS] = str(target_items)
    for field in _RETIRED_TEXT_FIELDS:
        tags.pop(field, None)


def _migrate_table_config(tags: dict[str, str]) -> None:
    raw = tags.get(_TABLE_CONFIG)
    if raw is None:
        raise _error("table component is missing efficio_table_config")
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise _error("efficio_table_config must be valid JSON") from error
    if not isinstance(parsed, dict) or set(parsed) - {"rows", "columns", "cells"}:
        raise _error("efficio_table_config must be a supported JSON object")
    cells = parsed.get("cells")
    if not isinstance(cells, list):
        raise _error("efficio_table_config must contain a cells array")

    for index, raw_cell in enumerate(cells):
        if not isinstance(raw_cell, dict) or set(raw_cell) - _TABLE_CELL_FIELDS:
            raise _error(f"table cell {index} contains unsupported fields")
        _validate_coordinate(raw_cell.get("row"), index, "row")
        _validate_coordinate(raw_cell.get("col"), index, "col")
        _migrate_table_cell(raw_cell, index)

    tags[_TABLE_CONFIG] = json.dumps(
        parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _migrate_table_cell(cell: dict[str, object], index: int) -> None:
    if not set(cell).intersection(_TABLE_CAPACITY_FIELDS):
        return
    values = {
        name: _optional_json_integer(cell, name, index)
        for name in _TABLE_CAPACITY_FIELDS
    }
    if cell.get("render_action", "preserve") != "render":
        _remove_retired_table_fields(cell)
        return

    text_format = cell.get("text_format", "plain")
    if not isinstance(text_format, str) or text_format not in _TEXT_FORMATS:
        raise _error(f"table cell {index} text_format is invalid")

    line_capacity = _resolve_table_line_capacity(values, text_format, index)
    is_plain = text_format == "plain"
    min_items = 1 if is_plain else values["min_items"] or 1
    max_items = (
        1
        if is_plain
        else values["max_items"] or (line_capacity[0] if line_capacity else None)
    )
    target_items = None if is_plain else values["target_items"]
    _validate_item_limits(
        text_format,
        min_items,
        max_items,
        target_items,
        line_capacity[0] if line_capacity else None,
        f"table cell {index}",
    )

    _remove_retired_table_fields(cell)
    if is_plain:
        cell.pop("target_items", None)
    if line_capacity is not None:
        cell["max_lines"], cell["estimated_chars_per_line"] = line_capacity
    if line_capacity is not None or is_plain:
        cell["min_items"] = min_items
        assert max_items is not None
        cell["max_items"] = max_items


def _resolve_table_line_capacity(
    values: Mapping[str, int | None], text_format: str, index: int
) -> tuple[int, int] | None:
    max_lines = values["max_lines"] or values["max_items"]
    if max_lines is None and text_format == "plain":
        max_lines = 1
    has_width_source = any(
        values[field] is not None
        for field in (
            "estimated_chars_per_line",
            "max_chars_per_line",
            "max_chars",
            "max_chars_per_item",
        )
    )
    if values["max_lines"] is not None and not has_width_source:
        raise _error(
            f"table cell {index} has max_lines without estimated_chars_per_line"
        )
    if has_width_source and max_lines is None:
        raise _error(
            f"table cell {index} has a character capacity without max_lines"
        )
    if max_lines is None or not has_width_source:
        return None
    return max_lines, _resolve_chars_per_line(
        current=values["estimated_chars_per_line"],
        legacy=values["max_chars_per_line"],
        max_chars=values["max_chars"],
        max_chars_per_item=values["max_chars_per_item"],
        max_lines=max_lines,
        subject=f"table cell {index}",
    )


def _remove_retired_table_fields(cell: dict[str, object]) -> None:
    for field in _TABLE_RETIRED_FIELDS:
        cell.pop(field, None)


def _resolve_chars_per_line(
    *,
    current: int | None,
    legacy: int | None,
    max_chars: int | None,
    max_chars_per_item: int | None,
    max_lines: int,
    subject: str,
) -> int:
    if current is not None and legacy is not None and current != legacy:
        raise _error(f"{subject} has conflicting characters-per-line values")
    if current is not None:
        return current
    if legacy is not None:
        return legacy
    if max_chars is not None:
        return ceil(max_chars / max_lines)
    if max_chars_per_item is not None:
        return max_chars_per_item
    raise _error(f"{subject} has no value from which estimated_chars_per_line can be migrated")


def _validate_item_limits(
    text_format: str,
    minimum: int,
    maximum: int | None,
    target: int | None,
    max_lines: int | None,
    subject: str,
) -> None:
    if maximum is not None and minimum > maximum:
        raise _error(f"{subject} min_items must not exceed max_items")
    if maximum is not None and max_lines is not None and maximum > max_lines:
        raise _error(f"{subject} max_items must not exceed max_lines")
    if target is not None and (
        target < minimum or (maximum is not None and target > maximum)
    ):
        raise _error(f"{subject} target_items must be within min_items and max_items")
    if text_format == "plain" and (minimum != 1 or maximum != 1 or target is not None):
        raise _error(f"{subject} plain text must use exactly one item and no target_items")


def _text_capacity_inputs() -> tuple[str, ...]:
    return (
        _MAX_LINES,
        _CHARS_PER_LINE,
        _MIN_ITEMS,
        _MAX_ITEMS,
        _TARGET_ITEMS,
        *_RETIRED_TEXT_FIELDS,
    )


def _optional_tag_integer(tags: Mapping[str, str], name: str) -> int | None:
    raw = tags.get(name)
    if raw is None:
        return None
    if (
        not raw.isascii()
        or not raw.isdecimal()
        or int(raw) < 1
        or int(raw) > _MAX_SAFE_INTEGER
    ):
        raise _error(f"tag {name} must be a positive integer string")
    return int(raw)


def _optional_json_integer(
    value: Mapping[str, object], name: str, index: int
) -> int | None:
    raw = value.get(name)
    if raw is None:
        return None
    if (
        not isinstance(raw, int)
        or isinstance(raw, bool)
        or raw < 1
        or raw > _MAX_SAFE_INTEGER
    ):
        raise _error(f"table cell {index} field {name} must be a positive integer")
    return raw


def _validate_coordinate(value: object, index: int, name: str) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > _MAX_SAFE_INTEGER
    ):
        raise _error(f"table cell {index} {name} must be a non-negative integer")


def _error(message: str) -> TemplateContractMigrationError:
    return TemplateContractMigrationError(f"text capacity migration failed: {message}")

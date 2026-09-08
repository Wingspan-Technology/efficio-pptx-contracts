"""Revision-4 migration for strict aggregate and per-item character limits."""

from __future__ import annotations

import json

from ._table_config import TABLE_CONFIG_TAG, TableConfigError, parse_table_config
from .errors import TemplateContractMigrationError

_COMPONENT_TYPE = "efficio_component_type"
_MAX_LINES = "efficio_max_lines"
_CHARS_PER_LINE = "efficio_estimated_chars_per_line"
_MIN_CHARS = "efficio_min_chars"
_MAX_CHARS = "efficio_max_chars"
_MIN_CHARS_PER_ITEM = "efficio_min_chars_per_item"
_MAX_CHARS_PER_ITEM = "efficio_max_chars_per_item"
_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def derive_text_character_limits(tags: dict[str, str]) -> None:
    """Derive strict limits from the existing estimated line capacity."""
    component_type = tags.get(_COMPONENT_TYPE)
    if component_type == "text":
        _derive_text_tags(tags)
    elif component_type == "table":
        _derive_table_cells(tags)


def _derive_text_tags(tags: dict[str, str]) -> None:
    max_lines = _positive_tag(tags, _MAX_LINES)
    chars_per_line = _positive_tag(tags, _CHARS_PER_LINE)
    maximum = _safe_capacity(max_lines, chars_per_line, "text component")
    tags[_MIN_CHARS] = "1"
    tags[_MAX_CHARS] = str(maximum)
    tags[_MIN_CHARS_PER_ITEM] = "1"
    tags[_MAX_CHARS_PER_ITEM] = str(maximum)


def _derive_table_cells(tags: dict[str, str]) -> None:
    raw = tags.get(TABLE_CONFIG_TAG)
    if raw is None:
        raise _error("table component is missing efficio_table_config")
    try:
        config = parse_table_config(raw)
        parsed: object = json.loads(raw)
    except (TableConfigError, json.JSONDecodeError) as error:
        raise _error("efficio_table_config is invalid") from error
    if not isinstance(parsed, dict) or not isinstance(parsed.get("cells"), list):
        raise _error("efficio_table_config must contain a cells array")

    changed = False
    for index, (cell, raw_cell) in enumerate(zip(config.cells, parsed["cells"], strict=True)):
        if not cell.render or not isinstance(raw_cell, dict):
            continue
        has_lines = cell.capacity.max_lines is not None
        has_width = cell.capacity.estimated_chars_per_line is not None
        if has_lines != has_width:
            raise _error(
                f"table cell {index} max_lines and estimated_chars_per_line "
                "must be provided together"
            )
        if not has_lines:
            continue
        assert cell.capacity.max_lines is not None
        assert cell.capacity.estimated_chars_per_line is not None
        maximum = _safe_capacity(
            cell.capacity.max_lines,
            cell.capacity.estimated_chars_per_line,
            f"table cell {index}",
        )
        raw_cell["min_chars"] = 1
        raw_cell["max_chars"] = maximum
        raw_cell["min_chars_per_item"] = 1
        raw_cell["max_chars_per_item"] = maximum
        changed = True
    if changed:
        tags[TABLE_CONFIG_TAG] = json.dumps(
            parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )


def _positive_tag(tags: dict[str, str], name: str) -> int:
    raw = tags.get(name)
    if (
        raw is None
        or not raw.isascii()
        or not raw.isdecimal()
        or int(raw) < 1
        or int(raw) > _MAX_SAFE_INTEGER
    ):
        raise _error(f"text component requires positive integer tag {name}")
    return int(raw)


def _safe_capacity(max_lines: int, chars_per_line: int, subject: str) -> int:
    maximum = max_lines * chars_per_line
    if maximum > _MAX_SAFE_INTEGER:
        raise _error(f"{subject} character capacity exceeds the supported integer range")
    return maximum


def _error(message: str) -> TemplateContractMigrationError:
    return TemplateContractMigrationError(
        f"strict character-limit migration failed: {message}"
    )

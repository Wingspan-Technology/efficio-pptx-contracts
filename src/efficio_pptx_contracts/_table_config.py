"""Typed parsing for the authored ``efficio_table_config`` tag value.

The table validation-schema builder, V2 projection, and semantic validator all
consume this one normalized representation. Parsing owns structural validity;
cross-field sizing and duplicate checks remain in ``_table_config_validation``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

TABLE_CONFIG_TAG = "efficio_table_config"

_ROOT_FIELDS = frozenset({"rows", "columns", "cells"})
_CELL_FIELDS = frozenset(
    {
        "row",
        "col",
        "render_action",
        "text_format",
        "instruction",
        "max_chars",
        "target_chars",
        "min_items",
        "target_items",
        "max_items",
        "min_chars_per_item",
        "max_chars_per_item",
        "target_chars_per_item",
    }
)
_CONTENT_POLICIES = frozenset({"required", "optional"})
_RENDER_ACTIONS = frozenset({"render", "preserve"})
_TEXT_FORMATS = frozenset({"plain", "paragraph", "bullets", "numbered_list"})
_SIZING_FIELDS = (
    "max_chars",
    "target_chars",
    "min_items",
    "target_items",
    "max_items",
    "min_chars_per_item",
    "max_chars_per_item",
    "target_chars_per_item",
)


class TableConfigError(ValueError):
    """The table configuration is not structurally valid."""


@dataclass(frozen=True, slots=True)
class TableAxis:
    """One normalized row or column policy."""

    index: int
    content_policy: str
    instruction: str

    @property
    def optional(self) -> bool:
        return self.content_policy == "optional"


@dataclass(frozen=True, slots=True)
class TableCell:
    """One normalized configured table cell."""

    row: int
    col: int
    render_action: str
    text_format: str
    instruction: str
    max_chars: int | None
    target_chars: int | None
    min_items: int | None
    target_items: int | None
    max_items: int | None
    min_chars_per_item: int | None
    max_chars_per_item: int | None
    target_chars_per_item: int | None

    @property
    def coordinate(self) -> tuple[int, int]:
        return self.row, self.col

    @property
    def coordinate_key(self) -> str:
        return f"{self.row},{self.col}"

    @property
    def render(self) -> bool:
        return self.render_action == "render"

    @property
    def plain(self) -> bool:
        return self.text_format == "plain"


@dataclass(frozen=True, slots=True)
class TableConfig:
    """Normalized table configuration in authored order."""

    rows: tuple[TableAxis, ...]
    columns: tuple[TableAxis, ...]
    cells: tuple[TableCell, ...]

    @property
    def render_cells(self) -> tuple[TableCell, ...]:
        return tuple(cell for cell in self.cells if cell.render)

    def row(self, index: int) -> TableAxis | None:
        return next((axis for axis in self.rows if axis.index == index), None)

    def column(self, index: int) -> TableAxis | None:
        return next((axis for axis in self.columns if axis.index == index), None)


def parse_table_config(raw: str) -> TableConfig:
    """Parse and structurally validate one serialized table configuration."""
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise TableConfigError(f"tag {TABLE_CONFIG_TAG!r} must be valid JSON") from error
    if not isinstance(parsed, dict):
        raise TableConfigError(f"tag {TABLE_CONFIG_TAG!r} must be a JSON object")

    root = cast(dict[str, object], parsed)
    _reject_unknown_fields(root, _ROOT_FIELDS, f"tag {TABLE_CONFIG_TAG!r}")
    raw_cells = root.get("cells")
    if not isinstance(raw_cells, list):
        raise TableConfigError(f"tag {TABLE_CONFIG_TAG!r} must have a 'cells' array")

    rows = _parse_axes(root["rows"], "rows", "row") if "rows" in root else ()
    columns = (
        _parse_axes(root["columns"], "columns", "col")
        if "columns" in root
        else ()
    )
    cells = tuple(_parse_cell(entry) for entry in raw_cells)
    return TableConfig(rows=rows, columns=columns, cells=cells)


def _parse_axes(raw: object, label: str, key: str) -> tuple[TableAxis, ...]:
    if not isinstance(raw, list):
        raise TableConfigError(f"tag {TABLE_CONFIG_TAG!r} {label} must be an array")
    return tuple(_parse_axis(entry, label, key) for entry in raw)


def _parse_axis(raw: object, label: str, key: str) -> TableAxis:
    if not isinstance(raw, dict):
        raise TableConfigError(f"each {TABLE_CONFIG_TAG!r} {label} entry must be an object")
    entry = cast(dict[str, object], raw)
    allowed = frozenset({key, "content_policy", "instruction"})
    _reject_unknown_fields(entry, allowed, f"{label} entry")
    index = _coordinate(entry.get(key), f"{label}.{key}")
    policy = entry.get("content_policy", "required")
    if not isinstance(policy, str) or policy not in _CONTENT_POLICIES:
        raise TableConfigError(
            f"{label} entry {index} content_policy must be one of "
            f"{sorted(_CONTENT_POLICIES)}"
        )
    return TableAxis(
        index=index,
        content_policy=policy,
        instruction=_instruction(entry, f"{label} entry {index}"),
    )


def _parse_cell(raw: object) -> TableCell:
    if not isinstance(raw, dict):
        raise TableConfigError(f"each {TABLE_CONFIG_TAG!r} cell must be an object")
    entry = cast(dict[str, object], raw)
    _reject_unknown_fields(entry, _CELL_FIELDS, "table cell")
    row = _coordinate(entry.get("row"), "cell.row")
    col = _coordinate(entry.get("col"), "cell.col")
    render_action = entry.get("render_action", "preserve")
    if not isinstance(render_action, str) or render_action not in _RENDER_ACTIONS:
        raise TableConfigError(
            f"cell ({row},{col}) render_action must be one of {sorted(_RENDER_ACTIONS)}"
        )
    text_format = entry.get("text_format", "plain")
    if not isinstance(text_format, str) or text_format not in _TEXT_FORMATS:
        raise TableConfigError(
            f"cell ({row},{col}) text_format must be one of {sorted(_TEXT_FORMATS)}"
        )
    sizing = {
        field: _optional_positive_integer(entry.get(field), row, col)
        for field in _SIZING_FIELDS
    }
    return TableCell(
        row=row,
        col=col,
        render_action=render_action,
        text_format=text_format,
        instruction=_instruction(entry, f"cell ({row},{col})"),
        max_chars=sizing["max_chars"],
        target_chars=sizing["target_chars"],
        min_items=sizing["min_items"],
        target_items=sizing["target_items"],
        max_items=sizing["max_items"],
        min_chars_per_item=sizing["min_chars_per_item"],
        max_chars_per_item=sizing["max_chars_per_item"],
        target_chars_per_item=sizing["target_chars_per_item"],
    )


def _coordinate(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise TableConfigError(
            f"tag {TABLE_CONFIG_TAG!r} {label} must be a non-negative integer"
        )
    return value


def _optional_positive_integer(value: object, row: int, col: int) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise TableConfigError(
            f"cell ({row},{col}) sizing limits must be positive integers"
        )
    return value


def _instruction(entry: Mapping[str, object], label: str) -> str:
    value = entry.get("instruction", "")
    if not isinstance(value, str):
        raise TableConfigError(f"{label} instruction must be a string")
    return value


def _reject_unknown_fields(
    value: Mapping[str, object], allowed: frozenset[str], label: str
) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise TableConfigError(f"{label} contains unsupported field {unknown[0]!r}")

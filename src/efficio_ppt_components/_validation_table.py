"""Table component per-instance validation schema.

Emits a ``oneOf`` of allowed ``{row, col}`` coordinates (the ``render`` cells),
each with its own item-count/length limits, plus a ``contains`` entry per cell so
required cells must appear exactly once and optional cells at most once. Preserve
and default-preserve cells are dropped; when every cell is preserved the content
may fill nothing (``maxItems: 0``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ._validation_common import _PLAIN_FORMAT, _TEXT_FORMATS, _base_content_schema, _required_tag

_TABLE_CONFIG_TAG = "efficio_table_config"
_RENDER_ACTIONS = frozenset({"render", "preserve"})
_CONTENT_POLICIES = frozenset({"required", "optional"})
_OPTIONAL_POLICY = "optional"


@dataclass(frozen=True)
class _TableCell:
    """One configured cell of ``efficio_table_config`` (validation view)."""

    row: int
    col: int
    render_action: str
    text_format: str
    max_chars_per_item: int | None
    max_lines: int | None
    max_chars_per_line: int | None


def _table_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    render_cells, required_coords = _parse_table_config(_required_tag(tags, _TABLE_CONFIG_TAG, "table"))

    schema = _base_content_schema("table")
    cells_schema: dict[str, Any] = {"type": "array"}
    if not render_cells:
        # Every configured cell is preserved: content may not fill anything.
        cells_schema["maxItems"] = 0
    else:
        cells_schema["items"] = {"oneOf": [_cell_schema(cell) for cell in render_cells]}
        # One contains entry per render cell: required cells must appear exactly
        # once; optional cells at most once (maxContains blocks duplicates).
        cells_schema["allOf"] = [
            _cell_contains(cell, required=(cell.row, cell.col) in required_coords)
            for cell in render_cells
        ]
    schema["properties"]["cells"] = cells_schema
    return schema


def _cell_schema(cell: _TableCell) -> dict[str, Any]:
    """The schema one content cell must match for this allowed coordinate."""
    items: dict[str, Any] = {"type": "array", "minItems": 1}
    if cell.text_format == _PLAIN_FORMAT:
        items["maxItems"] = 1
    elif cell.max_lines is not None:
        items["maxItems"] = cell.max_lines
    item: dict[str, Any] = {"type": "string"}
    limits = [n for n in (cell.max_chars_per_item, cell.max_chars_per_line) if n is not None]
    if limits:
        item["maxLength"] = min(limits)
    items["items"] = item
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["row", "col", "items"],
        "properties": {
            "row": {"const": cell.row},
            "col": {"const": cell.col},
            "items": items,
        },
    }


def _cell_contains(cell: _TableCell, *, required: bool) -> dict[str, Any]:
    return {
        "contains": {
            "type": "object",
            "required": ["row", "col"],
            "properties": {"row": {"const": cell.row}, "col": {"const": cell.col}},
        },
        "minContains": 1 if required else 0,
        "maxContains": 1,
    }


def _parse_table_config(raw: str) -> tuple[list[_TableCell], set[tuple[int, int]]]:
    """Parse ``efficio_table_config`` into render cells + required coordinates.

    Returns the ``render_action == "render"`` cells in config order and the
    subset of their coordinates whose row and column content policies are both
    required (the contract default). Preserve / default-preserve cells are
    dropped. Structural violations raise ``ValueError`` — the tag is
    contract-validated at import, so a failure here means a broken artifact.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} must be valid JSON") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} must be a JSON object")
    if not isinstance(parsed.get("cells"), list):
        raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} must have a 'cells' array")

    optional_rows = _optional_axis_indexes(parsed.get("rows"), "rows", "row")
    optional_cols = _optional_axis_indexes(parsed.get("columns"), "columns", "col")

    render_cells: list[_TableCell] = []
    required_coords: set[tuple[int, int]] = set()
    seen: set[tuple[int, int]] = set()
    for entry in parsed["cells"]:
        if not isinstance(entry, dict):
            raise ValueError(f"each {_TABLE_CONFIG_TAG!r} cell must be an object")
        row = _coordinate(entry.get("row"), "cell.row")
        col = _coordinate(entry.get("col"), "cell.col")
        if (row, col) in seen:
            raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} has a duplicate cell ({row},{col})")
        seen.add((row, col))

        render_action = entry.get("render_action", "preserve")
        if render_action not in _RENDER_ACTIONS:
            raise ValueError(
                f"cell ({row},{col}) render_action must be one of {sorted(_RENDER_ACTIONS)}"
            )
        if render_action != "render":
            continue
        text_format = entry.get("text_format", _PLAIN_FORMAT)
        if text_format not in _TEXT_FORMATS:
            raise ValueError(
                f"cell ({row},{col}) text_format must be one of {sorted(_TEXT_FORMATS)}"
            )
        render_cells.append(
            _TableCell(
                row=row,
                col=col,
                render_action=render_action,
                text_format=text_format,
                max_chars_per_item=_optional_limit(entry.get("max_chars_per_item"), row, col),
                max_lines=_optional_limit(entry.get("max_lines"), row, col),
                max_chars_per_line=_optional_limit(entry.get("max_chars_per_line"), row, col),
            )
        )
        if row not in optional_rows and col not in optional_cols:
            required_coords.add((row, col))
    return render_cells, required_coords


def _optional_axis_indexes(raw: Any, label: str, key: str) -> set[int]:
    """Indexes of the rows/columns whose ``content_policy`` is ``optional``."""
    if raw is None:
        return set()
    if not isinstance(raw, list):
        raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} {label} must be an array")
    optional: set[int] = set()
    seen: set[int] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError(f"each {_TABLE_CONFIG_TAG!r} {label} entry must be an object")
        index = _coordinate(entry.get(key), f"{label}.{key}")
        if index in seen:
            raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} {label} has a duplicate {key} {index}")
        seen.add(index)
        policy = entry.get("content_policy", "required")
        if policy not in _CONTENT_POLICIES:
            raise ValueError(
                f"{label} entry {index} content_policy must be one of {sorted(_CONTENT_POLICIES)}"
            )
        if policy == _OPTIONAL_POLICY:
            optional.add(index)
    return optional


def _coordinate(value: Any, label: str) -> int:
    # bool is an int subclass; a JSON true/false is not a coordinate.
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"tag {_TABLE_CONFIG_TAG!r} {label} must be a non-negative integer")
    return value


def _optional_limit(value: Any, row: int, col: int) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"cell ({row},{col}) sizing limits must be positive integers")
    return value

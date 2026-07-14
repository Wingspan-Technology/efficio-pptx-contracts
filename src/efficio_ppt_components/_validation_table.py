"""Table component per-instance validation schema.

Emits ``cells`` as an object keyed by ``"row,col"`` — one property per allowed
(``render``) cell, each carrying its own item-count/length limits. Required cells
go in ``required``; optional cells are properties but not required; the object's
``additionalProperties`` is ``false`` so any cell not configured for render is
rejected by name (``/cells/9,9``). A content violation reports the exact cell and
item (``/cells/3,1/items/0``). Preserve and default-preserve cells are dropped;
when every cell is preserved ``cells`` is an empty object (``properties: {}``,
``additionalProperties: false``). Object keys make duplicate coordinates
unrepresentable, so no explicit ``contains``/uniqueness rule is needed.
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
    min_items: int | None
    max_items: int | None
    min_chars_per_item: int | None
    max_chars_per_item: int | None


def _table_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    render_cells, required_coords = _parse_table_config(_required_tag(tags, _TABLE_CONFIG_TAG, "table"))

    schema = _base_content_schema("table")
    # cells is an object keyed by "row,col": one property per render cell. Object
    # keys give allowed-coordinate + no-duplicate enforcement for free; a cell not
    # configured for render is rejected by name via additionalProperties: false.
    # No render cells (every cell preserved) -> an empty object; only {} validates.
    cells_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {_coord_key(cell): _cell_value_schema(cell) for cell in render_cells},
    }
    required = [_coord_key(cell) for cell in render_cells if (cell.row, cell.col) in required_coords]
    if required:
        cells_schema["required"] = required
    schema["properties"]["cells"] = cells_schema
    return schema


def _coord_key(cell: _TableCell) -> str:
    """The ``"row,col"`` object key for a render cell."""
    return f"{cell.row},{cell.col}"


def _cell_value_schema(cell: _TableCell) -> dict[str, Any]:
    """The schema the content value for one allowed coordinate must match.

    Mirrors the text builder's item bounds, but per cell and all-optional: a render
    cell always holds at least one item (base ``minItems`` 1); ``plain`` pins it to
    exactly one; otherwise ``min_items`` / ``max_items`` bound the item count and
    ``min_chars_per_item`` / ``max_chars_per_item`` bound each item's length when
    present. The aggregate ``max_chars`` and the ``target_*`` guidance never appear.
    """
    items: dict[str, Any] = {"type": "array", "minItems": 1}
    if cell.text_format == _PLAIN_FORMAT:
        items["maxItems"] = 1
    else:
        if cell.min_items is not None:
            items["minItems"] = cell.min_items
        if cell.max_items is not None:
            items["maxItems"] = cell.max_items
    item: dict[str, Any] = {"type": "string"}
    if cell.min_chars_per_item is not None:
        item["minLength"] = cell.min_chars_per_item
    if cell.max_chars_per_item is not None:
        item["maxLength"] = cell.max_chars_per_item
    items["items"] = item
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {"items": items},
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
                min_items=_optional_limit(entry.get("min_items"), row, col),
                max_items=_optional_limit(entry.get("max_items"), row, col),
                min_chars_per_item=_optional_limit(entry.get("min_chars_per_item"), row, col),
                max_chars_per_item=_optional_limit(entry.get("max_chars_per_item"), row, col),
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

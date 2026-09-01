"""Table component per-instance validation schema.

Emits ``cells`` as an object keyed by ``"row,col"`` — one property per render
cell, each carrying its own item-count and length limits. Optional row or column
policies make a cell optional; preserved and unconfigured cells are rejected by
``additionalProperties: false``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._table_config import (
    TABLE_CONFIG_TAG,
    TableCell,
    TableConfig,
    parse_table_config,
)
from ._validation_common import _base_content_schema, _required_tag


def _table_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    config = _validated_table_config(tags)
    render_cells = config.render_cells

    schema = _base_content_schema("table")
    cells_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            cell.coordinate_key: _cell_value_schema(cell) for cell in render_cells
        },
    }
    required = [
        cell.coordinate_key
        for cell in render_cells
        if _cell_is_required(config, cell)
    ]
    if required:
        cells_schema["required"] = required
    schema["properties"]["cells"] = cells_schema
    return schema


def _validated_table_config(tags: Mapping[str, str]) -> TableConfig:
    """Return the shared table model after structural and semantic validation."""
    _reject_invalid_table_config(tags)
    raw = _required_tag(tags, TABLE_CONFIG_TAG, "table")
    return parse_table_config(raw)


def _reject_invalid_table_config(tags: Mapping[str, str]) -> None:
    """Preserve the public tag-validator errors before model construction."""
    from .tag_validation import validate_component_tags

    invalid = [
        issue.message
        for issue in validate_component_tags("table", dict(tags))
        if issue.tag_name == TABLE_CONFIG_TAG
    ]
    if invalid:
        raise ValueError(f"invalid {TABLE_CONFIG_TAG!r}: {'; '.join(invalid)}")


def _cell_is_required(config: TableConfig, cell: TableCell) -> bool:
    row = config.row(cell.row)
    column = config.column(cell.col)
    return not (
        (row is not None and row.optional)
        or (column is not None and column.optional)
    )


def _cell_value_schema(cell: TableCell) -> dict[str, Any]:
    """Build the canonical content value schema for one render cell."""
    items: dict[str, Any] = {"type": "array", "minItems": 1}
    if cell.plain:
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

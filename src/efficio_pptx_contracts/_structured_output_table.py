"""V2 Structured Outputs projection and normalization for table components."""

# Provider-content validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from ._structured_output_common import join_sentences
from ._text_capacity import (
    build_text_items_schema,
    estimated_line_usage,
    text_capacity_metadata,
    text_capacity_description,
    validate_text_capacity_metadata,
)
from ._table_config import TableAxis, TableCell
from ._validation_table import _validated_table_config
from .ai_projection import PROMPT_INSTRUCTION_TAG

_COORDINATE = re.compile(r"^(0|[1-9][0-9]*),(0|[1-9][0-9]*)$")


def build_table_v2_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    """Build an exact coordinate-keyed table contract from validated config."""
    config = _validated_table_config(tags)
    component_instruction = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()

    properties: dict[str, Any] = {}
    optional_cells: list[str] = []
    capacities: dict[str, dict[str, int]] = {}
    for cell in config.render_cells:
        coordinate = cell.coordinate_key
        row = config.row(cell.row)
        column = config.column(cell.col)
        row_optional, column_optional = _optionality(row, column)
        optional = row_optional or column_optional
        description = _cell_description(
            cell,
            component_instruction,
            row,
            column,
            row_optional=row_optional,
            column_optional=column_optional,
        )
        cell_schema = _cell_schema(cell, description)
        properties[coordinate] = (
            {
                "description": description,
                "anyOf": [cell_schema, {"type": "null"}],
            }
            if optional
            else cell_schema
        )
        if optional:
            optional_cells.append(coordinate)
        capacity = text_capacity_metadata(cell.capacity)
        if capacity is not None:
            capacities[coordinate] = capacity

    description = join_sentences(
        component_instruction,
        "Return generated content only for the listed zero-based row,column coordinates",
        "Every listed coordinate must be present; use null only where its description says optional",
        "For an optional row, return null for every render cell when the row does not apply; "
        "meaningful non-whitespace text in any valid render cell keeps the row",
        "A column-only optional cell may be null without removing its row",
        "If every physical row is optional and empty, the original first row remains",
        "Never invent filler or placeholder content to keep an optional row",
    )
    output_schema = {
        "type": "object",
        "description": description,
        "properties": {
            "cells": {
                "type": "object",
                "description": "Generated table cells keyed by zero-based row,column coordinate.",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            }
        },
        "required": ["cells"],
        "additionalProperties": False,
    }
    return {
        "component_type": "table",
        "output_schema": output_schema,
        "normalization": {
            "optional_cells": optional_cells,
            "text_capacity": capacities,
        },
    }


def normalize_table_v2_content(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    """Remove explicitly null optional cells without mutating caller content."""
    cells = content.get("cells")
    if not isinstance(cells, Mapping):
        raise ValueError("table V2 content at /cells must be an object")
    optional, _ = _validated_table_normalization(normalization)
    normalized_cells: dict[str, Any] = {}
    for coordinate, value in cells.items():
        if value is None:
            if coordinate not in optional:
                raise ValueError(
                    f"table V2 content at /cells/{coordinate} cannot be null"
                )
            continue
        normalized_cells[str(coordinate)] = copy.deepcopy(value)
    normalized = copy.deepcopy(dict(content))
    normalized["cells"] = normalized_cells
    return normalized


def validate_table_v2_semantics(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    """Enforce configured aggregate character and estimated line limits."""
    cells = content.get("cells")
    if not isinstance(cells, Mapping):
        raise ValueError("table V2 content at /cells must be an object")
    _, capacities = _validated_table_normalization(normalization)
    for coordinate, limits in capacities.items():
        cell = cells.get(coordinate)
        if cell is None:
            continue
        maximum_lines, chars_per_line, minimum_chars, maximum_chars = limits
        if minimum_chars is not None and maximum_chars is not None:
            actual_chars = table_v2_cell_character_usage(coordinate, cell)
            if actual_chars < minimum_chars or actual_chars > maximum_chars:
                raise ValueError(
                    f"table V2 content at /cells/{coordinate}/items uses "
                    f"{actual_chars} characters; required range is "
                    f"{minimum_chars}–{maximum_chars}"
                )
        if maximum_lines is None or chars_per_line is None:
            continue
        actual_lines = table_v2_cell_estimated_line_usage(
            coordinate, cell, chars_per_line=chars_per_line
        )
        if actual_lines > maximum_lines:
            raise ValueError(
                f"table V2 content at /cells/{coordinate}/items uses an estimated "
                f"{actual_lines} lines; maximum is {maximum_lines}"
            )


def table_v2_cell_estimated_line_usage(
    coordinate: str,
    content: object,
    *,
    chars_per_line: int,
) -> int:
    """Return estimated lines for one canonically shaped table cell."""
    if (
        not isinstance(content, Mapping)
        or not isinstance(content.get("items"), list)
        or any(not isinstance(item, str) for item in content["items"])
    ):
        raise ValueError(
            f"table V2 content at /cells/{coordinate}/items must be an array of strings"
        )
    return estimated_line_usage(content["items"], chars_per_line=chars_per_line)


def table_v2_cell_character_usage(coordinate: str, content: object) -> int:
    """Return aggregate characters for one canonically shaped table cell."""
    if (
        not isinstance(content, Mapping)
        or not isinstance(content.get("items"), list)
        or any(not isinstance(item, str) for item in content["items"])
    ):
        raise ValueError(
            f"table V2 content at /cells/{coordinate}/items must be an array of strings"
        )
    return sum(len(item) for item in content["items"])


def validate_table_v2_normalization(normalization: Mapping[str, Any]) -> None:
    """Validate the exact trusted table metadata shape."""
    _validated_table_normalization(normalization)


def _validated_table_normalization(
    normalization: Mapping[str, Any],
) -> tuple[
    set[str],
    dict[str, tuple[int | None, int | None, int | None, int | None]],
]:
    if set(normalization) != {"optional_cells", "text_capacity"}:
        raise ValueError(
            "table V2 normalization must contain exactly optional_cells and text_capacity"
        )
    raw_optional = normalization["optional_cells"]
    if not isinstance(raw_optional, list) or any(
        not isinstance(coordinate, str) or _COORDINATE.fullmatch(coordinate) is None
        for coordinate in raw_optional
    ):
        raise ValueError(
            "table V2 normalization optional_cells must contain valid row,column strings"
        )
    if len(raw_optional) != len(set(raw_optional)):
        raise ValueError("table V2 normalization optional_cells must not contain duplicates")

    raw_capacities = normalization["text_capacity"]
    if not isinstance(raw_capacities, Mapping):
        raise ValueError("table V2 normalization text_capacity must be an object")
    capacities: dict[
        str, tuple[int | None, int | None, int | None, int | None]
    ] = {}
    for coordinate, capacity in raw_capacities.items():
        if not isinstance(coordinate, str) or _COORDINATE.fullmatch(coordinate) is None:
            raise ValueError(
                "table V2 normalization text_capacity has an invalid coordinate"
            )
        if not isinstance(capacity, Mapping):
            raise ValueError(
                "table V2 normalization text_capacity values must be objects"
            )
        capacities[coordinate] = validate_text_capacity_metadata(capacity)
    return set(raw_optional), capacities


def _optionality(
    row: TableAxis | None, column: TableAxis | None
) -> tuple[bool, bool]:
    return (
        row is not None and row.optional,
        column is not None and column.optional,
    )


def _cell_schema(cell: TableCell, description: str) -> dict[str, Any]:
    items_schema = build_text_items_schema(cell.capacity, plain=cell.plain)
    items_schema["description"] = description
    items_schema["items"]["description"] = "One generated table-cell text item."
    return {
        "type": "object",
        "description": description,
        "properties": {"items": items_schema},
        "required": ["items"],
        "additionalProperties": False,
    }


def _cell_description(
    cell: TableCell,
    component_instruction: str,
    row: TableAxis | None,
    column: TableAxis | None,
    *,
    row_optional: bool,
    column_optional: bool,
) -> str:
    return join_sentences(
        component_instruction,
        row.instruction if row is not None else "",
        column.instruction if column is not None else "",
        cell.instruction,
        text_capacity_description(cell.capacity, plain=cell.plain),
        f"Each item is one {cell.text_format.replace('_', '-')} content unit, not one rendered line",
        _optionality_description(row_optional, column_optional),
    )


def _optionality_description(row_optional: bool, column_optional: bool) -> str:
    if row_optional:
        reason = (
            "This cell is nullable because both its row and column are optional"
            if column_optional
            else "This cell is nullable because its row is optional"
        )
        return join_sentences(
            reason,
            "Return null for every render cell in this row when the row does not apply",
            "The row is removed when none of its valid render cells contains meaningful "
            "non-whitespace generated text",
            "If every physical row is optional and empty, the original first row remains",
            "Return meaningful content for at least one render cell to keep the row; "
            "do not invent filler or placeholder content",
        )
    if column_optional:
        return join_sentences(
            "This cell is nullable because its column is optional",
            "Return null when no content applies; this does not remove the row",
        )
    return ""

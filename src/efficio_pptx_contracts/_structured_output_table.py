"""V2 Structured Outputs projection and normalization for table components."""

# Provider-content validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from typing import Any

from ._structured_output_common import (
    ensure_aggregate_character_budget_is_feasible,
    join_sentences,
    string_schema,
)
from ._validation_table import _table_validation_schema
from .ai_projection import PROMPT_INSTRUCTION_TAG

_TABLE_CONFIG_TAG = "efficio_table_config"
_COORDINATE = re.compile(r"^(0|[1-9][0-9]*),(0|[1-9][0-9]*)$")


def build_table_v2_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    """Build an exact coordinate-keyed table contract from validated config."""
    _table_validation_schema(tags)
    config = json.loads(tags[_TABLE_CONFIG_TAG])
    row_context = _axis_context(config.get("rows"), "row")
    column_context = _axis_context(config.get("columns"), "col")
    component_instruction = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()

    properties: dict[str, Any] = {}
    optional_cells: list[str] = []
    maximum_chars: dict[str, int] = {}
    for cell in config["cells"]:
        if cell.get("render_action", "preserve") != "render":
            continue
        coordinate = f"{cell['row']},{cell['col']}"
        row = row_context.get(cell["row"], {})
        column = column_context.get(cell["col"], {})
        row_optional, column_optional = _optionality(row, column)
        optional = row_optional or column_optional
        _validate_cell_feasibility(cell, coordinate)
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
        if isinstance(cell.get("max_chars"), int):
            maximum_chars[coordinate] = cell["max_chars"]

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
            "max_chars": maximum_chars,
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
    """Enforce configured aggregate character budgets on present cells."""
    cells = content.get("cells")
    if not isinstance(cells, Mapping):
        raise ValueError("table V2 content at /cells must be an object")
    _, limits = _validated_table_normalization(normalization)
    for coordinate, maximum in limits.items():
        cell = cells.get(coordinate)
        if cell is None:
            continue
        actual = table_v2_cell_character_usage(coordinate, cell)
        if actual > maximum:
            raise ValueError(
                f"table V2 content at /cells/{coordinate}/items uses {actual} characters; "
                f"maximum is {maximum}"
            )


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
) -> tuple[set[str], dict[str, int]]:
    if set(normalization) != {"optional_cells", "max_chars"}:
        raise ValueError(
            "table V2 normalization must contain exactly optional_cells and max_chars"
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

    raw_limits = normalization["max_chars"]
    if not isinstance(raw_limits, Mapping):
        raise ValueError("table V2 normalization max_chars must be an object")
    limits: dict[str, int] = {}
    for coordinate, maximum in raw_limits.items():
        if not isinstance(coordinate, str) or _COORDINATE.fullmatch(coordinate) is None:
            raise ValueError("table V2 normalization max_chars has an invalid coordinate")
        if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
            raise ValueError(
                "table V2 normalization max_chars values must be positive integers"
            )
        limits[coordinate] = maximum
    return set(raw_optional), limits


def _axis_context(raw: Any, key: str) -> dict[int, dict[str, Any]]:
    if not isinstance(raw, list):
        return {}
    return {entry[key]: entry for entry in raw if isinstance(entry, dict) and key in entry}


def _optionality(
    row: Mapping[str, Any], column: Mapping[str, Any]
) -> tuple[bool, bool]:
    return (
        row.get("content_policy", "required") == "optional",
        column.get("content_policy", "required") == "optional",
    )


def _cell_schema(cell: Mapping[str, Any], description: str) -> dict[str, Any]:
    text_format = cell.get("text_format", "plain")
    minimum_items = 1 if text_format == "plain" else cell.get("min_items", 1)
    maximum_items = 1 if text_format == "plain" else cell.get("max_items")
    items_schema: dict[str, Any] = {
        "type": "array",
        "description": description,
        "items": string_schema(
            cell.get("min_chars_per_item"),
            cell.get("max_chars_per_item"),
            description="One generated table-cell text item.",
        ),
        "minItems": minimum_items,
    }
    if maximum_items is not None:
        items_schema["maxItems"] = maximum_items
    return {
        "type": "object",
        "description": description,
        "properties": {"items": items_schema},
        "required": ["items"],
        "additionalProperties": False,
    }


def _validate_cell_feasibility(cell: Mapping[str, Any], coordinate: str) -> None:
    maximum_chars = cell.get("max_chars")
    if maximum_chars is None:
        return
    text_format = cell.get("text_format", "plain")
    minimum_items = 1 if text_format == "plain" else cell.get("min_items", 1)
    ensure_aggregate_character_budget_is_feasible(
        minimum_items=minimum_items,
        minimum_chars_per_item=cell.get("min_chars_per_item", 0),
        maximum_chars=maximum_chars,
        subject=f"table V2 cell {coordinate!r} non-null contract",
    )


def _cell_description(
    cell: Mapping[str, Any],
    component_instruction: str,
    row: Mapping[str, Any],
    column: Mapping[str, Any],
    *,
    row_optional: bool,
    column_optional: bool,
) -> str:
    text_format = cell.get("text_format", "plain")
    minimum_items = 1 if text_format == "plain" else cell.get("min_items", 1)
    maximum_items = 1 if text_format == "plain" else cell.get("max_items")
    return join_sentences(
        component_instruction,
        str(row.get("instruction", "")),
        str(column.get("instruction", "")),
        str(cell.get("instruction", "")),
        _count_description(text_format, minimum_items, maximum_items),
        _character_description(cell),
        _optionality_description(row_optional, column_optional),
        _target_description(cell),
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


def _count_description(text_format: str, minimum: int, maximum: int | None) -> str:
    label = text_format.replace("_", "-")
    if maximum == minimum:
        return f"Return exactly {minimum} {label} item" + ("" if minimum == 1 else "s")
    if maximum is None:
        return f"Return at least {minimum} {label} item" + ("" if minimum == 1 else "s")
    return f"Return {minimum}–{maximum} {label} items"


def _character_description(cell: Mapping[str, Any]) -> str:
    minimum, maximum = cell.get("min_chars_per_item"), cell.get("max_chars_per_item")
    parts: list[str] = []
    if minimum is not None and maximum is not None:
        parts.append(f"Each item must contain {minimum}–{maximum} characters")
    elif minimum is not None:
        parts.append(f"Each item must contain at least {minimum} characters")
    elif maximum is not None:
        parts.append(f"Each item must contain at most {maximum} characters")
    if cell.get("max_chars") is not None:
        parts.append(
            f"The combined item length must not exceed {cell['max_chars']} characters"
        )
    return join_sentences(*parts)


def _target_description(cell: Mapping[str, Any]) -> str:
    targets: list[str] = []
    for field, label in (
        ("target_items", "items"),
        ("target_chars", "characters total"),
        ("target_chars_per_item", "characters per item"),
    ):
        if cell.get(field) is not None:
            targets.append(f"{cell[field]} {label}")
    return "Aim for approximately " + ", and ".join(targets) if targets else ""

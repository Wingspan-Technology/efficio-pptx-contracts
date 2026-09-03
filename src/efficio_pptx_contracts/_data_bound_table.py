"""Renderer-safe, limit-free data-bound table contract and normalization."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from ._validation_table import _cell_is_required, _validated_table_config

_COORDINATE = re.compile(r"^(0|[1-9][0-9]*),(0|[1-9][0-9]*)$")


def build_data_bound_table_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    config = _validated_table_config(tags)
    optional_cells: list[str] = []
    properties: dict[str, Any] = {}
    required: list[str] = []
    for cell in config.render_cells:
        coordinate = cell.coordinate_key
        schema = _cell_schema()
        if _cell_is_required(config, cell):
            properties[coordinate] = schema
            required.append(coordinate)
        else:
            properties[coordinate] = {"anyOf": [schema, {"type": "null"}]}
            optional_cells.append(coordinate)
    return {
        "submission_schema": {
            "type": "object",
            "properties": {
                "cells": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                }
            },
            "required": ["cells"],
            "additionalProperties": False,
        },
        "normalization": {"optional_cells": optional_cells},
    }


def normalize_data_bound_table(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    optional = _validate_normalization(normalization)
    cells = content.get("cells")
    if not isinstance(cells, Mapping):
        raise ValueError("data-bound table content at /cells must be an object")
    normalized_cells: dict[str, Any] = {}
    for coordinate, value in cells.items():
        if value is None:
            if coordinate not in optional:
                raise ValueError(f"data-bound table content at /cells/{coordinate} cannot be null")
            continue
        normalized_cells[str(coordinate)] = copy.deepcopy(value)
    normalized = copy.deepcopy(dict(content))
    normalized["cells"] = normalized_cells
    return normalized


def validate_data_bound_table_coherence(
    schema: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    optional = _validate_normalization(normalization)
    properties = _object_properties(schema, "data-bound table")
    if set(properties) != {"cells"} or schema.get("required") != ["cells"]:
        raise ValueError("data-bound table schema must contain exactly cells")
    cells_schema = properties["cells"]
    cells = _object_properties(cells_schema, "data-bound table cells")
    required = cells_schema.get("required")
    if not isinstance(required, list) or any(not isinstance(item, str) for item in required):
        raise ValueError("data-bound table required cells must be a string array")
    if set(required) != set(cells) - optional:
        raise ValueError("data-bound table required and optional cells disagree")
    if optional - set(cells):
        raise ValueError("data-bound table optional cells must exist in its schema")
    for coordinate, cell_schema in cells.items():
        if _COORDINATE.fullmatch(coordinate) is None:
            raise ValueError("data-bound table schema contains an invalid coordinate")
        _validate_cell_schema(cell_schema, coordinate in optional)


def _cell_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
        "required": ["items"],
        "additionalProperties": False,
    }


def _validate_normalization(normalization: Mapping[str, Any]) -> set[str]:
    if set(normalization) != {"optional_cells"}:
        raise ValueError("data-bound table normalization must contain optional_cells")
    raw = normalization["optional_cells"]
    if not isinstance(raw, list) or any(
        not isinstance(value, str) or _COORDINATE.fullmatch(value) is None for value in raw
    ):
        raise ValueError("data-bound table optional_cells are invalid")
    if len(raw) != len(set(raw)):
        raise ValueError("data-bound table optional_cells must not contain duplicates")
    return set(raw)


def _object_properties(schema: object, label: str) -> Mapping[str, Any]:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError(f"{label} schema must be an object")
    if set(schema) != {"type", "properties", "required", "additionalProperties"}:
        raise ValueError(f"{label} schema fields are invalid")
    if schema.get("additionalProperties") is not False:
        raise ValueError(f"{label} schema must be closed")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError(f"{label} schema must declare properties")
    return properties


def _validate_cell_schema(schema: object, nullable: bool) -> None:
    if not isinstance(schema, Mapping):
        raise ValueError("data-bound table cell schema must be an object")
    branches = schema.get("anyOf")
    content = schema
    if nullable:
        if set(schema) != {"anyOf"} or not isinstance(branches, list) or len(branches) != 2:
            raise ValueError("optional data-bound table cells must be nullable")
        objects = [
            item for item in branches if isinstance(item, Mapping) and item.get("type") == "object"
        ]
        if len(objects) != 1 or {"type": "null"} not in branches:
            raise ValueError("optional data-bound table cell branches are invalid")
        content = objects[0]
    elif branches is not None:
        raise ValueError("required data-bound table cells cannot be nullable")
    properties = _object_properties(content, "data-bound table cell")
    if set(properties) != {"items"} or content.get("required") != ["items"]:
        raise ValueError("data-bound table cell schema must contain exactly items")
    items = properties["items"]
    if (
        not isinstance(items, Mapping)
        or set(items) != {"type", "items", "minItems"}
        or items.get("type") != "array"
        or items.get("minItems") != 1
    ):
        raise ValueError("data-bound table cell items schema is invalid")
    if items.get("items") != {"type": "string"}:
        raise ValueError("data-bound table cell items must be strings")

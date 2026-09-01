"""Cross-field coherence checks for persisted V2 component contracts."""

# Persisted contract validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

_COORDINATE = re.compile(r"^(0|[1-9][0-9]*),(0|[1-9][0-9]*)$")


def validate_v2_component_shape_coherence(
    component_type: str,
    output_schema: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> None:
    """Require the prompt schema and private metadata to agree structurally."""
    if component_type == "text":
        _validate_text_shape(output_schema)
    elif component_type == "table":
        _validate_table_shape(output_schema, normalization)
    else:
        _validate_chart_shape(output_schema, normalization)


def _validate_text_shape(schema: Mapping[str, Any]) -> None:
    properties = _object_properties(schema, "text")
    if set(properties) != {"items"}:
        raise ValueError("text V2 schema must contain exactly the items property")
    _require_nonempty_array(properties["items"], "string", "text items")


def _validate_table_shape(
    schema: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    properties = _object_properties(schema, "table")
    if set(properties) != {"cells"}:
        raise ValueError("table V2 schema must contain exactly the cells property")
    cell_properties = _object_properties(properties["cells"], "table cells")
    schema_cells = set(cell_properties)
    if any(
        not isinstance(coordinate, str) or _COORDINATE.fullmatch(coordinate) is None
        for coordinate in schema_cells
    ):
        raise ValueError("table V2 schema contains an invalid cell coordinate")

    nullable_cells: set[str] = set()
    for coordinate, cell_schema in cell_properties.items():
        content_schema, nullable = _table_cell_content_schema(cell_schema)
        content_properties = _object_properties(content_schema, "table cell")
        if set(content_properties) != {"items"}:
            raise ValueError(
                "table cell V2 schema must contain exactly the items property"
            )
        _require_nonempty_array(
            content_properties["items"], "string", "table cell items"
        )
        if nullable:
            nullable_cells.add(coordinate)

    optional_cells = set(normalization["optional_cells"])
    if nullable_cells != optional_cells:
        raise ValueError(
            "table V2 nullable cell schemas must exactly match optional_cells metadata"
        )
    if not set(normalization["max_chars"]) <= schema_cells:
        raise ValueError(
            "table V2 max_chars metadata must reference declared cell schemas"
        )


def _validate_chart_shape(
    schema: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    properties = _object_properties(schema, "category-chart")
    category_mode = normalization["category_mode"]
    series_mode = normalization["series_mode"]
    expected = {"series"} if category_mode == "fixed" else {"categories", "series"}
    if set(properties) != expected:
        raise ValueError("category-chart V2 schema properties do not match category mode")
    if category_mode != "fixed":
        _require_nonempty_array(
            properties["categories"], "string", "generated chart categories"
        )
    _validate_chart_series(properties["series"], series_mode=series_mode)


def _validate_chart_series(schema: object, *, series_mode: str) -> None:
    item = _require_nonempty_array(schema, None, "category-chart series")
    properties = _object_properties(item, "category-chart series item")
    expected = {"values"} if series_mode == "fixed" else {"name", "values"}
    if set(properties) != expected:
        raise ValueError("category-chart V2 series item does not match series mode")
    if series_mode != "fixed":
        name = properties["name"]
        if not isinstance(name, Mapping) or name.get("type") != "string":
            raise ValueError("generated category-chart series name must be a string")
    _require_nonempty_array(
        properties["values"], {"integer", "number"}, "category-chart values"
    )


def _object_properties(schema: object, subject: str) -> Mapping[str, Any]:
    if not isinstance(schema, Mapping) or schema.get("type") != "object":
        raise ValueError(f"{subject} V2 schema must be an object")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        raise ValueError(f"{subject} V2 schema must declare properties")
    return properties


def _require_nonempty_array(
    schema: object, expected_item_type: str | set[str] | None, subject: str
) -> Mapping[str, Any]:
    if not isinstance(schema, Mapping) or schema.get("type") != "array":
        raise ValueError(f"{subject} V2 schema must be an array")
    minimum = schema.get("minItems")
    maximum = schema.get("maxItems")
    if (
        not isinstance(minimum, int)
        or isinstance(minimum, bool)
        or minimum < 1
    ):
        raise ValueError(f"{subject} V2 schema must have a positive minItems")
    if maximum is not None and (
        not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < minimum
    ):
        raise ValueError(
            f"{subject} V2 schema maxItems must be at least minItems"
        )
    item = schema.get("items")
    if not isinstance(item, Mapping):
        raise ValueError(f"{subject} V2 schema must declare an item schema")
    if expected_item_type is not None:
        actual = item.get("type")
        valid = (
            actual == expected_item_type
            if isinstance(expected_item_type, str)
            else actual in expected_item_type
        )
        if not valid:
            raise ValueError(f"{subject} V2 array item type is invalid")
    return item


def _table_cell_content_schema(
    schema: object,
) -> tuple[Mapping[str, Any], bool]:
    if not isinstance(schema, Mapping):
        raise ValueError("table V2 cell schema must be an object")
    branches = schema.get("anyOf")
    if branches is None:
        return schema, False
    if not isinstance(branches, list) or len(branches) != 2:
        raise ValueError(
            "nullable table V2 cell schema must have one object and one null branch"
        )
    nulls = [branch for branch in branches if branch == {"type": "null"}]
    objects = [
        branch
        for branch in branches
        if isinstance(branch, Mapping) and branch.get("type") == "object"
    ]
    if len(nulls) != 1 or len(objects) != 1:
        raise ValueError(
            "nullable table V2 cell schema must have one object and one null branch"
        )
    return objects[0], True


__all__ = ["validate_v2_component_shape_coherence"]

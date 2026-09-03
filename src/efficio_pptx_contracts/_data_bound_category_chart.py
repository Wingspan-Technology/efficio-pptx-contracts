"""Renderer-safe, limit-free data-bound category-chart contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._category_chart_validation import FIXED_MODE
from ._structured_output_category_chart import normalize_category_chart_v2_content
from ._validation_category_chart import _validated_config


def build_data_bound_category_chart_contract(
    tags: Mapping[str, str],
) -> dict[str, Any]:
    config = _validated_config(tags)
    categories_fixed = config["category_mode"] == FIXED_MODE
    series_fixed = config["series_mode"] == FIXED_MODE
    category_count = len(config["categories"]) if categories_fixed else None
    properties: dict[str, Any] = {}
    if not categories_fixed:
        properties["categories"] = {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        }
    properties["series"] = _series_schema(config, category_count, series_fixed)
    return {
        "submission_schema": {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        },
        "normalization": {
            "category_mode": config["category_mode"],
            "fixed_categories": list(config["categories"]) if categories_fixed else None,
            "series_mode": config["series_mode"],
            "fixed_series_names": list(config["series_names"]) if series_fixed else None,
        },
    }


def normalize_data_bound_category_chart(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    normalized = normalize_category_chart_v2_content(content, normalization)
    categories = normalized.get("categories")
    series = normalized.get("series")
    if not isinstance(categories, list) or not categories:
        raise ValueError("data-bound category-chart categories must be a non-empty array")
    if not isinstance(series, list) or not series:
        raise ValueError("data-bound category-chart series must be a non-empty array")
    for index, item in enumerate(series):
        values = item.get("values") if isinstance(item, Mapping) else None
        if not isinstance(values, list) or len(values) != len(categories):
            raise ValueError(
                "data-bound category-chart values count must match categories "
                f"at /series/{index}/values"
            )
    return normalized


def validate_data_bound_category_chart_coherence(
    schema: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    category_mode, fixed_categories, series_mode, fixed_names = _normalization(normalization)
    properties = _object_properties(schema, "data-bound category-chart")
    expected = {"series"} if category_mode == FIXED_MODE else {"categories", "series"}
    required = schema.get("required")
    if (
        set(properties) != expected
        or not isinstance(required, list)
        or len(required) != len(set(required))
        or set(required) != expected
    ):
        raise ValueError("data-bound category-chart schema does not match category mode")
    if category_mode != FIXED_MODE:
        _validate_array(properties["categories"], {"type": "string"}, None)
    series_schema = properties["series"]
    expected_count = len(fixed_names) if series_mode == FIXED_MODE and fixed_names else None
    series_item = _validate_array(series_schema, None, expected_count)
    item_properties = _object_properties(series_item, "data-bound category-chart series")
    expected_fields = {"values"} if series_mode == FIXED_MODE else {"name", "values"}
    if set(item_properties) != expected_fields:
        raise ValueError("data-bound category-chart series schema does not match series mode")
    item_required = series_item.get("required")
    if (
        not isinstance(item_required, list)
        or len(item_required) != len(set(item_required))
        or set(item_required) != expected_fields
    ):
        raise ValueError("data-bound category-chart series required fields are invalid")
    if series_mode != FIXED_MODE and item_properties["name"] != {"type": "string"}:
        raise ValueError("data-bound category-chart names must be strings")
    value_count = (
        len(fixed_categories) if category_mode == FIXED_MODE and fixed_categories else None
    )
    _validate_array(item_properties["values"], {"type": "number"}, value_count)


def _series_schema(
    config: Mapping[str, Any], category_count: int | None, fixed: bool
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    if not fixed:
        properties["name"] = {"type": "string"}
    values: dict[str, Any] = {
        "type": "array",
        "items": {"type": "number"},
        "minItems": category_count or 1,
    }
    if category_count is not None:
        values["maxItems"] = category_count
    properties["values"] = values
    item = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    count = len(config["series_names"]) if fixed else None
    schema: dict[str, Any] = {"type": "array", "items": item, "minItems": count or 1}
    if count is not None:
        schema["maxItems"] = count
    return schema


def _normalization(
    normalization: Mapping[str, Any],
) -> tuple[str, list[str] | None, str, list[str] | None]:
    expected = {"category_mode", "fixed_categories", "series_mode", "fixed_series_names"}
    if set(normalization) != expected:
        raise ValueError("data-bound category-chart normalization fields are invalid")
    category_mode, series_mode = normalization["category_mode"], normalization["series_mode"]
    fixed_categories = normalization["fixed_categories"]
    fixed_names = normalization["fixed_series_names"]
    if category_mode not in {FIXED_MODE, "ai_generated"} or series_mode not in {
        FIXED_MODE,
        "ai_generated",
    }:
        raise ValueError("data-bound category-chart normalization modes are invalid")
    if category_mode == FIXED_MODE and not _string_list(fixed_categories):
        raise ValueError("fixed data-bound categories are invalid")
    if category_mode != FIXED_MODE and fixed_categories is not None:
        raise ValueError("generated data-bound categories cannot carry fixed values")
    if series_mode == FIXED_MODE and not _string_list(fixed_names):
        raise ValueError("fixed data-bound series names are invalid")
    if series_mode != FIXED_MODE and fixed_names is not None:
        raise ValueError("generated data-bound series cannot carry fixed names")
    return category_mode, fixed_categories, series_mode, fixed_names


def _string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
    )


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


def _validate_array(
    schema: object, item_schema: Mapping[str, Any] | None, exact_count: int | None
) -> Mapping[str, Any]:
    if not isinstance(schema, Mapping) or schema.get("type") != "array":
        raise ValueError("data-bound category-chart schema must use arrays")
    expected_fields = {"type", "items", "minItems"}
    if exact_count is not None:
        expected_fields.add("maxItems")
    if set(schema) != expected_fields:
        raise ValueError("data-bound category-chart array fields are invalid")
    if schema.get("minItems") != (exact_count or 1):
        raise ValueError("data-bound category-chart array minimum is invalid")
    if exact_count is not None and schema.get("maxItems") != exact_count:
        raise ValueError("data-bound category-chart fixed array count is invalid")
    item = schema.get("items")
    if not isinstance(item, Mapping) or (item_schema is not None and item != item_schema):
        raise ValueError("data-bound category-chart array items are invalid")
    return item

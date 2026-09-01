"""V2 Structured Outputs projection and normalization for category charts."""

# Provider-content validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ._category_chart_validation import (
    CATEGORY_INSTRUCTION_TAG,
    FIXED_MODE,
    PERCENT_STACKED_CHART_TYPES,
    SERIES_INSTRUCTION_TAG,
    VALUE_UNIT_TAG,
)
from ._structured_output_common import (
    join_sentences,
    string_schema,
)
from ._validation_category_chart import _validated_config
from .ai_projection import PROMPT_INSTRUCTION_TAG

_MAX_CATEGORY_COUNT_BRANCHES = 100


def build_category_chart_v2_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    """Build a chart schema for all fixed/generated category/series modes."""
    config = _validated_config(tags)
    category_instruction = tags.get(CATEGORY_INSTRUCTION_TAG, "").strip()
    series_instruction = tags.get(SERIES_INSTRUCTION_TAG, "").strip()
    categories_hard = _categories_hard_description(config)
    series_hard = _series_hard_description(config)
    categories_target = _categories_target_description(config)
    series_target = _series_target_description(config)
    categories_description = join_sentences(
        category_instruction, categories_hard, categories_target
    )
    series_description = join_sentences(
        series_instruction, series_hard, series_target
    )
    values_description = _values_description(config, tags)
    prompt = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()
    component_description = join_sentences(
        prompt,
        category_instruction,
        series_instruction,
        f"Generate content for a {config['chart_type']} category chart",
        "Return values in category order",
        categories_hard,
        series_hard,
        values_description,
        categories_target,
        series_target,
    )

    output_schema = _chart_schema(
        config,
        component_description=component_description,
        categories_description=categories_description,
        series_description=series_description,
        values_description=values_description,
    )

    normalization: dict[str, Any] = {
        "category_mode": config["category_mode"],
        "fixed_categories": list(config["categories"])
        if config["category_mode"] == FIXED_MODE
        else None,
        "series_mode": config["series_mode"],
        "fixed_series_names": list(config["series_names"])
        if config["series_mode"] == FIXED_MODE
        else None,
    }
    return {
        "component_type": "category_chart",
        "output_schema": output_schema,
        "normalization": normalization,
    }


def normalize_category_chart_v2_content(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    """Inject authoritative fixed labels/names into a copied chart payload."""
    normalized = copy.deepcopy(dict(content))
    category_mode, fixed_categories, series_mode, fixed_names = _validated_normalization(
        normalization
    )
    if category_mode == FIXED_MODE:
        assert fixed_categories is not None
        if "categories" in normalized:
            raise ValueError("category-chart V2 content must omit fixed categories")
        normalized["categories"] = list(fixed_categories)

    if series_mode == FIXED_MODE:
        assert fixed_names is not None
        series = normalized.get("series")
        if not isinstance(series, list) or len(series) != len(fixed_names):
            raise ValueError(
                "category-chart V2 content series count does not match fixed series names"
            )
        injected: list[dict[str, Any]] = []
        for index, (item, name) in enumerate(zip(series, fixed_names, strict=True)):
            if not isinstance(item, Mapping):
                raise ValueError(f"category-chart V2 content at /series/{index} must be an object")
            if "name" in item:
                raise ValueError(
                    f"category-chart V2 content at /series/{index} must omit its fixed name"
                )
            injected.append({"name": name, **copy.deepcopy(dict(item))})
        normalized["series"] = injected
    return normalized


def validate_category_chart_v2_normalization(normalization: Mapping[str, Any]) -> None:
    """Validate exact chart modes and their fixed-value metadata."""
    _validated_normalization(normalization)


def _chart_schema(
    config: Mapping[str, Any],
    *,
    component_description: str,
    categories_description: str,
    series_description: str,
    values_description: str,
) -> dict[str, Any]:
    if config["category_mode"] == FIXED_MODE:
        return _chart_object_schema(
            config,
            category_count=len(config["categories"]),
            include_categories=False,
            component_description=component_description,
            categories_description=categories_description,
            series_description=series_description,
            values_description=values_description,
        )

    branch_count = config["max_categories"] - config["min_categories"] + 1
    if branch_count > _MAX_CATEGORY_COUNT_BRANCHES:
        raise ValueError(
            "category-chart V2 category range creates "
            f"{branch_count} correlated schema branches; narrow min_categories "
            f"and max_categories to at most {_MAX_CATEGORY_COUNT_BRANCHES} possible counts"
        )
    if branch_count == 1:
        return _chart_object_schema(
            config,
            category_count=config["min_categories"],
            include_categories=True,
            component_description=component_description,
            categories_description=categories_description,
            series_description=series_description,
            values_description=values_description,
        )
    schema = _chart_object_schema(
        config,
        category_count=None,
        include_categories=True,
        component_description=component_description,
        categories_description=categories_description,
        series_description=series_description,
        values_description=values_description,
    )
    schema["oneOf"] = [
        _chart_object_schema(
            config,
            category_count=count,
            include_categories=True,
            component_description=component_description,
            categories_description=categories_description,
            series_description=series_description,
            values_description=values_description,
        )
        for count in range(config["min_categories"], config["max_categories"] + 1)
    ]
    return schema


def _chart_object_schema(
    config: Mapping[str, Any],
    *,
    category_count: int | None,
    include_categories: bool,
    component_description: str,
    categories_description: str,
    series_description: str,
    values_description: str,
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    if include_categories:
        minimum = category_count or config["min_categories"]
        maximum = category_count or config["max_categories"]
        properties["categories"] = {
            "type": "array",
            "description": categories_description,
            "items": string_schema(1, description="One non-empty category label."),
            "minItems": minimum,
            "maxItems": maximum,
        }
    properties["series"] = _series_schema(
        config,
        category_count=category_count,
        series_description=series_description,
        values_description=values_description,
    )
    return {
        "type": "object",
        "description": component_description,
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def _series_schema(
    config: Mapping[str, Any],
    *,
    category_count: int | None,
    series_description: str,
    values_description: str,
) -> dict[str, Any]:
    fixed = config["series_mode"] == FIXED_MODE
    properties: dict[str, Any] = {}
    if not fixed:
        properties["name"] = string_schema(1, description="One non-empty generated series name.")
    value_schema: dict[str, Any] = {
        "type": "integer" if not config["allow_decimal_values"] else "number"
    }
    if (
        not config["allow_negative_values"]
        or config["chart_type"] in PERCENT_STACKED_CHART_TYPES
    ):
        value_schema["minimum"] = 0
    values_minimum = category_count or config["min_categories"]
    values_maximum = category_count or config["max_categories"]
    properties["values"] = {
        "type": "array",
        "description": values_description,
        "items": value_schema,
        "minItems": values_minimum,
        "maxItems": values_maximum,
    }
    item = {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }
    if fixed:
        minimum = maximum = len(config["series_names"])
    else:
        minimum, maximum = config["min_series"], config["max_series"]
    return {
        "type": "array",
        "description": series_description,
        "items": item,
        "minItems": minimum,
        "maxItems": maximum,
    }


def _categories_hard_description(config: Mapping[str, Any]) -> str:
    if config["category_mode"] == FIXED_MODE:
        labels = ", ".join(repr(label) for label in config["categories"])
        return f"Use these fixed categories in order: {labels}"
    return (
        f"Generate {config['min_categories']}–{config['max_categories']} "
        "non-empty category labels"
    )


def _categories_target_description(config: Mapping[str, Any]) -> str:
    if config["category_mode"] == FIXED_MODE:
        return (
            f"The authored target is {config['target_categories']} categories; "
            "fixed labels remain authoritative"
        )
    return f"Aim for approximately {config['target_categories']} categories"


def _series_hard_description(config: Mapping[str, Any]) -> str:
    if config["series_mode"] == FIXED_MODE:
        names = ", ".join(repr(name) for name in config["series_names"])
        return f"Return values for these fixed series in order: {names}; omit their names"
    return f"Generate {config['min_series']}–{config['max_series']} named series"


def _series_target_description(config: Mapping[str, Any]) -> str:
    if config["series_mode"] == FIXED_MODE:
        return (
            f"The authored target is {config['target_series']} series; "
            "fixed names remain authoritative"
        )
    return f"Aim for approximately {config['target_series']} series"


def _values_description(config: Mapping[str, Any], tags: Mapping[str, str]) -> str:
    numeric_type = "whole-number" if not config["allow_decimal_values"] else "numeric"
    sign = "non-negative" if (
        not config["allow_negative_values"]
        or config["chart_type"] in PERCENT_STACKED_CHART_TYPES
    ) else "positive or negative"
    unit = tags.get(VALUE_UNIT_TAG, "").strip()
    unit_guidance = f"Interpret values using the {unit!r} unit" if unit else ""
    return join_sentences(
        f"Return one {sign} {numeric_type} value per category, in category order",
        unit_guidance,
    )


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) and bool(item) for item in value
    )


def _validated_normalization(
    normalization: Mapping[str, Any],
) -> tuple[str, list[str] | None, str, list[str] | None]:
    expected = {"category_mode", "fixed_categories", "series_mode", "fixed_series_names"}
    if set(normalization) != expected:
        raise ValueError(
            "category-chart V2 normalization must contain exactly category_mode, "
            "fixed_categories, series_mode, and fixed_series_names"
        )
    category_mode = normalization["category_mode"]
    series_mode = normalization["series_mode"]
    fixed_categories = normalization["fixed_categories"]
    fixed_names = normalization["fixed_series_names"]
    _validate_axis_metadata("category", category_mode, fixed_categories)
    _validate_axis_metadata("series", series_mode, fixed_names)
    return category_mode, fixed_categories, series_mode, fixed_names


def _validate_axis_metadata(axis: str, mode: Any, fixed_values: Any) -> None:
    if mode not in {FIXED_MODE, "ai_generated"}:
        raise ValueError(f"category-chart V2 {axis}_mode metadata is invalid")
    if mode == FIXED_MODE:
        if not _is_string_list(fixed_values) or not fixed_values:
            raise ValueError(
                f"category-chart V2 fixed {axis} metadata must be a non-empty string array"
            )
    elif fixed_values is not None:
        raise ValueError(
            f"category-chart V2 generated {axis} metadata must not carry fixed values"
        )

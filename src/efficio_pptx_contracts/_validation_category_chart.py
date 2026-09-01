"""Strict per-instance validation schema for category_chart content.

Builds a Draft 2020-12 schema from a chart's flat tags so a chart response is
validated exactly: category labels/counts, series names/counts, and one numeric
value per category per series, with value constraints (integer-only, non-negative)
derived from the tags.

The flat tags are validated first — structurally per tag and semantically
(cross-field) via :func:`validate_component_tags` — so an invalid configuration
raises ``ValueError`` rather than yielding a permissive schema. The emitted schema
is pure validation keywords: no prose, no ``component_type``, no ``$schema``, no
raw ``efficio_*`` tags.

When categories are fixed, the category count is known and baked into each series'
``values`` length. When categories are AI-generated the count varies, so the root
carries a ``oneOf`` with one branch per allowed count that pins ``categories``
length and every series' ``values`` length to the same number.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ._category_chart_validation import (
    ALLOW_DECIMAL_TAG,
    ALLOW_NEGATIVE_TAG,
    CATEGORIES_TAG,
    CATEGORY_CHART_TAG_NAMES,
    CATEGORY_MODE_TAG,
    CHART_TYPE_TAG,
    FIXED_MODE,
    MAX_CATEGORIES_TAG,
    MAX_SERIES_TAG,
    MIN_CATEGORIES_TAG,
    MIN_SERIES_TAG,
    PERCENT_STACKED_CHART_TYPES,
    SERIES_MODE_TAG,
    SERIES_NAMES_TAG,
    TARGET_CATEGORIES_TAG,
    TARGET_SERIES_TAG,
)
from .tag_validation import validate_component_tags


def _category_chart_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    return _strict_schema(_validated_config(tags))


# ── flat-tag parsing + validation ────────────────────────────────────────────


def _validated_config(tags: Mapping[str, str]) -> dict[str, Any]:
    """Validate the flat chart tags and assemble the config dict the schema builder
    consumes. Any structural (per-tag) or cross-field problem raises ``ValueError``
    rather than yielding a permissive schema."""
    issues = [
        issue
        for issue in validate_component_tags("category_chart", dict(tags))
        if issue.tag_name is None or issue.tag_name in CATEGORY_CHART_TAG_NAMES
    ]
    if issues:
        raise ValueError(
            "category_chart tags are invalid: " + "; ".join(issue.message for issue in issues)
        )
    config: dict[str, Any] = {
        "chart_type": tags[CHART_TYPE_TAG],
        "category_mode": tags[CATEGORY_MODE_TAG],
        "series_mode": tags[SERIES_MODE_TAG],
        "min_categories": int(tags[MIN_CATEGORIES_TAG]),
        "max_categories": int(tags[MAX_CATEGORIES_TAG]),
        "target_categories": int(tags[TARGET_CATEGORIES_TAG]),
        "min_series": int(tags[MIN_SERIES_TAG]),
        "max_series": int(tags[MAX_SERIES_TAG]),
        "target_series": int(tags[TARGET_SERIES_TAG]),
        "allow_negative_values": tags[ALLOW_NEGATIVE_TAG] == "true",
        "allow_decimal_values": tags[ALLOW_DECIMAL_TAG] == "true",
    }
    if config["category_mode"] == FIXED_MODE:
        config["categories"] = json.loads(tags[CATEGORIES_TAG])
    if config["series_mode"] == FIXED_MODE:
        config["series_names"] = json.loads(tags[SERIES_NAMES_TAG])
    return config


# ── schema construction ──────────────────────────────────────────────────────


def _strict_schema(config: dict[str, Any]) -> dict[str, Any]:
    categories_fixed = config["category_mode"] == FIXED_MODE
    # Fixed categories fix the value count directly; AI-generated ones vary and
    # are pinned per branch (values_length None here, set in _count_branch).
    values_length = len(config["categories"]) if categories_fixed else None

    properties: dict[str, Any] = {"series": _series_schema(config, values_length)}
    required = ["series"]

    if categories_fixed:
        # Optional; if present it must equal the configured labels exactly.
        properties["categories"] = {"const": list(config["categories"])}
    else:
        properties["categories"] = {
            "type": "array",
            "minItems": config["min_categories"],
            "maxItems": config["max_categories"],
            "items": {"type": "string", "minLength": 1},
        }
        required.append("categories")

    schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }
    if not categories_fixed:
        schema["oneOf"] = [
            _count_branch(config, count)
            for count in range(config["min_categories"], config["max_categories"] + 1)
        ]
    return schema


def _series_schema(config: dict[str, Any], values_length: int | None) -> dict[str, Any]:
    """The ``series`` array schema for the configured series mode."""
    value_schema = _value_schema(config)
    if config["series_mode"] == FIXED_MODE:
        names = config["series_names"]
        if len(names) == 1:
            # Exactly one series; its name is optional but const if present.
            item = _series_item(value_schema, values_length, {"const": names[0]}, name_required=False)
            return {"type": "array", "minItems": 1, "maxItems": 1, "items": item}
        # Multiple series: exact count with positional const names.
        return {
            "type": "array",
            "minItems": len(names),
            "maxItems": len(names),
            "prefixItems": [
                _series_item(value_schema, values_length, {"const": name}, name_required=True)
                for name in names
            ],
            "items": False,
        }
    # AI-generated series: count within bounds, each item a non-empty name.
    item = _series_item(
        value_schema, values_length, {"type": "string", "minLength": 1}, name_required=True
    )
    return {
        "type": "array",
        "minItems": config["min_series"],
        "maxItems": config["max_series"],
        "items": item,
    }


def _series_item(
    value_schema: dict[str, Any],
    values_length: int | None,
    name_schema: dict[str, Any],
    *,
    name_required: bool,
) -> dict[str, Any]:
    values: dict[str, Any] = {"type": "array", "items": value_schema}
    if values_length is not None:
        values["minItems"] = values_length
        values["maxItems"] = values_length
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "values"] if name_required else ["values"],
        "properties": {"name": name_schema, "values": values},
    }


def _value_schema(config: dict[str, Any]) -> dict[str, Any]:
    """One series value's numeric constraints, derived from the config."""
    schema: dict[str, Any] = {"type": "number"}
    if not config["allow_decimal_values"]:
        schema["multipleOf"] = 1
    percent_stacked = config["chart_type"] in PERCENT_STACKED_CHART_TYPES
    # Percent-stacked charts never take negatives, regardless of the flag.
    if percent_stacked or not config["allow_negative_values"]:
        schema["minimum"] = 0
    return schema


def _count_branch(config: dict[str, Any], count: int) -> dict[str, Any]:
    """One AI-generated-categories branch pinning category and value counts to ``count``."""
    length: dict[str, Any] = {"minItems": count, "maxItems": count}
    item_length: dict[str, Any] = {"properties": {"values": length}}
    series_length: dict[str, Any]
    if config["series_mode"] == FIXED_MODE and len(config["series_names"]) > 1:
        series_length = {"prefixItems": [item_length for _ in config["series_names"]]}
    else:
        series_length = {"items": item_length}
    return {"properties": {"categories": length, "series": series_length}}

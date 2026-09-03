"""Public limit-free contracts for trusted externally calculated content."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ._data_bound_category_chart import (
    build_data_bound_category_chart_contract,
    normalize_data_bound_category_chart,
    validate_data_bound_category_chart_coherence,
)
from ._data_bound_table import (
    build_data_bound_table_contract,
    normalize_data_bound_table,
    validate_data_bound_table_coherence,
)
from ._data_bound_text import (
    build_data_bound_text_contract,
    normalize_data_bound_text,
)
from ._structured_output_schema_validation import validate_v2_executable_component_schema
from .registry import assert_component_type

_Builder = Callable[[Mapping[str, str]], dict[str, Any]]
_Normalizer = Callable[[Mapping[str, Any], Mapping[str, Any]], dict[str, Any]]

_BUILDERS: dict[str, _Builder] = {
    "text": build_data_bound_text_contract,
    "table": build_data_bound_table_contract,
    "category_chart": build_data_bound_category_chart_contract,
}
_NORMALIZERS: dict[str, _Normalizer] = {
    "text": normalize_data_bound_text,
    "table": normalize_data_bound_table,
    "category_chart": normalize_data_bound_category_chart,
}


def build_data_bound_component_contract(
    component_type: str, tags: Mapping[str, str]
) -> dict[str, Any]:
    """Build a renderer-safe schema without authored AI content limits."""
    builder = _builder(component_type)
    contract = builder(tags)
    validate_data_bound_component_contract_coherence(
        component_type,
        contract["submission_schema"],
        contract["normalization"],
    )
    return contract


def normalize_data_bound_component_content(
    component_type: str,
    content: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize validated data-bound content into the renderer's canonical shape."""
    _builder(component_type)
    if not isinstance(content, Mapping) or not isinstance(normalization, Mapping):
        raise ValueError("data-bound content and normalization must be objects")
    return _NORMALIZERS[component_type](content, normalization)


def validate_data_bound_component_contract_coherence(
    component_type: str,
    submission_schema: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> None:
    """Validate one persisted data-bound schema and its private metadata together."""
    _builder(component_type)
    if not isinstance(submission_schema, Mapping) or not isinstance(normalization, Mapping):
        raise ValueError("data-bound schema and normalization must be objects")
    validate_v2_executable_component_schema(submission_schema, require_prompt_profile=False)
    if component_type == "text":
        if normalization:
            raise ValueError("data-bound text normalization must be empty")
        _validate_text_schema(submission_schema)
    elif component_type == "table":
        validate_data_bound_table_coherence(submission_schema, normalization)
    else:
        validate_data_bound_category_chart_coherence(submission_schema, normalization)


def _builder(component_type: str) -> _Builder:
    builder = _BUILDERS.get(component_type)
    if builder is not None:
        return builder
    assert_component_type(component_type)
    raise ValueError(f"component type {component_type!r} has no data-bound contract")


def _validate_text_schema(schema: Mapping[str, Any]) -> None:
    if set(schema) != {"type", "properties", "required", "additionalProperties"}:
        raise ValueError("data-bound text schema fields are invalid")
    if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise ValueError("data-bound text schema must be a closed object")
    properties = schema.get("properties")
    if not isinstance(properties, Mapping) or set(properties) != {"items"}:
        raise ValueError("data-bound text schema must contain exactly items")
    if schema.get("required") != ["items"]:
        raise ValueError("data-bound text schema must require items")
    items = properties["items"]
    if not isinstance(items, Mapping) or set(items) != {"type", "items", "minItems"}:
        raise ValueError("data-bound text items schema is invalid")
    if items.get("type") != "array" or items.get("minItems") != 1:
        raise ValueError("data-bound text items must be a non-empty array")
    if items.get("items") != {"type": "string"}:
        raise ValueError("data-bound text items must contain strings")


__all__ = [
    "build_data_bound_component_contract",
    "normalize_data_bound_component_content",
    "validate_data_bound_component_contract_coherence",
]

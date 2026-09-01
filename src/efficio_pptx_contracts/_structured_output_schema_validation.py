"""Closed Draft 2020-12 schema checks for executable V2 component schemas."""

# Persisted schema validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

from ._structured_output_common import validate_prompt_json_schema


def validate_v2_executable_component_schema(
    schema: Mapping[str, Any], *, require_prompt_profile: bool
) -> None:
    """Validate one persisted prompt or canonical component schema."""
    if not isinstance(schema, Mapping):
        raise ValueError("component schema must be an object")
    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as error:
        raise ValueError("component schema is not valid Draft 2020-12") from error
    _validate_executable_schema_nodes(schema)
    if not _has_object_only_root(schema):
        raise ValueError("component schema root must be a non-null object")
    if require_prompt_profile:
        validate_prompt_json_schema(schema)


def _validate_executable_schema_nodes(schema: Mapping[str, Any]) -> None:
    stack: list[Mapping[str, Any]] = [schema]
    numeric_keywords = {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
    }
    while stack:
        node = stack.pop()
        if "$ref" in node or "$dynamicRef" in node:
            raise ValueError(
                "component schemas must not contain $ref or $dynamicRef references"
            )
        for keyword in numeric_keywords & set(node):
            value = node[keyword]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError(
                    f"component schema {keyword} must be finite numeric"
                )
            if keyword == "multipleOf" and value <= 0:
                raise ValueError(
                    "component schema multipleOf must be greater than zero"
                )
        for value in node.values():
            if isinstance(value, Mapping):
                stack.append(value)
            elif isinstance(value, list):
                stack.extend(
                    item for item in value if isinstance(item, Mapping)
                )


def _has_object_only_root(schema: Mapping[str, Any]) -> bool:
    if schema.get("type") == "object":
        return True
    branches = schema.get("anyOf")
    return (
        isinstance(branches, list)
        and bool(branches)
        and all(
            isinstance(branch, Mapping) and _has_object_only_root(branch)
            for branch in branches
        )
    )


__all__ = ["validate_v2_executable_component_schema"]

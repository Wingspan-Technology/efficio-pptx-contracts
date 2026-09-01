"""Shared provider-neutral prompt JSON Schema V2 helpers."""

# Prompt-schema validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

JSON_SCHEMA_DRAFT_2020_12_PROFILE = "json-schema-draft-2020-12"
JSON_SCHEMA_DRAFT_2020_12_URI = "https://json-schema.org/draft/2020-12/schema"

_COMMON_KEYWORDS = frozenset(
    {"type", "description", "enum", "const", "anyOf", "oneOf"}
)
_NUMERIC_KEYWORDS = frozenset(
    {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"}
)
_TYPE_KEYWORDS = {
    "object": frozenset({"properties", "required", "additionalProperties"}),
    "array": frozenset({"items", "minItems", "maxItems"}),
    "string": frozenset({"minLength", "maxLength"}),
    "number": _NUMERIC_KEYWORDS,
    "integer": _NUMERIC_KEYWORDS,
    "boolean": frozenset(),
    "null": frozenset(),
}


def validate_prompt_json_schema(
    schema: Mapping[str, Any],
    *,
    require_object_root: bool = True,
    require_schema_declaration: bool = False,
) -> None:
    """Validate the deterministic V2 Draft 2020-12 schema subset.

    Component fragments omit ``$schema``. Complete response schemas opt into
    and require the exact Draft 2020-12 declaration.
    """
    if not isinstance(schema, Mapping):
        raise ValueError("structured output schema must be an object")
    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as error:
        raise ValueError("structured output schema is not valid Draft 2020-12") from error
    declaration = schema.get("$schema")
    if require_schema_declaration:
        if declaration != JSON_SCHEMA_DRAFT_2020_12_URI:
            raise ValueError(
                "complete structured output schema must declare Draft 2020-12"
            )
    elif declaration is not None:
        raise ValueError("structured output component fragments must omit $schema")
    if require_object_root and schema.get("type") != "object":
        raise ValueError("structured output root schema must have type 'object'")
    if require_object_root and "anyOf" in schema:
        raise ValueError("structured output root schema must not use anyOf")
    _validate_schema_node(
        schema,
        path="$",
        allow_schema_declaration=require_schema_declaration,
    )


def ensure_aggregate_character_budget_is_feasible(
    *,
    minimum_items: int,
    minimum_chars_per_item: int,
    maximum_chars: int,
    subject: str,
) -> None:
    """Reject a V2 item contract whose aggregate character cap is impossible."""
    required_characters = minimum_items * minimum_chars_per_item
    if maximum_chars < required_characters:
        raise ValueError(
            f"{subject} cannot satisfy max_chars {maximum_chars}: "
            f"at least {minimum_items} item(s) with {minimum_chars_per_item} "
            f"characters require {required_characters} characters"
        )


def _validate_schema_node(
    schema: Mapping[str, Any], *, path: str, allow_schema_declaration: bool = False
) -> None:
    if not isinstance(schema, Mapping):
        raise ValueError(f"structured output schema at {path} must be an object")

    schema_type = schema.get("type")
    has_union = "anyOf" in schema
    if schema_type not in _TYPE_KEYWORDS and not (schema_type is None and has_union):
        raise ValueError(
            f"structured output schema at {path} has unsupported or missing type"
        )
    if has_union and schema_type is not None:
        raise ValueError(
            f"structured output nullable anyOf at {path} must not also declare type"
        )

    allowed = set(_COMMON_KEYWORDS)
    if isinstance(schema_type, str):
        allowed.update(_TYPE_KEYWORDS[schema_type])
    if allow_schema_declaration:
        allowed.add("$schema")
    unsupported = sorted(set(schema) - allowed)
    if unsupported:
        raise ValueError(
            f"structured output schema at {path} uses unsupported keywords: "
            f"{unsupported}"
        )

    description = schema.get("description")
    if description is not None and not isinstance(description, str):
        raise ValueError(f"structured output description at {path} must be a string")
    _validate_enum_and_const(schema, path)

    if schema_type == "object":
        _validate_object(schema, path)
    elif schema_type == "array":
        _validate_array(schema, path)
    elif schema_type == "string":
        _validate_string(schema, path)
    elif schema_type in {"number", "integer"}:
        _validate_numeric(schema, path)

    branches = schema.get("anyOf")
    if branches is not None:
        if not isinstance(branches, list) or len(branches) != 2:
            raise ValueError(
                f"structured output anyOf at {path} must contain exactly one "
                "non-null branch and one null branch"
            )
        null_branches = [branch for branch in branches if branch == {"type": "null"}]
        if len(null_branches) != 1:
            raise ValueError(
                f"structured output anyOf at {path} must contain exactly one "
                "non-null branch and one null branch"
            )
        for index, branch in enumerate(branches):
            _validate_schema_node(branch, path=f"{path}/anyOf/{index}")

    alternatives = schema.get("oneOf")
    if alternatives is not None:
        if not isinstance(alternatives, list) or not alternatives:
            raise ValueError(
                f"structured output oneOf at {path} must be a non-empty array"
            )
        for index, branch in enumerate(alternatives):
            _validate_schema_node(branch, path=f"{path}/oneOf/{index}")


def _validate_object(schema: Mapping[str, Any], path: str) -> None:
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, Mapping):
        raise ValueError(f"structured output object at {path} must declare properties")
    if schema.get("additionalProperties") is not False:
        raise ValueError(
            f"structured output object at {path} must set additionalProperties to false"
        )
    if not isinstance(required, list) or set(required) != set(properties):
        raise ValueError(
            f"structured output object at {path} required names must exactly "
            "match its declared properties"
        )
    for name, child in properties.items():
        if not isinstance(name, str):
            raise ValueError(
                f"structured output property name at {path} must be a string"
            )
        _validate_schema_node(child, path=f"{path}/properties/{name}")


def _validate_array(schema: Mapping[str, Any], path: str) -> None:
    items = schema.get("items")
    if not isinstance(items, Mapping):
        raise ValueError(f"structured output array at {path} must declare an item schema")
    _validate_non_negative_bounds(schema, path, "minItems", "maxItems")
    _validate_schema_node(items, path=f"{path}/items")


def _validate_string(schema: Mapping[str, Any], path: str) -> None:
    _validate_non_negative_bounds(schema, path, "minLength", "maxLength")


def _validate_non_negative_bounds(
    schema: Mapping[str, Any], path: str, minimum_name: str, maximum_name: str
) -> None:
    for keyword in (minimum_name, maximum_name):
        value = schema.get(keyword)
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise ValueError(
                f"structured output {keyword} at {path} must be a non-negative integer"
            )
    minimum = schema.get(minimum_name)
    maximum = schema.get(maximum_name)
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(
            f"structured output {minimum_name} at {path} must not exceed {maximum_name}"
        )


def _validate_numeric(schema: Mapping[str, Any], path: str) -> None:
    for keyword in _NUMERIC_KEYWORDS:
        value = schema.get(keyword)
        if value is None:
            continue
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"structured output {keyword} at {path} must be finite numeric"
            )
        if keyword == "multipleOf" and value <= 0:
            raise ValueError(
                f"structured output multipleOf at {path} must be greater than zero"
            )


def _validate_enum_and_const(schema: Mapping[str, Any], path: str) -> None:
    enum = schema.get("enum")
    if enum is not None:
        if not isinstance(enum, list) or not enum:
            raise ValueError(
                f"structured output enum at {path} must be a non-empty array"
            )
        if any(not _is_primitive(value) for value in enum):
            raise ValueError(
                f"structured output enum at {path} may contain only primitive values"
            )
    if "const" in schema and not _is_primitive(schema["const"]):
        raise ValueError(
            f"structured output const at {path} must be a primitive value"
        )


def _is_primitive(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool, int)):
        return True
    return isinstance(value, float) and math.isfinite(value)


def string_schema(
    minimum: int | None = None,
    maximum: int | None = None,
    *,
    description: str | None = None,
) -> dict[str, Any]:
    """Return a bounded string schema in deterministic keyword order."""
    if minimum is not None and minimum < 0:
        raise ValueError("minimum string length must be non-negative")
    if maximum is not None and maximum < 0:
        raise ValueError("maximum string length must be non-negative")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("minimum string length must not exceed maximum")
    schema: dict[str, Any] = {"type": "string"}
    if description:
        schema["description"] = description
    if minimum is not None:
        schema["minLength"] = minimum
    if maximum is not None:
        schema["maxLength"] = maximum
    return schema


def sentence(value: str) -> str:
    """Trim prose and terminate it once for deterministic description joins."""
    trimmed = value.strip()
    if not trimmed:
        return ""
    return trimmed if trimmed[-1] in ".!?" else f"{trimmed}."


def join_sentences(*values: str) -> str:
    """Join non-blank snippets into compact, deterministic prose."""
    return " ".join(part for value in values if (part := sentence(value)))

"""Tests for the provider-neutral prompt JSON Schema profile."""

from __future__ import annotations

import math

import pytest
from efficio_pptx_contracts import (
    JSON_SCHEMA_DRAFT_2020_12_URI,
    validate_prompt_json_schema,
    validate_v2_executable_component_schema,
)


def _object(properties: dict | None = None) -> dict:
    properties = properties or {}
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def test_profile_accepts_closed_objects_nested_unions_and_descriptions() -> None:
    schema = _object(
        {
            "value": {
                "anyOf": [
                    {"type": "string", "description": "Generated content."},
                    {"type": "null"},
                ]
            },
            "items": {
                "type": "array",
                "items": {"type": "integer"},
                "minItems": 1,
                "maxItems": 3,
            },
        }
    )

    validate_prompt_json_schema(schema)


def test_profile_rejects_non_nullable_anyof_fragment() -> None:
    schema = {
        "anyOf": [
            _object({"a": {"type": "string"}}),
            _object({"b": {"type": "number"}}),
        ]
    }

    with pytest.raises(ValueError, match="root schema must have type 'object'"):
        validate_prompt_json_schema(schema)
    with pytest.raises(ValueError, match="one non-null branch and one null branch"):
        validate_prompt_json_schema(schema, require_object_root=False)


def test_profile_rejects_anyof_even_when_root_also_declares_object() -> None:
    schema = _object({"value": {"type": "string"}})
    schema["anyOf"] = [_object({"value": {"type": "string"}})]

    with pytest.raises(ValueError, match="root schema must not use anyOf"):
        validate_prompt_json_schema(schema)


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        (
            {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
            "additionalProperties",
        ),
        (
            {
                "type": "object",
                "properties": {"a": {"type": "string"}},
                "required": [],
                "additionalProperties": False,
            },
            "required names",
        ),
        (_object({"value": {"type": "array"}}), "item schema"),
    ],
)
def test_profile_rejects_non_strict_schema(schema: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_prompt_json_schema(schema)


def test_profile_accepts_jsonb_reordered_object_properties() -> None:
    schema = {
        "type": "object",
        "properties": {
            "series": {"type": "array", "items": {"type": "number"}},
            "categories": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["categories", "series"],
        "additionalProperties": False,
    }

    validate_prompt_json_schema(schema)


@pytest.mark.parametrize(
    "property_schema",
    [
        {"type": "string", "pattern": "^[a-z]+$"},
        {"type": "string", "format": "date"},
        {"type": "string", "$ref": "#/$defs/value"},
        {"type": "string", "allOf": [{"type": "string"}]},
    ],
)
def test_profile_rejects_keywords_outside_the_prompt_subset(
    property_schema: dict,
) -> None:
    with pytest.raises(ValueError, match="unsupported keywords"):
        validate_prompt_json_schema(_object({"value": property_schema}))


@pytest.mark.parametrize("minimum", [0, 1, 2, 100])
def test_profile_accepts_non_negative_min_items_values(minimum: int) -> None:
    validate_prompt_json_schema(
        _object(
            {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": minimum,
                }
            }
        )
    )


@pytest.mark.parametrize("minimum", [-1, True, 1.5])
def test_profile_rejects_invalid_min_items_values(minimum: object) -> None:
    schema = _object(
        {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": minimum,
            }
        }
    )

    with pytest.raises(ValueError, match="Draft 2020-12|non-negative integer"):
        validate_prompt_json_schema(schema)


def test_profile_accepts_exact_bounds_numeric_constraints_and_oneof() -> None:
    branch = _object(
        {
            "items": {
                "type": "array",
                "items": {"type": "string", "minLength": 2, "maxLength": 10},
                "minItems": 2,
                "maxItems": 4,
            },
            "value": {"type": "number", "minimum": 0, "maximum": 100},
        }
    )
    schema = _object(branch["properties"])
    schema["oneOf"] = [branch]

    validate_prompt_json_schema(schema)


@pytest.mark.parametrize(
    "property_schema",
    [
        {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 1},
        {"type": "string", "minLength": 2, "maxLength": 1},
        {"type": "number", "multipleOf": 0},
    ],
)
def test_profile_rejects_invalid_hard_constraints(property_schema: dict) -> None:
    with pytest.raises(ValueError, match="Draft 2020-12|must not exceed|greater than zero"):
        validate_prompt_json_schema(_object({"value": property_schema}))


def test_profile_requires_schema_declaration_only_for_complete_roots() -> None:
    fragment = _object({"value": {"type": "string"}})
    complete = {"$schema": JSON_SCHEMA_DRAFT_2020_12_URI, **fragment}

    validate_prompt_json_schema(fragment)
    validate_prompt_json_schema(complete, require_schema_declaration=True)
    with pytest.raises(ValueError, match=r"fragments must omit \$schema"):
        validate_prompt_json_schema(complete)
    with pytest.raises(ValueError, match="must declare Draft 2020-12"):
        validate_prompt_json_schema(fragment, require_schema_declaration=True)


def test_profile_accepts_only_primitive_finite_enum_and_const_values() -> None:
    validate_prompt_json_schema(
        _object(
            {
                "value": {
                    "type": "string",
                    "enum": [None, "A", True, 1, 1.5],
                    "const": "A",
                }
            }
        )
    )

    for invalid in ({"nested": True}, ["nested"], math.nan):
        with pytest.raises(ValueError, match="primitive"):
            validate_prompt_json_schema(
                _object({"value": {"type": "string", "enum": [invalid]}})
            )


def test_profile_rejects_unresolved_reference_in_persisted_schema() -> None:
    schema = _object(
        {"value": {"type": "string", "$ref": "#/$defs/missing"}}
    )

    with pytest.raises(ValueError, match=r"unsupported keywords.*\$ref"):
        validate_prompt_json_schema(schema)


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ({"type": "string"}, "non-null object"),
        (
            {"anyOf": [{"type": "object"}, {"type": "null"}]},
            "non-null object",
        ),
        ({"type": "object", "multipleOf": 0}, "Draft 2020-12"),
        ({"type": "object", "$ref": "https://invalid/schema"}, "references"),
        ({"type": "object", "$dynamicRef": "#thing"}, "references"),
    ],
)
def test_executable_component_schema_rejects_unsafe_roots_and_keywords(
    schema: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        validate_v2_executable_component_schema(
            schema, require_prompt_profile=False
        )


def test_executable_component_schema_accepts_object_only_root_union() -> None:
    schema = {
        "anyOf": [
            _object(),
            _object({"x": {"type": "string"}}),
        ]
    }

    validate_v2_executable_component_schema(
        schema, require_prompt_profile=False
    )


def test_canonical_hard_bounds_are_executable_and_prompt_safe() -> None:
    canonical_schema = _object(
        {
            "items": {
                "type": "array",
                "items": {"type": "string", "minLength": 5, "maxLength": 40},
                "minItems": 2,
                "maxItems": 4,
            }
        }
    )

    validate_v2_executable_component_schema(
        canonical_schema, require_prompt_profile=False
    )
    validate_v2_executable_component_schema(
        canonical_schema, require_prompt_profile=True
    )

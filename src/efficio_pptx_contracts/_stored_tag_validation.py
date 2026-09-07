"""Stored-tag-value primitives shared by component and presentation validation.

PowerPoint custom tags always store strings. This module owns the generic
value-level rules applied to one stored tag: native type, enum membership,
length/pattern/minimum constraints, and JSON Schema validation for object/array
tags stored as JSON text. It knows nothing about components, slides, or decks.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, cast

from jsonschema import Draft202012Validator


@dataclass(frozen=True)
class TagValidationIssue:
    code: str
    message: str
    tag_name: str | None = None


def validate_component_value(
    tag_name: str,
    value: object,
    expected_type: object,
    enums: dict[str, list[str]],
    json_schemas: dict[str, dict[str, Any]],
) -> list[TagValidationIssue]:
    """Validate one component tag value against its compatibility-schema type."""
    if not isinstance(value, str):
        return [type_issue(tag_name, "string", value)]

    if expected_type in {"json_object", "json_array"}:
        return validate_structured_value(
            tag_name, value, expected_type, json_schemas.get(tag_name)
        )

    issues: list[TagValidationIssue] = []
    if expected_type == "non_empty_string" and not value.strip():
        issues.append(
            TagValidationIssue(
                code="empty_tag_value",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be a non-empty string.",
            )
        )
    if expected_type == "positive_integer_string" and (
        not value.isascii() or not value.isdecimal() or int(value) < 1
    ):
        issues.append(
            TagValidationIssue(
                code="invalid_positive_integer",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be a positive integer string.",
            )
        )
    if expected_type in {"enum", "enum_boolean_string"}:
        allowed = enums.get(tag_name, [])
        if value not in allowed:
            issues.append(enum_issue(tag_name, value, allowed))
    return issues


def validate_structured_value(
    tag_name: str,
    value: str,
    expected_type: str,
    tag_schema: object,
) -> list[TagValidationIssue]:
    """Validate an object/array tag stored as JSON text against its JSON Schema."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as decode_error:
        return [
            TagValidationIssue(
                code="invalid_json",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be valid JSON: {decode_error}.",
            )
        ]

    if expected_type == "json_object" and not isinstance(parsed, dict):
        return [
            TagValidationIssue(
                code="invalid_json_type",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be a JSON object.",
            )
        ]
    if expected_type == "json_array" and not isinstance(parsed, list):
        return [
            TagValidationIssue(
                code="invalid_json_type",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be a JSON array.",
            )
        ]

    if not isinstance(tag_schema, dict):
        return []

    issues: list[TagValidationIssue] = []
    errors = sorted(
        Draft202012Validator(tag_schema).iter_errors(parsed),
        key=lambda error: list(error.absolute_path),
    )
    for validation_error in errors:
        path = (
            "/".join(str(part) for part in validation_error.absolute_path)
            or "<root>"
        )
        issues.append(
            TagValidationIssue(
                code="schema_violation",
                tag_name=tag_name,
                message=(
                    f"Tag {tag_name} failed schema at {path}: "
                    f"{validation_error.message}."
                ),
            )
        )
    return issues


def validate_tag_value(
    tag_name: str,
    value: Any,
    definition: dict[str, Any],
) -> list[TagValidationIssue]:
    """Validate one slide/deck tag value against its native tag definition."""
    expected_type = definition.get("type")
    if expected_type in {"object", "array"}:
        if not isinstance(value, str):
            return [type_issue(tag_name, "JSON string", value)]
        return validate_structured_value(
            tag_name,
            value,
            f"json_{expected_type}",
            definition.get("schema"),
        )
    if expected_type == "string" and not isinstance(value, str):
        return [type_issue(tag_name, "string", value)]
    if expected_type == "integer":
        if not is_integer_string(value):
            return [type_issue(tag_name, "integer", value)]

    text = str(value)
    issues: list[TagValidationIssue] = []
    allowed = definition.get("enum")
    if isinstance(allowed, list) and text not in allowed:
        issues.append(enum_issue(tag_name, text, cast(list[str], allowed)))

    constraints = definition.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    minimum = definition.get("minimum", constraints.get("minimum"))
    if minimum is not None and int(text) < int(minimum):
        issues.append(
            TagValidationIssue(
                code="below_minimum",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be >= {minimum}.",
            )
        )

    max_length = definition.get("max_length", constraints.get("max_length"))
    if max_length is not None and len(text) > int(max_length):
        issues.append(
            TagValidationIssue(
                code="exceeds_max_length",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be at most {max_length} characters.",
            )
        )

    min_length = definition.get("min_length", constraints.get("min_length"))
    if min_length is not None and len(text) < int(min_length):
        issues.append(
            TagValidationIssue(
                code="below_min_length",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be at least {min_length} characters.",
            )
        )

    pattern = definition.get("pattern", constraints.get("pattern"))
    if isinstance(pattern, str) and re.fullmatch(pattern, text) is None:
        issues.append(
            TagValidationIssue(
                code="pattern_mismatch",
                tag_name=tag_name,
                message=f"Tag {tag_name} does not match required pattern.",
            )
        )
    return issues


def enum_issue(tag_name: str, value: str, allowed: list[str]) -> TagValidationIssue:
    return TagValidationIssue(
        code="invalid_enum",
        tag_name=tag_name,
        message=f"Tag {tag_name} value {value!r} is not one of {allowed}.",
    )


def type_issue(tag_name: str, expected_type: str, value: object) -> TagValidationIssue:
    return TagValidationIssue(
        code="invalid_type",
        tag_name=tag_name,
        message=f"Tag {tag_name} must be {expected_type}; got {type(value).__name__}.",
    )


def is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def is_integer_string(value: object) -> bool:
    if isinstance(value, int):
        return True
    if not isinstance(value, str):
        return False
    text = value.removeprefix("-")
    return bool(text) and text.isascii() and text.isdecimal()

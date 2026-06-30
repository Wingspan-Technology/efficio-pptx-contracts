"""Tag contract loading and validation for Python consumers.

The generated JSON resources remain the source data. This module is a thin SDK
layer used by runtime/import tooling so contract rules are not duplicated in
application packages.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from ._resources import load_json
from .errors import UnknownComponentTypeError
from .registry import assert_component_type


@dataclass(frozen=True)
class TagValidationIssue:
    code: str
    message: str
    tag_name: str | None = None


def load_component_tag_schema(component_type: str) -> dict:
    """Load the generated compatibility tag schema for one component type."""
    assert_component_type(component_type)
    file_name = f"{component_type.replace('_', '-')}.json"
    return load_json("schemas", "components", file_name)


def load_slide_tag_contract() -> dict:
    """Load the generated slide tag contract."""
    return load_json("schemas", "presentation", "slide-tags.json")


def validate_component_tags(component_type: str, tags: dict[str, str]) -> list[TagValidationIssue]:
    """Validate component tags against the generated component tag schema."""
    try:
        schema = load_component_tag_schema(component_type)
    except UnknownComponentTypeError:
        return [
            TagValidationIssue(
                code="unknown_component_type",
                tag_name="efficio_component_type",
                message=f"Unknown component type {component_type!r}.",
            )
        ]

    issues: list[TagValidationIssue] = []
    for tag_name in schema.get("required_tags", []):
        if _is_missing(tags.get(tag_name)):
            issues.append(
                TagValidationIssue(
                    code="missing_required_tag",
                    tag_name=tag_name,
                    message=f"Missing required tag {tag_name}.",
                )
            )

    enums = schema.get("enums", {})
    types = schema.get("types", {})
    json_schemas = schema.get("json_schemas", {})
    for tag_name, expected_type in types.items():
        value = tags.get(tag_name)
        if _is_missing(value):
            continue
        issues.extend(
            _validate_component_value(tag_name, value, expected_type, enums, json_schemas)
        )
    return issues


def validate_slide_tags(tags: dict[str, str]) -> list[TagValidationIssue]:
    """Validate slide tags against the generated slide tag contract."""
    contract = load_slide_tag_contract()
    issues: list[TagValidationIssue] = []
    for tag_name, definition in contract.get("tags", {}).items():
        if not isinstance(definition, dict):
            continue
        value = tags.get(tag_name)
        if definition.get("required") is True and _is_missing(value):
            issues.append(
                TagValidationIssue(
                    code="missing_required_tag",
                    tag_name=tag_name,
                    message=f"Missing required slide tag {tag_name}.",
                )
            )
            continue
        if _is_missing(value):
            continue
        issues.extend(_validate_slide_value(tag_name, value, definition))
    return issues


def _validate_component_value(
    tag_name: str,
    value: Any,
    expected_type: Any,
    enums: dict[str, list[str]],
    json_schemas: dict[str, dict],
) -> list[TagValidationIssue]:
    if not isinstance(value, str):
        return [_type_issue(tag_name, "string", value)]

    if expected_type in {"json_object", "json_array"}:
        return _validate_structured_value(
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
    if expected_type == "positive_integer_string":
        if not value.isdecimal() or int(value) < 1:
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
            issues.append(_enum_issue(tag_name, value, allowed))
    return issues


def _validate_structured_value(
    tag_name: str,
    value: str,
    expected_type: str,
    tag_schema: Any,
) -> list[TagValidationIssue]:
    """Validate an object/array tag stored as JSON text against its JSON Schema."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        return [
            TagValidationIssue(
                code="invalid_json",
                tag_name=tag_name,
                message=f"Tag {tag_name} must be valid JSON: {error}.",
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
    for error in errors:
        path = "/".join(str(part) for part in error.absolute_path) or "<root>"
        issues.append(
            TagValidationIssue(
                code="schema_violation",
                tag_name=tag_name,
                message=f"Tag {tag_name} failed schema at {path}: {error.message}.",
            )
        )
    return issues


def _validate_slide_value(
    tag_name: str,
    value: Any,
    definition: dict[str, Any],
) -> list[TagValidationIssue]:
    expected_type = definition.get("type")
    if expected_type == "string" and not isinstance(value, str):
        return [_type_issue(tag_name, "string", value)]
    if expected_type == "integer":
        if not _is_integer_string(value):
            return [_type_issue(tag_name, "integer", value)]

    text = str(value)
    issues: list[TagValidationIssue] = []
    allowed = definition.get("enum")
    if isinstance(allowed, list) and text not in allowed:
        issues.append(_enum_issue(tag_name, text, allowed))

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


def _enum_issue(tag_name: str, value: str, allowed: list[str]) -> TagValidationIssue:
    return TagValidationIssue(
        code="invalid_enum",
        tag_name=tag_name,
        message=f"Tag {tag_name} value {value!r} is not one of {allowed}.",
    )


def _type_issue(tag_name: str, expected_type: str, value: Any) -> TagValidationIssue:
    return TagValidationIssue(
        code="invalid_type",
        tag_name=tag_name,
        message=f"Tag {tag_name} must be {expected_type}; got {type(value).__name__}.",
    )


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_integer_string(value: Any) -> bool:
    if isinstance(value, int):
        return True
    if not isinstance(value, str):
        return False
    text = value.removeprefix("-")
    return bool(text) and text.isdecimal()

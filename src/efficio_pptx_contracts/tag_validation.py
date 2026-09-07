"""Tag contract loading and validation for Python consumers.

The generated JSON resources remain the source data. This module is a thin SDK
layer used by runtime/import tooling so contract rules are not duplicated in
application packages.

It owns component tag validation and stays the single public import path for the
whole validation surface: the generic stored-value rules live in
:mod:`._stored_tag_validation` and the deck/slide contract loading and
presentation-level rules in :mod:`._presentation_tag_validation`, both re-exported
here unchanged.
"""

from __future__ import annotations

from typing import Any

from ._category_chart_validation import category_chart_issues
from .classification_schemes import (
    CLASSIFICATION_SCHEME_ID_TAG,
    resolve_categorical_fill_scheme,
)
from ._presentation_tag_validation import (
    load_deck_tag_contract,
    load_slide_tag_contract,
    validate_deck_tags,
    validate_slide_tags,
)
from ._resources import load_json
from ._stored_tag_validation import (
    TagValidationIssue,
    is_missing,
    validate_component_value,
)
from ._table_config_validation import table_config_issues
from ._text_sizing_validation import text_sizing_issues
from .errors import UnknownComponentTypeError
from .registry import assert_component_type

__all__ = [
    "TagValidationIssue",
    "load_component_tag_schema",
    "load_deck_tag_contract",
    "load_slide_tag_contract",
    "validate_component_tags",
    "validate_deck_tags",
    "validate_slide_tags",
]


def load_component_tag_schema(component_type: str) -> dict[str, Any]:
    """Load the generated compatibility tag schema for one component type."""
    assert_component_type(component_type)
    file_name = f"{component_type.replace('_', '-')}.json"
    return load_json("schemas", "components", file_name)


def validate_component_tags(
    component_type: str,
    tags: dict[str, str],
    *,
    deck_tags: dict[str, str] | None = None,
) -> list[TagValidationIssue]:
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
        if is_missing(tags.get(tag_name)):
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
        if is_missing(value):
            continue
        issues.extend(
            validate_component_value(tag_name, value, expected_type, enums, json_schemas)
        )

    issues.extend(_component_semantic_issues(component_type, tags, issues))
    if component_type == "categorical_fill" and deck_tags is not None:
        prior_tags = {
            issue.tag_name for issue in issues if issue.tag_name is not None
        }
        if CLASSIFICATION_SCHEME_ID_TAG not in prior_tags:
            try:
                resolve_categorical_fill_scheme(tags, deck_tags)
            except ValueError:
                issues.append(
                    TagValidationIssue(
                        code="invalid_classification_scheme_reference",
                        tag_name=CLASSIFICATION_SCHEME_ID_TAG,
                        message=(
                            "The categorical-fill component must reference one "
                            "valid presentation classification scheme."
                        ),
                    )
                )
    return issues


def _component_semantic_issues(
    component_type: str,
    tags: dict[str, str],
    prior_issues: list[TagValidationIssue],
) -> list[TagValidationIssue]:
    """Wrap a component's flat cross-field checks (the relationships JSON Schema
    cannot express) as :class:`TagValidationIssue`, attached to the exact tag. Tags
    that already carry a structural issue are skipped, so a malformed value is
    reported once (structurally) with no noisy follow-on."""
    prior_tags = {issue.tag_name for issue in prior_issues if issue.tag_name is not None}
    if component_type == "text":
        raw_issues = text_sizing_issues(tags, prior_tags)
    elif component_type == "table":
        raw_issues = table_config_issues(tags, prior_tags)
    elif component_type == "category_chart":
        raw_issues = category_chart_issues(tags, prior_tags)
    else:
        return []
    return [
        TagValidationIssue(code=code, tag_name=tag_name, message=message)
        for code, tag_name, message in raw_issues
    ]

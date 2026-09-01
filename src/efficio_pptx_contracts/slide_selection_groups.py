"""Public parsing and validation API for deck-level slide-selection groups."""

from __future__ import annotations

import json
from typing import Any, cast

from jsonschema import Draft202012Validator

from ._slide_selection_group_graph import (
    normalize_slide_selection_groups,
    validate_slide_selection_group_selection,
)
from ._slide_selection_group_models import (
    SLIDE_SELECTION_GROUPS_TAG,
    SlideSelectionGroup,
    SlideSelectionGroupContractError,
    SlideSelectionGroupIssue,
    SlideSelectionGroupIssueCode,
    SlideSelectionGroupRegistry,
    SlideSelectionGroupType,
)
from .tag_validation import load_deck_tag_contract

__all__ = [
    "SLIDE_SELECTION_GROUPS_TAG",
    "SlideSelectionGroup",
    "SlideSelectionGroupContractError",
    "SlideSelectionGroupIssue",
    "SlideSelectionGroupIssueCode",
    "SlideSelectionGroupRegistry",
    "SlideSelectionGroupType",
    "normalize_slide_selection_groups",
    "parse_slide_selection_groups",
    "validate_slide_selection_group_selection",
]


def parse_slide_selection_groups(
    raw_value: str | list[Any] | None,
) -> tuple[SlideSelectionGroup, ...]:
    """Parse a PowerPoint tag string or an already-decoded artifact value."""
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return ()

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as error:
            raise SlideSelectionGroupContractError(
                [
                    SlideSelectionGroupIssue(
                        code=SlideSelectionGroupIssueCode.INVALID_JSON,
                        message="The slide-selection group tag must contain valid JSON.",
                    )
                ]
            ) from error
    else:
        parsed = raw_value

    schema = _load_selection_group_schema()
    errors = sorted(
        Draft202012Validator(schema).iter_errors(parsed),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise SlideSelectionGroupContractError(
            [
                SlideSelectionGroupIssue(
                    code=SlideSelectionGroupIssueCode.INVALID_SHAPE,
                    message="The slide-selection group value does not match its contract.",
                    path=tuple(error.absolute_path),
                )
                for error in errors
            ]
        )

    records = cast(list[dict[str, Any]], parsed)
    return tuple(
        SlideSelectionGroup(
            group_id=record["group_id"],
            name=record["name"],
            group_type=SlideSelectionGroupType(record["type"]),
            members=tuple(record["members"]),
            inclusion_policy=record.get("inclusion_policy"),
            instruction=record.get("instruction"),
        )
        for record in records
    )


def _load_selection_group_schema() -> dict[str, Any]:
    contract = load_deck_tag_contract()
    definition = contract.get("tags", {}).get(SLIDE_SELECTION_GROUPS_TAG)
    if not isinstance(definition, dict) or not isinstance(definition.get("schema"), dict):
        raise SlideSelectionGroupContractError(
            [
                SlideSelectionGroupIssue(
                    code=SlideSelectionGroupIssueCode.MISSING_CONTRACT,
                    message="The slide-selection group contract is unavailable.",
                )
            ]
        )
    return cast(dict[str, Any], definition["schema"])

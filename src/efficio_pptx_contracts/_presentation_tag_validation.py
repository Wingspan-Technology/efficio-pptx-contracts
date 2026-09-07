"""Deck and slide tag contract loading and presentation-level validation.

Generic stored-value rules live in :mod:`._stored_tag_validation`; this module
adds the presentation semantics JSON Schema cannot express on its own — unique
classification-scheme and archetype IDs in the deck registry, and slide archetype
assignments resolved against that registry.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._resources import load_json
from ._stored_tag_validation import (
    TagValidationIssue,
    is_missing,
    validate_tag_value,
)
from .classification_schemes import (
    CLASSIFICATION_SCHEMES_TAG,
    parse_classification_schemes,
)
from .slide_archetypes import (
    SLIDE_ARCHETYPES_TAG,
    SLIDE_ARCHETYPE_IDS_TAG,
    parse_slide_archetype_ids,
    parse_slide_archetypes,
)


def load_slide_tag_contract() -> dict[str, Any]:
    """Load the generated slide tag contract."""
    return load_json("schemas", "presentation", "slide-tags.json")


def load_deck_tag_contract() -> dict[str, Any]:
    """Load the generated presentation/deck tag contract.

    Deck tags are presentation-level Efficio metadata stored on the PowerPoint
    presentation itself (not on slides or shapes)."""
    return load_json("schemas", "presentation", "deck-tags.json")


def validate_slide_tags(
    tags: dict[str, str],
    *,
    deck_tags: dict[str, str] | None = None,
) -> list[TagValidationIssue]:
    """Validate slide tags against the generated slide tag contract.

    ``deck_tags`` is optional and only needed by slides that carry an archetype
    assignment: an assignment can only be checked against the deck registry that
    defines the archetypes. Slides without the tag validate exactly as before.
    """
    issues = _validate_presentation_tags(load_slide_tag_contract(), tags, "slide")
    issues.extend(_slide_archetype_issues(tags, deck_tags, issues))
    return issues


def validate_deck_tags(tags: dict[str, str]) -> list[TagValidationIssue]:
    """Validate presentation/deck tags against the generated deck tag contract.

    Optional tags that are absent or blank are skipped; present values are checked
    against the contract's type, enum, and length/pattern constraints — the same
    generic rules as slide tags. ``efficio_template_instruction`` is optional and
    only length-bounded, so a template with no deck instruction validates cleanly.
    """
    issues = _validate_presentation_tags(load_deck_tag_contract(), tags, "deck")
    if not any(issue.tag_name == CLASSIFICATION_SCHEMES_TAG for issue in issues):
        try:
            parse_classification_schemes(tags.get(CLASSIFICATION_SCHEMES_TAG))
        except ValueError:
            issues.append(
                TagValidationIssue(
                    code="invalid_classification_schemes",
                    tag_name=CLASSIFICATION_SCHEMES_TAG,
                    message=(
                        "Classification schemes must have unique scheme and case IDs "
                        "and match the presentation contract."
                    ),
                )
            )
    if not any(issue.tag_name == SLIDE_ARCHETYPES_TAG for issue in issues):
        try:
            parse_slide_archetypes(tags.get(SLIDE_ARCHETYPES_TAG))
        except ValueError:
            issues.append(
                TagValidationIssue(
                    code="invalid_slide_archetypes",
                    tag_name=SLIDE_ARCHETYPES_TAG,
                    message=(
                        "Slide archetypes must have unique archetype IDs and match "
                        "the presentation contract."
                    ),
                )
            )
    return issues


def _slide_archetype_issues(
    tags: Mapping[str, str],
    deck_tags: Mapping[str, str] | None,
    prior_issues: list[TagValidationIssue],
) -> list[TagValidationIssue]:
    """Resolve a present slide archetype assignment against the deck registry.

    An absent assignment is a generic slide and needs no deck context. A tag that
    already failed structurally is skipped, so a malformed value is reported once.
    """
    raw_assignment = tags.get(SLIDE_ARCHETYPE_IDS_TAG)
    if raw_assignment is None:
        return []
    if any(issue.tag_name == SLIDE_ARCHETYPE_IDS_TAG for issue in prior_issues):
        return []

    try:
        assigned_ids = parse_slide_archetype_ids(raw_assignment)
    except ValueError:
        return [
            TagValidationIssue(
                code="invalid_slide_archetype_assignment",
                tag_name=SLIDE_ARCHETYPE_IDS_TAG,
                message=(
                    f"Tag {SLIDE_ARCHETYPE_IDS_TAG} must be a non-empty JSON array "
                    "of unique archetype IDs."
                ),
            )
        ]

    if deck_tags is None:
        return [
            TagValidationIssue(
                code="missing_slide_archetype_context",
                tag_name=SLIDE_ARCHETYPE_IDS_TAG,
                message=(
                    "Validating a slide archetype assignment requires the deck tags "
                    f"that define {SLIDE_ARCHETYPES_TAG}."
                ),
            )
        ]

    try:
        registry = parse_slide_archetypes(deck_tags.get(SLIDE_ARCHETYPES_TAG))
    except ValueError:
        return [
            TagValidationIssue(
                code="invalid_slide_archetype_context",
                tag_name=SLIDE_ARCHETYPE_IDS_TAG,
                message=(
                    f"The deck {SLIDE_ARCHETYPES_TAG} registry is invalid, so this "
                    "slide archetype assignment cannot be resolved."
                ),
            )
        ]

    known = {archetype.archetype_id for archetype in registry}
    unknown = [archetype_id for archetype_id in assigned_ids if archetype_id not in known]
    if unknown:
        return [
            TagValidationIssue(
                code="unknown_slide_archetype_reference",
                tag_name=SLIDE_ARCHETYPE_IDS_TAG,
                message=(
                    "The slide references archetype IDs that the deck registry does "
                    f"not define: {sorted(set(unknown))}."
                ),
            )
        ]
    return []


def _validate_presentation_tags(
    contract: dict[str, Any], tags: dict[str, str], kind: str
) -> list[TagValidationIssue]:
    """Validate ``tags`` against a slide/deck tag contract (shared generic rules)."""
    issues: list[TagValidationIssue] = []
    for tag_name, definition in contract.get("tags", {}).items():
        if not isinstance(definition, dict):
            continue
        value = tags.get(tag_name)
        if definition.get("required") is True and is_missing(value):
            issues.append(
                TagValidationIssue(
                    code="missing_required_tag",
                    tag_name=tag_name,
                    message=f"Missing required {kind} tag {tag_name}.",
                )
            )
            continue
        if is_missing(value):
            continue
        issues.extend(validate_tag_value(tag_name, value, definition))
    return issues

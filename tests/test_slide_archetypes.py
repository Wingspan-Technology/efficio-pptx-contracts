"""Slide archetype parsing, resolution, applicability, and validation coverage.

The case tables come from tests/fixtures/slide-archetype-cases.json, shared with
tests/slideArchetypes.test.ts so both SDKs are proven to agree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import efficio_pptx_contracts as sdk
from efficio_pptx_contracts import (
    SLIDE_ARCHETYPES_TAG,
    SLIDE_ARCHETYPE_IDS_TAG,
    SlideArchetype,
    SlideArchetypeContractError,
    is_slide_applicable_to_archetype,
    parse_slide_archetype_ids,
    parse_slide_archetypes,
    resolve_slide_archetype_assignment,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "slide-archetype-cases.json").read_text(
        encoding="utf-8"
    )
)


def _cases(key: str) -> list[Any]:
    return list(FIXTURE[key])


def _ids(key: str) -> list[str]:
    return [str(case["name"]) for case in FIXTURE[key]]


def _wire(archetype: SlideArchetype) -> dict[str, str]:
    """Project a parsed archetype back to the shared fixture's wire shape."""
    record = {"archetype_id": archetype.archetype_id, "name": archetype.name}
    if archetype.description is not None:
        record["description"] = archetype.description
    return record


def test_tag_constants_match_the_generated_contracts() -> None:
    assert SLIDE_ARCHETYPES_TAG == "efficio_slide_archetypes"
    assert SLIDE_ARCHETYPE_IDS_TAG == "efficio_slide_archetype_ids"
    contract = sdk.load_deck_tag_contract()["tags"][SLIDE_ARCHETYPES_TAG]
    assert contract["type"] == "array"
    assert contract["required"] is False
    assert "ai" not in contract
    assignment = sdk.load_slide_tag_contract()["tags"][SLIDE_ARCHETYPE_IDS_TAG]
    assert assignment["required"] is False
    assert assignment["schema"]["minItems"] == 1
    assert assignment["schema"]["uniqueItems"] is True
    assert "ai" not in assignment


@pytest.mark.parametrize("case", _cases("registry_cases"), ids=_ids("registry_cases"))
def test_parse_slide_archetypes_accepts_valid_registries(case: dict[str, Any]) -> None:
    parsed = parse_slide_archetypes(case["raw"])
    assert [_wire(archetype) for archetype in parsed] == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("invalid_registry_cases"), ids=_ids("invalid_registry_cases")
)
def test_parse_slide_archetypes_rejects_invalid_registries(case: dict[str, Any]) -> None:
    with pytest.raises(SlideArchetypeContractError):
        parse_slide_archetypes(case["raw"])


@pytest.mark.parametrize("case", _cases("assignment_cases"), ids=_ids("assignment_cases"))
def test_parse_slide_archetype_ids_accepts_valid_assignments(case: dict[str, Any]) -> None:
    assert list(parse_slide_archetype_ids(case["raw"])) == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("invalid_assignment_cases"), ids=_ids("invalid_assignment_cases")
)
def test_parse_slide_archetype_ids_rejects_invalid_assignments(case: dict[str, Any]) -> None:
    with pytest.raises(SlideArchetypeContractError):
        parse_slide_archetype_ids(case["raw"])


@pytest.mark.parametrize("case", _cases("resolution_cases"), ids=_ids("resolution_cases"))
def test_resolve_slide_archetype_assignment(case: dict[str, Any]) -> None:
    resolved = resolve_slide_archetype_assignment(case["slide_tags"], case["deck_tags"])
    assert [_wire(archetype) for archetype in resolved] == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("resolution_error_cases"), ids=_ids("resolution_error_cases")
)
def test_resolve_slide_archetype_assignment_rejects(case: dict[str, Any]) -> None:
    with pytest.raises(SlideArchetypeContractError):
        resolve_slide_archetype_assignment(case["slide_tags"], case["deck_tags"])


@pytest.mark.parametrize(
    "case", _cases("applicability_cases"), ids=_ids("applicability_cases")
)
def test_is_slide_applicable_to_archetype(case: dict[str, Any]) -> None:
    assert (
        is_slide_applicable_to_archetype(
            case["slide_tags"], case["deck_tags"], case["archetype_id"]
        )
        is case["expected"]
    )


@pytest.mark.parametrize(
    "case", _cases("applicability_error_cases"), ids=_ids("applicability_error_cases")
)
def test_is_slide_applicable_to_archetype_rejects(case: dict[str, Any]) -> None:
    with pytest.raises(SlideArchetypeContractError):
        is_slide_applicable_to_archetype(
            case["slide_tags"], case["deck_tags"], case["archetype_id"]
        )


def test_slide_archetype_contract_error_is_a_value_error() -> None:
    assert issubclass(SlideArchetypeContractError, ValueError)


REGISTRY = json.dumps(
    [
        {"archetype_id": "pitch_deck", "name": "Pitch deck"},
        {"archetype_id": "training", "name": "Training"},
    ]
)


def valid_slide_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_slide_id": "slide_001",
        "efficio_slide_role": "content",
        "efficio_slide_placement": "body",
        "efficio_slide_inclusion_policy": "when_relevant",
    }
    tags.update(overrides)
    return tags


def _codes(issues: list[sdk.TagValidationIssue]) -> list[tuple[str, str | None]]:
    return [(issue.code, issue.tag_name) for issue in issues]


def test_validate_slide_tags_without_an_assignment_needs_no_deck_context() -> None:
    assert sdk.validate_slide_tags(valid_slide_tags()) == []
    assert sdk.validate_slide_tags(valid_slide_tags(), deck_tags={}) == []
    assert (
        sdk.validate_slide_tags(
            valid_slide_tags(), deck_tags={SLIDE_ARCHETYPES_TAG: REGISTRY}
        )
        == []
    )


def test_validate_slide_tags_accepts_a_known_assignment() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids='["pitch_deck","training"]')
    assert sdk.validate_slide_tags(tags, deck_tags={SLIDE_ARCHETYPES_TAG: REGISTRY}) == []


def test_validate_slide_tags_requires_deck_context_for_an_assignment() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids='["pitch_deck"]')
    assert _codes(sdk.validate_slide_tags(tags)) == [
        ("missing_slide_archetype_context", SLIDE_ARCHETYPE_IDS_TAG)
    ]


def test_validate_slide_tags_reports_a_blank_assignment() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids="   ")
    assert _codes(sdk.validate_slide_tags(tags, deck_tags={})) == [
        ("invalid_slide_archetype_assignment", SLIDE_ARCHETYPE_IDS_TAG)
    ]
    # Blank is invalid with or without deck context, and never a structural issue.
    assert _codes(sdk.validate_slide_tags(tags)) == [
        ("invalid_slide_archetype_assignment", SLIDE_ARCHETYPE_IDS_TAG)
    ]


def test_validate_slide_tags_reports_invalid_deck_context() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids='["pitch_deck"]')
    deck_tags = {SLIDE_ARCHETYPES_TAG: '[{"archetype_id":"Pitch","name":"A"}]'}
    assert _codes(sdk.validate_slide_tags(tags, deck_tags=deck_tags)) == [
        ("invalid_slide_archetype_context", SLIDE_ARCHETYPE_IDS_TAG)
    ]


def test_validate_slide_tags_reports_unknown_references() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids='["board_update"]')
    assert _codes(sdk.validate_slide_tags(tags, deck_tags={SLIDE_ARCHETYPES_TAG: REGISTRY})) == [
        ("unknown_slide_archetype_reference", SLIDE_ARCHETYPE_IDS_TAG)
    ]
    # An assignment with no definitions to reference is an unknown reference too.
    assert _codes(sdk.validate_slide_tags(tags, deck_tags={})) == [
        ("unknown_slide_archetype_reference", SLIDE_ARCHETYPE_IDS_TAG)
    ]


@pytest.mark.parametrize(
    ("stored", "expected_code"),
    [
        ('["pitch_deck"', "invalid_json"),
        ('{"a":1}', "invalid_json_type"),
        ("[]", "schema_violation"),
        ('["pitch_deck","pitch_deck"]', "schema_violation"),
        ('["Pitch_deck"]', "schema_violation"),
        ("[1]", "schema_violation"),
    ],
)
def test_structural_assignment_errors_suppress_semantic_duplicates(
    stored: str, expected_code: str
) -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids=stored)
    codes = _codes(sdk.validate_slide_tags(tags, deck_tags={SLIDE_ARCHETYPES_TAG: REGISTRY}))
    assert (expected_code, SLIDE_ARCHETYPE_IDS_TAG) in codes
    assert all(not code.startswith("unknown_slide_archetype") for code, _tag in codes)
    assert all(not code.endswith("_archetype_context") for code, _tag in codes)


def valid_deck_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_template_id": "acme_quarterly",
        "efficio_template_contract_revision": "3",
    }
    tags.update(overrides)
    return tags


def test_validate_deck_tags_accepts_missing_blank_and_empty_registries() -> None:
    assert sdk.validate_deck_tags(valid_deck_tags()) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_slide_archetypes="   ")) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_slide_archetypes="[]")) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_slide_archetypes=REGISTRY)) == []


def test_validate_deck_tags_rejects_duplicate_archetype_ids() -> None:
    duplicated = json.dumps(
        [
            {"archetype_id": "pitch_deck", "name": "One"},
            {"archetype_id": "pitch_deck", "name": "Two", "description": "Other."},
        ]
    )
    assert _codes(sdk.validate_deck_tags(valid_deck_tags(efficio_slide_archetypes=duplicated))) == [
        ("invalid_slide_archetypes", SLIDE_ARCHETYPES_TAG)
    ]


def test_validate_deck_tags_reports_structural_registry_errors_once() -> None:
    codes = _codes(
        sdk.validate_deck_tags(
            valid_deck_tags(efficio_slide_archetypes='[{"archetype_id":"Pitch","name":"A"}]')
        )
    )
    assert ("schema_violation", SLIDE_ARCHETYPES_TAG) in codes
    assert ("invalid_slide_archetypes", SLIDE_ARCHETYPES_TAG) not in codes


def test_archetype_metadata_does_not_alter_other_slide_semantics() -> None:
    """Archetypes are applicability metadata only.

    Adding a registry and an assignment must not change role, placement,
    ordering, inclusion-policy validation, or the deck-level AI projection.
    """
    plain = valid_slide_tags(efficio_slide_placement="fixed_start", efficio_slide_group_order="1")
    tagged = dict(plain, efficio_slide_archetype_ids='["pitch_deck"]')
    deck_tags = {SLIDE_ARCHETYPES_TAG: REGISTRY}

    assert sdk.validate_slide_tags(plain, deck_tags=deck_tags) == []
    assert sdk.validate_slide_tags(tagged, deck_tags=deck_tags) == []

    broken_plain = sdk.validate_slide_tags(
        valid_slide_tags(efficio_slide_placement="unknown"), deck_tags=deck_tags
    )
    broken_tagged = sdk.validate_slide_tags(
        valid_slide_tags(
            efficio_slide_placement="unknown",
            efficio_slide_archetype_ids='["pitch_deck"]',
        ),
        deck_tags=deck_tags,
    )
    assert _codes(broken_plain) == _codes(broken_tagged)


def test_archetype_registry_does_not_alter_selection_groups_or_deck_context() -> None:
    groups = [
        {
            "group_id": "group_intro",
            "name": "Intro",
            "type": "choice",
            "inclusion_policy": "when_relevant",
            "members": ["slide_001", "slide_002"],
        }
    ]
    policies = {"slide_001": "when_relevant", "slide_002": "when_relevant"}
    registry = sdk.normalize_slide_selection_groups(
        sdk.parse_slide_selection_groups(groups), slide_inclusion_policies=policies
    )
    assert sdk.validate_slide_selection_group_selection(registry, ["slide_001"]) == ()

    deck_tags = valid_deck_tags(
        efficio_slide_archetypes=REGISTRY,
        efficio_slide_selection_groups=json.dumps(groups),
    )
    assert sdk.validate_deck_tags(deck_tags) == []
    # The registry is not AI-facing, so it never reaches the deck context.
    assert sdk.project_deck_context(deck_tags) == {}


def test_slide_selection_instruction_never_mentions_archetypes() -> None:
    instruction = sdk.load_slide_selection_instruction()
    assert SLIDE_ARCHETYPE_IDS_TAG not in instruction["slide_tag_instructions"]
    assert "archetype" not in json.dumps(instruction)


# A trailing line feed passes JSON Schema `pattern` (a search) and Python's `$`,
# so these guard the strict full-string identifier check in both validators.
NEWLINE_REGISTRY = json.dumps([{"archetype_id": "pitch_deck\n", "name": "Pitch deck"}])


def test_validate_deck_tags_rejects_a_newline_suffixed_registry_id() -> None:
    issues = sdk.validate_deck_tags(
        valid_deck_tags(efficio_slide_archetypes=NEWLINE_REGISTRY)
    )
    assert _codes(issues) == [("invalid_slide_archetypes", SLIDE_ARCHETYPES_TAG)]


def test_validate_slide_tags_rejects_a_newline_suffixed_assignment_once() -> None:
    tags = valid_slide_tags(efficio_slide_archetype_ids=json.dumps(["pitch_deck\n"]))
    issues = sdk.validate_slide_tags(tags, deck_tags={SLIDE_ARCHETYPES_TAG: REGISTRY})
    # Exactly one issue: no duplicate unknown-reference or context follow-on.
    assert _codes(issues) == [
        ("invalid_slide_archetype_assignment", SLIDE_ARCHETYPE_IDS_TAG)
    ]


@pytest.mark.parametrize(
    "deck_tags",
    [{SLIDE_ARCHETYPES_TAG: REGISTRY}, {SLIDE_ARCHETYPES_TAG: "[]"}, {}],
    ids=["populated registry", "empty registry", "missing registry"],
)
def test_applicability_rejects_a_newline_suffixed_requested_id(
    deck_tags: dict[str, str],
) -> None:
    with pytest.raises(SlideArchetypeContractError, match="not a valid archetype ID"):
        is_slide_applicable_to_archetype(
            {"efficio_slide_id": "slide_001"}, deck_tags, "pitch_deck\n"
        )


def test_strict_identifier_matching_keeps_every_valid_id_accepted() -> None:
    registry = json.dumps(
        [
            {"archetype_id": "a", "name": "Single letter"},
            {"archetype_id": "a1_b2_c3", "name": "Multi segment"},
            {"archetype_id": "pitch_deck", "name": "Pitch deck"},
        ]
    )
    deck_tags = {SLIDE_ARCHETYPES_TAG: registry}
    assert [item.archetype_id for item in parse_slide_archetypes(registry)] == [
        "a",
        "a1_b2_c3",
        "pitch_deck",
    ]
    for archetype_id in ("a", "a1_b2_c3", "pitch_deck"):
        assert is_slide_applicable_to_archetype({}, deck_tags, archetype_id) is True
        assert parse_slide_archetype_ids(json.dumps([archetype_id])) == (archetype_id,)

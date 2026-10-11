"""Data-topic parsing, resolution, and validation coverage.

The case tables come from tests/fixtures/data-topic-cases.json, shared with
tests/dataTopics.test.ts so both SDKs are proven to agree.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import efficio_pptx_contracts as sdk
from efficio_pptx_contracts import (
    DATA_TOPICS_TAG,
    SLIDE_DATA_TOPIC_IDS_TAG,
    DataTopic,
    DataTopicContractError,
    parse_data_topics,
    parse_slide_data_topic_ids,
    resolve_slide_data_topic_assignment,
)

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "data-topic-cases.json").read_text(
        encoding="utf-8"
    )
)


def _cases(key: str) -> list[Any]:
    return list(FIXTURE[key])


def _ids(key: str) -> list[str]:
    return [str(case["name"]) for case in FIXTURE[key]]


def _wire(topic: DataTopic) -> dict[str, str]:
    """Project a parsed topic back to the shared fixture's wire shape."""
    return {"topic_id": topic.topic_id, "name": topic.name}


def test_tag_constants_match_the_generated_contracts() -> None:
    assert DATA_TOPICS_TAG == "efficio_data_topics"
    assert SLIDE_DATA_TOPIC_IDS_TAG == "efficio_slide_data_topic_ids"
    registry = sdk.load_deck_tag_contract()["tags"][DATA_TOPICS_TAG]
    assert registry["type"] == "array"
    assert registry["required"] is False
    assert "ai" not in registry
    item = registry["schema"]["items"]
    assert item["required"] == ["topic_id", "name"]
    assert list(item["properties"]) == ["topic_id", "name"]
    assert item["additionalProperties"] is False
    assignment = sdk.load_slide_tag_contract()["tags"][SLIDE_DATA_TOPIC_IDS_TAG]
    assert assignment["required"] is False
    assert assignment["schema"]["minItems"] == 1
    assert assignment["schema"]["uniqueItems"] is True
    assert assignment["schema"]["items"]["pattern"] == item["properties"]["topic_id"]["pattern"]
    assert "ai" not in assignment


@pytest.mark.parametrize("case", _cases("registry_cases"), ids=_ids("registry_cases"))
def test_parse_data_topics_accepts_valid_registries(case: dict[str, Any]) -> None:
    parsed = parse_data_topics(case["raw"])
    assert [_wire(topic) for topic in parsed] == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("invalid_registry_cases"), ids=_ids("invalid_registry_cases")
)
def test_parse_data_topics_rejects_invalid_registries(case: dict[str, Any]) -> None:
    with pytest.raises(DataTopicContractError):
        parse_data_topics(case["raw"])


@pytest.mark.parametrize("case", _cases("assignment_cases"), ids=_ids("assignment_cases"))
def test_parse_slide_data_topic_ids_accepts_valid_assignments(case: dict[str, Any]) -> None:
    assert list(parse_slide_data_topic_ids(case["raw"])) == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("invalid_assignment_cases"), ids=_ids("invalid_assignment_cases")
)
def test_parse_slide_data_topic_ids_rejects_invalid_assignments(case: dict[str, Any]) -> None:
    with pytest.raises(DataTopicContractError):
        parse_slide_data_topic_ids(case["raw"])


@pytest.mark.parametrize("case", _cases("resolution_cases"), ids=_ids("resolution_cases"))
def test_resolve_slide_data_topic_assignment(case: dict[str, Any]) -> None:
    resolved = resolve_slide_data_topic_assignment(case["slide_tags"], case["deck_tags"])
    assert [_wire(topic) for topic in resolved] == case["expected"]


@pytest.mark.parametrize(
    "case", _cases("resolution_error_cases"), ids=_ids("resolution_error_cases")
)
def test_resolve_slide_data_topic_assignment_rejects(case: dict[str, Any]) -> None:
    with pytest.raises(DataTopicContractError):
        resolve_slide_data_topic_assignment(case["slide_tags"], case["deck_tags"])


def test_data_topic_contract_error_is_a_value_error() -> None:
    assert issubclass(DataTopicContractError, ValueError)


def test_data_topic_is_an_immutable_two_field_record() -> None:
    topic = DataTopic("topic_revenue", "Revenue")
    assert topic == DataTopic(topic_id="topic_revenue", name="Revenue")
    with pytest.raises(AttributeError):
        topic.name = "Sales"  # type: ignore[misc]


REGISTRY = json.dumps(
    [
        {"topic_id": "topic_revenue", "name": "Revenue"},
        {"topic_id": "topic_headcount", "name": "Headcount"},
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


def valid_deck_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_template_id": "acme_quarterly",
        "efficio_template_contract_revision": "5",
    }
    tags.update(overrides)
    return tags


def _codes(issues: list[sdk.TagValidationIssue]) -> list[tuple[str, str | None]]:
    return [(issue.code, issue.tag_name) for issue in issues]


def test_validate_slide_tags_without_an_assignment_needs_no_deck_context() -> None:
    assert sdk.validate_slide_tags(valid_slide_tags()) == []
    assert sdk.validate_slide_tags(valid_slide_tags(), deck_tags={}) == []
    assert (
        sdk.validate_slide_tags(valid_slide_tags(), deck_tags={DATA_TOPICS_TAG: REGISTRY})
        == []
    )


def test_validate_slide_tags_accepts_a_known_assignment() -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids='["topic_headcount","topic_revenue"]')
    assert sdk.validate_slide_tags(tags, deck_tags={DATA_TOPICS_TAG: REGISTRY}) == []


@pytest.mark.parametrize("stored", ["   ", ""], ids=["blank", "empty"])
def test_validate_slide_tags_reports_a_blank_assignment(stored: str) -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids=stored)
    expected = [("invalid_slide_data_topic_assignment", SLIDE_DATA_TOPIC_IDS_TAG)]
    assert _codes(sdk.validate_slide_tags(tags, deck_tags={DATA_TOPICS_TAG: REGISTRY})) == expected
    # Blank is invalid with or without deck context, and never a structural issue.
    assert _codes(sdk.validate_slide_tags(tags)) == expected


@pytest.mark.parametrize(
    "deck_tags",
    [{DATA_TOPICS_TAG: REGISTRY}, {DATA_TOPICS_TAG: "[]"}, {DATA_TOPICS_TAG: "  "}, {}],
    ids=["populated registry", "empty registry", "blank registry", "missing registry"],
)
def test_validate_slide_tags_reports_unknown_references(deck_tags: dict[str, str]) -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids='["topic_revenue","topic_margin"]')
    if deck_tags.get(DATA_TOPICS_TAG) == REGISTRY:
        unknown = "['topic_margin']"
    else:
        unknown = "['topic_revenue', 'topic_margin']"
    issues = sdk.validate_slide_tags(tags, deck_tags=deck_tags)
    assert _codes(issues) == [("unknown_data_topic_reference", SLIDE_DATA_TOPIC_IDS_TAG)]
    assert unknown in issues[0].message


def test_validate_slide_tags_cannot_resolve_an_assignment_without_deck_context() -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids='["topic_revenue"]')
    issues = sdk.validate_slide_tags(tags)
    assert _codes(issues) == [("unknown_data_topic_reference", SLIDE_DATA_TOPIC_IDS_TAG)]
    assert DATA_TOPICS_TAG in issues[0].message


def test_validate_slide_tags_cannot_resolve_against_an_invalid_registry() -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids='["topic_revenue"]')
    deck_tags = {DATA_TOPICS_TAG: '[{"topic_id":"topic_Revenue","name":"Revenue"}]'}
    issues = sdk.validate_slide_tags(tags, deck_tags=deck_tags)
    assert _codes(issues) == [("unknown_data_topic_reference", SLIDE_DATA_TOPIC_IDS_TAG)]
    assert "registry is invalid" in issues[0].message


@pytest.mark.parametrize(
    ("stored", "expected_code"),
    [
        ('["topic_revenue"', "invalid_json"),
        ('{"a":1}', "invalid_json_type"),
        ("[]", "schema_violation"),
        ('["topic_revenue","topic_revenue"]', "schema_violation"),
        ('["topic_Revenue"]', "schema_violation"),
        ('["revenue"]', "schema_violation"),
        ("[1]", "schema_violation"),
    ],
)
def test_structural_assignment_errors_suppress_semantic_duplicates(
    stored: str, expected_code: str
) -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids=stored)
    codes = _codes(sdk.validate_slide_tags(tags, deck_tags={DATA_TOPICS_TAG: REGISTRY}))
    assert (expected_code, SLIDE_DATA_TOPIC_IDS_TAG) in codes
    assert all(tag == SLIDE_DATA_TOPIC_IDS_TAG for _code, tag in codes)
    assert all("data_topic" not in code for code, _tag in codes)


def test_validate_deck_tags_accepts_missing_blank_and_empty_registries() -> None:
    assert sdk.validate_deck_tags(valid_deck_tags()) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics="   ")) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics="[]")) == []
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics=REGISTRY)) == []


def test_validate_deck_tags_accepts_duplicate_names() -> None:
    registry = json.dumps(
        [
            {"topic_id": "topic_revenue_eu", "name": "Revenue"},
            {"topic_id": "topic_revenue_us", "name": "Revenue"},
        ]
    )
    assert sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics=registry)) == []


def test_validate_deck_tags_rejects_duplicate_topic_ids() -> None:
    duplicated = json.dumps(
        [
            {"topic_id": "topic_revenue", "name": "Revenue"},
            {"topic_id": "topic_revenue", "name": "Sales"},
        ]
    )
    assert _codes(sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics=duplicated))) == [
        ("invalid_data_topics", DATA_TOPICS_TAG)
    ]


@pytest.mark.parametrize(
    ("stored", "expected_code"),
    [
        ('[{"topic_id":', "invalid_json"),
        ('{"topic_id":"topic_revenue","name":"Revenue"}', "invalid_json_type"),
        ('[{"topic_id":"topic_Revenue","name":"Revenue"}]', "schema_violation"),
        ('[{"topic_id":"topic_revenue","name":"   "}]', "schema_violation"),
        ('[{"topic_id":"topic_revenue","name":"Revenue","source":"crm"}]', "schema_violation"),
    ],
)
def test_validate_deck_tags_reports_structural_registry_errors_once(
    stored: str, expected_code: str
) -> None:
    codes = _codes(sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics=stored)))
    assert (expected_code, DATA_TOPICS_TAG) in codes
    assert ("invalid_data_topics", DATA_TOPICS_TAG) not in codes


# A trailing line feed passes JSON Schema `pattern` (a search) and Python's `$`,
# so these guard the strict full-string identifier check in both validators.
def test_validate_deck_tags_rejects_a_newline_suffixed_topic_id() -> None:
    registry = json.dumps([{"topic_id": "topic_revenue\n", "name": "Revenue"}])
    issues = sdk.validate_deck_tags(valid_deck_tags(efficio_data_topics=registry))
    assert _codes(issues) == [("invalid_data_topics", DATA_TOPICS_TAG)]


def test_validate_slide_tags_rejects_a_newline_suffixed_assignment_once() -> None:
    tags = valid_slide_tags(efficio_slide_data_topic_ids=json.dumps(["topic_revenue\n"]))
    issues = sdk.validate_slide_tags(tags, deck_tags={DATA_TOPICS_TAG: REGISTRY})
    # Exactly one issue: no duplicate unknown-reference follow-on.
    assert _codes(issues) == [
        ("invalid_slide_data_topic_assignment", SLIDE_DATA_TOPIC_IDS_TAG)
    ]


def test_data_topic_and_archetype_assignments_validate_independently() -> None:
    deck_tags = {
        DATA_TOPICS_TAG: REGISTRY,
        sdk.SLIDE_ARCHETYPES_TAG: json.dumps([{"archetype_id": "pitch_deck", "name": "Pitch"}]),
    }
    both = valid_slide_tags(
        efficio_slide_archetype_ids='["pitch_deck"]',
        efficio_slide_data_topic_ids='["topic_revenue"]',
    )
    assert sdk.validate_slide_tags(both, deck_tags=deck_tags) == []
    broken_topics = dict(both, efficio_slide_data_topic_ids='["topic_margin"]')
    assert _codes(sdk.validate_slide_tags(broken_topics, deck_tags=deck_tags)) == [
        ("unknown_data_topic_reference", SLIDE_DATA_TOPIC_IDS_TAG)
    ]
    # An archetype ID is not a data topic ID, even when the deck defines it.
    crossed = dict(both, efficio_slide_data_topic_ids='["pitch_deck"]')
    assert _codes(sdk.validate_slide_tags(crossed, deck_tags=deck_tags)) == [
        ("schema_violation", SLIDE_DATA_TOPIC_IDS_TAG)
    ]


def test_data_topics_do_not_alter_other_slide_semantics() -> None:
    """Data topics are advisory metadata only.

    Adding a registry and an assignment must not change role, placement,
    ordering, or inclusion-policy validation.
    """
    deck_tags = {DATA_TOPICS_TAG: REGISTRY}
    plain = valid_slide_tags(efficio_slide_placement="fixed_start", efficio_slide_group_order="1")
    tagged = dict(plain, efficio_slide_data_topic_ids='["topic_revenue"]')
    assert sdk.validate_slide_tags(plain, deck_tags=deck_tags) == []
    assert sdk.validate_slide_tags(tagged, deck_tags=deck_tags) == []

    broken_plain = sdk.validate_slide_tags(
        valid_slide_tags(efficio_slide_placement="unknown"), deck_tags=deck_tags
    )
    broken_tagged = sdk.validate_slide_tags(
        valid_slide_tags(
            efficio_slide_placement="unknown",
            efficio_slide_data_topic_ids='["topic_revenue"]',
        ),
        deck_tags=deck_tags,
    )
    assert _codes(broken_plain) == _codes(broken_tagged)


def test_data_topics_never_reach_ai_context_or_slide_selection() -> None:
    deck_tags = valid_deck_tags(efficio_data_topics=REGISTRY)
    assert sdk.validate_deck_tags(deck_tags) == []
    # The registry is not AI-facing, so it never reaches the deck context.
    assert sdk.project_deck_context(deck_tags) == {}
    instruction = sdk.load_slide_selection_instruction()
    assert SLIDE_DATA_TOPIC_IDS_TAG not in instruction["slide_tag_instructions"]
    serialized = json.dumps(instruction)
    assert "data_topic" not in serialized
    assert "topic_" not in serialized

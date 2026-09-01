"""Behavior tests for the public slide-selection group contract API."""

from __future__ import annotations

import json

import pytest

from efficio_pptx_contracts import (
    SlideSelectionGroup,
    SlideSelectionGroupContractError,
    SlideSelectionGroupIssueCode,
    SlideSelectionGroupType,
    normalize_slide_selection_groups,
    parse_slide_selection_groups,
    validate_slide_selection_group_selection,
)


def _policies(**overrides: str) -> dict[str, str]:
    values = {
        "slide_001": "when_relevant",
        "slide_002": "when_relevant",
        "slide_003": "when_relevant",
        "slide_004": "when_relevant",
    }
    values.update(overrides)
    return values


def _group(
    group_id: str,
    group_type: SlideSelectionGroupType,
    members: tuple[str, ...],
    *,
    inclusion_policy: str | None = None,
) -> SlideSelectionGroup:
    return SlideSelectionGroup(
        group_id=group_id,
        name=group_id,
        group_type=group_type,
        members=members,
        inclusion_policy=inclusion_policy,
    )


def _codes(error: SlideSelectionGroupContractError) -> set[SlideSelectionGroupIssueCode]:
    return {issue.code for issue in error.issues}


@pytest.mark.parametrize("value", [None, "", "  ", "[]", []])
def test_parse_empty_registry_values(value: str | list[object] | None) -> None:
    assert parse_slide_selection_groups(value) == ()


def test_parse_accepts_tag_json_and_decoded_artifact_list() -> None:
    value = [
        {
            "group_id": "group_options",
            "name": "Options",
            "type": "choice",
            "inclusion_policy": "when_relevant",
            "instruction": "Choose the most relevant option.",
            "members": ["slide_001", "slide_002"],
        }
    ]

    expected = (
        SlideSelectionGroup(
            group_id="group_options",
            name="Options",
            group_type=SlideSelectionGroupType.CHOICE,
            members=("slide_001", "slide_002"),
            inclusion_policy="when_relevant",
            instruction="Choose the most relevant option.",
        ),
    )
    assert parse_slide_selection_groups(value) == expected
    assert parse_slide_selection_groups(json.dumps(value)) == expected


def test_parse_reports_safe_typed_json_and_shape_errors() -> None:
    with pytest.raises(SlideSelectionGroupContractError) as invalid_json:
        parse_slide_selection_groups('[{"instruction":"private generated text"}')
    assert invalid_json.value.issues[0].code is SlideSelectionGroupIssueCode.INVALID_JSON
    assert "private generated text" not in str(invalid_json.value)
    assert "private generated text" not in invalid_json.value.issues[0].message

    with pytest.raises(SlideSelectionGroupContractError) as invalid_shape:
        parse_slide_selection_groups([{"group_id": "not_a_group"}])
    assert _codes(invalid_shape.value) == {SlideSelectionGroupIssueCode.INVALID_SHAPE}
    assert invalid_shape.value.issues[0].path


def test_normalize_builds_deterministic_nested_registry() -> None:
    groups = parse_slide_selection_groups(
        [
            {
                "group_id": "group_root",
                "name": "Root",
                "type": "bundle",
                "inclusion_policy": "always",
                "members": ["slide_001", "group_options"],
            },
            {
                "group_id": "group_options",
                "name": "Options",
                "type": "choice",
                "members": ["slide_002", "slide_003"],
            },
        ]
    )

    registry = normalize_slide_selection_groups(groups, slide_inclusion_policies=_policies())

    assert tuple(registry.groups) == ("group_root", "group_options")
    assert registry.root_group_ids == ("group_root",)
    assert registry.slide_ids == ("slide_001", "slide_002", "slide_003", "slide_004")
    assert registry.grouped_slide_ids == ("slide_001", "slide_002", "slide_003")
    assert registry.singleton_slide_ids == ()


def test_root_single_slide_wrapper_is_normalized_away_without_policy() -> None:
    singleton = _group(
        "group_single",
        SlideSelectionGroupType.CHOICE,
        ("slide_001",),
    )

    registry = normalize_slide_selection_groups(
        [singleton],
        slide_inclusion_policies=_policies(slide_001="always"),
    )

    assert dict(registry.groups) == {}
    assert registry.root_group_ids == ()
    assert registry.grouped_slide_ids == ()
    assert registry.singleton_slide_ids == ("slide_001",)
    assert validate_slide_selection_group_selection(registry, []) == ()


@pytest.mark.parametrize(
    ("groups", "expected_code"),
    [
        (
            [_group("group_root", SlideSelectionGroupType.CHOICE, ("slide_001", "slide_002"))],
            SlideSelectionGroupIssueCode.ROOT_POLICY_REQUIRED,
        ),
        (
            [
                _group(
                    "group_root",
                    SlideSelectionGroupType.BUNDLE,
                    ("group_nested", "slide_001"),
                    inclusion_policy="when_relevant",
                ),
                _group(
                    "group_nested",
                    SlideSelectionGroupType.CHOICE,
                    ("slide_002", "slide_003"),
                    inclusion_policy="when_relevant",
                ),
            ],
            SlideSelectionGroupIssueCode.NESTED_POLICY_FORBIDDEN,
        ),
        (
            [
                _group(
                    "group_root",
                    SlideSelectionGroupType.CHOICE,
                    ("group_nested", "slide_001"),
                    inclusion_policy="when_relevant",
                ),
                _group(
                    "group_nested",
                    SlideSelectionGroupType.BUNDLE,
                    ("slide_002",),
                ),
            ],
            SlideSelectionGroupIssueCode.INVALID_SINGLETON,
        ),
        (
            [
                _group(
                    "group_root",
                    SlideSelectionGroupType.CHOICE,
                    ("group_nested",),
                    inclusion_policy="when_relevant",
                ),
                _group(
                    "group_nested",
                    SlideSelectionGroupType.BUNDLE,
                    ("slide_001", "slide_002"),
                ),
            ],
            SlideSelectionGroupIssueCode.INVALID_SINGLETON,
        ),
    ],
)
def test_normalize_rejects_invalid_policy_and_singleton_rules(
    groups: list[SlideSelectionGroup],
    expected_code: SlideSelectionGroupIssueCode,
) -> None:
    with pytest.raises(SlideSelectionGroupContractError) as error:
        normalize_slide_selection_groups(groups, slide_inclusion_policies=_policies())
    assert expected_code in _codes(error.value)


@pytest.mark.parametrize(
    ("groups", "expected_code"),
    [
        (
            [
                _group(
                    "group_root",
                    SlideSelectionGroupType.CHOICE,
                    ("slide_999", "slide_001"),
                    inclusion_policy="when_relevant",
                )
            ],
            SlideSelectionGroupIssueCode.UNKNOWN_MEMBER,
        ),
        (
            [
                _group(
                    "group_one",
                    SlideSelectionGroupType.CHOICE,
                    ("slide_001", "slide_002"),
                    inclusion_policy="when_relevant",
                ),
                _group(
                    "group_two",
                    SlideSelectionGroupType.BUNDLE,
                    ("slide_001", "slide_003"),
                    inclusion_policy="when_relevant",
                ),
            ],
            SlideSelectionGroupIssueCode.MULTIPLE_PARENTS,
        ),
        (
            [
                _group(
                    "group_one",
                    SlideSelectionGroupType.CHOICE,
                    ("group_two", "slide_001"),
                    inclusion_policy="when_relevant",
                ),
                _group(
                    "group_two",
                    SlideSelectionGroupType.BUNDLE,
                    ("group_one", "slide_002"),
                ),
            ],
            SlideSelectionGroupIssueCode.CYCLE,
        ),
    ],
)
def test_normalize_rejects_invalid_graphs(
    groups: list[SlideSelectionGroup],
    expected_code: SlideSelectionGroupIssueCode,
) -> None:
    with pytest.raises(SlideSelectionGroupContractError) as error:
        normalize_slide_selection_groups(groups, slide_inclusion_policies=_policies())
    assert expected_code in _codes(error.value)


def test_normalize_rejects_grouped_hard_slide_policy_and_empty_descendants() -> None:
    group = _group(
        "group_root",
        SlideSelectionGroupType.CHOICE,
        ("slide_001", "slide_002"),
        inclusion_policy="when_relevant",
    )
    with pytest.raises(SlideSelectionGroupContractError) as hard_policy:
        normalize_slide_selection_groups(
            [group],
            slide_inclusion_policies=_policies(slide_001="never"),
        )
    assert SlideSelectionGroupIssueCode.GROUPED_SLIDE_POLICY in _codes(hard_policy.value)

    empty = _group(
        "group_empty",
        SlideSelectionGroupType.BUNDLE,
        (),
        inclusion_policy="when_relevant",
    )
    with pytest.raises(SlideSelectionGroupContractError) as empty_descendants:
        normalize_slide_selection_groups([empty], slide_inclusion_policies=_policies())
    assert SlideSelectionGroupIssueCode.NO_SLIDE_DESCENDANT in _codes(empty_descendants.value)


def test_final_selection_enforces_choice_bundle_and_root_policies() -> None:
    choice = normalize_slide_selection_groups(
        [
            _group(
                "group_choice",
                SlideSelectionGroupType.CHOICE,
                ("slide_001", "slide_002"),
                inclusion_policy="when_relevant",
            )
        ],
        slide_inclusion_policies=_policies(),
    )
    assert validate_slide_selection_group_selection(choice, []) == ()
    assert validate_slide_selection_group_selection(choice, ["slide_001"]) == ()
    assert SlideSelectionGroupIssueCode.CHOICE_SELECTION in {
        issue.code
        for issue in validate_slide_selection_group_selection(
            choice, ["slide_001", "slide_002"]
        )
    }

    bundle = normalize_slide_selection_groups(
        [
            _group(
                "group_bundle",
                SlideSelectionGroupType.BUNDLE,
                ("slide_001", "slide_002"),
                inclusion_policy="always",
            )
        ],
        slide_inclusion_policies=_policies(),
    )
    assert validate_slide_selection_group_selection(bundle, ["slide_001", "slide_002"]) == ()
    assert {
        issue.code for issue in validate_slide_selection_group_selection(bundle, ["slide_001"])
    } == {SlideSelectionGroupIssueCode.BUNDLE_SELECTION}
    assert {
        issue.code for issue in validate_slide_selection_group_selection(bundle, [])
    } == {SlideSelectionGroupIssueCode.ROOT_POLICY_VIOLATION}

    never = normalize_slide_selection_groups(
        [
            _group(
                "group_never",
                SlideSelectionGroupType.CHOICE,
                ("slide_001", "slide_002"),
                inclusion_policy="never",
            )
        ],
        slide_inclusion_policies=_policies(),
    )
    assert validate_slide_selection_group_selection(never, []) == ()
    assert {
        issue.code for issue in validate_slide_selection_group_selection(never, ["slide_001"])
    } == {SlideSelectionGroupIssueCode.ROOT_POLICY_VIOLATION}


def test_final_selection_checks_nested_activation_and_selected_id_integrity() -> None:
    registry = normalize_slide_selection_groups(
        [
            _group(
                "group_root",
                SlideSelectionGroupType.BUNDLE,
                ("slide_001", "group_options"),
                inclusion_policy="when_relevant",
            ),
            _group(
                "group_options",
                SlideSelectionGroupType.CHOICE,
                ("slide_002", "slide_003"),
            ),
        ],
        slide_inclusion_policies=_policies(),
    )

    assert validate_slide_selection_group_selection(registry, []) == ()
    assert validate_slide_selection_group_selection(registry, ["slide_001", "slide_002"]) == ()
    partial = validate_slide_selection_group_selection(registry, ["slide_002"])
    assert {issue.code for issue in partial} == {SlideSelectionGroupIssueCode.BUNDLE_SELECTION}

    malformed = validate_slide_selection_group_selection(
        registry,
        ["slide_004", "slide_004", "slide_999"],
    )
    assert [issue.code for issue in malformed] == [
        SlideSelectionGroupIssueCode.DUPLICATE_SELECTED_SLIDE,
        SlideSelectionGroupIssueCode.UNKNOWN_SELECTED_SLIDE,
    ]

"""Tests for the public efficio_ppt_components Python SDK surface."""

from __future__ import annotations

import pytest

import efficio_ppt_components as sdk
from efficio_ppt_components import _resources
from efficio_ppt_components.errors import (
    EfficioComponentsError,
    MissingResourceError,
    UnknownComponentTypeError,
)

EXPECTED_TYPES = ["approval_block", "grouped_checklist_table", "table", "text"]


def test_import_exposes_only_stable_public_names() -> None:
    assert sorted(sdk.__all__) == sorted(
        [
            "EfficioComponentsError",
            "MissingResourceError",
            "UnknownComponentTypeError",
            "load_component_registry",
            "list_component_types",
            "has_component_type",
            "assert_component_type",
            "load_component_instruction",
            "load_component_instructions",
            "build_component_instruction_block",
            "load_slide_selection_instruction",
            "TagValidationIssue",
            "load_component_tag_schema",
            "load_slide_tag_contract",
            "validate_component_tags",
            "validate_slide_tags",
            "is_ai_facing",
            "ai_visible_tag_names",
            "project_component_context",
            "RENDER_BEHAVIOR_TAG",
            "AI_FACING_RENDER_BEHAVIOR",
            "PROMPT_INSTRUCTION_TAG",
        ]
    )
    for name in sdk.__all__:
        assert hasattr(sdk, name)


def test_list_component_types_is_sorted_and_complete() -> None:
    assert sdk.list_component_types() == EXPECTED_TYPES


def test_is_ai_facing_only_for_render_by_component_type() -> None:
    assert sdk.is_ai_facing({"efficio_render_behavior": "render_by_component_type"}) is True
    for behavior in ("preserve", "remove_on_render", "", "bogus"):
        assert sdk.is_ai_facing({"efficio_render_behavior": behavior}) is False
    assert sdk.is_ai_facing({}) is False


def test_ai_visible_tag_names_are_public_aliases() -> None:
    names = sdk.ai_visible_tag_names("text")
    assert {
        "text_format",
        "max_chars",
        "max_lines",
        "max_chars_per_line",
    } <= names
    # raw efficio_* names never appear in the AI-facing contract
    assert not any(name.startswith("efficio_") for name in names)
    # sizing mode is a required editor/runtime tag but is no longer AI-visible
    assert "sizing_mode" not in names
    # identity/runtime tags are not AI-visible
    assert "component_id" not in names


def test_project_component_context_is_ai_safe() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "title_01",
        "efficio_component_type": "text",
        "efficio_prompt_instruction": "Write a title.",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "30",
    }
    context = sdk.project_component_context("text", tags)
    assert context["component_type"] == "text"
    assert context["instructions"] == "Write a title."
    # Keys are public aliases; integer tag values become JSON numbers.
    # efficio_sizing_mode is present on the shape but no longer AI-visible, so it is filtered out.
    assert context["tag_context"] == {
        "text_format": "plain",
        "max_chars": 30,
    }
    # render-behavior (filtering) and prompt-instruction (surfaced) never duplicated;
    # identity/runtime tags never leak — under neither raw nor aliased names.
    for excluded in (
        "efficio_render_behavior",
        "render_behavior",
        "efficio_prompt_instruction",
        "prompt_instruction",
        "efficio_component_id",
        "component_id",
    ):
        assert excluded not in context["tag_context"]


def test_project_component_context_omits_missing_instructions() -> None:
    context = sdk.project_component_context(
        "text", {"efficio_render_behavior": "render_by_component_type"}
    )
    assert "instructions" not in context
    assert context["tag_context"] == {}


def test_project_component_context_omits_blank_instruction_variants() -> None:
    for blank in ("", "   ", "\n", "\t\n "):
        context = sdk.project_component_context(
            "text",
            {
                "efficio_render_behavior": "render_by_component_type",
                "efficio_prompt_instruction": blank,
            },
        )
        assert "instructions" not in context, blank


def test_project_component_context_trims_nonblank_instruction() -> None:
    context = sdk.project_component_context(
        "text",
        {
            "efficio_render_behavior": "render_by_component_type",
            "efficio_prompt_instruction": "  Write a title.  ",
        },
    )
    assert context["instructions"] == "Write a title."


def test_project_component_context_omits_blank_tag_values() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_text_format": "plain",
        "efficio_max_chars": "   ",  # blank -> omitted
        "efficio_max_lines": "\n",  # blank -> omitted
        "efficio_max_chars_per_line": "40",  # non-blank -> kept
    }
    context = sdk.project_component_context("text", tags)
    assert context["tag_context"] == {
        "text_format": "plain",
        "max_chars_per_line": 40,
    }


def test_project_component_context_parses_json_object_tags() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_groups": '{"groups":[{"key":"now","label":"Do now","inclusion_policy":"always"}]}',
    }
    context = sdk.project_component_context("grouped_checklist_table", tags)
    assert context["tag_context"] == {
        "groups": {
            "groups": [{"key": "now", "label": "Do now", "inclusion_policy": "always"}]
        }
    }


def test_project_component_context_rejects_non_integer_value() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_max_chars": "thirty",
    }
    with pytest.raises(ValueError, match="efficio_max_chars"):
        sdk.project_component_context("text", tags)


def test_project_component_context_rejects_invalid_json_value() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_groups": "{not valid json",
    }
    with pytest.raises(ValueError, match="efficio_groups"):
        sdk.project_component_context("grouped_checklist_table", tags)


def test_project_component_context_ignores_non_efficio_tags() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_text_format": "plain",
        "text_format": "bullets",  # foreign non-efficio tag never leaks in
    }
    context = sdk.project_component_context("text", tags)
    assert context["tag_context"] == {"text_format": "plain"}


def test_has_component_type() -> None:
    assert sdk.has_component_type("text") is True
    assert sdk.has_component_type("missing") is False


def test_assert_component_type_raises_for_unknown() -> None:
    sdk.assert_component_type("text")  # no raise
    with pytest.raises(UnknownComponentTypeError):
        sdk.assert_component_type("missing")


def test_load_component_registry_returns_dict_with_components() -> None:
    registry = sdk.load_component_registry()
    assert isinstance(registry, dict)
    assert set(registry["components"].keys()) == set(EXPECTED_TYPES)


def test_load_component_instruction_returns_text_instruction() -> None:
    instruction = sdk.load_component_instruction("text")
    assert instruction["component_type"] == "text"
    assert "tag_instructions" in instruction
    assert "expected_content_schema" in instruction


def test_load_component_instruction_rejects_unknown_type() -> None:
    with pytest.raises(UnknownComponentTypeError):
        sdk.load_component_instruction("missing")


def test_load_component_instructions_full_catalog() -> None:
    catalog = sdk.load_component_instructions()
    assert sorted(catalog.keys()) == ["component_instructions", "instruction"]
    assert isinstance(catalog["instruction"], str) and catalog["instruction"]
    assert set(catalog["component_instructions"].keys()) == set(EXPECTED_TYPES)


def test_load_component_instructions_dedupes_and_sorts() -> None:
    catalog = sdk.load_component_instructions(["text", "text", "grouped_checklist_table"])
    assert sorted(catalog.keys()) == ["component_instructions", "instruction"]
    assert list(catalog["component_instructions"].keys()) == ["grouped_checklist_table", "text"]


def test_build_component_instruction_block_returns_only_selected() -> None:
    block = sdk.build_component_instruction_block(["text"])
    assert sorted(block.keys()) == ["component_instructions", "instruction"]
    assert list(block["component_instructions"].keys()) == ["text"]
    assert block["component_instructions"]["text"]["component_type"] == "text"
    # Preserves the authored general instruction; no file paths leak.
    assert isinstance(block["instruction"], str) and block["instruction"]
    assert "paths" not in block["component_instructions"]["text"]


def test_build_component_instruction_block_preserves_same_instruction() -> None:
    block = sdk.build_component_instruction_block(["text"])
    assert block["instruction"] == sdk.load_component_instructions()["instruction"]


def test_build_component_instruction_block_dedupes_and_sorts() -> None:
    block = sdk.build_component_instruction_block(["text", "grouped_checklist_table", "text"])
    assert list(block["component_instructions"].keys()) == ["grouped_checklist_table", "text"]


def test_build_component_instruction_block_rejects_unknown_type() -> None:
    with pytest.raises(UnknownComponentTypeError):
        sdk.build_component_instruction_block(["text", "missing"])


def test_load_slide_selection_instruction() -> None:
    artifact = sdk.load_slide_selection_instruction()
    assert isinstance(artifact, dict)
    assert "expected_slide_selection_schema" in artifact


def test_slide_selection_schema_is_strict_object_items() -> None:
    schema = sdk.load_slide_selection_instruction()["expected_slide_selection_schema"]
    selected = schema["properties"]["selected_slides"]
    assert selected["type"] == "array"
    assert selected["minItems"] == 1
    item = selected["items"]
    # Object items with a required slide_id and a bounded optional reason — no
    # wrapper fields on the item or the root.
    assert item["type"] == "object"
    assert item["required"] == ["slide_id"]
    assert item["properties"]["slide_id"]["type"] == "string"
    assert item["properties"]["selection_reason"]["maxLength"] == 300
    assert item["additionalProperties"] is False
    assert schema["additionalProperties"] is False


def valid_text_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "title",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "30",
        "efficio_max_lines": "30",
        "efficio_max_chars_per_line": "30",
    }
    tags.update(overrides)
    return tags


def test_load_component_tag_schema() -> None:
    schema = sdk.load_component_tag_schema("text")
    assert schema["component_type"] == "text"
    assert "efficio_component_id" in schema["required_tags"]


def test_load_slide_tag_contract() -> None:
    contract = sdk.load_slide_tag_contract()
    assert contract["contract_type"] == "slide_tags"
    assert contract["tags"]["efficio_slide_id"]["required"] is True


def test_validate_component_tags_accepts_valid_text_tags() -> None:
    assert sdk.validate_component_tags("text", valid_text_tags()) == []


def test_validate_component_tags_reports_required_and_enum_errors() -> None:
    issues = sdk.validate_component_tags(
        "text",
        valid_text_tags(efficio_text_format="wrong", efficio_max_chars="0"),
    )
    codes = {issue.code for issue in issues}
    assert "invalid_enum" in codes
    assert "invalid_positive_integer" in codes


def test_validate_component_tags_reports_missing_required_tag() -> None:
    tags = valid_text_tags()
    del tags["efficio_component_id"]
    issues = sdk.validate_component_tags("text", tags)
    assert [(issue.code, issue.tag_name) for issue in issues] == [
        ("missing_required_tag", "efficio_component_id")
    ]


def valid_groups_json() -> str:
    return (
        '{"groups":[{"key":"now","label":"Do now","inclusion_policy":"always",'
        '"suggested_items":["Confirm scope"]},'
        '{"key":"next","label":"Do next","inclusion_policy":"when_relevant"}]}'
    )


def valid_grouped_checklist_table_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "action_groups",
        "efficio_component_type": "grouped_checklist_table",
        "efficio_groups": valid_groups_json(),
    }
    tags.update(overrides)
    return tags


def test_validate_grouped_checklist_table_accepts_valid_groups_json() -> None:
    assert sdk.validate_component_tags("grouped_checklist_table", valid_grouped_checklist_table_tags()) == []


def test_validate_grouped_checklist_table_rejects_invalid_json() -> None:
    issues = sdk.validate_component_tags(
        "grouped_checklist_table",
        valid_grouped_checklist_table_tags(efficio_groups="{not valid json"),
    )
    assert [(i.code, i.tag_name) for i in issues] == [("invalid_json", "efficio_groups")]


def test_validate_grouped_checklist_table_rejects_missing_group_key() -> None:
    issues = sdk.validate_component_tags(
        "grouped_checklist_table",
        valid_grouped_checklist_table_tags(
            efficio_groups='{"groups":[{"label":"A","inclusion_policy":"always"}]}'
        ),
    )
    codes = {i.code for i in issues}
    assert "schema_violation" in codes


def test_validate_grouped_checklist_table_rejects_invalid_inclusion_policy() -> None:
    issues = sdk.validate_component_tags(
        "grouped_checklist_table",
        valid_grouped_checklist_table_tags(
            efficio_groups='{"groups":[{"key":"a","label":"A","inclusion_policy":"sometimes"}]}'
        ),
    )
    assert any(i.code == "schema_violation" and "inclusion_policy" in i.message for i in issues)


def test_validate_grouped_checklist_table_reports_missing_groups_tag() -> None:
    tags = valid_grouped_checklist_table_tags()
    del tags["efficio_groups"]
    issues = sdk.validate_component_tags("grouped_checklist_table", tags)
    assert [(i.code, i.tag_name) for i in issues] == [
        ("missing_required_tag", "efficio_groups")
    ]


def valid_approval_block_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "approval_1",
        "efficio_component_type": "approval_block",
        "efficio_approval_block_layout": "table_2row_person_role",
        "efficio_label_cell": '{"row":0,"col":0}',
        "efficio_name_cell": '{"row":0,"col":1}',
        "efficio_role_cell": '{"row":1,"col":1}',
        "efficio_default_subtype": "approved",
        "efficio_subtype_policy": "ai_selectable",
        "efficio_missing_content_behavior": "leave_as_is",
        "efficio_approval_block_subtypes": (
            '{"recommended":{"label":"R"},"endorsed":{"label":"E"},"approved":{"label":"A"}}'
        ),
    }
    tags.update(overrides)
    return tags


def test_validate_approval_block_accepts_valid_tags() -> None:
    assert sdk.validate_component_tags("approval_block", valid_approval_block_tags()) == []


def test_validate_approval_block_reports_missing_required_tags() -> None:
    tags = valid_approval_block_tags()
    del tags["efficio_label_cell"]
    del tags["efficio_default_subtype"]
    issues = sdk.validate_component_tags("approval_block", tags)
    missing = {i.tag_name for i in issues if i.code == "missing_required_tag"}
    assert {"efficio_label_cell", "efficio_default_subtype"} <= missing


def test_validate_approval_block_rejects_invalid_cell_json() -> None:
    issues = sdk.validate_component_tags(
        "approval_block", valid_approval_block_tags(efficio_name_cell="{not json")
    )
    assert [(i.code, i.tag_name) for i in issues] == [("invalid_json", "efficio_name_cell")]


def test_validate_approval_block_rejects_out_of_range_cell() -> None:
    issues = sdk.validate_component_tags(
        "approval_block", valid_approval_block_tags(efficio_label_cell='{"row":5,"col":0}')
    )
    assert any(i.code == "schema_violation" and i.tag_name == "efficio_label_cell" for i in issues)


def test_validate_approval_block_rejects_incomplete_subtype_config() -> None:
    issues = sdk.validate_component_tags(
        "approval_block",
        valid_approval_block_tags(efficio_approval_block_subtypes='{"recommended":{"label":"R"}}'),
    )
    assert any(i.code == "schema_violation" and i.tag_name == "efficio_approval_block_subtypes" for i in issues)


def test_validate_approval_block_rejects_invalid_enum() -> None:
    issues = sdk.validate_component_tags(
        "approval_block", valid_approval_block_tags(efficio_default_subtype="nope")
    )
    assert ("invalid_enum", "efficio_default_subtype") in [(i.code, i.tag_name) for i in issues]


def test_validate_slide_tags_accepts_required_slide_tags() -> None:
    issues = sdk.validate_slide_tags(
        {
            "efficio_slide_id": "slide_001",
            "efficio_slide_placement": "body",
            "efficio_slide_inclusion_policy": "when_relevant",
        }
    )
    assert issues == []


def test_validate_slide_tags_reports_contract_errors() -> None:
    issues = sdk.validate_slide_tags(
        {
            "efficio_slide_id": "bad id",
            "efficio_slide_placement": "unknown",
            "efficio_slide_inclusion_policy": "when_relevant",
            "efficio_slide_group_order": "0",
        }
    )
    codes = {(issue.code, issue.tag_name) for issue in issues}
    assert ("pattern_mismatch", "efficio_slide_id") in codes
    assert ("invalid_enum", "efficio_slide_placement") in codes
    assert ("below_minimum", "efficio_slide_group_order") in codes


def test_missing_resource_raises_missing_resource_error() -> None:
    with pytest.raises(MissingResourceError):
        _resources.load_json("does-not-exist.json")


def test_error_hierarchy() -> None:
    assert issubclass(MissingResourceError, EfficioComponentsError)
    assert issubclass(UnknownComponentTypeError, EfficioComponentsError)

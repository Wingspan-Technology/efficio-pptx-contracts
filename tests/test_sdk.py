"""Tests for the public efficio_ppt_components Python SDK surface."""

from __future__ import annotations

import json

import pytest

import efficio_ppt_components as sdk
from efficio_ppt_components import _resources
from efficio_ppt_components.errors import (
    EfficioComponentsError,
    MissingResourceError,
    UnknownComponentTypeError,
)

EXPECTED_TYPES = ["category_chart", "table", "text"]


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
            "build_validation_content_schema",
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
        "target_chars",
        "min_items",
        "max_items",
        "min_chars_per_item",
        "max_chars_per_item",
        "target_chars_per_item",
    } <= names
    # raw efficio_* names never appear in the AI-facing contract
    assert not any(name.startswith("efficio_") for name in names)
    # sizing mode is a required editor/runtime tag but is no longer AI-visible
    assert "sizing_mode" not in names
    # identity/runtime tags are not AI-visible
    assert "component_id" not in names
    # structural tags never appear in tag_instructions (render filter / instructions surface)
    assert "render_behavior" not in names
    assert "prompt_instruction" not in names


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


def test_project_component_context_includes_target_chars_as_integer() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "title_01",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "40",
        "efficio_target_chars": "30",
    }
    context = sdk.project_component_context("text", tags)
    # target_chars is AI-visible sizing guidance; the integer tag becomes a JSON number.
    assert context["tag_context"]["target_chars"] == 30
    assert context["tag_context"]["max_chars"] == 40


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
        "efficio_min_items": "\n",  # blank -> omitted
        "efficio_max_chars_per_item": "40",  # non-blank -> kept
    }
    context = sdk.project_component_context("text", tags)
    assert context["tag_context"] == {
        "text_format": "plain",
        "max_chars_per_item": 40,
    }


def test_project_component_context_parses_json_object_tags() -> None:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_table_config": '{"cells":[{"row":0,"col":0,"render_action":"render"}]}',
    }
    context = sdk.project_component_context("table", tags)
    assert context["tag_context"] == {
        "table_config": {"cells": [{"row": 0, "col": 0, "render_action": "render"}]}
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
        "efficio_table_config": "{not valid json",
    }
    with pytest.raises(ValueError, match="efficio_table_config"):
        sdk.project_component_context("table", tags)


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
    catalog = sdk.load_component_instructions(["text", "text", "table"])
    assert sorted(catalog.keys()) == ["component_instructions", "instruction"]
    assert list(catalog["component_instructions"].keys()) == ["table", "text"]


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
    block = sdk.build_component_instruction_block(["text", "table", "text"])
    assert list(block["component_instructions"].keys()) == ["table", "text"]


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
    # Object items carry slide_id only — no other fields on the item or the root.
    assert item["type"] == "object"
    assert item["required"] == ["slide_id"]
    assert list(item["properties"]) == ["slide_id"]
    assert item["properties"]["slide_id"]["type"] == "string"
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
        "efficio_target_chars": "30",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "30",
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


def test_validate_text_accepts_target_chars_within_max() -> None:
    # target_chars <= max_chars is valid (below or equal).
    assert sdk.validate_component_tags("text", valid_text_tags(efficio_target_chars="20")) == []


def test_validate_text_accepts_missing_target_chars() -> None:
    # target_chars is optional guidance; omitting it is valid.
    tags = valid_text_tags()
    del tags["efficio_target_chars"]
    assert sdk.validate_component_tags("text", tags) == []


def test_validate_text_rejects_target_chars_exceeding_max() -> None:
    # target_chars > max_chars is a single semantic issue on efficio_target_chars:
    # target is AI sizing guidance, max_chars is the strict bound it must fit within.
    issues = sdk.validate_component_tags(
        "text", valid_text_tags(efficio_max_chars="30", efficio_target_chars="45")
    )
    assert [(i.code, i.tag_name) for i in issues] == [
        ("target_exceeds_max", "efficio_target_chars")
    ]


def test_validate_text_target_chars_non_integer_is_structural() -> None:
    # A zero/non-integer target is caught by structural (positive-integer) validation,
    # not the semantic comparison.
    issues = sdk.validate_component_tags("text", valid_text_tags(efficio_target_chars="0"))
    codes = {(i.code, i.tag_name) for i in issues}
    assert ("invalid_positive_integer", "efficio_target_chars") in codes
    assert all(i.code != "target_exceeds_max" for i in issues)


def test_validate_text_skips_target_semantic_when_max_structurally_invalid() -> None:
    # When max_chars is structurally invalid the target<=max comparison is skipped, so
    # only the structural error is reported (no noisy follow-on).
    issues = sdk.validate_component_tags(
        "text", valid_text_tags(efficio_max_chars="oops", efficio_target_chars="45")
    )
    assert any(i.tag_name == "efficio_max_chars" for i in issues)
    assert all(i.code != "target_exceeds_max" for i in issues)


def test_validate_text_rejects_min_items_over_max_items() -> None:
    # A list format so min/max items are not forced to 1; min_items > max_items fails.
    issues = sdk.validate_component_tags(
        "text",
        valid_text_tags(efficio_text_format="bullets", efficio_min_items="4", efficio_max_items="2"),
    )
    assert ("min_exceeds_max", "efficio_min_items") in [(i.code, i.tag_name) for i in issues]


def test_validate_text_rejects_min_chars_per_item_over_max() -> None:
    issues = sdk.validate_component_tags(
        "text",
        valid_text_tags(efficio_min_chars_per_item="40", efficio_max_chars_per_item="20"),
    )
    assert ("min_exceeds_max", "efficio_min_chars_per_item") in [
        (i.code, i.tag_name) for i in issues
    ]


def test_validate_text_rejects_target_per_item_outside_bounds() -> None:
    over = sdk.validate_component_tags(
        "text",
        valid_text_tags(efficio_max_chars_per_item="20", efficio_target_chars_per_item="45"),
    )
    assert ("target_exceeds_max", "efficio_target_chars_per_item") in [
        (i.code, i.tag_name) for i in over
    ]
    under = sdk.validate_component_tags(
        "text",
        valid_text_tags(
            efficio_min_chars_per_item="10",
            efficio_max_chars_per_item="30",
            efficio_target_chars_per_item="5",
        ),
    )
    assert ("target_below_min", "efficio_target_chars_per_item") in [
        (i.code, i.tag_name) for i in under
    ]


def test_validate_text_accepts_missing_target_per_item() -> None:
    # target_chars_per_item is optional; omitting it is valid.
    tags = valid_text_tags(efficio_min_chars_per_item="1", efficio_max_chars_per_item="30")
    assert "efficio_target_chars_per_item" not in tags
    assert sdk.validate_component_tags("text", tags) == []


def test_validate_text_plain_requires_single_item() -> None:
    # plain text must be exactly one item: min_items and max_items must both be 1.
    issues = sdk.validate_component_tags(
        "text", valid_text_tags(efficio_text_format="plain", efficio_max_items="3")
    )
    assert ("plain_requires_single_item", "efficio_max_items") in [
        (i.code, i.tag_name) for i in issues
    ]


def valid_table_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "grid_1",
        "efficio_component_type": "table",
        "efficio_table_config": '{"cells":[{"row":0,"col":0,"render_action":"render"}]}',
    }
    tags.update(overrides)
    return tags


def test_validate_table_accepts_valid_config() -> None:
    assert sdk.validate_component_tags("table", valid_table_tags()) == []


def test_validate_table_rejects_invalid_config_json() -> None:
    issues = sdk.validate_component_tags(
        "table", valid_table_tags(efficio_table_config="{not valid json")
    )
    assert [(i.code, i.tag_name) for i in issues] == [("invalid_json", "efficio_table_config")]


def test_validate_table_rejects_out_of_range_cell() -> None:
    issues = sdk.validate_component_tags(
        "table", valid_table_tags(efficio_table_config='{"cells":[{"row":-1,"col":0}]}')
    )
    assert any(i.code == "schema_violation" and i.tag_name == "efficio_table_config" for i in issues)


def test_validate_table_reports_missing_config_tag() -> None:
    tags = valid_table_tags()
    del tags["efficio_table_config"]
    issues = sdk.validate_component_tags("table", tags)
    assert [(i.code, i.tag_name) for i in issues] == [
        ("missing_required_tag", "efficio_table_config")
    ]


def _category_chart_config(**overrides: object) -> dict:
    config = {
        "chart_type": "CLUSTERED_COLUMN",
        "category_mode": "fixed",
        "categories": ["Q1", "Q2", "Q3", "Q4"],
        "series_mode": "ai_generated",
        "min_categories": 4,
        "max_categories": 4,
        "target_categories": 4,
        "min_series": 1,
        "max_series": 3,
        "target_series": 2,
        "value_type": "number",
        "allow_negative_values": False,
        "allow_decimal_values": True,
    }
    config.update(overrides)
    return config


def valid_category_chart_tags(**config_overrides: object) -> dict[str, str]:
    config = _category_chart_config(**config_overrides)
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "revenue_chart",
        "efficio_component_type": "category_chart",
        "efficio_chart_type": config["chart_type"],
        "efficio_category_mode": config["category_mode"],
        "efficio_series_mode": config["series_mode"],
        "efficio_min_categories": str(config["min_categories"]),
        "efficio_max_categories": str(config["max_categories"]),
        "efficio_target_categories": str(config["target_categories"]),
        "efficio_min_series": str(config["min_series"]),
        "efficio_max_series": str(config["max_series"]),
        "efficio_target_series": str(config["target_series"]),
        "efficio_value_type": config["value_type"],
        "efficio_allow_negative_values": "true" if config["allow_negative_values"] else "false",
        "efficio_allow_decimal_values": "true" if config["allow_decimal_values"] else "false",
    }
    if "categories" in config:
        tags["efficio_categories"] = json.dumps(config["categories"])
    if "series_names" in config:
        tags["efficio_series_names"] = json.dumps(config["series_names"])
    return tags


def test_validate_category_chart_accepts_valid_config() -> None:
    assert sdk.validate_component_tags("category_chart", valid_category_chart_tags()) == []


def test_validate_category_chart_requires_fixed_categories() -> None:
    tags = valid_category_chart_tags()
    del tags["efficio_categories"]  # fixed mode without the required labels
    issues = sdk.validate_component_tags("category_chart", tags)
    assert any(
        i.code == "fixed_axis_requires_labels" and i.tag_name == "efficio_categories"
        for i in issues
    )


def test_validate_category_chart_forbids_labels_in_ai_generated_mode() -> None:
    # ai_generated categories must not also supply a fixed label array.
    issues = sdk.validate_component_tags(
        "category_chart", valid_category_chart_tags(category_mode="ai_generated")
    )
    assert any(
        i.code == "ai_axis_forbids_labels" and i.tag_name == "efficio_categories"
        for i in issues
    )


def test_validate_category_chart_rejects_invalid_count_ordering() -> None:
    issues = sdk.validate_component_tags(
        "category_chart", valid_category_chart_tags(target_series=9)
    )
    assert [(i.code, i.tag_name) for i in issues] == [
        ("target_exceeds_max", "efficio_target_series")
    ]


def test_validate_category_chart_rejects_percent_stacked_negative() -> None:
    issues = sdk.validate_component_tags(
        "category_chart",
        valid_category_chart_tags(
            chart_type="PERCENTS_STACKED_COLUMN", allow_negative_values=True
        ),
    )
    assert [(i.code, i.tag_name) for i in issues] == [
        ("percent_stacked_negative", "efficio_allow_negative_values")
    ]


def test_validate_category_chart_skips_semantics_when_structurally_invalid() -> None:
    # A structurally broken tag (bad chart_type enum) is reported structurally; the
    # cross-field checks that read that tag do not pile on redundant errors.
    issues = sdk.validate_component_tags(
        "category_chart", valid_category_chart_tags(chart_type="PIE")
    )
    assert any(i.code == "invalid_enum" and i.tag_name == "efficio_chart_type" for i in issues)
    assert all(i.code != "percent_stacked_negative" for i in issues)


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

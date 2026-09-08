"""Smoke-tests the built wheel's public Python SDK surface.

Run by scripts/verify-release-artifacts.sh with a throwaway virtual
environment's interpreter, which has the freshly built wheel installed, so the
imports below resolve through that installation rather than this repository's
sources.
"""

from importlib.resources import files
import json

from efficio_pptx_contracts import (
    CLASSIFICATION_SCHEMES_TAG,
    CLASSIFICATION_SCHEME_ID_TAG,
    CURRENT_TEMPLATE_CONTRACT_REVISION,
    SLIDE_ARCHETYPES_TAG,
    SLIDE_ARCHETYPE_IDS_TAG,
    ContentMode,
    SlideArchetype,
    SlideArchetypeContractError,
    SlideSelectionGroupType,
    TemplateTagScope,
    TemplateTagTarget,
    V2ComponentRepairReason,
    V2ComponentSemanticFinding,
    V2SemanticRule,
    build_data_bound_component_contract,
    build_component_render_metadata,
    build_validation_content_schema,
    build_v2_component_contract,
    is_slide_applicable_to_archetype,
    list_component_types,
    load_component_instructions,
    load_deck_tag_contract,
    load_slide_tag_contract,
    normalize_v2_component_content,
    normalize_slide_selection_groups,
    parse_slide_archetype_ids,
    parse_slide_archetypes,
    parse_slide_selection_groups,
    parse_classification_schemes,
    plan_template_contract_migration,
    resolve_content_mode,
    resolve_slide_archetype_assignment,
    validate_deck_tags,
    validate_slide_selection_group_selection,
    validate_slide_tags,
    validate_v2_component_semantics,
    validate_v2_executable_component_schema,
    project_component_context,
)

component_types = list_component_types()
assert {"text", "table", "category_chart", "categorical_fill"}.issubset(component_types)
assert load_component_instructions()["component_instructions"]
assert files("efficio_pptx_contracts").joinpath("_generated/component-registry.json").is_file()

slide_contract = load_slide_tag_contract()
slide_role = slide_contract["tags"]["efficio_slide_role"]
assert slide_role["required"] is True
assert slide_role["enum"] == ["content", "separator"]
for role in slide_role["enum"]:
    assert validate_slide_tags(
        {
            "efficio_slide_id": "slide_001",
            "efficio_slide_role": role,
            "efficio_slide_placement": "body",
            "efficio_slide_inclusion_policy": "when_relevant",
        }
    ) == []

selection_groups = parse_slide_selection_groups(
    [
        {
            "group_id": "group_release",
            "name": "Release smoke",
            "type": "choice",
            "inclusion_policy": "when_relevant",
            "members": ["slide_001", "slide_002"],
        }
    ]
)
assert selection_groups[0].group_type is SlideSelectionGroupType.CHOICE
selection_registry = normalize_slide_selection_groups(
    selection_groups,
    slide_inclusion_policies={
        "slide_001": "when_relevant",
        "slide_002": "when_relevant",
    },
)
assert validate_slide_selection_group_selection(selection_registry, ["slide_001"]) == ()

text_contract = build_v2_component_contract(
    "text",
    {
        "efficio_content_mode": "ai_generated",
        "efficio_component_id": "release_smoke",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_lines": "1",
        "efficio_estimated_chars_per_line": "40",
        "efficio_min_chars": "1",
        "efficio_max_chars": "40",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "40",
    },
)
content = {"items": ["Release smoke"]}
validate_v2_executable_component_schema(
    text_contract["output_schema"], require_prompt_profile=True
)
validate_v2_component_semantics("text", content, text_contract["normalization"])
assert normalize_v2_component_content(
    "text", content, text_contract["normalization"]
) == content

classification_schemes = [
    {
        "scheme_id": "selection_state",
        "instruction": "Decide whether the option should be selected.",
        "palette_mode": "rgb",
        "cases": [
            {
                "case_id": "selected",
                "label": "Selected",
                "description": "The option should be highlighted.",
                "fill": {"value": "17365D"},
            },
            {
                "case_id": "unselected",
                "label": "Unselected",
                "description": "The option should remain inactive.",
                "fill": {"value": "BFBFBF"},
            },
        ],
    }
]
deck_tags = {CLASSIFICATION_SCHEMES_TAG: json.dumps(classification_schemes)}
fill_tags = {
    "efficio_content_mode": "ai_generated",
    "efficio_component_id": "option_one",
    "efficio_component_type": "categorical_fill",
    "efficio_content_role": "Option one",
    CLASSIFICATION_SCHEME_ID_TAG: "selection_state",
}
assert parse_classification_schemes(deck_tags[CLASSIFICATION_SCHEMES_TAG])[0].scheme_id == "selection_state"
fill_contract = build_v2_component_contract(
    "categorical_fill", fill_tags, deck_tags=deck_tags
)
assert fill_contract["output_schema"]["properties"]["case_id"]["enum"] == [
    "selected",
    "unselected",
]
assert build_validation_content_schema(
    "categorical_fill", fill_tags, deck_tags=deck_tags
) == {
    "type": "object",
    "properties": {
        "case_id": {"type": "string", "enum": ["selected", "unselected"]}
    },
    "required": ["case_id"],
    "additionalProperties": False,
}
assert "'fill':" not in str(
    project_component_context("categorical_fill", fill_tags, deck_tags=deck_tags)
)
assert build_component_render_metadata(
    "categorical_fill", fill_tags, deck_tags=deck_tags
)["cases"]["selected"]["fill"] == {"kind": "rgb", "value": "17365D"}
fill_data_bound = build_data_bound_component_contract(
    "categorical_fill",
    {**fill_tags, "efficio_content_mode": "data_bound"},
    deck_tags=deck_tags,
)
assert normalize_v2_component_content(
    "categorical_fill",
    {"case_id": "selected"},
    fill_contract["normalization"],
) == {"case_id": "selected"}
assert fill_data_bound["submission_schema"]["properties"]["case_id"]["enum"] == [
    "selected",
    "unselected",
]
finding = V2ComponentSemanticFinding(
    path=("items",),
    cell=None,
    rule=V2SemanticRule.ESTIMATED_LINE_LIMIT,
    reason=V2ComponentRepairReason.ESTIMATED_LINE_LIMIT,
)
assert finding.reason is V2ComponentRepairReason.ESTIMATED_LINE_LIMIT

assert CURRENT_TEMPLATE_CONTRACT_REVISION == 4
assert resolve_content_mode({"efficio_content_mode": "data_bound"}) is ContentMode.DATA_BOUND
plan = plan_template_contract_migration(
    [
        TemplateTagTarget("deck", TemplateTagScope.DECK, {}),
        TemplateTagTarget(
            "shape:1",
            TemplateTagScope.SHAPE,
            {"efficio_render_behavior": "render_by_component_type"},
        ),
    ]
)
assert plan.from_revision == 0 and plan.to_revision == 4 and len(plan.patches) == 2

archetype_registry = json.dumps(
    [
        {
            "archetype_id": "pitch_deck",
            "name": "Pitch deck",
            "description": "Investor narrative.",
        },
        {"archetype_id": "training", "name": "Training"},
    ]
)
deck_archetype_tags = {SLIDE_ARCHETYPES_TAG: archetype_registry}
archetypes = parse_slide_archetypes(archetype_registry)
assert archetypes == (
    SlideArchetype("pitch_deck", "Pitch deck", "Investor narrative."),
    SlideArchetype("training", "Training"),
)
assert parse_slide_archetype_ids('["training"]') == ("training",)
assigned_slide = {SLIDE_ARCHETYPE_IDS_TAG: '["training"]'}
assert resolve_slide_archetype_assignment(assigned_slide, deck_archetype_tags) == (
    archetypes[1],
)
assert resolve_slide_archetype_assignment({}, deck_archetype_tags) == ()
assert is_slide_applicable_to_archetype({}, deck_archetype_tags, "pitch_deck") is True
assert (
    is_slide_applicable_to_archetype(assigned_slide, deck_archetype_tags, "pitch_deck")
    is False
)
assert (
    is_slide_applicable_to_archetype(assigned_slide, deck_archetype_tags, "training")
    is True
)
try:
    is_slide_applicable_to_archetype({}, deck_archetype_tags, "board_update")
    raise AssertionError("an undeclared archetype must be rejected")
except SlideArchetypeContractError:
    pass

archetype_entity = load_deck_tag_contract()["tags"][SLIDE_ARCHETYPES_TAG]
assert archetype_entity["type"] == "array" and archetype_entity["required"] is False
assert "ai" not in archetype_entity
assignment_entity = load_slide_tag_contract()["tags"][SLIDE_ARCHETYPE_IDS_TAG]
assert assignment_entity["schema"]["minItems"] == 1
assert assignment_entity["schema"]["uniqueItems"] is True
assert "ai" not in assignment_entity
assert (
    validate_deck_tags(
        {
            "efficio_template_id": "release_smoke",
            "efficio_template_contract_revision": "4",
            SLIDE_ARCHETYPES_TAG: archetype_registry,
        }
    )
    == []
)
assert (
    validate_slide_tags(
        {
            "efficio_slide_id": "slide_001",
            "efficio_slide_role": "content",
            "efficio_slide_placement": "body",
            "efficio_slide_inclusion_policy": "when_relevant",
            SLIDE_ARCHETYPE_IDS_TAG: '["training"]',
        },
        deck_tags=deck_archetype_tags,
    )
    == []
)
data_bound = build_data_bound_component_contract(
    "text",
    {
        "efficio_content_mode": "data_bound",
        "efficio_component_id": "release_smoke",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "manual",
        "efficio_max_lines": "1",
        "efficio_estimated_chars_per_line": "2",
        "efficio_min_chars": "1",
        "efficio_max_chars": "2",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "2",
    },
)
assert data_bound["submission_schema"]["properties"]["items"] == {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
}

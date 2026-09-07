"""Categorical-fill schemes, contracts, projection, and normalization."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict

import pytest
from jsonschema import Draft202012Validator

from efficio_pptx_contracts import (
    CLASSIFICATION_SCHEMES_TAG,
    CLASSIFICATION_SCHEME_ID_TAG,
    ClassificationPaletteMode,
    V2ComponentRepairReason,
    build_component_render_metadata,
    build_data_bound_component_contract,
    build_v2_component_contract,
    build_validation_content_schema,
    collect_v2_component_semantic_findings,
    format_v2_component_repair_instruction,
    normalize_data_bound_component_content,
    normalize_v2_component_content,
    parse_classification_schemes,
    project_component_context,
    resolve_categorical_fill_scheme,
    validate_component_tags,
    validate_data_bound_component_contract_coherence,
    validate_deck_tags,
    validate_v2_component_contract_coherence,
)


def _schemes() -> list[dict[str, object]]:
    return [
        {
            "scheme_id": "selection_state",
            "instruction": "Decide whether each option should be selected.",
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


def _deck_tags(schemes: list[dict[str, object]] | None = None) -> dict[str, str]:
    return {
        "efficio_template_id": "supplier_review",
        "efficio_template_contract_revision": "2",
        CLASSIFICATION_SCHEMES_TAG: json.dumps(_schemes() if schemes is None else schemes),
    }


def _component_tags(mode: str = "ai_generated") -> dict[str, str]:
    return {
        "efficio_content_mode": mode,
        "efficio_component_id": "option_germany",
        "efficio_component_type": "categorical_fill",
        "efficio_content_role": "Germany",
        CLASSIFICATION_SCHEME_ID_TAG: "selection_state",
        "efficio_prompt_instruction": "Use evidence for Germany only.",
    }


def _private_metadata() -> dict[str, object]:
    return {
        "scheme_id": "selection_state",
        "cases": {
            "selected": {"fill": {"kind": "rgb", "value": "17365D"}},
            "unselected": {"fill": {"kind": "rgb", "value": "BFBFBF"}},
        },
    }


def test_parser_returns_typed_ordered_schemes() -> None:
    schemes = parse_classification_schemes(_deck_tags()[CLASSIFICATION_SCHEMES_TAG])
    assert len(schemes) == 1
    scheme = schemes[0]
    assert scheme.scheme_id == "selection_state"
    assert scheme.palette_mode is ClassificationPaletteMode.RGB
    assert [case.case_id for case in scheme.cases] == ["selected", "unselected"]
    assert scheme.cases[0].fill.value == "17365D"
    assert not hasattr(scheme.cases[0].fill, "kind")
    assert json.loads(json.dumps(asdict(scheme))) == _schemes()[0]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value.append(copy.deepcopy(value[0])), "scheme IDs"),
        (
            lambda value: value[0]["cases"].append(copy.deepcopy(value[0]["cases"][0])),
            "case IDs",
        ),
    ],
)
def test_parser_rejects_duplicate_ids(mutate, message: str) -> None:
    value = _schemes()
    mutate(value)
    with pytest.raises(ValueError, match=message):
        parse_classification_schemes(value)


@pytest.mark.parametrize("value", ["#17365D", "17365d", "17365", "GGGGGG"])
def test_deck_validation_rejects_invalid_rgb(value: str) -> None:
    schemes = _schemes()
    schemes[0]["cases"][0]["fill"]["value"] = value
    issues = validate_deck_tags(_deck_tags(schemes))
    assert ("schema_violation", CLASSIFICATION_SCHEMES_TAG) in {
        (issue.code, issue.tag_name) for issue in issues
    }


def test_component_reference_validation_is_context_aware() -> None:
    assert (
        validate_component_tags("categorical_fill", _component_tags(), deck_tags=_deck_tags()) == []
    )
    tags = _component_tags()
    tags[CLASSIFICATION_SCHEME_ID_TAG] = "missing_scheme"
    issues = validate_component_tags("categorical_fill", tags, deck_tags=_deck_tags())
    assert [(issue.code, issue.tag_name) for issue in issues] == [
        ("invalid_classification_scheme_reference", CLASSIFICATION_SCHEME_ID_TAG)
    ]


def test_resolver_requires_an_existing_scheme() -> None:
    assert (
        resolve_categorical_fill_scheme(_component_tags(), _deck_tags()).scheme_id
        == "selection_state"
    )
    with pytest.raises(ValueError, match="unknown classification scheme"):
        resolve_categorical_fill_scheme(
            {
                **_component_tags(),
                CLASSIFICATION_SCHEME_ID_TAG: "missing_scheme",
            },
            _deck_tags(),
        )


def test_ai_projection_exposes_semantics_but_never_colors() -> None:
    context = project_component_context(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    assert context == {
        "component_type": "categorical_fill",
        "instructions": "Use evidence for Germany only.",
        "tag_context": {
            "content_role": "Germany",
            "classification_scheme": {
                "scheme_id": "selection_state",
                "instruction": "Decide whether each option should be selected.",
                "cases": [
                    {
                        "case_id": "selected",
                        "label": "Selected",
                        "description": "The option should be highlighted.",
                    },
                    {
                        "case_id": "unselected",
                        "label": "Unselected",
                        "description": "The option should remain inactive.",
                    },
                ],
            },
        },
    }
    serialized = json.dumps(context)
    assert "17365D" not in serialized
    assert "BFBFBF" not in serialized
    assert '"fill":' not in serialized


def test_v2_contract_has_exact_case_enum_and_private_metadata() -> None:
    contract = build_v2_component_contract(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    schema = contract["output_schema"]
    assert schema["properties"]["case_id"]["enum"] == ["selected", "unselected"]
    assert "selected — Selected" in schema["properties"]["case_id"]["description"]
    assert schema["description"].startswith("Classify Germany.")
    assert contract["normalization"] == _private_metadata()
    assert "17365D" not in json.dumps(schema)
    Draft202012Validator(schema).validate({"case_id": "selected"})
    assert not Draft202012Validator(schema).is_valid({"case_id": "other"})


def test_canonical_and_data_bound_schemas_keep_exact_case_contract() -> None:
    canonical = build_validation_content_schema(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    data_bound = build_data_bound_component_contract(
        "categorical_fill",
        _component_tags("data_bound"),
        deck_tags=_deck_tags(),
    )
    expected = {
        "type": "object",
        "properties": {"case_id": {"type": "string", "enum": ["selected", "unselected"]}},
        "required": ["case_id"],
        "additionalProperties": False,
    }
    assert canonical == expected
    assert data_bound == {
        "submission_schema": expected,
        "normalization": _private_metadata(),
    }


def test_normalization_is_deterministic_and_rejects_unknown_cases() -> None:
    contract = build_v2_component_contract(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    content = {"case_id": "selected"}
    before = copy.deepcopy(content)
    assert (
        normalize_v2_component_content("categorical_fill", content, contract["normalization"])
        == content
    )
    assert content == before
    assert (
        normalize_data_bound_component_content(
            "categorical_fill", content, contract["normalization"]
        )
        == content
    )
    assert (
        collect_v2_component_semantic_findings(
            "categorical_fill", content, contract["normalization"]
        )
        == ()
    )
    with pytest.raises(ValueError, match="unknown case_id"):
        normalize_v2_component_content(
            "categorical_fill",
            {"case_id": "other"},
            contract["normalization"],
        )


def test_coherence_rejects_public_private_case_drift() -> None:
    contract = build_v2_component_contract(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    schema = copy.deepcopy(contract["output_schema"])
    schema["properties"]["case_id"]["enum"] = ["selected", "missing"]
    with pytest.raises(ValueError, match="must match normalization"):
        validate_v2_component_contract_coherence(
            "categorical_fill", schema, contract["normalization"]
        )
    data_bound = build_data_bound_component_contract(
        "categorical_fill", _component_tags("data_bound"), deck_tags=_deck_tags()
    )
    data_bound_schema = copy.deepcopy(data_bound["submission_schema"])
    data_bound_schema["properties"]["case_id"]["enum"] = ["selected", "missing"]
    with pytest.raises(ValueError, match="must match normalization"):
        validate_data_bound_component_contract_coherence(
            "categorical_fill", data_bound_schema, data_bound["normalization"]
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda schema: schema["properties"]["case_id"].update({"const": "missing"}),
        lambda schema: schema.update({"description": "Expose private RGB 17365D."}),
    ],
)
def test_coherence_rejects_extra_constraints_and_private_fill_leaks(mutation) -> None:
    contract = build_v2_component_contract(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    schema = copy.deepcopy(contract["output_schema"])
    mutation(schema)

    with pytest.raises(ValueError):
        validate_v2_component_contract_coherence(
            "categorical_fill", schema, contract["normalization"]
        )


def test_render_metadata_uses_the_same_private_mapping() -> None:
    assert (
        build_component_render_metadata(
            "categorical_fill", _component_tags(), deck_tags=_deck_tags()
        )
        == _private_metadata()
    )
    assert build_component_render_metadata("text", {}) == {}


def test_repair_instruction_lists_only_allowed_semantic_cases() -> None:
    canonical = build_validation_content_schema(
        "categorical_fill", _component_tags(), deck_tags=_deck_tags()
    )
    instruction = format_v2_component_repair_instruction(
        "categorical_fill",
        V2ComponentRepairReason.OTHER,
        canonical,
        _private_metadata(),
        cell=None,
    )
    assert instruction == (
        "Return exactly one string case_id for this categorical fill. "
        "Choose one allowed case_id: selected, unselected."
    )
    assert "17365D" not in instruction


@pytest.mark.parametrize(
    "builder",
    [
        lambda: build_v2_component_contract("categorical_fill", _component_tags()),
        lambda: build_validation_content_schema("categorical_fill", _component_tags()),
        lambda: build_data_bound_component_contract(
            "categorical_fill", _component_tags("data_bound")
        ),
        lambda: project_component_context("categorical_fill", _component_tags()),
        lambda: build_component_render_metadata("categorical_fill", _component_tags()),
    ],
)
def test_context_aware_apis_fail_without_deck_tags(builder) -> None:
    with pytest.raises(ValueError, match="deck_tags"):
        builder()

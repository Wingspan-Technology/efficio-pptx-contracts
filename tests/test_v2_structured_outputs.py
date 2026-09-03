"""Component-level V2 Structured Outputs projections and normalization."""

from __future__ import annotations

import copy
import json

import pytest
from efficio_pptx_contracts import (
    JSON_SCHEMA_DRAFT_2020_12_PROFILE,
    UnknownComponentTypeError,
    build_v2_component_contract,
    build_validation_content_schema,
    list_component_types,
    normalize_v2_component_content,
    validate_v2_component_contract_coherence,
    validate_v2_component_normalization,
    validate_v2_component_semantics,
)
from jsonschema import Draft202012Validator


def _text_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_content_mode": "ai_generated",
        "efficio_component_id": "title",
        "efficio_component_type": "text",
        "efficio_text_format": "bullets",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "120",
        "efficio_min_items": "2",
        "efficio_max_items": "4",
        "efficio_min_chars_per_item": "5",
        "efficio_max_chars_per_item": "40",
    }
    tags.update(overrides)
    return tags


def _table_tags(config: dict, **overrides: str) -> dict[str, str]:
    tags = {
        "efficio_content_mode": "ai_generated",
        "efficio_component_id": "supplier_table",
        "efficio_component_type": "table",
        "efficio_table_config": json.dumps(config),
    }
    tags.update(overrides)
    return tags


def _chart_tags(
    *,
    category_mode: str = "fixed",
    series_mode: str = "fixed",
    allow_decimals: bool = True,
    allow_negatives: bool = True,
) -> dict[str, str]:
    tags = {
        "efficio_content_mode": "ai_generated",
        "efficio_component_id": "spend_chart",
        "efficio_component_type": "category_chart",
        "efficio_chart_type": "CLUSTERED_COLUMN",
        "efficio_category_mode": category_mode,
        "efficio_min_categories": "2",
        "efficio_max_categories": "3",
        "efficio_target_categories": "2",
        "efficio_category_instruction": "Use concise period labels",
        "efficio_series_mode": series_mode,
        "efficio_min_series": "1",
        "efficio_max_series": "2",
        "efficio_target_series": "1",
        "efficio_series_instruction": "Use business metric names",
        "efficio_value_type": "number",
        "efficio_value_unit": "EUR millions",
        "efficio_allow_negative_values": str(allow_negatives).lower(),
        "efficio_allow_decimal_values": str(allow_decimals).lower(),
    }
    if category_mode == "fixed":
        tags["efficio_categories"] = json.dumps(["2025", "2026"])
    if series_mode == "fixed":
        tags["efficio_series_names"] = json.dumps(["Spend"])
    return tags


def _valid(schema: dict, value: dict) -> bool:
    return Draft202012Validator(schema).is_valid(value)


def _without_descriptions(value):
    if isinstance(value, dict):
        return {
            key: _without_descriptions(child)
            for key, child in value.items()
            if key != "description"
        }
    if isinstance(value, list):
        return [_without_descriptions(child) for child in value]
    return value


def test_named_profile_is_stable() -> None:
    assert JSON_SCHEMA_DRAFT_2020_12_PROFILE == "json-schema-draft-2020-12"


def test_text_schema_contains_hard_bounds_and_ordered_guidance() -> None:
    base = build_v2_component_contract("text", _text_tags())
    targeted = build_v2_component_contract(
        "text",
        _text_tags(
            efficio_target_chars="90",
            efficio_target_items="3",
            efficio_target_chars_per_item="30",
            efficio_prompt_instruction="Summarize verified savings",
        ),
    )
    assert set(targeted) == {"component_type", "output_schema", "normalization"}
    item = targeted["output_schema"]["properties"]["items"]["items"]
    assert item == {
        "type": "string",
        "description": "One bullet content item.",
        "minLength": 5,
        "maxLength": 40,
    }
    items = targeted["output_schema"]["properties"]["items"]
    assert items["minItems"] == 2
    assert items["maxItems"] == 4
    assert "EUR" not in json.dumps(targeted["output_schema"])
    description = targeted["output_schema"]["description"]
    assert "5–40 characters" in description
    assert "approximately 3 items" in description
    assert description.startswith("Summarize verified savings.")
    assert description.rfind("Aim for approximately") > description.index(
        "combined item length"
    )
    assert _without_descriptions(targeted["output_schema"]) == _without_descriptions(
        base["output_schema"]
    )
    assert targeted["normalization"] == {"max_chars": 120}
    assert "target_" not in json.dumps(targeted)


def test_plain_text_schema_requires_exactly_one_item() -> None:
    contract = build_v2_component_contract(
        "text",
        _text_tags(
            efficio_text_format="plain",
            efficio_min_items="1",
            efficio_max_items="1",
        ),
    )
    items = contract["output_schema"]["properties"]["items"]
    assert items["minItems"] == items["maxItems"] == 1
    assert "Return exactly 1 plain-text item" in contract["output_schema"]["description"]

    two_items = {"items": ["first", "second"]}
    assert not _valid(contract["output_schema"], two_items)
    canonical = build_validation_content_schema(
        "text",
        _text_tags(
            efficio_text_format="plain",
            efficio_min_items="1",
            efficio_max_items="1",
        ),
    )
    assert not _valid(canonical, two_items)


def test_text_semantics_enforce_aggregate_budget() -> None:
    contract = build_v2_component_contract("text", _text_tags(efficio_max_chars="10"))
    content = {"items": ["abcdef", "ghijk"]}
    with pytest.raises(ValueError, match="uses 11 characters"):
        validate_v2_component_semantics("text", content, contract["normalization"])
    validate_v2_component_semantics(
        "text", {"items": ["abcde", "fghij"]}, contract["normalization"]
    )


def test_text_rejects_impossible_v2_aggregate_budget_without_changing_v1() -> None:
    tags = _text_tags(efficio_max_chars="9")

    build_validation_content_schema("text", tags)

    with pytest.raises(
        ValueError,
        match=r"text V2 contract cannot satisfy max_chars 9.*require 10 characters",
    ):
        build_v2_component_contract("text", tags)


@pytest.mark.parametrize(
    "metadata",
    [{}, {"max_chars": 10, "extra": True}, {"max_chars": 0}, {"max_chars": True}],
)
def test_text_rejects_malformed_normalization(metadata: dict) -> None:
    with pytest.raises(ValueError, match="normalization"):
        normalize_v2_component_content("text", {"items": ["valid"]}, metadata)


def test_table_optional_cells_are_required_but_nullable() -> None:
    config = {
        "rows": [
            {"row": 0, "instruction": "Supplier identity"},
            {"row": 1, "content_policy": "optional", "instruction": "Optional note"},
        ],
        "columns": [{"col": 0, "instruction": "Use source wording"}],
        "cells": [
            {"row": 0, "col": 0, "render_action": "render", "instruction": "Supplier"},
            {
                "row": 1,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "max_items": 2,
                "min_chars_per_item": 3,
                "max_chars_per_item": 10,
                "max_chars": 20,
                "target_chars": 15,
            },
            {"row": 2, "col": 0, "render_action": "preserve"},
        ],
    }
    contract = build_v2_component_contract(
        "table", _table_tags(config, efficio_prompt_instruction="Complete the table")
    )
    cells = contract["output_schema"]["properties"]["cells"]
    assert list(cells["properties"]) == ["0,0", "1,0"]
    assert cells["required"] == ["0,0", "1,0"]
    assert cells["properties"]["1,0"]["anyOf"][1] == {"type": "null"}
    assert _valid(
        contract["output_schema"],
        {"cells": {"0,0": {"items": ["Northstar"]}, "1,0": None}},
    )
    assert not _valid(contract["output_schema"], {"cells": {"0,0": {"items": ["Northstar"]}}})
    description = cells["properties"]["0,0"]["description"]
    assert description.index("Complete the table") < description.index("Supplier identity")
    assert description.index("Supplier identity") < description.index("Use source wording")
    assert description.index("Use source wording") < description.rindex("Supplier")
    optional_schema = cells["properties"]["1,0"]
    optional_description = optional_schema["description"]
    optional_items = optional_schema["anyOf"][0]["properties"]["items"]
    assert optional_items["minItems"] == 1
    assert optional_items["maxItems"] == 2
    assert optional_items["items"]["minLength"] == 3
    assert optional_items["items"]["maxLength"] == 10
    assert "nullable because its row is optional" in optional_description
    assert "Return null for every render cell in this row" in optional_description
    assert "meaningful non-whitespace generated text" in optional_description
    assert "original first row remains" in optional_description
    assert "do not invent filler or placeholder content" in optional_description
    assert "authored content" not in optional_description
    assert optional_description.rfind("Aim for approximately") > optional_description.index(
        "nullable because its row is optional"
    )
    component_description = contract["output_schema"]["description"]
    assert component_description.startswith("Complete the table.")
    assert "A column-only optional cell may be null without removing its row" in component_description
    assert "original first row remains" in component_description
    assert "target_" not in json.dumps(contract)


def test_table_column_only_optional_cell_does_not_describe_row_removal() -> None:
    config = {
        "rows": [{"row": 0, "content_policy": "required"}],
        "columns": [{"col": 0, "content_policy": "optional"}],
        "cells": [{"row": 0, "col": 0, "render_action": "render"}],
    }

    contract = build_v2_component_contract("table", _table_tags(config))

    cell = contract["output_schema"]["properties"]["cells"]["properties"]["0,0"]
    assert cell["anyOf"][1] == {"type": "null"}
    description = cell["description"]
    assert "nullable because its column is optional" in description
    assert "this does not remove the row" in description
    assert "row is removed" not in description
    assert "authored content" not in description


def test_table_normalization_removes_only_optional_null_without_mutation() -> None:
    config = {
        "rows": [{"row": 1, "content_policy": "optional"}],
        "cells": [
            {"row": 0, "col": 0, "render_action": "render"},
            {"row": 1, "col": 0, "render_action": "render"},
        ],
    }
    contract = build_v2_component_contract("table", _table_tags(config))
    raw = {"cells": {"0,0": {"items": ["A"]}, "1,0": None}}
    before = copy.deepcopy(raw)
    assert normalize_v2_component_content(
        "table", raw, contract["normalization"]
    ) == {"cells": {"0,0": {"items": ["A"]}}}
    assert raw == before
    with pytest.raises(ValueError, match="0,0.*cannot be null"):
        normalize_v2_component_content(
            "table", {"cells": {"0,0": None}}, contract["normalization"]
        )


def test_table_semantics_enforce_per_cell_aggregate_budget() -> None:
    config = {
        "cells": [
            {
                "row": 0,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "max_chars": 5,
            }
        ]
    }
    contract = build_v2_component_contract("table", _table_tags(config))
    with pytest.raises(ValueError, match="maximum is 5"):
        validate_v2_component_semantics(
            "table", {"cells": {"0,0": {"items": ["abc", "def"]}}}, contract["normalization"]
        )


def test_table_with_no_render_cells_has_an_exact_empty_cells_object() -> None:
    contract = build_v2_component_contract(
        "table",
        _table_tags(
            {"cells": [{"row": 0, "col": 0, "render_action": "preserve"}]}
        ),
    )
    cells = contract["output_schema"]["properties"]["cells"]
    assert cells["properties"] == {}
    assert cells["required"] == []
    assert _valid(contract["output_schema"], {"cells": {}})
    assert contract["normalization"] == {"optional_cells": [], "max_chars": {}}


@pytest.mark.parametrize("optional", [False, True])
def test_table_rejects_impossible_non_null_cell_budget_without_changing_v1(
    optional: bool,
) -> None:
    config = {
        "rows": [{"row": 0, "content_policy": "optional" if optional else "required"}],
        "cells": [
            {
                "row": 0,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "min_items": 2,
                "max_items": 3,
                "min_chars_per_item": 5,
                "max_chars_per_item": 20,
                "max_chars": 9,
            }
        ],
    }
    tags = _table_tags(config)

    build_validation_content_schema("table", tags)

    with pytest.raises(
        ValueError,
        match=r"table V2 cell '0,0' non-null contract.*max_chars 9.*require 10",
    ):
        build_v2_component_contract("table", tags)


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"optional_cells": [], "max_chars": {}, "extra": True},
        {"optional_cells": ["0,0", "0,0"], "max_chars": {}},
        {"optional_cells": ["01,0"], "max_chars": {}},
        {"optional_cells": [], "max_chars": {"bad": 10}},
        {"optional_cells": [], "max_chars": {"0,0": 0}},
    ],
)
def test_table_rejects_malformed_normalization(metadata: dict) -> None:
    with pytest.raises(ValueError, match="normalization"):
        normalize_v2_component_content("table", {"cells": {}}, metadata)


@pytest.mark.parametrize(
    ("category_mode", "series_mode"),
    [
        ("fixed", "fixed"),
        ("fixed", "ai_generated"),
        ("ai_generated", "fixed"),
        ("ai_generated", "ai_generated"),
    ],
)
def test_chart_supports_all_category_and_series_modes(
    category_mode: str, series_mode: str
) -> None:
    contract = build_v2_component_contract(
        "category_chart",
        _chart_tags(category_mode=category_mode, series_mode=series_mode),
    )
    series = {"values": [1.5, 2.5]}
    if series_mode == "ai_generated":
        series["name"] = "Spend"
    raw = {"series": [series]}
    if category_mode == "ai_generated":
        raw["categories"] = ["2025", "2026"]
    assert _valid(contract["output_schema"], raw)

    normalized = normalize_v2_component_content(
        "category_chart", raw, contract["normalization"]
    )
    assert normalized["categories"] == ["2025", "2026"]
    assert normalized["series"] == [{"name": "Spend", "values": [1.5, 2.5]}]
    assert raw is not normalized
    canonical = build_validation_content_schema(
        "category_chart",
        _chart_tags(category_mode=category_mode, series_mode=series_mode),
    )
    assert _valid(canonical, normalized)


def test_chart_normalization_metadata_is_explicit_and_target_free() -> None:
    fixed = build_v2_component_contract("category_chart", _chart_tags())
    assert fixed["normalization"] == {
        "category_mode": "fixed",
        "fixed_categories": ["2025", "2026"],
        "series_mode": "fixed",
        "fixed_series_names": ["Spend"],
    }
    generated = build_v2_component_contract(
        "category_chart",
        _chart_tags(category_mode="ai_generated", series_mode="ai_generated"),
    )
    assert generated["normalization"] == {
        "category_mode": "ai_generated",
        "fixed_categories": None,
        "series_mode": "ai_generated",
        "fixed_series_names": None,
    }
    assert "target" not in json.dumps(fixed["normalization"])


def test_chart_fixed_metadata_accepts_contract_valid_whitespace_labels() -> None:
    tags = _chart_tags()
    tags["efficio_categories"] = json.dumps([" ", "2026"])
    tags["efficio_series_names"] = json.dumps([" "])

    contract = build_v2_component_contract("category_chart", tags)

    assert contract["normalization"]["fixed_categories"] == [" ", "2026"]
    assert contract["normalization"]["fixed_series_names"] == [" "]


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {
            "category_mode": "fixed",
            "fixed_categories": ["A"],
            "series_mode": "fixed",
            "fixed_series_names": ["S"],
            "extra": True,
        },
        {
            "category_mode": "fixed",
            "fixed_categories": None,
            "series_mode": "fixed",
            "fixed_series_names": ["S"],
        },
        {
            "category_mode": "ai_generated",
            "fixed_categories": ["A"],
            "series_mode": "ai_generated",
            "fixed_series_names": None,
        },
        {
            "category_mode": "ai_generated",
            "fixed_categories": None,
            "series_mode": "fixed",
            "fixed_series_names": [],
        },
    ],
)
def test_chart_rejects_malformed_normalization(metadata: dict) -> None:
    with pytest.raises(ValueError, match="category-chart V2"):
        normalize_v2_component_content(
            "category_chart", {"series": []}, metadata
        )


@pytest.mark.parametrize(
    ("component_type", "metadata"),
    [
        ("text", {"max_chars": 20}),
        ("table", {"optional_cells": ["0,0"], "max_chars": {"0,0": 20}}),
        (
            "category_chart",
            {
                "category_mode": "fixed",
                "fixed_categories": ["A"],
                "series_mode": "ai_generated",
                "fixed_series_names": None,
            },
        ),
    ],
)
def test_public_normalization_validator_dispatches_valid_metadata(
    component_type: str, metadata: dict
) -> None:
    validate_v2_component_normalization(component_type, metadata)


def test_public_normalization_validator_rejects_invalid_metadata() -> None:
    with pytest.raises(ValueError, match="exactly max_chars"):
        validate_v2_component_normalization("text", {})


def test_generated_chart_schema_couples_category_and_value_counts() -> None:
    contract = build_v2_component_contract(
        "category_chart",
        _chart_tags(category_mode="ai_generated", series_mode="ai_generated"),
    )
    schema = contract["output_schema"]
    assert schema["type"] == "object"
    assert len(schema["oneOf"]) == 2
    valid = {
        "categories": ["A", "B", "C"],
        "series": [{"name": "Spend", "values": [1, 2, 3]}],
    }
    invalid = {
        "categories": ["A", "B", "C"],
        "series": [{"name": "Spend", "values": [1, 2]}],
    }
    assert _valid(schema, valid)
    assert not _valid(schema, invalid)

    canonical = build_validation_content_schema(
        "category_chart",
        _chart_tags(category_mode="ai_generated", series_mode="ai_generated"),
    )
    assert _valid(canonical, valid)
    assert not _valid(canonical, invalid)


@pytest.mark.parametrize("series_mode", ["fixed", "ai_generated"])
def test_generated_category_range_fails_before_branch_materialization(
    monkeypatch: pytest.MonkeyPatch, series_mode: str,
) -> None:
    from efficio_pptx_contracts import _structured_output_category_chart as chart_v2

    tags = _chart_tags(category_mode="ai_generated", series_mode=series_mode)
    tags["efficio_max_categories"] = "1000000"

    def fail_if_materialized(*_args, **_kwargs) -> dict:
        raise AssertionError("category branch was materialized")

    monkeypatch.setattr(chart_v2, "_chart_object_schema", fail_if_materialized)

    with pytest.raises(ValueError, match=r"999999 correlated schema branches.*at most 100"):
        build_v2_component_contract("category_chart", tags)


def test_single_generated_category_count_uses_direct_object_schema() -> None:
    tags = _chart_tags(category_mode="ai_generated", series_mode="fixed")
    tags["efficio_max_categories"] = "2"
    contract = build_v2_component_contract("category_chart", tags)
    assert contract["output_schema"]["type"] == "object"
    assert "oneOf" not in contract["output_schema"]


def test_chart_schema_enforces_numeric_type_and_sign_rule() -> None:
    tags = _chart_tags(allow_decimals=False, allow_negatives=False)
    contract = build_v2_component_contract(
        "category_chart",
        tags,
    )
    values = contract["output_schema"]["properties"]["series"]["items"]["properties"][
        "values"
    ]["items"]
    assert values == {"type": "integer", "minimum": 0}
    assert "non-negative whole-number" in contract["output_schema"]["description"]

    raw = {"series": [{"values": [-1, 2]}]}
    assert not _valid(contract["output_schema"], raw)
    normalized = normalize_v2_component_content(
        "category_chart", raw, contract["normalization"]
    )
    assert not _valid(build_validation_content_schema("category_chart", tags), normalized)


def test_targets_remain_chart_descriptions_not_hard_counts() -> None:
    tags = _chart_tags(category_mode="ai_generated", series_mode="ai_generated")
    tags["efficio_prompt_instruction"] = "Explain the verified trend"
    contract = build_v2_component_contract("category_chart", tags)
    prompt_schema = contract["output_schema"]
    root_description = prompt_schema["description"]
    assert root_description.startswith("Explain the verified trend.")
    assert "approximately 2 categories" in root_description
    assert "approximately 1 series" in root_description
    assert root_description.rfind("Aim for approximately") > root_description.index(
        "Return one positive or negative numeric value"
    )
    assert prompt_schema["properties"]["categories"]["minItems"] == 2
    assert prompt_schema["properties"]["categories"]["maxItems"] == 3
    assert prompt_schema["properties"]["series"]["minItems"] == 1
    assert prompt_schema["properties"]["series"]["maxItems"] == 2

    canonical = build_validation_content_schema(
        "category_chart",
        tags,
    )
    assert canonical["properties"]["categories"]["minItems"] == 2
    assert canonical["properties"]["categories"]["maxItems"] == 3
    assert canonical["properties"]["series"]["minItems"] == 1
    assert canonical["properties"]["series"]["maxItems"] == 2
    assert "target_" not in json.dumps(contract)


def test_every_registered_component_has_v2_support() -> None:
    fixtures = {
        "text": _text_tags(),
        "table": _table_tags({"cells": []}),
        "category_chart": _chart_tags(),
    }
    assert set(fixtures) == set(list_component_types())
    for component_type, tags in fixtures.items():
        assert build_v2_component_contract(component_type, tags)["component_type"] == component_type


@pytest.mark.parametrize(
    ("component_type", "tags"),
    [
        ("text", _text_tags(efficio_target_chars="90")),
        ("table", _table_tags({"cells": []})),
        ("category_chart", _chart_tags()),
    ],
)
def test_v2_projection_is_deterministic_and_does_not_mutate_tags(
    component_type: str, tags: dict[str, str]
) -> None:
    before = copy.deepcopy(tags)
    first = build_v2_component_contract(component_type, tags)
    second = build_v2_component_contract(component_type, tags)
    assert first == second
    assert tags == before


def test_unknown_component_fails_fast() -> None:
    with pytest.raises(UnknownComponentTypeError):
        build_v2_component_contract("missing", {})


@pytest.mark.parametrize(
    ("component_type", "tags"),
    [
        ("text", _text_tags()),
        (
            "table",
            _table_tags(
                {
                    "rows": [{"row": 0, "content_policy": "optional"}],
                    "cells": [
                        {
                            "row": 0,
                            "col": 0,
                            "render_action": "render",
                            "max_chars": 20,
                        }
                    ],
                }
            ),
        ),
        ("category_chart", _chart_tags()),
        (
            "category_chart",
            _chart_tags(category_mode="ai_generated", series_mode="ai_generated"),
        ),
    ],
)
def test_component_contract_coherence_accepts_emitted_shapes(
    component_type: str, tags: dict[str, str]
) -> None:
    contract = build_v2_component_contract(component_type, tags)
    validate_v2_component_contract_coherence(
        component_type,
        contract["output_schema"],
        contract["normalization"],
    )


def test_component_contract_coherence_rejects_another_component_shape() -> None:
    text = build_v2_component_contract("text", _text_tags())
    table = build_v2_component_contract("table", _table_tags({"cells": []}))

    with pytest.raises(ValueError, match="text V2 schema.*items"):
        validate_v2_component_contract_coherence(
            "text", table["output_schema"], text["normalization"]
        )


def test_table_contract_coherence_requires_nullable_metadata_alignment() -> None:
    contract = build_v2_component_contract(
        "table",
        _table_tags(
            {
                "rows": [{"row": 0, "content_policy": "optional"}],
                "cells": [
                    {"row": 0, "col": 0, "render_action": "render", "max_chars": 20}
                ],
            }
        ),
    )
    normalization = copy.deepcopy(contract["normalization"])
    normalization["optional_cells"] = []
    with pytest.raises(ValueError, match="nullable cell schemas.*optional_cells"):
        validate_v2_component_contract_coherence(
            "table", contract["output_schema"], normalization
        )

    normalization = copy.deepcopy(contract["normalization"])
    normalization["max_chars"]["9,9"] = 10
    with pytest.raises(ValueError, match="max_chars metadata.*declared"):
        validate_v2_component_contract_coherence(
            "table", contract["output_schema"], normalization
        )


@pytest.mark.parametrize(
    ("metadata_field", "replacement", "message"),
    [
        ("category_mode", "ai_generated", "properties do not match category mode"),
        ("series_mode", "ai_generated", "series item does not match series mode"),
    ],
)
def test_chart_contract_coherence_requires_mode_and_schema_alignment(
    metadata_field: str, replacement: str, message: str
) -> None:
    contract = build_v2_component_contract("category_chart", _chart_tags())
    normalization = copy.deepcopy(contract["normalization"])
    normalization[metadata_field] = replacement
    normalization[
        "fixed_categories" if metadata_field == "category_mode" else "fixed_series_names"
    ] = None

    with pytest.raises(ValueError, match=message):
        validate_v2_component_contract_coherence(
            "category_chart", contract["output_schema"], normalization
        )

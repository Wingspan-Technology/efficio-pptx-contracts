"""Data-bound component schemas keep only renderer-safe content rules."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from efficio_pptx_contracts import (
    UnknownComponentTypeError,
    build_data_bound_component_contract,
    normalize_data_bound_component_content,
    validate_data_bound_component_contract_coherence,
)


def _text_tags() -> dict[str, str]:
    return {
        "efficio_content_mode": "data_bound",
        "efficio_component_id": "summary",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "manual",
        "efficio_max_chars": "10",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "2",
        "efficio_max_chars_per_item": "5",
    }


def _table_tags() -> dict[str, str]:
    config = {
        "rows": [{"row": 1, "content_policy": "optional"}],
        "cells": [
            {
                "row": 0,
                "col": 0,
                "render_action": "render",
                "text_format": "plain",
                "max_chars": 5,
                "max_items": 1,
            },
            {
                "row": 1,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "min_items": 2,
                "max_items": 2,
                "max_chars_per_item": 3,
            },
            {"row": 2, "col": 0, "render_action": "preserve"},
        ],
    }
    return {
        "efficio_content_mode": "data_bound",
        "efficio_component_id": "facts",
        "efficio_component_type": "table",
        "efficio_table_config": json.dumps(config),
    }


def _chart_tags(category_mode: str, series_mode: str) -> dict[str, str]:
    tags = {
        "efficio_content_mode": "data_bound",
        "efficio_component_id": "trend",
        "efficio_component_type": "category_chart",
        "efficio_chart_type": "CLUSTERED_COLUMN",
        "efficio_category_mode": category_mode,
        "efficio_min_categories": "1",
        "efficio_max_categories": "1",
        "efficio_target_categories": "1",
        "efficio_series_mode": series_mode,
        "efficio_min_series": "1",
        "efficio_max_series": "1",
        "efficio_target_series": "1",
        "efficio_value_type": "number",
        "efficio_allow_negative_values": "false",
        "efficio_allow_decimal_values": "false",
    }
    if category_mode == "fixed":
        tags["efficio_categories"] = '["Q1", "Q2"]'
        tags["efficio_min_categories"] = "2"
        tags["efficio_max_categories"] = "2"
        tags["efficio_target_categories"] = "2"
    if series_mode == "fixed":
        tags["efficio_series_names"] = '["Revenue", "Cost"]'
        tags["efficio_min_series"] = "2"
        tags["efficio_max_series"] = "2"
        tags["efficio_target_series"] = "2"
    return tags


def _assert_schema_accepts(schema: dict[str, Any], content: dict[str, Any]) -> None:
    Draft202012Validator(schema).validate(content)


def test_text_contract_ignores_authored_size_and_count_limits() -> None:
    contract = build_data_bound_component_contract("text", _text_tags())
    schema = contract["submission_schema"]
    items = schema["properties"]["items"]

    assert items == {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
    }
    assert contract["normalization"] == {}
    content = {"items": ["far longer than five characters", "second item"]}
    _assert_schema_accepts(schema, content)
    assert normalize_data_bound_component_content("text", content, {}) == content


def test_table_contract_keeps_only_render_cells_and_optional_nullability() -> None:
    contract = build_data_bound_component_contract("table", _table_tags())
    cells_schema = contract["submission_schema"]["properties"]["cells"]

    assert list(cells_schema["properties"]) == ["0,0", "1,0"]
    assert cells_schema["required"] == ["0,0"]
    assert contract["normalization"] == {"optional_cells": ["1,0"]}
    assert "maxItems" not in cells_schema["properties"]["0,0"]["properties"]["items"]

    content = {
        "cells": {
            "0,0": {"items": ["one", "two", "three"]},
            "1,0": None,
        }
    }
    _assert_schema_accepts(contract["submission_schema"], content)
    assert normalize_data_bound_component_content("table", content, contract["normalization"]) == {
        "cells": {"0,0": {"items": ["one", "two", "three"]}}
    }


@pytest.mark.parametrize(
    ("category_mode", "series_mode"),
    [
        ("fixed", "fixed"),
        ("fixed", "ai_generated"),
        ("ai_generated", "fixed"),
        ("ai_generated", "ai_generated"),
    ],
)
def test_chart_contract_supports_all_axis_modes(category_mode: str, series_mode: str) -> None:
    contract = build_data_bound_component_contract(
        "category_chart", _chart_tags(category_mode, series_mode)
    )
    raw: dict[str, Any] = {"series": []}
    if category_mode == "ai_generated":
        raw["categories"] = ["Q1", "Q2", "Q3"]
    series_count = 2 if series_mode == "fixed" else 3
    for index in range(series_count):
        item: dict[str, Any] = {"values": [-1.5, 2.25]}
        if category_mode == "ai_generated":
            item["values"].append(3.75)
        if series_mode == "ai_generated":
            item["name"] = f"Series {index + 1}"
        raw["series"].append(item)

    _assert_schema_accepts(contract["submission_schema"], raw)
    normalized = normalize_data_bound_component_content(
        "category_chart", raw, contract["normalization"]
    )
    assert normalized["categories"] == (
        ["Q1", "Q2"] if category_mode == "fixed" else ["Q1", "Q2", "Q3"]
    )
    if series_mode == "fixed":
        assert [item["name"] for item in normalized["series"]] == ["Revenue", "Cost"]


def test_chart_normalization_rejects_category_value_dimension_mismatch() -> None:
    contract = build_data_bound_component_contract(
        "category_chart", _chart_tags("ai_generated", "ai_generated")
    )
    with pytest.raises(ValueError, match="values count must match categories"):
        normalize_data_bound_component_content(
            "category_chart",
            {
                "categories": ["Q1", "Q2"],
                "series": [{"name": "Revenue", "values": [1]}],
            },
            contract["normalization"],
        )


def test_contract_coherence_rejects_corrupted_schema_and_metadata() -> None:
    contract = build_data_bound_component_contract("table", _table_tags())
    schema = deepcopy(contract["submission_schema"])
    schema["properties"]["cells"]["required"] = ["0,0", "1,0"]

    with pytest.raises(ValueError, match="required and optional cells disagree"):
        validate_data_bound_component_contract_coherence("table", schema, contract["normalization"])


@pytest.mark.parametrize(
    ("component_type", "tags", "mutate"),
    [
        (
            "text",
            _text_tags(),
            lambda schema: schema.update(maxProperties=0),
        ),
        (
            "table",
            _table_tags(),
            lambda schema: schema["properties"]["cells"]["properties"]["0,0"]["properties"][
                "items"
            ].update(maxItems=1),
        ),
        (
            "category_chart",
            _chart_tags("ai_generated", "ai_generated"),
            lambda schema: schema["properties"]["series"].update(maxItems=1),
        ),
    ],
)
def test_contract_coherence_rejects_added_data_bound_limits(
    component_type: str,
    tags: dict[str, str],
    mutate,
) -> None:
    contract = build_data_bound_component_contract(component_type, tags)
    schema = deepcopy(contract["submission_schema"])
    mutate(schema)

    with pytest.raises(ValueError, match="invalid"):
        validate_data_bound_component_contract_coherence(
            component_type,
            schema,
            contract["normalization"],
        )


def test_data_bound_builders_do_not_mutate_tags_and_reject_unknown_types() -> None:
    tags = _text_tags()
    before = deepcopy(tags)
    build_data_bound_component_contract("text", tags)
    assert tags == before
    with pytest.raises(UnknownComponentTypeError):
        build_data_bound_component_contract("missing", {})

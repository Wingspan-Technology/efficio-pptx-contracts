"""Focused tests for typed V2 semantic findings and repair guidance."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest
from efficio_pptx_contracts import (
    V2ComponentRepairReason,
    V2ComponentSemanticFinding,
    V2SemanticRule,
    build_v2_component_contract,
    build_validation_content_schema,
    collect_v2_component_semantic_findings,
    collect_v2_table_cell_semantic_findings,
    format_v2_component_repair_instruction,
    validate_v2_component_semantics,
)


def _text_tags(*, max_chars: int = 10) -> dict[str, str]:
    return {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "summary",
        "efficio_component_type": "text",
        "efficio_text_format": "bullets",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": str(max_chars),
        "efficio_min_items": "2",
        "efficio_max_items": "4",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "20",
    }


def _text_contract(*, max_chars: int = 10) -> dict[str, object]:
    return build_v2_component_contract("text", _text_tags(max_chars=max_chars))


def _table_tags() -> dict[str, str]:
    config = {
        "rows": [{"row": 1, "content_policy": "optional"}],
        "cells": [
            {
                "row": 1,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "min_items": 1,
                "max_items": 3,
                "max_chars": 5,
            },
            {
                "row": 0,
                "col": 0,
                "render_action": "render",
                "text_format": "bullets",
                "min_items": 1,
                "max_items": 2,
                "max_chars": 4,
            },
            {"row": 0, "col": 1, "render_action": "render"},
        ],
    }
    return {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "facts",
        "efficio_component_type": "table",
        "efficio_table_config": json.dumps(config),
    }


def _table_contract() -> dict[str, object]:
    return build_v2_component_contract("table", _table_tags())


def test_finding_contract_is_immutable_and_bounded() -> None:
    finding = V2ComponentSemanticFinding(
        path=("items",),
        cell=None,
        rule=V2SemanticRule.AGGREGATE_CHARACTER_LIMIT,
        reason=V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT,
    )
    with pytest.raises(FrozenInstanceError):
        finding.cell = "0,0"  # type: ignore[misc]

    assert [rule.value for rule in V2SemanticRule] == ["aggregate_character_limit"]
    assert {reason.value for reason in V2ComponentRepairReason} == {
        "type",
        "required",
        "additional_property",
        "item_count",
        "item_length",
        "numeric_constraint",
        "aggregate_character_limit",
        "other",
    }


def test_text_returns_one_content_free_aggregate_finding() -> None:
    contract = _text_contract()
    findings = collect_v2_component_semantic_findings(
        "text",
        {"items": ["secret-value"]},
        contract["normalization"],  # type: ignore[arg-type]
    )

    assert findings == (
        V2ComponentSemanticFinding(
            path=("items",),
            cell=None,
            rule=V2SemanticRule.AGGREGATE_CHARACTER_LIMIT,
            reason=V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT,
        ),
    )
    assert "secret-value" not in repr(findings)
    assert collect_v2_component_semantic_findings(
        "text", {"items": ["12345", "67890"]}, contract["normalization"]  # type: ignore[arg-type]
    ) == ()


def test_table_findings_follow_artifact_limit_order_not_content_order() -> None:
    contract = _table_contract()
    findings = collect_v2_component_semantic_findings(
        "table",
        {
            "cells": {
                "0,1": {"items": ["ignored by semantics"]},
                "0,0": {"items": ["12345"]},
                "1,0": {"items": ["123456"]},
            }
        },
        contract["normalization"],  # type: ignore[arg-type]
    )

    assert [finding.cell for finding in findings] == ["1,0", "0,0"]
    assert [finding.path for finding in findings] == [
        ("cells", "1,0", "items"),
        ("cells", "0,0", "items"),
    ]


def test_table_cell_semantics_are_independent() -> None:
    contract = _table_contract()
    normalization = contract["normalization"]

    assert collect_v2_table_cell_semantic_findings(
        "1,0", {"items": ["123456"]}, normalization  # type: ignore[arg-type]
    )[0].cell == "1,0"
    assert collect_v2_table_cell_semantic_findings(
        "0,0", {"items": ["1234"]}, normalization  # type: ignore[arg-type]
    ) == ()
    assert collect_v2_table_cell_semantic_findings(
        "0,1", {"items": ["any schema-valid value"]}, normalization  # type: ignore[arg-type]
    ) == ()


def test_chart_has_no_component_owned_semantic_rule() -> None:
    normalization = {
        "category_mode": "fixed",
        "fixed_categories": ["2025"],
        "series_mode": "fixed",
        "fixed_series_names": ["Spend"],
    }
    content = {"categories": ["2025"], "series": [{"name": "Spend", "values": [1]}]}

    assert collect_v2_component_semantic_findings(
        "category_chart", content, normalization
    ) == ()


def test_repair_instructions_use_only_reason_and_trusted_limits() -> None:
    text = _text_contract(max_chars=10)
    table = _table_contract()
    text_schema = build_validation_content_schema("text", _text_tags(max_chars=10))
    text_normalization = text["normalization"]
    table_schema = build_validation_content_schema("table", _table_tags())
    table_normalization = table["normalization"]

    assert format_v2_component_repair_instruction(
        "text",
        V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT,
        text_schema,  # type: ignore[arg-type]
        text_normalization,  # type: ignore[arg-type]
        cell=None,
    ) == "The combined item length must not exceed 10 characters."
    assert format_v2_component_repair_instruction(
        "table",
        V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT,
        table_schema,  # type: ignore[arg-type]
        table_normalization,  # type: ignore[arg-type]
        cell="1,0",
    ) == "The combined item length must not exceed 5 characters."
    assert format_v2_component_repair_instruction(
        "text",
        V2ComponentRepairReason.ITEM_COUNT,
        text_schema,  # type: ignore[arg-type]
        text_normalization,  # type: ignore[arg-type]
        cell=None,
    ) == "Return 2–4 items."

    for reason in V2ComponentRepairReason:
        instruction = format_v2_component_repair_instruction(
            "text",
            reason,
            text_schema,  # type: ignore[arg-type]
            text_normalization,  # type: ignore[arg-type]
            cell=None,
        )
        assert instruction
        assert "secret-value" not in instruction


def test_existing_exception_validator_keeps_its_contract() -> None:
    text = _text_contract(max_chars=10)
    with pytest.raises(
        ValueError,
        match=r"text V2 content at /items uses 11 characters; maximum is 10",
    ):
        validate_v2_component_semantics(
            "text",
            {"items": ["123456", "12345"]},
            text["normalization"],  # type: ignore[arg-type]
        )

    table = _table_contract()
    with pytest.raises(
        ValueError,
        match=r"table V2 content at /cells/1,0/items uses 6 characters; maximum is 5",
    ):
        validate_v2_component_semantics(
            "table",
            {"cells": {"1,0": {"items": ["123456"]}}},
            table["normalization"],  # type: ignore[arg-type]
        )

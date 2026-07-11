"""Tests for build_validation_content_schema (DMS validation.json schemas)."""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

from efficio_ppt_components import (
    UnknownComponentTypeError,
    build_validation_content_schema,
    list_component_types,
)


def _text_tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "title_1",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "120",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "60",
    }
    tags.update(overrides)
    return tags


def _table_tags(config: dict) -> dict[str, str]:
    return {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "table_1",
        "efficio_component_type": "table",
        "efficio_table_config": json.dumps(config),
    }


def _is_valid(schema: dict, content: dict) -> bool:
    return Draft202012Validator(schema).is_valid(content)


# ── text ─────────────────────────────────────────────────────────────────────


def test_text_plain_caps_items_at_one() -> None:
    schema = build_validation_content_schema("text", _text_tags())
    items = schema["properties"]["items"]
    assert items["minItems"] == 1
    assert items["maxItems"] == 1
    assert _is_valid(schema, {"items": ["one line"]})
    assert not _is_valid(schema, {"items": ["one", "two"]})
    assert not _is_valid(schema, {"items": []})


def test_text_list_formats_bound_items_by_min_and_max_items() -> None:
    for text_format in ("paragraph", "bullets", "numbered_list"):
        schema = build_validation_content_schema(
            "text",
            _text_tags(efficio_text_format=text_format, efficio_min_items="1", efficio_max_items="3"),
        )
        items = schema["properties"]["items"]
        assert items["minItems"] == 1
        assert items["maxItems"] == 3
        assert _is_valid(schema, {"items": ["a", "b", "c"]})
        assert not _is_valid(schema, {"items": ["a", "b", "c", "d"]})


def test_text_per_item_length_bounds_from_min_max_chars_per_item() -> None:
    schema = build_validation_content_schema(
        "text", _text_tags(efficio_min_chars_per_item="5", efficio_max_chars_per_item="40")
    )
    item = schema["properties"]["items"]["items"]
    assert item["minLength"] == 5
    assert item["maxLength"] == 40
    # Every item is bounded: over max or under min fails.
    assert not _is_valid(schema, {"items": ["x" * 41]})
    assert _is_valid(schema, {"items": ["x" * 40]})
    assert not _is_valid(schema, {"items": ["x" * 4]})
    assert _is_valid(schema, {"items": ["x" * 5]})


def test_text_schema_ignores_target_tags() -> None:
    # target_chars / target_chars_per_item are AI sizing guidance, never content
    # bounds: they must not appear in or change the validation.json schema.
    base = build_validation_content_schema("text", _text_tags())
    with_targets = build_validation_content_schema(
        "text", _text_tags(efficio_target_chars="45", efficio_target_chars_per_item="20")
    )
    assert with_targets == base
    assert "target" not in json.dumps(with_targets)


def test_text_schema_matches_documented_contract_shape() -> None:
    # Pure validation keywords: no identity, prose, raw tags, or internals.
    schema = build_validation_content_schema(
        "text",
        _text_tags(
            efficio_text_format="paragraph",
            efficio_min_items="1",
            efficio_max_items="3",
            efficio_min_chars_per_item="5",
            efficio_max_chars_per_item="30",
        ),
    )
    assert schema == {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"type": "string", "minLength": 5, "maxLength": 30},
            }
        },
    }


@pytest.mark.parametrize(
    "missing",
    [
        "efficio_text_format",
        "efficio_min_items",
        "efficio_max_items",
        "efficio_min_chars_per_item",
        "efficio_max_chars_per_item",
    ],
)
def test_text_missing_limit_tag_fails_clearly(missing: str) -> None:
    tags = _text_tags()
    del tags[missing]
    with pytest.raises(ValueError, match=missing):
        build_validation_content_schema("text", tags)


@pytest.mark.parametrize("bad", ["0", "-3", "3.5", "abc", " "])
def test_text_invalid_limit_value_fails_clearly(bad: str) -> None:
    with pytest.raises(ValueError, match="efficio_max_items"):
        build_validation_content_schema("text", _text_tags(efficio_max_items=bad))


def test_text_unknown_format_fails_clearly() -> None:
    with pytest.raises(ValueError, match="efficio_text_format"):
        build_validation_content_schema("text", _text_tags(efficio_text_format="prose"))


# ── table ────────────────────────────────────────────────────────────────────


def _render_cell(row: int, col: int, **extra) -> dict:
    return {"row": row, "col": col, "render_action": "render", **extra}


def test_table_includes_only_render_cells() -> None:
    config = {
        "cells": [
            {"row": 0, "col": 0},  # default-preserve -> omitted
            {"row": 0, "col": 1, "render_action": "preserve"},  # omitted
            _render_cell(1, 0),
            _render_cell(1, 1),
        ]
    }
    schema = build_validation_content_schema("table", _table_tags(config))
    cells = schema["properties"]["cells"]
    assert cells["type"] == "object"
    assert cells["additionalProperties"] is False
    assert list(cells["properties"]) == ["1,0", "1,1"]
    # Preserve/default-preserve coordinates are not allowed in content.
    assert not _is_valid(schema, {"cells": {"0,0": {"items": ["x"]}}})


def test_table_all_preserve_cells_allows_no_content_cells() -> None:
    config = {"cells": [{"row": 0, "col": 0}, {"row": 0, "col": 1, "render_action": "preserve"}]}
    schema = build_validation_content_schema("table", _table_tags(config))
    cells = schema["properties"]["cells"]
    assert cells["type"] == "object"
    assert cells["properties"] == {}
    assert cells["additionalProperties"] is False
    assert _is_valid(schema, {"cells": {}})
    assert not _is_valid(schema, {"cells": {"0,0": {"items": ["x"]}}})


def test_table_emits_keyed_render_cells() -> None:
    schema = build_validation_content_schema(
        "table", _table_tags({"cells": [_render_cell(2, 3, text_format="plain")]})
    )
    cells = schema["properties"]["cells"]
    assert set(cells["properties"]) == {"2,3"}
    cell_schema = cells["properties"]["2,3"]
    assert cell_schema["required"] == ["items"]
    assert cell_schema["additionalProperties"] is False
    assert set(cell_schema["properties"]) == {"items"}
    # A coordinate outside the allowed set is rejected by name (additionalProperties).
    assert not _is_valid(schema, {"cells": {"9,9": {"items": ["x"]}}})


def test_table_required_render_cell_is_required_key() -> None:
    schema = build_validation_content_schema(
        "table", _table_tags({"cells": [_render_cell(0, 1)]})
    )
    cells = schema["properties"]["cells"]
    assert cells["required"] == ["0,1"]
    # Required cell must be present; a duplicate coordinate is unrepresentable as a key.
    assert not _is_valid(schema, {"cells": {}})
    assert _is_valid(schema, {"cells": {"0,1": {"items": ["x"]}}})


def test_table_optional_row_or_column_policy_relaxes_requiredness() -> None:
    config = {
        "rows": [{"row": 0, "content_policy": "optional"}],
        "columns": [{"col": 2, "content_policy": "optional"}],
        "cells": [_render_cell(0, 0), _render_cell(1, 2), _render_cell(1, 0)],
    }
    schema = build_validation_content_schema("table", _table_tags(config))
    cells = schema["properties"]["cells"]
    assert set(cells["properties"]) == {"0,0", "1,2", "1,0"}
    # Only the fully-required cell (required row + required column) is required.
    assert cells["required"] == ["1,0"]
    # Optional cells may be omitted.
    assert _is_valid(schema, {"cells": {"1,0": {"items": ["x"]}}})
    # A preserve/unknown coordinate is still rejected by name.
    assert not _is_valid(schema, {"cells": {"1,0": {"items": ["x"]}, "5,5": {"items": ["y"]}}})


def test_table_cell_item_limits() -> None:
    config = {
        "cells": [
            _render_cell(0, 0, text_format="plain", max_lines=5),
            _render_cell(0, 1, text_format="bullets", max_lines=4),
            _render_cell(0, 2, text_format="bullets", max_chars_per_item=50, max_chars_per_line=30),
            _render_cell(0, 3, text_format="bullets"),
        ]
    }
    schema = build_validation_content_schema("table", _table_tags(config))
    props = schema["properties"]["cells"]["properties"]
    plain = props["0,0"]["properties"]["items"]
    bullets = props["0,1"]["properties"]["items"]
    limited = props["0,2"]["properties"]["items"]
    unlimited = props["0,3"]["properties"]["items"]
    assert plain["maxItems"] == 1  # plain wins over max_lines
    assert bullets["maxItems"] == 4
    assert limited["items"]["maxLength"] == 30  # stricter limit
    assert "maxItems" not in unlimited
    assert "maxLength" not in unlimited["items"]


def test_table_cell_violation_reports_exact_cell_and_item_path() -> None:
    # A too-long item in a render cell fails at its own precise path — the point of
    # the keyed shape (vs the old oneOf collapsing to a misleading row/col const error).
    schema = build_validation_content_schema(
        "table",
        _table_tags({"cells": [_render_cell(3, 1, text_format="bullets", max_chars_per_item=4)]}),
    )
    errors = sorted(
        Draft202012Validator(schema).iter_errors({"cells": {"3,1": {"items": ["xxxxx"]}}}),
        key=lambda e: list(e.absolute_path),
    )
    assert errors, "expected a validation error"
    first = errors[0]
    assert list(first.absolute_path) == ["cells", "3,1", "items", 0]
    assert first.validator == "maxLength"


def test_table_duplicate_config_coordinates_fail_clearly() -> None:
    config = {"cells": [_render_cell(0, 0), _render_cell(0, 0)]}
    with pytest.raises(ValueError, match="duplicate cell"):
        build_validation_content_schema("table", _table_tags(config))


def test_table_invalid_config_fails_clearly() -> None:
    with pytest.raises(ValueError, match="efficio_table_config"):
        build_validation_content_schema(
            "table", {**_table_tags({"cells": []}), "efficio_table_config": "{not json"}
        )
    with pytest.raises(ValueError, match="cells"):
        build_validation_content_schema("table", _table_tags({}))
    with pytest.raises(ValueError, match="efficio_table_config"):
        build_validation_content_schema("table", {"efficio_component_type": "table"})


# ── category_chart ─────────────────────────────────────────────────────────


def _chart_config(**overrides: object) -> dict:
    """A valid category_chart config; counts auto-derived to stay consistent.

    Fixed axes default their min/max/target to the label-array length; AI-
    generated axes get small default ranges. Explicit overrides win.
    """
    config: dict = {
        "chart_type": "CLUSTERED_COLUMN",
        "category_mode": "fixed",
        "categories": ["Q1", "Q2", "Q3"],
        "series_mode": "fixed",
        "series_names": ["Revenue"],
        "value_type": "number",
        "allow_negative_values": True,
        "allow_decimal_values": True,
    }
    config.update(overrides)
    if config["category_mode"] == "fixed":
        count = len(config["categories"])
        for key in ("min_categories", "max_categories", "target_categories"):
            config.setdefault(key, count)
    else:
        config.pop("categories", None)
        config.setdefault("min_categories", 2)
        config.setdefault("max_categories", 4)
        config.setdefault("target_categories", 3)
    if config["series_mode"] == "fixed":
        count = len(config["series_names"])
        config.setdefault("min_series", 1)
        config.setdefault("max_series", max(count, 1))
        config.setdefault("target_series", count)
    else:
        config.pop("series_names", None)
        config.setdefault("min_series", 1)
        config.setdefault("max_series", 3)
        config.setdefault("target_series", 2)
    return config


def _chart_flat_tags(**overrides: object) -> dict[str, str]:
    config = _chart_config(**overrides)
    tags = {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "chart_1",
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


def _chart_schema(**overrides: object) -> dict:
    return build_validation_content_schema("category_chart", _chart_flat_tags(**overrides))


def test_category_chart_requires_the_flat_tags() -> None:
    with pytest.raises(ValueError, match="category_chart tags are invalid"):
        build_validation_content_schema(
            "category_chart", {"efficio_component_type": "category_chart"}
        )


def test_category_chart_rejects_invalid_config() -> None:
    # Structural (bad enum) and semantic (bad ordering) failures both raise.
    with pytest.raises(ValueError, match="category_chart tags are invalid"):
        _chart_schema(chart_type="PIE")
    with pytest.raises(ValueError, match="category_chart tags are invalid"):
        _chart_schema(
            category_mode="ai_generated", min_categories=5, max_categories=3, target_categories=4
        )


def test_category_chart_emits_pure_validation_keywords() -> None:
    schema = _chart_schema()
    text = json.dumps(schema)
    assert "description" not in text
    assert "efficio_" not in text
    assert "component_type" not in text
    assert "$schema" not in text
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["series"]


def test_fixed_categories_fixed_single_series() -> None:
    schema = _chart_schema(categories=["Q1", "Q2", "Q3"], series_names=["Revenue"])
    assert _is_valid(schema, {"series": [{"values": [1, 2, 3]}]})  # name may be omitted
    assert _is_valid(schema, {"series": [{"name": "Revenue", "values": [1, 2, 3]}]})
    assert not _is_valid(schema, {"series": [{"name": "Sales", "values": [1, 2, 3]}]})  # wrong name
    assert not _is_valid(schema, {"series": [{"values": [1, 2]}]})  # wrong values length
    # Fixed categories may be omitted, but if present must match exactly.
    assert _is_valid(schema, {"categories": ["Q1", "Q2", "Q3"], "series": [{"values": [1, 2, 3]}]})
    assert not _is_valid(schema, {"categories": ["Q1", "Q2"], "series": [{"values": [1, 2, 3]}]})


def test_fixed_single_series_rejects_extra_series() -> None:
    schema = _chart_schema(categories=["Q1", "Q2"], series_names=["Revenue"])
    assert _is_valid(schema, {"series": [{"values": [1, 2]}]})
    # Exactly one series is allowed; a second one is rejected.
    assert not _is_valid(schema, {"series": [{"values": [1, 2]}, {"values": [3, 4]}]})


def test_fixed_categories_fixed_multiple_series_require_names_by_index() -> None:
    schema = _chart_schema(categories=["Q1", "Q2"], series_names=["Plan", "Actual"], max_series=3)
    assert _is_valid(
        schema,
        {"series": [{"name": "Plan", "values": [1, 2]}, {"name": "Actual", "values": [3, 4]}]},
    )
    # Names are positional; swapping them fails.
    assert not _is_valid(
        schema,
        {"series": [{"name": "Actual", "values": [1, 2]}, {"name": "Plan", "values": [3, 4]}]},
    )
    # Name is required for multi-series; count is exact.
    assert not _is_valid(
        schema, {"series": [{"values": [1, 2]}, {"name": "Actual", "values": [3, 4]}]}
    )
    assert not _is_valid(schema, {"series": [{"name": "Plan", "values": [1, 2]}]})


def test_fixed_categories_ai_generated_series() -> None:
    schema = _chart_schema(
        categories=["Q1", "Q2"], series_mode="ai_generated", min_series=2, max_series=3
    )
    assert _is_valid(
        schema, {"series": [{"name": "A", "values": [1, 2]}, {"name": "B", "values": [3, 4]}]}
    )
    # Generated names are required and non-empty.
    assert not _is_valid(
        schema, {"series": [{"values": [1, 2]}, {"name": "B", "values": [3, 4]}]}
    )
    assert not _is_valid(
        schema, {"series": [{"name": "", "values": [1, 2]}, {"name": "B", "values": [3, 4]}]}
    )
    # Series min/max are enforced.
    assert not _is_valid(schema, {"series": [{"name": "A", "values": [1, 2]}]})
    assert not _is_valid(
        schema, {"series": [{"name": n, "values": [1, 2]} for n in "ABCD"]}
    )


def test_ai_generated_categories_fixed_series_couple_lengths() -> None:
    schema = _chart_schema(
        category_mode="ai_generated", min_categories=2, max_categories=4, series_names=["Revenue"]
    )
    assert not _is_valid(schema, {"series": [{"values": [1, 2]}]})  # categories required
    assert _is_valid(schema, {"categories": ["a", "b", "c"], "series": [{"values": [1, 2, 3]}]})
    assert not _is_valid(schema, {"categories": ["a"], "series": [{"values": [1]}]})  # below min
    assert not _is_valid(
        schema, {"categories": list("abcde"), "series": [{"values": [1, 2, 3, 4, 5]}]}
    )  # above max
    # values length must equal the chosen category count.
    assert not _is_valid(schema, {"categories": ["a", "b", "c"], "series": [{"values": [1, 2]}]})


def test_ai_generated_categories_with_fixed_multiple_series() -> None:
    schema = _chart_schema(
        category_mode="ai_generated",
        min_categories=2,
        max_categories=3,
        series_names=["Plan", "Actual"],
    )
    # The AI picks the category count; positional names and each series' value
    # length are pinned to it.
    assert _is_valid(
        schema,
        {
            "categories": ["a", "b", "c"],
            "series": [{"name": "Plan", "values": [1, 2, 3]}, {"name": "Actual", "values": [4, 5, 6]}],
        },
    )
    assert _is_valid(
        schema,
        {
            "categories": ["a", "b"],
            "series": [{"name": "Plan", "values": [1, 2]}, {"name": "Actual", "values": [3, 4]}],
        },
    )
    # Positional names are enforced (swapping fails).
    assert not _is_valid(
        schema,
        {
            "categories": ["a", "b", "c"],
            "series": [{"name": "Actual", "values": [1, 2, 3]}, {"name": "Plan", "values": [4, 5, 6]}],
        },
    )
    # Every series' value length must match the chosen category count.
    assert not _is_valid(
        schema,
        {
            "categories": ["a", "b", "c"],
            "series": [{"name": "Plan", "values": [1, 2, 3]}, {"name": "Actual", "values": [4, 5]}],
        },
    )


def test_ai_generated_categories_and_series_enforced_together() -> None:
    schema = _chart_schema(
        category_mode="ai_generated",
        min_categories=2,
        max_categories=3,
        series_mode="ai_generated",
        min_series=1,
        max_series=2,
    )
    assert _is_valid(
        schema,
        {
            "categories": ["a", "b"],
            "series": [{"name": "S1", "values": [1, 2]}, {"name": "S2", "values": [3, 4]}],
        },
    )
    assert not _is_valid(
        schema, {"categories": list("abcd"), "series": [{"name": "S1", "values": [1, 2, 3, 4]}]}
    )  # categories above max
    assert not _is_valid(
        schema,
        {"categories": ["a", "b"], "series": [{"name": n, "values": [1, 2]} for n in "xyz"]},
    )  # series above max
    assert not _is_valid(
        schema, {"categories": ["a", "b"], "series": [{"name": "S1", "values": [1, 2, 3]}]}
    )  # values length mismatch


def test_decimals_rejected_when_disallowed() -> None:
    schema = _chart_schema(allow_decimal_values=False)
    assert _is_valid(schema, {"series": [{"values": [1, 2, 3]}]})
    assert not _is_valid(schema, {"series": [{"values": [1.5, 2, 3]}]})


def test_negatives_rejected_when_disallowed() -> None:
    schema = _chart_schema(allow_negative_values=False)
    assert _is_valid(schema, {"series": [{"values": [0, 2, 3]}]})
    assert not _is_valid(schema, {"series": [{"values": [-1, 2, 3]}]})


def test_non_numeric_values_are_rejected() -> None:
    schema = _chart_schema(categories=["Q1", "Q2", "Q3"])
    assert _is_valid(schema, {"series": [{"values": [1, 2, 3]}]})
    assert not _is_valid(schema, {"series": [{"values": [1, "two", 3]}]})
    assert not _is_valid(schema, {"series": [{"values": ["1", "2", "3"]}]})


def test_percent_stacked_rejects_negatives() -> None:
    # A valid percent-stacked config (negatives already disallowed) rejects them.
    schema = _chart_schema(chart_type="PERCENTS_STACKED_COLUMN", allow_negative_values=False)
    assert _is_valid(schema, {"series": [{"values": [0, 2, 3]}]})
    assert not _is_valid(schema, {"series": [{"values": [-1, 2, 3]}]})
    # Attempting to allow negatives on a percent-stacked chart is rejected outright.
    with pytest.raises(ValueError, match="percent-stacked"):
        _chart_schema(chart_type="PERCENTS_STACKED_BAR", allow_negative_values=True)


def test_category_chart_schemas_are_valid_json_schema() -> None:
    for schema in (
        _chart_schema(),
        _chart_schema(series_names=["Plan", "Actual"], max_series=3),
        _chart_schema(category_mode="ai_generated", min_categories=1, max_categories=4),
        _chart_schema(
            category_mode="ai_generated",
            series_mode="ai_generated",
            min_categories=2,
            max_categories=3,
            min_series=1,
            max_series=3,
        ),
        _chart_schema(allow_decimal_values=False, allow_negative_values=False),
    ):
        Draft202012Validator.check_schema(schema)


# ── scope ────────────────────────────────────────────────────────────────────


def test_every_registered_type_gets_a_schema() -> None:
    # Strict: build returns a schema (never None) for every registered type — no
    # registered-but-unsupported branch remains.
    assert set(list_component_types()) == {"category_chart", "table", "text"}
    assert build_validation_content_schema("text", _text_tags()) is not None
    assert build_validation_content_schema("table", _table_tags({"cells": []})) is not None
    assert _chart_schema() is not None


def test_unknown_component_type_raises() -> None:
    # A typo or not-yet-registered type must fail fast, not be silently omitted.
    with pytest.raises(UnknownComponentTypeError, match="not_a_component"):
        build_validation_content_schema("not_a_component", {})


# ── documented limitations & schema validity ─────────────────────────────────


def test_multi_item_text_does_not_enforce_aggregate_max_chars() -> None:
    # Documented limitation: for list formats the schema caps per-item length and
    # item count, but NOT the total characters across items[]. Three 10-char items
    # (sum 30) pass despite max_chars=10 — DMS enforces the aggregate later.
    schema = build_validation_content_schema(
        "text",
        _text_tags(
            efficio_text_format="bullets",
            efficio_max_chars="10",
            efficio_min_items="1",
            efficio_max_items="3",
            efficio_min_chars_per_item="1",
            efficio_max_chars_per_item="10",
        ),
    )
    assert schema["properties"]["items"]["items"]["maxLength"] == 10
    assert _is_valid(schema, {"items": ["x" * 10, "y" * 10, "z" * 10]})


def test_emitted_schemas_are_valid_json_schema() -> None:
    # Every emitted schema must itself be a valid Draft 2020-12 schema.
    Draft202012Validator.check_schema(build_validation_content_schema("text", _text_tags()))
    for text_format in ("paragraph", "bullets", "numbered_list"):
        Draft202012Validator.check_schema(
            build_validation_content_schema("text", _text_tags(efficio_text_format=text_format))
        )
    table_config = {
        "rows": [{"row": 0, "content_policy": "optional"}],
        "cells": [
            _render_cell(0, 0),
            _render_cell(1, 1, text_format="bullets", max_lines=3, max_chars_per_line=20),
            {"row": 2, "col": 2, "render_action": "preserve"},
        ],
    }
    Draft202012Validator.check_schema(
        build_validation_content_schema("table", _table_tags(table_config))
    )
    Draft202012Validator.check_schema(
        build_validation_content_schema("table", _table_tags({"cells": []}))
    )

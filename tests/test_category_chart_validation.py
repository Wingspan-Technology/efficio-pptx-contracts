"""Unit tests for category_chart cross-field flat-tag validation.

These exercise ``category_chart_issues`` directly: given flat chart tags (already
structurally valid per tag), assert the cross-field relationships and that each
issue attaches to the exact offending flat tag.
"""

from __future__ import annotations

import json

from efficio_ppt_components._category_chart_validation import category_chart_issues


def _tags(**overrides: str) -> dict[str, str]:
    tags = {
        "efficio_chart_type": "CLUSTERED_COLUMN",
        "efficio_category_mode": "fixed",
        "efficio_categories": json.dumps(["Q1", "Q2", "Q3", "Q4"]),
        "efficio_series_mode": "fixed",
        "efficio_series_names": json.dumps(["Plan", "Actual"]),
        "efficio_min_categories": "4",
        "efficio_max_categories": "4",
        "efficio_target_categories": "4",
        "efficio_min_series": "1",
        "efficio_max_series": "3",
        "efficio_target_series": "2",
        "efficio_value_type": "number",
        "efficio_allow_negative_values": "false",
        "efficio_allow_decimal_values": "true",
    }
    tags.update(overrides)
    return tags


def _codes(**overrides: str) -> list[tuple[str, str]]:
    return [(code, tag) for code, tag, _ in category_chart_issues(_tags(**overrides), ())]


def test_valid_tags_have_no_issues() -> None:
    assert category_chart_issues(_tags(), ()) == []


def test_category_target_below_min_attaches_to_target() -> None:
    assert ("target_below_min", "efficio_target_categories") in _codes(
        efficio_min_categories="3", efficio_target_categories="2", efficio_max_categories="5"
    )


def test_series_target_above_max_attaches_to_target() -> None:
    assert ("target_exceeds_max", "efficio_target_series") in _codes(
        efficio_min_series="1", efficio_target_series="9", efficio_max_series="3"
    )


def test_min_above_max_attaches_to_min() -> None:
    assert ("min_exceeds_max", "efficio_min_categories") in _codes(
        efficio_min_categories="5", efficio_target_categories="5", efficio_max_categories="4"
    )


def test_fixed_categories_length_outside_bounds_attaches_to_categories() -> None:
    # Four fixed labels but the bounds cap categories at 3.
    assert ("fixed_axis_length_out_of_bounds", "efficio_categories") in _codes(
        efficio_min_categories="1", efficio_target_categories="3", efficio_max_categories="3"
    )


def test_fixed_series_length_outside_bounds_attaches_to_series_names() -> None:
    assert ("fixed_axis_length_out_of_bounds", "efficio_series_names") in _codes(
        efficio_series_names=json.dumps(["A", "B", "C", "D"]),
        efficio_min_series="1",
        efficio_target_series="2",
        efficio_max_series="2",
    )


def test_fixed_mode_missing_labels_attaches_to_array_tag() -> None:
    tags = _tags()
    del tags["efficio_categories"]
    codes = [(c, t) for c, t, _ in category_chart_issues(tags, ())]
    assert ("fixed_axis_requires_labels", "efficio_categories") in codes


def test_ai_generated_mode_forbids_present_labels() -> None:
    # category_mode flips to ai_generated but the fixed labels are still supplied.
    assert ("ai_axis_forbids_labels", "efficio_categories") in _codes(
        efficio_category_mode="ai_generated"
    )


def test_ai_generated_modes_skip_fixed_length_checks() -> None:
    tags = _tags(efficio_category_mode="ai_generated", efficio_series_mode="ai_generated")
    del tags["efficio_categories"]
    del tags["efficio_series_names"]
    assert category_chart_issues(tags, ()) == []


def test_percent_stacked_with_negatives_attaches_to_allow_negative() -> None:
    assert ("percent_stacked_negative", "efficio_allow_negative_values") in _codes(
        efficio_chart_type="PERCENTS_STACKED_COLUMN", efficio_allow_negative_values="true"
    )


def test_percent_stacked_without_negatives_is_allowed() -> None:
    assert (
        category_chart_issues(
            _tags(efficio_chart_type="PERCENTS_STACKED_BAR", efficio_allow_negative_values="false"),
            (),
        )
        == []
    )


def test_non_percent_stacked_may_allow_negatives() -> None:
    assert (
        category_chart_issues(
            _tags(efficio_chart_type="CLUSTERED_BAR", efficio_allow_negative_values="true"), ()
        )
        == []
    )


def test_prior_structural_issue_skips_its_semantic_check() -> None:
    # A tag already flagged structurally is skipped, so there is no noisy follow-on.
    codes = [
        (c, t)
        for c, t, _ in category_chart_issues(
            _tags(efficio_min_categories="5", efficio_max_categories="4"),
            {"efficio_min_categories"},
        )
    ]
    assert ("min_exceeds_max", "efficio_min_categories") not in codes

"""Focused tests for the shared text and table-cell capacity model."""

from __future__ import annotations

import pytest

from efficio_pptx_contracts._text_capacity import (
    TextCapacity,
    build_text_items_schema,
    estimated_line_usage,
    text_capacity_metadata,
    text_capacity_description,
    text_capacity_issues,
)


def test_items_schema_keeps_structural_bounds_without_character_ceiling() -> None:
    capacity = TextCapacity(
        max_lines=4,
        estimated_chars_per_line=20,
        min_items=1,
        max_items=3,
        target_items=2,
    )

    assert build_text_items_schema(capacity, plain=False) == {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "minItems": 1,
        "maxItems": 3,
    }
    assert text_capacity_metadata(capacity) == {
        "max_lines": 4,
        "estimated_chars_per_line": 20,
    }


def test_plain_text_is_exactly_one_item() -> None:
    capacity = TextCapacity(
        max_lines=2,
        estimated_chars_per_line=40,
        min_items=1,
        max_items=1,
    )

    assert build_text_items_schema(capacity, plain=True)["maxItems"] == 1
    assert "exactly 1 semantic item" in text_capacity_description(capacity, plain=True)


def test_capacity_rejects_item_count_above_line_count() -> None:
    issues = text_capacity_issues(
        TextCapacity(
            max_lines=2,
            estimated_chars_per_line=40,
            min_items=1,
            max_items=3,
        ),
        plain=False,
    )

    assert [(issue.code, issue.field) for issue in issues] == [
        ("items_exceed_line_capacity", "max_items")
    ]


@pytest.mark.parametrize(
    ("capacity", "expected"),
    [
        (
            TextCapacity(
                max_lines=2,
                estimated_chars_per_line=10,
                min_chars=21,
                max_chars=30,
                min_items=1,
                max_items=2,
                min_chars_per_item=1,
                max_chars_per_item=30,
            ),
            ("minimum_chars_exceeds_line_capacity", "min_chars"),
        ),
        (
            TextCapacity(
                max_lines=3,
                estimated_chars_per_line=10,
                min_chars=1,
                max_chars=100,
                min_items=2,
                max_items=2,
                min_chars_per_item=15,
                max_chars_per_item=40,
            ),
            ("minimum_items_exceed_line_capacity", "min_items"),
        ),
    ],
)
def test_capacity_rejects_minimums_that_cannot_fit_available_lines(
    capacity: TextCapacity,
    expected: tuple[str, str],
) -> None:
    issues = text_capacity_issues(capacity, plain=False)

    assert [(issue.code, issue.field) for issue in issues] == [expected]


def test_estimated_lines_account_for_wrapping_items_and_explicit_breaks() -> None:
    assert estimated_line_usage(["12345", "123456"], chars_per_line=5) == 3
    assert estimated_line_usage(["one\ntwo"], chars_per_line=80) == 2
    assert estimated_line_usage(["one\r\ntwo\rthree"], chars_per_line=80) == 3
    assert estimated_line_usage([""], chars_per_line=80) == 1


def test_estimated_lines_count_unicode_code_points_deterministically() -> None:
    assert estimated_line_usage(["é" * 5, "🙂" * 5], chars_per_line=5) == 2
    assert estimated_line_usage(["🙂" * 6], chars_per_line=5) == 2


@pytest.mark.parametrize("chars_per_line", [0, -1, True])
def test_estimated_lines_reject_invalid_width(chars_per_line: int) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        estimated_line_usage(["valid"], chars_per_line=chars_per_line)


def test_estimated_lines_reject_non_string_items() -> None:
    with pytest.raises(ValueError, match="must be strings"):
        estimated_line_usage(["valid", 1], chars_per_line=20)  # type: ignore[list-item]

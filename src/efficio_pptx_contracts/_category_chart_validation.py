"""Cross-field category-chart tag validation (flat tags).

Pure logic mirroring :mod:`_text_sizing_validation`: given a raw tag map and the
set of tags that already carry a structural issue, return ``(code, tag_name,
message)`` tuples for the semantic problems JSON Schema cannot express across the
flat category-chart tags. The caller wraps these into its own issue type.

Per-tag structure (enum chart type/modes, positive-integer counts, non-empty
category/series labels) is owned by each tag's generated schema; the relationships
below cannot be expressed per tag, so they live here and attach to the exact
offending flat tag:

- ``min_* <= target_* <= max_*`` for categories and series;
- a fixed axis supplies its labels/names (present, count within min/max); an
  ai_generated axis must not supply them;
- percent-stacked chart types cannot allow negative values.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from typing import cast

CHART_TYPE_TAG = "efficio_chart_type"
CATEGORY_MODE_TAG = "efficio_category_mode"
SERIES_MODE_TAG = "efficio_series_mode"
CATEGORIES_TAG = "efficio_categories"
SERIES_NAMES_TAG = "efficio_series_names"
MIN_CATEGORIES_TAG = "efficio_min_categories"
MAX_CATEGORIES_TAG = "efficio_max_categories"
TARGET_CATEGORIES_TAG = "efficio_target_categories"
MIN_SERIES_TAG = "efficio_min_series"
MAX_SERIES_TAG = "efficio_max_series"
TARGET_SERIES_TAG = "efficio_target_series"
VALUE_TYPE_TAG = "efficio_value_type"
VALUE_UNIT_TAG = "efficio_value_unit"
ALLOW_NEGATIVE_TAG = "efficio_allow_negative_values"
ALLOW_DECIMAL_TAG = "efficio_allow_decimal_values"
CATEGORY_INSTRUCTION_TAG = "efficio_category_instruction"
SERIES_INSTRUCTION_TAG = "efficio_series_instruction"
COMPONENT_TYPE_TAG = "efficio_component_type"

# Every category_chart-specific flat tag. The component-agnostic shared tags
# (render_behavior, component_id, content_role, prompt_instruction) are validated
# elsewhere, so the per-instance content-schema builder scopes its check to these.
CATEGORY_CHART_TAG_NAMES = frozenset(
    {
        COMPONENT_TYPE_TAG, CHART_TYPE_TAG, CATEGORY_MODE_TAG, SERIES_MODE_TAG,
        CATEGORIES_TAG, SERIES_NAMES_TAG, MIN_CATEGORIES_TAG, MAX_CATEGORIES_TAG,
        TARGET_CATEGORIES_TAG, MIN_SERIES_TAG, MAX_SERIES_TAG, TARGET_SERIES_TAG,
        CATEGORY_INSTRUCTION_TAG, SERIES_INSTRUCTION_TAG, VALUE_TYPE_TAG, VALUE_UNIT_TAG,
        ALLOW_NEGATIVE_TAG, ALLOW_DECIMAL_TAG,
    }
)

FIXED_MODE = "fixed"
AI_GENERATED_MODE = "ai_generated"

PERCENT_STACKED_CHART_TYPES = frozenset({"PERCENTS_STACKED_COLUMN", "PERCENTS_STACKED_BAR"})

ChartIssue = tuple[str, str, str]
IntegerReader = Callable[[str], int | None]
LabelsReader = Callable[[str], list[object] | None]
PresenceCheck = Callable[[str], bool]


def category_chart_issues(
    tags: Mapping[str, str], prior_issue_tags: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Return ``(code, tag_name, message)`` for each cross-field chart violation.

    A check is skipped when an operand is missing/blank or already carries a
    structural issue, so a malformed value is reported once (structurally) with no
    noisy follow-on; the remaining values are known-good.
    """
    skip = set(prior_issue_tags)

    def as_int(tag: str) -> int | None:
        raw = tags.get(tag)
        if raw is None or not raw.strip() or tag in skip:
            return None
        raw = raw.strip()
        return int(raw) if raw.isdecimal() else None

    def as_labels(tag: str) -> list[object] | None:
        raw = tags.get(tag)
        if raw is None or not raw.strip() or tag in skip:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return cast(list[object], parsed) if isinstance(parsed, list) else None

    def present(tag: str) -> bool:
        raw = tags.get(tag)
        return raw is not None and bool(raw.strip())

    issues: list[tuple[str, str, str]] = []
    issues.extend(
        _count_order_issues(as_int, MIN_CATEGORIES_TAG, TARGET_CATEGORIES_TAG, MAX_CATEGORIES_TAG)
    )
    issues.extend(_count_order_issues(as_int, MIN_SERIES_TAG, TARGET_SERIES_TAG, MAX_SERIES_TAG))
    issues.extend(
        _axis_issues(
            tags.get(CATEGORY_MODE_TAG), CATEGORIES_TAG, CATEGORY_MODE_TAG,
            MIN_CATEGORIES_TAG, MAX_CATEGORIES_TAG, as_int, as_labels, present, skip,
        )
    )
    issues.extend(
        _axis_issues(
            tags.get(SERIES_MODE_TAG), SERIES_NAMES_TAG, SERIES_MODE_TAG,
            MIN_SERIES_TAG, MAX_SERIES_TAG, as_int, as_labels, present, skip,
        )
    )
    chart_type = tags.get(CHART_TYPE_TAG)
    if (
        chart_type in PERCENT_STACKED_CHART_TYPES
        and tags.get(ALLOW_NEGATIVE_TAG) == "true"
        and ALLOW_NEGATIVE_TAG not in skip
    ):
        issues.append(
            (
                "percent_stacked_negative",
                ALLOW_NEGATIVE_TAG,
                f"Tag {ALLOW_NEGATIVE_TAG} must be false for percent-stacked chart type {chart_type}.",
            )
        )
    return issues


def _count_order_issues(
    as_int: IntegerReader, min_tag: str, target_tag: str, max_tag: str
) -> list[ChartIssue]:
    minimum, target, maximum = as_int(min_tag), as_int(target_tag), as_int(max_tag)
    issues: list[tuple[str, str, str]] = []
    if minimum is not None and maximum is not None and minimum > maximum:
        issues.append(("min_exceeds_max", min_tag, f"Tag {min_tag} must not exceed {max_tag}."))
    if target is not None and minimum is not None and target < minimum:
        issues.append(("target_below_min", target_tag, f"Tag {target_tag} must be at least {min_tag}."))
    if target is not None and maximum is not None and target > maximum:
        issues.append(("target_exceeds_max", target_tag, f"Tag {target_tag} must not exceed {max_tag}."))
    return issues


def _axis_issues(
    mode: str | None,
    array_tag: str,
    mode_tag: str,
    min_tag: str,
    max_tag: str,
    as_int: IntegerReader,
    as_labels: LabelsReader,
    present: PresenceCheck,
    skip: set[str],
) -> list[ChartIssue]:
    issues: list[ChartIssue] = []
    if array_tag in skip:
        return issues  # a structural issue on the labels tag is already reported
    if mode == FIXED_MODE:
        if not present(array_tag):
            issues.append(
                ("fixed_axis_requires_labels", array_tag, f"Tag {array_tag} is required when {mode_tag} is fixed.")
            )
            return issues
        labels = as_labels(array_tag)
        minimum, maximum = as_int(min_tag), as_int(max_tag)
        if labels is not None and minimum is not None and maximum is not None:
            length = len(labels)
            if not minimum <= length <= maximum:
                issues.append(
                    (
                        "fixed_axis_length_out_of_bounds",
                        array_tag,
                        f"Tag {array_tag} has {length} entries but must have between {min_tag} and {max_tag}.",
                    )
                )
    elif mode == AI_GENERATED_MODE and present(array_tag):
        issues.append(
            ("ai_axis_forbids_labels", array_tag, f"Tag {array_tag} must be omitted when {mode_tag} is ai_generated.")
        )
    return issues

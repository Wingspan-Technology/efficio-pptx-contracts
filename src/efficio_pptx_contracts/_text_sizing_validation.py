"""Flat text-tag adapter for the shared estimated capacity model."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ._text_capacity import TextCapacity, text_capacity_issues as capacity_issues

_TEXT_FORMAT_TAG = "efficio_text_format"
_PLAIN_TEXT_FORMAT = "plain"
_MAX_LINES_TAG = "efficio_max_lines"
_ESTIMATED_CHARS_PER_LINE_TAG = "efficio_estimated_chars_per_line"
_MIN_ITEMS_TAG = "efficio_min_items"
_MAX_ITEMS_TAG = "efficio_max_items"
_TARGET_ITEMS_TAG = "efficio_target_items"

_REQUIRED_CAPACITY_TAGS = (
    _MAX_LINES_TAG,
    _ESTIMATED_CHARS_PER_LINE_TAG,
    _MIN_ITEMS_TAG,
    _MAX_ITEMS_TAG,
)


def text_sizing_issues(
    tags: Mapping[str, str], prior_issue_tags: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Return tag-scoped cross-field issues without duplicating structural errors."""
    skip = set(prior_issue_tags)
    values = {tag: _value(tags, tag, skip) for tag in _REQUIRED_CAPACITY_TAGS}
    if any(value is None for value in values.values()):
        return []
    capacity = TextCapacity(
        max_lines=values[_MAX_LINES_TAG],
        estimated_chars_per_line=values[_ESTIMATED_CHARS_PER_LINE_TAG],
        min_items=values[_MIN_ITEMS_TAG] or 1,
        max_items=values[_MAX_ITEMS_TAG],
        target_items=_value(tags, _TARGET_ITEMS_TAG, skip),
    )
    issues = capacity_issues(
        capacity,
        plain=tags.get(_TEXT_FORMAT_TAG) == _PLAIN_TEXT_FORMAT,
    )
    return [
        (
            issue.code,
            f"efficio_{issue.field}",
            f"Tag efficio_{issue.field}: {issue.message}",
        )
        for issue in issues
    ]


def text_capacity_from_tags(tags: Mapping[str, str]) -> TextCapacity:
    """Parse one text component's required positive capacity tags."""
    capacity = TextCapacity(
        max_lines=_required_positive(tags, _MAX_LINES_TAG),
        estimated_chars_per_line=_required_positive(
            tags, _ESTIMATED_CHARS_PER_LINE_TAG
        ),
        min_items=_required_positive(tags, _MIN_ITEMS_TAG),
        max_items=_required_positive(tags, _MAX_ITEMS_TAG),
        target_items=_optional_positive(tags, _TARGET_ITEMS_TAG),
    )
    issues = capacity_issues(
        capacity,
        plain=tags.get(_TEXT_FORMAT_TAG) == _PLAIN_TEXT_FORMAT,
    )
    if issues:
        raise ValueError("text tags are invalid: " + "; ".join(issue.message for issue in issues))
    return capacity


def _value(tags: Mapping[str, str], tag: str, skip: set[str]) -> int | None:
    raw = tags.get(tag)
    if raw is None or not raw.strip() or tag in skip:
        return None
    return int(raw.strip())


def _required_positive(tags: Mapping[str, str], tag: str) -> int:
    value = _optional_positive(tags, tag)
    if value is None:
        raise ValueError(f"text component requires positive integer tag {tag!r}")
    return value


def _optional_positive(tags: Mapping[str, str], tag: str) -> int | None:
    raw = tags.get(tag)
    if raw is None or not raw.strip():
        return None
    if not raw.isascii() or not raw.isdecimal() or int(raw) < 1:
        raise ValueError(
            f"text component tag {tag!r} must be a positive integer string"
        )
    return int(raw)

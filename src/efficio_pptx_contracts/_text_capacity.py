"""Shared strict text-capacity model for text components and table cells."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any


@dataclass(frozen=True, slots=True)
class TextCapacity:
    """Normalized strict character/item bounds and estimated line capacity."""

    max_lines: int | None
    estimated_chars_per_line: int | None
    min_chars: int | None = None
    max_chars: int | None = None
    min_items: int = 1
    max_items: int | None = None
    min_chars_per_item: int | None = None
    max_chars_per_item: int | None = None
    target_items: int | None = None

    @property
    def has_line_capacity(self) -> bool:
        return self.max_lines is not None and self.estimated_chars_per_line is not None

    @property
    def has_character_capacity(self) -> bool:
        return self.min_chars is not None and self.max_chars is not None

    @property
    def has_per_item_character_capacity(self) -> bool:
        return (
            self.min_chars_per_item is not None
            and self.max_chars_per_item is not None
        )

    def effective_max_items(self, *, plain: bool) -> int | None:
        if plain:
            return 1
        return self.max_items if self.max_items is not None else self.max_lines


@dataclass(frozen=True, slots=True)
class TextCapacityIssue:
    code: str
    field: str
    message: str


def text_capacity_issues(
    capacity: TextCapacity,
    *,
    plain: bool,
) -> tuple[TextCapacityIssue, ...]:
    """Return deterministic cross-field issues for one normalized capacity."""
    values = {
        "max_lines": capacity.max_lines,
        "estimated_chars_per_line": capacity.estimated_chars_per_line,
        "min_chars": capacity.min_chars,
        "max_chars": capacity.max_chars,
        "min_items": capacity.min_items,
        "max_items": capacity.max_items,
        "min_chars_per_item": capacity.min_chars_per_item,
        "max_chars_per_item": capacity.max_chars_per_item,
        "target_items": capacity.target_items,
    }
    for field, value in values.items():
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 1
        ):
            raise ValueError(f"text capacity {field} must be a positive integer")

    issues: list[TextCapacityIssue] = []
    has_lines = capacity.max_lines is not None
    has_width = capacity.estimated_chars_per_line is not None
    if has_lines != has_width:
        missing = "estimated_chars_per_line" if has_lines else "max_lines"
        issues.append(
            TextCapacityIssue(
                "incomplete_line_capacity",
                missing,
                "max_lines and estimated_chars_per_line must be provided together.",
            )
        )

    _append_pair_issues(
        issues,
        minimum=capacity.min_chars,
        maximum=capacity.max_chars,
        minimum_field="min_chars",
        maximum_field="max_chars",
        pair_code="incomplete_character_capacity",
    )
    _append_pair_issues(
        issues,
        minimum=capacity.min_chars_per_item,
        maximum=capacity.max_chars_per_item,
        minimum_field="min_chars_per_item",
        maximum_field="max_chars_per_item",
        pair_code="incomplete_per_item_character_capacity",
    )

    maximum = capacity.effective_max_items(plain=plain)
    if maximum is not None and capacity.min_items > maximum:
        issues.append(
            TextCapacityIssue(
                "min_exceeds_max",
                "min_items",
                "min_items must not exceed max_items.",
            )
        )
    if (
        capacity.max_lines is not None
        and capacity.max_items is not None
        and capacity.max_items > capacity.max_lines
    ):
        issues.append(
            TextCapacityIssue(
                "items_exceed_line_capacity",
                "max_items",
                "max_items must not exceed max_lines because every item consumes a line.",
            )
        )
    if capacity.target_items is not None:
        if capacity.target_items < capacity.min_items:
            issues.append(
                TextCapacityIssue(
                    "target_below_min",
                    "target_items",
                    "target_items must be at least min_items.",
                )
            )
        if maximum is not None and capacity.target_items > maximum:
            issues.append(
                TextCapacityIssue(
                    "target_exceeds_max",
                    "target_items",
                    "target_items must not exceed max_items.",
                )
            )
    if (
        capacity.max_chars is not None
        and capacity.min_chars_per_item is not None
        and capacity.min_items * capacity.min_chars_per_item > capacity.max_chars
    ):
        issues.append(
            TextCapacityIssue(
                "minimum_content_exceeds_max_chars",
                "max_chars",
                "max_chars must allow min_items at min_chars_per_item.",
            )
        )
    if (
        capacity.min_chars is not None
        and capacity.max_chars_per_item is not None
        and maximum is not None
        and capacity.min_chars > maximum * capacity.max_chars_per_item
    ):
        issues.append(
            TextCapacityIssue(
                "minimum_chars_exceeds_item_capacity",
                "min_chars",
                "min_chars must fit within max_items at max_chars_per_item.",
            )
        )
    if capacity.has_line_capacity:
        assert capacity.max_lines is not None
        assert capacity.estimated_chars_per_line is not None
        line_character_capacity = (
            capacity.max_lines * capacity.estimated_chars_per_line
        )
        if (
            capacity.min_chars is not None
            and capacity.min_chars > line_character_capacity
        ):
            issues.append(
                TextCapacityIssue(
                    "minimum_chars_exceeds_line_capacity",
                    "min_chars",
                    "min_chars must fit within max_lines at "
                    "estimated_chars_per_line.",
                )
            )
        if capacity.min_chars_per_item is not None:
            minimum_required_lines = capacity.min_items * ceil(
                capacity.min_chars_per_item / capacity.estimated_chars_per_line
            )
            if minimum_required_lines > capacity.max_lines:
                issues.append(
                    TextCapacityIssue(
                        "minimum_items_exceed_line_capacity",
                        "min_items",
                        "min_items at min_chars_per_item must fit within max_lines "
                        "at estimated_chars_per_line.",
                    )
                )
    if plain:
        if capacity.min_items != 1:
            issues.append(
                TextCapacityIssue(
                    "plain_requires_single_item",
                    "min_items",
                    "min_items must be 1 for plain text.",
                )
            )
        if capacity.max_items is not None and capacity.max_items != 1:
            issues.append(
                TextCapacityIssue(
                    "plain_requires_single_item",
                    "max_items",
                    "max_items must be 1 for plain text.",
                )
            )
        if capacity.target_items is not None:
            issues.append(
                TextCapacityIssue(
                    "plain_forbids_target_items",
                    "target_items",
                    "target_items is not valid for plain text, which is always one item.",
                )
            )
    return tuple(issues)


def build_text_items_schema(capacity: TextCapacity, *, plain: bool) -> dict[str, Any]:
    """Build the shared renderer-compatible ``items`` array schema."""
    _raise_capacity_issues(capacity, plain=plain)
    schema: dict[str, Any] = {
        "type": "array",
        "items": {
            "type": "string",
            "minLength": capacity.min_chars_per_item or 1,
        },
        "minItems": 1 if plain else capacity.min_items,
    }
    if capacity.max_chars_per_item is not None:
        schema["items"]["maxLength"] = capacity.max_chars_per_item
    maximum = capacity.effective_max_items(plain=plain)
    if maximum is not None:
        schema["maxItems"] = maximum
    return schema


def text_capacity_description(capacity: TextCapacity, *, plain: bool) -> str:
    """Build concise deterministic count and estimated-fit guidance."""
    _raise_capacity_issues(capacity, plain=plain)
    minimum = 1 if plain else capacity.min_items
    maximum = capacity.effective_max_items(plain=plain)
    parts = [_item_count_description(minimum, maximum)]
    if capacity.has_per_item_character_capacity:
        parts.append(
            f"Keep each item between {capacity.min_chars_per_item} and "
            f"{capacity.max_chars_per_item} characters"
        )
    if capacity.has_character_capacity:
        parts.append(
            f"Keep the combined length of all items between {capacity.min_chars} and "
            f"{capacity.max_chars} characters"
        )
    if capacity.has_line_capacity:
        parts.append(
            f"Fit all items within an estimated maximum of {capacity.max_lines} rendered "
            f"lines, using approximately {capacity.estimated_chars_per_line} characters "
            "per line to estimate wrapping; explicit line breaks consume lines and the "
            "result is an estimate rather than exact visual measurement"
        )
    if capacity.target_items is not None:
        parts.append(f"Aim for approximately {capacity.target_items} items")
    return ". ".join(parts) + "."


def estimated_line_usage(items: Sequence[str], *, chars_per_line: int) -> int:
    """Estimate rendered lines deterministically from semantic text items."""
    if not isinstance(chars_per_line, int) or isinstance(chars_per_line, bool) or chars_per_line < 1:
        raise ValueError("estimated characters per line must be a positive integer")
    total = 0
    for item in items:
        if not isinstance(item, str):
            raise ValueError("text capacity items must be strings")
        normalized = item.replace("\r\n", "\n").replace("\r", "\n")
        total += sum(max(1, ceil(len(segment) / chars_per_line)) for segment in normalized.split("\n"))
    return total


def validate_text_capacity_metadata(
    value: Mapping[str, object],
) -> tuple[int | None, int | None, int | None, int | None]:
    """Validate private line and aggregate-character metadata."""
    allowed = {"max_lines", "estimated_chars_per_line", "min_chars", "max_chars"}
    if not set(value) <= allowed or not value:
        raise ValueError("text capacity metadata fields are invalid")
    parsed: dict[str, int | None] = {}
    for field in allowed:
        raw = value.get(field)
        if raw is not None and (
            not isinstance(raw, int) or isinstance(raw, bool) or raw < 1
        ):
            raise ValueError("text capacity metadata values must be positive integers")
        parsed[field] = raw
    if (parsed["max_lines"] is None) != (
        parsed["estimated_chars_per_line"] is None
    ):
        raise ValueError("text capacity metadata line fields must be provided together")
    if (parsed["min_chars"] is None) != (parsed["max_chars"] is None):
        raise ValueError(
            "text capacity metadata character fields must be provided together"
        )
    if (
        parsed["min_chars"] is not None
        and parsed["max_chars"] is not None
        and parsed["min_chars"] > parsed["max_chars"]
    ):
        raise ValueError("text capacity metadata min_chars must not exceed max_chars")
    return (
        parsed["max_lines"],
        parsed["estimated_chars_per_line"],
        parsed["min_chars"],
        parsed["max_chars"],
    )


def text_capacity_metadata(capacity: TextCapacity) -> dict[str, int] | None:
    """Project private metadata for semantic limits not expressible in schema."""
    metadata: dict[str, int] = {}
    if capacity.has_line_capacity:
        assert capacity.max_lines is not None
        assert capacity.estimated_chars_per_line is not None
        metadata.update(
            max_lines=capacity.max_lines,
            estimated_chars_per_line=capacity.estimated_chars_per_line,
        )
    if capacity.has_character_capacity:
        assert capacity.min_chars is not None
        assert capacity.max_chars is not None
        metadata.update(min_chars=capacity.min_chars, max_chars=capacity.max_chars)
    if not metadata:
        return None
    return metadata


def _raise_capacity_issues(capacity: TextCapacity, *, plain: bool) -> None:
    issues = text_capacity_issues(capacity, plain=plain)
    if issues:
        raise ValueError("invalid text capacity: " + "; ".join(issue.message for issue in issues))


def _item_count_description(minimum: int, maximum: int | None) -> str:
    if maximum == minimum:
        noun = "item" if minimum == 1 else "items"
        return f"Return exactly {minimum} semantic {noun}"
    if maximum is None:
        noun = "item" if minimum == 1 else "items"
        return f"Return at least {minimum} semantic {noun}"
    return f"Return {minimum}–{maximum} semantic items"


def _append_pair_issues(
    issues: list[TextCapacityIssue],
    *,
    minimum: int | None,
    maximum: int | None,
    minimum_field: str,
    maximum_field: str,
    pair_code: str,
) -> None:
    if (minimum is None) != (maximum is None):
        missing = maximum_field if minimum is not None else minimum_field
        issues.append(
            TextCapacityIssue(
                pair_code,
                missing,
                f"{minimum_field} and {maximum_field} must be provided together.",
            )
        )
    elif minimum is not None and maximum is not None and minimum > maximum:
        issues.append(
            TextCapacityIssue(
                "min_exceeds_max",
                minimum_field,
                f"{minimum_field} must not exceed {maximum_field}.",
            )
        )

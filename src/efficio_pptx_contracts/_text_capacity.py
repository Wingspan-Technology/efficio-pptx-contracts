"""Shared estimated text-capacity model for text components and table cells."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil
from typing import Any


@dataclass(frozen=True, slots=True)
class TextCapacity:
    """Normalized item bounds and optional estimated rendered-line capacity."""

    max_lines: int | None
    estimated_chars_per_line: int | None
    min_items: int = 1
    max_items: int | None = None
    target_items: int | None = None

    @property
    def has_line_capacity(self) -> bool:
        return self.max_lines is not None and self.estimated_chars_per_line is not None

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
        "min_items": capacity.min_items,
        "max_items": capacity.max_items,
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
        "items": {"type": "string", "minLength": 1},
        "minItems": 1 if plain else capacity.min_items,
    }
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


def validate_line_capacity_metadata(value: Mapping[str, object]) -> tuple[int, int]:
    """Validate private line-capacity metadata and return its two values."""
    if set(value) != {"max_lines", "estimated_chars_per_line"}:
        raise ValueError(
            "text capacity metadata must contain exactly max_lines and "
            "estimated_chars_per_line"
        )
    maximum = value["max_lines"]
    width = value["estimated_chars_per_line"]
    if (
        not isinstance(maximum, int)
        or isinstance(maximum, bool)
        or maximum < 1
        or not isinstance(width, int)
        or isinstance(width, bool)
        or width < 1
    ):
        raise ValueError("text capacity metadata values must be positive integers")
    return maximum, width


def line_capacity_metadata(capacity: TextCapacity) -> dict[str, int] | None:
    """Project private metadata only when an estimated line capacity exists."""
    if not capacity.has_line_capacity:
        return None
    assert capacity.max_lines is not None
    assert capacity.estimated_chars_per_line is not None
    return {
        "max_lines": capacity.max_lines,
        "estimated_chars_per_line": capacity.estimated_chars_per_line,
    }


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

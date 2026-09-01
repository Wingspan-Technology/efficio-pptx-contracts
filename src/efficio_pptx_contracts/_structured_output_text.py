"""V2 Structured Outputs projection for text components."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._structured_output_common import (
    ensure_aggregate_character_budget_is_feasible,
    join_sentences,
    string_schema,
)
from ._text_sizing_validation import text_sizing_issues
from ._validation_common import _positive_int_tag
from ._validation_text import _text_validation_schema
from .ai_projection import PROMPT_INSTRUCTION_TAG

_TEXT_FORMAT_TAG = "efficio_text_format"
_MAX_CHARS_TAG = "efficio_max_chars"
_TARGET_CHARS_TAG = "efficio_target_chars"
_MIN_ITEMS_TAG = "efficio_min_items"
_TARGET_ITEMS_TAG = "efficio_target_items"
_MAX_ITEMS_TAG = "efficio_max_items"
_MIN_CHARS_PER_ITEM_TAG = "efficio_min_chars_per_item"
_MAX_CHARS_PER_ITEM_TAG = "efficio_max_chars_per_item"
_TARGET_CHARS_PER_ITEM_TAG = "efficio_target_chars_per_item"

_FORMAT_LABELS = {
    "plain": "plain-text",
    "paragraph": "paragraph",
    "bullets": "bullet",
    "numbered_list": "numbered-list",
}


def build_text_v2_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    """Build the self-contained output schema and private text metadata."""
    # Reuse V1's required-tag/type checks while keeping V2 description ordering
    # and aggregate-limit metadata explicit.
    _text_validation_schema(tags)
    issues = text_sizing_issues(tags, ())
    if issues:
        raise ValueError("text tags are invalid: " + "; ".join(issue[2] for issue in issues))

    text_format = tags[_TEXT_FORMAT_TAG]
    minimum_items = 1 if text_format == "plain" else int(tags[_MIN_ITEMS_TAG])
    maximum_items = 1 if text_format == "plain" else int(tags[_MAX_ITEMS_TAG])
    minimum_chars = int(tags[_MIN_CHARS_PER_ITEM_TAG])
    maximum_chars = int(tags[_MAX_CHARS_PER_ITEM_TAG])
    maximum_total = _positive_int_tag(tags, _MAX_CHARS_TAG, "text")
    ensure_aggregate_character_budget_is_feasible(
        minimum_items=minimum_items,
        minimum_chars_per_item=minimum_chars,
        maximum_chars=maximum_total,
        subject="text V2 contract",
    )

    hard_constraints = join_sentences(
        _item_count_description(text_format, minimum_items, maximum_items),
        f"Each item must contain {minimum_chars}–{maximum_chars} characters",
        f"The combined item length must not exceed {maximum_total} characters",
    )
    prompt = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()
    description = join_sentences(prompt, hard_constraints, _target_description(tags))

    item_schema = string_schema(
        minimum_chars,
        maximum_chars,
        description=f"One {_FORMAT_LABELS[text_format]} content item.",
    )
    output_schema = {
        "type": "object",
        "description": description,
        "properties": {
            "items": {
                "type": "array",
                "description": description,
                "items": item_schema,
                "minItems": minimum_items,
                "maxItems": maximum_items,
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    return {
        "component_type": "text",
        "output_schema": output_schema,
        "normalization": {"max_chars": maximum_total},
    }


def validate_text_v2_semantics(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    """Enforce the aggregate character budget JSON Schema cannot express."""
    actual, maximum = text_v2_aggregate_character_usage(content, normalization)
    if actual > maximum:
        raise ValueError(
            f"text V2 content at /items uses {actual} characters; maximum is {maximum}"
        )


def text_v2_aggregate_character_usage(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> tuple[int, int]:
    """Return actual and allowed aggregate characters for validated text shape."""
    maximum = validate_text_v2_normalization(normalization)
    items = content.get("items")
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        raise ValueError("text V2 content at /items must be an array of strings")
    actual = sum(len(item) for item in items)
    return actual, maximum


def validate_text_v2_normalization(normalization: Mapping[str, Any]) -> int:
    """Return the aggregate limit after exact trusted-metadata validation."""
    if set(normalization) != {"max_chars"}:
        raise ValueError("text V2 normalization must contain exactly max_chars")
    maximum = normalization["max_chars"]
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        raise ValueError("text V2 normalization max_chars must be a positive integer")
    return maximum


def _item_count_description(text_format: str, minimum: int, maximum: int) -> str:
    label = _FORMAT_LABELS[text_format]
    if minimum == maximum:
        noun = "item" if minimum == 1 else "items"
        return f"Return exactly {minimum} {label} {noun}"
    return f"Return {minimum}–{maximum} {label} items"


def _target_description(tags: Mapping[str, str]) -> str:
    targets: list[str] = []
    target_items = tags.get(_TARGET_ITEMS_TAG, "").strip()
    target_total = tags.get(_TARGET_CHARS_TAG, "").strip()
    target_per_item = tags.get(_TARGET_CHARS_PER_ITEM_TAG, "").strip()
    if target_items:
        targets.append(f"{target_items} items")
    if target_total:
        targets.append(f"{target_total} characters total")
    if target_per_item:
        targets.append(f"{target_per_item} characters per item")
    if not targets:
        return ""
    return "Aim for approximately " + ", and ".join(targets)

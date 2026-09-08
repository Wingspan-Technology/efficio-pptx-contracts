"""V2 schema projection and estimated-capacity validation for text."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._structured_output_common import join_sentences
from ._text_capacity import (
    estimated_line_usage,
    text_capacity_metadata,
    text_capacity_description,
    validate_text_capacity_metadata,
)
from ._text_sizing_validation import text_capacity_from_tags
from ._validation_text import _text_validation_schema
from .ai_projection import PROMPT_INSTRUCTION_TAG

_TEXT_FORMAT_TAG = "efficio_text_format"
_FORMAT_LABELS = {
    "plain": "plain-text",
    "paragraph": "paragraph",
    "bullets": "bullet",
    "numbered_list": "numbered-list",
}


def build_text_v2_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    """Build a self-contained text schema and private capacity metadata."""
    canonical = _text_validation_schema(tags)
    capacity = text_capacity_from_tags(tags)
    text_format = tags[_TEXT_FORMAT_TAG]
    description = join_sentences(
        tags.get(PROMPT_INSTRUCTION_TAG, "").strip(),
        text_capacity_description(capacity, plain=text_format == "plain"),
        f"Each item is one {_FORMAT_LABELS[text_format]} content unit, not one rendered line",
    )
    items_schema = canonical["properties"]["items"]
    items_schema["description"] = description
    items_schema["items"]["description"] = (
        f"One {_FORMAT_LABELS[text_format]} content item."
    )
    output_schema = {
        "type": "object",
        "description": description,
        "properties": {"items": items_schema},
        "required": ["items"],
        "additionalProperties": False,
    }
    metadata = text_capacity_metadata(capacity)
    if metadata is None:
        raise ValueError("text components require estimated line capacity")
    return {
        "component_type": "text",
        "output_schema": output_schema,
        "normalization": {"text_capacity": metadata},
    }


def validate_text_v2_semantics(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> None:
    """Enforce aggregate character bounds and estimated line capacity."""
    actual_chars, minimum_chars, maximum_chars = text_v2_character_usage(
        content, normalization
    )
    if actual_chars < minimum_chars or actual_chars > maximum_chars:
        raise ValueError(
            f"text V2 content at /items uses {actual_chars} characters; "
            f"required range is {minimum_chars}–{maximum_chars}"
        )
    actual_lines, maximum_lines = text_v2_estimated_line_usage(content, normalization)
    if actual_lines > maximum_lines:
        raise ValueError(
            f"text V2 content at /items uses an estimated {actual_lines} lines; "
            f"maximum is {maximum_lines}"
        )


def text_v2_estimated_line_usage(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> tuple[int, int]:
    """Return estimated used and allowed lines for validated text content."""
    maximum, chars_per_line, _, _ = validate_text_v2_normalization(normalization)
    if maximum is None or chars_per_line is None:
        raise ValueError("text V2 normalization requires estimated line capacity")
    items = content.get("items")
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        raise ValueError("text V2 content at /items must be an array of strings")
    return estimated_line_usage(items, chars_per_line=chars_per_line), maximum


def text_v2_character_usage(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> tuple[int, int, int]:
    """Return aggregate used, minimum, and maximum characters."""
    _, _, minimum, maximum = validate_text_v2_normalization(normalization)
    if minimum is None or maximum is None:
        raise ValueError("text V2 normalization requires character capacity")
    items = content.get("items")
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        raise ValueError("text V2 content at /items must be an array of strings")
    return sum(len(item) for item in items), minimum, maximum


def validate_text_v2_normalization(
    normalization: Mapping[str, Any],
) -> tuple[int | None, int | None, int | None, int | None]:
    """Validate private text-capacity metadata."""
    if set(normalization) != {"text_capacity"}:
        raise ValueError("text V2 normalization must contain exactly text_capacity")
    raw = normalization["text_capacity"]
    if not isinstance(raw, Mapping):
        raise ValueError("text V2 normalization text_capacity must be an object")
    return validate_text_capacity_metadata(raw)

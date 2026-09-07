"""Text component per-instance validation schema."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._text_capacity import build_text_items_schema
from ._text_sizing_validation import text_capacity_from_tags
from ._validation_common import (
    _PLAIN_FORMAT,
    _TEXT_FORMATS,
    _base_content_schema,
    _required_tag,
)

_TEXT_FORMAT_TAG = "efficio_text_format"


def _text_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    text_format = _required_tag(tags, _TEXT_FORMAT_TAG, "text")
    if text_format not in _TEXT_FORMATS:
        raise ValueError(
            f"tag {_TEXT_FORMAT_TAG!r} value {text_format!r} is not one of "
            f"{sorted(_TEXT_FORMATS)}"
        )
    capacity = text_capacity_from_tags(tags)
    schema = _base_content_schema("text")
    schema["properties"]["items"] = build_text_items_schema(
        capacity,
        plain=text_format == _PLAIN_FORMAT,
    )
    return schema

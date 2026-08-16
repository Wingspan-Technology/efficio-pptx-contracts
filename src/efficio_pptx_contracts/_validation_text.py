"""Text component per-instance validation schema.

Bounds the item count (``efficio_min_items`` / ``efficio_max_items``) and each
item's length (``efficio_min_chars_per_item`` / ``efficio_max_chars_per_item``);
every string in ``items[]`` shares the same per-item length bounds. ``plain`` is
exactly one item (``minItems`` == ``maxItems`` == 1). Aggregate ``efficio_max_chars``
across ``items[]`` and the ``target_*`` guidance tags (``efficio_target_chars``,
``efficio_target_items``, ``efficio_target_chars_per_item``) are intentionally not
encoded — JSON Schema cannot sum item lengths, and the targets are guidance, not
bounds; ``efficio_target_items`` in particular never appears in runtime validation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._validation_common import (
    _PLAIN_FORMAT,
    _TEXT_FORMATS,
    _base_content_schema,
    _positive_int_tag,
    _required_tag,
)

_TEXT_FORMAT_TAG = "efficio_text_format"
_MIN_ITEMS_TAG = "efficio_min_items"
_MAX_ITEMS_TAG = "efficio_max_items"
_MIN_CHARS_PER_ITEM_TAG = "efficio_min_chars_per_item"
_MAX_CHARS_PER_ITEM_TAG = "efficio_max_chars_per_item"


def _text_validation_schema(tags: Mapping[str, str]) -> dict[str, Any]:
    text_format = _required_tag(tags, _TEXT_FORMAT_TAG, "text")
    if text_format not in _TEXT_FORMATS:
        raise ValueError(
            f"tag {_TEXT_FORMAT_TAG!r} value {text_format!r} is not one of {sorted(_TEXT_FORMATS)}"
        )
    min_items = _positive_int_tag(tags, _MIN_ITEMS_TAG, "text")
    max_items = _positive_int_tag(tags, _MAX_ITEMS_TAG, "text")
    min_chars_per_item = _positive_int_tag(tags, _MIN_CHARS_PER_ITEM_TAG, "text")
    max_chars_per_item = _positive_int_tag(tags, _MAX_CHARS_PER_ITEM_TAG, "text")

    schema = _base_content_schema("text")
    items = schema["properties"]["items"]
    if text_format == _PLAIN_FORMAT:
        items["minItems"] = 1
        items["maxItems"] = 1
    else:
        items["minItems"] = min_items
        items["maxItems"] = max_items
    # Per-item length bounds apply to every string in items[]. The aggregate
    # efficio_max_chars across items is intentionally not encoded (JSON Schema cannot
    # sum item lengths); the target_* tags are guidance and never appear here.
    items["items"]["minLength"] = min_chars_per_item
    items["items"]["maxLength"] = max_chars_per_item
    return schema

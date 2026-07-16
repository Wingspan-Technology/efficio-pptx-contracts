"""Shared helpers for the per-instance validation-schema builders.

The public dispatcher lives in :mod:`validation_schema`; the per-type builders
(text, table, category_chart) live in their own focused modules. This module
holds the small pieces they share so no rule is duplicated.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .instructions import load_component_instruction

_PLAIN_FORMAT = "plain"
_TEXT_FORMATS = frozenset({"plain", "paragraph", "bullets", "numbered_list"})

# Stripped from the deep-copied base expected_content_schema: the emitted
# instance schema is pure validation keywords (no identity or AI prose).
_STRIPPED_BASE_KEYS = ("$schema", "component_type", "description")


def _base_content_schema(component_type: str) -> dict[str, Any]:
    """Deep copy of the type's authored expected_content_schema, prose stripped."""
    schema = copy.deepcopy(load_component_instruction(component_type)["expected_content_schema"])
    for key in _STRIPPED_BASE_KEYS:
        schema.pop(key, None)
    return schema


def _required_tag(tags: Mapping[str, str], tag_name: str, component_type: str) -> str:
    value = tags.get(tag_name)
    if value is None or not value.strip():
        raise ValueError(
            f"tag {tag_name!r} is required to build a {component_type} validation schema"
        )
    return value


def _positive_int_tag(tags: Mapping[str, str], tag_name: str, component_type: str) -> int:
    value = _required_tag(tags, tag_name, component_type)
    if not value.isdecimal() or int(value) < 1:
        raise ValueError(f"tag {tag_name!r} must be a positive integer string")
    return int(value)

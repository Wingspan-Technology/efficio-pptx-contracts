"""Renderer-safe, limit-free data-bound text contract."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ._validation_text import _text_validation_schema


def build_data_bound_text_contract(tags: Mapping[str, str]) -> dict[str, Any]:
    _text_validation_schema(tags)
    return {
        "submission_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
        "normalization": {},
    }


def normalize_data_bound_text(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    if normalization:
        raise ValueError("data-bound text normalization must be empty")
    return copy.deepcopy(dict(content))

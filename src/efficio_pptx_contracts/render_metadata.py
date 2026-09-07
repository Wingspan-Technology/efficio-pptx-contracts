"""Trusted component render metadata derived from authored contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .classification_schemes import (
    classification_scheme_private_metadata,
    resolve_categorical_fill_scheme,
)
from .registry import assert_component_type


def build_component_render_metadata(
    component_type: str,
    component_tags: Mapping[str, str],
    *,
    deck_tags: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build private renderer metadata without content-mode coupling."""
    assert_component_type(component_type)
    if component_type != "categorical_fill":
        return {}
    if deck_tags is None:
        raise ValueError("categorical-fill render metadata requires deck_tags")
    scheme = resolve_categorical_fill_scheme(component_tags, deck_tags)
    return classification_scheme_private_metadata(scheme)


__all__ = ["build_component_render_metadata"]

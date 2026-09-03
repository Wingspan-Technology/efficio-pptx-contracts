"""Current component content modes and narrow legacy-tag resolution."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from .errors import ContentModeError

CONTENT_MODE_TAG = "efficio_content_mode"
LEGACY_RENDER_BEHAVIOR_TAG = "efficio_render_behavior"


class ContentMode(StrEnum):
    AI_GENERATED = "ai_generated"
    DATA_BOUND = "data_bound"
    PRESERVE = "preserve"
    REMOVE = "remove"


_LEGACY_CONTENT_MODES = {
    "render_by_component_type": ContentMode.AI_GENERATED,
    "preserve": ContentMode.PRESERVE,
    "remove_on_render": ContentMode.REMOVE,
}


def resolve_content_mode(tags: Mapping[str, str]) -> ContentMode | None:
    """Resolve current or exact legacy mode tags without inventing defaults."""
    current_raw = tags.get(CONTENT_MODE_TAG)
    legacy_raw = tags.get(LEGACY_RENDER_BEHAVIOR_TAG)
    current = _current_mode(current_raw) if current_raw is not None else None
    legacy = _legacy_mode(legacy_raw) if legacy_raw is not None else None
    if current is not None and legacy is not None and current is not legacy:
        raise ContentModeError("current and legacy component content modes conflict")
    return current if current is not None else legacy


def is_ai_facing(tags: Mapping[str, str]) -> bool:
    """Return whether this component belongs in externally generated AI content."""
    return resolve_content_mode(tags) is ContentMode.AI_GENERATED


def is_data_bound(tags: Mapping[str, str]) -> bool:
    """Return whether content is supplied by a trusted external calculation."""
    return resolve_content_mode(tags) is ContentMode.DATA_BOUND


def is_renderable(tags: Mapping[str, str]) -> bool:
    """Return whether a component renderer should receive replacement content."""
    return resolve_content_mode(tags) in {
        ContentMode.AI_GENERATED,
        ContentMode.DATA_BOUND,
    }


def _current_mode(value: str) -> ContentMode:
    try:
        return ContentMode(value)
    except ValueError as error:
        raise ContentModeError(f"unsupported {CONTENT_MODE_TAG} value") from error


def _legacy_mode(value: str) -> ContentMode:
    try:
        return _LEGACY_CONTENT_MODES[value]
    except KeyError as error:
        raise ContentModeError(
            f"unsupported {LEGACY_RENDER_BEHAVIOR_TAG} value"
        ) from error


__all__ = [
    "CONTENT_MODE_TAG",
    "LEGACY_RENDER_BEHAVIOR_TAG",
    "ContentMode",
    "is_ai_facing",
    "is_data_bound",
    "is_renderable",
    "resolve_content_mode",
]

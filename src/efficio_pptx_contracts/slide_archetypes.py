"""Typed template-authored slide archetype metadata.

The deck registry (``efficio_slide_archetypes``) declares which archetypes a
template supports. A slide may narrow itself to a subset of them through
``efficio_slide_archetype_ids``; a slide with no assignment is generic and stays
applicable to every declared archetype. Neither tag carries an ``ai`` block:
archetypes are pre-selection metadata a client uses to filter its own slide
catalog before AI slide selection runs, so they never reach the generated
slide-selection instructions and never affect inclusion policy, choice/bundle
structure, role, placement, or ordering.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

from jsonschema import Draft202012Validator

from ._resources import load_json

SLIDE_ARCHETYPES_TAG = "efficio_slide_archetypes"
SLIDE_ARCHETYPE_IDS_TAG = "efficio_slide_archetype_ids"

_INVALID_REGISTRY = "slide archetypes do not match the deck tag contract"
_INVALID_ASSIGNMENT = "slide archetype IDs do not match the slide tag contract"


class SlideArchetypeContractError(ValueError):
    """Raised when archetype metadata or a reference violates the contracts."""


@dataclass(frozen=True)
class SlideArchetype:
    """One authored archetype definition in the exact deck-tag wire shape."""

    archetype_id: str
    name: str
    description: str | None = None


def parse_slide_archetypes(
    raw_value: str | list[Any] | None,
) -> tuple[SlideArchetype, ...]:
    """Parse a deck archetype registry from stored JSON text or a decoded array.

    A missing, blank, or empty value is a template that declares no archetype
    restrictions and yields an empty registry.
    """
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return ()
    parsed = _decode(raw_value, "slide archetypes must contain valid JSON")
    schema = _registry_schema()
    _require_schema(parsed, schema, _INVALID_REGISTRY)

    records = cast(list[dict[str, Any]], parsed)
    id_pattern = _strict_pattern(
        str(schema["items"]["properties"]["archetype_id"]["pattern"])
    )
    for record in records:
        if id_pattern.fullmatch(record["archetype_id"]) is None:
            raise SlideArchetypeContractError(_INVALID_REGISTRY)

    archetypes = tuple(_parse_archetype(record) for record in records)
    identifiers = [archetype.archetype_id for archetype in archetypes]
    if len(set(identifiers)) != len(identifiers):
        raise SlideArchetypeContractError("slide archetype IDs must be unique")
    return archetypes


def parse_slide_archetype_ids(
    raw_value: str | list[Any] | None,
) -> tuple[str, ...]:
    """Parse one slide's archetype assignment from stored JSON text or an array.

    A missing tag means the slide is generic and returns an empty tuple; a blank
    or empty stored value is invalid. IDs keep their authored order and are never
    trimmed or case-folded.
    """
    if raw_value is None:
        return ()
    if isinstance(raw_value, str) and not raw_value.strip():
        raise SlideArchetypeContractError(_INVALID_ASSIGNMENT)
    parsed = _decode(raw_value, "slide archetype IDs must contain valid JSON")
    schema = _assignment_schema()
    _require_schema(parsed, schema, _INVALID_ASSIGNMENT)

    identifiers = tuple(cast(list[str], parsed))
    id_pattern = _strict_pattern(str(schema["items"]["pattern"]))
    if any(id_pattern.fullmatch(identifier) is None for identifier in identifiers):
        raise SlideArchetypeContractError(_INVALID_ASSIGNMENT)
    return identifiers


def resolve_slide_archetype_assignment(
    slide_tags: Mapping[str, str],
    deck_tags: Mapping[str, str],
) -> tuple[SlideArchetype, ...]:
    """Resolve a slide's assignment to definitions, in assignment order.

    A generic slide resolves to an empty tuple. Unknown references and
    structurally invalid values raise :class:`SlideArchetypeContractError`.
    """
    assigned_ids = parse_slide_archetype_ids(slide_tags.get(SLIDE_ARCHETYPE_IDS_TAG))
    if not assigned_ids:
        return ()

    registry = parse_slide_archetypes(deck_tags.get(SLIDE_ARCHETYPES_TAG))
    by_id = {archetype.archetype_id: archetype for archetype in registry}
    resolved: list[SlideArchetype] = []
    for archetype_id in assigned_ids:
        archetype = by_id.get(archetype_id)
        if archetype is None:
            raise SlideArchetypeContractError(
                f"the slide references an unknown slide archetype {archetype_id!r}"
            )
        resolved.append(archetype)
    return tuple(resolved)


def is_slide_applicable_to_archetype(
    slide_tags: Mapping[str, str],
    deck_tags: Mapping[str, str],
    archetype_id: str,
) -> bool:
    """Report whether one slide may be offered for the requested archetype.

    Generic slides apply to every archetype, including when the registry declares
    none. A malformed requested ID, an unsupported requested ID against a
    populated registry, and an invalid registry or assignment all raise rather
    than silently filtering the slide out.
    """
    registry = parse_slide_archetypes(deck_tags.get(SLIDE_ARCHETYPES_TAG))
    if not _is_archetype_id(archetype_id):
        raise SlideArchetypeContractError(
            f"requested slide archetype {archetype_id!r} is not a valid archetype ID"
        )
    assigned = resolve_slide_archetype_assignment(slide_tags, deck_tags)
    if registry and all(
        archetype.archetype_id != archetype_id for archetype in registry
    ):
        raise SlideArchetypeContractError(
            f"requested slide archetype {archetype_id!r} is not declared by the deck"
        )
    if not assigned:
        return True
    return any(archetype.archetype_id == archetype_id for archetype in assigned)


def _parse_archetype(record: dict[str, Any]) -> SlideArchetype:
    description = record.get("description")
    return SlideArchetype(
        archetype_id=record["archetype_id"],
        name=record["name"].strip(),
        description=None if description is None else description.strip(),
    )


def _decode(raw_value: str | list[Any], message: str) -> Any:
    if not isinstance(raw_value, str):
        return raw_value
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise SlideArchetypeContractError(message) from error


def _require_schema(parsed: Any, schema: dict[str, Any], message: str) -> None:
    if next(Draft202012Validator(schema).iter_errors(parsed), None) is not None:
        raise SlideArchetypeContractError(message)


def _registry_schema() -> dict[str, Any]:
    return _tag_schema("deck-tags.json", SLIDE_ARCHETYPES_TAG)


def _assignment_schema() -> dict[str, Any]:
    return _tag_schema("slide-tags.json", SLIDE_ARCHETYPE_IDS_TAG)


def _tag_schema(resource: str, tag_name: str) -> dict[str, Any]:
    contract = load_json("schemas", "presentation", resource)
    definition = contract.get("tags", {}).get(tag_name)
    if not isinstance(definition, dict) or not isinstance(definition.get("schema"), dict):
        raise SlideArchetypeContractError(f"the {tag_name} tag contract is unavailable")
    return cast(dict[str, Any], definition["schema"])


def _is_archetype_id(value: object) -> bool:
    properties = _registry_schema()["items"]["properties"]["archetype_id"]
    return (
        isinstance(value, str)
        and len(value) <= int(properties["maxLength"])
        and _strict_pattern(str(properties["pattern"])).fullmatch(value) is not None
    )


@lru_cache(maxsize=8)
def _strict_pattern(pattern: str) -> re.Pattern[str]:
    """Compile an authored contract pattern for strict full-string matching.

    JSON Schema treats ``pattern`` as a search, and Python's ``$`` additionally
    matches just before a trailing line feed, so schema validation alone accepts
    ``"pitch_deck\n"``. Matching the same authored pattern with ``fullmatch``
    rejects any trailing or embedded character outside the identifier, which is
    what the TypeScript SDK's ``RegExp.test`` already does.
    """
    return re.compile(pattern)


__all__ = [
    "SLIDE_ARCHETYPES_TAG",
    "SLIDE_ARCHETYPE_IDS_TAG",
    "SlideArchetype",
    "SlideArchetypeContractError",
    "is_slide_applicable_to_archetype",
    "parse_slide_archetype_ids",
    "parse_slide_archetypes",
    "resolve_slide_archetype_assignment",
]

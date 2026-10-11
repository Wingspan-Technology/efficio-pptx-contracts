"""Typed template-authored, name-only data-topic metadata.

The deck registry (``efficio_data_topics``) declares the data topics a template
talks about, each as an exact ``{topic_id, name}`` pair. A slide may name the
topics it relates to through ``efficio_slide_data_topic_ids``; a slide without
that tag simply has no assignment. Neither tag carries an ``ai`` block: data
topics are advisory labels only, so they never bind data, filter or select
slides, constrain generated content schemas, or reach the generated
slide-selection instructions.
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

DATA_TOPICS_TAG = "efficio_data_topics"
SLIDE_DATA_TOPIC_IDS_TAG = "efficio_slide_data_topic_ids"

_INVALID_REGISTRY = "data topics do not match the deck tag contract"
_INVALID_ASSIGNMENT = "slide data topic IDs do not match the slide tag contract"


class DataTopicContractError(ValueError):
    """Raised when data-topic metadata or a reference violates the contracts."""


@dataclass(frozen=True)
class DataTopic:
    """One authored data-topic definition in the exact deck-tag wire shape."""

    topic_id: str
    name: str


def parse_data_topics(raw_value: str | list[Any] | None) -> tuple[DataTopic, ...]:
    """Parse a deck data-topic registry from stored JSON text or a decoded array.

    A missing, blank, or empty value declares no data topics and yields an empty
    registry. Topics keep their authored order. IDs must be unique and are never
    trimmed or case-folded; names may repeat and are trimmed.
    """
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return ()
    parsed = _decode(raw_value, "data topics must contain valid JSON")
    schema = _registry_schema()
    _require_schema(parsed, schema, _INVALID_REGISTRY)

    records = cast(list[dict[str, str]], parsed)
    id_pattern = _strict_pattern(str(schema["items"]["properties"]["topic_id"]["pattern"]))
    if any(id_pattern.fullmatch(record["topic_id"]) is None for record in records):
        raise DataTopicContractError(_INVALID_REGISTRY)

    topics = tuple(
        DataTopic(topic_id=record["topic_id"], name=record["name"].strip())
        for record in records
    )
    identifiers = [topic.topic_id for topic in topics]
    if len(set(identifiers)) != len(identifiers):
        raise DataTopicContractError("data topic IDs must be unique")
    return topics


def parse_slide_data_topic_ids(raw_value: str | list[Any] | None) -> tuple[str, ...]:
    """Parse one slide's data-topic assignment from stored JSON text or an array.

    A missing tag means the slide has no assignment and returns an empty tuple; a
    blank or empty stored value is invalid. IDs keep their authored order and are
    never trimmed or case-folded.
    """
    if raw_value is None:
        return ()
    if isinstance(raw_value, str) and not raw_value.strip():
        raise DataTopicContractError(_INVALID_ASSIGNMENT)
    parsed = _decode(raw_value, "slide data topic IDs must contain valid JSON")
    schema = _assignment_schema()
    _require_schema(parsed, schema, _INVALID_ASSIGNMENT)

    identifiers = tuple(cast(list[str], parsed))
    id_pattern = _strict_pattern(str(schema["items"]["pattern"]))
    if any(id_pattern.fullmatch(identifier) is None for identifier in identifiers):
        raise DataTopicContractError(_INVALID_ASSIGNMENT)
    return identifiers


def resolve_slide_data_topic_assignment(
    slide_tags: Mapping[str, str],
    deck_tags: Mapping[str, str],
) -> tuple[DataTopic, ...]:
    """Resolve a slide's assignment to definitions, in assignment order.

    A slide without an assignment resolves to an empty tuple. Unknown references
    and structurally invalid values raise :class:`DataTopicContractError`.
    """
    assigned_ids = parse_slide_data_topic_ids(slide_tags.get(SLIDE_DATA_TOPIC_IDS_TAG))
    if not assigned_ids:
        return ()

    registry = parse_data_topics(deck_tags.get(DATA_TOPICS_TAG))
    by_id = {topic.topic_id: topic for topic in registry}
    resolved: list[DataTopic] = []
    for topic_id in assigned_ids:
        topic = by_id.get(topic_id)
        if topic is None:
            raise DataTopicContractError(
                f"the slide references an unknown data topic {topic_id!r}"
            )
        resolved.append(topic)
    return tuple(resolved)


def _decode(raw_value: str | list[Any], message: str) -> Any:
    if not isinstance(raw_value, str):
        return raw_value
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise DataTopicContractError(message) from error


def _require_schema(parsed: Any, schema: dict[str, Any], message: str) -> None:
    if next(Draft202012Validator(schema).iter_errors(parsed), None) is not None:
        raise DataTopicContractError(message)


def _registry_schema() -> dict[str, Any]:
    return _tag_schema("deck-tags.json", DATA_TOPICS_TAG)


def _assignment_schema() -> dict[str, Any]:
    return _tag_schema("slide-tags.json", SLIDE_DATA_TOPIC_IDS_TAG)


def _tag_schema(resource: str, tag_name: str) -> dict[str, Any]:
    contract = load_json("schemas", "presentation", resource)
    definition = contract.get("tags", {}).get(tag_name)
    if not isinstance(definition, dict) or not isinstance(definition.get("schema"), dict):
        raise DataTopicContractError(f"the {tag_name} tag contract is unavailable")
    return cast(dict[str, Any], definition["schema"])


@lru_cache(maxsize=8)
def _strict_pattern(pattern: str) -> re.Pattern[str]:
    """Compile an authored contract pattern for strict full-string matching.

    JSON Schema treats ``pattern`` as a search, and Python's ``$`` additionally
    matches just before a trailing line feed, so schema validation alone accepts
    ``"topic_revenue\\n"``. ``fullmatch`` rejects it, matching the TypeScript
    SDK's ``RegExp.test``.
    """
    return re.compile(pattern)


__all__ = [
    "DATA_TOPICS_TAG",
    "SLIDE_DATA_TOPIC_IDS_TAG",
    "DataTopic",
    "DataTopicContractError",
    "parse_data_topics",
    "parse_slide_data_topic_ids",
    "resolve_slide_data_topic_assignment",
]

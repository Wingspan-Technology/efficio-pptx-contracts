"""AI-facing per-instance projection of component tag data.

Given a component instance's raw Efficio tag map (from the private import
artifact) plus its component type, produce the AI-safe per-instance context that
may be exposed to generation. Tag AI-visibility is owned by the component
contracts: a tag may appear only if its contract declares ``ai`` — i.e. it is
present in the generated component instruction's ``tag_instructions``. Callers
must not maintain their own AI tag allowlists; they go through these helpers.

The AI-facing projection speaks the public alias contract, never raw tag names:
every ``tag_context`` key is the tag name with the ``efficio_`` prefix stripped
(``efficio_max_chars`` -> ``max_chars``), matching the aliased
``tag_instructions`` keys in the generated component instructions. Values are
typed for AI consumption: integer tags become ``int``, object/array tags are
parsed into real JSON values, strings/enums stay strings. Internal artifacts,
PowerPoint tags, the editor, and validation keep raw ``efficio_*`` names.

Two structural tags are consumed by dedicated paths and appear in neither
``tag_instructions`` nor ``tag_context`` (their contracts declare no ``ai``):

- ``efficio_content_mode`` — decides AI-facing inclusion (``is_ai_facing``);
- ``efficio_prompt_instruction`` — surfaced per instance as the top-level
  ``instructions`` field.

The projection never includes shape paths, raw tag maps, table/cell coordinates,
PowerPoint object ids, or any tag without ``ai``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .instructions import load_component_instruction
from .tag_validation import load_component_tag_schema
from .content_mode import CONTENT_MODE_TAG

PROMPT_INSTRUCTION_TAG = "efficio_prompt_instruction"
TEMPLATE_INSTRUCTION_TAG = "efficio_template_instruction"

# Structural tags never copied into tag_context, independent of contract state —
# a guard even if a contract were to (re)declare ai on them.
_EXCLUDED_FROM_TAG_CONTEXT = frozenset({CONTENT_MODE_TAG, PROMPT_INSTRUCTION_TAG})

_TAG_PREFIX = "efficio_"

# Compatibility tag types whose string values are converted for AI consumption.
_INTEGER_TAG_TYPE = "positive_integer_string"
_JSON_TAG_TYPES = frozenset({"json_object", "json_array"})


def public_tag_alias(tag_name: str) -> str:
    """Public AI alias of an internal tag name: the ``efficio_`` prefix stripped.

    Aliases cannot collide because every contract tag name carries the prefix.
    Raises ``ValueError`` for a name without it.
    """
    alias = tag_name.removeprefix(_TAG_PREFIX)
    if alias == tag_name or alias == "":
        raise ValueError(f"cannot build a public AI alias for tag name {tag_name!r}")
    return alias


def ai_visible_tag_names(component_type: str) -> frozenset[str]:
    """The public tag aliases exposed to AI for a component type.

    Sourced from the generated component instruction (``tag_instructions``),
    whose keys are the public aliases of exactly the tags whose contract declares
    ``ai``. Raises ``UnknownComponentTypeError`` for an unregistered component
    type.
    """
    instruction = load_component_instruction(component_type)
    return frozenset(instruction.get("tag_instructions") or {})


def project_component_context(component_type: str, tags: Mapping[str, str]) -> dict[str, Any]:
    """AI-safe per-instance context: ``component_type``, optional ``instructions``, ``tag_context``.

    ``tag_context`` carries only AI-visible tag values (per the component
    contract), keyed by public alias and typed for AI consumption (integer tags
    as numbers, object/array tags as parsed JSON values, strings/enums as
    strings). The content-mode and prompt-instruction tags and any tag whose
    raw value is blank (empty, spaces, or only newlines) are excluded. No shape
    paths, raw tags, or PowerPoint internals are included. ``instructions`` is
    included only when ``efficio_prompt_instruction`` has a non-blank value
    (trimmed); a missing or blank prompt omits the field entirely.

    Tags must already satisfy the component contract (the importer validates
    before projecting); a non-integer value on an integer tag or invalid JSON on
    an object/array tag raises ``ValueError`` instead of being passed through.
    """
    visible = ai_visible_tag_names(component_type)
    tag_types = load_component_tag_schema(component_type).get("types") or {}

    tag_context: dict[str, Any] = {}
    for name, value in tags.items():
        if name in _EXCLUDED_FROM_TAG_CONTEXT or not name.startswith(_TAG_PREFIX):
            continue
        alias = public_tag_alias(name)
        if alias not in visible or value.strip() == "":
            continue
        tag_context[alias] = _typed_tag_value(name, value, tag_types.get(name))

    context: dict[str, Any] = {"component_type": component_type}
    prompt = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()
    if prompt != "":
        context["instructions"] = prompt
    context["tag_context"] = tag_context
    return context


def project_deck_context(tags: Mapping[str, str]) -> dict[str, Any]:
    """AI-safe deck-level context derived from the presentation/deck tag map.

    Returns ``{"instructions": <trimmed value>}`` only when
    ``efficio_template_instruction`` is present and non-blank; a missing or blank
    value yields ``{}`` (no template instruction). The raw ``efficio_*`` tag name
    never appears — only the aliased ``instructions`` field, matching the
    per-instance ``instructions`` field on component context. This is deck-wide AI
    guidance, less specific than any slide/component instruction and never a
    validation or schema constraint.
    """
    instruction = tags.get(TEMPLATE_INSTRUCTION_TAG, "").strip()
    if instruction == "":
        return {}
    return {"instructions": instruction}


def _typed_tag_value(tag_name: str, value: str, tag_type: str | None) -> Any:
    """Convert a raw tag string to its AI-facing value per the contract tag type."""
    if tag_type == _INTEGER_TAG_TYPE:
        if not value.isdecimal():
            raise ValueError(f"tag {tag_name!r} must be a positive integer string")
        return int(value)
    if tag_type in _JSON_TAG_TYPES:
        try:
            return json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"tag {tag_name!r} must be valid JSON") from error
    return value

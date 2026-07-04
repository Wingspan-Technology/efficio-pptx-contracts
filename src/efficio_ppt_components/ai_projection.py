"""AI-facing per-instance projection of component tag data.

Given a component instance's raw Efficio tag map (from the private import
artifact) plus its component type, produce the AI-safe per-instance context that
may be exposed to generation. Tag AI-visibility is owned by the component
contracts: a tag may appear only if its contract declares ``ai`` — i.e. it is
present in the generated component instruction's ``tag_instructions``. Callers
must not maintain their own AI tag allowlists; they go through these helpers.

Two AI-visible tags are handled structurally and never copied into
``tag_context``:

- ``efficio_render_behavior`` — used only to decide AI-facing inclusion;
- ``efficio_prompt_instruction`` — surfaced as the component ``instructions``.

The projection never includes shape paths, raw tag maps, table/cell coordinates,
PowerPoint object ids, or any tag without ``ai``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .instructions import load_component_instruction

RENDER_BEHAVIOR_TAG = "efficio_render_behavior"
AI_FACING_RENDER_BEHAVIOR = "render_by_component_type"
PROMPT_INSTRUCTION_TAG = "efficio_prompt_instruction"

# AI-visible tags handled structurally rather than copied into tag_context.
_EXCLUDED_FROM_TAG_CONTEXT = frozenset({RENDER_BEHAVIOR_TAG, PROMPT_INSTRUCTION_TAG})


def is_ai_facing(tags: Mapping[str, str]) -> bool:
    """True if a component renders by component type (the only AI-facing behavior).

    ``preserve``, ``remove_on_render``, and missing/unknown render behavior are
    all non-AI-facing.
    """
    return tags.get(RENDER_BEHAVIOR_TAG) == AI_FACING_RENDER_BEHAVIOR


def ai_visible_tag_names(component_type: str) -> frozenset[str]:
    """The tag names exposed to AI for a component type.

    Sourced from the generated component instruction (``tag_instructions``), which
    contains exactly the tags whose contract declares ``ai``. Raises
    ``UnknownComponentTypeError`` for an unregistered component type.
    """
    instruction = load_component_instruction(component_type)
    return frozenset(instruction.get("tag_instructions") or {})


def project_component_context(component_type: str, tags: Mapping[str, str]) -> dict[str, Any]:
    """AI-safe per-instance context: ``component_type``, optional ``instructions``, ``tag_context``.

    ``tag_context`` carries only AI-visible tag values (per the component
    contract), excluding the render-behavior and prompt-instruction tags and any
    tag whose value is blank (empty, spaces, or only newlines). No shape paths,
    raw tags, or PowerPoint internals are included. ``instructions`` is included
    only when ``efficio_prompt_instruction`` has a non-blank value (trimmed);
    a missing or blank prompt omits the field entirely.
    """
    visible = ai_visible_tag_names(component_type)
    tag_context = {
        name: value
        for name, value in tags.items()
        if name in visible
        and name not in _EXCLUDED_FROM_TAG_CONTEXT
        and value.strip() != ""
    }

    context: dict[str, Any] = {"component_type": component_type}
    prompt = tags.get(PROMPT_INSTRUCTION_TAG, "").strip()
    if prompt != "":
        context["instructions"] = prompt
    context["tag_context"] = tag_context
    return context

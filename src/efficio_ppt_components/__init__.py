"""Public Python SDK for Efficio PowerPoint component contracts.

Reads generated contract artifacts that ship inside this package and exposes a
small, stable, read-only API. Generated artifacts are produced by
``scripts/generate-ts-contracts.ts``; this package never hand-maintains them.
"""

from __future__ import annotations

from .errors import (
    EfficioComponentsError,
    MissingResourceError,
    UnknownComponentTypeError,
)
from .ai_projection import (
    AI_FACING_RENDER_BEHAVIOR,
    PROMPT_INSTRUCTION_TAG,
    RENDER_BEHAVIOR_TAG,
    ai_visible_tag_names,
    is_ai_facing,
    project_component_context,
)
from .instructions import (
    build_component_instruction_block,
    load_component_instruction,
    load_component_instructions,
    load_slide_selection_instruction,
)
from .registry import (
    assert_component_type,
    has_component_type,
    list_component_types,
    load_component_registry,
)
from .tag_validation import (
    TagValidationIssue,
    load_component_tag_schema,
    load_slide_tag_contract,
    validate_component_tags,
    validate_slide_tags,
)
from .validation_schema import build_validation_content_schema

__all__ = [
    "EfficioComponentsError",
    "MissingResourceError",
    "UnknownComponentTypeError",
    "load_component_registry",
    "list_component_types",
    "has_component_type",
    "assert_component_type",
    "load_component_instruction",
    "load_component_instructions",
    "build_component_instruction_block",
    "load_slide_selection_instruction",
    "is_ai_facing",
    "ai_visible_tag_names",
    "project_component_context",
    "RENDER_BEHAVIOR_TAG",
    "AI_FACING_RENDER_BEHAVIOR",
    "PROMPT_INSTRUCTION_TAG",
    "TagValidationIssue",
    "load_component_tag_schema",
    "load_slide_tag_contract",
    "validate_component_tags",
    "validate_slide_tags",
    "build_validation_content_schema",
]

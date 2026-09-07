"""Dynamic categorical-fill schemas, metadata, and normalization."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from ._structured_output_common import join_sentences
from .ai_projection import PROMPT_INSTRUCTION_TAG
from .classification_schemes import (
    ClassificationScheme,
    classification_scheme_private_metadata,
    resolve_categorical_fill_scheme,
)

_CONTENT_ROLE_TAG = "efficio_content_role"
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def build_categorical_fill_validation_schema(
    tags: Mapping[str, str], deck_tags: Mapping[str, str]
) -> dict[str, Any]:
    """Build the authoritative case-id content schema for one component."""
    scheme = resolve_categorical_fill_scheme(tags, deck_tags)
    return _case_schema(scheme, include_descriptions=False)


def build_categorical_fill_v2_contract(
    tags: Mapping[str, str], deck_tags: Mapping[str, str]
) -> dict[str, Any]:
    """Build AI-facing schema plus trusted private fill metadata."""
    scheme = resolve_categorical_fill_scheme(tags, deck_tags)
    return {
        "component_type": "categorical_fill",
        "output_schema": _case_schema(
            scheme,
            include_descriptions=True,
            component_instruction=tags.get(PROMPT_INSTRUCTION_TAG, "").strip(),
            content_role=tags.get(_CONTENT_ROLE_TAG, "").strip(),
        ),
        "normalization": classification_scheme_private_metadata(scheme),
    }


def build_data_bound_categorical_fill_contract(
    tags: Mapping[str, str], deck_tags: Mapping[str, str]
) -> dict[str, Any]:
    """Build the strict renderer-safe data-bound categorical-fill contract."""
    scheme = resolve_categorical_fill_scheme(tags, deck_tags)
    return {
        "submission_schema": _case_schema(scheme, include_descriptions=False),
        "normalization": classification_scheme_private_metadata(scheme),
    }


def normalize_categorical_fill_content(
    content: Mapping[str, Any], normalization: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate the selected trusted case and preserve the canonical shape."""
    case_ids = validate_categorical_fill_normalization(normalization)
    if set(content) != {"case_id"} or not isinstance(content.get("case_id"), str):
        raise ValueError("categorical-fill content must contain exactly one string case_id")
    if content["case_id"] not in case_ids:
        raise ValueError("categorical-fill content contains an unknown case_id")
    return copy.deepcopy(dict(content))


def validate_categorical_fill_normalization(
    normalization: Mapping[str, Any],
) -> frozenset[str]:
    """Validate exact trusted categorical-fill metadata without using its values."""
    if set(normalization) != {"scheme_id", "cases"}:
        raise ValueError("categorical-fill normalization must contain exactly scheme_id and cases")
    scheme_id = normalization.get("scheme_id")
    cases = normalization.get("cases")
    if not isinstance(scheme_id, str) or _ID_PATTERN.fullmatch(scheme_id) is None:
        raise ValueError("categorical-fill normalization scheme_id is invalid")
    if not isinstance(cases, Mapping) or not 2 <= len(cases) <= 32:
        raise ValueError("categorical-fill normalization must contain 2 to 32 cases")
    for case_id, case in cases.items():
        if not isinstance(case_id, str) or _ID_PATTERN.fullmatch(case_id) is None:
            raise ValueError("categorical-fill normalization case ID is invalid")
        if not isinstance(case, Mapping) or set(case) != {"fill"}:
            raise ValueError("categorical-fill normalization case must contain exactly fill")
        fill = case.get("fill")
        if not isinstance(fill, Mapping) or set(fill) != {"kind", "value"}:
            raise ValueError(
                "categorical-fill normalization fill must contain exactly kind and value"
            )
        value = fill.get("value")
        if fill.get("kind") != "rgb" or not _is_rgb(value):
            raise ValueError("categorical-fill normalization requires an uppercase RGB fill")
    return frozenset(cases)


def validate_categorical_fill_schema_coherence(
    schema: Mapping[str, Any],
    normalization: Mapping[str, Any],
    *,
    require_descriptions: bool,
) -> None:
    """Require a closed case-id schema to match its trusted cases exactly."""
    case_ids = validate_categorical_fill_normalization(normalization)
    root_fields = {"type", "properties", "required", "additionalProperties"}
    if require_descriptions:
        root_fields.add("description")
    if set(schema) != root_fields:
        raise ValueError("categorical-fill schema fields are invalid")
    properties = schema.get("properties")
    if (
        schema.get("type") != "object"
        or schema.get("additionalProperties") is not False
        or schema.get("required") != ["case_id"]
        or not isinstance(properties, Mapping)
        or set(properties) != {"case_id"}
    ):
        raise ValueError("categorical-fill schema must be a closed case_id object")
    case_schema = properties["case_id"]
    case_fields = {"type", "enum"}
    if require_descriptions:
        case_fields.add("description")
    if (
        not isinstance(case_schema, Mapping)
        or set(case_schema) != case_fields
        or case_schema.get("type") != "string"
    ):
        raise ValueError("categorical-fill case_id schema must be a string")
    enum = case_schema.get("enum")
    if not isinstance(enum, list) or any(not isinstance(item, str) for item in enum):
        raise ValueError("categorical-fill case_id schema must declare a string enum")
    if len(enum) != len(set(enum)) or set(enum) != case_ids:
        raise ValueError("categorical-fill schema cases must match normalization metadata")
    if require_descriptions:
        descriptions = (schema["description"], case_schema["description"])
        if any(not isinstance(value, str) or not value.strip() for value in descriptions):
            raise ValueError("categorical-fill schema descriptions must be non-empty")
        private_values = _private_fill_values(normalization)
        if any(
            fill.lower() in description.lower()
            for fill in private_values
            for description in descriptions
        ):
            raise ValueError("categorical-fill schema must not expose private fill values")


def _private_fill_values(normalization: Mapping[str, Any]) -> tuple[str, ...]:
    cases = normalization["cases"]
    assert isinstance(cases, Mapping)
    return tuple(str(case["fill"]["value"]) for case in cases.values())


def _case_schema(
    scheme: ClassificationScheme,
    *,
    include_descriptions: bool,
    component_instruction: str = "",
    content_role: str = "",
) -> dict[str, Any]:
    case_ids = [case.case_id for case in scheme.cases]
    case_schema: dict[str, Any] = {"type": "string", "enum": case_ids}
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {"case_id": case_schema},
        "required": ["case_id"],
        "additionalProperties": False,
    }
    if include_descriptions:
        subject = f"Classify {content_role}" if content_role else "Classify this target"
        cases = "; ".join(
            f"{case.case_id} — {case.label}: {case.description}" for case in scheme.cases
        )
        description = join_sentences(
            subject,
            scheme.instruction,
            component_instruction,
            "Return exactly one semantic case_id and no presentation styling",
        )
        schema["description"] = description
        case_schema["description"] = f"Select exactly one case: {cases}."
    return schema


def _is_rgb(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 6
        and all(character in "0123456789ABCDEF" for character in value)
    )


__all__ = [
    "build_categorical_fill_validation_schema",
    "build_categorical_fill_v2_contract",
    "build_data_bound_categorical_fill_contract",
    "normalize_categorical_fill_content",
    "validate_categorical_fill_normalization",
    "validate_categorical_fill_schema_coherence",
]

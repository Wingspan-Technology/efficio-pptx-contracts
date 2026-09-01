"""Public provider-neutral V2 component contracts.

This module derives deterministic Draft 2020-12 schemas from the authored tags that own
canonical ``validation.json``. It also owns the small, deterministic bridge from
generated output to the existing renderer content shapes. It performs no AI
request and contains no provider client code.
"""

# Public contract validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from ._structured_output_category_chart import (
    build_category_chart_v2_contract,
    normalize_category_chart_v2_content,
    validate_category_chart_v2_normalization,
)
from ._structured_output_coherence import validate_v2_component_shape_coherence
from ._structured_output_common import (
    JSON_SCHEMA_DRAFT_2020_12_PROFILE,
    JSON_SCHEMA_DRAFT_2020_12_URI,
    validate_prompt_json_schema,
)
from ._structured_output_schema_validation import (
    validate_v2_executable_component_schema,
)
from ._structured_output_table import (
    build_table_v2_contract,
    normalize_table_v2_content,
    validate_table_v2_normalization,
    validate_table_v2_semantics,
)
from ._structured_output_text import (
    build_text_v2_contract,
    validate_text_v2_normalization,
    validate_text_v2_semantics,
)
from .errors import UnknownComponentTypeError
from .registry import assert_component_type

_Builder = Callable[[Mapping[str, str]], dict[str, Any]]

_BUILDERS: dict[str, _Builder] = {
    "text": build_text_v2_contract,
    "table": build_table_v2_contract,
    "category_chart": build_category_chart_v2_contract,
}


def build_v2_component_contract(
    component_type: str, tags: Mapping[str, str]
) -> dict[str, Any]:
    """Build one component's V2 output schema and private metadata.

    The exact return keys are ``component_type``, ``output_schema``, and
    ``normalization``. ``output_schema`` is safe to expose to an AI caller;
    ``normalization`` is trusted import/runtime metadata and must not be accepted
    from or returned to an external caller.
    """
    builder = _BUILDERS.get(component_type)
    if builder is None:
        assert_component_type(component_type)
        raise UnknownComponentTypeError(
            f"component type {component_type!r} is registered but has no V2 builder"
        )
    contract = builder(tags)
    validate_v2_component_contract_coherence(
        component_type,
        contract["output_schema"],
        contract["normalization"],
    )
    return contract


def validate_v2_component_contract_coherence(
    component_type: str,
    output_schema: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> None:
    """Validate a persisted V2 schema and metadata as one component contract."""
    _assert_supported(component_type)
    if not isinstance(output_schema, Mapping):
        raise ValueError(f"{component_type} V2 output schema must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError(
            f"{component_type} V2 normalization metadata must be an object"
        )
    validate_v2_executable_component_schema(
        output_schema, require_prompt_profile=True
    )
    validate_v2_component_normalization(component_type, normalization)
    validate_v2_component_shape_coherence(
        component_type, output_schema, normalization
    )


def normalize_v2_component_content(
    component_type: str,
    content: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize generated V2 content to canonical renderer content."""
    _assert_supported(component_type)
    if not isinstance(content, Mapping):
        raise ValueError(f"{component_type} V2 content must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError(f"{component_type} V2 normalization metadata must be an object")
    if component_type == "table":
        return normalize_table_v2_content(content, normalization)
    if component_type == "category_chart":
        return normalize_category_chart_v2_content(content, normalization)
    validate_text_v2_normalization(normalization)
    return copy.deepcopy(dict(content))


def validate_v2_component_semantics(
    component_type: str,
    content: Mapping[str, Any],
    normalization: Mapping[str, Any],
) -> None:
    """Validate hard aggregate limits JSON Schema cannot express."""
    _assert_supported(component_type)
    if not isinstance(content, Mapping):
        raise ValueError(f"{component_type} V2 content must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError(f"{component_type} V2 normalization metadata must be an object")
    if component_type == "text":
        validate_text_v2_semantics(content, normalization)
    elif component_type == "table":
        validate_table_v2_semantics(content, normalization)


def validate_v2_component_normalization(
    component_type: str, normalization: Mapping[str, Any]
) -> None:
    """Validate one persisted component's exact trusted V2 metadata shape."""
    _assert_supported(component_type)
    if not isinstance(normalization, Mapping):
        raise ValueError(f"{component_type} V2 normalization metadata must be an object")
    if component_type == "text":
        validate_text_v2_normalization(normalization)
    elif component_type == "table":
        validate_table_v2_normalization(normalization)
    else:
        validate_category_chart_v2_normalization(normalization)


def _assert_supported(component_type: str) -> None:
    if component_type in _BUILDERS:
        return
    assert_component_type(component_type)
    raise UnknownComponentTypeError(
        f"component type {component_type!r} is registered but has no V2 support"
    )


__all__ = [
    "JSON_SCHEMA_DRAFT_2020_12_PROFILE",
    "JSON_SCHEMA_DRAFT_2020_12_URI",
    "build_v2_component_contract",
    "normalize_v2_component_content",
    "validate_prompt_json_schema",
    "validate_v2_component_contract_coherence",
    "validate_v2_component_normalization",
    "validate_v2_component_semantics",
    "validate_v2_executable_component_schema",
]

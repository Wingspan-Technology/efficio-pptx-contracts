"""Per-instance content-validation schemas (validation.json).

Given a component instance's type and raw Efficio tag map (from the private
import artifact), derive the JSON Schema that validates that instance's
``component.content``. The importer writes these schemas into the per-slide
``slide-components/{slide_id}/validation.json`` artifact, keyed by component id.
They are served to the DMS authoring client by the orchestrator's
content-validation-schema endpoint and read by the generation runner to validate
AI content before rendering — DMS-facing and runtime-used.

This module is the public dispatcher: it maps a component type to its builder
and fails fast on unknown or unsupported types. Each per-type builder lives in
its own focused module (:mod:`_validation_text`, :mod:`_validation_table`,
:mod:`_validation_category_chart`) and shares small helpers through
:mod:`_validation_common`. The emitted schemas carry validation keywords only —
no component identity, AI prose, raw tags, shape paths, or PowerPoint internals.

Every registered component type (``text``, ``table``, ``category_chart``) is
supported, so a schema is always returned; an unregistered/unknown component
type raises ``UnknownComponentTypeError`` (fail-fast on typos and not-yet-wired
types). Missing or invalid limit/config tags raise ``ValueError`` — a permissive
schema is never emitted.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._validation_category_chart import _category_chart_validation_schema
from ._validation_table import _table_validation_schema
from ._validation_text import _text_validation_schema
from .errors import UnknownComponentTypeError
from .registry import assert_component_type


def build_validation_content_schema(
    component_type: str, tags: Mapping[str, str]
) -> dict[str, Any]:
    """The JSON Schema validating one component instance's ``content``.

    Every registered component type is supported, so a schema is always returned.
    An unregistered/unknown type raises :class:`UnknownComponentTypeError`. For
    supported types, missing or invalid limit/config tags raise ``ValueError``
    rather than degrading to a permissive schema.
    """
    builder = _BUILDERS.get(component_type)
    if builder is None:
        # Unknown types fail fast. A registered type with no builder is contract/
        # code drift — every registered type must be supported — so also fail fast.
        assert_component_type(component_type)
        raise UnknownComponentTypeError(
            f"component type {component_type!r} is registered but has no validation "
            "schema builder; every registered type must be supported"
        )
    return builder(tags)


_BUILDERS = {
    "text": _text_validation_schema,
    "table": _table_validation_schema,
    "category_chart": _category_chart_validation_schema,
}

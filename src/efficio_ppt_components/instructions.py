"""AI instruction artifact access for the efficio_ppt_components SDK.

Backed by generated ``_generated/ai/*`` resources produced from authored tag
``ai`` metadata, content contracts, and the authored slide-selection sources.
These functions return structured ``dict`` data only; they do not assemble
runtime prompt prose.
"""

from __future__ import annotations

from collections.abc import Iterable

from ._resources import load_json
from .registry import assert_component_type

_AGGREGATE_RESOURCE = ("ai", "component-instructions.json")
_SLIDE_SELECTION_RESOURCE = ("ai", "slide-selection.instruction.json")


def load_component_instruction(component_type: str) -> dict:
    """Return the generated AI instruction artifact for one component type."""
    assert_component_type(component_type)
    return load_json("ai", "components", f"{component_type}.instruction.json")


def load_component_instructions(component_types: Iterable[str] | None = None) -> dict:
    """Return the AI instruction catalog, optionally filtered to selected types.

    With ``component_types=None`` the full generated aggregate block is returned.
    When types are supplied they are deduplicated, sorted, and validated against
    the registry; unknown types raise :class:`UnknownComponentTypeError`. The
    return shape is always the aggregate block shape
    ``{"instruction": ..., "component_instructions": {...}}``.
    """
    aggregate = load_json(*_AGGREGATE_RESOURCE)
    if component_types is None:
        return aggregate
    return _filter_block(aggregate, component_types)


def build_component_instruction_block(component_types: Iterable[str]) -> dict:
    """Return the aggregate instruction block filtered to the selected types.

    Component types are deduplicated, sorted, and validated against the registry.
    The result preserves the general ``instruction`` and groups each selected
    component under ``component_instructions``. No file paths are added and no
    schema validation is performed.
    """
    return _filter_block(load_json(*_AGGREGATE_RESOURCE), component_types)


def load_slide_selection_instruction() -> dict:
    """Return the generated static slide-selection AI instruction artifact."""
    return load_json(*_SLIDE_SELECTION_RESOURCE)


def _filter_block(aggregate: dict, component_types: Iterable[str]) -> dict:
    """Filter the aggregate block to the selected types, preserving instruction."""
    selected = _normalize_types(component_types)
    component_instructions = aggregate.get("component_instructions", {})
    return {
        "instruction": aggregate["instruction"],
        "component_instructions": {
            component_type: component_instructions[component_type] for component_type in selected
        },
    }


def _normalize_types(component_types: Iterable[str]) -> list[str]:
    """Deduplicate, validate, and deterministically sort requested types."""
    unique = set(component_types)
    for component_type in unique:
        assert_component_type(component_type)
    return sorted(unique)

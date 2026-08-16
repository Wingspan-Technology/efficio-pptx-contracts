"""Component registry access for the efficio_pptx_contracts SDK.

Backed by the generated ``_generated/component-registry.json`` resource, which is
produced from ``contracts/components/*`` by ``scripts/generate-ts-contracts.ts``. The
registry is the authority for which component types exist.
"""

from __future__ import annotations

from ._resources import load_json
from .errors import UnknownComponentTypeError

_REGISTRY_RESOURCE = ("component-registry.json",)


def load_component_registry() -> dict:
    """Return the generated component registry as a plain ``dict``."""
    return load_json(*_REGISTRY_RESOURCE)


def list_component_types() -> list[str]:
    """Return the registered component types, sorted deterministically."""
    registry = load_component_registry()
    components = registry.get("components", {})
    return sorted(components.keys())


def has_component_type(component_type: str) -> bool:
    """Return whether ``component_type`` is present in the registry."""
    registry = load_component_registry()
    return component_type in registry.get("components", {})


def assert_component_type(component_type: str) -> None:
    """Raise :class:`UnknownComponentTypeError` if ``component_type`` is unknown."""
    if not has_component_type(component_type):
        known = ", ".join(list_component_types())
        raise UnknownComponentTypeError(
            f"Unknown component type: {component_type!r}. Known types: {known}."
        )

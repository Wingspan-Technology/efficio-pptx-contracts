"""Internal resource loading for generated SDK artifacts.

All generated runtime JSON ships inside this package under ``_generated/`` and is
read through :mod:`importlib.resources`. Callers use the public ``registry`` and
``instructions`` modules; they never touch this module or receive filesystem
paths. This keeps resource access wheel-safe and independent of the top-level
``generated/`` tree consumed by the TypeScript/editor flow.
"""

from __future__ import annotations

import json
from importlib.resources import files
from importlib.resources.abc import Traversable
from typing import Any, cast

from .errors import EfficioComponentsError, MissingResourceError

_GENERATED_ROOT = "_generated"


def _resource(*parts: str) -> Traversable:
    """Resolve a Traversable for a resource under ``_generated/``."""
    resource = files(__package__).joinpath(_GENERATED_ROOT)
    for part in parts:
        resource = resource.joinpath(part)
    return resource


def load_json(*parts: str) -> dict[str, Any]:
    """Load and parse a generated JSON resource under ``_generated/``.

    ``parts`` is the path relative to ``_generated/`` (e.g.
    ``("ai", "component-instructions.json")``). A missing resource raises
    :class:`MissingResourceError`; invalid JSON raises
    :class:`EfficioComponentsError`. Filesystem paths are never returned.
    """
    resource = _resource(*parts)
    rel = "/".join((_GENERATED_ROOT, *parts))
    try:
        text = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, OSError) as error:
        raise MissingResourceError(f"Generated SDK resource not found: {rel}") from error

    try:
        return cast(dict[str, Any], json.loads(text))
    except json.JSONDecodeError as error:
        raise EfficioComponentsError(f"Generated SDK resource is not valid JSON: {rel}") from error

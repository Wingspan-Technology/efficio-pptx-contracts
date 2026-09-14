"""Typed native-group selection configuration and renderer-safe membership."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from jsonschema import Draft202012Validator

from ._resources import load_json
from ._structured_output_common import join_sentences
from .classification_schemes import ClassificationScheme, classification_scheme_private_metadata

FILL_MODE_TAG = "efficio_fill_mode"
FILL_SELECTION_TAG = "efficio_fill_selection"
SELECTION_ITEM_ID_TAG = "efficio_selection_item_id"
_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class CategoricalFillMode(StrEnum):
    CLASSIFICATION = "classification"
    SELECTION = "selection"


@dataclass(frozen=True)
class CategoricalSelectionItem:
    item_id: str
    label: str
    instruction: str = ""


@dataclass(frozen=True)
class CategoricalFillSelection:
    selected_case_id: str
    unselected_case_id: str
    items: tuple[CategoricalSelectionItem, ...]


def resolve_categorical_fill_mode(tags: Mapping[str, str]) -> CategoricalFillMode:
    """Missing mode retains the established whole-component classification."""
    try:
        return CategoricalFillMode(tags.get(FILL_MODE_TAG, "classification"))
    except ValueError as error:
        raise ValueError("categorical-fill mode must be classification or selection") from error


def resolve_categorical_fill_selection(
    tags: Mapping[str, str], scheme: ClassificationScheme
) -> CategoricalFillSelection | None:
    """Resolve selection metadata and require the scheme's exact two cases."""
    mode = resolve_categorical_fill_mode(tags)
    raw = tags.get(FILL_SELECTION_TAG)
    if mode is CategoricalFillMode.CLASSIFICATION:
        if raw is not None:
            raise ValueError("classification mode must not declare fill selection")
        return None
    if not isinstance(raw, str):
        raise ValueError("selection mode requires fill selection configuration")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("fill selection must contain valid JSON") from error
    contract = load_json("schemas", "components", "categorical-fill.json")
    schema = contract["json_schemas"][FILL_SELECTION_TAG]
    if not Draft202012Validator(schema).is_valid(parsed):
        raise ValueError("fill selection does not match its tag contract")
    selected, unselected = parsed["selected_case_id"], parsed["unselected_case_id"]
    if _ID_PATTERN.fullmatch(selected) is None or _ID_PATTERN.fullmatch(unselected) is None:
        raise ValueError("selection case IDs must be exact lower_snake_case identifiers")
    if selected == unselected or {selected, unselected} != {case.case_id for case in scheme.cases}:
        raise ValueError("selection requires exactly its distinct selected and unselected cases")
    items = tuple(
        CategoricalSelectionItem(
            item_id=item["item_id"],
            label=item["label"].strip(),
            instruction=item.get("instruction", "").strip(),
        )
        for item in parsed["items"]
    )
    if len({item.item_id for item in items}) != len(items):
        raise ValueError("selection item IDs must be unique")
    if any(_ID_PATTERN.fullmatch(item.item_id) is None for item in items):
        raise ValueError("selection item IDs must be exact lower_snake_case identifiers")
    if any(not item.label for item in items):
        raise ValueError("selection item labels must not be blank")
    if any("instruction" in item and not item["instruction"].strip() for item in parsed["items"]):
        raise ValueError("selection item instructions must not be blank when present")
    return CategoricalFillSelection(selected, unselected, items)


def selection_private_metadata(
    scheme: ClassificationScheme, selection: CategoricalFillSelection
) -> dict[str, Any]:
    """Keep styling and ordered target identity separate from public context."""
    return {
        "fill_mode": CategoricalFillMode.SELECTION.value,
        **classification_scheme_private_metadata(scheme),
        "selected_case_id": selection.selected_case_id,
        "unselected_case_id": selection.unselected_case_id,
        "item_ids": [item.item_id for item in selection.items],
    }


def selection_public_context(selection: CategoricalFillSelection) -> dict[str, Any]:
    """Return item meaning and case mapping without presentation styling."""
    return {
        "selected_case_id": selection.selected_case_id,
        "unselected_case_id": selection.unselected_case_id,
        "items": [
            {
                "item_id": item.item_id,
                "label": item.label,
                **({"instruction": item.instruction} if item.instruction else {}),
            }
            for item in selection.items
        ],
    }


def build_selection_schema(
    scheme: ClassificationScheme,
    selection: CategoricalFillSelection,
    *,
    include_descriptions: bool,
    component_instruction: str = "",
    content_role: str = "",
) -> dict[str, Any]:
    """Use one closed selected-ID array for all members of the native group."""
    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "selected_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": [item.item_id for item in selection.items]},
            }
        },
        "required": ["selected_ids"],
        "additionalProperties": False,
    }
    if include_descriptions:
        cases = "; ".join(f"{case.case_id}: {case.description}" for case in scheme.cases)
        labels = "; ".join(
            f"{item.item_id} — {item.label}" + (f": {item.instruction}" if item.instruction else "")
            for item in selection.items
        )
        schema["description"] = join_sentences(
            f"Select {content_role}" if content_role else "Select applicable items",
            scheme.instruction,
            component_instruction,
            f"Cases: {cases}",
            f"Return only selected_ids for items matching {selection.selected_case_id}; "
            f"all omitted items receive {selection.unselected_case_id}. "
            "Use each item ID at most once; [] means select none. Return no styling",
            f"Items: {labels}",
        )
    return schema


def validate_selection_metadata(
    metadata: Mapping[str, Any], case_ids: frozenset[str]
) -> tuple[str, ...]:
    """Validate mode-specific metadata after the shared trusted cases are checked."""
    if set(metadata) != {
        "fill_mode",
        "scheme_id",
        "cases",
        "selected_case_id",
        "unselected_case_id",
        "item_ids",
    }:
        raise ValueError("selection normalization fields are invalid")
    selected, unselected = metadata.get("selected_case_id"), metadata.get("unselected_case_id")
    if (
        metadata.get("fill_mode") != CategoricalFillMode.SELECTION.value
        or not isinstance(selected, str)
        or not isinstance(unselected, str)
        or selected == unselected
        or {selected, unselected} != case_ids
    ):
        raise ValueError("selection normalization must map exactly two distinct cases")
    item_ids = metadata.get("item_ids")
    if not isinstance(item_ids, list) or not 1 <= len(item_ids) <= 1000:
        raise ValueError("selection normalization requires 1 to 1000 item IDs")
    if any(
        not isinstance(item, str) or len(item) > 120 or _ID_PATTERN.fullmatch(item) is None
        for item in item_ids
    ):
        raise ValueError("selection normalization item ID is invalid")
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("selection normalization item IDs must be unique")
    return tuple(item_ids)


def normalize_selection_content(
    content: Mapping[str, Any], item_ids: tuple[str, ...]
) -> dict[str, Any]:
    """Require a duplicate-free subset; omission selects the unselected case."""
    values = content.get("selected_ids")
    if set(content) != {"selected_ids"} or not isinstance(values, list):
        raise ValueError("selection content must contain exactly one selected_ids array")
    allowed = frozenset(item_ids)
    if any(not isinstance(value, str) or value not in allowed for value in values):
        raise ValueError("selection content contains an unknown item ID")
    if len(values) != len(set(values)):
        raise ValueError("selection content must not repeat item IDs")
    return {"selected_ids": list(values)}


def validate_selection_schema_coherence(
    schema: Mapping[str, Any], item_ids: tuple[str, ...], *, require_descriptions: bool
) -> None:
    expected = {
        "type": "object",
        "properties": {
            "selected_ids": {
                "type": "array",
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(item_ids)},
            }
        },
        "required": ["selected_ids"],
        "additionalProperties": False,
    }
    if require_descriptions:
        description = schema.get("description")
        if not isinstance(description, str) or not description.strip():
            raise ValueError("selection schema description must be non-empty")
        expected["description"] = description
    if schema != expected:
        raise ValueError("selection schema must exactly match its declared item membership")


__all__ = [
    "FILL_MODE_TAG",
    "FILL_SELECTION_TAG",
    "SELECTION_ITEM_ID_TAG",
    "CategoricalFillMode",
    "CategoricalFillSelection",
    "CategoricalSelectionItem",
    "resolve_categorical_fill_mode",
    "resolve_categorical_fill_selection",
]

"""Typed presentation-level classification schemes for categorical fills."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from jsonschema import Draft202012Validator

from ._resources import load_json

CLASSIFICATION_SCHEMES_TAG = "efficio_classification_schemes"
CLASSIFICATION_SCHEME_ID_TAG = "efficio_classification_scheme_id"


class ClassificationPaletteMode(StrEnum):
    """Supported trusted palette representations."""

    RGB = "rgb"


@dataclass(frozen=True)
class ClassificationFill:
    """One authored solid fill in the exact deck-tag wire shape."""

    value: str


@dataclass(frozen=True)
class ClassificationCase:
    """One semantic case and its trusted presentation styling."""

    case_id: str
    label: str
    description: str
    fill: ClassificationFill


@dataclass(frozen=True)
class ClassificationScheme:
    """One ordered reusable semantic classification scheme."""

    scheme_id: str
    instruction: str
    palette_mode: ClassificationPaletteMode
    cases: tuple[ClassificationCase, ...]


def parse_classification_schemes(
    raw_value: str | list[Any] | None,
) -> tuple[ClassificationScheme, ...]:
    """Parse and semantically validate a deck classification-schemes value."""
    if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
        return ()
    parsed = _decode_value(raw_value)
    errors = sorted(
        Draft202012Validator(_load_scheme_schema()).iter_errors(parsed),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        raise ValueError("classification schemes do not match the deck tag contract")

    records = cast(list[dict[str, Any]], parsed)
    schemes = tuple(_parse_scheme(record) for record in records)
    _validate_unique_ids(schemes)
    return schemes


def resolve_categorical_fill_scheme(
    component_tags: Mapping[str, str],
    deck_tags: Mapping[str, str],
) -> ClassificationScheme:
    """Resolve one categorical-fill component's referenced authored scheme."""
    raw_scheme_id = component_tags.get(CLASSIFICATION_SCHEME_ID_TAG)
    if not isinstance(raw_scheme_id, str) or not raw_scheme_id.strip():
        raise ValueError(
            f"categorical-fill component requires {CLASSIFICATION_SCHEME_ID_TAG}"
        )
    scheme_id = raw_scheme_id.strip()
    schemes = parse_classification_schemes(deck_tags.get(CLASSIFICATION_SCHEMES_TAG))
    for scheme in schemes:
        if scheme.scheme_id == scheme_id:
            return scheme
    raise ValueError("categorical-fill component references an unknown classification scheme")


def classification_scheme_public_context(
    scheme: ClassificationScheme,
) -> dict[str, Any]:
    """Return semantic AI context without trusted fill values."""
    return {
        "scheme_id": scheme.scheme_id,
        "instruction": scheme.instruction,
        "cases": [
            {
                "case_id": case.case_id,
                "label": case.label,
                "description": case.description,
            }
            for case in scheme.cases
        ],
    }


def classification_scheme_private_metadata(
    scheme: ClassificationScheme,
) -> dict[str, Any]:
    """Return deterministic trusted metadata for validation and rendering."""
    return {
        "scheme_id": scheme.scheme_id,
        "cases": {
            case.case_id: {
                "fill": {"kind": scheme.palette_mode.value, "value": case.fill.value}
            }
            for case in scheme.cases
        },
    }


def _decode_value(raw_value: str | list[Any]) -> Any:
    if not isinstance(raw_value, str):
        return raw_value
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError("classification schemes must contain valid JSON") from error


def _load_scheme_schema() -> dict[str, Any]:
    contract = load_json("schemas", "presentation", "deck-tags.json")
    definition = contract.get("tags", {}).get(CLASSIFICATION_SCHEMES_TAG)
    if not isinstance(definition, dict) or not isinstance(
        definition.get("schema"), dict
    ):
        raise ValueError("classification-schemes deck tag contract is unavailable")
    return cast(dict[str, Any], definition["schema"])


def _parse_scheme(record: dict[str, Any]) -> ClassificationScheme:
    mode = ClassificationPaletteMode(record["palette_mode"])
    return ClassificationScheme(
        scheme_id=record["scheme_id"],
        instruction=record["instruction"].strip(),
        palette_mode=mode,
        cases=tuple(
            ClassificationCase(
                case_id=case["case_id"],
                label=case["label"].strip(),
                description=case["description"].strip(),
                fill=ClassificationFill(value=case["fill"]["value"]),
            )
            for case in record["cases"]
        ),
    )


def _validate_unique_ids(schemes: tuple[ClassificationScheme, ...]) -> None:
    scheme_ids: set[str] = set()
    for scheme in schemes:
        if scheme.scheme_id in scheme_ids:
            raise ValueError("classification scheme IDs must be unique")
        scheme_ids.add(scheme.scheme_id)
        case_ids: set[str] = set()
        for case in scheme.cases:
            if case.case_id in case_ids:
                raise ValueError(
                    f"case IDs must be unique within scheme {scheme.scheme_id!r}"
                )
            case_ids.add(case.case_id)


__all__ = [
    "CLASSIFICATION_SCHEMES_TAG",
    "CLASSIFICATION_SCHEME_ID_TAG",
    "ClassificationCase",
    "ClassificationFill",
    "ClassificationPaletteMode",
    "ClassificationScheme",
    "classification_scheme_private_metadata",
    "classification_scheme_public_context",
    "parse_classification_schemes",
    "resolve_categorical_fill_scheme",
]

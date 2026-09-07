"""Typed, content-free V2 semantic findings and repair instructions."""

# Contract validation intentionally exposes one stable ValueError API.
# ruff: noqa: TRY004

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from ._categorical_fill import (
    normalize_categorical_fill_content,
    validate_categorical_fill_normalization,
)
from ._structured_output_category_chart import (
    validate_category_chart_v2_normalization,
)
from ._structured_output_table import (
    _validated_table_normalization,
    table_v2_cell_estimated_line_usage,
)
from ._structured_output_text import (
    text_v2_estimated_line_usage,
    validate_text_v2_normalization,
)
from .errors import UnknownComponentTypeError
from .registry import assert_component_type


class V2SemanticRule(str, Enum):
    """Component-owned semantic rules that JSON Schema cannot express."""

    ESTIMATED_LINE_LIMIT = "estimated_line_limit"


class V2ComponentRepairReason(str, Enum):
    """Bounded content-repair reasons shared with the orchestrator."""

    TYPE = "type"
    REQUIRED = "required"
    ADDITIONAL_PROPERTY = "additional_property"
    ITEM_COUNT = "item_count"
    ITEM_LENGTH = "item_length"
    NUMERIC_CONSTRAINT = "numeric_constraint"
    ESTIMATED_LINE_LIMIT = "estimated_line_limit"
    OTHER = "other"


@dataclass(frozen=True)
class V2ComponentSemanticFinding:
    """One trusted component-relative semantic failure."""

    path: tuple[str | int, ...]
    cell: str | None
    rule: V2SemanticRule
    reason: V2ComponentRepairReason


def collect_v2_component_semantic_findings(
    component_type: str,
    content: Mapping[str, object],
    normalization: Mapping[str, object],
) -> tuple[V2ComponentSemanticFinding, ...]:
    """Collect ordered semantic failures for one canonically shaped component."""
    _assert_supported(component_type)
    _require_mappings(component_type, content, normalization)
    if component_type == "text":
        actual, maximum = text_v2_estimated_line_usage(content, normalization)
        return (_line_capacity_finding(("items",), cell=None),) if actual > maximum else ()
    if component_type == "table":
        cells = content.get("cells")
        if not isinstance(cells, Mapping):
            raise ValueError("table V2 content at /cells must be an object")
        _, capacities = _validated_table_normalization(normalization)
        findings: list[V2ComponentSemanticFinding] = []
        for coordinate, (maximum, chars_per_line) in capacities.items():
            cell_content = cells.get(coordinate)
            if cell_content is None:
                continue
            actual = table_v2_cell_estimated_line_usage(
                coordinate,
                cell_content,
                chars_per_line=chars_per_line,
            )
            if actual > maximum:
                findings.append(
                    _line_capacity_finding(("cells", coordinate, "items"), cell=coordinate)
                )
        return tuple(findings)
    if component_type == "categorical_fill":
        normalize_categorical_fill_content(content, normalization)
        return ()
    validate_category_chart_v2_normalization(normalization)
    return ()


def collect_v2_table_cell_semantic_findings(
    cell: str,
    content: Mapping[str, object],
    normalization: Mapping[str, object],
) -> tuple[V2ComponentSemanticFinding, ...]:
    """Collect semantic failures for one independently validated table cell."""
    if not isinstance(cell, str):
        raise ValueError("table V2 cell coordinate must be a string")
    if not isinstance(content, Mapping):
        raise ValueError("table V2 cell content must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError("table V2 normalization metadata must be an object")
    _, capacities = _validated_table_normalization(normalization)
    capacity = capacities.get(cell)
    if capacity is None:
        return ()
    maximum, chars_per_line = capacity
    actual = table_v2_cell_estimated_line_usage(
        cell,
        content,
        chars_per_line=chars_per_line,
    )
    if actual <= maximum:
        return ()
    return (_line_capacity_finding(("cells", cell, "items"), cell=cell),)


def format_v2_component_repair_instruction(
    component_type: str,
    reason: V2ComponentRepairReason,
    validation_schema: Mapping[str, object],
    normalization: Mapping[str, object],
    *,
    cell: str | None,
) -> str:
    """Format safe repair guidance from a bounded reason and trusted metadata."""
    _assert_supported(component_type)
    if not isinstance(reason, V2ComponentRepairReason):
        raise ValueError("V2 repair reason must be a V2ComponentRepairReason")
    if not isinstance(validation_schema, Mapping):
        raise ValueError("V2 validation schema must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError("V2 normalization metadata must be an object")

    target_schema = _repair_target_schema(component_type, validation_schema, cell)
    _validate_normalization(component_type, normalization)
    if component_type == "categorical_fill":
        return _categorical_fill_repair_instruction(reason, target_schema)
    if reason is V2ComponentRepairReason.ESTIMATED_LINE_LIMIT:
        return _line_capacity_instruction(component_type, normalization, cell)
    if reason is V2ComponentRepairReason.ITEM_COUNT:
        bounds = _item_count_bounds(target_schema)
        if bounds is not None:
            return _item_count_instruction(*bounds)

    subject = "table cell" if cell is not None else component_type.replace("_", " ")
    return {
        V2ComponentRepairReason.TYPE: (
            f"Return the {subject} using the exact JSON types declared by its schema."
        ),
        V2ComponentRepairReason.REQUIRED: (
            f"Return every required field declared for the {subject}."
        ),
        V2ComponentRepairReason.ADDITIONAL_PROPERTY: (
            f"Return only the fields declared for the {subject}."
        ),
        V2ComponentRepairReason.ITEM_COUNT: (
            f"Return every array in the {subject} with the item count declared by its schema."
        ),
        V2ComponentRepairReason.ITEM_LENGTH: (
            f"Keep every text item in the {subject} within its declared character limits."
        ),
        V2ComponentRepairReason.NUMERIC_CONSTRAINT: (
            f"Keep every numeric value in the {subject} within its declared constraints."
        ),
        V2ComponentRepairReason.OTHER: (
            f"Regenerate the {subject} so it matches the provided schema."
        ),
        V2ComponentRepairReason.ESTIMATED_LINE_LIMIT: "",
    }[reason]


def _line_capacity_finding(
    path: tuple[str | int, ...], *, cell: str | None
) -> V2ComponentSemanticFinding:
    return V2ComponentSemanticFinding(
        path=path,
        cell=cell,
        rule=V2SemanticRule.ESTIMATED_LINE_LIMIT,
        reason=V2ComponentRepairReason.ESTIMATED_LINE_LIMIT,
    )


def _assert_supported(component_type: str) -> None:
    if component_type in {"text", "table", "category_chart", "categorical_fill"}:
        return
    assert_component_type(component_type)
    raise UnknownComponentTypeError(
        f"component type {component_type!r} is registered but has no V2 support"
    )


def _require_mappings(
    component_type: str,
    content: Mapping[str, object],
    normalization: Mapping[str, object],
) -> None:
    if not isinstance(content, Mapping):
        raise ValueError(f"{component_type} V2 content must be an object")
    if not isinstance(normalization, Mapping):
        raise ValueError(f"{component_type} V2 normalization metadata must be an object")


def _validate_normalization(
    component_type: str, normalization: Mapping[str, object]
) -> None:
    if component_type == "text":
        validate_text_v2_normalization(normalization)
    elif component_type == "table":
        _validated_table_normalization(normalization)
    elif component_type == "category_chart":
        validate_category_chart_v2_normalization(normalization)
    else:
        validate_categorical_fill_normalization(normalization)


def _repair_target_schema(
    component_type: str,
    output_schema: Mapping[str, object],
    cell: str | None,
) -> Mapping[str, object]:
    if cell is None:
        return output_schema
    if component_type != "table":
        raise ValueError("only table repair instructions may identify a cell")
    properties = output_schema.get("properties")
    cells_schema = properties.get("cells") if isinstance(properties, Mapping) else None
    cell_properties = (
        cells_schema.get("properties") if isinstance(cells_schema, Mapping) else None
    )
    cell_schema = cell_properties.get(cell) if isinstance(cell_properties, Mapping) else None
    if not isinstance(cell_schema, Mapping):
        raise ValueError("table repair cell is absent from the trusted output schema")
    branches = cell_schema.get("anyOf")
    if isinstance(branches, list):
        non_null = [
            branch
            for branch in branches
            if isinstance(branch, Mapping) and branch.get("type") != "null"
        ]
        if len(non_null) != 1:
            raise ValueError("table repair cell schema has no single non-null branch")
        return non_null[0]
    return cell_schema


def _line_capacity_instruction(
    component_type: str,
    normalization: Mapping[str, object],
    cell: str | None,
) -> str:
    if component_type == "text":
        maximum, chars_per_line = validate_text_v2_normalization(normalization)
    elif component_type == "table" and cell is not None:
        _, capacities = _validated_table_normalization(normalization)
        capacity = capacities.get(cell)
        if capacity is None:
            raise ValueError("table repair cell has no estimated text capacity")
        maximum, chars_per_line = capacity
    else:
        raise ValueError("component has no estimated line-capacity repair rule")
    return (
        f"Keep all items within an estimated {maximum} rendered lines at approximately "
        f"{chars_per_line} characters per line. Explicit line breaks consume lines."
    )


def _item_count_bounds(schema: Mapping[str, object]) -> tuple[int, int | None] | None:
    properties = schema.get("properties")
    items_schema = properties.get("items") if isinstance(properties, Mapping) else None
    if not isinstance(items_schema, Mapping) or items_schema.get("type") != "array":
        return None
    minimum = items_schema.get("minItems")
    maximum = items_schema.get("maxItems")
    if not isinstance(minimum, int) or isinstance(minimum, bool):
        return None
    if maximum is not None and (
        not isinstance(maximum, int) or isinstance(maximum, bool)
    ):
        return None
    return minimum, maximum


def _item_count_instruction(minimum: int, maximum: int | None) -> str:
    if maximum == minimum:
        noun = "item" if minimum == 1 else "items"
        return f"Return exactly {minimum} {noun}."
    if maximum is None:
        noun = "item" if minimum == 1 else "items"
        return f"Return at least {minimum} {noun}."
    return f"Return {minimum}–{maximum} items."


def _categorical_fill_repair_instruction(
    reason: V2ComponentRepairReason,
    schema: Mapping[str, object],
) -> str:
    properties = schema.get("properties")
    case_schema = properties.get("case_id") if isinstance(properties, Mapping) else None
    enum = case_schema.get("enum") if isinstance(case_schema, Mapping) else None
    if not isinstance(enum, list) or not enum or any(
        not isinstance(case_id, str) for case_id in enum
    ):
        raise ValueError("categorical-fill repair schema has no valid case_id enum")
    allowed = ", ".join(enum)
    if reason is V2ComponentRepairReason.ADDITIONAL_PROPERTY:
        return (
            "Return only the case_id field for this categorical fill. "
            f"Choose one allowed case_id: {allowed}."
        )
    return (
        "Return exactly one string case_id for this categorical fill. "
        f"Choose one allowed case_id: {allowed}."
    )


__all__ = [
    "V2ComponentRepairReason",
    "V2ComponentSemanticFinding",
    "V2SemanticRule",
    "collect_v2_component_semantic_findings",
    "collect_v2_table_cell_semantic_findings",
    "format_v2_component_repair_instruction",
]

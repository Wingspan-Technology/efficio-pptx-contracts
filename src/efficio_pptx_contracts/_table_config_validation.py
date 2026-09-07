"""Cross-field semantic validation for normalized table configuration.

JSON Schema owns structure and primitive types. This module owns relationships
that schema cannot express: sizing bounds, plain-cell item rules, and duplicate
cell/axis coordinates. Only render cells receive sizing checks because preserve
cells keep their authored content.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ._text_capacity import text_capacity_issues

from ._table_config import (
    TABLE_CONFIG_TAG,
    TableAxis,
    TableCell,
    TableConfig,
    TableConfigError,
    parse_table_config,
)

TableConfigIssue = tuple[str, str, str]


def table_config_issues(
    tags: Mapping[str, str], prior_issue_tags: Iterable[str]
) -> list[TableConfigIssue]:
    """Return semantic issues for a structurally valid table configuration.

    A malformed or already-reported tag is skipped because the structural tag
    validator owns that error and callers should receive it only once.
    """
    if TABLE_CONFIG_TAG in set(prior_issue_tags):
        return []
    raw = tags.get(TABLE_CONFIG_TAG)
    if raw is None or not raw.strip():
        return []
    try:
        config = parse_table_config(raw)
    except TableConfigError:
        return []
    return table_config_model_issues(config)


def table_config_model_issues(config: TableConfig) -> list[TableConfigIssue]:
    """Validate cross-field rules on an already normalized table model."""
    issues: list[TableConfigIssue] = []
    for cell in config.render_cells:
        issues.extend(_cell_issues(cell))
    issues.extend(_duplicate_coordinate_issues(config.cells))
    issues.extend(_duplicate_axis_issues(config.rows, "duplicate_row", "Row"))
    issues.extend(_duplicate_axis_issues(config.columns, "duplicate_column", "Column"))
    return issues


def _duplicate_coordinate_issues(cells: tuple[TableCell, ...]) -> list[TableConfigIssue]:
    """Report each cell coordinate configured more than once."""
    seen: set[tuple[int, int]] = set()
    reported: set[tuple[int, int]] = set()
    issues: list[TableConfigIssue] = []
    for cell in cells:
        coordinate = cell.coordinate
        if coordinate in seen and coordinate not in reported:
            issues.append(
                (
                    "duplicate_cell",
                    TABLE_CONFIG_TAG,
                    f"Cell {coordinate} is configured more than once.",
                )
            )
            reported.add(coordinate)
        seen.add(coordinate)
    return issues


def _duplicate_axis_issues(
    axes: tuple[TableAxis, ...], code: str, label: str
) -> list[TableConfigIssue]:
    """Report each row or column index configured more than once."""
    seen: set[int] = set()
    reported: set[int] = set()
    issues: list[TableConfigIssue] = []
    for axis in axes:
        if axis.index in seen and axis.index not in reported:
            issues.append(
                (
                    code,
                    TABLE_CONFIG_TAG,
                    f"{label} {axis.index} is configured more than once.",
                )
            )
            reported.add(axis.index)
        seen.add(axis.index)
    return issues


def _cell_issues(cell: TableCell) -> list[TableConfigIssue]:
    where = _cell_label(cell)
    return [
        (issue.code, TABLE_CONFIG_TAG, f"{where} {issue.message}")
        for issue in text_capacity_issues(cell.capacity, plain=cell.plain)
    ]


def _cell_label(cell: TableCell) -> str:
    return f"Cell ({cell.row},{cell.col}):"

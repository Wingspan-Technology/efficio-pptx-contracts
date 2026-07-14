"""Cross-field table cell sizing validation (kept out of ``tag_validation`` for size).

Pure logic: given a component's raw tag map and the set of tags that already carry a
structural issue, return ``(code, tag_name, message)`` tuples for the per-cell sizing
relationships JSON Schema cannot express — the same checks the text component applies,
but per cell over the ``efficio_table_config`` JSON. Every issue attaches to the
``efficio_table_config`` tag; its message names the offending cell. The ``target_*``
fields are optional guidance; the min/max fields are strict bounds:

- optional ``target_chars`` <= ``max_chars``;
- optional ``target_items`` within [``min_items``, ``max_items``];
- optional ``target_chars_per_item`` within [``min_chars_per_item``, ``max_chars_per_item``];
- ``min_items`` <= ``max_items``; ``min_chars_per_item`` <= ``max_chars_per_item``;
- a ``plain`` cell is exactly one item (``min_items`` == ``max_items`` == 1; no ``target_items``).
  A cell with no ``text_format`` defaults to plain, so the single-item rule applies to it too.

None of these bounds is encoded in ``validation.json`` (targets never appear there). When
the tag is missing, unparseable, or already carries a structural issue, no cross-field
issue is added — the structural layer already reported it.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, TypeGuard

_TABLE_CONFIG_TAG = "efficio_table_config"
_PLAIN_TEXT_FORMAT = "plain"


def table_config_issues(
    tags: Mapping[str, str], prior_issue_tags: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Return ``(code, tag_name, message)`` for each cross-field table cell sizing violation.

    Skipped entirely when ``efficio_table_config`` is missing/blank or already carries a
    structural issue; each cell's checks run only over its known-good positive-integer
    sizing fields (any malformed value is left to the structural layer).
    """
    if _TABLE_CONFIG_TAG in set(prior_issue_tags):
        return []
    raw = tags.get(_TABLE_CONFIG_TAG)
    if raw is None or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, dict) or not isinstance(parsed.get("cells"), list):
        return []

    issues: list[tuple[str, str, str]] = []
    for entry in parsed["cells"]:
        if isinstance(entry, dict):
            issues.extend(_cell_issues(entry))
    issues.extend(_duplicate_coordinate_issues(parsed["cells"]))
    issues.extend(_duplicate_axis_issues(parsed.get("rows"), "row", "Row"))
    issues.extend(_duplicate_axis_issues(parsed.get("columns"), "col", "Column"))
    return issues


def _duplicate_coordinate_issues(cells: list[Any]) -> list[tuple[str, str, str]]:
    """A cell coordinate may be configured at most once; report each repeated (row, col)."""
    seen: set[tuple[int, int]] = set()
    reported: set[tuple[int, int]] = set()
    issues: list[tuple[str, str, str]] = []
    for entry in cells:
        if not isinstance(entry, dict):
            continue
        row = entry.get("row")
        col = entry.get("col")
        if not (_is_index(row) and _is_index(col)):
            continue
        key = (row, col)
        if key in seen and key not in reported:
            issues.append(
                ("duplicate_cell", _TABLE_CONFIG_TAG, f"Cell {key} is configured more than once.")
            )
            reported.add(key)
        seen.add(key)
    return issues


def _duplicate_axis_issues(value: Any, key: str, label: str) -> list[tuple[str, str, str]]:
    """A row/column index may be configured at most once; report each repeated index."""
    if not isinstance(value, list):
        return []
    code = "duplicate_row" if key == "row" else "duplicate_column"
    seen: set[int] = set()
    reported: set[int] = set()
    issues: list[tuple[str, str, str]] = []
    for entry in value:
        if not isinstance(entry, dict):
            continue
        index = entry.get(key)
        if not _is_index(index):
            continue
        if index in seen and index not in reported:
            issues.append(
                (code, _TABLE_CONFIG_TAG, f"{label} {index} is configured more than once.")
            )
            reported.add(index)
        seen.add(index)
    return issues


def _cell_issues(entry: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    where = _cell_label(entry)

    def value_of(field: str) -> int | None:
        value = entry.get(field)
        # bool is an int subclass; a JSON true/false is not a sizing value.
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            return None
        return value

    max_chars = value_of("max_chars")
    target_chars = value_of("target_chars")
    min_items = value_of("min_items")
    max_items = value_of("max_items")
    target_items = value_of("target_items")
    min_per_item = value_of("min_chars_per_item")
    max_per_item = value_of("max_chars_per_item")
    target_per_item = value_of("target_chars_per_item")

    issues: list[tuple[str, str, str]] = []

    def exceeds(field: str, other: str) -> None:
        issues.append(("target_exceeds_max", _TABLE_CONFIG_TAG, f"{where} {field} must not exceed {other}."))

    # Optional targets must fit within their strict bounds.
    if target_chars is not None and max_chars is not None and target_chars > max_chars:
        exceeds("target_chars", "max_chars")
    if target_items is not None and max_items is not None and target_items > max_items:
        exceeds("target_items", "max_items")
    if target_items is not None and min_items is not None and target_items < min_items:
        issues.append(
            ("target_below_min", _TABLE_CONFIG_TAG, f"{where} target_items must be at least min_items.")
        )
    if target_per_item is not None and max_per_item is not None and target_per_item > max_per_item:
        exceeds("target_chars_per_item", "max_chars_per_item")
    if target_per_item is not None and min_per_item is not None and target_per_item < min_per_item:
        issues.append(
            (
                "target_below_min",
                _TABLE_CONFIG_TAG,
                f"{where} target_chars_per_item must be at least min_chars_per_item.",
            )
        )
    # Strict min <= max ranges.
    if min_items is not None and max_items is not None and min_items > max_items:
        issues.append(
            ("min_exceeds_max", _TABLE_CONFIG_TAG, f"{where} min_items must not exceed max_items.")
        )
    if min_per_item is not None and max_per_item is not None and min_per_item > max_per_item:
        issues.append(
            (
                "min_exceeds_max",
                _TABLE_CONFIG_TAG,
                f"{where} min_chars_per_item must not exceed max_chars_per_item.",
            )
        )
    # A plain cell (explicit or defaulted) is exactly one item, so its counts are pinned
    # to 1 and a preferred item count is meaningless.
    if entry.get("text_format", _PLAIN_TEXT_FORMAT) == _PLAIN_TEXT_FORMAT:
        for field, value in (("min_items", min_items), ("max_items", max_items)):
            if value is not None and value != 1:
                issues.append(
                    (
                        "plain_requires_single_item",
                        _TABLE_CONFIG_TAG,
                        f"{where} {field} must be 1 for a plain cell.",
                    )
                )
        if target_items is not None:
            issues.append(
                (
                    "plain_forbids_target_items",
                    _TABLE_CONFIG_TAG,
                    f"{where} target_items is not valid for a plain cell, which is always one item.",
                )
            )
    return issues


def _cell_label(entry: Mapping[str, Any]) -> str:
    """A ``"Cell (row,col):"`` prefix; falls back to ``"Cell:"`` for missing coordinates."""
    row = entry.get("row")
    col = entry.get("col")
    if _is_index(row) and _is_index(col):
        return f"Cell ({row},{col}):"
    return "Cell:"


def _is_index(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0

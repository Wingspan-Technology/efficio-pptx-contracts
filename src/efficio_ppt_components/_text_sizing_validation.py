"""Cross-field text sizing validation (kept out of ``tag_validation`` for size).

Pure logic: given a raw tag map and the set of tags that already carry a structural
issue, return ``(code, tag_name, message)`` tuples for the semantic problems JSON
Schema cannot express. The caller wraps these into its own issue type. The
``target_*`` tags are optional AI guidance; the min/max tags are strict bounds:

- optional ``target_chars`` <= ``max_chars``;
- optional ``target_chars_per_item`` within [``min_chars_per_item``, ``max_chars_per_item``];
- ``min_items`` <= ``max_items``; ``min_chars_per_item`` <= ``max_chars_per_item``;
- ``plain`` text is exactly one item (``min_items`` == ``max_items`` == 1).

None of these bounds is encoded in ``validation.json`` (targets never appear there).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

_TEXT_FORMAT_TAG = "efficio_text_format"
_PLAIN_TEXT_FORMAT = "plain"
_MAX_CHARS_TAG = "efficio_max_chars"
_TARGET_CHARS_TAG = "efficio_target_chars"
_MIN_ITEMS_TAG = "efficio_min_items"
_MAX_ITEMS_TAG = "efficio_max_items"
_MIN_CHARS_PER_ITEM_TAG = "efficio_min_chars_per_item"
_MAX_CHARS_PER_ITEM_TAG = "efficio_max_chars_per_item"
_TARGET_CHARS_PER_ITEM_TAG = "efficio_target_chars_per_item"


def text_sizing_issues(
    tags: Mapping[str, str], prior_issue_tags: Iterable[str]
) -> list[tuple[str, str, str]]:
    """Return ``(code, tag_name, message)`` for each cross-field text sizing violation.

    Each check is skipped when an operand is missing/blank or already carries a
    structural issue (so a non-integer/zero value is reported once, structurally, with
    no noisy follow-on); the remaining values are known-good positive integers.
    """
    skip = set(prior_issue_tags)

    def value_of(tag: str) -> int | None:
        raw = tags.get(tag)
        if raw is None or not raw.strip() or tag in skip:
            return None
        return int(raw.strip())

    max_chars = value_of(_MAX_CHARS_TAG)
    target_chars = value_of(_TARGET_CHARS_TAG)
    min_items = value_of(_MIN_ITEMS_TAG)
    max_items = value_of(_MAX_ITEMS_TAG)
    min_per_item = value_of(_MIN_CHARS_PER_ITEM_TAG)
    max_per_item = value_of(_MAX_CHARS_PER_ITEM_TAG)
    target_per_item = value_of(_TARGET_CHARS_PER_ITEM_TAG)

    issues: list[tuple[str, str, str]] = []

    def exceeds(tag: str, other: str) -> None:
        issues.append(("target_exceeds_max", tag, f"Tag {tag} must not exceed {other}."))

    # Optional targets must fit within their strict bounds.
    if target_chars is not None and max_chars is not None and target_chars > max_chars:
        exceeds(_TARGET_CHARS_TAG, _MAX_CHARS_TAG)
    if target_per_item is not None and max_per_item is not None and target_per_item > max_per_item:
        exceeds(_TARGET_CHARS_PER_ITEM_TAG, _MAX_CHARS_PER_ITEM_TAG)
    if target_per_item is not None and min_per_item is not None and target_per_item < min_per_item:
        issues.append(
            (
                "target_below_min",
                _TARGET_CHARS_PER_ITEM_TAG,
                f"Tag {_TARGET_CHARS_PER_ITEM_TAG} must be at least {_MIN_CHARS_PER_ITEM_TAG}.",
            )
        )
    # Strict min <= max ranges.
    if min_items is not None and max_items is not None and min_items > max_items:
        issues.append(
            ("min_exceeds_max", _MIN_ITEMS_TAG, f"Tag {_MIN_ITEMS_TAG} must not exceed {_MAX_ITEMS_TAG}.")
        )
    if min_per_item is not None and max_per_item is not None and min_per_item > max_per_item:
        issues.append(
            (
                "min_exceeds_max",
                _MIN_CHARS_PER_ITEM_TAG,
                f"Tag {_MIN_CHARS_PER_ITEM_TAG} must not exceed {_MAX_CHARS_PER_ITEM_TAG}.",
            )
        )
    # plain text is exactly one item.
    if tags.get(_TEXT_FORMAT_TAG) == _PLAIN_TEXT_FORMAT:
        for tag, value in ((_MIN_ITEMS_TAG, min_items), (_MAX_ITEMS_TAG, max_items)):
            if value is not None and value != 1:
                issues.append(
                    ("plain_requires_single_item", tag, f"Tag {tag} must be 1 for plain text.")
                )
    return issues

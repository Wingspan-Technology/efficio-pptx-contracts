"""Typed value objects shared by slide-selection group parsing and validation."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from .errors import EfficioComponentsError

SLIDE_SELECTION_GROUPS_TAG = "efficio_slide_selection_groups"


class SlideSelectionGroupType(StrEnum):
    CHOICE = "choice"
    BUNDLE = "bundle"


class SlideSelectionGroupIssueCode(StrEnum):
    INVALID_JSON = "invalid_json"
    INVALID_SHAPE = "invalid_shape"
    MISSING_CONTRACT = "missing_contract"
    DUPLICATE_GROUP_ID = "duplicate_group_id"
    UNKNOWN_MEMBER = "unknown_member"
    MULTIPLE_PARENTS = "multiple_parents"
    CYCLE = "cycle"
    ROOT_POLICY_REQUIRED = "root_policy_required"
    NESTED_POLICY_FORBIDDEN = "nested_policy_forbidden"
    INVALID_SINGLETON = "invalid_singleton"
    NO_SLIDE_DESCENDANT = "no_slide_descendant"
    GROUPED_SLIDE_POLICY = "grouped_slide_policy"
    DUPLICATE_SELECTED_SLIDE = "duplicate_selected_slide"
    UNKNOWN_SELECTED_SLIDE = "unknown_selected_slide"
    ROOT_POLICY_VIOLATION = "root_policy_violation"
    CHOICE_SELECTION = "choice_selection"
    BUNDLE_SELECTION = "bundle_selection"


@dataclass(frozen=True)
class SlideSelectionGroupIssue:
    code: SlideSelectionGroupIssueCode
    message: str
    path: tuple[str | int, ...] = ()
    group_id: str | None = None
    member_id: str | None = None


class SlideSelectionGroupContractError(EfficioComponentsError):
    """Raised when authored selection-group JSON or graph semantics are invalid."""

    def __init__(self, issues: Iterable[SlideSelectionGroupIssue]) -> None:
        self.issues = tuple(issues)
        if not self.issues:
            raise ValueError("SlideSelectionGroupContractError requires at least one issue")
        first_code = self.issues[0].code.value
        super().__init__(
            f"Slide-selection groups are invalid ({len(self.issues)} issue(s); "
            f"first code: {first_code})."
        )


@dataclass(frozen=True)
class SlideSelectionGroup:
    group_id: str
    name: str
    group_type: SlideSelectionGroupType
    members: tuple[str, ...]
    inclusion_policy: str | None = None
    instruction: str | None = None


@dataclass(frozen=True)
class SlideSelectionGroupRegistry:
    groups: Mapping[str, SlideSelectionGroup]
    root_group_ids: tuple[str, ...]
    slide_ids: tuple[str, ...]
    grouped_slide_ids: tuple[str, ...]
    singleton_slide_ids: tuple[str, ...]

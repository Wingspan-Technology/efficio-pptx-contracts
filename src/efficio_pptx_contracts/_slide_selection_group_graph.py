"""Graph normalization and final-selection checks for slide-selection groups."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from ._slide_selection_group_models import (
    SlideSelectionGroup,
    SlideSelectionGroupContractError,
    SlideSelectionGroupIssue,
    SlideSelectionGroupIssueCode,
    SlideSelectionGroupRegistry,
    SlideSelectionGroupType,
)

_HARD_SLIDE_POLICIES = frozenset({"always", "never"})


def normalize_slide_selection_groups(
    groups: Iterable[SlideSelectionGroup],
    *,
    slide_inclusion_policies: Mapping[str, str],
) -> SlideSelectionGroupRegistry:
    """Validate graph semantics and remove valid standalone singleton wrappers."""
    ordered_groups = tuple(groups)
    slide_ids = tuple(slide_inclusion_policies)
    known_slides = frozenset(slide_ids)
    issues: list[SlideSelectionGroupIssue] = []
    by_id: dict[str, SlideSelectionGroup] = {}
    index_by_id: dict[str, int] = {}
    for index, group in enumerate(ordered_groups):
        if group.group_id in by_id:
            issues.append(
                _issue(
                    SlideSelectionGroupIssueCode.DUPLICATE_GROUP_ID,
                    "A selection group ID is duplicated.",
                    index,
                    group,
                    "group_id",
                )
            )
            continue
        by_id[group.group_id] = group
        index_by_id[group.group_id] = index
    if issues:
        raise SlideSelectionGroupContractError(issues)

    parent_by_member: dict[str, str] = {}
    for group in ordered_groups:
        group_index = index_by_id[group.group_id]
        for member_index, member in enumerate(group.members):
            if member not in known_slides and member not in by_id:
                issues.append(
                    _issue(
                        SlideSelectionGroupIssueCode.UNKNOWN_MEMBER,
                        "A group member must reference a known slide or group.",
                        group_index,
                        group,
                        "members",
                        member_index,
                        member_id=member,
                    )
                )
                continue
            if member in parent_by_member:
                issues.append(
                    _issue(
                        SlideSelectionGroupIssueCode.MULTIPLE_PARENTS,
                        "A slide or nested group cannot belong to multiple groups.",
                        group_index,
                        group,
                        "members",
                        member_index,
                        member_id=member,
                    )
                )
                continue
            parent_by_member[member] = group.group_id

    issues.extend(_cycle_issues(ordered_groups, by_id, index_by_id))
    root_ids = tuple(group.group_id for group in ordered_groups if group.group_id not in parent_by_member)
    root_set = frozenset(root_ids)

    singleton_group_ids: set[str] = set()
    singleton_slide_ids: list[str] = []
    for group in ordered_groups:
        if len(group.members) != 1:
            continue
        member = group.members[0]
        if group.group_id in root_set and member in known_slides:
            singleton_group_ids.add(group.group_id)
            singleton_slide_ids.append(member)
            continue
        issues.append(
            _issue(
                SlideSelectionGroupIssueCode.INVALID_SINGLETON,
                "Only a root group containing one direct slide may be a singleton.",
                index_by_id[group.group_id],
                group,
                "members",
            )
        )

    for group in ordered_groups:
        if group.group_id in singleton_group_ids:
            continue
        index = index_by_id[group.group_id]
        if group.group_id in root_set and group.inclusion_policy is None:
            issues.append(
                _issue(
                    SlideSelectionGroupIssueCode.ROOT_POLICY_REQUIRED,
                    "A root selection group must declare inclusion_policy.",
                    index,
                    group,
                    "inclusion_policy",
                )
            )
        if group.group_id not in root_set and group.inclusion_policy is not None:
            issues.append(
                _issue(
                    SlideSelectionGroupIssueCode.NESTED_POLICY_FORBIDDEN,
                    "A nested selection group must not declare inclusion_policy.",
                    index,
                    group,
                    "inclusion_policy",
                )
            )

    blocking_codes = {
        SlideSelectionGroupIssueCode.CYCLE,
        SlideSelectionGroupIssueCode.UNKNOWN_MEMBER,
    }
    grouped_slides: set[str] = set()
    if not any(issue.code in blocking_codes for issue in issues):
        descendants = _slide_descendants(ordered_groups, by_id, known_slides)
        for group in ordered_groups:
            if not descendants[group.group_id]:
                issues.append(
                    _issue(
                        SlideSelectionGroupIssueCode.NO_SLIDE_DESCENDANT,
                        "A selection group must contain at least one slide descendant.",
                        index_by_id[group.group_id],
                        group,
                        "members",
                    )
                )

        grouped_slides = {
            member
            for group in ordered_groups
            if group.group_id not in singleton_group_ids
            for member in group.members
            if member in known_slides
        }
        for slide_id in slide_ids:
            policy = slide_inclusion_policies[slide_id]
            if slide_id in grouped_slides and policy in _HARD_SLIDE_POLICIES:
                issues.append(
                    SlideSelectionGroupIssue(
                        code=SlideSelectionGroupIssueCode.GROUPED_SLIDE_POLICY,
                        message="A grouped slide cannot use the always or never inclusion policy.",
                        member_id=slide_id,
                    )
                )

    if issues:
        raise SlideSelectionGroupContractError(issues)

    normalized_groups = {
        group.group_id: group for group in ordered_groups if group.group_id not in singleton_group_ids
    }
    return SlideSelectionGroupRegistry(
        groups=MappingProxyType(normalized_groups),
        root_group_ids=tuple(group_id for group_id in root_ids if group_id not in singleton_group_ids),
        slide_ids=slide_ids,
        grouped_slide_ids=tuple(slide_id for slide_id in slide_ids if slide_id in grouped_slides),
        singleton_slide_ids=tuple(singleton_slide_ids),
    )


def validate_slide_selection_group_selection(
    registry: SlideSelectionGroupRegistry,
    selected_slide_ids: Iterable[str],
) -> tuple[SlideSelectionGroupIssue, ...]:
    """Return deterministic issues when final selected IDs violate group rules."""
    selected: set[str] = set()
    issues: list[SlideSelectionGroupIssue] = []
    known_slides = frozenset(registry.slide_ids)
    for index, slide_id in enumerate(selected_slide_ids):
        if slide_id in selected:
            issues.append(
                SlideSelectionGroupIssue(
                    code=SlideSelectionGroupIssueCode.DUPLICATE_SELECTED_SLIDE,
                    message="The final slide selection contains a duplicate slide ID.",
                    path=("selected_slides", index),
                    member_id=slide_id,
                )
            )
        elif slide_id not in known_slides:
            issues.append(
                SlideSelectionGroupIssue(
                    code=SlideSelectionGroupIssueCode.UNKNOWN_SELECTED_SLIDE,
                    message="The final slide selection contains an unknown slide ID.",
                    path=("selected_slides", index),
                    member_id=slide_id,
                )
            )
        selected.add(slide_id)

    active_groups = _active_groups(registry.groups, selected)

    def member_active(member_id: str) -> bool:
        return active_groups[member_id] if member_id in registry.groups else member_id in selected

    for group in registry.groups.values():
        active_members = sum(member_active(member) for member in group.members)
        if group.group_type is SlideSelectionGroupType.CHOICE and active_members > 1:
            issues.append(
                _selection_issue(
                    SlideSelectionGroupIssueCode.CHOICE_SELECTION,
                    "An active choice group must select exactly one direct member.",
                    group,
                )
            )
        if (
            group.group_type is SlideSelectionGroupType.BUNDLE
            and active_members > 0
            and active_members != len(group.members)
        ):
            issues.append(
                _selection_issue(
                    SlideSelectionGroupIssueCode.BUNDLE_SELECTION,
                    "An active bundle group must select every direct member.",
                    group,
                )
            )

    for root_id in registry.root_group_ids:
        root = registry.groups[root_id]
        active = active_groups[root_id]
        if root.inclusion_policy == "always" and not active:
            issues.append(
                _selection_issue(
                    SlideSelectionGroupIssueCode.ROOT_POLICY_VIOLATION,
                    "An always root selection group must be active.",
                    root,
                )
            )
        if root.inclusion_policy == "never" and active:
            issues.append(
                _selection_issue(
                    SlideSelectionGroupIssueCode.ROOT_POLICY_VIOLATION,
                    "A never root selection group must remain inactive.",
                    root,
                )
            )
    return tuple(issues)


def _cycle_issues(
    groups: tuple[SlideSelectionGroup, ...],
    by_id: Mapping[str, SlideSelectionGroup],
    index_by_id: Mapping[str, int],
) -> list[SlideSelectionGroupIssue]:
    state: dict[str, int] = {}
    issues: list[SlideSelectionGroupIssue] = []

    for first_group in groups:
        if state.get(first_group.group_id, 0) != 0:
            continue
        state[first_group.group_id] = 1
        stack = [(first_group.group_id, 0)]
        while stack:
            group_id, member_index = stack[-1]
            group = by_id[group_id]
            if member_index >= len(group.members):
                state[group_id] = 2
                stack.pop()
                continue
            stack[-1] = (group_id, member_index + 1)
            member = group.members[member_index]
            if member not in by_id:
                continue
            if state.get(member) == 1:
                issues.append(
                    _issue(
                        SlideSelectionGroupIssueCode.CYCLE,
                        "Selection groups must not contain a reference cycle.",
                        index_by_id[group_id],
                        group,
                        "members",
                        member_index,
                        member_id=member,
                    )
                )
            elif state.get(member, 0) == 0:
                state[member] = 1
                stack.append((member, 0))
    return issues


def _slide_descendants(
    groups: tuple[SlideSelectionGroup, ...],
    by_id: Mapping[str, SlideSelectionGroup],
    known_slides: frozenset[str],
) -> dict[str, frozenset[str]]:
    result: dict[str, frozenset[str]] = {}
    group_ids = (group.group_id for group in groups)
    for group_id in _postorder_group_ids(group_ids, by_id):
        slides: set[str] = set()
        for member in by_id[group_id].members:
            if member in known_slides:
                slides.add(member)
            elif member in by_id:
                slides.update(result[member])
        result[group_id] = frozenset(slides)
    return result


def _active_groups(
    groups: Mapping[str, SlideSelectionGroup], selected: set[str]
) -> dict[str, bool]:
    active: dict[str, bool] = {}
    for group_id in _postorder_group_ids(groups, groups):
        active[group_id] = any(
            active[member] if member in groups else member in selected
            for member in groups[group_id].members
        )
    return active


def _postorder_group_ids(
    group_ids: Iterable[str], by_id: Mapping[str, SlideSelectionGroup]
) -> tuple[str, ...]:
    """Return child-before-parent IDs for an already cycle-free group graph."""
    complete: set[str] = set()
    result: list[str] = []
    for first_group_id in group_ids:
        if first_group_id in complete:
            continue
        stack = [(first_group_id, False)]
        while stack:
            group_id, expanded = stack.pop()
            if group_id in complete:
                continue
            if expanded:
                complete.add(group_id)
                result.append(group_id)
                continue
            stack.append((group_id, True))
            for member in reversed(by_id[group_id].members):
                if member in by_id and member not in complete:
                    stack.append((member, False))
    return tuple(result)


def _issue(
    code: SlideSelectionGroupIssueCode,
    message: str,
    group_index: int,
    group: SlideSelectionGroup,
    *path: str | int,
    member_id: str | None = None,
) -> SlideSelectionGroupIssue:
    return SlideSelectionGroupIssue(
        code=code,
        message=message,
        path=(group_index, *path),
        group_id=group.group_id,
        member_id=member_id,
    )


def _selection_issue(
    code: SlideSelectionGroupIssueCode,
    message: str,
    group: SlideSelectionGroup,
) -> SlideSelectionGroupIssue:
    return SlideSelectionGroupIssue(
        code=code,
        message=message,
        path=("groups", group.group_id),
        group_id=group.group_id,
    )

"""Pure template contract migration planning over opaque tagged targets."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from ._template_contract_migration_catalog import (
    CURRENT_TEMPLATE_CONTRACT_REVISION,
    TEMPLATE_CONTRACT_REVISION_TAG,
    UNVERSIONED_TEMPLATE_CONTRACT_REVISION,
    RenameTagOperation,
    SetTagIfMissingOperation,
    TemplateContractMigration,
    TemplateContractMigrationCatalog,
    TemplateContractMigrationOperation,
    TemplateMigrationOperationType,
    TemplateTagScope,
    get_template_contract_migration_path,
    load_template_contract_migration_catalog,
)
from .errors import TemplateContractMigrationError

_REVISION = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class TemplateTagTarget:
    target_ref: str
    scope: TemplateTagScope
    tags: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class TemplateTagPatch:
    target_ref: str
    scope: TemplateTagScope
    set_tags: Mapping[str, str]
    remove_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TemplateContractMigrationPlan:
    from_revision: int
    to_revision: int
    patches: tuple[TemplateTagPatch, ...]


def plan_template_contract_migration(
    targets: Sequence[TemplateTagTarget],
) -> TemplateContractMigrationPlan:
    """Plan deterministic set/remove patches without mutating caller-owned tags."""
    prepared = _prepare_targets(targets)
    deck_indexes = [
        index for index, (target, _tags) in enumerate(prepared)
        if target.scope is TemplateTagScope.DECK
    ]
    if len(deck_indexes) != 1:
        raise TemplateContractMigrationError(
            "template migration requires exactly one deck target"
        )
    deck_index = deck_indexes[0]
    from_revision = _read_revision(prepared[deck_index][1])
    path = get_template_contract_migration_path(from_revision)
    original = [dict(tags) for _target, tags in prepared]
    for migration in path:
        for operation in migration.operations:
            _apply_operation(prepared, operation)
    prepared[deck_index][1][TEMPLATE_CONTRACT_REVISION_TAG] = str(
        CURRENT_TEMPLATE_CONTRACT_REVISION
    )
    _validate_no_retired_tags(prepared)
    patches = tuple(
        patch for index, (target, tags) in enumerate(prepared)
        if (patch := _build_patch(target, original[index], tags)) is not None
    )
    return TemplateContractMigrationPlan(
        from_revision=from_revision,
        to_revision=CURRENT_TEMPLATE_CONTRACT_REVISION,
        patches=patches,
    )


def _validate_no_retired_tags(
    targets: Sequence[tuple[TemplateTagTarget, Mapping[str, str]]],
) -> None:
    retired = {
        (operation.scope, operation.source_tag)
        for migration in load_template_contract_migration_catalog().migrations
        for operation in migration.operations
        if isinstance(operation, RenameTagOperation)
    }
    for target, tags in targets:
        if any(scope is target.scope and tag in tags for scope, tag in retired):
            raise TemplateContractMigrationError(
                "current template contract contains a retired tag"
            )


def _prepare_targets(
    targets: Sequence[TemplateTagTarget],
) -> list[tuple[TemplateTagTarget, dict[str, str]]]:
    prepared: list[tuple[TemplateTagTarget, dict[str, str]]] = []
    identities: set[tuple[TemplateTagScope, str]] = set()
    for target in targets:
        try:
            scope = TemplateTagScope(target.scope)
        except ValueError as error:
            raise TemplateContractMigrationError("template target scope is invalid") from error
        if not isinstance(target.target_ref, str) or not target.target_ref.strip():
            raise TemplateContractMigrationError("template target_ref must be non-empty")
        identity = (scope, target.target_ref)
        if identity in identities:
            raise TemplateContractMigrationError("template target references must be unique")
        identities.add(identity)
        if not isinstance(target.tags, Mapping) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in target.tags.items()
        ):
            raise TemplateContractMigrationError("template target tags must map strings to strings")
        prepared.append((TemplateTagTarget(target.target_ref, scope, target.tags), dict(target.tags)))
    return prepared


def _read_revision(deck_tags: Mapping[str, str]) -> int:
    raw = deck_tags.get(TEMPLATE_CONTRACT_REVISION_TAG)
    if raw is None:
        return UNVERSIONED_TEMPLATE_CONTRACT_REVISION
    if _REVISION.fullmatch(raw) is None:
        raise TemplateContractMigrationError(
            f"{TEMPLATE_CONTRACT_REVISION_TAG} must be a non-negative integer string"
        )
    revision = int(raw)
    if revision > CURRENT_TEMPLATE_CONTRACT_REVISION:
        raise TemplateContractMigrationError(
            f"template contract revision {revision} is newer than supported revision "
            f"{CURRENT_TEMPLATE_CONTRACT_REVISION}"
        )
    return revision


def _apply_operation(
    targets: list[tuple[TemplateTagTarget, dict[str, str]]],
    operation: TemplateContractMigrationOperation,
) -> None:
    for target, tags in targets:
        if target.scope is not operation.scope:
            continue
        if isinstance(operation, SetTagIfMissingOperation):
            if operation.tag not in tags:
                tags[operation.tag] = operation.value
            continue
        source = tags.get(operation.source_tag)
        if source is None:
            continue
        mapped = source
        if operation.value_map is not None:
            mapped_value = operation.value_map.get(source)
            if mapped_value is None:
                raise TemplateContractMigrationError(
                    f"tag {operation.source_tag} has no migration mapping"
                )
            mapped = mapped_value
        existing = tags.get(operation.target_tag)
        if existing is not None and existing != mapped:
            raise TemplateContractMigrationError(
                f"tag {operation.target_tag} conflicts with migrated content"
            )
        tags[operation.target_tag] = mapped
        del tags[operation.source_tag]


def _build_patch(
    target: TemplateTagTarget,
    original: Mapping[str, str],
    migrated: Mapping[str, str],
) -> TemplateTagPatch | None:
    set_tags = {
        key: migrated[key]
        for key in sorted(migrated)
        if original.get(key) != migrated[key]
    }
    remove_tags = tuple(sorted(set(original) - set(migrated)))
    if not set_tags and not remove_tags:
        return None
    return TemplateTagPatch(
        target_ref=target.target_ref,
        scope=target.scope,
        set_tags=MappingProxyType(set_tags),
        remove_tags=remove_tags,
    )


__all__ = [
    "CURRENT_TEMPLATE_CONTRACT_REVISION", "TEMPLATE_CONTRACT_REVISION_TAG",
    "UNVERSIONED_TEMPLATE_CONTRACT_REVISION", "RenameTagOperation",
    "SetTagIfMissingOperation", "TemplateContractMigration",
    "TemplateContractMigrationCatalog", "TemplateContractMigrationOperation",
    "TemplateContractMigrationPlan", "TemplateContractMigrationError",
    "TemplateMigrationOperationType", "TemplateTagPatch", "TemplateTagScope",
    "TemplateTagTarget", "get_template_contract_migration_path",
    "load_template_contract_migration_catalog", "plan_template_contract_migration",
]

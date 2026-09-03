"""Immutable models and generated-resource parsing for template migrations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TypeAlias, TypeGuard

from ._resources import load_json
from .errors import TemplateContractMigrationError

TEMPLATE_CONTRACT_REVISION_TAG = "efficio_template_contract_revision"
UNVERSIONED_TEMPLATE_CONTRACT_REVISION = 0
TEMPLATE_MIGRATION_FORMAT_VERSION = 1
_RESOURCE = ("schemas", "presentation", "template-contract-migrations.json")
_TAG_NAME = re.compile(r"^efficio_[a-z][a-z0-9_]*$")


class TemplateTagScope(StrEnum):
    DECK = "deck"
    SLIDE = "slide"
    SHAPE = "shape"


class TemplateMigrationOperationType(StrEnum):
    SET_TAG_IF_MISSING = "set_tag_if_missing"
    RENAME_TAG = "rename_tag"


@dataclass(frozen=True, slots=True)
class SetTagIfMissingOperation:
    scope: TemplateTagScope
    tag: str
    value: str
    operation_type: TemplateMigrationOperationType = (
        TemplateMigrationOperationType.SET_TAG_IF_MISSING
    )


@dataclass(frozen=True, slots=True)
class RenameTagOperation:
    scope: TemplateTagScope
    source_tag: str
    target_tag: str
    value_map: Mapping[str, str] | None
    operation_type: TemplateMigrationOperationType = (
        TemplateMigrationOperationType.RENAME_TAG
    )


TemplateContractMigrationOperation: TypeAlias = (
    SetTagIfMissingOperation | RenameTagOperation
)


@dataclass(frozen=True, slots=True)
class TemplateContractMigration:
    from_revision: int
    to_revision: int
    description: str
    operations: tuple[TemplateContractMigrationOperation, ...]


@dataclass(frozen=True, slots=True)
class TemplateContractMigrationCatalog:
    format_version: int
    unversioned_revision: int
    current_revision: int
    revision_tag: str
    migrations: tuple[TemplateContractMigration, ...]


def load_template_contract_migration_catalog() -> TemplateContractMigrationCatalog:
    """Load and validate an immutable copy of the generated migration catalog."""
    return _parse_catalog(load_json(*_RESOURCE))


def get_template_contract_migration_path(
    from_revision: int,
) -> tuple[TemplateContractMigration, ...]:
    """Return the contiguous path from ``from_revision`` to the current revision."""
    catalog = load_template_contract_migration_catalog()
    _validate_requested_revision(from_revision, catalog.current_revision)
    by_source = {migration.from_revision: migration for migration in catalog.migrations}
    path: list[TemplateContractMigration] = []
    revision = from_revision
    while revision < catalog.current_revision:
        migration = by_source.get(revision)
        if migration is None:
            raise TemplateContractMigrationError(
                f"no template contract migration exists from revision {revision}"
            )
        path.append(migration)
        revision = migration.to_revision
    return tuple(path)


def _parse_catalog(raw: Mapping[str, object]) -> TemplateContractMigrationCatalog:
    expected = {
        "generated_from", "contract_type", "format_version", "unversioned_revision",
        "current_revision", "revision_tag", "migrations",
    }
    if set(raw) != expected or raw.get("contract_type") != "template_contract_migrations":
        raise TemplateContractMigrationError("template migration catalog fields are invalid")
    if not _is_revision(raw.get("format_version")) or (
        raw["format_version"] != TEMPLATE_MIGRATION_FORMAT_VERSION
    ):
        raise TemplateContractMigrationError("template migration catalog format is unsupported")
    if not _is_revision(raw.get("unversioned_revision")) or (
        raw["unversioned_revision"] != UNVERSIONED_TEMPLATE_CONTRACT_REVISION
    ):
        raise TemplateContractMigrationError("template migration baseline is unsupported")
    if raw.get("revision_tag") != TEMPLATE_CONTRACT_REVISION_TAG:
        raise TemplateContractMigrationError("template migration revision tag is invalid")
    migrations_raw = raw.get("migrations")
    if not isinstance(migrations_raw, list):
        raise TemplateContractMigrationError("template migration catalog migrations must be an array")
    migrations = tuple(_parse_migration(value) for value in migrations_raw)
    expected_revision = UNVERSIONED_TEMPLATE_CONTRACT_REVISION
    for migration in migrations:
        if migration.from_revision != expected_revision:
            raise TemplateContractMigrationError("template migration catalog has a gap or branch")
        expected_revision = migration.to_revision
    if not _is_revision(raw.get("current_revision")) or (
        raw["current_revision"] != expected_revision
    ):
        raise TemplateContractMigrationError("template migration current revision is inconsistent")
    _validate_generated_from(raw.get("generated_from"), migrations)
    return TemplateContractMigrationCatalog(
        format_version=TEMPLATE_MIGRATION_FORMAT_VERSION,
        unversioned_revision=UNVERSIONED_TEMPLATE_CONTRACT_REVISION,
        current_revision=expected_revision,
        revision_tag=TEMPLATE_CONTRACT_REVISION_TAG,
        migrations=migrations,
    )


def _parse_migration(raw: object) -> TemplateContractMigration:
    if not isinstance(raw, Mapping):
        raise TemplateContractMigrationError("template migration must be an object")
    fields = {
        "format_version", "contract_type", "from_revision", "to_revision",
        "description", "operations",
    }
    if (
        set(raw) != fields
        or not _is_revision(raw.get("format_version"))
        or raw["format_version"] != TEMPLATE_MIGRATION_FORMAT_VERSION
    ):
        raise TemplateContractMigrationError("template migration fields are invalid")
    if raw.get("contract_type") != "template_contract_migration":
        raise TemplateContractMigrationError("template migration type is invalid")
    source, target = raw.get("from_revision"), raw.get("to_revision")
    description, operations_raw = raw.get("description"), raw.get("operations")
    if (
        not _is_revision(source) or not _is_revision(target) or target != source + 1
        or not isinstance(description, str) or not description.strip()
        or not isinstance(operations_raw, list) or not operations_raw
    ):
        raise TemplateContractMigrationError("template migration content is invalid")
    operations = tuple(_parse_operation(value) for value in operations_raw)
    _validate_operation_conflicts(operations)
    return TemplateContractMigration(
        from_revision=source,
        to_revision=target,
        description=description,
        operations=operations,
    )


def _parse_operation(raw: object) -> TemplateContractMigrationOperation:
    if not isinstance(raw, Mapping):
        raise TemplateContractMigrationError("template migration operation must be an object")
    raw_scope = raw.get("scope")
    if not isinstance(raw_scope, str):
        raise TemplateContractMigrationError("template migration scope is invalid")
    try:
        scope = TemplateTagScope(raw_scope)
    except ValueError as error:
        raise TemplateContractMigrationError("template migration scope is invalid") from error
    if raw.get("type") == TemplateMigrationOperationType.SET_TAG_IF_MISSING:
        if set(raw) != {"type", "scope", "tag", "value"}:
            raise TemplateContractMigrationError("set_tag_if_missing fields are invalid")
        tag, value = raw.get("tag"), raw.get("value")
        if not _is_tag_name(tag) or not isinstance(value, str):
            raise TemplateContractMigrationError("set_tag_if_missing values are invalid")
        return SetTagIfMissingOperation(scope=scope, tag=tag, value=value)
    if raw.get("type") != TemplateMigrationOperationType.RENAME_TAG:
        raise TemplateContractMigrationError("template migration operation type is invalid")
    allowed = {"type", "scope", "source_tag", "target_tag", "value_map"}
    required = {"type", "scope", "source_tag", "target_tag"}
    if not required <= set(raw) or not set(raw) <= allowed:
        raise TemplateContractMigrationError("rename_tag fields are invalid")
    source, target = raw.get("source_tag"), raw.get("target_tag")
    if not _is_tag_name(source) or not _is_tag_name(target) or source == target:
        raise TemplateContractMigrationError("rename_tag names are invalid")
    value_map = raw.get("value_map")
    if value_map is not None and not _is_string_map(value_map):
        raise TemplateContractMigrationError("rename_tag value_map is invalid")
    return RenameTagOperation(
        scope=scope,
        source_tag=source,
        target_tag=target,
        value_map=None if value_map is None else MappingProxyType(dict(value_map)),
    )


def _is_string_map(value: object) -> TypeGuard[Mapping[str, str]]:
    return (
        isinstance(value, Mapping) and bool(value)
        and all(
            isinstance(key, str)
            and bool(key)
            and isinstance(item, str)
            for key, item in value.items()
        )
    )


def _validate_generated_from(
    value: object, migrations: tuple[TemplateContractMigration, ...]
) -> None:
    expected = [
        "contracts/presentation/template/migrations/"
        f"{migration.from_revision:04d}-to-{migration.to_revision:04d}.json"
        for migration in migrations
    ]
    if value != expected:
        raise TemplateContractMigrationError(
            "template migration generated_from paths are inconsistent"
        )


def _validate_operation_conflicts(
    operations: tuple[TemplateContractMigrationOperation, ...],
) -> None:
    touched: set[tuple[TemplateTagScope, str]] = set()
    for operation in operations:
        tags = (
            (operation.tag,)
            if isinstance(operation, SetTagIfMissingOperation)
            else (operation.source_tag, operation.target_tag)
        )
        for tag in tags:
            identity = operation.scope, tag
            if identity in touched:
                raise TemplateContractMigrationError(
                    "template migration operations conflict"
                )
            touched.add(identity)


def _is_tag_name(value: object) -> TypeGuard[str]:
    return isinstance(value, str) and _TAG_NAME.fullmatch(value) is not None


def _validate_requested_revision(revision: int, current: int) -> None:
    if not _is_revision(revision):
        raise TemplateContractMigrationError("template contract revision must be non-negative")
    if revision > current:
        raise TemplateContractMigrationError(
            f"template contract revision {revision} is newer than supported revision {current}"
        )


def _is_revision(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


CURRENT_TEMPLATE_CONTRACT_REVISION = (
    load_template_contract_migration_catalog().current_revision
)

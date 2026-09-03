import { readdir } from "node:fs/promises";
import path from "node:path";

import {
  assertObject,
  isValidEfficioTagName,
  type JsonObject,
} from "./contractLib.js";
import { readJson } from "./generatorIo.js";
import { presentationTemplateMigrationsDir } from "./generatorPaths.js";
import { validateStoredTagValue } from "./storedTagValueContractLib.js";

const FILE_PATTERN = /^(\d{4})-to-(\d{4})\.json$/;
const SCOPES = new Set(["deck", "slide", "shape"]);
const MIGRATION_FIELDS = new Set([
  "format_version",
  "contract_type",
  "from_revision",
  "to_revision",
  "description",
  "operations",
]);
const SET_FIELDS = new Set(["type", "scope", "tag", "value"]);
const RENAME_FIELDS = new Set([
  "type",
  "scope",
  "source_tag",
  "target_tag",
  "value_map",
]);

export const TEMPLATE_MIGRATION_FORMAT_VERSION = 1;
export const UNVERSIONED_TEMPLATE_CONTRACT_REVISION = 0;
export const TEMPLATE_CONTRACT_REVISION_TAG = "efficio_template_contract_revision";

export type TemplateContractMigrationCatalog = JsonObject & {
  format_version: number;
  unversioned_revision: number;
  current_revision: number;
  revision_tag: string;
  migrations: JsonObject[];
};

export async function loadTemplateContractMigrationCatalog(
  migrationsDir = presentationTemplateMigrationsDir,
): Promise<TemplateContractMigrationCatalog> {
  const entries = await readdir(migrationsDir, { withFileTypes: true });
  if (entries.length === 0) {
    throw new Error("template migration directory must contain at least one migration");
  }

  const sources: { label: string; migration: JsonObject }[] = [];
  for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
    if (!entry.isFile() || FILE_PATTERN.exec(entry.name) === null) {
      throw new Error(`template migration filename ${JSON.stringify(entry.name)} is invalid`);
    }
    const label = `contracts/presentation/template/migrations/${entry.name}`;
    const value = await readJson(path.join(migrationsDir, entry.name));
    assertObject(value, label);
    validateTemplateContractMigration(value, label, entry.name);
    sources.push({ label, migration: value });
  }

  validateMigrationChain(sources);
  const currentRevision = sources.at(-1)?.migration.to_revision;
  if (!isRevision(currentRevision)) {
    throw new Error("template migration chain has no valid current revision");
  }
  return {
    generated_from: sources.map(({ label }) => label),
    contract_type: "template_contract_migrations",
    format_version: TEMPLATE_MIGRATION_FORMAT_VERSION,
    unversioned_revision: UNVERSIONED_TEMPLATE_CONTRACT_REVISION,
    current_revision: currentRevision,
    revision_tag: TEMPLATE_CONTRACT_REVISION_TAG,
    migrations: sources.map(({ migration }) => migration),
  };
}

export function validateTemplateContractRevisionTag(
  catalog: TemplateContractMigrationCatalog,
  deckSchema: JsonObject,
  deckDefaults: Record<string, string>,
): void {
  const tags = deckSchema.tags;
  assertObject(tags, "deck tag contract tags");
  const entity = tags[TEMPLATE_CONTRACT_REVISION_TAG];
  assertObject(entity, `deck tag ${TEMPLATE_CONTRACT_REVISION_TAG}`);
  if (entity.type !== "integer" || entity.required !== true || entity.minimum !== 1) {
    throw new Error(
      `${TEMPLATE_CONTRACT_REVISION_TAG} must be a required integer tag with minimum 1`,
    );
  }
  if ((entity.ui as JsonObject | undefined)?.hidden !== true) {
    throw new Error(`${TEMPLATE_CONTRACT_REVISION_TAG} must set ui.hidden to true`);
  }
  if (deckDefaults[TEMPLATE_CONTRACT_REVISION_TAG] !== String(catalog.current_revision)) {
    throw new Error(
      `${TEMPLATE_CONTRACT_REVISION_TAG} default must equal current template contract revision`,
    );
  }
}

export function validateMigrationTargetTags(
  catalog: TemplateContractMigrationCatalog,
  tagDefinitionsByScope: Record<string, Record<string, JsonObject>>,
): void {
  for (const migration of catalog.migrations) {
    const operations = migration.operations as JsonObject[];
    for (const operation of operations) {
      const targetTag = operation.type === "rename_tag" ? operation.target_tag : operation.tag;
      if (typeof targetTag !== "string") continue;
      const scope = operation.scope as string;
      const tagDefinitions = tagDefinitionsByScope[scope] ?? {};
      const definition = tagDefinitions[targetTag];
      if (definition === undefined) {
        throw new Error(`migration target tag ${targetTag} is not defined by the current contracts`);
      }
      const values = operation.type === "rename_tag"
        ? operation.value_map === undefined
          ? []
          : Object.values(operation.value_map as JsonObject)
        : [operation.value];
      for (const value of values) {
        validateStoredTagValue(targetTag, value, definition, "template migration target");
      }
    }
  }
}

export function validateTemplateContractMigration(
  migration: JsonObject,
  label: string,
  fileName: string,
): void {
  assertExactFields(migration, MIGRATION_FIELDS, label);
  if (migration.format_version !== TEMPLATE_MIGRATION_FORMAT_VERSION) {
    throw new Error(`${label}.format_version must be ${TEMPLATE_MIGRATION_FORMAT_VERSION}`);
  }
  if (migration.contract_type !== "template_contract_migration") {
    throw new Error(`${label}.contract_type must be template_contract_migration`);
  }
  const fromRevision = migration.from_revision;
  const toRevision = migration.to_revision;
  if (!isRevision(fromRevision) || !isRevision(toRevision) || toRevision !== fromRevision + 1) {
    throw new Error(`${label} must advance exactly one non-negative revision`);
  }
  const match = FILE_PATTERN.exec(fileName);
  if (!match || Number(match[1]) !== fromRevision || Number(match[2]) !== toRevision) {
    throw new Error(`${label} filename must match its from_revision and to_revision`);
  }
  if (typeof migration.description !== "string" || migration.description.trim() === "") {
    throw new Error(`${label}.description must be a non-empty string`);
  }
  if (!Array.isArray(migration.operations) || migration.operations.length === 0) {
    throw new Error(`${label}.operations must be a non-empty array`);
  }
  const touched = new Set<string>();
  migration.operations.forEach((operation, index) => {
    const operationLabel = `${label}.operations[${index}]`;
    assertObject(operation, operationLabel);
    validateOperation(operation, operationLabel, touched);
  });
}

function validateMigrationChain(sources: { label: string; migration: JsonObject }[]): void {
  let expected = UNVERSIONED_TEMPLATE_CONTRACT_REVISION;
  for (const { label, migration } of sources) {
    if (migration.from_revision !== expected) {
      throw new Error(`${label} creates a gap or branch at revision ${expected}`);
    }
    expected = migration.to_revision as number;
  }
}

function validateOperation(operation: JsonObject, label: string, touched: Set<string>): void {
  if (operation.type === "set_tag_if_missing") {
    assertExactFields(operation, SET_FIELDS, label);
    validateScopeAndTag(operation.scope, operation.tag, label);
    if (typeof operation.value !== "string") throw new Error(`${label}.value must be a string`);
    markTouched(touched, operation.scope as string, operation.tag as string, label);
    return;
  }
  if (operation.type !== "rename_tag") {
    throw new Error(`${label}.type must be rename_tag or set_tag_if_missing`);
  }
  const allowed = new Set(RENAME_FIELDS);
  if (operation.value_map === undefined) allowed.delete("value_map");
  assertExactFields(operation, allowed, label);
  validateScopeAndTag(operation.scope, operation.source_tag, label);
  validateScopeAndTag(operation.scope, operation.target_tag, label);
  if (operation.source_tag === operation.target_tag) {
    throw new Error(`${label} source_tag and target_tag must differ`);
  }
  if (operation.value_map !== undefined) {
    assertObject(operation.value_map, `${label}.value_map`);
    if (Object.keys(operation.value_map).length === 0) {
      throw new Error(`${label}.value_map must not be empty`);
    }
    for (const [source, target] of Object.entries(operation.value_map)) {
      if (source === "" || typeof target !== "string") {
        throw new Error(`${label}.value_map must map non-empty strings to strings`);
      }
    }
  }
  markTouched(touched, operation.scope as string, operation.source_tag as string, label);
  markTouched(touched, operation.scope as string, operation.target_tag as string, label);
}

function validateScopeAndTag(scope: unknown, tag: unknown, label: string): void {
  if (typeof scope !== "string" || !SCOPES.has(scope)) {
    throw new Error(`${label}.scope must be deck, slide, or shape`);
  }
  if (typeof tag !== "string" || !isValidEfficioTagName(tag)) {
    throw new Error(`${label} must reference a valid Efficio tag`);
  }
}

function markTouched(touched: Set<string>, scope: string, tag: string, label: string): void {
  const key = `${scope}:${tag}`;
  if (touched.has(key)) throw new Error(`${label} conflicts with another operation on ${key}`);
  touched.add(key);
}

function assertExactFields(value: JsonObject, fields: Set<string>, label: string): void {
  const actual = Object.keys(value).sort();
  const expected = [...fields].sort();
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`${label} must contain exactly ${expected.join(", ")}`);
  }
}

function isRevision(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

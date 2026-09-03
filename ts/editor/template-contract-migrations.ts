import { templateContractMigrationCatalog } from "../../generated/ts/presentation/templateContractMigrations.js";
import { copyContractValue } from "./contract-copy.js";

export const TEMPLATE_CONTRACT_REVISION_TAG = "efficio_template_contract_revision";
export const UNVERSIONED_TEMPLATE_CONTRACT_REVISION = 0;
export const CURRENT_TEMPLATE_CONTRACT_REVISION = templateContractMigrationCatalog.current_revision;

export type TemplateTagScope = "deck" | "slide" | "shape";
export type SetTagIfMissingOperation = Readonly<{
  type: "set_tag_if_missing";
  scope: TemplateTagScope;
  tag: string;
  value: string;
}>;
export type RenameTagOperation = Readonly<{
  type: "rename_tag";
  scope: TemplateTagScope;
  source_tag: string;
  target_tag: string;
  value_map?: Readonly<Record<string, string>>;
}>;
export type TemplateContractMigrationOperation = SetTagIfMissingOperation | RenameTagOperation;
export type TemplateContractMigration = Readonly<{
  format_version: 1;
  contract_type: "template_contract_migration";
  from_revision: number;
  to_revision: number;
  description: string;
  operations: readonly TemplateContractMigrationOperation[];
}>;
export type TemplateContractMigrationCatalog = Readonly<{
  generated_from: readonly string[];
  contract_type: "template_contract_migrations";
  format_version: 1;
  unversioned_revision: 0;
  current_revision: number;
  revision_tag: typeof TEMPLATE_CONTRACT_REVISION_TAG;
  migrations: readonly TemplateContractMigration[];
}>;
export type TemplateTagTarget = Readonly<{
  target_ref: string;
  scope: TemplateTagScope;
  tags: Readonly<Record<string, string>>;
}>;
export type TemplateTagPatch = Readonly<{
  target_ref: string;
  scope: TemplateTagScope;
  set_tags: Readonly<Record<string, string>>;
  remove_tags: readonly string[];
}>;
export type TemplateContractMigrationPlan = Readonly<{
  from_revision: number;
  to_revision: number;
  patches: readonly TemplateTagPatch[];
}>;

export class TemplateContractMigrationError extends Error {
  override readonly name = "TemplateContractMigrationError";
}

const catalog = templateContractMigrationCatalog as unknown as TemplateContractMigrationCatalog;

export function getTemplateContractMigrationCatalog(): TemplateContractMigrationCatalog {
  return copyContractValue(catalog);
}

export function getTemplateContractMigrationPath(
  fromRevision: number,
): readonly TemplateContractMigration[] {
  validateRevision(fromRevision);
  const bySource = new Map(catalog.migrations.map((migration) => [migration.from_revision, migration]));
  const path: TemplateContractMigration[] = [];
  let revision = fromRevision;
  while (revision < CURRENT_TEMPLATE_CONTRACT_REVISION) {
    const migration = bySource.get(revision);
    if (!migration) {
      throw new TemplateContractMigrationError(
        `No template contract migration exists from revision ${revision}.`,
      );
    }
    path.push(copyContractValue(migration));
    revision = migration.to_revision;
  }
  return path;
}

export function planTemplateContractMigration(
  targets: readonly TemplateTagTarget[],
): TemplateContractMigrationPlan {
  const prepared = prepareTargets(targets);
  const deckIndexes = prepared.flatMap((entry, index) => entry.target.scope === "deck" ? [index] : []);
  if (deckIndexes.length !== 1) {
    throw new TemplateContractMigrationError("Template migration requires exactly one deck target.");
  }
  const deckIndex = deckIndexes[0];
  const fromRevision = readRevision(prepared[deckIndex].tags);
  const path = getTemplateContractMigrationPath(fromRevision);
  const originals = prepared.map(({ tags }) => ({ ...tags }));
  for (const migration of path) {
    for (const operation of migration.operations) applyOperation(prepared, operation);
  }
  prepared[deckIndex].tags[TEMPLATE_CONTRACT_REVISION_TAG] = String(CURRENT_TEMPLATE_CONTRACT_REVISION);
  validateNoRetiredTags(prepared);
  const patches = prepared.flatMap(({ target, tags }, index) => {
    const patch = buildPatch(target, originals[index], tags);
    return patch ? [patch] : [];
  });
  return { from_revision: fromRevision, to_revision: CURRENT_TEMPLATE_CONTRACT_REVISION, patches };
}

function validateNoRetiredTags(targets: PreparedTarget[]): void {
  for (const migration of catalog.migrations) {
    for (const operation of migration.operations) {
      if (operation.type !== "rename_tag") continue;
      if (targets.some(({ target, tags }) =>
        target.scope === operation.scope && operation.source_tag in tags
      )) {
        throw new TemplateContractMigrationError(
          "Current template contract contains a retired tag.",
        );
      }
    }
  }
}

type PreparedTarget = { target: TemplateTagTarget; tags: Record<string, string> };

function prepareTargets(targets: readonly TemplateTagTarget[]): PreparedTarget[] {
  if (!Array.isArray(targets)) {
    throw new TemplateContractMigrationError("Template targets must be an array.");
  }
  const identities = new Set<string>();
  return targets.map((target) => {
    if (typeof target !== "object" || target === null) {
      throw new TemplateContractMigrationError("Template target must be an object.");
    }
    if (typeof target.target_ref !== "string" || !target.target_ref.trim()) {
      throw new TemplateContractMigrationError("Template target_ref must be non-empty.");
    }
    if (!(["deck", "slide", "shape"] as const).includes(target.scope)) {
      throw new TemplateContractMigrationError("Template target scope is invalid.");
    }
    const identity = `${target.scope}\u0000${target.target_ref}`;
    if (identities.has(identity)) {
      throw new TemplateContractMigrationError("Template target references must be unique.");
    }
    identities.add(identity);
    if (typeof target.tags !== "object" || target.tags === null || Array.isArray(target.tags)) {
      throw new TemplateContractMigrationError("Template target tags must map strings to strings.");
    }
    if (Object.values(target.tags).some((value) => typeof value !== "string")) {
      throw new TemplateContractMigrationError("Template target tags must map strings to strings.");
    }
    return { target: { ...target, tags: { ...target.tags } }, tags: { ...target.tags } };
  });
}

function readRevision(deckTags: Readonly<Record<string, string>>): number {
  const raw = deckTags[TEMPLATE_CONTRACT_REVISION_TAG];
  if (raw === undefined) return UNVERSIONED_TEMPLATE_CONTRACT_REVISION;
  if (!/^[0-9]+$/.test(raw)) {
    throw new TemplateContractMigrationError(
      `${TEMPLATE_CONTRACT_REVISION_TAG} must be a non-negative integer string.`,
    );
  }
  const revision = Number(raw);
  validateRevision(revision);
  return revision;
}

function validateRevision(revision: number): void {
  if (!Number.isSafeInteger(revision) || revision < 0) {
    throw new TemplateContractMigrationError("Template contract revision must be non-negative.");
  }
  if (revision > CURRENT_TEMPLATE_CONTRACT_REVISION) {
    throw new TemplateContractMigrationError(
      `Template contract revision ${revision} is newer than supported revision ${CURRENT_TEMPLATE_CONTRACT_REVISION}.`,
    );
  }
}

function applyOperation(targets: PreparedTarget[], operation: TemplateContractMigrationOperation): void {
  for (const { target, tags } of targets) {
    if (target.scope !== operation.scope) continue;
    if (operation.type === "set_tag_if_missing") {
      if (!(operation.tag in tags)) tags[operation.tag] = operation.value;
      continue;
    }
    const source = tags[operation.source_tag];
    if (source === undefined) continue;
    const mapped = operation.value_map ? operation.value_map[source] : source;
    if (mapped === undefined) {
      throw new TemplateContractMigrationError(`Tag ${operation.source_tag} has no migration mapping.`);
    }
    const existing = tags[operation.target_tag];
    if (existing !== undefined && existing !== mapped) {
      throw new TemplateContractMigrationError(
        `Tag ${operation.target_tag} conflicts with migrated content.`,
      );
    }
    tags[operation.target_tag] = mapped;
    delete tags[operation.source_tag];
  }
}

function buildPatch(
  target: TemplateTagTarget,
  original: Readonly<Record<string, string>>,
  migrated: Readonly<Record<string, string>>,
): TemplateTagPatch | undefined {
  const set_tags = Object.fromEntries(
    Object.keys(migrated).sort().flatMap((key) => original[key] === migrated[key] ? [] : [[key, migrated[key]]]),
  );
  const remove_tags = Object.keys(original).filter((key) => !(key in migrated)).sort();
  if (Object.keys(set_tags).length === 0 && remove_tags.length === 0) return undefined;
  return { target_ref: target.target_ref, scope: target.scope, set_tags, remove_tags };
}

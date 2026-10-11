import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  CURRENT_TEMPLATE_CONTRACT_REVISION,
  TEMPLATE_CONTRACT_REVISION_TAG,
  getTemplateContractMigrationCatalog,
  getTemplateContractMigrationPath,
  planTemplateContractMigration,
  type TemplateContractMigrationPlan,
  type TemplateTagTarget,
} from "../ts/editor";

type Fixture = {
  successful_cases: {
    name: string;
    targets: TemplateTagTarget[];
    expected: unknown;
  }[];
  error_cases: {
    name: string;
    targets: TemplateTagTarget[];
    error_contains: string;
  }[];
};

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  readFileSync(
    path.join(here, "fixtures", "template-contract-migration-cases.json"),
    "utf8",
  ),
) as Fixture;

describe("template contract migration catalog", () => {
  it("derives the current revision from one contiguous adjacent migration", () => {
    const catalog = getTemplateContractMigrationCatalog();
    expect(CURRENT_TEMPLATE_CONTRACT_REVISION).toBe(5);
    expect(catalog.revision_tag).toBe(TEMPLATE_CONTRACT_REVISION_TAG);
    expect(catalog.migrations.map(({ from_revision, to_revision }) => [from_revision, to_revision]))
      .toEqual([[0, 1], [1, 2], [2, 3], [3, 4], [4, 5]]);
    expect(catalog.migrations[1].operations).toEqual([
      { type: "migrate_text_capacity", scope: "shape" },
    ]);
    expect(getTemplateContractMigrationPath(0)).toEqual(catalog.migrations);
  });

  it("carries the revision-only and strict-character migrations", () => {
    const catalog = getTemplateContractMigrationCatalog();
    const revisionOnly = catalog.migrations[2];
    expect(revisionOnly.from_revision).toBe(2);
    expect(revisionOnly.to_revision).toBe(3);
    expect(revisionOnly.operations).toEqual([]);
    const strictCharacters = catalog.migrations[3];
    expect(strictCharacters.operations).toEqual([
      { type: "derive_text_character_limits", scope: "shape" },
    ]);
    const dataTopics = catalog.migrations[4];
    expect(getTemplateContractMigrationPath(2)).toEqual([
      revisionOnly,
      strictCharacters,
      dataTopics,
    ]);
    expect(getTemplateContractMigrationPath(3)).toEqual([strictCharacters, dataTopics]);
  });

  it("carries a revision-only 4 to 5 data-topic migration with no operations", () => {
    const catalog = getTemplateContractMigrationCatalog();
    const dataTopics = catalog.migrations[4];
    expect(dataTopics.from_revision).toBe(4);
    expect(dataTopics.to_revision).toBe(5);
    expect(dataTopics.operations).toEqual([]);
    expect(getTemplateContractMigrationPath(4)).toEqual([dataTopics]);
    expect(getTemplateContractMigrationPath(5)).toEqual([]);
  });

  it("returns a defensive catalog copy", () => {
    const catalog = getTemplateContractMigrationCatalog() as {
      migrations: { description: string }[];
    };
    catalog.migrations[0].description = "mutated";
    expect(getTemplateContractMigrationCatalog().migrations[0].description).not.toBe("mutated");
  });
});

describe("template contract migration planner parity", () => {
  for (const testCase of fixture.successful_cases) {
    it(testCase.name, () => {
      const before = structuredClone(testCase.targets);
      expect(planTemplateContractMigration(testCase.targets)).toEqual(testCase.expected);
      expect(testCase.targets).toEqual(before);
    });
  }

  for (const testCase of fixture.successful_cases) {
    it(`re-planning after applying is a no-op: ${testCase.name}`, () => {
      const migrated = applyPlan(testCase.targets, planTemplateContractMigration(testCase.targets));
      expect(planTemplateContractMigration(migrated)).toEqual({
        from_revision: CURRENT_TEMPLATE_CONTRACT_REVISION,
        to_revision: CURRENT_TEMPLATE_CONTRACT_REVISION,
        patches: [],
      });
    });
  }

  for (const testCase of fixture.error_cases) {
    it(testCase.name, () => {
      expect(() => planTemplateContractMigration(testCase.targets)).toThrow(
        testCase.error_contains,
      );
    });
  }

  it.each(["", " 1", "1.0", "-1", "true"])(
    "rejects malformed revision %j",
    (revision) => {
      expect(() =>
        planTemplateContractMigration([
          {
            target_ref: "deck",
            scope: "deck",
            tags: { [TEMPLATE_CONTRACT_REVISION_TAG]: revision },
          },
        ]),
      ).toThrow("integer string");
    },
  );

  it("rejects future revisions", () => {
    expect(() =>
      planTemplateContractMigration([
        {
          target_ref: "deck",
          scope: "deck",
          tags: { [TEMPLATE_CONTRACT_REVISION_TAG]: "6" },
        },
      ]),
    ).toThrow("newer than supported");
  });
});

// Applies a plan's set/remove patches to copies of the targets, the way a
// consumer applies them to PowerPoint tags before re-validating.
function applyPlan(
  targets: readonly TemplateTagTarget[],
  plan: TemplateContractMigrationPlan,
): TemplateTagTarget[] {
  return targets.map((target) => {
    const tags: Record<string, string> = { ...target.tags };
    for (const patch of plan.patches) {
      if (patch.scope !== target.scope || patch.target_ref !== target.target_ref) continue;
      Object.assign(tags, patch.set_tags);
      for (const tag of patch.remove_tags) delete tags[tag];
    }
    return { ...target, tags };
  });
}

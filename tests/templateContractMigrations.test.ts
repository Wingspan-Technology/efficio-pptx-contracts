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
    expect(CURRENT_TEMPLATE_CONTRACT_REVISION).toBe(1);
    expect(catalog.revision_tag).toBe(TEMPLATE_CONTRACT_REVISION_TAG);
    expect(catalog.migrations.map(({ from_revision, to_revision }) => [from_revision, to_revision]))
      .toEqual([[0, 1]]);
    expect(getTemplateContractMigrationPath(0)).toEqual(catalog.migrations);
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
          tags: { [TEMPLATE_CONTRACT_REVISION_TAG]: "2" },
        },
      ]),
    ).toThrow("newer than supported");
  });
});

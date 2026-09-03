import { afterEach, describe, expect, it } from "vitest";
import { cp, mkdtemp, readFile, rename, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { validateAllContracts } from "../scripts/contractValidation";

const here = path.dirname(fileURLToPath(import.meta.url));
const realContractsDir = path.resolve(here, "..", "contracts");

describe("validateAllContracts — real contracts", () => {
  it("reports the authored contracts as valid with no issues", async () => {
    const report = await validateAllContracts();
    expect(report.issues).toEqual([]);
    expect(report.ok).toBe(true);
    expect(report.checked).toBeGreaterThan(0);
  });
});

describe("validateAllContracts — structured report over an injected contracts dir", () => {
  let workDir: string | undefined;

  afterEach(async () => {
    if (workDir) await rm(workDir, { recursive: true, force: true });
    workDir = undefined;
  });

  async function copyContracts(): Promise<string> {
    workDir = await mkdtemp(path.join(tmpdir(), "efficio-contracts-"));
    const dir = path.join(workDir, "contracts");
    await cp(realContractsDir, dir, { recursive: true });
    return dir;
  }

  async function mutateJson(file: string, mutate: (value: Record<string, unknown>) => void): Promise<void> {
    const value = JSON.parse(await readFile(file, "utf8")) as Record<string, unknown>;
    mutate(value);
    await writeFile(file, `${JSON.stringify(value, null, 2)}\n`);
  }

  it("collects rule violations without throwing, and points at the offending contracts", async () => {
    const dir = await copyContracts();

    // Rule 1: a structurally valid tag entity with a non-conforming name.
    await mutateJson(path.join(dir, "components", "text", "tags.contract.json"), (contract) => {
      (contract.tags as Record<string, unknown>).BadTagName = { type: "string", required: false };
    });
    // Rule 2: an object-tag default that parses but violates its embedded schema.
    await mutateJson(path.join(dir, "components", "table", "tags.defaults.json"), (defaults) => {
      defaults.efficio_table_config = '{"cells":"not-an-array"}';
    });

    const report = await validateAllContracts({ contractsDir: dir });

    expect(report.ok).toBe(false);
    expect(
      report.issues.some(
        (issue) =>
          issue.contract === "contracts/components/text/tags.contract.json" &&
          /BadTagName is not a valid Efficio tag name/.test(issue.message),
      ),
    ).toBe(true);
    expect(
      report.issues.some(
        (issue) =>
          issue.contract === "contracts/components/table/tags.defaults.json" &&
          /does not match its tag schema/.test(issue.message),
      ),
    ).toBe(true);
  });

  it("returns ok for an untouched copy of the real contracts", async () => {
    const dir = await copyContracts();
    const report = await validateAllContracts({ contractsDir: dir });
    expect(report.ok).toBe(true);
    expect(report.issues).toEqual([]);
  });

  it("rejects selection-group policies that drift from slide policies", async () => {
    const dir = await copyContracts();
    await mutateJson(path.join(dir, "presentation", "deck", "tags.contract.json"), (contract) => {
      const tags = contract.tags as Record<string, unknown>;
      const groupTag = tags.efficio_slide_selection_groups as Record<string, unknown>;
      const schema = groupTag.schema as Record<string, unknown>;
      const item = schema.items as Record<string, unknown>;
      const properties = item.properties as Record<string, unknown>;
      const policy = properties.inclusion_policy as Record<string, unknown>;
      policy.enum = ["always", "never"];
    });

    const report = await validateAllContracts({ contractsDir: dir });

    expect(report.ok).toBe(false);
    expect(
      report.issues.some(
        (issue) =>
          issue.contract === "presentation slide-selection groups" &&
          /must exactly match slide inclusion policies/.test(issue.message),
      ),
    ).toBe(true);
  });

  it("rejects migration filenames that disagree with their revisions", async () => {
    const dir = await copyContracts();
    const migrations = path.join(dir, "presentation", "template", "migrations");
    await rename(
      path.join(migrations, "0000-to-0001.json"),
      path.join(migrations, "0000-to-0002.json"),
    );

    const report = await validateAllContracts({ contractsDir: dir });

    expect(report.ok).toBe(false);
    expect(report.issues.some((issue) => /filename must match/.test(issue.message))).toBe(true);
  });

  it("rejects migration gaps and unknown fields or operations", async () => {
    const dir = await copyContracts();
    const migrations = path.join(dir, "presentation", "template", "migrations");
    const original = path.join(migrations, "0000-to-0001.json");
    const gap = path.join(migrations, "0001-to-0002.json");
    await mutateJson(original, (migration) => {
      migration.from_revision = 1;
      migration.to_revision = 2;
    });
    await rename(original, gap);
    let report = await validateAllContracts({ contractsDir: dir });
    expect(report.issues.some((issue) => /gap or branch/.test(issue.message))).toBe(true);

    await mutateJson(gap, (migration) => {
      migration.unexpected = true;
    });
    report = await validateAllContracts({ contractsDir: dir });
    expect(report.issues.some((issue) => /must contain exactly/.test(issue.message))).toBe(true);

    await mutateJson(gap, (migration) => {
      delete migration.unexpected;
      const operations = migration.operations as Record<string, unknown>[];
      operations[0].type = "unknown";
    });
    report = await validateAllContracts({ contractsDir: dir });
    expect(report.issues.some((issue) => /must be rename_tag or set_tag_if_missing/.test(issue.message)))
      .toBe(true);
  });

  it("rejects conflicting operations within one migration", async () => {
    const dir = await copyContracts();
    const migration = path.join(
      dir,
      "presentation",
      "template",
      "migrations",
      "0000-to-0001.json",
    );
    await mutateJson(migration, (value) => {
      const operations = value.operations as Record<string, unknown>[];
      operations.push({
        type: "set_tag_if_missing",
        scope: "shape",
        tag: "efficio_content_mode",
        value: "ai_generated",
      });
    });

    const report = await validateAllContracts({ contractsDir: dir });

    expect(report.issues.some((issue) => /conflicts with another operation/.test(issue.message)))
      .toBe(true);
  });

  it("rejects migration values that violate the target tag contract", async () => {
    const dir = await copyContracts();
    const migration = path.join(
      dir,
      "presentation",
      "template",
      "migrations",
      "0000-to-0001.json",
    );
    await mutateJson(migration, (value) => {
      const operations = value.operations as Record<string, unknown>[];
      operations[0].tag = "efficio_template_id";
      operations[0].value = "Invalid Template Id";
    });

    const report = await validateAllContracts({ contractsDir: dir });

    expect(
      report.issues.some(
        (issue) =>
          issue.contract === "template contract revision" &&
          /efficio_template_id does not match its required pattern/.test(issue.message),
      ),
    ).toBe(true);
  });
});

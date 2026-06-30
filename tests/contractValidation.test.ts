import { afterEach, describe, expect, it } from "vitest";
import { cp, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
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
    await mutateJson(path.join(dir, "components", "approval_block", "tags.defaults.json"), (defaults) => {
      defaults.efficio_label_cell = '{"row":9,"col":0}';
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
          issue.contract === "contracts/components/approval_block/tags.defaults.json" &&
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
});

import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { componentRegistry } from "../generated/ts/componentRegistry";
import type { JsonObject } from "../scripts/contractLib";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const componentsDir = path.join(pkgRoot, "contracts", "components");

function readJson(filePath: string): JsonObject {
  return JSON.parse(readFileSync(filePath, "utf8")) as JsonObject;
}

const registryJson = readJson(path.join(pkgRoot, "generated", "component-registry.json"));
const components = registryJson.components as Record<string, Record<string, string>>;

function discoverComponents(): string[] {
  return readdirSync(componentsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

describe("generated component registry", () => {
  it("contains no presentation or shared contract folders", () => {
    expect(components).not.toHaveProperty("presentation");
    expect(components).not.toHaveProperty("shared");
  });

  it("includes exactly the discovered component folders", () => {
    expect(Object.keys(components).sort()).toEqual(discoverComponents());
  });

  it("is deterministic (component keys sorted)", () => {
    const keys = Object.keys(components);
    expect(keys).toEqual([...keys].sort());
  });

  it("points each component at existing contract and defaults files", () => {
    for (const [componentType, entry] of Object.entries(components)) {
      expect(entry.tags_contract).toBe(`contracts/components/${componentType}/tags.contract.json`);
      expect(entry.content_contract).toBe(`contracts/components/${componentType}/content.contract.json`);
      expect(entry.tags_defaults).toBe(`contracts/components/${componentType}/tags.defaults.json`);
      for (const relPath of Object.values(entry)) {
        expect(existsSync(path.join(pkgRoot, relPath))).toBe(true);
      }
    }
  });

  it("TS registry mirrors the JSON registry exactly", () => {
    expect(componentRegistry).toEqual(registryJson);
  });

  it("has a generated defaults export for every registry component", () => {
    for (const componentType of Object.keys(components)) {
      const camel = componentType.replace(/_([a-z])/g, (_m, c: string) => c.toUpperCase());
      const exportFile = path.join(pkgRoot, "generated", "ts", "components", `${camel}Defaults.ts`);
      expect(existsSync(exportFile)).toBe(true);
    }
  });
});

import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { Ajv2020 } from "ajv/dist/2020.js";
import { validateTagEntityContract, type JsonObject } from "../scripts/contractLib";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const srcDir = path.join(pkgRoot, "src");
const contractsDir = path.join(pkgRoot, "contracts");
const componentsDir = path.join(contractsDir, "components");
const sharedDir = path.join(contractsDir, "shared");
const presentationDir = path.join(contractsDir, "presentation");
const sharedTagFragments = [
  "render-behavior-tags.contract.json",
  "component-base-tags.contract.json",
];

function readJson(filePath: string): JsonObject {
  return JSON.parse(readFileSync(filePath, "utf8")) as JsonObject;
}

function discoverComponents(): string[] {
  return readdirSync(componentsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

function walkFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === "__pycache__") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walkFiles(full));
    else out.push(full);
  }
  return out;
}

const components = discoverComponents();

describe("component discovery", () => {
  it("scans only contracts/components (authored contracts live outside the Python src/ package)", () => {
    // Authored contract sources live under contracts/, not under the Python SDK src/.
    expect(readdirSync(contractsDir, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => entry.name)).toEqual(
      expect.arrayContaining(["components", "presentation", "shared"]),
    );
    expect(readdirSync(srcDir, { withFileTypes: true }).filter((entry) => entry.isDirectory()).map((entry) => entry.name)).toEqual(
      ["efficio_pptx_contracts"],
    );
    expect(components).not.toContain("presentation");
    expect(components).not.toContain("shared");
  });

  it("discovers the expected components deterministically", () => {
    expect(components).toEqual(["category_chart", "table", "text"]);
  });
});

describe.each(components)("component %s", (component) => {
  const dir = path.join(componentsDir, component);

  it("has tags.contract.json, content.contract.json, and tags.defaults.json", () => {
    expect(existsSync(path.join(dir, "tags.contract.json"))).toBe(true);
    expect(existsSync(path.join(dir, "content.contract.json"))).toBe(true);
    expect(existsSync(path.join(dir, "tags.defaults.json"))).toBe(true);
  });

  it("has no defaults.ts (component defaults are JSON, generated to TS)", () => {
    expect(existsSync(path.join(dir, "defaults.ts"))).toBe(false);
  });

  it("tags.contract.json uses the Tag Entity shape and validates", () => {
    const contract = readJson(path.join(dir, "tags.contract.json"));
    expect(contract.tags).toBeTypeOf("object");
    expect(() => validateTagEntityContract(contract, `contracts/components/${component}/tags.contract.json`, { componentType: component })).not.toThrow();
  });

  it("content.contract.json is a valid JSON Schema Draft 2020-12", () => {
    const schema = readJson(path.join(dir, "content.contract.json"));
    const ajv = new Ajv2020({ strict: false });
    expect(() => ajv.compile(schema)).not.toThrow();
  });

  it("content.contract.json is a self-describing schema (declares $schema and an object type)", () => {
    const schema = readJson(path.join(dir, "content.contract.json"));
    expect(schema.$schema).toBe("https://json-schema.org/draft/2020-12/schema");
    // A content schema declares an object root: type may be "object" or an array
    // of types that includes "object" (a nullable root remains permitted).
    const type = schema.type;
    const declaresObject = type === "object" || (Array.isArray(type) && type.includes("object"));
    expect(declaresObject).toBe(true);
  });
});

describe("shared contract fragments", () => {
  it.each(sharedTagFragments)("validates %s with no component_type", (fileName) => {
    const label = `contracts/shared/${fileName}`;
    const contract = readJson(path.join(sharedDir, fileName));
    expect(contract.tags).toBeTypeOf("object");
    expect(() => validateTagEntityContract(contract, label, {})).not.toThrow();
  });

  it("contains only JSON contract fragments and defaults", () => {
    const files = readdirSync(sharedDir, { withFileTypes: true }).map((entry) => entry.name).sort();
    expect(files).toEqual([
      "component-base-tags.contract.json",
      "component-default-tags.defaults.json",
      "render-behavior-tags.contract.json",
      "tag-definition.schema.json",
    ]);
  });
});

describe("text content contract (Step 4 target shape)", () => {
  const schema = readJson(path.join(componentsDir, "text", "content.contract.json"));

  it("is Draft 2020-12 with the stable { items: string[] } shape", () => {
    expect(schema.$schema).toBe("https://json-schema.org/draft/2020-12/schema");
    expect(schema.type).toBe("object");
    expect(schema.additionalProperties).toBe(false);
    expect(schema.required).toEqual(["items"]);
    const items = (schema.properties as JsonObject).items as JsonObject;
    expect(items.type).toBe("array");
    expect(items.minItems).toBe(1);
    expect((items.items as JsonObject).type).toBe("string");
    expect((items.items as JsonObject).minLength).toBe(1);
  });

  it("no longer exposes the legacy top-level content string", () => {
    expect((schema.properties as JsonObject).content).toBeUndefined();
  });
});

describe("presentation contracts", () => {
  it("keeps slide/template contracts outside component discovery", () => {
    expect(existsSync(path.join(presentationDir, "slide", "tags.contract.json"))).toBe(true);
    expect(existsSync(path.join(presentationDir, "slide", "tags.defaults.json"))).toBe(true);
    expect(existsSync(path.join(presentationDir, "slide", "slide.contract.json"))).toBe(true);
    expect(existsSync(path.join(presentationDir, "template", "template.contract.json"))).toBe(true);
    expect(components).toEqual(["category_chart", "table", "text"]);
  });

  it("slide tags.contract.json uses the Tag Entity shape and validates as a slide contract", () => {
    const label = "contracts/presentation/slide/tags.contract.json";
    const contract = readJson(path.join(presentationDir, "slide", "tags.contract.json"));
    expect(contract.contract_type).toBe("slide_tags");
    expect(contract).not.toHaveProperty("component_type");
    expect(contract.tags).toBeTypeOf("object");
    for (const field of ["required_tags", "optional_tags", "enums", "types", "max_lengths", "conditional_required_tags", "conditional_disallowed_tags"]) {
      expect(contract).not.toHaveProperty(field);
    }
    expect(() => validateTagEntityContract(contract, label, { slideContractType: "slide_tags" })).not.toThrow();
  });
});

describe("no legacy filenames", () => {
  it("has no output.schema.json references left in authored contracts", () => {
    const offenders = walkFiles(contractsDir).filter((file) => {
      if (path.basename(file) === "output.schema.json") return true;
      if (!/\.(ts|json|py)$/.test(file)) return false;
      return readFileSync(file, "utf8").includes("output.schema.json");
    });
    expect(offenders).toEqual([]);
  });
});

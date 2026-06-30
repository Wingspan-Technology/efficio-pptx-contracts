import { readdir } from "node:fs/promises";
import path from "node:path";

import {
  assertNoDefaults,
  assertObject,
  assertTextContentShape,
  assertValidJsonSchema,
  getRecord,
  validateTagEntityContract,
  type JsonObject,
} from "./contractLib.js";
import { readJson } from "./generatorIo.js";
import { componentsDir, sharedDir, sharedTagFragmentNames } from "./generatorPaths.js";

export type ComponentSource = {
  componentType: string;
  label: string;
  schema: JsonObject;
  contentContract: JsonObject;
};

export type SharedTagContract = {
  labels: string[];
  schema: JsonObject;
};

export async function loadComponentSources(): Promise<ComponentSource[]> {
  const entries = await readdir(componentsDir, { withFileTypes: true });
  const sources: ComponentSource[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const sourcePath = path.join(componentsDir, entry.name, "tags.contract.json");
    const label = `contracts/components/${entry.name}/tags.contract.json`;
    const schema = await readJson(sourcePath).catch((error: unknown) => {
      throw new Error(`Could not read ${label}. Every component folder must include tags.contract.json.`, {
        cause: error,
      });
    });

    assertObject(schema, label);
    assertNoDefaults(schema, label);
    validateTagEntityContract(schema, label, { componentType: entry.name });
    const contentContract = await loadAndValidateContentContract(entry.name);

    sources.push({ componentType: schema.component_type as string, label, schema, contentContract });
  }

  return sources.sort((left, right) => left.componentType.localeCompare(right.componentType));
}

async function loadAndValidateContentContract(componentName: string): Promise<JsonObject> {
  const label = `contracts/components/${componentName}/content.contract.json`;
  const schema = await readJson(path.join(componentsDir, componentName, "content.contract.json")).catch((error: unknown) => {
    throw new Error(`Could not read ${label}. Every component folder must include content.contract.json.`, {
      cause: error,
    });
  });

  assertObject(schema, label);
  assertValidJsonSchema(schema, label);
  if (componentName === "text") {
    assertTextContentShape(schema, label);
  }

  return schema;
}

export async function loadSharedTagContract(): Promise<SharedTagContract> {
  const schema: JsonObject = { description: "Shared tag contract fragments for all Efficio components.", tags: {} };
  const labels: string[] = [];

  for (const fileName of sharedTagFragmentNames) {
    const label = `contracts/shared/${fileName}`;
    const fragment = await readJson(path.join(sharedDir, fileName));
    assertObject(fragment, label);
    assertNoDefaults(fragment, label);
    validateTagEntityContract(fragment, label, {});

    const tags = getRecord(fragment, "tags");
    for (const tag of Object.keys(tags)) {
      if (tag in getRecord(schema, "tags")) {
        throw new Error(`${label}.tags.${tag} duplicates a shared tag fragment.`);
      }
      getRecord(schema, "tags")[tag] = tags[tag];
    }
    labels.push(label);
  }

  return { labels, schema };
}

// The authored general component instruction (a single non-empty string). Lives
// directly under contracts/components/ as a file, so component discovery (which
// scans only directories) ignores it. Mirrors the slides.instructions.json shape.
export async function loadComponentsInstruction(): Promise<string> {
  const label = "contracts/components/components.instructions.json";
  const value = await readJson(path.join(componentsDir, "components.instructions.json"));
  assertObject(value, label);
  return validateComponentsInstruction(value, label);
}

// Pure shape check: the file holds exactly one non-empty "instruction" string.
// Returns the instruction so the loader can hand it straight to the builders.
export function validateComponentsInstruction(value: JsonObject, label: string): string {
  const keys = Object.keys(value);
  if (keys.length !== 1 || keys[0] !== "instruction") {
    throw new Error(`${label} must contain only an "instruction" field.`);
  }
  if (typeof value.instruction !== "string" || value.instruction.trim().length === 0) {
    throw new Error(`${label}.instruction must be a non-empty string.`);
  }

  return value.instruction;
}

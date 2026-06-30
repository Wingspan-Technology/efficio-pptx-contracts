import path from "node:path";

import {
  assertNoDefaults,
  assertObject,
  assertValidJsonSchema,
  getRecord,
  validateTagEntityContract,
  type JsonObject,
} from "./contractLib.js";
import { readJson } from "./generatorIo.js";
import { presentationSlideDir } from "./generatorPaths.js";

export async function loadSlideTagSchema(): Promise<JsonObject> {
  const label = "contracts/presentation/slide/tags.contract.json";
  const schema = await readJson(path.join(presentationSlideDir, "tags.contract.json"));

  assertObject(schema, label);
  assertNoDefaults(schema, label);
  validateTagEntityContract(schema, label, { slideContractType: "slide_tags" });

  return schema;
}

export async function loadSlideDefaults(slideSchema: JsonObject): Promise<Record<string, string>> {
  const label = "contracts/presentation/slide/tags.defaults.json";
  const defaults = await readJson(path.join(presentationSlideDir, "tags.defaults.json"));
  assertObject(defaults, label);
  return validateSlideDefaults(defaults, slideSchema, label);
}

// Pure slide-defaults validation against the slide tag schema: every key must be
// a known slide tag, every value a string, and enum values must match. Shared by
// the loader (above) and the standalone contract validation.
export function validateSlideDefaults(
  defaults: JsonObject,
  slideSchema: JsonObject,
  label: string,
): Record<string, string> {
  const tags = getRecord(slideSchema, "tags");
  const knownTags = new Set(Object.keys(tags));
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(defaults)) {
    if (!knownTags.has(key)) throw new Error(`${label}.${key} is not a known slide tag.`);
    if (typeof value !== "string") throw new Error(`${label}.${key} must be a string value.`);
    const enumValues = getRecord(tags, key).enum;
    if (Array.isArray(enumValues) && !enumValues.includes(value)) {
      throw new Error(`${label}.${key} must be one of ${JSON.stringify(enumValues)}.`);
    }
    result[key] = value;
  }

  return result;
}

export async function loadSlidesInstructions(): Promise<JsonObject> {
  const label = "contracts/presentation/slide/slides.instructions.json";
  const value = await readJson(path.join(presentationSlideDir, "slides.instructions.json"));
  assertObject(value, label);
  validateSlidesInstructions(value, label);
  return value;
}

// Pure shape check: the file holds exactly one non-empty "description" string.
export function validateSlidesInstructions(value: JsonObject, label: string): void {
  const keys = Object.keys(value);
  if (keys.length !== 1 || keys[0] !== "description") {
    throw new Error(`${label} must contain only a "description" field.`);
  }
  if (typeof value.description !== "string" || value.description.trim().length === 0) {
    throw new Error(`${label}.description must be a non-empty string.`);
  }
}

export async function loadSlideSelectionSchema(): Promise<JsonObject> {
  const label = "contracts/presentation/slide/slide-selection.schema.json";
  const schema = await readJson(path.join(presentationSlideDir, "slide-selection.schema.json"));
  assertObject(schema, label);
  assertValidJsonSchema(schema, label);
  return schema;
}

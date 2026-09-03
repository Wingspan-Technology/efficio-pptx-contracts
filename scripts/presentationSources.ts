import path from "node:path";

import {
  assertNoDefaults,
  assertObject,
  assertStringArray,
  assertValidJsonSchema,
  getRecord,
  validateTagEntityContract,
  type JsonObject,
} from "./contractLib.js";
import { readJson } from "./generatorIo.js";
import { presentationDeckDir, presentationSlideDir } from "./generatorPaths.js";
import { validateStoredTagValue } from "./storedTagValueContractLib.js";

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

// Pure presentation-defaults validation against the native tag contract. Shared
// by the slide/deck loaders and the standalone contract validation.
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
    validateStoredTagValue(key, value, getRecord(tags, key), label);
    result[key] = value;
  }

  return result;
}

// Deck (presentation-level) tag contract + defaults. Mirrors the slide loaders;
// `validateSlideDefaults` is generic (validates defaults against a tag schema),
// so it is reused for the deck defaults too.
export async function loadDeckTagSchema(): Promise<JsonObject> {
  const label = "contracts/presentation/deck/tags.contract.json";
  const schema = await readJson(path.join(presentationDeckDir, "tags.contract.json"));

  assertObject(schema, label);
  assertNoDefaults(schema, label);
  validateTagEntityContract(schema, label, { slideContractType: "deck_tags" });

  return schema;
}

export async function loadDeckDefaults(deckSchema: JsonObject): Promise<Record<string, string>> {
  const label = "contracts/presentation/deck/tags.defaults.json";
  const defaults = await readJson(path.join(presentationDeckDir, "tags.defaults.json"));
  assertObject(defaults, label);
  return validateSlideDefaults(defaults, deckSchema, label);
}

export async function loadSlidesInstructions(): Promise<JsonObject> {
  const label = "contracts/presentation/slide/slides.instructions.json";
  const value = await readJson(path.join(presentationSlideDir, "slides.instructions.json"));
  assertObject(value, label);
  validateSlidesInstructions(value, label);
  return value;
}

const SELECTION_GROUP_TYPES = ["choice", "bundle"];

// Pure shape check for the reusable slide-selection prompt guidance.
export function validateSlidesInstructions(value: JsonObject, label: string): void {
  const keys = Object.keys(value).sort();
  if (JSON.stringify(keys) !== JSON.stringify(["description", "selection_group_instructions"])) {
    throw new Error(`${label} must contain description and selection_group_instructions.`);
  }
  if (typeof value.description !== "string" || value.description.trim().length === 0) {
    throw new Error(`${label}.description must be a non-empty string.`);
  }

  const groupInstructions = value.selection_group_instructions;
  assertObject(groupInstructions, `${label}.selection_group_instructions`);
  const instructionKeys = Object.keys(groupInstructions).sort();
  const expectedKeys = ["purpose", "rules", "type_descriptions"];
  if (JSON.stringify(instructionKeys) !== JSON.stringify(expectedKeys)) {
    throw new Error(`${label}.selection_group_instructions has unexpected fields.`);
  }
  if (typeof groupInstructions.purpose !== "string" || groupInstructions.purpose.trim().length === 0) {
    throw new Error(`${label}.selection_group_instructions.purpose must be a non-empty string.`);
  }
  assertDescriptionMap(
    groupInstructions.type_descriptions,
    SELECTION_GROUP_TYPES,
    `${label}.selection_group_instructions.type_descriptions`,
  );
  assertStringArray(groupInstructions.rules, `${label}.selection_group_instructions.rules`);
  if (groupInstructions.rules.length === 0 || groupInstructions.rules.some((rule) => rule.trim().length === 0)) {
    throw new Error(`${label}.selection_group_instructions.rules must contain non-empty strings.`);
  }
}

export function validateSelectionGroupContract(
  deckSchema: JsonObject,
  slideSchema: JsonObject,
  slidesInstructions: JsonObject,
  label: string,
): void {
  const deckTags = getRecord(deckSchema, "tags");
  const groupTag = getRecord(deckTags, "efficio_slide_selection_groups");
  if (groupTag.type !== "array" || groupTag.required !== false) {
    throw new Error(`${label} must define efficio_slide_selection_groups as an optional array tag.`);
  }
  const groupSchema = getRecord(groupTag, "schema");
  const groupItem = getRecord(groupSchema, "items");
  const groupProperties = getRecord(groupItem, "properties");
  const groupTypeValues = getRecord(groupProperties, "type").enum;
  if (
    !Array.isArray(groupTypeValues) ||
    JSON.stringify(groupTypeValues) !== JSON.stringify(SELECTION_GROUP_TYPES)
  ) {
    throw new Error(`${label} group type enum must be ${JSON.stringify(SELECTION_GROUP_TYPES)}.`);
  }

  const slideTags = getRecord(slideSchema, "tags");
  const slidePolicies = getRecord(slideTags, "efficio_slide_inclusion_policy").enum;
  const groupPolicies = getRecord(groupProperties, "inclusion_policy").enum;
  if (!Array.isArray(slidePolicies) || JSON.stringify(groupPolicies) !== JSON.stringify(slidePolicies)) {
    throw new Error(`${label} group inclusion policies must exactly match slide inclusion policies.`);
  }
  const groupInstructions = getRecord(slidesInstructions, "selection_group_instructions");
  assertDescriptionMap(
    groupInstructions.type_descriptions,
    groupTypeValues.map(String),
    `${label} type_descriptions`,
  );
}

function assertDescriptionMap(value: unknown, expectedKeys: string[], label: string): void {
  assertObject(value, label);
  if (JSON.stringify(Object.keys(value)) !== JSON.stringify(expectedKeys)) {
    throw new Error(`${label} keys must be ${JSON.stringify(expectedKeys)}.`);
  }
  for (const description of Object.values(value)) {
    if (typeof description !== "string" || description.trim().length === 0) {
      throw new Error(`${label} values must be non-empty strings.`);
    }
  }
}

export async function loadSlideSelectionSchema(): Promise<JsonObject> {
  const label = "contracts/presentation/slide/slide-selection.schema.json";
  const schema = await readJson(path.join(presentationSlideDir, "slide-selection.schema.json"));
  assertObject(schema, label);
  assertValidJsonSchema(schema, label);
  return schema;
}

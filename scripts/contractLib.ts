// Pure authored-contract validation and shared JSON shape helpers.
// The generator entrypoint (generate-ts-contracts.ts) owns file IO and
// orchestration; this module owns the logic so it can be unit-tested directly.

export type JsonObject = Record<string, unknown>;

import { assertJsonMatchesSchema, assertTextContentShape, assertValidJsonSchema } from "./contentContractLib.js";

export { assertJsonMatchesSchema, assertTextContentShape, assertValidJsonSchema };
export { validateComponentDefaults } from "./defaultsContractLib.js";

// ─── Generic JSON helpers ─────────────────────────────────────────────────────

export function assertObject(value: unknown, label: string): asserts value is JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be a JSON object.`);
  }
}

export function assertStringArray(value: unknown, label: string): asserts value is string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new Error(`${label} must be an array of strings.`);
  }
}

export function validateTagArray(schema: JsonObject, fieldName: string, label: string): void {
  const value = schema[fieldName];

  if (value !== undefined) {
    assertStringArray(value, `${label}.${fieldName}`);
  }
}

export function assertNoDefaults(schema: JsonObject, label: string): void {
  if ("defaults" in schema) {
    throw new Error(`${label}.defaults is not allowed. Component defaults live in contracts/components/{component}/tags.defaults.json.`);
  }
}

export function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export function isObject(value: unknown): value is JsonObject {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function getStringArray(schema: JsonObject, fieldName: string): string[] {
  const value = schema[fieldName];
  return isStringArray(value) ? value : [];
}

export function getRecord(schema: JsonObject, fieldName: string): JsonObject {
  const value = schema[fieldName];
  return isObject(value) ? value : {};
}

export function mergeExample(componentSchema: JsonObject): JsonObject {
  const example = getRecord(componentSchema, "example");

  if (Object.keys(example).length > 0) {
    return example;
  }

  return {};
}

// ─── Tag Entity contract validation ───────────────────────────────────────────

export const ALLOWED_TAG_TYPES = ["string", "integer", "boolean", "object", "array"] as const;
const STRING_CONSTRAINTS = ["min_length", "max_length", "pattern"] as const;
const INTEGER_CONSTRAINTS = ["minimum", "maximum"] as const;
const ALL_CONSTRAINTS = [...STRING_CONSTRAINTS, ...INTEGER_CONSTRAINTS] as const;
// Object/array tags are stored as JSON text in PowerPoint custom tags and carry a
// `schema` (validated as JSON Schema). Scalar tags must not declare `schema`.
const STRUCTURED_TAG_TYPES = ["object", "array"] as const;
const TAG_ENTITY_FIELDS = new Set<string>([
  "type",
  "required",
  "enum",
  "description",
  "ai",
  "ui",
  "schema",
  ...ALL_CONSTRAINTS,
]);
const COMPONENT_CONTRACT_FIELDS = new Set<string>(["component_type", "description", "tags", "example"]);
const SLIDE_CONTRACT_FIELDS = new Set<string>(["contract_type", "description", "tags"]);
const SHARED_CONTRACT_FIELDS = new Set<string>(["description", "tags"]);
export const COMPONENT_TYPE_TAG = "efficio_component_type";

export type TagType = (typeof ALLOWED_TAG_TYPES)[number];

// Every Efficio tag name is `efficio_` + lower snake_case (lowercase
// alphanumeric segments joined by single underscores). Enforced over authored
// tag-contract tag names by the pre-import contract validation (see
// contractValidation.ts), not by validateTagEntity, whose unit tests use
// synthetic single-letter tag names.
export const EFFICIO_TAG_NAME_PATTERN = /^efficio_[a-z0-9]+(_[a-z0-9]+)*$/;

export function isValidEfficioTagName(tag: string): boolean {
  return EFFICIO_TAG_NAME_PATTERN.test(tag);
}

const EFFICIO_TAG_PREFIX = "efficio_";

// Public AI alias of an internal tag name: the name with the `efficio_` prefix
// stripped. AI-facing component artifacts (tag_instructions keys, per-instance
// tag_context keys) expose only aliases; internal artifacts keep raw names.
// Aliases cannot collide because every tag name carries the prefix.
export function publicTagAlias(tag: string): string {
  if (!isValidEfficioTagName(tag)) {
    throw new Error(`Cannot build a public AI alias for invalid tag name ${JSON.stringify(tag)}.`);
  }
  return tag.slice(EFFICIO_TAG_PREFIX.length);
}

export function assertEfficioTagNames(schema: JsonObject, label: string): void {
  const tags = getRecord(schema, "tags");
  for (const tag of Object.keys(tags)) {
    if (!isValidEfficioTagName(tag)) {
      throw new Error(
        `${label}.tags.${tag} is not a valid Efficio tag name; tag names must match ${String(EFFICIO_TAG_NAME_PATTERN)}.`,
      );
    }
  }
}

function nativeTypeMatches(value: unknown, type: TagType): boolean {
  if (type === "string") return typeof value === "string";
  if (type === "integer") return typeof value === "number" && Number.isInteger(value);
  return typeof value === "boolean";
}

export function validateTagEntity(tag: string, value: unknown, label: string): void {
  const ctx = `${label}.tags.${tag}`;
  assertObject(value, ctx);

  for (const key of Object.keys(value)) {
    if (!TAG_ENTITY_FIELDS.has(key)) {
      throw new Error(`${ctx}.${key} is not an allowed tag entity field.`);
    }
  }

  const type = value.type;
  if (typeof type !== "string" || !ALLOWED_TAG_TYPES.includes(type as TagType)) {
    throw new Error(`${ctx}.type must be one of ${ALLOWED_TAG_TYPES.join(", ")}.`);
  }
  const tagType = type as TagType;

  if (typeof value.required !== "boolean") {
    throw new Error(`${ctx}.required must be a boolean.`);
  }

  const isStructured = (STRUCTURED_TAG_TYPES as readonly string[]).includes(tagType);
  if (isStructured) {
    if (value.schema === undefined) {
      throw new Error(`${ctx}.schema is required for type "${tagType}".`);
    }
    assertObject(value.schema, `${ctx}.schema`);
    assertValidJsonSchema(value.schema, `${ctx}.schema`);
    if (value.enum !== undefined) {
      throw new Error(`${ctx}.enum is not allowed for type "${tagType}".`);
    }
  } else if ("schema" in value) {
    throw new Error(`${ctx}.schema is only allowed for object/array tags.`);
  }

  if (value.enum !== undefined) {
    if (!Array.isArray(value.enum) || value.enum.length === 0) {
      throw new Error(`${ctx}.enum must be a non-empty array.`);
    }
    for (const entry of value.enum) {
      if (!nativeTypeMatches(entry, tagType)) {
        throw new Error(`${ctx}.enum value ${JSON.stringify(entry)} does not match declared type "${tagType}".`);
      }
    }
  }

  const allowedConstraints: readonly string[] =
    tagType === "string" ? STRING_CONSTRAINTS : tagType === "integer" ? INTEGER_CONSTRAINTS : [];
  for (const constraint of ALL_CONSTRAINTS) {
    if (constraint in value && !allowedConstraints.includes(constraint)) {
      throw new Error(`${ctx}.${constraint} is not allowed for type "${tagType}".`);
    }
  }
  for (const constraint of allowedConstraints) {
    if (constraint in value) {
      const expected = constraint === "pattern" ? "string" : "number";
      if (typeof value[constraint] !== expected) {
        throw new Error(`${ctx}.${constraint} must be a ${expected}.`);
      }
    }
  }

  if (value.ui !== undefined) {
    assertObject(value.ui, `${ctx}.ui`);
    for (const key of Object.keys(value.ui)) {
      if (key !== "order" && key !== "multiline") {
        throw new Error(`${ctx}.ui.${key} is not an allowed ui field.`);
      }
    }
    if (value.ui.order !== undefined && typeof value.ui.order !== "number") {
      throw new Error(`${ctx}.ui.order must be a number.`);
    }
    if (value.ui.multiline !== undefined && typeof value.ui.multiline !== "boolean") {
      throw new Error(`${ctx}.ui.multiline must be a boolean.`);
    }
  }

  // `ai` is the single source of truth for AI visibility: present means
  // AI-visible (and requires a purpose); absent means private/runtime/editor-only.
  // An AI-visible enum tag must describe every enum value, so the AI knows what
  // each choice means.
  if (value.ai !== undefined) {
    assertObject(value.ai, `${ctx}.ai`);
    for (const key of Object.keys(value.ai)) {
      if (key !== "purpose" && key !== "enum_descriptions") {
        throw new Error(`${ctx}.ai.${key} is not an allowed ai field.`);
      }
    }
    if (typeof value.ai.purpose !== "string" || value.ai.purpose.length === 0) {
      throw new Error(`${ctx}.ai.purpose is required and must be a non-empty string.`);
    }

    const hasEnum = Array.isArray(value.enum) && value.enum.length > 0;
    if (hasEnum && value.ai.enum_descriptions === undefined) {
      throw new Error(
        `${ctx}.ai.enum_descriptions is required for an AI-visible enum tag (describe every enum value).`,
      );
    }
    if (value.ai.enum_descriptions !== undefined) {
      assertObject(value.ai.enum_descriptions, `${ctx}.ai.enum_descriptions`);
      if (!hasEnum) {
        throw new Error(`${ctx}.ai.enum_descriptions requires ${ctx}.enum.`);
      }
      const enumValues = (value.enum as unknown[]).map((entry) => String(entry));
      const descriptions = value.ai.enum_descriptions;
      const descKeys = Object.keys(descriptions);
      const matches =
        descKeys.length === enumValues.length && enumValues.every((entry) => descKeys.includes(entry));
      if (!matches) {
        throw new Error(`${ctx}.ai.enum_descriptions keys must exactly match enum values.`);
      }
      for (const enumValue of enumValues) {
        const description = descriptions[enumValue];
        if (typeof description !== "string" || description.length === 0) {
          throw new Error(`${ctx}.ai.enum_descriptions.${enumValue} must be a non-empty string.`);
        }
      }
    }
  }
}

export function validateTagEntityContract(
  schema: JsonObject,
  label: string,
  options: { componentType?: string; slideContractType?: string },
): void {
  const isComponent = options.componentType !== undefined;
  const isSlide = options.slideContractType !== undefined;
  const allowedFields = isComponent
    ? COMPONENT_CONTRACT_FIELDS
    : isSlide
      ? SLIDE_CONTRACT_FIELDS
      : SHARED_CONTRACT_FIELDS;

  for (const key of Object.keys(schema)) {
    if (!allowedFields.has(key)) {
      throw new Error(`${label}.${key} is not an allowed contract field.`);
    }
  }

  const tags = schema.tags;
  assertObject(tags, `${label}.tags`);
  if (Object.keys(tags).length === 0) {
    throw new Error(`${label}.tags must declare at least one tag.`);
  }

  for (const [tag, entity] of Object.entries(tags)) {
    validateTagEntity(tag, entity, label);
  }

  if (isSlide) {
    if (schema.contract_type !== options.slideContractType) {
      throw new Error(`${label}.contract_type must be "${options.slideContractType}".`);
    }
    return;
  }

  if (!isComponent) {
    // Shared fragment: component_type / contract_type already rejected by the
    // allowed-field check above.
    return;
  }

  if (schema.component_type !== options.componentType) {
    throw new Error(`${label}.component_type must be "${options.componentType}".`);
  }

  const componentTypeTag = tags[COMPONENT_TYPE_TAG];
  if (componentTypeTag === undefined) {
    throw new Error(`${label}.tags.${COMPONENT_TYPE_TAG} is required in a component contract.`);
  }
  assertObject(componentTypeTag, `${label}.tags.${COMPONENT_TYPE_TAG}`);
  const enumValues = componentTypeTag.enum;
  if (
    !Array.isArray(enumValues) ||
    enumValues.length !== 1 ||
    enumValues[0] !== options.componentType
  ) {
    throw new Error(
      `${label}.tags.${COMPONENT_TYPE_TAG}.enum must be exactly ["${options.componentType}"].`,
    );
  }
}

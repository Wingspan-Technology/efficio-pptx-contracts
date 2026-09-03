import { assertJsonMatchesSchema } from "./contentContractLib.js";
import { assertObject, type JsonObject } from "./contractLib.js";

export function validateStoredTagValue(
  tag: string,
  value: unknown,
  definition: JsonObject,
  label: string,
): asserts value is string {
  if (typeof value !== "string") {
    throw new Error(`${label}.${tag} must be stored as a string.`);
  }

  const type = definition.type;
  if (type === "object" || type === "array") {
    validateStructuredValue(tag, value, definition, label, type);
    return;
  }
  if (type === "boolean") {
    if (value !== "true" && value !== "false") {
      throw new Error(`${label}.${tag} must be stored as "true" or "false".`);
    }
  } else if (type === "integer") {
    validateIntegerValue(tag, value, definition, label);
  } else if (type === "string") {
    validateStringValue(tag, value, definition, label);
  } else {
    throw new Error(`${label}.${tag} has unsupported tag type ${JSON.stringify(type)}.`);
  }

  const allowed = definition.enum;
  if (Array.isArray(allowed) && !allowed.map(String).includes(value)) {
    throw new Error(`${label}.${tag} must be one of ${JSON.stringify(allowed.map(String))}.`);
  }
}

function validateIntegerValue(
  tag: string,
  value: string,
  definition: JsonObject,
  label: string,
): void {
  if (!/^-?\d+$/.test(value)) {
    throw new Error(`${label}.${tag} must be stored as an integer string.`);
  }
  const parsed = Number(value);
  if (typeof definition.minimum === "number" && parsed < definition.minimum) {
    throw new Error(`${label}.${tag} must be at least ${definition.minimum}.`);
  }
  if (typeof definition.maximum === "number" && parsed > definition.maximum) {
    throw new Error(`${label}.${tag} must be at most ${definition.maximum}.`);
  }
}

function validateStringValue(
  tag: string,
  value: string,
  definition: JsonObject,
  label: string,
): void {
  if (typeof definition.min_length === "number" && value.length < definition.min_length) {
    throw new Error(`${label}.${tag} must contain at least ${definition.min_length} characters.`);
  }
  if (typeof definition.max_length === "number" && value.length > definition.max_length) {
    throw new Error(`${label}.${tag} must contain at most ${definition.max_length} characters.`);
  }
  if (typeof definition.pattern === "string") {
    const pattern = new RegExp(`^(?:${definition.pattern})$`, "u");
    if (!pattern.test(value)) {
      throw new Error(`${label}.${tag} does not match its required pattern.`);
    }
  }
}

function validateStructuredValue(
  tag: string,
  value: string,
  definition: JsonObject,
  label: string,
  type: "object" | "array",
): void {
  const schema = definition.schema;
  assertObject(schema, `${label}.${tag}.schema`);
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch (error) {
    throw new Error(`${label}.${tag} must be valid JSON text: ${(error as Error).message}`);
  }
  const hasExpectedType = type === "array"
    ? Array.isArray(parsed)
    : parsed !== null && typeof parsed === "object" && !Array.isArray(parsed);
  if (!hasExpectedType) {
    throw new Error(`${label}.${tag} must contain a JSON ${type}.`);
  }
  assertJsonMatchesSchema(value, schema, `${label}.${tag}`);
}

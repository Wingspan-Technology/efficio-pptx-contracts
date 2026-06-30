import { Ajv2020 } from "ajv/dist/2020.js";

type JsonObject = Record<string, unknown>;

export function assertValidJsonSchema(schema: JsonObject, label: string): void {
  const ajv = new Ajv2020({ strict: false });
  try {
    ajv.compile(schema);
  } catch (error) {
    throw new Error(`${label} is not a valid JSON Schema document: ${(error as Error).message}`);
  }
}

// Validates a JSON-text value (e.g. an object/array tag default stored as a
// string in a PowerPoint custom tag) against an embedded JSON Schema: it must
// parse as JSON and then satisfy the schema. Uses the same Draft 2020-12 AJV
// setup as schema validation so embedded `$schema: .../2020-12/schema` documents
// are honored.
export function assertJsonMatchesSchema(jsonText: string, schema: JsonObject, label: string): void {
  let parsed: unknown;
  try {
    parsed = JSON.parse(jsonText);
  } catch (error) {
    throw new Error(`${label} must be valid JSON text: ${(error as Error).message}`);
  }

  const ajv = new Ajv2020({ strict: false });
  const validate = ajv.compile(schema);
  if (!validate(parsed)) {
    const detail = (validate.errors ?? [])
      .map((error) => `${error.instancePath || "(root)"} ${error.message ?? "is invalid"}`)
      .join("; ");
    throw new Error(`${label} does not match its tag schema: ${detail}.`);
  }
}

// Enforces the current text content shape: { "items": ["..."] }.
export function assertTextContentShape(schema: JsonObject, label: string): void {
  if (schema.type !== "object") {
    throw new Error(`${label}.type must be "object".`);
  }
  if (schema.additionalProperties !== false) {
    throw new Error(`${label}.additionalProperties must be false.`);
  }
  if (!Array.isArray(schema.required) || !schema.required.includes("items")) {
    throw new Error(`${label}.required must include "items".`);
  }

  const items = getRecord(schema, "properties").items;
  assertObject(items, `${label}.properties.items`);
  if (items.type !== "array") {
    throw new Error(`${label}.properties.items.type must be "array".`);
  }
  if (typeof items.minItems !== "number" || items.minItems < 1) {
    throw new Error(`${label}.properties.items.minItems must be >= 1.`);
  }

  const itemSchema = items.items;
  assertObject(itemSchema, `${label}.properties.items.items`);
  if (itemSchema.type !== "string") {
    throw new Error(`${label}.properties.items.items.type must be "string".`);
  }
  if (typeof itemSchema.minLength !== "number" || itemSchema.minLength < 1) {
    throw new Error(`${label}.properties.items.items.minLength must be >= 1.`);
  }
}

function assertObject(value: unknown, label: string): asserts value is JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be a JSON object.`);
  }
}

function getRecord(schema: JsonObject, fieldName: string): JsonObject {
  const value = schema[fieldName];
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
}

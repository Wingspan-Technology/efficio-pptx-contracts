import { assertJsonMatchesSchema } from "./contentContractLib.js";

type JsonObject = Record<string, unknown>;

export function validateComponentDefaults(
  defaults: unknown,
  tagSchema: JsonObject,
  label: string,
): Record<string, string> {
  assertObject(defaults, label);

  const knownTags = new Set<string>([
    ...getStringArray(tagSchema, "required_tags"),
    ...getStringArray(tagSchema, "optional_tags"),
  ]);
  const enums = getRecord(tagSchema, "enums");
  const types = getRecord(tagSchema, "types");
  const jsonSchemas = getRecord(tagSchema, "json_schemas");

  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(defaults)) {
    if (key === "efficio_component_id") {
      throw new Error(`${label}.${key} must not be set in defaults; the editor generates it from shape context.`);
    }
    if (!knownTags.has(key)) {
      throw new Error(`${label}.${key} is not a known tag for this component.`);
    }
    if (typeof value !== "string") {
      throw new Error(`${label}.${key} must be a string value.`);
    }

    validateDefaultValue(key, value, enums, types, jsonSchemas, label);
    result[key] = value;
  }

  return result;
}

function validateDefaultValue(
  key: string,
  value: string,
  enums: JsonObject,
  types: JsonObject,
  jsonSchemas: JsonObject,
  label: string,
): void {
  const enumValues = enums[key];
  if (Array.isArray(enumValues) && !enumValues.includes(value)) {
    throw new Error(`${label}.${key} must be one of ${JSON.stringify(enumValues)}.`);
  }

  const type = types[key];
  if (type === "positive_integer_string" && !/^[1-9]\d*$/.test(value)) {
    throw new Error(`${label}.${key} must be a positive integer string.`);
  }
  if (type === "non_empty_string" && value.length === 0) {
    throw new Error(`${label}.${key} must be a non-empty string.`);
  }
  if (type === "enum_boolean_string" && value !== "true" && value !== "false") {
    throw new Error(`${label}.${key} must be "true" or "false".`);
  }
  // Object/array (json_object/json_array) defaults are stored as JSON text and
  // must parse and satisfy the tag's embedded JSON Schema, not just be a string.
  if (type === "json_object" || type === "json_array") {
    const schema = jsonSchemas[key];
    if (schema !== null && typeof schema === "object" && !Array.isArray(schema)) {
      assertJsonMatchesSchema(value, schema as JsonObject, `${label}.${key}`);
    }
  }
}

function assertObject(value: unknown, label: string): asserts value is JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be a JSON object.`);
  }
}

function getStringArray(schema: JsonObject, fieldName: string): string[] {
  const value = schema[fieldName];
  return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : [];
}

function getRecord(schema: JsonObject, fieldName: string): JsonObject {
  const value = schema[fieldName];
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as JsonObject : {};
}

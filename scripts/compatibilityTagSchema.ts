import {
  COMPONENT_TYPE_TAG,
  getRecord,
  isObject,
  mergeExample,
  type JsonObject,
} from "./contractLib.js";

export function legacyEnum(entity: JsonObject): string[] | undefined {
  if (entity.type === "boolean") {
    return ["true", "false"];
  }
  const values = entity.enum;
  if (Array.isArray(values) && values.length > 0) {
    return values.map((value) => String(value));
  }
  return undefined;
}

export function legacyType(entity: JsonObject, ctx: string): string {
  if (entity.type === "string") {
    if (Array.isArray(entity.enum) && entity.enum.length > 0) {
      return "enum";
    }
    if (typeof entity.min_length === "number" && entity.min_length >= 1) {
      return "non_empty_string";
    }
    return "string";
  }
  if (entity.type === "integer") {
    if (typeof entity.minimum === "number" && entity.minimum >= 1) {
      return "positive_integer_string";
    }
    throw new Error(`${ctx}: integer tags must declare minimum >= 1 to map to the current editor type.`);
  }
  if (entity.type === "boolean") return "enum_boolean_string";
  if (entity.type === "object") return "json_object";
  if (entity.type === "array") return "json_array";
  throw new Error(`${ctx}: unsupported tag type "${String(entity.type)}".`);
}

export function mergeNativeTags(
  commonSchema: JsonObject,
  componentSchema: JsonObject,
  label: string,
): Record<string, JsonObject> {
  const commonTags = getRecord(commonSchema, "tags");
  const componentTags = getRecord(componentSchema, "tags");
  const merged: Record<string, JsonObject> = {};

  for (const [key, entity] of Object.entries(commonTags)) {
    if (key in componentTags) {
      if (key !== COMPONENT_TYPE_TAG) {
        throw new Error(`${label}.tags.${key} conflicts with common.tags.${key}.`);
      }
      merged[key] = { ...(entity as JsonObject), enum: (componentTags[key] as JsonObject).enum };
    } else {
      merged[key] = entity as JsonObject;
    }
  }

  for (const [key, entity] of Object.entries(componentTags)) {
    if (!(key in commonTags)) {
      merged[key] = entity as JsonObject;
    }
  }
  return merged;
}

export function mergeTagSchema(
  commonSchema: JsonObject,
  componentSchema: JsonObject,
  label: string,
  commonLabels: string[],
): JsonObject {
  const commonTags = getRecord(commonSchema, "tags");
  const componentTags = getRecord(componentSchema, "tags");
  const commonKeys = Object.keys(commonTags);
  const componentKeys = Object.keys(componentTags);
  const componentOnlyKeys = componentKeys.filter((key) => !(key in commonTags));
  const mergedCommon: Record<string, JsonObject> = {};

  for (const key of commonKeys) {
    const commonEntity = commonTags[key] as JsonObject;
    if (key in componentTags) {
      if (key !== COMPONENT_TYPE_TAG) {
        throw new Error(`${label}.tags.${key} conflicts with common.tags.${key}.`);
      }
      mergedCommon[key] = { ...commonEntity, enum: (componentTags[key] as JsonObject).enum };
    } else {
      mergedCommon[key] = commonEntity;
    }
  }

  const requiredTags: string[] = [];
  const optionalTags: string[] = [];
  for (const key of commonKeys) {
    ((commonTags[key] as JsonObject).required ? requiredTags : optionalTags).push(key);
  }
  for (const key of componentOnlyKeys) {
    ((componentTags[key] as JsonObject).required ? requiredTags : optionalTags).push(key);
  }

  const enums: JsonObject = {};
  for (const key of commonKeys) {
    const values = legacyEnum(commonTags[key] as JsonObject);
    if (values) enums[key] = values;
  }
  for (const key of componentKeys) {
    const values = legacyEnum(componentTags[key] as JsonObject);
    if (!values) continue;
    if (key in enums && JSON.stringify(enums[key]) !== JSON.stringify(values)) {
      throw new Error(`${label}.tags.${key}.enum conflicts with common.tags.${key}.enum.`);
    }
    enums[key] = values;
  }

  const types: JsonObject = {};
  for (const key of commonKeys) {
    types[key] = legacyType(mergedCommon[key], `${label}.tags.${key}`);
  }
  for (const key of componentOnlyKeys) {
    types[key] = legacyType(componentTags[key] as JsonObject, `${label}.tags.${key}`);
  }

  const jsonSchemas: JsonObject = {};
  for (const key of commonKeys) {
    const schema = mergedCommon[key].schema;
    if (isObject(schema)) jsonSchemas[key] = schema;
  }
  for (const key of componentOnlyKeys) {
    const schema = (componentTags[key] as JsonObject).schema;
    if (isObject(schema)) jsonSchemas[key] = schema;
  }

  return {
    generated_from: [...commonLabels, label],
    component_type: componentSchema.component_type,
    description: componentSchema.description,
    required_tags: requiredTags,
    optional_tags: optionalTags,
    enums,
    types,
    json_schemas: jsonSchemas,
    example: mergeExample(componentSchema),
  };
}

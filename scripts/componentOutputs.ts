import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { validateComponentDefaults, type JsonObject } from "./contractLib.js";
import { mergeNativeTags, mergeTagSchema } from "./compatibilityTagSchema.js";
import { buildConstSource, readJson, toCamelCase, writeJson } from "./generatorIo.js";
import type { ComponentSource, SharedTagContract } from "./componentSources.js";
import {
  componentsDir,
  generatedComponentSchemasDir,
  generatedDir,
  sharedDefaultsLabel,
  sharedDir,
  tsComponentsDir,
  tsOutputDir,
} from "./generatorPaths.js";

export function componentPaths(componentType: string): JsonObject {
  return {
    tags_contract: `contracts/components/${componentType}/tags.contract.json`,
    content_contract: `contracts/components/${componentType}/content.contract.json`,
    tags_defaults: `contracts/components/${componentType}/tags.defaults.json`,
  };
}

export function buildComponentTypesSchema(componentSources: ComponentSource[]): JsonObject {
  return {
    generated_from: componentSources.map((source) => source.label),
    component_types: componentSources.map((source) => source.componentType),
  };
}

export function buildComponentTypesSource(componentTypes: string[]): string {
  return `export const componentTypes = ${JSON.stringify(componentTypes, null, 2)} as const;
export type ComponentType = (typeof componentTypes)[number];
`;
}

export function buildTagSchemasSource(tagSchemas: Record<string, JsonObject>): string {
  return `import type { ComponentType } from "./componentTypes.js";

export const tagSchemas = ${JSON.stringify(tagSchemas, null, 2)} as const;

export type TagSchema = (typeof tagSchemas)[ComponentType];
`;
}

export async function buildTagSchemas(
  sharedTags: SharedTagContract,
  componentSources: ComponentSource[],
): Promise<Record<string, JsonObject>> {
  const builtSchemasByType: Record<string, JsonObject> = {};

  await mkdir(generatedComponentSchemasDir, { recursive: true });
  for (const { componentType, label, schema } of componentSources) {
    const builtSchema = mergeTagSchema(sharedTags.schema, schema, label, sharedTags.labels);
    builtSchemasByType[componentType] = builtSchema;
    await writeJson(
      path.join(generatedComponentSchemasDir, `${componentType.replace(/_/g, "-")}.json`),
      builtSchema,
    );
  }

  return builtSchemasByType;
}

export async function buildComponentMetadata(
  sharedSchema: JsonObject,
  componentSources: ComponentSource[],
  effectiveDefaultsByType: Record<string, Record<string, string>>,
): Promise<void> {
  const metadata: JsonObject = {};

  for (const source of componentSources) {
    const nativeTags = mergeNativeTags(sharedSchema, source.schema, source.label);
    const tags: JsonObject = {};
    for (const [tag, entity] of Object.entries(nativeTags)) {
      tags[tag] = stripAiMetadata(entity);
    }

    metadata[source.componentType] = {
      component_type: source.componentType,
      paths: componentPaths(source.componentType),
      tags,
      defaults: effectiveDefaultsByType[source.componentType],
    };
  }

  await writeFile(path.join(tsComponentsDir, "componentMetadata.ts"), buildConstSource("componentMetadata", metadata, [
    "export type ComponentMetadataMap = typeof componentMetadata;",
    "export type ComponentMetadata = ComponentMetadataMap[keyof ComponentMetadataMap];",
  ]));
}

function stripAiMetadata(entity: JsonObject): JsonObject {
  const { ai: _ai, ...rest } = entity;
  return rest;
}

export async function buildComponentDefaults(componentType: string, tagSchema: JsonObject): Promise<Record<string, string>> {
  const label = `contracts/components/${componentType}/tags.defaults.json`;
  const sharedDefaultsRaw = await readJson(path.join(sharedDir, "component-default-tags.defaults.json"));
  const componentDefaultsRaw = await readJson(path.join(componentsDir, componentType, "tags.defaults.json")).catch((error: unknown) => {
    throw new Error(`Could not read ${label}. Every component folder must include tags.defaults.json.`, { cause: error });
  });

  const sharedDefaults = validateComponentDefaults(sharedDefaultsRaw, tagSchema, sharedDefaultsLabel);
  const componentDefaults = validateComponentDefaults(componentDefaultsRaw, tagSchema, label);
  const effectiveDefaults = { ...sharedDefaults, ...componentDefaults };
  const exportName = `${toCamelCase(componentType)}Defaults`;

  await writeFile(path.join(tsComponentsDir, `${exportName}.ts`), buildConstSource(exportName, effectiveDefaults, [], [
    `// Source: ${sharedDefaultsLabel} + ${label}`,
  ]));
  return effectiveDefaults;
}

export async function buildComponentRegistry(componentSources: ComponentSource[]): Promise<void> {
  const components: JsonObject = {};
  for (const { componentType } of componentSources) {
    components[componentType] = componentPaths(componentType);
  }

  const registry = { components };
  await writeJson(path.join(generatedDir, "component-registry.json"), registry);
  await writeFile(path.join(tsOutputDir, "componentRegistry.ts"), buildConstSource("componentRegistry", registry, [
    "export type ComponentRegistry = typeof componentRegistry;",
  ]));
}

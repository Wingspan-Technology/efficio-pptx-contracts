import { mkdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";

import { writeJson } from "./generatorIo.js";
import { validateAllContracts } from "./contractValidation.js";
import { loadComponentSources, loadSharedTagContract } from "./componentSources.js";
import {
  buildComponentDefaults,
  buildComponentMetadata,
  buildComponentRegistry,
  buildComponentTypesSchema,
  buildComponentTypesSource,
  buildTagSchemas,
  buildTagSchemasSource,
} from "./componentOutputs.js";
import {
  loadDeckDefaults,
  loadDeckTagSchema,
  loadSlideDefaults,
  loadSlideTagSchema,
} from "./presentationSources.js";
import { buildDeckOutputs, buildSlideOutputs, copyPresentationContract } from "./presentationOutputs.js";
import { buildAiInstructionOutputs, buildSlideSelectionInstructionOutputs } from "./aiOutputs.js";
import { mirrorSdkResources } from "./sdkMirror.js";
import { loadTemplateContractMigrationCatalog } from "./templateMigrationContract.js";
import { buildTemplateMigrationOutputs } from "./templateMigrationOutput.js";
import {
  generatedAiDir,
  generatedComponentSchemasDir,
  generatedPresentationSchemasDir,
  generatedSchemasDir,
  tsAiDir,
  tsComponentsDir,
  tsOutputDir,
  tsPresentationDir,
} from "./generatorPaths.js";

async function main(): Promise<void> {
  // Validate every contract before deleting anything: a bad contract must fail
  // here, with the generated outputs left intact, rather than half-cleared.
  const report = await validateAllContracts();
  if (!report.ok) {
    const detail = report.issues.map((issue) => `  - ${issue.contract}: ${issue.message}`).join("\n");
    throw new Error(`Contract validation failed; not clearing or regenerating outputs:\n${detail}`);
  }

  const migrationCatalog = await loadTemplateContractMigrationCatalog();

  await clearObsoleteGeneratedOutputs();

  const sharedTags = await loadSharedTagContract();
  const componentSources = await loadComponentSources();
  const componentTypes = componentSources.map((source) => source.componentType);
  const tagSchemas = await buildTagSchemas(sharedTags, componentSources);
  const slideSchema = await loadSlideTagSchema();
  const slideDefaults = await loadSlideDefaults(slideSchema);
  const deckSchema = await loadDeckTagSchema();
  const deckDefaults = await loadDeckDefaults(deckSchema);

  await mkdir(generatedSchemasDir, { recursive: true });
  await writeJson(path.join(generatedSchemasDir, "component-types.json"), buildComponentTypesSchema(componentSources));
  await copyPresentationContract("slide/slide.contract.json", "slide-contract.json", "slideContract");
  await copyPresentationContract("template/template.contract.json", "template-contract.json", "templateContract");

  await mkdir(tsComponentsDir, { recursive: true });
  await writeFile(path.join(tsComponentsDir, "componentTypes.ts"), buildComponentTypesSource(componentTypes));
  await writeFile(path.join(tsComponentsDir, "tagSchemas.ts"), buildTagSchemasSource(tagSchemas));
  await buildSlideOutputs(slideSchema, slideDefaults);
  await buildDeckOutputs(deckSchema, deckDefaults);
  await buildTemplateMigrationOutputs(migrationCatalog);

  const effectiveDefaultsByType: Record<string, Record<string, string>> = {};
  for (const { componentType } of componentSources) {
    effectiveDefaultsByType[componentType] = await buildComponentDefaults(componentType, tagSchemas[componentType]);
  }
  await buildComponentRegistry(componentSources);
  await buildComponentMetadata(sharedTags.schema, componentSources, effectiveDefaultsByType);
  await buildAiInstructionOutputs(sharedTags.schema, componentSources);
  await buildSlideSelectionInstructionOutputs(slideSchema);
  await mirrorSdkResources(componentTypes);
}

async function clearObsoleteGeneratedOutputs(): Promise<void> {
  await Promise.all([
    rm(path.join(generatedSchemasDir, "tags"), { recursive: true, force: true }),
    rm(path.join(generatedSchemasDir, "slide"), { recursive: true, force: true }),
    rm(path.join(generatedSchemasDir, "component-registry.json"), { force: true }),
    rm(path.join(generatedSchemasDir, "slide-contract.json"), { force: true }),
    rm(path.join(generatedSchemasDir, "template-contract.json"), { force: true }),
    rm(path.join(tsOutputDir, "componentMetadata.ts"), { force: true }),
    rm(path.join(tsOutputDir, "componentTypes.ts"), { force: true }),
    rm(path.join(tsOutputDir, "tagSchemas.ts"), { force: true }),
    rm(path.join(tsOutputDir, "imageDefaults.ts"), { force: true }),
    rm(path.join(tsOutputDir, "textDefaults.ts"), { force: true }),
    rm(path.join(tsOutputDir, "slideTagSchema.ts"), { force: true }),
  ]);
  await Promise.all([
    rm(generatedComponentSchemasDir, { recursive: true, force: true }),
    rm(generatedPresentationSchemasDir, { recursive: true, force: true }),
    rm(generatedAiDir, { recursive: true, force: true }),
    rm(tsComponentsDir, { recursive: true, force: true }),
    rm(tsPresentationDir, { recursive: true, force: true }),
    rm(tsAiDir, { recursive: true, force: true }),
  ]);
}

await main();

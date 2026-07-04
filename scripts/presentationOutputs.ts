import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { assertObject, type JsonObject } from "./contractLib.js";
import { buildConstSource, readJson, writeJson } from "./generatorIo.js";
import { buildSlideTagSchemaSource } from "./slideTsOutput.js";
import { buildDeckTagSchemaSource } from "./deckTsOutput.js";
import {
  generatedPresentationSchemasDir,
  presentationSlideDir,
  presentationTemplateDir,
  tsPresentationDir,
} from "./generatorPaths.js";

export async function copyPresentationContract(
  sourceRelativePath: "slide/slide.contract.json" | "template/template.contract.json",
  outputFileName: string,
  exportName: string,
): Promise<void> {
  const sourceLabel = `contracts/presentation/${sourceRelativePath}`;
  const sourcePath = sourceRelativePath.startsWith("slide/")
    ? path.join(presentationSlideDir, path.basename(sourceRelativePath))
    : path.join(presentationTemplateDir, path.basename(sourceRelativePath));
  const schema = await readJson(sourcePath);
  assertObject(schema, sourceLabel);

  const generatedSchema = { generated_from: sourceLabel, ...schema };
  await mkdir(generatedPresentationSchemasDir, { recursive: true });
  await writeJson(path.join(generatedPresentationSchemasDir, outputFileName), generatedSchema);
  await mkdir(tsPresentationDir, { recursive: true });
  await writeFile(path.join(tsPresentationDir, `${exportName}.ts`), buildConstSource(exportName, generatedSchema));
}

export async function buildSlideOutputs(schema: JsonObject, defaults: Record<string, string>): Promise<void> {
  const generated = { generated_from: "contracts/presentation/slide/tags.contract.json", ...schema };

  await mkdir(generatedPresentationSchemasDir, { recursive: true });
  await writeJson(path.join(generatedPresentationSchemasDir, "slide-tags.json"), generated);
  await mkdir(tsPresentationDir, { recursive: true });
  await writeFile(path.join(tsPresentationDir, "slideTagSchema.ts"), buildSlideTagSchemaSource(schema));
  await writeFile(path.join(tsPresentationDir, "slideDefaults.ts"), buildConstSource("slideDefaults", defaults));
}

export async function buildDeckOutputs(schema: JsonObject, defaults: Record<string, string>): Promise<void> {
  const generated = { generated_from: "contracts/presentation/deck/tags.contract.json", ...schema };

  await mkdir(generatedPresentationSchemasDir, { recursive: true });
  await writeJson(path.join(generatedPresentationSchemasDir, "deck-tags.json"), generated);
  await mkdir(tsPresentationDir, { recursive: true });
  await writeFile(path.join(tsPresentationDir, "deckTagSchema.ts"), buildDeckTagSchemaSource(schema));
  await writeFile(path.join(tsPresentationDir, "deckDefaults.ts"), buildConstSource("deckDefaults", defaults));
}

import { copyFile, mkdir, rm } from "node:fs/promises";
import path from "node:path";

import {
  generatedAiComponentsDir,
  generatedAiDir,
  generatedComponentSchemasDir,
  generatedDir,
  generatedPresentationSchemasDir,
  sdkGeneratedDir,
} from "./generatorPaths.js";

// Mirrors the runtime JSON consumed by the Python SDK into the importable
// package under efficio_ppt_components/_generated/. These are exact copies of the
// canonical top-level generated JSON, written in the same pass so the two stay
// in sync (asserted by tests/generated.test.ts). Only the artifacts the SDK
// loads are mirrored; generated/ts/* stays TypeScript-only.
export async function mirrorSdkResources(componentTypes: string[]): Promise<void> {
  await rm(sdkGeneratedDir, { recursive: true, force: true });
  await mkdir(path.join(sdkGeneratedDir, "ai", "components"), { recursive: true });
  await mkdir(path.join(sdkGeneratedDir, "schemas", "components"), { recursive: true });
  await mkdir(path.join(sdkGeneratedDir, "schemas", "presentation"), { recursive: true });

  await copyFile(
    path.join(generatedDir, "component-registry.json"),
    path.join(sdkGeneratedDir, "component-registry.json"),
  );
  await copyFile(
    path.join(generatedAiDir, "component-instructions.json"),
    path.join(sdkGeneratedDir, "ai", "component-instructions.json"),
  );
  await copyFile(
    path.join(generatedAiDir, "slide-selection.instruction.json"),
    path.join(sdkGeneratedDir, "ai", "slide-selection.instruction.json"),
  );
  for (const componentType of componentTypes) {
    const fileName = `${componentType}.instruction.json`;
    await copyFile(
      path.join(generatedAiComponentsDir, fileName),
      path.join(sdkGeneratedDir, "ai", "components", fileName),
    );
    const schemaFileName = `${componentType.replace(/_/g, "-")}.json`;
    await copyFile(
      path.join(generatedComponentSchemasDir, schemaFileName),
      path.join(sdkGeneratedDir, "schemas", "components", schemaFileName),
    );
  }
  await copyFile(
    path.join(generatedPresentationSchemasDir, "slide-tags.json"),
    path.join(sdkGeneratedDir, "schemas", "presentation", "slide-tags.json"),
  );
}

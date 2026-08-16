import path from "node:path";
import { fileURLToPath } from "node:url";

// All filesystem locations the generator reads from and writes to, resolved
// once. Kept in one place so source/output layout changes touch a single file.
export const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
// Authored contract source of truth (cross-language inputs to the generator).
// Lives at the package root, outside the Python SDK under src/.
export const contractsDir = path.join(packageRoot, "contracts");
export const componentsDir = path.join(contractsDir, "components");
export const sharedDir = path.join(contractsDir, "shared");
export const presentationSlideDir = path.join(contractsDir, "presentation", "slide");
export const presentationDeckDir = path.join(contractsDir, "presentation", "deck");
export const presentationTemplateDir = path.join(contractsDir, "presentation", "template");
export const generatedDir = path.join(packageRoot, "generated");
export const generatedSchemasDir = path.join(generatedDir, "schemas");
export const generatedComponentSchemasDir = path.join(generatedSchemasDir, "components");
export const generatedPresentationSchemasDir = path.join(generatedSchemasDir, "presentation");
export const tsOutputDir = path.join(generatedDir, "ts");
export const tsComponentsDir = path.join(tsOutputDir, "components");
export const tsPresentationDir = path.join(tsOutputDir, "presentation");
export const generatedAiDir = path.join(generatedDir, "ai");
export const generatedAiComponentsDir = path.join(generatedAiDir, "components");
export const tsAiDir = path.join(tsOutputDir, "ai");

// Runtime JSON for the Python SDK ships inside the importable package so it is
// wheel-safe via importlib.resources. It is a mirror of the canonical top-level
// generated JSON, copied in the same generation pass (see sdkMirror.ts).
export const sdkPackageDir = path.join(packageRoot, "src", "efficio_pptx_contracts");
export const sdkGeneratedDir = path.join(sdkPackageDir, "_generated");

export const sharedTagFragmentNames = [
  "render-behavior-tags.contract.json",
  "component-base-tags.contract.json",
];
export const sharedDefaultsLabel = "contracts/shared/component-default-tags.defaults.json";

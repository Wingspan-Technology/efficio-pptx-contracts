// Standalone, pre-import contract validation. Reads every authored contract and
// runs the same pure rule validators the generator uses, but writes nothing and
// collects all problems into a structured report instead of throwing on the
// first one. The generator runs this before clearing any generated outputs, and
// the `validate:contracts` CLI runs it on its own; both share this single source
// of validation truth so no rule is duplicated.

import { readdir } from "node:fs/promises";
import path from "node:path";

import {
  assertEfficioTagNames,
  assertNoDefaults,
  assertObject,
  assertValidJsonSchema,
  assertTextContentShape,
  getRecord,
  validateComponentDefaults,
  validateTagEntityContract,
  type JsonObject,
} from "./contractLib.js";
import { mergeTagSchema } from "./compatibilityTagSchema.js";
import { validateComponentsInstruction } from "./componentSources.js";
import {
  validateSelectionGroupContract,
  validateSlideDefaults,
  validateSlidesInstructions,
} from "./presentationSources.js";
import { readJson } from "./generatorIo.js";
import { contractsDir as defaultContractsDir, sharedDefaultsLabel, sharedTagFragmentNames } from "./generatorPaths.js";

export type ContractIssue = { contract: string; message: string };
export type ValidationReport = { ok: boolean; checked: number; issues: ContractIssue[] };

type Layout = {
  sharedDir: string;
  componentsDir: string;
  slideDir: string;
  deckDir: string;
  templateDir: string;
};

export async function validateAllContracts(
  options: { contractsDir?: string } = {},
): Promise<ValidationReport> {
  const root = options.contractsDir ?? defaultContractsDir;
  const layout: Layout = {
    sharedDir: path.join(root, "shared"),
    componentsDir: path.join(root, "components"),
    slideDir: path.join(root, "presentation", "slide"),
    deckDir: path.join(root, "presentation", "deck"),
    templateDir: path.join(root, "presentation", "template"),
  };

  const issues: ContractIssue[] = [];
  let checked = 0;
  const addIssue = (contract: string, error: unknown): void => {
    issues.push({ contract, message: error instanceof Error ? error.message : String(error) });
  };
  const check = async (contract: string, fn: () => Promise<void> | void): Promise<void> => {
    checked += 1;
    try {
      await fn();
    } catch (error) {
      addIssue(contract, error);
    }
  };

  // 1. Shared tag fragments → composed shared schema (mirrors loadSharedTagContract).
  const sharedSchema: JsonObject = { tags: {} };
  const sharedLabels: string[] = [];
  for (const fileName of sharedTagFragmentNames) {
    const label = `contracts/shared/${fileName}`;
    await check(label, async () => {
      const fragment = await readJson(path.join(layout.sharedDir, fileName));
      assertObject(fragment, label);
      assertNoDefaults(fragment, label);
      validateTagEntityContract(fragment, label, {});
      assertEfficioTagNames(fragment, label);

      const sharedTags = getRecord(sharedSchema, "tags");
      for (const [tag, entity] of Object.entries(getRecord(fragment, "tags"))) {
        if (tag in sharedTags) {
          throw new Error(`${label}.tags.${tag} duplicates a shared tag fragment.`);
        }
        sharedTags[tag] = entity;
      }
      sharedLabels.push(label);
    });
  }
  const sharedOk = sharedLabels.length === sharedTagFragmentNames.length;

  // 2. Components: tag contract, content contract, merge, and defaults.
  let componentNames: string[] = [];
  try {
    const entries = await readdir(layout.componentsDir, { withFileTypes: true });
    componentNames = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name).sort();
  } catch (error) {
    addIssue("contracts/components", error);
  }

  let sharedDefaultsRaw: unknown;
  let sharedDefaultsReadError: unknown;
  try {
    sharedDefaultsRaw = await readJson(path.join(layout.sharedDir, "component-default-tags.defaults.json"));
  } catch (error) {
    sharedDefaultsReadError = error;
  }

  for (const name of componentNames) {
    const tagsLabel = `contracts/components/${name}/tags.contract.json`;
    const contentLabel = `contracts/components/${name}/content.contract.json`;
    const defaultsLabel = `contracts/components/${name}/tags.defaults.json`;
    let componentSchema: JsonObject | undefined;

    await check(tagsLabel, async () => {
      const schema = await readJson(path.join(layout.componentsDir, name, "tags.contract.json"));
      assertObject(schema, tagsLabel);
      assertNoDefaults(schema, tagsLabel);
      validateTagEntityContract(schema, tagsLabel, { componentType: name });
      assertEfficioTagNames(schema, tagsLabel);
      componentSchema = schema;
    });

    await check(contentLabel, async () => {
      const content = await readJson(path.join(layout.componentsDir, name, "content.contract.json"));
      assertObject(content, contentLabel);
      assertValidJsonSchema(content, contentLabel);
      if (name === "text") assertTextContentShape(content, contentLabel);
    });

    // Merge + defaults depend on a clean shared schema and a valid component
    // contract; skip them otherwise so the report shows root causes, not cascades.
    if (!sharedOk || componentSchema === undefined) continue;

    let builtSchema: JsonObject | undefined;
    await check(tagsLabel, () => {
      builtSchema = mergeTagSchema(sharedSchema, componentSchema as JsonObject, tagsLabel, sharedLabels);
    });
    if (builtSchema === undefined) continue;

    await check(sharedDefaultsLabel, () => {
      if (sharedDefaultsReadError !== undefined) throw sharedDefaultsReadError;
      validateComponentDefaults(sharedDefaultsRaw, builtSchema as JsonObject, sharedDefaultsLabel);
    });

    await check(defaultsLabel, async () => {
      const defaults = await readJson(path.join(layout.componentsDir, name, "tags.defaults.json"));
      validateComponentDefaults(defaults, builtSchema as JsonObject, defaultsLabel);
    });
  }

  // 3. General component instruction.
  const componentsInstructionLabel = "contracts/components/components.instructions.json";
  await check(componentsInstructionLabel, async () => {
    const value = await readJson(path.join(layout.componentsDir, "components.instructions.json"));
    assertObject(value, componentsInstructionLabel);
    validateComponentsInstruction(value, componentsInstructionLabel);
  });

  // 4. Presentation slide: tag contract, defaults, selection schema, instructions.
  const slideTagsLabel = "contracts/presentation/slide/tags.contract.json";
  let slideSchema: JsonObject | undefined;
  await check(slideTagsLabel, async () => {
    const schema = await readJson(path.join(layout.slideDir, "tags.contract.json"));
    assertObject(schema, slideTagsLabel);
    assertNoDefaults(schema, slideTagsLabel);
    validateTagEntityContract(schema, slideTagsLabel, { slideContractType: "slide_tags" });
    assertEfficioTagNames(schema, slideTagsLabel);
    slideSchema = schema;
  });

  if (slideSchema !== undefined) {
    const slideDefaultsLabel = "contracts/presentation/slide/tags.defaults.json";
    await check(slideDefaultsLabel, async () => {
      const defaults = await readJson(path.join(layout.slideDir, "tags.defaults.json"));
      assertObject(defaults, slideDefaultsLabel);
      validateSlideDefaults(defaults, slideSchema as JsonObject, slideDefaultsLabel);
    });
  }

  // 4b. Presentation deck: tag contract + defaults (presentation-level tags).
  const deckTagsLabel = "contracts/presentation/deck/tags.contract.json";
  let deckSchema: JsonObject | undefined;
  await check(deckTagsLabel, async () => {
    const schema = await readJson(path.join(layout.deckDir, "tags.contract.json"));
    assertObject(schema, deckTagsLabel);
    assertNoDefaults(schema, deckTagsLabel);
    validateTagEntityContract(schema, deckTagsLabel, { slideContractType: "deck_tags" });
    assertEfficioTagNames(schema, deckTagsLabel);
    deckSchema = schema;
  });

  if (deckSchema !== undefined) {
    const deckDefaultsLabel = "contracts/presentation/deck/tags.defaults.json";
    await check(deckDefaultsLabel, async () => {
      const defaults = await readJson(path.join(layout.deckDir, "tags.defaults.json"));
      assertObject(defaults, deckDefaultsLabel);
      validateSlideDefaults(defaults, deckSchema as JsonObject, deckDefaultsLabel);
    });
  }

  const selectionSchemaLabel = "contracts/presentation/slide/slide-selection.schema.json";
  await check(selectionSchemaLabel, async () => {
    const schema = await readJson(path.join(layout.slideDir, "slide-selection.schema.json"));
    assertObject(schema, selectionSchemaLabel);
    assertValidJsonSchema(schema, selectionSchemaLabel);
  });

  const slidesInstructionLabel = "contracts/presentation/slide/slides.instructions.json";
  let slidesInstructions: JsonObject | undefined;
  await check(slidesInstructionLabel, async () => {
    const value = await readJson(path.join(layout.slideDir, "slides.instructions.json"));
    assertObject(value, slidesInstructionLabel);
    validateSlidesInstructions(value, slidesInstructionLabel);
    slidesInstructions = value;
  });

  if (slideSchema !== undefined && deckSchema !== undefined && slidesInstructions !== undefined) {
    await check("presentation slide-selection groups", () => {
      validateSelectionGroupContract(
        deckSchema as JsonObject,
        slideSchema as JsonObject,
        slidesInstructions as JsonObject,
        "presentation slide-selection groups",
      );
    });
  }

  // Slide and template contracts are copied verbatim by the generator; it only
  // requires that they are JSON objects, so that is all the gate checks here.
  for (const [contractPath, file] of [
    ["contracts/presentation/slide/slide.contract.json", path.join(layout.slideDir, "slide.contract.json")],
    ["contracts/presentation/template/template.contract.json", path.join(layout.templateDir, "template.contract.json")],
  ] as const) {
    await check(contractPath, async () => {
      assertObject(await readJson(file), contractPath);
    });
  }

  return { ok: issues.length === 0, checked, issues };
}

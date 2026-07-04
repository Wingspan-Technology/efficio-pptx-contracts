import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { mergeTagSchema, type JsonObject } from "../scripts/contractLib";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const srcDir = path.join(pkgRoot, "src");
const contractsDir = path.join(pkgRoot, "contracts");
const componentsDir = path.join(contractsDir, "components");
const generatedTagsDir = path.join(pkgRoot, "generated", "schemas", "components");

const COMPONENTS = ["approval_block", "grouped_checklist_table", "table", "text"];
const COMMON_REQUIRED = [
  "efficio_render_behavior",
  "efficio_component_id",
  "efficio_component_type",
];

function readJson(filePath: string): JsonObject {
  return JSON.parse(readFileSync(filePath, "utf8")) as JsonObject;
}

function generatedFileFor(component: string): string {
  return path.join(generatedTagsDir, `${component.replace(/_/g, "-")}.json`);
}

const sharedLabels = [
  "contracts/shared/render-behavior-tags.contract.json",
  "contracts/shared/component-base-tags.contract.json",
];

function mergeShared(): JsonObject {
  const tags: JsonObject = {};
  for (const label of sharedLabels) {
    const fragment = readJson(path.join(pkgRoot, label));
    Object.assign(tags, fragment.tags);
  }
  return { tags };
}

const common = mergeShared();

describe.each(COMPONENTS)("generated tag schema for %s", (component) => {
  const file = generatedFileFor(component);

  it("exists and exposes the compatibility output fields", () => {
    expect(existsSync(file)).toBe(true);
    const schema = readJson(file);
    for (const field of ["required_tags", "optional_tags", "enums", "types", "json_schemas"]) {
      expect(schema).toHaveProperty(field);
    }
  });

  it("records generated_from pointing back to authored sources", () => {
    const schema = readJson(file);
    expect(schema.generated_from).toEqual([
      ...sharedLabels,
      `contracts/components/${component}/tags.contract.json`,
    ]);
  });

  it("composes the common required tags into the output", () => {
    const schema = readJson(file);
    expect(schema.required_tags).toEqual(expect.arrayContaining(COMMON_REQUIRED));
  });

  it("constrains efficio_component_type to the component type", () => {
    const enums = readJson(file).enums as JsonObject;
    expect(enums.efficio_component_type).toEqual([component]);
  });

  it("is reproducible byte-for-byte from authored sources via mergeTagSchema", () => {
    const label = `contracts/components/${component}/tags.contract.json`;
    const componentContract = readJson(path.join(componentsDir, component, "tags.contract.json"));
    const rebuilt = mergeTagSchema(common, componentContract, label, sharedLabels);
    const expected = `${JSON.stringify(rebuilt, null, 2)}\n`;
    expect(readFileSync(file, "utf8")).toBe(expected);
  });
});

describe("generated presentation schemas", () => {
  it("records presentation source paths", () => {
    expect(readJson(path.join(pkgRoot, "generated", "schemas", "presentation", "slide-tags.json")).generated_from).toBe(
      "contracts/presentation/slide/tags.contract.json",
    );
    expect(readJson(path.join(pkgRoot, "generated", "schemas", "presentation", "slide-contract.json")).generated_from).toBe(
      "contracts/presentation/slide/slide.contract.json",
    );
    expect(readJson(path.join(pkgRoot, "generated", "schemas", "presentation", "template-contract.json")).generated_from).toBe(
      "contracts/presentation/template/template.contract.json",
    );
  });
});

describe("generated JSON omits the redundant `generated` marker", () => {
  // The `generated/` folder name already signals provenance; the boolean
  // `generated: true` marker was removed. `generated_from` is retained.
  const jsonArtifacts = [
    "component-registry.json",
    "schemas/component-types.json",
    ...COMPONENTS.map((component) => `schemas/components/${component.replace(/_/g, "-")}.json`),
    "schemas/presentation/slide-tags.json",
    "schemas/presentation/slide-contract.json",
    "schemas/presentation/template-contract.json",
  ];

  for (const relativePath of jsonArtifacts) {
    it(`${relativePath} has no \`generated\` property`, () => {
      expect(readJson(path.join(pkgRoot, "generated", relativePath))).not.toHaveProperty("generated");
    });
  }

  it("retains generated_from provenance on schemas", () => {
    expect(readJson(path.join(pkgRoot, "generated", "schemas", "component-types.json"))).toHaveProperty("generated_from");
    expect(readJson(generatedFileFor("text"))).toHaveProperty("generated_from");
  });

  it("does not leak the marker into generated TS exports", () => {
    const registryTs = readFileSync(path.join(pkgRoot, "generated", "ts", "componentRegistry.ts"), "utf8");
    expect(registryTs).not.toContain('"generated": true');
  });
});

describe("Python SDK generated resource mirror", () => {
  const sdkGeneratedDir = path.join(srcDir, "efficio_ppt_components", "_generated");

  it.each(COMPONENTS)("mirrors %s component schema for Python SDK validation", (component) => {
    const relativePath = path.join("schemas", "components", `${component.replace(/_/g, "-")}.json`);
    expect(readJson(path.join(sdkGeneratedDir, relativePath))).toEqual(
      readJson(path.join(pkgRoot, "generated", relativePath)),
    );
  });

  it("mirrors slide tag schema for Python SDK validation", () => {
    const relativePath = path.join("schemas", "presentation", "slide-tags.json");
    expect(readJson(path.join(sdkGeneratedDir, relativePath))).toEqual(
      readJson(path.join(pkgRoot, "generated", relativePath)),
    );
  });
});

describe("text sizing tags", () => {
  it("generates sizing fields as normal required tags", () => {
    const schema = readJson(generatedFileFor("text"));
    expect(schema).not.toHaveProperty("conditional_required_tags");
    expect(schema.required_tags).toEqual(expect.arrayContaining([
      "efficio_max_chars",
      "efficio_max_lines",
      "efficio_max_chars_per_line",
    ]));
    expect(schema.optional_tags).not.toEqual(expect.arrayContaining([
      "efficio_max_chars",
      "efficio_max_lines",
      "efficio_max_chars_per_line",
    ]));
  });
});

describe("generated json_schemas for object/array tags", () => {
  it("text has an empty json_schemas map (no structured tags)", () => {
    expect(readJson(generatedFileFor("text")).json_schemas).toEqual({});
  });

  it("grouped_checklist_table maps efficio_groups (json_object) to its embedded schema", () => {
    const schema = readJson(generatedFileFor("grouped_checklist_table"));
    expect((schema.types as JsonObject).efficio_groups).toBe("json_object");
    const jsonSchemas = schema.json_schemas as JsonObject;
    expect(jsonSchemas).toHaveProperty("efficio_groups");
    const authored = readJson(path.join(componentsDir, "grouped_checklist_table", "tags.contract.json"));
    const authoredGroupsSchema = ((authored.tags as JsonObject).efficio_groups as JsonObject).schema;
    expect(jsonSchemas.efficio_groups).toEqual(authoredGroupsSchema);
  });

  it("table maps efficio_table_config (json_object) to its embedded schema", () => {
    const schema = readJson(generatedFileFor("table"));
    expect((schema.types as JsonObject).efficio_table_config).toBe("json_object");
    const jsonSchemas = schema.json_schemas as JsonObject;
    expect(jsonSchemas).toHaveProperty("efficio_table_config");
    const authored = readJson(path.join(componentsDir, "table", "tags.contract.json"));
    const authoredConfigSchema = ((authored.tags as JsonObject).efficio_table_config as JsonObject).schema;
    expect(jsonSchemas.efficio_table_config).toEqual(authoredConfigSchema);
  });

  it("table cells require only row + col; render_action is optional and defaults to preserve", () => {
    const configSchema = (readJson(generatedFileFor("table")).json_schemas as JsonObject)
      .efficio_table_config as JsonObject;
    const cellItems = ((configSchema.properties as JsonObject).cells as JsonObject)
      .items as JsonObject;
    expect(cellItems.required).toEqual(["row", "col"]);
    expect((cellItems.properties as JsonObject).render_action).toMatchObject({
      default: "preserve",
      enum: ["render", "preserve"],
    });
  });

  it("native metadata preserves the schema on the efficio_groups entity", () => {
    const metadataTs = readFileSync(
      path.join(pkgRoot, "generated", "ts", "components", "componentMetadata.ts"),
      "utf8",
    );
    const literal = metadataTs.slice(metadataTs.indexOf("{"), metadataTs.lastIndexOf("}") + 1);
    const metadata = JSON.parse(literal) as Record<string, JsonObject>;
    const groups = ((metadata.grouped_checklist_table.tags as JsonObject).efficio_groups as JsonObject);
    expect(groups.type).toBe("object");
    expect(groups).toHaveProperty("schema");
    expect(groups).not.toHaveProperty("ai");
  });
});

describe("generated AI component instructions", () => {
  const aiDir = path.join(pkgRoot, "generated", "ai");
  const aggregate = readJson(path.join(aiDir, "component-instructions.json"));
  const aggregateComponents = aggregate.component_instructions as Record<string, JsonObject>;

  function instructionFileFor(component: string): string {
    return path.join(aiDir, "components", `${component}.instruction.json`);
  }

  it("authored components.instructions.json contains only a non-empty instruction", () => {
    const authored = readJson(path.join(componentsDir, "components.instructions.json"));
    expect(Object.keys(authored)).toEqual(["instruction"]);
    expect(authored.instruction).toBeTypeOf("string");
    expect((authored.instruction as string).trim().length).toBeGreaterThan(0);
  });

  it("aggregate has exactly instruction + component_instructions and no build metadata", () => {
    expect(Object.keys(aggregate).sort()).toEqual(["component_instructions", "instruction"]);
    expect(aggregate).not.toHaveProperty("generated");
    expect(Object.keys(aggregateComponents).sort()).toEqual([...COMPONENTS].sort());
  });

  it("aggregate instruction equals the authored general instruction", () => {
    const authored = readJson(path.join(componentsDir, "components.instructions.json"));
    expect(aggregate.instruction).toBe(authored.instruction);
  });

  it.each(COMPONENTS)("per-component file for %s matches the aggregate entry exactly", (component) => {
    expect(existsSync(instructionFileFor(component))).toBe(true);
    expect(readJson(instructionFileFor(component))).toEqual(aggregateComponents[component]);
  });

  it.each(COMPONENTS)("%s tag_instructions only contains tags that declare ai", (component) => {
    const tagInstructions = (aggregateComponents[component].tag_instructions as JsonObject);
    for (const instruction of Object.values(tagInstructions)) {
      expect((instruction as JsonObject).purpose).toBeTypeOf("string");
    }
    // shared prompt instruction appears for every component
    expect(tagInstructions).toHaveProperty("efficio_prompt_instruction");
    // tags without ai must not appear
    expect(tagInstructions).not.toHaveProperty("efficio_component_id");
  });

  it("text includes its ai-bearing component tags but not sizing mode", () => {
    const tags = aggregateComponents.text.tag_instructions as JsonObject;
    expect(tags).toHaveProperty("efficio_text_format");
    expect(tags).toHaveProperty("efficio_max_chars");
    expect(tags).toHaveProperty("efficio_max_lines");
    expect(tags).toHaveProperty("efficio_max_chars_per_line");
    // sizing mode is a required editor/runtime tag but is no longer AI-visible
    expect(tags).not.toHaveProperty("efficio_sizing_mode");
  });

  it("grouped_checklist_table includes its ai-bearing efficio_groups tag", () => {
    const tags = aggregateComponents.grouped_checklist_table.tag_instructions as JsonObject;
    expect(tags).toHaveProperty("efficio_groups");
  });

  it.each(COMPONENTS)("%s: every AI-visible enum tag instruction has complete enum_descriptions", (component) => {
    const authored = readJson(path.join(componentsDir, component, "tags.contract.json"));
    const mergedTags = { ...(common.tags as JsonObject), ...(authored.tags as JsonObject) };
    const tagInstructions = aggregateComponents[component].tag_instructions as JsonObject;
    for (const [tag, entity] of Object.entries(mergedTags)) {
      const ent = entity as JsonObject;
      const ai = ent.ai as JsonObject | undefined;
      const enumValues = ent.enum;
      if (!ai || !Array.isArray(enumValues) || enumValues.length === 0) continue;
      // An AI-visible enum tag must reach the instructions with a description per value.
      expect(tagInstructions).toHaveProperty(tag);
      const descriptions = (tagInstructions[tag] as JsonObject).enum_descriptions as JsonObject;
      expect(descriptions).toBeTypeOf("object");
      expect(Object.keys(descriptions).sort()).toEqual(enumValues.map((value) => String(value)).sort());
      for (const value of Object.values(descriptions)) {
        expect(value).toBeTypeOf("string");
        expect((value as string).length).toBeGreaterThan(0);
      }
    }
  });

  it("text exposes the sizing limit tags as AI-visible instructions", () => {
    const tags = aggregateComponents.text.tag_instructions as JsonObject;
    for (const tag of ["efficio_max_chars", "efficio_max_lines", "efficio_max_chars_per_line"]) {
      expect(tags).toHaveProperty(tag);
      expect((tags[tag] as JsonObject).purpose).toBeTypeOf("string");
      // numeric limits have no enum, so no enum_descriptions
      expect(tags[tag]).not.toHaveProperty("enum_descriptions");
    }
  });

  it("approval_block excludes private table cell-mapping tags but keeps the AI-visible ones", () => {
    const tags = aggregateComponents.approval_block.tag_instructions as JsonObject;
    for (const tag of [
      "efficio_label_cell",
      "efficio_name_cell",
      "efficio_role_cell",
      "efficio_approval_block_layout",
    ]) {
      expect(tags).not.toHaveProperty(tag);
    }
    for (const tag of [
      "efficio_default_subtype",
      "efficio_subtype_policy",
      "efficio_missing_content_behavior",
      "efficio_approval_block_subtypes",
    ]) {
      expect(tags).toHaveProperty(tag);
    }
  });

  it.each(COMPONENTS)("%s expected_content_schema is the authored content contract directly (no wrapper)", (component) => {
    const expected = aggregateComponents[component].expected_content_schema as JsonObject;
    const authored = readJson(path.join(componentsDir, component, "content.contract.json"));
    expect(expected).toEqual(authored);
    // self-describing JSON Schema, no schema_standard/schema wrapper
    expect(expected).toHaveProperty("$schema");
    expect(expected).not.toHaveProperty("schema_standard");
    expect(expected).not.toHaveProperty("schema");
  });

  it.each(COMPONENTS)("%s instruction is prompt-facing only (no build/provenance metadata)", (component) => {
    const instruction = aggregateComponents[component] as JsonObject;
    expect(instruction).not.toHaveProperty("generated");
    expect(instruction).not.toHaveProperty("generated_from");
    expect(JSON.stringify(instruction)).not.toContain("content_contract");
    expect(JSON.stringify(instruction)).not.toContain("schema_standard");
    expect(Object.keys(instruction).sort()).toEqual([
      "component_type",
      "expected_content_schema",
      "tag_instructions",
    ]);
  });
});

describe("generated slide-selection AI instructions", () => {
  const slideDir = path.join(contractsDir, "presentation", "slide");
  const artifact = readJson(path.join(pkgRoot, "generated", "ai", "slide-selection.instruction.json"));

  it("authored slides.instructions.json contains only a non-empty description", () => {
    const instructions = readJson(path.join(slideDir, "slides.instructions.json"));
    expect(Object.keys(instructions)).toEqual(["description"]);
    expect(instructions.description).toBeTypeOf("string");
    expect((instructions.description as string).trim().length).toBeGreaterThan(0);
  });

  it("has exactly the prompt-facing fields and no build/wrapper metadata", () => {
    expect(Object.keys(artifact).sort()).toEqual([
      "description",
      "expected_slide_selection_schema",
      "slide_tag_instructions",
    ]);
    for (const forbidden of ["catalog_type", "generated", "generated_from", "schema_standard"]) {
      expect(artifact).not.toHaveProperty(forbidden);
    }
    // expected schema is the direct schema, not wrapped under a "schema" field
    expect(artifact.expected_slide_selection_schema).not.toHaveProperty("schema");
    expect(artifact.expected_slide_selection_schema).not.toHaveProperty("schema_standard");
  });

  it("slide_tag_instructions includes ai-bearing slide tags and excludes the rest", () => {
    const tags = artifact.slide_tag_instructions as JsonObject;
    expect(tags).toHaveProperty("efficio_slide_placement");
    expect(tags).toHaveProperty("efficio_slide_inclusion_policy");
    expect(tags).not.toHaveProperty("efficio_slide_id");
    expect(tags).not.toHaveProperty("efficio_slide_purpose");
  });

  it("expected_slide_selection_schema equals the authored slide-selection schema", () => {
    const authored = readJson(path.join(slideDir, "slide-selection.schema.json"));
    expect(artifact.expected_slide_selection_schema).toEqual(authored);
  });

  it("TS export mirrors the JSON artifact", () => {
    const tsSource = readFileSync(path.join(pkgRoot, "generated", "ts", "ai", "slideSelectionInstructions.ts"), "utf8");
    expect(tsSource).toContain("export const slideSelectionInstructions =");
    const literal = tsSource.slice(tsSource.indexOf("{"), tsSource.lastIndexOf("}") + 1);
    expect(JSON.parse(literal)).toEqual(artifact);
  });
});

// The Python SDK reads runtime JSON from efficio_ppt_components/_generated/, which
// is mirrored from the canonical top-level generated JSON in the same generation
// pass. These tests guard against the two locations drifting.
describe("SDK _generated runtime resources mirror top-level generated JSON", () => {
  const generatedDir = path.join(pkgRoot, "generated");
  const sdkGeneratedDir = path.join(pkgRoot, "src", "efficio_ppt_components", "_generated");

  const mirroredFiles = [
    "component-registry.json",
    path.join("ai", "component-instructions.json"),
    path.join("ai", "slide-selection.instruction.json"),
    ...COMPONENTS.map((component) => path.join("ai", "components", `${component}.instruction.json`)),
  ];

  for (const relativePath of mirroredFiles) {
    it(`${relativePath} is identical in both locations`, () => {
      const sdkPath = path.join(sdkGeneratedDir, relativePath);
      expect(existsSync(sdkPath), `missing SDK resource: ${relativePath}`).toBe(true);
      expect(readJson(sdkPath)).toEqual(readJson(path.join(generatedDir, relativePath)));
    });
  }
});

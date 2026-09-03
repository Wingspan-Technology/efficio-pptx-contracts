import { describe, expect, it } from "vitest";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { publicTagAlias, type JsonObject } from "../scripts/contractLib";
import { mergeTagSchema } from "../scripts/compatibilityTagSchema";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const srcDir = path.join(pkgRoot, "src");
const contractsDir = path.join(pkgRoot, "contracts");
const componentsDir = path.join(contractsDir, "components");
const generatedTagsDir = path.join(pkgRoot, "generated", "schemas", "components");

const COMPONENTS = ["category_chart", "table", "text"];
const COMMON_REQUIRED = [
  "efficio_content_mode",
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
  "contracts/shared/content-mode-tags.contract.json",
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
    expect(
      readJson(
        path.join(
          pkgRoot,
          "generated",
          "schemas",
          "presentation",
          "template-contract-migrations.json",
        ),
      ).generated_from,
    ).toEqual(["contracts/presentation/template/migrations/0000-to-0001.json"]);
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
    "schemas/presentation/template-contract-migrations.json",
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
  const sdkGeneratedDir = path.join(srcDir, "efficio_pptx_contracts", "_generated");

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

  it("mirrors deck tag schema for Python SDK validation", () => {
    const relativePath = path.join("schemas", "presentation", "deck-tags.json");
    expect(readJson(path.join(sdkGeneratedDir, relativePath))).toEqual(
      readJson(path.join(pkgRoot, "generated", relativePath)),
    );
  });

  it("mirrors the template migration catalog for Python SDK planning", () => {
    const relativePath = path.join(
      "schemas",
      "presentation",
      "template-contract-migrations.json",
    );
    expect(readJson(path.join(sdkGeneratedDir, relativePath))).toEqual(
      readJson(path.join(pkgRoot, "generated", relativePath)),
    );
  });
});

describe("deck template instruction tag", () => {
  const deckSchema = readJson(
    path.join(pkgRoot, "generated", "schemas", "presentation", "deck-tags.json"),
  );

  it("generates the optional efficio_template_instruction deck tag", () => {
    const tags = deckSchema.tags as JsonObject;
    const tag = tags.efficio_template_instruction as JsonObject;
    expect(tag).toBeDefined();
    expect(tag.type).toBe("string");
    expect(tag.required).toBe(false);
    expect(tag.max_length).toBe(2000);
    expect((tag.ui as JsonObject).multiline).toBe(true);
    expect(typeof (tag.ai as JsonObject).purpose).toBe("string");
  });

  it("assigns the deck instruction no default value", () => {
    const deckDefaults = readFileSync(
      path.join(pkgRoot, "generated", "ts", "presentation", "deckDefaults.ts"),
      "utf8",
    );
    expect(deckDefaults).not.toContain("efficio_template_instruction");
    // The authored defaults likewise omit it (absence/blank = no instruction).
    const authored = readJson(
      path.join(contractsDir, "presentation", "deck", "tags.defaults.json"),
    );
    expect(authored).not.toHaveProperty("efficio_template_instruction");
  });

  it("generates the optional direct-array slide-selection group tag", () => {
    const tag = (deckSchema.tags as JsonObject).efficio_slide_selection_groups as JsonObject;
    expect(tag.type).toBe("array");
    expect(tag.required).toBe(false);
    const schema = tag.schema as JsonObject;
    expect(schema.type).toBe("array");
    const item = schema.items as JsonObject;
    expect(item.required).toEqual(["group_id", "name", "type", "members"]);
    expect(item.additionalProperties).toBe(false);
  });
});

describe("slide display name tag", () => {
  const slideSchema = readJson(
    path.join(pkgRoot, "generated", "schemas", "presentation", "slide-tags.json"),
  );

  it("generates the optional efficio_slide_name slide tag with no ai block", () => {
    const tag = (slideSchema.tags as JsonObject).efficio_slide_name as JsonObject;
    expect(tag).toBeDefined();
    expect(tag.type).toBe("string");
    expect(tag.required).toBe(false);
    expect(tag.max_length).toBe(120);
    // A display label only — no AI instruction metadata, so it never reaches
    // slide_tag_instructions.
    expect(tag).not.toHaveProperty("ai");
  });
});

describe("slide role tag", () => {
  const slideSchema = readJson(
    path.join(pkgRoot, "generated", "schemas", "presentation", "slide-tags.json"),
  );

  it("generates the required content-or-separator contract", () => {
    const tag = (slideSchema.tags as JsonObject).efficio_slide_role as JsonObject;
    expect(tag.type).toBe("string");
    expect(tag.required).toBe(true);
    expect(tag.enum).toEqual(["content", "separator"]);
  });

  it("keeps role descriptive and independent of selection behavior", () => {
    const tag = (slideSchema.tags as JsonObject).efficio_slide_role as JsonObject;
    const purpose = (tag.ai as JsonObject).purpose as string;
    expect(purpose).toContain("normal content or a section divider");
    expect(purpose).toContain("does not control inclusion, placement, ordering, or grouping");
  });
});

describe("text sizing tags", () => {
  it("generates sizing fields as normal required tags", () => {
    const schema = readJson(generatedFileFor("text"));
    expect(schema).not.toHaveProperty("conditional_required_tags");
    // The strict sizing limits are required; the target_* guidance tags are optional.
    expect(schema.required_tags).toEqual(expect.arrayContaining([
      "efficio_max_chars",
      "efficio_min_items",
      "efficio_max_items",
      "efficio_min_chars_per_item",
      "efficio_max_chars_per_item",
    ]));
    expect(schema.optional_tags).toEqual(expect.arrayContaining([
      "efficio_target_chars",
      "efficio_target_chars_per_item",
    ]));
    expect(schema.required_tags).not.toEqual(
      expect.arrayContaining(["efficio_target_chars", "efficio_target_chars_per_item"])
    );
  });

  it("adds efficio_target_items as an optional integer sizing tag (never required)", () => {
    const schema = readJson(generatedFileFor("text"));
    expect(schema.optional_tags).toEqual(expect.arrayContaining(["efficio_target_items"]));
    expect(schema.required_tags).not.toContain("efficio_target_items");
    expect((schema.types as JsonObject).efficio_target_items).toBe("positive_integer_string");
  });
});

describe("generated json_schemas for object/array tags", () => {
  it("text has an empty json_schemas map (no structured tags)", () => {
    expect(readJson(generatedFileFor("text")).json_schemas).toEqual({});
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

  it("native metadata preserves the schema on the efficio_table_config entity", () => {
    const metadataTs = readFileSync(
      path.join(pkgRoot, "generated", "ts", "components", "componentMetadata.ts"),
      "utf8",
    );
    const literal = metadataTs.slice(metadataTs.indexOf("{"), metadataTs.lastIndexOf("}") + 1);
    const metadata = JSON.parse(literal) as Record<string, JsonObject>;
    const config = ((metadata.table.tags as JsonObject).efficio_table_config as JsonObject);
    expect(config.type).toBe("object");
    expect(config).toHaveProperty("schema");
  });
});

describe("generated category_chart flat tags", () => {
  const schema = readJson(generatedFileFor("category_chart"));

  it("requires the flat chart tags and maps their compatibility types", () => {
    expect(schema.required_tags).toEqual(
      expect.arrayContaining([
        "efficio_chart_type",
        "efficio_category_mode",
        "efficio_series_mode",
        "efficio_min_categories",
        "efficio_value_type",
        "efficio_allow_negative_values",
      ]),
    );
    const types = schema.types as JsonObject;
    expect(types.efficio_chart_type).toBe("enum");
    expect(types.efficio_min_categories).toBe("positive_integer_string");
    expect(types.efficio_allow_negative_values).toBe("enum_boolean_string");
    // The fixed-label arrays are json_array tags carrying their embedded schema.
    expect(types.efficio_categories).toBe("json_array");
    expect(schema.json_schemas as JsonObject).toHaveProperty("efficio_categories");
    // No single config object tag remains.
    expect(schema.required_tags).not.toContain("efficio_category_chart_config");
  });

  it("fixes the chart-type/mode enums and the label-array schema from the authored contract", () => {
    const enums = schema.enums as JsonObject;
    expect(enums.efficio_chart_type).toEqual([
      "CLUSTERED_COLUMN",
      "STACKED_COLUMN",
      "PERCENTS_STACKED_COLUMN",
      "CLUSTERED_BAR",
      "STACKED_BAR",
      "PERCENTS_STACKED_BAR",
    ]);
    expect(enums.efficio_category_mode).toEqual(["fixed", "ai_generated"]);
    const authored = readJson(path.join(componentsDir, "category_chart", "tags.contract.json"));
    const authoredCategories = ((authored.tags as JsonObject).efficio_categories as JsonObject).schema;
    expect((schema.json_schemas as JsonObject).efficio_categories).toEqual(authoredCategories);
  });

  it("exposes the flat chart tags to AI under their public aliases (no efficio_ prefix)", () => {
    const instruction = readJson(
      path.join(pkgRoot, "generated", "ai", "components", "category_chart.instruction.json"),
    );
    const tagInstructions = instruction.tag_instructions as JsonObject;
    expect(tagInstructions).toHaveProperty("chart_type");
    expect(tagInstructions).toHaveProperty("categories");
    expect(tagInstructions).not.toHaveProperty("category_chart_config");
    expect(tagInstructions).not.toHaveProperty("efficio_chart_type");
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
    // tags without ai must not appear
    expect(tagInstructions).not.toHaveProperty("component_id");
  });

  it.each(COMPONENTS)("%s tag_instructions excludes the structural tags (they never reach tag_context)", (component) => {
    const tagInstructions = aggregateComponents[component].tag_instructions as JsonObject;
    // render_behavior filters AI-facing components; prompt_instruction surfaces
    // as the per-instance top-level instructions field.
    for (const structural of ["render_behavior", "prompt_instruction"]) {
      expect(tagInstructions).not.toHaveProperty(structural);
      expect(tagInstructions).not.toHaveProperty(`efficio_${structural}`);
    }
  });

  it.each(COMPONENTS)("%s tag_instructions keys are public aliases, never raw efficio_* names", (component) => {
    const tagInstructions = aggregateComponents[component].tag_instructions as JsonObject;
    for (const key of Object.keys(tagInstructions)) {
      expect(key, `${component} tag_instructions key ${key}`).not.toMatch(/^efficio_/);
    }
  });

  it.each(COMPONENTS)("%s instruction artifact contains no efficio_ anywhere in its JSON", (component) => {
    // The whole content-generation artifact (tag_instructions keys, purposes,
    // enum_descriptions, expected_content_schema prose) speaks public names only.
    expect(JSON.stringify(aggregateComponents[component])).not.toContain("efficio_");
  });

  it("the aggregate component-instructions artifact contains no efficio_ anywhere", () => {
    expect(JSON.stringify(aggregate)).not.toContain("efficio_");
  });

  it("text includes its ai-bearing component tags but not sizing mode", () => {
    const tags = aggregateComponents.text.tag_instructions as JsonObject;
    expect(tags).toHaveProperty("text_format");
    expect(tags).toHaveProperty("max_chars");
    expect(tags).toHaveProperty("min_items");
    expect(tags).toHaveProperty("max_items");
    expect(tags).toHaveProperty("target_items");
    expect(tags).toHaveProperty("max_chars_per_item");
    expect(tags).toHaveProperty("target_chars_per_item");
    // sizing mode is a required editor/runtime tag but is no longer AI-visible
    expect(tags).not.toHaveProperty("sizing_mode");
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
      // An AI-visible enum tag must reach the instructions (under its public
      // alias) with a description per value.
      const alias = publicTagAlias(tag);
      expect(tagInstructions).toHaveProperty(alias);
      const descriptions = (tagInstructions[alias] as JsonObject).enum_descriptions as JsonObject;
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
    for (const tag of [
      "max_chars",
      "min_items",
      "max_items",
      "min_chars_per_item",
      "max_chars_per_item",
    ]) {
      expect(tags).toHaveProperty(tag);
      expect((tags[tag] as JsonObject).purpose).toBeTypeOf("string");
      // numeric limits have no enum, so no enum_descriptions
      expect(tags[tag]).not.toHaveProperty("enum_descriptions");
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

describe("strict sizing instruction wording", () => {
  const aggregate = readJson(path.join(pkgRoot, "generated", "ai", "component-instructions.json"));
  const aggregateComponents = aggregate.component_instructions as Record<string, JsonObject>;

  // Sizing/count fields are strict requirements for the AI; hint language must
  // never come back through authored sources.
  const FORBIDDEN_HINT_PHRASES = [
    "soft ai hint",
    "optional sizing hint",
    "sizing hint",
    "not hard limits",
    "not a hard limit",
  ];

  function generatedFiles(dir: string): string[] {
    return (readdirSync(dir, { recursive: true }) as string[])
      .map((entry) => path.join(dir, entry))
      .filter((entry) => /\.(json|ts)$/.test(entry));
  }

  function purposeOf(component: string, tag: string): string {
    const tags = aggregateComponents[component].tag_instructions as JsonObject;
    return (tags[tag] as JsonObject).purpose as string;
  }

  it("no generated output carries soft-hint sizing language", () => {
    for (const file of generatedFiles(path.join(pkgRoot, "generated"))) {
      const content = readFileSync(file, "utf8").toLowerCase();
      for (const phrase of FORBIDDEN_HINT_PHRASES) {
        expect(content, `${file} contains forbidden phrase "${phrase}"`).not.toContain(phrase);
      }
    }
  });

  it.each([
    ["text", "max_chars"],
    ["text", "max_items"],
    ["text", "max_chars_per_item"],
    ["table", "table_config"],
  ])("%s %s purpose demands strict, never-exceeded sizing", (component, tag) => {
    const purpose = purposeOf(component, tag).toLowerCase();
    expect(purpose).toContain("strict");
    expect(purpose).toContain("must never exceed");
    expect(purpose).toMatch(/shorten or compact/);
  });

  it("the general instruction calls sizing/count constraints strict requirements", () => {
    const instruction = (aggregate.instruction as string).toLowerCase();
    expect(instruction).toContain("strict requirements, not guidance");
    expect(instruction).toContain("must never exceed");
    expect(instruction).toMatch(/shorten or compact/);
  });
});

describe("table content generation instructions", () => {
  const aggregate = readJson(path.join(pkgRoot, "generated", "ai", "component-instructions.json"));
  const aggregateComponents = aggregate.component_instructions as Record<string, JsonObject>;
  const tableInstruction = aggregateComponents.table;
  const tablePurpose = (
    (tableInstruction.tag_instructions as JsonObject).table_config as JsonObject
  ).purpose as string;

  it("output is keyed by \"row,col\" and returns generated content only", () => {
    expect(tablePurpose).toContain('cells["1,2"]');
    expect(tablePurpose).toContain('Return only generated cell content keyed by "row,col"');
    expect(tablePurpose).toContain("never return table config");
  });

  it("row instructions apply to every generated cell in that row", () => {
    expect(tablePurpose).toContain("rows[] contains row-level guidance");
    expect(tablePurpose).toContain(
      "a row instruction applies to every generated cell whose row matches that row index",
    );
  });

  it("column instructions apply to every generated cell in that column", () => {
    expect(tablePurpose).toContain("columns[] contains column-level guidance");
    expect(tablePurpose).toContain(
      "a column instruction applies to every generated cell whose col matches that column index",
    );
  });

  it("component, row, column, and cell instructions are combined per cell", () => {
    expect(tablePurpose).toContain(
      "combine the component-level instruction, matching row instruction, matching column instruction, and that cell's instruction",
    );
    // cell instruction is most specific, but row/column still apply
    expect(tablePurpose).toContain("The cell instruction is the most specific");
    expect(tablePurpose).toContain("row and column instructions must still be followed");
  });

  it("cell sizing is item-based, strict where present, with target guidance", () => {
    expect(tablePurpose).toContain("Cell sizing fields are optional");
    // strict item vocabulary shared with the text component, not lines
    expect(tablePurpose).toContain("min_items and max_items");
    expect(tablePurpose).toContain("min_chars_per_item and max_chars_per_item");
    expect(tablePurpose).toContain("must never exceed");
    expect(tablePurpose).toMatch(/shorten or compact/);
    // max_chars is the aggregate budget; target_* are guidance only
    expect(tablePurpose).toContain("max_chars is the strict total character budget");
    expect(tablePurpose).toContain("guidance only, not limits");
    // the removed line-based vocabulary must be gone
    expect(tablePurpose).not.toContain("max_lines");
    expect(tablePurpose).not.toContain("max_chars_per_line");
  });

  it("only render cells receive content; preserve or missing render_action is not returned", () => {
    expect(tablePurpose).toContain(
      'only cells with render_action "render" can receive generated content',
    );
    expect(tablePurpose).toContain(
      "preserve or missing render_action means keep authored content and do not return that cell",
    );
    expect(tablePurpose).toContain("content_policy does not make a preserved cell renderable");
  });

  it("explains optional-row removal without encouraging filler content", () => {
    expect(tablePurpose).toContain('For a row with content_policy "optional"');
    expect(tablePurpose).toContain("omit every render cell in that row when no applicable content exists");
    expect(tablePurpose).toContain("at least one non-whitespace string");
    expect(tablePurpose).toContain("never invent filler or placeholder content merely to keep it");
    expect(tablePurpose).toContain("A required or unspecified row remains");
    expect(tablePurpose).toContain(
      'A column with content_policy "optional" permits its matching render cells to be omitted but never removes a row',
    );
  });

  it("expected content schema describes generated content keyed to configured render cells", () => {
    const schema = tableInstruction.expected_content_schema as JsonObject;
    expect(schema.description as string).toContain(
      "generated cell content only, never table configuration",
    );
    expect(schema.description as string).toContain(
      "For an optional row with no applicable content, omit every render cell in that row",
    );
    const cells = (schema.properties as JsonObject).cells as JsonObject;
    expect(cells.description as string).toContain("must match a render cell configured");
    const items = ((cells.additionalProperties as JsonObject).properties as JsonObject)
      .items as JsonObject;
    expect(items.description as string).toContain("never exceed the cell's strict limits");
  });
});

describe("generated slide-selection AI instructions", () => {
  const slideDir = path.join(contractsDir, "presentation", "slide");
  const artifact = readJson(path.join(pkgRoot, "generated", "ai", "slide-selection.instruction.json"));

  it("authored slides.instructions.json owns the group purpose, types, and rules", () => {
    const instructions = readJson(path.join(slideDir, "slides.instructions.json"));
    expect(Object.keys(instructions)).toEqual(["description", "selection_group_instructions"]);
    expect(instructions.description).toBeTypeOf("string");
    expect((instructions.description as string).trim().length).toBeGreaterThan(0);
    const groups = instructions.selection_group_instructions as JsonObject;
    expect(Object.keys(groups)).toEqual(["purpose", "type_descriptions", "rules"]);
    expect(groups).not.toHaveProperty("inclusion_policy_descriptions");
  });

  it("has exactly the prompt-facing fields and no build/wrapper metadata", () => {
    expect(Object.keys(artifact).sort()).toEqual([
      "description",
      "expected_slide_selection_schema",
      "selection_group_instructions",
      "slide_tag_instructions",
    ]);
    for (const forbidden of ["catalog_type", "generated", "generated_from", "schema_standard"]) {
      expect(artifact).not.toHaveProperty(forbidden);
    }
    // expected schema is the direct schema, not wrapped under a "schema" field
    expect(artifact.expected_slide_selection_schema).not.toHaveProperty("schema");
    expect(artifact.expected_slide_selection_schema).not.toHaveProperty("schema_standard");
  });

  it("derives group policy guidance from the slide inclusion-policy tag", () => {
    const instructions = artifact.selection_group_instructions as JsonObject;
    const slideTags = readJson(path.join(slideDir, "tags.contract.json"));
    const policy = (slideTags.tags as JsonObject).efficio_slide_inclusion_policy as JsonObject;
    expect(instructions.inclusion_policy_descriptions).toEqual(
      (policy.ai as JsonObject).enum_descriptions,
    );
  });

  it("slide_tag_instructions includes ai-bearing slide tags and excludes the rest", () => {
    const tags = artifact.slide_tag_instructions as JsonObject;
    const slideTags = readJson(path.join(slideDir, "tags.contract.json"));
    const role = (slideTags.tags as JsonObject).efficio_slide_role as JsonObject;

    expect(tags.efficio_slide_role).toEqual(role.ai);
    expect(tags).toHaveProperty("efficio_slide_placement");
    expect(tags).toHaveProperty("efficio_slide_inclusion_policy");
    expect(tags).not.toHaveProperty("efficio_slide_id");
    expect(tags).not.toHaveProperty("efficio_slide_purpose");
    // The display-name tag has no ai block, so it is never an AI instruction.
    expect(tags).not.toHaveProperty("efficio_slide_name");
  });

  it("expected_slide_selection_schema equals the authored slide-selection schema", () => {
    const authored = readJson(path.join(slideDir, "slide-selection.schema.json"));
    expect(artifact.expected_slide_selection_schema).toEqual(authored);
  });

  it("selected-slide items carry slide_id only", () => {
    const schema = artifact.expected_slide_selection_schema as JsonObject;
    const selected = (schema.properties as JsonObject).selected_slides as JsonObject;
    const item = selected.items as JsonObject;
    expect(Object.keys(item.properties as JsonObject)).toEqual(["slide_id"]);
    expect(item.required).toEqual(["slide_id"]);
    expect(item.additionalProperties).toBe(false);
  });

  it("TS export mirrors the JSON artifact", () => {
    const tsSource = readFileSync(path.join(pkgRoot, "generated", "ts", "ai", "slideSelectionInstructions.ts"), "utf8");
    expect(tsSource).toContain("export const slideSelectionInstructions =");
    const literal = tsSource.slice(tsSource.indexOf("{"), tsSource.lastIndexOf("}") + 1);
    expect(JSON.parse(literal)).toEqual(artifact);
  });
});

// The Python SDK reads runtime JSON from efficio_pptx_contracts/_generated/, which
// is mirrored from the canonical top-level generated JSON in the same generation
// pass. These tests guard against the two locations drifting.
describe("SDK _generated runtime resources mirror top-level generated JSON", () => {
  const generatedDir = path.join(pkgRoot, "generated");
  const sdkGeneratedDir = path.join(pkgRoot, "src", "efficio_pptx_contracts", "_generated");

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

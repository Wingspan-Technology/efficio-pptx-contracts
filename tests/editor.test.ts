import { describe, expect, it } from "vitest";

import { componentMetadata } from "../generated/ts/components/componentMetadata";
import {
  getAllKnownComponentTags,
  getCommonComponentTags,
  getComponentCompatibilityTagSchema,
  getComponentMetadata,
  getComponentTagContract,
  getComponentTagDefaults,
  getCompatibilityTagSchemaMap,
  getDeckTagContract,
  getDeckTagDefaults,
  getContentModeValues,
  getSlideTagContract,
  getSlideTagDefaults,
  getTagEnumValues,
  hasComponentType,
  listComponentCompatibilityTagSchemas,
  listComponentTypes,
  estimateTextLineUse,
  validateTextCapacity,
  validateTableConfigSemantics,
  validateTextSizingSemantics,
  DECK_TEMPLATE_ID_TAG,
  DECK_INITIALIZED_TAG,
  DECK_TEMPLATE_CONTRACT_REVISION_TAG,
  DECK_CLASSIFICATION_SCHEMES_TAG,
  DECK_SLIDE_SELECTION_GROUPS_TAG,
  SLIDE_ID_TAG,
  SLIDE_ROLE_TAG,
  SLIDE_ROLES,
  SLIDE_PLACEMENTS,
  SLIDE_PURPOSE_MAX_LENGTH,
  type SlideRole,
} from "../ts/editor";

const EXPECTED_TYPES = ["categorical_fill", "category_chart", "table", "text"];

describe("editor SDK component metadata", () => {
  it("lists the same component types as the generated metadata", () => {
    expect(listComponentTypes().sort()).toEqual([...EXPECTED_TYPES].sort());
    expect(listComponentTypes().sort()).toEqual(Object.keys(componentMetadata).sort());
  });

  it("each metadata key matches its component_type", () => {
    for (const componentType of listComponentTypes()) {
      expect(getComponentMetadata(componentType).component_type).toBe(componentType);
    }
  });

  it("throws clearly for an unknown component type", () => {
    expect(hasComponentType("missing")).toBe(false);
    expect(() => getComponentMetadata("missing")).toThrow(/Unknown Efficio component type "missing"/);
  });

  it("exposes tag contracts and defaults", () => {
    const tags = getComponentTagContract("text");
    expect(tags.efficio_component_type.enum).toEqual(["text"]);
    const defaults = getComponentTagDefaults("text");
    expect(defaults.efficio_sizing_mode).toBe("auto");
    // Shape-specific capacity is filled by auto sizing or manually.
    expect(defaults.efficio_max_lines).toBeUndefined();
  });

  it("returns a defensive copy of defaults", () => {
    const defaults = getComponentTagDefaults("text");
    defaults.efficio_sizing_mode = "manual";
    expect(getComponentTagDefaults("text").efficio_sizing_mode).toBe("auto");
  });

  it("returns defensive copies of component metadata and nested tag contracts", () => {
    const metadata = getComponentMetadata("text");
    metadata.paths.tags_contract = "mutated";
    metadata.defaults.efficio_sizing_mode = "manual";
    metadata.tags.efficio_component_type.description = "mutated";

    const fresh = getComponentMetadata("text");
    expect(fresh.paths.tags_contract).not.toBe("mutated");
    expect(fresh.defaults.efficio_sizing_mode).toBe("auto");
    expect(fresh.tags.efficio_component_type.description).not.toBe("mutated");

    const tags = getComponentTagContract("text");
    tags.efficio_component_type.description = "mutated again";
    expect(getComponentTagContract("text").efficio_component_type.description).not.toBe(
      "mutated again"
    );

    const table = getComponentMetadata("table");
    const properties = table.tags.efficio_table_config.schema?.properties as Record<
      string,
      unknown
    >;
    properties.cells = "mutated";
    const freshProperties = getComponentMetadata("table").tags.efficio_table_config.schema
      ?.properties as Record<string, unknown>;
    expect(freshProperties.cells).not.toBe("mutated");
  });

  it("derives common tags, all known tags, and content mode values", () => {
    const common = getCommonComponentTags();
    expect(common.has("efficio_component_type")).toBe(true);
    expect(common.has("efficio_content_mode")).toBe(true);
    const all = getAllKnownComponentTags();
    expect(all.has("efficio_text_format")).toBe(true);
    expect(getContentModeValues()).toEqual([
      "ai_generated",
      "data_bound",
      "preserve",
      "remove",
    ]);
  });

  it("derives enum values for boolean and enum tags", () => {
    expect(getTagEnumValues({ type: "boolean", required: true })).toEqual(["true", "false"]);
    expect(getTagEnumValues({ type: "string", required: true, enum: ["a", "b"] })).toEqual(["a", "b"]);
    expect(getTagEnumValues({ type: "string", required: true })).toBeUndefined();
  });
});

describe("editor SDK compatibility tag schemas", () => {
  it("exposes the text compatibility schema", () => {
    const schema = getComponentCompatibilityTagSchema("text");
    expect(schema.component_type).toBe("text");
    expect(schema.required_tags).toContain("efficio_component_type");
    expect(schema.enums.efficio_content_mode).toContain("preserve");
  });

  it("throws for unknown compatibility schema", () => {
    expect(() => getComponentCompatibilityTagSchema("missing")).toThrow(/Unknown Efficio component type "missing"/);
  });

  it("lists one compatibility schema per component type", () => {
    expect(listComponentCompatibilityTagSchemas().map((s) => s.component_type).sort()).toEqual([...EXPECTED_TYPES].sort());
  });

  it("returns defensive copies of compatibility schemas", () => {
    const schema = getComponentCompatibilityTagSchema("text");
    schema.component_type = "mutated";
    schema.types.efficio_component_type = "mutated";
    (schema.required_tags as string[])[0] = "mutated";
    (schema.enums.efficio_content_mode as string[])[0] = "mutated";

    expect(getComponentCompatibilityTagSchema("text").component_type).toBe("text");
    expect(getComponentCompatibilityTagSchema("text").types.efficio_component_type).not.toBe(
      "mutated"
    );
    expect(getComponentCompatibilityTagSchema("text").required_tags[0]).not.toBe("mutated");
    expect(getComponentCompatibilityTagSchema("text").enums.efficio_content_mode[0]).not.toBe(
      "mutated"
    );

    const schemas = getCompatibilityTagSchemaMap();
    schemas.text.component_type = "mutated again";
    expect(getCompatibilityTagSchemaMap().text.component_type).toBe("text");
  });
});

describe("editor SDK slide surface", () => {
  it("re-exports slide tag constants and enums", () => {
    const role: SlideRole = "separator";

    expect(SLIDE_ID_TAG).toBe("efficio_slide_id");
    expect(SLIDE_ROLE_TAG).toBe("efficio_slide_role");
    expect(SLIDE_ROLES).toEqual(["content", "separator"]);
    expect(role).toBe("separator");
    expect(SLIDE_PLACEMENTS).toContain("body");
    expect(typeof SLIDE_PURPOSE_MAX_LENGTH).toBe("number");
  });

  it("exposes slide defaults as a copy", () => {
    const defaults = getSlideTagDefaults();
    expect(defaults).toBeTypeOf("object");
    expect(defaults.efficio_slide_role).toBe("content");
  });

  it("exposes the slide tag contract as a defensive copy", () => {
    const contract = getSlideTagContract() as unknown as {
      tags: Record<string, { description: string }>;
    };
    contract.tags.efficio_slide_id.description = "mutated";
    expect(getSlideTagContract().tags.efficio_slide_id.description).not.toBe("mutated");
  });
});

describe("editor SDK deck surface", () => {
  it("re-exports the deck tag constants", () => {
    expect(DECK_TEMPLATE_ID_TAG).toBe("efficio_template_id");
    expect(DECK_INITIALIZED_TAG).toBe("efficio_initialized");
    expect(DECK_TEMPLATE_CONTRACT_REVISION_TAG).toBe(
      "efficio_template_contract_revision",
    );
    expect(DECK_CLASSIFICATION_SCHEMES_TAG).toBe(
      "efficio_classification_schemes",
    );
    expect(DECK_SLIDE_SELECTION_GROUPS_TAG).toBe("efficio_slide_selection_groups");
  });

  it("exposes the deck tag contract with the template-id entity", () => {
    const contract = getDeckTagContract();
    expect(contract.contract_type).toBe("deck_tags");
    const entity = contract.tags.efficio_template_id;
    expect(entity.type).toBe("string");
    expect(entity.required).toBe(true);
    expect(entity.pattern).toBe("^[a-z0-9][a-z0-9_-]*$");
  });

  it("exposes the optional efficio_initialized enum entity", () => {
    const entity = getDeckTagContract().tags.efficio_initialized;
    expect(entity.type).toBe("string");
    expect(entity.required).toBe(false);
    expect(entity.enum).toEqual(["true"]);
  });

  it("exposes slide-selection groups as an optional direct JSON array", () => {
    const entity = getDeckTagContract().tags.efficio_slide_selection_groups;
    expect(entity.type).toBe("array");
    expect(entity.required).toBe(false);
    expect(entity.schema.type).toBe("array");
  });

  it("exposes reusable RGB classification schemes", () => {
    const entity = getDeckTagContract().tags.efficio_classification_schemes;
    expect(entity.type).toBe("array");
    expect(entity.required).toBe(false);
    expect(entity.schema.type).toBe("array");
    expect(entity.schema.maxItems).toBe(50);
    expect(entity.schema.items.properties.palette_mode.enum).toEqual(["rgb"]);
    expect(entity.schema.items.properties.cases.maxItems).toBe(32);
  });

  it("exposes the hidden current template contract revision", () => {
    const entity = getDeckTagContract().tags.efficio_template_contract_revision;
    expect(entity.type).toBe("integer");
    expect(entity.required).toBe(true);
    expect(entity.minimum).toBe(1);
    expect(entity.ui.hidden).toBe(true);
    expect(getDeckTagDefaults().efficio_template_contract_revision).toBe("2");
  });

  it("exposes the deck tag contract as a defensive copy", () => {
    const contract = getDeckTagContract() as unknown as {
      tags: Record<string, { description: string }>;
    };
    contract.tags.efficio_template_id.description = "mutated";
    expect(getDeckTagContract().tags.efficio_template_id.description).not.toBe("mutated");
  });

  it("defaults efficio_template_id to default_template but never efficio_initialized", () => {
    const defaults = getDeckTagDefaults() as Record<string, string>;
    expect(defaults.efficio_template_id).toBe("default_template");
    // Only the editor's initialization step writes efficio_initialized; it is not a default.
    expect(defaults.efficio_initialized).toBeUndefined();
  });

  it("exposes deck defaults as a defensive copy", () => {
    const defaults = getDeckTagDefaults() as Record<string, string>;
    defaults.efficio_template_id = "mutated";
    expect((getDeckTagDefaults() as Record<string, string>).efficio_template_id).toBe(
      "default_template"
    );
  });
});

describe("validateTableConfigSemantics (SDK table cross-field rule)", () => {
  const cfg = (cells: unknown[], extra: Record<string, unknown> = {}): Record<string, string> => ({
    efficio_table_config: JSON.stringify({ cells, ...extra }),
  });

  it("passes a clean config and is a no-op without the tag", () => {
    expect(validateTableConfigSemantics({})).toEqual([]);
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            text_format: "bullets",
            max_lines: 4,
            estimated_chars_per_line: 20,
            min_items: 1,
            max_items: 3,
            target_items: 2,
          },
        ])
      )
    ).toEqual([]);
  });

  it("flags item bounds, line capacity, and plain single-item violations", () => {
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            text_format: "bullets",
            max_lines: 4,
            estimated_chars_per_line: 20,
            min_items: 4,
            max_items: 2,
          },
        ])
      ).some((i) => i.code === "min_exceeds_max")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            text_format: "bullets",
            max_lines: 4,
            estimated_chars_per_line: 20,
            min_items: 1,
            max_items: 5,
          },
        ])
      ).some((i) => i.code === "items_exceed_line_capacity")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            text_format: "bullets",
            max_lines: 4,
            estimated_chars_per_line: 20,
            min_items: 1,
            max_items: 2,
            target_items: 5,
          },
        ])
      ).some((i) => i.code === "target_exceeds_max")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            text_format: "plain",
            max_lines: 3,
            estimated_chars_per_line: 20,
            min_items: 1,
            max_items: 3,
          },
        ])
      ).some((i) => i.code === "plain_requires_single_item")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([
          {
            row: 0,
            col: 0,
            render_action: "render",
            max_lines: 3,
            estimated_chars_per_line: 20,
            min_items: 1,
            max_items: 1,
            target_items: 1,
          },
        ])
      ).some((i) => i.code === "plain_forbids_target_items")
    ).toBe(true);
  });

  it("does not apply text-capacity semantics to preserved cells", () => {
    const invalidCapacity = {
      row: 0,
      col: 0,
      max_lines: 2,
      estimated_chars_per_line: 20,
      min_items: 3,
      max_items: 4,
    };

    expect(validateTableConfigSemantics(cfg([invalidCapacity]))).toEqual([]);
    expect(
      validateTableConfigSemantics(
        cfg([{ ...invalidCapacity, render_action: "preserve" }])
      )
    ).toEqual([]);
  });

  it("flags duplicate cell / row / column coordinates once each", () => {
    expect(
      validateTableConfigSemantics(
        cfg([
          { row: 0, col: 0 },
          { row: 0, col: 0 },
        ])
      ).filter((i) => i.code === "duplicate_cell")
    ).toHaveLength(1);
    expect(
      validateTableConfigSemantics(cfg([], { rows: [{ row: 1 }, { row: 1 }] })).some(
        (i) => i.code === "duplicate_row"
      )
    ).toBe(true);
    expect(
      validateTableConfigSemantics(cfg([], { columns: [{ col: 2 }, { col: 2 }] })).some(
        (i) => i.code === "duplicate_column"
      )
    ).toBe(true);
  });

  it("skips semantics on invalid/non-object JSON (structural layer owns it)", () => {
    expect(validateTableConfigSemantics({ efficio_table_config: "{not json" })).toEqual([]);
    expect(validateTableConfigSemantics({ efficio_table_config: "[]" })).toEqual([]);
  });
});

describe("text capacity SDK", () => {
  const capacity = {
    max_lines: 4,
    estimated_chars_per_line: 20,
    min_items: 1,
    max_items: 4,
  };

  it("validates positive item bounds within the available lines", () => {
    expect(validateTextCapacity(capacity, "multi_item")).toEqual([]);
    expect(
      validateTextCapacity({ ...capacity, max_items: 5 }, "multi_item")
    ).toContainEqual(expect.objectContaining({ code: "items_exceed_line_capacity" }));
    expect(
      validateTextCapacity({ ...capacity, min_items: 3, max_items: 2 }, "multi_item")
    ).toContainEqual(expect.objectContaining({ code: "min_exceeds_max" }));
    expect(
      validateTextCapacity({ ...capacity, estimated_chars_per_line: 0 }, "multi_item")
    ).toContainEqual(
      expect.objectContaining({
        code: "invalid_positive_integer",
        field: "estimated_chars_per_line",
      })
    );
  });

  it("validates target guidance and plain-text item rules", () => {
    expect(
      validateTextCapacity({ ...capacity, max_items: 3, target_items: 4 }, "multi_item")
    ).toContainEqual(expect.objectContaining({ code: "target_exceeds_max" }));
    expect(
      validateTextCapacity({ ...capacity, min_items: 2, target_items: 1 }, "multi_item")
    ).toContainEqual(expect.objectContaining({ code: "target_below_min" }));
    expect(
      validateTextCapacity({ ...capacity, min_items: 1, max_items: 1 }, "plain")
    ).toEqual([]);
    expect(
      validateTextCapacity(
        { ...capacity, min_items: 1, max_items: 1, target_items: 1 },
        "plain"
      )
    ).toContainEqual(expect.objectContaining({ code: "plain_forbids_target_items" }));
  });

  it("estimates wrapping by Unicode code points and counts explicit line breaks", () => {
    expect(estimateTextLineUse(["123456", "ab"], 5)).toBe(3);
    expect(estimateTextLineUse(["ab\r\nc\rd"], 5)).toBe(3);
    expect(estimateTextLineUse(["😀😀", ""], 1)).toBe(3);
    expect(() => estimateTextLineUse(["text"], 0)).toThrow(RangeError);
  });
});

describe("validateTextSizingSemantics (SDK text capacity adapter)", () => {
  const base = {
    efficio_component_type: "text",
    efficio_text_format: "bullets",
    efficio_max_lines: "4",
    efficio_estimated_chars_per_line: "20",
    efficio_min_items: "1",
    efficio_max_items: "4",
  };

  it("passes a valid capacity and maps shared findings to component tags", () => {
    expect(validateTextSizingSemantics(base)).toEqual([]);
    expect(validateTextSizingSemantics({ ...base, efficio_max_items: "5" })).toEqual([
      expect.objectContaining({
        code: "items_exceed_line_capacity",
        tag: "efficio_max_items",
      }),
    ]);
    expect(
      validateTextSizingSemantics({ ...base, efficio_max_items: "3", efficio_target_items: "4" })
    ).toEqual([
      expect.objectContaining({ code: "target_exceeds_max", tag: "efficio_target_items" }),
    ]);
  });

  it("requires plain text to use one item without target guidance", () => {
    const issues = validateTextSizingSemantics({
      ...base,
      efficio_text_format: "plain",
      efficio_max_items: "3",
      efficio_target_items: "1",
    });
    expect(issues).toEqual([
      expect.objectContaining({ code: "plain_requires_single_item", tag: "efficio_max_items" }),
      expect.objectContaining({ code: "plain_forbids_target_items", tag: "efficio_target_items" }),
    ]);
  });

  it("leaves malformed or incomplete tag values to structural validation", () => {
    expect(
      validateTextSizingSemantics({ ...base, efficio_estimated_chars_per_line: "invalid" })
    ).toEqual([]);
    expect(validateTextSizingSemantics({ efficio_max_lines: "4" })).toEqual([]);
  });
});

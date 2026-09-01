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
  getRenderBehaviorValues,
  getSlideTagContract,
  getSlideTagDefaults,
  getTagEnumValues,
  hasComponentType,
  listComponentCompatibilityTagSchemas,
  listComponentTypes,
  validateTableConfigSemantics,
  validateTextSizingSemantics,
  DECK_TEMPLATE_ID_TAG,
  DECK_INITIALIZED_TAG,
  SLIDE_ID_TAG,
  SLIDE_PLACEMENTS,
  SLIDE_PURPOSE_MAX_LENGTH,
} from "../ts/editor";

const EXPECTED_TYPES = ["category_chart", "table", "text"];

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
    // Sizing tags carry no static default; they are filled by auto sizing or manually.
    expect(defaults.efficio_max_chars).toBeUndefined();
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

  it("derives common tags, all known tags, and render behavior values", () => {
    const common = getCommonComponentTags();
    expect(common.has("efficio_component_type")).toBe(true);
    expect(common.has("efficio_render_behavior")).toBe(true);
    const all = getAllKnownComponentTags();
    expect(all.has("efficio_text_format")).toBe(true);
    expect(getRenderBehaviorValues()).toContain("render_by_component_type");
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
    expect(schema.enums.efficio_render_behavior).toContain("preserve");
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
    (schema.enums.efficio_render_behavior as string[])[0] = "mutated";

    expect(getComponentCompatibilityTagSchema("text").component_type).toBe("text");
    expect(getComponentCompatibilityTagSchema("text").types.efficio_component_type).not.toBe(
      "mutated"
    );
    expect(getComponentCompatibilityTagSchema("text").required_tags[0]).not.toBe("mutated");
    expect(getComponentCompatibilityTagSchema("text").enums.efficio_render_behavior[0]).not.toBe(
      "mutated"
    );

    const schemas = getCompatibilityTagSchemaMap();
    schemas.text.component_type = "mutated again";
    expect(getCompatibilityTagSchemaMap().text.component_type).toBe("text");
  });
});

describe("editor SDK slide surface", () => {
  it("re-exports slide tag constants and enums", () => {
    expect(SLIDE_ID_TAG).toBe("efficio_slide_id");
    expect(SLIDE_PLACEMENTS).toContain("body");
    expect(typeof SLIDE_PURPOSE_MAX_LENGTH).toBe("number");
  });

  it("exposes slide defaults as a copy", () => {
    const defaults = getSlideTagDefaults();
    expect(defaults).toBeTypeOf("object");
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
          { row: 0, col: 0, text_format: "bullets", min_items: 1, max_items: 3, target_items: 2 },
        ])
      )
    ).toEqual([]);
  });

  it("flags min>max, target out of bounds, and plain single-item violations", () => {
    expect(
      validateTableConfigSemantics(
        cfg([{ row: 0, col: 0, text_format: "bullets", min_items: 4, max_items: 2 }])
      ).some((i) => i.code === "min_exceeds_max")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([{ row: 0, col: 0, text_format: "bullets", max_items: 2, target_items: 5 }])
      ).some((i) => i.code === "target_exceeds_max")
    ).toBe(true);
    expect(
      validateTableConfigSemantics(
        cfg([{ row: 0, col: 0, text_format: "plain", max_items: 3 }])
      ).some((i) => i.code === "plain_requires_single_item")
    ).toBe(true);
    // A cell with no text_format defaults to plain, so target_items is invalid.
    expect(
      validateTableConfigSemantics(cfg([{ row: 0, col: 0, target_items: 2 }])).some(
        (i) => i.code === "plain_forbids_target_items"
      )
    ).toBe(true);
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

describe("validateTextSizingSemantics (SDK cross-field text rule)", () => {
  const base = { efficio_component_type: "text", efficio_max_chars: "30" };

  it("passes when the optional target_chars is absent", () => {
    expect(validateTextSizingSemantics(base)).toEqual([]);
  });

  it("passes when target_chars <= max_chars", () => {
    expect(validateTextSizingSemantics({ ...base, efficio_target_chars: "20" })).toEqual([]);
    expect(validateTextSizingSemantics({ ...base, efficio_target_chars: "30" })).toEqual([]);
  });

  it("flags target_chars > max_chars on efficio_target_chars", () => {
    const issues = validateTextSizingSemantics({ ...base, efficio_target_chars: "45" });
    expect(issues).toHaveLength(1);
    expect(issues[0].code).toBe("target_exceeds_max");
    expect(issues[0].tag).toBe("efficio_target_chars");
  });

  it("skips the comparison when either value is not a positive integer", () => {
    expect(
      validateTextSizingSemantics({ efficio_max_chars: "oops", efficio_target_chars: "45" })
    ).toEqual([]);
    expect(
      validateTextSizingSemantics({ efficio_max_chars: "30", efficio_target_chars: "0" })
    ).toEqual([]);
  });

  it("flags min_items > max_items and min_chars_per_item > max_chars_per_item", () => {
    const items = validateTextSizingSemantics({ efficio_min_items: "4", efficio_max_items: "2" });
    expect(items).toEqual([
      expect.objectContaining({ code: "min_exceeds_max", tag: "efficio_min_items" }),
    ]);
    const perItem = validateTextSizingSemantics({
      efficio_min_chars_per_item: "40",
      efficio_max_chars_per_item: "20",
    });
    expect(perItem).toEqual([
      expect.objectContaining({ code: "min_exceeds_max", tag: "efficio_min_chars_per_item" }),
    ]);
  });

  it("bounds target_chars_per_item within [min, max] per item", () => {
    expect(
      validateTextSizingSemantics({
        efficio_max_chars_per_item: "20",
        efficio_target_chars_per_item: "45",
      })
    ).toEqual([
      expect.objectContaining({ code: "target_exceeds_max", tag: "efficio_target_chars_per_item" }),
    ]);
    expect(
      validateTextSizingSemantics({
        efficio_min_chars_per_item: "10",
        efficio_target_chars_per_item: "5",
      })
    ).toEqual([
      expect.objectContaining({ code: "target_below_min", tag: "efficio_target_chars_per_item" }),
    ]);
  });

  it("requires plain text to be exactly one item", () => {
    const issues = validateTextSizingSemantics({
      efficio_text_format: "plain",
      efficio_min_items: "1",
      efficio_max_items: "3",
    });
    expect(issues).toEqual([
      expect.objectContaining({ code: "plain_requires_single_item", tag: "efficio_max_items" }),
    ]);
  });

  it("accepts a preferred item count within [min_items, max_items] for a list format", () => {
    expect(
      validateTextSizingSemantics({
        efficio_text_format: "bullets",
        efficio_min_items: "1",
        efficio_target_items: "3",
        efficio_max_items: "5",
      })
    ).toEqual([]);
  });

  it("flags target_items outside its [min_items, max_items] bounds", () => {
    expect(
      validateTextSizingSemantics({
        efficio_min_items: "1",
        efficio_max_items: "2",
        efficio_target_items: "5",
      })
    ).toEqual([
      expect.objectContaining({ code: "target_exceeds_max", tag: "efficio_target_items" }),
    ]);
    expect(
      validateTextSizingSemantics({
        efficio_min_items: "3",
        efficio_max_items: "5",
        efficio_target_items: "1",
      })
    ).toEqual([
      expect.objectContaining({ code: "target_below_min", tag: "efficio_target_items" }),
    ]);
  });

  it("rejects a preferred item count for plain text (always one item)", () => {
    expect(
      validateTextSizingSemantics({
        efficio_text_format: "plain",
        efficio_min_items: "1",
        efficio_max_items: "1",
        efficio_target_items: "1",
      })
    ).toEqual([
      expect.objectContaining({
        code: "plain_forbids_target_items",
        tag: "efficio_target_items",
      }),
    ]);
  });
});

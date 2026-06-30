import { describe, expect, it } from "vitest";

import { componentMetadata } from "../generated/ts/components/componentMetadata";
import {
  getAllKnownComponentTags,
  getCommonComponentTags,
  getComponentCompatibilityTagSchema,
  getComponentMetadata,
  getComponentTagContract,
  getComponentTagDefaults,
  getRenderBehaviorValues,
  getSlideTagDefaults,
  getTagEnumValues,
  hasComponentType,
  listComponentCompatibilityTagSchemas,
  listComponentTypes,
  SLIDE_ID_TAG,
  SLIDE_PLACEMENTS,
  SLIDE_PURPOSE_MAX_LENGTH,
} from "../ts/editor";

const EXPECTED_TYPES = ["approval_block", "grouped_checklist_table", "text"];

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
    expect(defaults.efficio_max_chars).toBe("30");
  });

  it("returns a defensive copy of defaults", () => {
    const defaults = getComponentTagDefaults("text");
    defaults.efficio_sizing_mode = "manual";
    expect(getComponentTagDefaults("text").efficio_sizing_mode).toBe("auto");
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
});

import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { categoryChartDefaults } from "../generated/ts/components/categoryChartDefaults";
import { tableDefaults } from "../generated/ts/components/tableDefaults";
import { textDefaults } from "../generated/ts/components/textDefaults";
import { slideDefaults } from "../generated/ts/presentation/slideDefaults";
import { validateComponentDefaults, type JsonObject } from "../scripts/contractLib";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const componentsDir = path.join(pkgRoot, "contracts", "components");

const COMPONENTS = ["category_chart", "table", "text"];

function readJson(filePath: string): JsonObject {
  return JSON.parse(readFileSync(filePath, "utf8")) as JsonObject;
}

function tagSchemaFor(component: string): JsonObject {
  return readJson(path.join(pkgRoot, "generated", "schemas", "components", `${component.replace(/_/g, "-")}.json`));
}

function defaultsJsonFor(component: string): JsonObject {
  return readJson(path.join(componentsDir, component, "tags.defaults.json"));
}

const commonEffective = {
  efficio_render_behavior: "render_by_component_type",
};

describe.each(COMPONENTS)("tags.defaults.json for %s", (component) => {
  const defaults = defaultsJsonFor(component);

  it("is a flat object of string values", () => {
    for (const value of Object.values(defaults)) {
      expect(typeof value).toBe("string");
    }
  });

  it("does not set efficio_component_id (editor-generated)", () => {
    expect(defaults).not.toHaveProperty("efficio_component_id");
  });

  it("keys are known tags and values satisfy the tag contract rules", () => {
    expect(() =>
      validateComponentDefaults(defaults, tagSchemaFor(component), `contracts/components/${component}/tags.defaults.json`),
    ).not.toThrow();
  });
});

describe("generated defaults preserve effective behavior", () => {
  it("text", () => {
    // Text sizing tags have no static defaults: they are authored, estimated by
    // the editor, or entered manually — never defaulted to "30".
    expect(textDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "text",
      efficio_text_format: "plain",
      efficio_sizing_mode: "auto",
    });
    // The optional preferred item count has no static default (estimated/manual only).
    expect(textDefaults).not.toHaveProperty("efficio_target_items");
  });

  it("table (object-tag default is a JSON string)", () => {
    expect(tableDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "table",
      efficio_table_config: '{"cells":[]}',
    });
  });

  it("category_chart (no default config; the author must supply one)", () => {
    expect(categoryChartDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "category_chart",
    });
    expect(categoryChartDefaults).not.toHaveProperty("efficio_category_chart_config");
  });

  it("none include efficio_component_id", () => {
    for (const defaults of [textDefaults, tableDefaults, categoryChartDefaults]) {
      expect(defaults).not.toHaveProperty("efficio_component_id");
    }
  });

  it("slide defaults are generated from presentation defaults", () => {
    expect(slideDefaults).toEqual({
      efficio_slide_placement: "body",
      efficio_slide_inclusion_policy: "when_relevant",
    });
  });
});

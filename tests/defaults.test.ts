import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { approvalBlockDefaults } from "../generated/ts/components/approvalBlockDefaults";
import { groupedChecklistTableDefaults } from "../generated/ts/components/groupedChecklistTableDefaults";
import { textDefaults } from "../generated/ts/components/textDefaults";
import { slideDefaults } from "../generated/ts/presentation/slideDefaults";
import { validateComponentDefaults, type JsonObject } from "../scripts/contractLib";

const here = path.dirname(fileURLToPath(import.meta.url));
const pkgRoot = path.resolve(here, "..");
const componentsDir = path.join(pkgRoot, "contracts", "components");

const COMPONENTS = ["approval_block", "grouped_checklist_table", "table", "text"];

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
  efficio_manually_reviewed: "false",
  efficio_requires_manual_review: "true",
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
    expect(textDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "text",
      efficio_text_format: "plain",
      efficio_sizing_mode: "auto",
      efficio_max_chars: "30",
      efficio_max_lines: "30",
      efficio_max_chars_per_line: "30",
    });
  });

  it("grouped_checklist_table (no efficio_groups default)", () => {
    expect(groupedChecklistTableDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "grouped_checklist_table",
    });
    expect(groupedChecklistTableDefaults).not.toHaveProperty("efficio_groups");
  });

  it("approval_block (object-tag defaults are JSON strings)", () => {
    expect(approvalBlockDefaults).toEqual({
      ...commonEffective,
      efficio_component_type: "approval_block",
      efficio_approval_block_layout: "table_2row_person_role",
      efficio_label_cell: '{"row":0,"col":0}',
      efficio_name_cell: '{"row":0,"col":1}',
      efficio_role_cell: '{"row":1,"col":1}',
      efficio_default_subtype: "approved",
      efficio_missing_content_behavior: "leave_as_is",
      efficio_subtype_policy: "ai_selectable",
      efficio_approval_block_subtypes:
        '{"recommended":{"label":"Recommended"},"endorsed":{"label":"Endorsed"},"approved":{"label":"Approved"}}',
    });
  });

  it("none include efficio_component_id", () => {
    for (const defaults of [textDefaults, groupedChecklistTableDefaults, approvalBlockDefaults]) {
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

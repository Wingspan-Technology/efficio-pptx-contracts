import { describe, expect, it } from "vitest";

import {
  assertEfficioTagNames,
  assertTextContentShape,
  assertValidJsonSchema,
  isValidEfficioTagName,
  publicTagAlias,
  validateComponentDefaults,
  validateTagEntityContract,
  type JsonObject,
} from "../scripts/contractLib";
import { legacyEnum, legacyType, mergeTagSchema } from "../scripts/compatibilityTagSchema";

const COMMON_LABELS = [
  "contracts/shared/content-mode-tags.contract.json",
  "contracts/shared/component-base-tags.contract.json",
];

const validCommon: JsonObject = {
  description: "common",
  tags: {
    efficio_content_mode: { type: "string", required: true, enum: ["a", "b"] },
    efficio_component_id: { type: "string", required: true, min_length: 1 },
    efficio_component_type: { type: "string", required: true },
    efficio_flag: { type: "boolean", required: false },
  },
};

function validComponent(): JsonObject {
  return {
    component_type: "text",
    description: "text",
    tags: {
      efficio_component_type: { type: "string", required: true, enum: ["text"] },
      efficio_text_format: { type: "string", required: true, enum: ["plain", "rich"] },
      efficio_max_chars: { type: "integer", required: false, minimum: 1 },
    },
  };
}

describe("validateTagEntityContract", () => {
  it("accepts a valid common contract", () => {
    expect(() => validateTagEntityContract(validCommon, "common", {})).not.toThrow();
  });

  it("accepts a valid component contract", () => {
    expect(() =>
      validateTagEntityContract(validComponent(), "text", { componentType: "text" }),
    ).not.toThrow();
  });

  it("rejects a missing tags object", () => {
    expect(() => validateTagEntityContract({ description: "x" }, "c", {})).toThrow(/tags must be a JSON object/);
  });

  it("rejects an empty tags object", () => {
    expect(() => validateTagEntityContract({ tags: {} }, "c", {})).toThrow(/at least one tag/);
  });

  it("rejects unknown top-level fields", () => {
    expect(() =>
      validateTagEntityContract({ tags: validCommon.tags, surprise: 1 } as JsonObject, "c", {}),
    ).toThrow(/not an allowed contract field/);
  });

  it("rejects the old conditional_required_tags top-level field", () => {
    const bad = validComponent();
    bad.conditional_required_tags = [
      { when: { tag: "efficio_text_format", equals: "rich" }, required_tags: ["efficio_max_chars"] },
    ];
    expect(() => validateTagEntityContract(bad, "text", { componentType: "text" })).toThrow(
      /conditional_required_tags is not an allowed contract field/,
    );
  });

  it("rejects an invalid tag type", () => {
    const bad: JsonObject = { tags: { t: { type: "number", required: true } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/type must be one of/);
  });

  it("rejects a missing required flag", () => {
    const bad: JsonObject = { tags: { t: { type: "string" } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/required must be a boolean/);
  });

  it("rejects enum values whose native type mismatches", () => {
    const bad: JsonObject = { tags: { t: { type: "string", required: true, enum: [1] } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/does not match declared type/);
  });

  it("rejects constraints not allowed for the type", () => {
    const bad: JsonObject = { tags: { t: { type: "string", required: true, minimum: 1 } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/not allowed for type/);
  });

  it("rejects ai without purpose", () => {
    const bad: JsonObject = { tags: { t: { type: "string", required: true, ai: {} } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/ai.purpose is required/);
  });

  it("rejects enum_descriptions without enum", () => {
    const bad: JsonObject = {
      tags: { t: { type: "string", required: true, ai: { purpose: "p", enum_descriptions: { x: "y" } } } },
    };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/enum_descriptions requires/);
  });

  it("rejects enum_descriptions keys that do not match enum", () => {
    const bad: JsonObject = {
      tags: {
        t: { type: "string", required: true, enum: ["a"], ai: { purpose: "p", enum_descriptions: { b: "y" } } },
      },
    };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/keys must exactly match enum values/);
  });

  it("rejects an AI-visible enum tag without enum_descriptions", () => {
    const bad: JsonObject = {
      tags: { t: { type: "string", required: true, enum: ["a", "b"], ai: { purpose: "p" } } },
    };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/enum_descriptions is required/);
  });

  it("rejects an AI-visible enum tag missing a description for one enum value", () => {
    const bad: JsonObject = {
      tags: {
        t: {
          type: "string",
          required: true,
          enum: ["a", "b"],
          ai: { purpose: "p", enum_descriptions: { a: "only a" } },
        },
      },
    };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/keys must exactly match enum values/);
  });

  it("rejects an AI-visible enum tag with an extra (unknown) enum description", () => {
    const bad: JsonObject = {
      tags: {
        t: {
          type: "string",
          required: true,
          enum: ["a"],
          ai: { purpose: "p", enum_descriptions: { a: "a", b: "extra" } },
        },
      },
    };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/keys must exactly match enum values/);
  });

  it("rejects an enum description that is empty or not a string", () => {
    const empty: JsonObject = {
      tags: {
        t: { type: "string", required: true, enum: ["a"], ai: { purpose: "p", enum_descriptions: { a: "" } } },
      },
    };
    expect(() => validateTagEntityContract(empty, "c", {})).toThrow(/enum_descriptions.a must be a non-empty string/);
    const nonString: JsonObject = {
      tags: {
        t: { type: "string", required: true, enum: ["a"], ai: { purpose: "p", enum_descriptions: { a: 1 } } },
      },
    };
    expect(() => validateTagEntityContract(nonString, "c", {})).toThrow(/enum_descriptions.a must be a non-empty string/);
  });

  it("accepts an AI-visible non-enum tag with only a purpose", () => {
    const ok: JsonObject = {
      tags: { t: { type: "integer", required: true, minimum: 1, ai: { purpose: "a safe numeric limit" } } },
    };
    expect(() => validateTagEntityContract(ok, "c", {})).not.toThrow();
  });

  it("accepts an AI-visible enum tag with complete non-empty descriptions", () => {
    const ok: JsonObject = {
      tags: {
        t: {
          type: "string",
          required: true,
          enum: ["a", "b"],
          ai: { purpose: "p", enum_descriptions: { a: "the a case", b: "the b case" } },
        },
      },
    };
    expect(() => validateTagEntityContract(ok, "c", {})).not.toThrow();
  });

  it("rejects a component_type enum that does not equal [component_type]", () => {
    const bad = validComponent();
    (bad.tags as JsonObject).efficio_component_type = { type: "string", required: true, enum: ["wrong"] };
    expect(() => validateTagEntityContract(bad, "text", { componentType: "text" })).toThrow(
      /efficio_component_type.enum must be exactly/,
    );
  });

  it("rejects a component_type top-level field that does not match the folder", () => {
    const bad = validComponent();
    bad.component_type = "other_type";
    expect(() => validateTagEntityContract(bad, "text", { componentType: "text" })).toThrow(
      /component_type must be "text"/,
    );
  });
});

describe("validateTagEntityContract — presentation slide", () => {
  function validSlide(): JsonObject {
    return {
      contract_type: "slide_tags",
      description: "slide tags",
      tags: {
        efficio_slide_id: { type: "string", required: true, pattern: "^slide_\\d{3}$" },
        efficio_slide_placement: { type: "string", required: true, enum: ["fixed_start", "body", "fixed_end"] },
        efficio_slide_group_order: { type: "integer", required: false, minimum: 1 },
        efficio_slide_purpose: { type: "string", required: false, max_length: 500 },
      },
    };
  }

  it("accepts a valid slide tag contract", () => {
    expect(() => validateTagEntityContract(validSlide(), "slide", { slideContractType: "slide_tags" })).not.toThrow();
  });

  it("rejects a missing/incorrect contract_type", () => {
    const bad = validSlide();
    delete bad.contract_type;
    expect(() => validateTagEntityContract(bad, "slide", { slideContractType: "slide_tags" })).toThrow(
      /contract_type must be "slide_tags"/,
    );
  });

  it("rejects component_type on a slide contract", () => {
    const bad = { ...validSlide(), component_type: "text" };
    expect(() => validateTagEntityContract(bad, "slide", { slideContractType: "slide_tags" })).toThrow(
      /component_type is not an allowed contract field/,
    );
  });

  it("rejects old compatibility fields (required_tags/enums/max_lengths)", () => {
    for (const field of ["required_tags", "optional_tags", "enums", "types", "max_lengths", "conditional_required_tags"]) {
      const bad = { ...validSlide(), [field]: {} } as JsonObject;
      expect(() => validateTagEntityContract(bad, "slide", { slideContractType: "slide_tags" })).toThrow(
        new RegExp(`${field} is not an allowed contract field`),
      );
    }
  });
});

describe("object/array (structured) tag entities", () => {
  const schema: JsonObject = { type: "object", properties: {} };

  it("accepts an object tag with a valid embedded schema", () => {
    const ok: JsonObject = { tags: { efficio_config: { type: "object", required: true, schema } } };
    expect(() => validateTagEntityContract(ok, "c", {})).not.toThrow();
  });

  it("accepts an array tag with a valid embedded schema", () => {
    const ok: JsonObject = { tags: { t: { type: "array", required: true, schema: { type: "array" } } } };
    expect(() => validateTagEntityContract(ok, "c", {})).not.toThrow();
  });

  it("rejects an object/array tag without a schema", () => {
    for (const type of ["object", "array"]) {
      const bad: JsonObject = { tags: { t: { type, required: true } } };
      expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/schema is required for type/);
    }
  });

  it("rejects a scalar tag that declares a schema", () => {
    const bad: JsonObject = { tags: { t: { type: "string", required: true, schema } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/schema is only allowed for object\/array/);
  });

  it("rejects enum on an object/array tag", () => {
    const bad: JsonObject = { tags: { t: { type: "object", required: true, schema, enum: ["x"] } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/enum is not allowed for type/);
  });

  it("rejects an invalid embedded JSON Schema", () => {
    const bad: JsonObject = { tags: { t: { type: "object", required: true, schema: { type: 123 } } } };
    expect(() => validateTagEntityContract(bad, "c", {})).toThrow(/not a valid JSON Schema/);
  });
});

describe("legacy compatibility mapping", () => {
  it("maps entity types to legacy logical types", () => {
    expect(legacyType({ type: "string", enum: ["a"] }, "x")).toBe("enum");
    expect(legacyType({ type: "string", min_length: 1 }, "x")).toBe("non_empty_string");
    expect(legacyType({ type: "string" }, "x")).toBe("string");
    expect(legacyType({ type: "integer", minimum: 1 }, "x")).toBe("positive_integer_string");
    expect(legacyType({ type: "boolean" }, "x")).toBe("enum_boolean_string");
    expect(legacyType({ type: "object" }, "x")).toBe("json_object");
    expect(legacyType({ type: "array" }, "x")).toBe("json_array");
  });

  it("fails for integers that cannot map to the current editor type", () => {
    expect(() => legacyType({ type: "integer" }, "x")).toThrow(/minimum >= 1/);
  });

  it("stringifies booleans and enums", () => {
    expect(legacyEnum({ type: "boolean" })).toEqual(["true", "false"]);
    expect(legacyEnum({ type: "string", enum: ["a", "b"] })).toEqual(["a", "b"]);
    expect(legacyEnum({ type: "string" })).toBeUndefined();
    expect(legacyEnum({ type: "object", schema: {} })).toBeUndefined();
  });
});

describe("mergeTagSchema", () => {
  const merged = mergeTagSchema(validCommon, validComponent(), "contracts/components/text/tags.contract.json", COMMON_LABELS);

  it("composes common + component required/optional tags", () => {
    expect(merged.required_tags).toEqual([
      "efficio_content_mode",
      "efficio_component_id",
      "efficio_component_type",
      "efficio_text_format",
    ]);
    expect(merged.optional_tags).toEqual(["efficio_flag", "efficio_max_chars"]);
  });

  it("derives enums with component_type landing in the component section", () => {
    expect(merged.enums).toEqual({
      efficio_content_mode: ["a", "b"],
      efficio_flag: ["true", "false"],
      efficio_component_type: ["text"],
      efficio_text_format: ["plain", "rich"],
    });
  });

  it("derives legacy types with component_type read as enum from the common section", () => {
    expect(merged.types).toEqual({
      efficio_content_mode: "enum",
      efficio_component_id: "non_empty_string",
      efficio_component_type: "enum",
      efficio_flag: "enum_boolean_string",
      efficio_text_format: "enum",
      efficio_max_chars: "positive_integer_string",
    });
  });

  it("rejects a component redefining a non-component_type common tag", () => {
    const clashing = validComponent();
    (clashing.tags as JsonObject).efficio_flag = { type: "boolean", required: false };
    expect(() => mergeTagSchema(validCommon, clashing, "contracts/components/text/tags.contract.json", COMMON_LABELS)).toThrow(
      /conflicts with common.tags.efficio_flag/,
    );
  });

  it("emits json_schemas for object/array tags (empty when there are none)", () => {
    expect(merged.json_schemas).toEqual({});

    const groupsSchema: JsonObject = { type: "object", properties: { groups: { type: "array" } } };
    const withObject = validComponent();
    (withObject.tags as JsonObject).efficio_config = { type: "object", required: true, schema: groupsSchema };
    const result = mergeTagSchema(validCommon, withObject, "contracts/components/x/tags.contract.json", COMMON_LABELS);

    expect((result.types as JsonObject).efficio_config).toBe("json_object");
    expect(result.json_schemas).toEqual({ efficio_config: groupsSchema });
  });
});

describe("content contract validation", () => {
  const validText: JsonObject = {
    $schema: "https://json-schema.org/draft/2020-12/schema",
    type: "object",
    additionalProperties: false,
    required: ["items"],
    properties: { items: { type: "array", minItems: 1, items: { type: "string", minLength: 1 } } },
  };

  it("accepts a valid JSON Schema document", () => {
    expect(() => assertValidJsonSchema(validText, "x")).not.toThrow();
  });

  it("rejects a malformed JSON Schema document", () => {
    expect(() => assertValidJsonSchema({ type: 123 } as unknown as JsonObject, "x")).toThrow(
      /not a valid JSON Schema/,
    );
  });

  it("accepts the text target shape", () => {
    expect(() => assertTextContentShape(validText, "x")).not.toThrow();
  });

  it("rejects a text shape missing items", () => {
    const bad: JsonObject = { ...validText, required: ["other"], properties: { other: { type: "string" } } };
    expect(() => assertTextContentShape(bad, "x")).toThrow(/required must include "items"/);
  });

  it("rejects text items that are not constrained strings", () => {
    const bad: JsonObject = {
      ...validText,
      properties: { items: { type: "array", minItems: 1, items: { type: "number" } } },
    };
    expect(() => assertTextContentShape(bad, "x")).toThrow(/items.items.type must be "string"/);
  });
});

describe("validateComponentDefaults", () => {
  const tagSchema = mergeTagSchema(validCommon, validComponent(), "contracts/components/text/tags.contract.json", COMMON_LABELS);

  it("accepts valid defaults", () => {
    expect(() =>
      validateComponentDefaults({ efficio_text_format: "plain" }, tagSchema, "d"),
    ).not.toThrow();
  });

  it("rejects efficio_component_id", () => {
    expect(() => validateComponentDefaults({ efficio_component_id: "x" }, tagSchema, "d")).toThrow(
      /must not be set in defaults/,
    );
  });

  it("rejects unknown tags", () => {
    expect(() => validateComponentDefaults({ efficio_unknown: "x" }, tagSchema, "d")).toThrow(
      /is not a known tag/,
    );
  });

  it("rejects values outside the tag enum", () => {
    expect(() => validateComponentDefaults({ efficio_text_format: "nope" }, tagSchema, "d")).toThrow(
      /must be one of/,
    );
  });

  it("rejects non-positive-integer strings for integer tags", () => {
    expect(() => validateComponentDefaults({ efficio_max_chars: "0" }, tagSchema, "d")).toThrow(
      /positive integer string/,
    );
  });

  it("rejects non-string values", () => {
    expect(() =>
      validateComponentDefaults({ efficio_text_format: 5 } as unknown as JsonObject, tagSchema, "d"),
    ).toThrow(/must be a string value/);
  });
});

describe("validateComponentDefaults — object/array (structured) defaults", () => {
  function structuredTagSchema(): JsonObject {
    const component = validComponent();
    (component.tags as JsonObject).efficio_config = {
      type: "object",
      required: false,
      schema: {
        type: "object",
        additionalProperties: false,
        required: ["count"],
        properties: { count: { type: "integer", minimum: 0 } },
      },
    };
    return mergeTagSchema(validCommon, component, "contracts/components/x/tags.contract.json", COMMON_LABELS);
  }

  const tagSchema = structuredTagSchema();

  it("accepts a structured default that parses and matches its embedded schema", () => {
    expect(() => validateComponentDefaults({ efficio_config: '{"count":2}' }, tagSchema, "d")).not.toThrow();
  });

  it("rejects a structured default that is not valid JSON text", () => {
    expect(() => validateComponentDefaults({ efficio_config: "{not json" }, tagSchema, "d")).toThrow(
      /must be valid JSON text/,
    );
  });

  it("rejects a structured default that parses but violates the embedded schema", () => {
    expect(() => validateComponentDefaults({ efficio_config: '{"count":-1}' }, tagSchema, "d")).toThrow(
      /does not match its tag schema/,
    );
    expect(() => validateComponentDefaults({ efficio_config: '{"other":1}' }, tagSchema, "d")).toThrow(
      /does not match its tag schema/,
    );
  });
});

describe("Efficio tag-name convention", () => {
  it("accepts efficio_ snake_case names", () => {
    for (const name of ["efficio_text_format", "efficio_max_chars_per_line", "efficio_slide_id", "efficio_config"]) {
      expect(isValidEfficioTagName(name)).toBe(true);
    }
  });

  it("rejects names that break the convention", () => {
    for (const name of ["text_format", "Efficio_text", "efficio_Text", "efficio__text", "efficio_text_", "efficio-text"]) {
      expect(isValidEfficioTagName(name)).toBe(false);
    }
  });

  it("assertEfficioTagNames accepts a contract whose tags all conform", () => {
    expect(() => assertEfficioTagNames(validComponent(), "c")).not.toThrow();
  });

  it("assertEfficioTagNames rejects a non-conforming tag name", () => {
    const bad = validComponent();
    (bad.tags as JsonObject).BadName = { type: "string", required: false };
    expect(() => assertEfficioTagNames(bad, "c")).toThrow(/BadName is not a valid Efficio tag name/);
  });

  it("publicTagAlias strips the efficio_ prefix", () => {
    expect(publicTagAlias("efficio_text_format")).toBe("text_format");
    expect(publicTagAlias("efficio_max_chars_per_line")).toBe("max_chars_per_line");
    expect(publicTagAlias("efficio_config")).toBe("config");
  });

  it("publicTagAlias rejects names outside the tag-name convention", () => {
    for (const name of ["text_format", "efficio_Text", "efficio__x", ""]) {
      expect(() => publicTagAlias(name)).toThrow(/public AI alias/);
    }
  });
});

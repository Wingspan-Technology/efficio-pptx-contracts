import { describe, expect, it } from "vitest";

import { validateStoredTagValue } from "../scripts/storedTagValueContractLib";

const label = "migration target";

describe("validateStoredTagValue", () => {
  it("enforces string length, pattern, and enum constraints", () => {
    const definition = {
      type: "string",
      min_length: 3,
      max_length: 8,
      pattern: "[a-z]+",
      enum: ["valid"],
    };
    expect(() => validateStoredTagValue("efficio_value", "valid", definition, label)).not.toThrow();
    expect(() => validateStoredTagValue("efficio_value", "x", definition, label)).toThrow(/at least 3/);
    expect(() => validateStoredTagValue("efficio_value", "toolonggg", definition, label)).toThrow(/at most 8/);
    expect(() => validateStoredTagValue("efficio_value", "BAD", definition, label)).toThrow(/required pattern/);
    expect(() => validateStoredTagValue("efficio_value", "other", definition, label)).toThrow(/must be one of/);
  });

  it("enforces integer bounds and boolean storage", () => {
    const integer = { type: "integer", minimum: 2, maximum: 4 };
    expect(() => validateStoredTagValue("efficio_count", "3", integer, label)).not.toThrow();
    expect(() => validateStoredTagValue("efficio_count", "1", integer, label)).toThrow(/at least 2/);
    expect(() => validateStoredTagValue("efficio_count", "5", integer, label)).toThrow(/at most 4/);
    expect(() => validateStoredTagValue("efficio_count", "1.0", integer, label)).toThrow(/integer string/);
    expect(() => validateStoredTagValue("efficio_flag", "yes", { type: "boolean" }, label)).toThrow(/"true" or "false"/);
  });

  it("enforces structured tag type and embedded schema", () => {
    const definition = {
      type: "array",
      schema: {
        type: "array",
        minItems: 1,
        items: { type: "string" },
      },
    };
    expect(() => validateStoredTagValue("efficio_items", '["one"]', definition, label)).not.toThrow();
    expect(() => validateStoredTagValue("efficio_items", "{}", definition, label)).toThrow(/JSON array/);
    expect(() => validateStoredTagValue("efficio_items", "[]", definition, label)).toThrow(/tag schema/);
  });
});

import { describe, expect, it } from "vitest";

import {
  CLASSIFICATION_SCHEMES_TAG,
  CLASSIFICATION_SCHEME_ID_TAG,
  ClassificationSchemeContractError,
  parseClassificationSchemes,
  resolveCategoricalFillScheme,
} from "../ts/editor";

function schemes(): Array<Record<string, unknown>> {
  return [
    {
      scheme_id: "selection_state",
      instruction: "Decide whether each option should be selected.",
      palette_mode: "rgb",
      cases: [
        {
          case_id: "selected",
          label: "Selected",
          description: "The option should be highlighted.",
          fill: { value: "17365D" },
        },
        {
          case_id: "unselected",
          label: "Unselected",
          description: "The option should remain inactive.",
          fill: { value: "BFBFBF" },
        },
      ],
    },
  ];
}

describe("classification scheme SDK", () => {
  it("parses authored schemes without changing their wire shape", () => {
    expect(parseClassificationSchemes(JSON.stringify(schemes()))).toEqual([
      {
        scheme_id: "selection_state",
        instruction: "Decide whether each option should be selected.",
        palette_mode: "rgb",
        cases: [
          {
            case_id: "selected",
            label: "Selected",
            description: "The option should be highlighted.",
            fill: { value: "17365D" },
          },
          {
            case_id: "unselected",
            label: "Unselected",
            description: "The option should remain inactive.",
            fill: { value: "BFBFBF" },
          },
        ],
      },
    ]);
  });

  it("resolves one component reference", () => {
    const resolved = resolveCategoricalFillScheme(
      { [CLASSIFICATION_SCHEME_ID_TAG]: "selection_state" },
      { [CLASSIFICATION_SCHEMES_TAG]: JSON.stringify(schemes()) }
    );
    expect(resolved.scheme_id).toBe("selection_state");
  });

  it("rejects invalid JSON, RGB values, duplicate IDs, and unknown references", () => {
    expect(() => parseClassificationSchemes("not-json")).toThrow(
      ClassificationSchemeContractError
    );

    const invalidRgb = schemes();
    const cases = invalidRgb[0].cases as Array<Record<string, unknown>>;
    cases[0].fill = { value: "#17365D" };
    expect(() => parseClassificationSchemes(invalidRgb)).toThrow(
      ClassificationSchemeContractError
    );

    const duplicate = schemes();
    duplicate.push(structuredClone(duplicate[0]));
    expect(() => parseClassificationSchemes(duplicate)).toThrow(/scheme IDs must be unique/);

    expect(() =>
      resolveCategoricalFillScheme(
        { [CLASSIFICATION_SCHEME_ID_TAG]: "unknown_scheme" },
        { [CLASSIFICATION_SCHEMES_TAG]: JSON.stringify(schemes()) }
      )
    ).toThrow(/unknown classification scheme/);
  });

  it("returns an empty registry for an absent or blank deck tag", () => {
    expect(parseClassificationSchemes(undefined)).toEqual([]);
    expect(parseClassificationSchemes("   ")).toEqual([]);
  });

  it("applies text ceilings in Unicode code points", () => {
    const unicode = schemes();
    const cases = unicode[0].cases as Array<Record<string, unknown>>;
    cases[0].label = "🟦".repeat(120);

    expect(parseClassificationSchemes(unicode)[0].cases[0].label).toBe(
      "🟦".repeat(120)
    );
  });
});

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  DECK_SLIDE_ARCHETYPES_TAG,
  SLIDE_ARCHETYPE_IDS_TAG,
  SlideArchetypeContractError,
  isSlideApplicableToArchetype,
  parseSlideArchetypeIds,
  parseSlideArchetypes,
  resolveSlideArchetypeAssignment,
  type SlideArchetype,
} from "../ts/editor";

type RawValue = string | unknown[] | null;
type Tags = Record<string, string>;

type Fixture = {
  registry_cases: { name: string; raw: RawValue; expected: SlideArchetype[] }[];
  invalid_registry_cases: { name: string; raw: RawValue }[];
  assignment_cases: { name: string; raw: RawValue; expected: string[] }[];
  invalid_assignment_cases: { name: string; raw: RawValue }[];
  resolution_cases: {
    name: string;
    deck_tags: Tags;
    slide_tags: Tags;
    expected: SlideArchetype[];
  }[];
  resolution_error_cases: { name: string; deck_tags: Tags; slide_tags: Tags }[];
  applicability_cases: {
    name: string;
    deck_tags: Tags;
    slide_tags: Tags;
    archetype_id: string;
    expected: boolean;
  }[];
  applicability_error_cases: {
    name: string;
    deck_tags: Tags;
    slide_tags: Tags;
    archetype_id: string;
  }[];
};

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  readFileSync(path.join(here, "fixtures", "slide-archetype-cases.json"), "utf8"),
) as Fixture;

// The fixture is shared with tests/test_slide_archetypes.py; `null` stands for an
// absent tag value, which reaches the SDK as `undefined` in TypeScript.
function raw(value: RawValue): string | readonly unknown[] | undefined {
  return value === null ? undefined : value;
}

describe("slide archetype tag constants", () => {
  it("re-exports the generated deck and slide tag names", () => {
    expect(DECK_SLIDE_ARCHETYPES_TAG).toBe("efficio_slide_archetypes");
    expect(SLIDE_ARCHETYPE_IDS_TAG).toBe("efficio_slide_archetype_ids");
  });
});

describe("parseSlideArchetypes", () => {
  for (const testCase of fixture.registry_cases) {
    it(testCase.name, () => {
      expect(parseSlideArchetypes(raw(testCase.raw))).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.invalid_registry_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() => parseSlideArchetypes(raw(testCase.raw))).toThrow(
        SlideArchetypeContractError,
      );
    });
  }

  it("returns a new array the caller may mutate freely", () => {
    const stored = '[{"archetype_id":"pitch_deck","name":"Pitch deck"}]';
    const parsed = parseSlideArchetypes(stored) as SlideArchetype[];
    parsed.push({ archetype_id: "training", name: "Training" });
    expect(parseSlideArchetypes(stored)).toHaveLength(1);
  });
});

describe("parseSlideArchetypeIds", () => {
  for (const testCase of fixture.assignment_cases) {
    it(testCase.name, () => {
      expect(parseSlideArchetypeIds(raw(testCase.raw))).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.invalid_assignment_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() => parseSlideArchetypeIds(raw(testCase.raw))).toThrow(
        SlideArchetypeContractError,
      );
    });
  }
});

describe("resolveSlideArchetypeAssignment", () => {
  for (const testCase of fixture.resolution_cases) {
    it(testCase.name, () => {
      expect(
        resolveSlideArchetypeAssignment(testCase.slide_tags, testCase.deck_tags),
      ).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.resolution_error_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() =>
        resolveSlideArchetypeAssignment(testCase.slide_tags, testCase.deck_tags),
      ).toThrow(SlideArchetypeContractError);
    });
  }
});

describe("isSlideApplicableToArchetype", () => {
  for (const testCase of fixture.applicability_cases) {
    it(testCase.name, () => {
      expect(
        isSlideApplicableToArchetype(
          testCase.slide_tags,
          testCase.deck_tags,
          testCase.archetype_id,
        ),
      ).toBe(testCase.expected);
    });
  }

  for (const testCase of fixture.applicability_error_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() =>
        isSlideApplicableToArchetype(
          testCase.slide_tags,
          testCase.deck_tags,
          testCase.archetype_id,
        ),
      ).toThrow(SlideArchetypeContractError);
    });
  }
});

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  DECK_DATA_TOPICS_TAG,
  SLIDE_DATA_TOPIC_IDS_TAG,
  DataTopicContractError,
  getDeckTagContract,
  getSlideTagContract,
  parseDataTopics,
  parseSlideDataTopicIds,
  resolveSlideDataTopicAssignment,
  type DataTopic,
} from "../ts/editor";

type RawValue = string | unknown[] | null;
type Tags = Record<string, string>;

type Fixture = {
  registry_cases: { name: string; raw: RawValue; expected: DataTopic[] }[];
  invalid_registry_cases: { name: string; raw: RawValue }[];
  assignment_cases: { name: string; raw: RawValue; expected: string[] }[];
  invalid_assignment_cases: { name: string; raw: RawValue }[];
  resolution_cases: {
    name: string;
    deck_tags: Tags;
    slide_tags: Tags;
    expected: DataTopic[];
  }[];
  resolution_error_cases: { name: string; deck_tags: Tags; slide_tags: Tags }[];
};

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  readFileSync(path.join(here, "fixtures", "data-topic-cases.json"), "utf8"),
) as Fixture;

// The fixture is shared with tests/test_data_topics.py; `null` stands for an
// absent tag value, which reaches the SDK as `undefined` in TypeScript.
function raw(value: RawValue): string | readonly unknown[] | undefined {
  return value === null ? undefined : value;
}

describe("data topic tag constants", () => {
  it("re-exports the generated deck and slide tag names", () => {
    expect(DECK_DATA_TOPICS_TAG).toBe("efficio_data_topics");
    expect(SLIDE_DATA_TOPIC_IDS_TAG).toBe("efficio_slide_data_topic_ids");
  });

  it("reads optional, non-AI tag definitions from the generated contracts", () => {
    const registry = getDeckTagContract().tags.efficio_data_topics;
    expect(registry.type).toBe("array");
    expect(registry.required).toBe(false);
    expect(registry).not.toHaveProperty("ai");
    const assignment = getSlideTagContract().tags.efficio_slide_data_topic_ids;
    expect(assignment.required).toBe(false);
    expect(assignment.schema.minItems).toBe(1);
    expect(assignment.schema.uniqueItems).toBe(true);
    expect(assignment).not.toHaveProperty("ai");
  });
});

describe("parseDataTopics", () => {
  for (const testCase of fixture.registry_cases) {
    it(testCase.name, () => {
      expect(parseDataTopics(raw(testCase.raw))).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.invalid_registry_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() => parseDataTopics(raw(testCase.raw))).toThrow(DataTopicContractError);
    });
  }

  it("returns a new array the caller may mutate freely", () => {
    const stored = '[{"topic_id":"topic_revenue","name":"Revenue"}]';
    const parsed = parseDataTopics(stored) as DataTopic[];
    parsed.push({ topic_id: "topic_headcount", name: "Headcount" });
    expect(parseDataTopics(stored)).toHaveLength(1);
  });
});

describe("parseSlideDataTopicIds", () => {
  for (const testCase of fixture.assignment_cases) {
    it(testCase.name, () => {
      expect(parseSlideDataTopicIds(raw(testCase.raw))).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.invalid_assignment_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() => parseSlideDataTopicIds(raw(testCase.raw))).toThrow(
        DataTopicContractError,
      );
    });
  }
});

describe("resolveSlideDataTopicAssignment", () => {
  for (const testCase of fixture.resolution_cases) {
    it(testCase.name, () => {
      expect(
        resolveSlideDataTopicAssignment(testCase.slide_tags, testCase.deck_tags),
      ).toEqual(testCase.expected);
    });
  }

  for (const testCase of fixture.resolution_error_cases) {
    it(`rejects ${testCase.name}`, () => {
      expect(() =>
        resolveSlideDataTopicAssignment(testCase.slide_tags, testCase.deck_tags),
      ).toThrow(DataTopicContractError);
    });
  }
});

// Typed access to the optional template-authored, name-only data-topic metadata.
//
// The deck registry (`efficio_data_topics`) declares the data topics a template
// talks about, each as an exact `{topic_id, name}` pair. A slide may name the
// topics it relates to through `efficio_slide_data_topic_ids`; a slide without
// that tag simply has no assignment. Neither tag carries an `ai` block: data
// topics are advisory labels only, so they never bind data, filter or select
// slides, constrain generated content schemas, or reach the generated
// slide-selection instructions.
//
// Explicit .js specifiers preserve native ESM behavior after TypeScript compilation.

import {
  deckTagSchema,
  DECK_DATA_TOPICS_TAG,
} from "../../generated/ts/presentation/deckTagSchema.js";
import {
  slideTagSchema,
  SLIDE_DATA_TOPIC_IDS_TAG,
} from "../../generated/ts/presentation/slideTagSchema.js";

export { DECK_DATA_TOPICS_TAG, SLIDE_DATA_TOPIC_IDS_TAG };

/** One authored data-topic definition in the exact deck-tag wire shape. */
export type DataTopic = {
  topic_id: string;
  name: string;
};

export class DataTopicContractError extends Error {
  override readonly name = "DataTopicContractError";
}

// Every constraint is read from the generated contracts; no topic ID, name, or
// limit is hardcoded here.
const topicProperties = deckTagSchema.tags.efficio_data_topics.schema.items.properties;
const assignmentSchema = slideTagSchema.tags.efficio_slide_data_topic_ids.schema;
const TOPIC_ID_PATTERN = new RegExp(topicProperties.topic_id.pattern);
const TOPIC_ID_MAX_LENGTH = topicProperties.topic_id.maxLength;
const NAME_PATTERN = new RegExp(topicProperties.name.pattern);
const NAME_MAX_LENGTH = topicProperties.name.maxLength;
const ASSIGNED_ID_PATTERN = new RegExp(assignmentSchema.items.pattern);
const ASSIGNED_ID_MAX_LENGTH = assignmentSchema.items.maxLength;
const ASSIGNMENT_MIN_ITEMS = assignmentSchema.minItems;
const TOPIC_FIELDS = ["topic_id", "name"] as const;

/**
 * Parse a deck data-topic registry from stored JSON text or an already-decoded
 * array. A missing, blank, or empty value declares no data topics and yields an
 * empty registry. Topics keep their authored order. IDs must be unique and are
 * never trimmed or case-folded; names may repeat and are trimmed.
 */
export function parseDataTopics(
  rawValue: string | readonly unknown[] | undefined
): readonly DataTopic[] {
  if (rawValue === undefined || (typeof rawValue === "string" && trimTopicWhitespace(rawValue) === "")) {
    return [];
  }
  const parsed = decodeValue(rawValue, "Data topics must contain valid JSON.");
  if (!Array.isArray(parsed)) throw invalidRegistry();

  const topics = parsed.map(parseTopic);
  const ids = topics.map((topic) => topic.topic_id);
  if (new Set(ids).size !== ids.length) {
    throw new DataTopicContractError("Data topic IDs must be unique.");
  }
  return topics;
}

/**
 * Parse one slide's data-topic assignment from stored JSON text or an
 * already-decoded array. A missing tag means the slide has no assignment and
 * returns an empty array; a blank or empty stored value is invalid. IDs are
 * returned in their authored order and are never trimmed or case-folded.
 */
export function parseSlideDataTopicIds(
  rawValue: string | readonly unknown[] | undefined
): readonly string[] {
  if (rawValue === undefined) return [];
  if (typeof rawValue === "string" && trimTopicWhitespace(rawValue) === "") {
    throw invalidAssignment();
  }
  const parsed = decodeValue(rawValue, "Slide data topic IDs must contain valid JSON.");
  if (!Array.isArray(parsed) || parsed.length < ASSIGNMENT_MIN_ITEMS) throw invalidAssignment();

  const ids = parsed.map((value) => {
    if (!isExactId(value, ASSIGNED_ID_MAX_LENGTH, ASSIGNED_ID_PATTERN)) throw invalidAssignment();
    return value;
  });
  if (new Set(ids).size !== ids.length) throw invalidAssignment();
  return ids;
}

/**
 * Resolve a slide's assignment against the deck registry, returning the
 * referenced definitions in assignment order. A slide without an assignment
 * resolves to an empty array. Unknown references and structurally invalid
 * values throw.
 */
export function resolveSlideDataTopicAssignment(
  slideTags: Readonly<Record<string, string>>,
  deckTags: Readonly<Record<string, string>>
): readonly DataTopic[] {
  const assignedIds = parseSlideDataTopicIds(slideTags[SLIDE_DATA_TOPIC_IDS_TAG]);
  if (assignedIds.length === 0) return [];

  const registry = new Map(
    parseDataTopics(deckTags[DECK_DATA_TOPICS_TAG]).map(
      (topic): [string, DataTopic] => [topic.topic_id, topic]
    )
  );
  return assignedIds.map((topicId) => {
    const topic = registry.get(topicId);
    if (topic === undefined) {
      throw new DataTopicContractError(
        `The slide references an unknown data topic ${JSON.stringify(topicId)}.`
      );
    }
    return topic;
  });
}

function parseTopic(value: unknown): DataTopic {
  if (!isTopicRecord(value)) throw invalidRegistry();
  if (!isExactId(value.topic_id, TOPIC_ID_MAX_LENGTH, TOPIC_ID_PATTERN)) throw invalidRegistry();
  const name = value.name;
  if (typeof name !== "string" || [...name].length > NAME_MAX_LENGTH || !NAME_PATTERN.test(name)) {
    throw invalidRegistry();
  }
  return { topic_id: value.topic_id, name: trimTopicWhitespace(name) };
}

// Use the authored whitespace rule, not JavaScript's different trim character set.
function trimTopicWhitespace(value: string): string {
  let start = 0;
  let end = value.length;
  while (start < end && !NAME_PATTERN.test(value[start]!)) start += 1;
  while (end > start && !NAME_PATTERN.test(value[end - 1]!)) end -= 1;
  return value.slice(start, end);
}

function decodeValue(rawValue: string | readonly unknown[], message: string): unknown {
  if (typeof rawValue !== "string") return rawValue;
  try {
    return JSON.parse(rawValue) as unknown;
  } catch {
    throw new DataTopicContractError(message);
  }
}

function isExactId(value: unknown, maximum: number, pattern: RegExp): value is string {
  return typeof value === "string" && [...value].length <= maximum && pattern.test(value);
}

function isTopicRecord(value: unknown): value is Record<(typeof TOPIC_FIELDS)[number], unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const actual = Object.keys(value);
  return (
    TOPIC_FIELDS.every((key) => actual.includes(key)) &&
    actual.every((key) => (TOPIC_FIELDS as readonly string[]).includes(key))
  );
}

function invalidRegistry(): DataTopicContractError {
  return new DataTopicContractError("Data topics do not match the deck tag contract.");
}

function invalidAssignment(): DataTopicContractError {
  return new DataTopicContractError(
    "Slide data topic IDs do not match the slide tag contract."
  );
}

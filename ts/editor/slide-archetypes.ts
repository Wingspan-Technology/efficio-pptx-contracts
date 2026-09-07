// Typed access to the optional template-authored slide archetype metadata.
//
// The deck registry (`efficio_slide_archetypes`) declares which archetypes a
// template supports. A slide may narrow itself to a subset of them through
// `efficio_slide_archetype_ids`; a slide with no assignment is generic and stays
// applicable to every declared archetype. Neither tag carries an `ai` block:
// archetypes are pre-selection metadata a client uses to filter its own slide
// catalog before AI slide selection runs, so they never reach the generated
// slide-selection instructions and never affect inclusion policy, choice/bundle
// structure, role, placement, or ordering.
//
// Explicit .js specifiers preserve native ESM behavior after TypeScript compilation.

import {
  deckTagSchema,
  DECK_SLIDE_ARCHETYPES_TAG,
} from "../../generated/ts/presentation/deckTagSchema.js";
import {
  slideTagSchema,
  SLIDE_ARCHETYPE_IDS_TAG,
} from "../../generated/ts/presentation/slideTagSchema.js";

export { DECK_SLIDE_ARCHETYPES_TAG, SLIDE_ARCHETYPE_IDS_TAG };

/** One authored archetype definition in the exact deck-tag wire shape. */
export type SlideArchetype = {
  archetype_id: string;
  name: string;
  description?: string;
};

export class SlideArchetypeContractError extends Error {
  override readonly name = "SlideArchetypeContractError";
}

// Every constraint is read from the generated contracts; no archetype ID, name,
// or limit is hardcoded here.
const definitionItem = deckTagSchema.tags.efficio_slide_archetypes.schema.items;
const definitionProperties = definitionItem.properties;
const assignmentSchema = slideTagSchema.tags.efficio_slide_archetype_ids.schema;
const ID_PATTERN = new RegExp(definitionProperties.archetype_id.pattern);
const ID_MAX_LENGTH = definitionProperties.archetype_id.maxLength;
const NAME_MAX_LENGTH = definitionProperties.name.maxLength;
const DESCRIPTION_MAX_LENGTH = definitionProperties.description.maxLength;
const ASSIGNED_ID_PATTERN = new RegExp(assignmentSchema.items.pattern);
const ASSIGNED_ID_MAX_LENGTH = assignmentSchema.items.maxLength;
const ASSIGNMENT_MIN_ITEMS = assignmentSchema.minItems;

/**
 * Parse a deck archetype registry from stored JSON text or an already-decoded
 * array. A missing, blank, or empty value is a template that declares no
 * archetype restrictions and yields an empty registry.
 */
export function parseSlideArchetypes(
  rawValue: string | readonly unknown[] | undefined
): readonly SlideArchetype[] {
  if (rawValue === undefined || (typeof rawValue === "string" && rawValue.trim() === "")) {
    return [];
  }
  const parsed = decodeValue(rawValue, "Slide archetypes must contain valid JSON.");
  if (!Array.isArray(parsed)) throw invalidRegistry();

  const archetypes = parsed.map(parseArchetype);
  const ids = archetypes.map((archetype) => archetype.archetype_id);
  if (new Set(ids).size !== ids.length) {
    throw new SlideArchetypeContractError("Slide archetype IDs must be unique.");
  }
  return archetypes;
}

/**
 * Parse one slide's archetype assignment from stored JSON text or an
 * already-decoded array. A missing tag means the slide is generic and returns an
 * empty array; a blank or empty stored value is invalid. IDs are returned in
 * their authored order and are never trimmed or case-folded.
 */
export function parseSlideArchetypeIds(
  rawValue: string | readonly unknown[] | undefined
): readonly string[] {
  if (rawValue === undefined) return [];
  if (typeof rawValue === "string" && rawValue.trim() === "") {
    throw invalidAssignment();
  }
  const parsed = decodeValue(rawValue, "Slide archetype IDs must contain valid JSON.");
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
 * referenced definitions in assignment order. A generic slide resolves to an
 * empty array. Unknown references and structurally invalid values throw.
 */
export function resolveSlideArchetypeAssignment(
  slideTags: Readonly<Record<string, string>>,
  deckTags: Readonly<Record<string, string>>
): readonly SlideArchetype[] {
  const assignedIds = parseSlideArchetypeIds(slideTags[SLIDE_ARCHETYPE_IDS_TAG]);
  if (assignedIds.length === 0) return [];

  const registry = parseSlideArchetypes(deckTags[DECK_SLIDE_ARCHETYPES_TAG]);
  return assignedIds.map((archetypeId) => {
    const archetype = registry.find((candidate) => candidate.archetype_id === archetypeId);
    if (archetype === undefined) {
      throw new SlideArchetypeContractError(
        `The slide references an unknown slide archetype ${JSON.stringify(archetypeId)}.`
      );
    }
    return archetype;
  });
}

/**
 * Report whether one slide may be offered for the requested archetype. Generic
 * slides apply to every archetype, including when the registry declares none.
 * A malformed requested ID, an unsupported requested ID against a populated
 * registry, and an invalid registry or assignment all throw rather than
 * silently filtering the slide out.
 */
export function isSlideApplicableToArchetype(
  slideTags: Readonly<Record<string, string>>,
  deckTags: Readonly<Record<string, string>>,
  archetypeId: string
): boolean {
  const registry = parseSlideArchetypes(deckTags[DECK_SLIDE_ARCHETYPES_TAG]);
  if (!isExactId(archetypeId, ID_MAX_LENGTH, ID_PATTERN)) {
    throw new SlideArchetypeContractError(
      `Requested slide archetype ${JSON.stringify(archetypeId)} is not a valid archetype ID.`
    );
  }
  const assigned = resolveSlideArchetypeAssignment(slideTags, deckTags);
  if (
    registry.length > 0 &&
    !registry.some((candidate) => candidate.archetype_id === archetypeId)
  ) {
    throw new SlideArchetypeContractError(
      `Requested slide archetype ${JSON.stringify(archetypeId)} is not declared by the deck.`
    );
  }
  if (assigned.length === 0) return true;
  return assigned.some((candidate) => candidate.archetype_id === archetypeId);
}

function parseArchetype(value: unknown): SlideArchetype {
  if (!isExactObject(value, ["archetype_id", "name"], ["description"])) {
    throw invalidRegistry();
  }
  if (!isExactId(value.archetype_id, ID_MAX_LENGTH, ID_PATTERN)) throw invalidRegistry();
  const archetype: SlideArchetype = {
    archetype_id: value.archetype_id,
    name: requiredText(value.name, NAME_MAX_LENGTH),
  };
  if (value.description === undefined) return archetype;
  return { ...archetype, description: requiredText(value.description, DESCRIPTION_MAX_LENGTH) };
}

function decodeValue(rawValue: string | readonly unknown[], message: string): unknown {
  if (typeof rawValue !== "string") return rawValue;
  try {
    return JSON.parse(rawValue) as unknown;
  } catch {
    throw new SlideArchetypeContractError(message);
  }
}

function requiredText(value: unknown, maximum: number): string {
  if (typeof value !== "string" || value.trim() === "" || [...value].length > maximum) {
    throw invalidRegistry();
  }
  return value.trim();
}

function isExactId(value: unknown, maximum: number, pattern: RegExp): value is string {
  return typeof value === "string" && [...value].length <= maximum && pattern.test(value);
}

function isExactObject<Required extends string, Optional extends string>(
  value: unknown,
  required: readonly Required[],
  optional: readonly Optional[]
): value is Record<Required, unknown> & Partial<Record<Optional, unknown>> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const actual = Object.keys(value);
  const allowed = new Set<string>([...required, ...optional]);
  return (
    required.every((key) => actual.includes(key)) && actual.every((key) => allowed.has(key))
  );
}

function invalidRegistry(): SlideArchetypeContractError {
  return new SlideArchetypeContractError(
    "Slide archetypes do not match the deck tag contract."
  );
}

function invalidAssignment(): SlideArchetypeContractError {
  return new SlideArchetypeContractError(
    "Slide archetype IDs do not match the slide tag contract."
  );
}

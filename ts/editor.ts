// Handwritten TypeScript SDK entrypoint for the Office editor.
//
// Apps import `@efficio/ppt-components/editor` instead of generated file paths;
// the generated TS under `generated/ts/*` stays a package internal. This module
// is the type authority for component metadata (TagEntity / ComponentMetadata)
// and re-exports the generated slide contract surface.
//
// Imports are extensionless to match the generated TS and the editor's bundler
// resolution; this file is type-checked by the editor's tsc, like generated TS.

import { componentMetadata } from "../generated/ts/components/componentMetadata";
import { componentTypes } from "../generated/ts/components/componentTypes";
import { tagSchemas } from "../generated/ts/components/tagSchemas";
import { slideDefaults } from "../generated/ts/presentation/slideDefaults";
import { deckDefaults } from "../generated/ts/presentation/deckDefaults";
import {
  deckTagSchema,
  DECK_TEMPLATE_ID_TAG,
  DECK_INITIALIZED_TAG,
} from "../generated/ts/presentation/deckTagSchema";
import {
  slideTagSchema,
  SLIDE_ID_TAG,
  SLIDE_PLACEMENT_TAG,
  SLIDE_GROUP_ORDER_TAG,
  SLIDE_PURPOSE_TAG,
  SLIDE_CONTENT_DESCRIPTION_TAG,
  SLIDE_INCLUSION_POLICY_TAG,
  SLIDE_PLACEMENTS,
  SLIDE_INCLUSION_POLICIES,
  SLIDE_PURPOSE_MAX_LENGTH,
  SLIDE_CONTENT_DESCRIPTION_MAX_LENGTH,
  type SlidePlacement,
  type SlideInclusionPolicy,
} from "../generated/ts/presentation/slideTagSchema";

const RENDER_BEHAVIOR_TAG = "efficio_render_behavior";

// ---- Component metadata types (SDK is the type authority) ----

export type TagEntity = {
  type: "string" | "integer" | "boolean" | "object" | "array";
  required: boolean;
  enum?: readonly string[];
  min_length?: number;
  max_length?: number;
  minimum?: number;
  maximum?: number;
  description?: string;
  // Object/array tags are stored as JSON text and carry the JSON Schema their
  // parsed value must satisfy. Absent on scalar (string/integer/boolean) tags.
  schema?: Record<string, unknown>;
  // Editor-facing presentation hints, authored on the tag contract. Optional:
  // tags without `ui` sort last and render single-line.
  ui?: {
    order?: number;
    multiline?: boolean;
  };
};

export type ComponentMetadata = {
  component_type: string;
  paths: {
    tags_contract: string;
    content_contract: string;
    tags_defaults: string;
  };
  tags: Record<string, TagEntity>;
  defaults: Record<string, string>;
};

// ---- Compatibility tag schema type (still Zod-validated editor-side) ----

export type CompatibilityTagSchema = {
  generated_from: readonly string[];
  component_type: string;
  description?: string;
  required_tags: readonly string[];
  optional_tags: readonly string[];
  enums: Record<string, readonly string[]>;
  types: Record<string, string>;
  example?: Record<string, string>;
};

const metadata = componentMetadata as unknown as Record<string, ComponentMetadata>;
const compatibilityTagSchemas = tagSchemas as unknown as Record<string, CompatibilityTagSchema>;

// ---- Component metadata accessors ----

export function listComponentTypes(): string[] {
  return [...componentTypes];
}

export function hasComponentType(componentType: string): boolean {
  return Object.prototype.hasOwnProperty.call(metadata, componentType);
}

export function getComponentMetadata(componentType: string): ComponentMetadata {
  if (!hasComponentType(componentType)) {
    throw new Error(`Unknown Efficio component type "${componentType}".`);
  }
  return metadata[componentType];
}

export function getComponentTagContract(componentType: string): Record<string, TagEntity> {
  return getComponentMetadata(componentType).tags;
}

export function getComponentTagDefaults(componentType: string): Record<string, string> {
  return { ...getComponentMetadata(componentType).defaults };
}

export function getKnownComponentTags(componentType: string): Set<string> {
  return new Set(Object.keys(getComponentTagContract(componentType)));
}

// Component tags in editor display order, derived from each tag's `ui.order`.
// Tags without `ui.order` sort after ordered tags, alphabetically — so a new tag
// with contract metadata slots in without editing the editor.
export function getOrderedComponentTags(componentType: string): string[] {
  const entities = getComponentTagContract(componentType);
  return Object.keys(entities).sort((left, right) => {
    const leftOrder = entities[left].ui?.order;
    const rightOrder = entities[right].ui?.order;
    if (leftOrder !== undefined && rightOrder !== undefined) return leftOrder - rightOrder;
    if (leftOrder !== undefined) return -1;
    if (rightOrder !== undefined) return 1;
    return left.localeCompare(right);
  });
}

// Cross-field text sizing checks the per-tag schema cannot express. The `target_*`
// tags are OPTIONAL AI guidance; the min/max tags are strict bounds. Returned as
// plain issues so a consumer maps them into its own validation result. A no-op for
// non-text shapes (the tags are absent), and each check is skipped when an operand is
// not a positive integer (the per-tag schema owns those structural errors). Mirrors
// the Python SDK's `_text_sizing_issues`.
export type ComponentSemanticIssue = {
  code: string;
  message: string;
  tag: string;
};

const TEXT_FORMAT_TAG = "efficio_text_format";
const PLAIN_TEXT_FORMAT = "plain";
const TEXT_MAX_CHARS_TAG = "efficio_max_chars";
const TEXT_TARGET_CHARS_TAG = "efficio_target_chars";
const TEXT_MIN_ITEMS_TAG = "efficio_min_items";
const TEXT_MAX_ITEMS_TAG = "efficio_max_items";
const TEXT_MIN_CHARS_PER_ITEM_TAG = "efficio_min_chars_per_item";
const TEXT_MAX_CHARS_PER_ITEM_TAG = "efficio_max_chars_per_item";
const TEXT_TARGET_CHARS_PER_ITEM_TAG = "efficio_target_chars_per_item";

export function validateTextSizingSemantics(
  tags: Record<string, string>
): ComponentSemanticIssue[] {
  const value = (tag: string): number | undefined => {
    const raw = tags[tag];
    return isPositiveIntegerString(raw) ? Number(raw.trim()) : undefined;
  };
  const maxChars = value(TEXT_MAX_CHARS_TAG);
  const targetChars = value(TEXT_TARGET_CHARS_TAG);
  const minItems = value(TEXT_MIN_ITEMS_TAG);
  const maxItems = value(TEXT_MAX_ITEMS_TAG);
  const minPerItem = value(TEXT_MIN_CHARS_PER_ITEM_TAG);
  const maxPerItem = value(TEXT_MAX_CHARS_PER_ITEM_TAG);
  const targetPerItem = value(TEXT_TARGET_CHARS_PER_ITEM_TAG);

  const issues: ComponentSemanticIssue[] = [];
  const exceeds = (tag: string, other: string): void => {
    issues.push({ code: "target_exceeds_max", tag, message: `"${tag}" must not exceed "${other}".` });
  };

  // Optional targets must fit within their strict bounds.
  if (targetChars !== undefined && maxChars !== undefined && targetChars > maxChars) {
    exceeds(TEXT_TARGET_CHARS_TAG, TEXT_MAX_CHARS_TAG);
  }
  if (targetPerItem !== undefined && maxPerItem !== undefined && targetPerItem > maxPerItem) {
    exceeds(TEXT_TARGET_CHARS_PER_ITEM_TAG, TEXT_MAX_CHARS_PER_ITEM_TAG);
  }
  if (targetPerItem !== undefined && minPerItem !== undefined && targetPerItem < minPerItem) {
    issues.push({
      code: "target_below_min",
      tag: TEXT_TARGET_CHARS_PER_ITEM_TAG,
      message: `"${TEXT_TARGET_CHARS_PER_ITEM_TAG}" must be at least "${TEXT_MIN_CHARS_PER_ITEM_TAG}".`,
    });
  }
  // Strict min <= max ranges.
  if (minItems !== undefined && maxItems !== undefined && minItems > maxItems) {
    issues.push({
      code: "min_exceeds_max",
      tag: TEXT_MIN_ITEMS_TAG,
      message: `"${TEXT_MIN_ITEMS_TAG}" must not exceed "${TEXT_MAX_ITEMS_TAG}".`,
    });
  }
  if (minPerItem !== undefined && maxPerItem !== undefined && minPerItem > maxPerItem) {
    issues.push({
      code: "min_exceeds_max",
      tag: TEXT_MIN_CHARS_PER_ITEM_TAG,
      message: `"${TEXT_MIN_CHARS_PER_ITEM_TAG}" must not exceed "${TEXT_MAX_CHARS_PER_ITEM_TAG}".`,
    });
  }
  // plain text is exactly one item.
  if (tags[TEXT_FORMAT_TAG] === PLAIN_TEXT_FORMAT) {
    if (minItems !== undefined && minItems !== 1) issues.push(plainSingleItem(TEXT_MIN_ITEMS_TAG));
    if (maxItems !== undefined && maxItems !== 1) issues.push(plainSingleItem(TEXT_MAX_ITEMS_TAG));
  }
  return issues;
}

function plainSingleItem(tag: string): ComponentSemanticIssue {
  return { code: "plain_requires_single_item", tag, message: `"${tag}" must be 1 for plain text.` };
}

function isPositiveIntegerString(value: string | undefined): boolean {
  if (typeof value !== "string") return false;
  const trimmed = value.trim();
  return /^\d+$/.test(trimmed) && Number(trimmed) >= 1;
}

// Tags present in every component (e.g. render behavior, component id/type).
export function getCommonComponentTags(): Set<string> {
  const [first, ...rest] = listComponentTypes();
  if (!first) {
    return new Set();
  }

  const common = getKnownComponentTags(first);
  for (const componentType of rest) {
    const tags = getKnownComponentTags(componentType);
    for (const tag of Array.from(common)) {
      if (!tags.has(tag)) {
        common.delete(tag);
      }
    }
  }
  return common;
}

export function getCommonComponentTagEntities(): Record<string, TagEntity> {
  const first = listComponentTypes()[0];
  if (!first) {
    return {};
  }

  const commonTags = getCommonComponentTags();
  const entities = getComponentTagContract(first);
  const commonEntities: Record<string, TagEntity> = {};

  for (const tag of Array.from(commonTags)) {
    commonEntities[tag] = entities[tag];
  }

  return commonEntities;
}

export function getComponentSpecificTags(): Set<string> {
  const common = getCommonComponentTags();
  const specific = new Set<string>();
  for (const componentType of listComponentTypes()) {
    for (const tag of Array.from(getKnownComponentTags(componentType))) {
      if (!common.has(tag)) {
        specific.add(tag);
      }
    }
  }
  return specific;
}

export function getAllKnownComponentTags(): Set<string> {
  const tags = new Set<string>();
  for (const componentType of listComponentTypes()) {
    for (const tag of Array.from(getKnownComponentTags(componentType))) {
      tags.add(tag);
    }
  }
  return tags;
}

// Allowed enum values for a tag in PowerPoint string storage. Booleans become
// "true"/"false"; enum-typed strings use their declared values.
export function getTagEnumValues(entity: TagEntity): string[] | undefined {
  if (entity.type === "boolean") {
    return ["true", "false"];
  }
  if (entity.enum && entity.enum.length > 0) {
    return [...entity.enum];
  }
  return undefined;
}

export function getRenderBehaviorValues(): string[] {
  const first = listComponentTypes()[0];
  if (!first) {
    return [];
  }
  const entity = getComponentTagContract(first)[RENDER_BEHAVIOR_TAG];
  return entity ? getTagEnumValues(entity) ?? [] : [];
}

// ---- Compatibility tag schema accessors ----
// Raw generated compatibility schemas; the editor still Zod-validates these for
// the text form. The SDK is the import source, not the validation boundary.

export function getCompatibilityTagSchemaMap(): Record<string, CompatibilityTagSchema> {
  return compatibilityTagSchemas;
}

export function getComponentCompatibilityTagSchema(componentType: string): CompatibilityTagSchema {
  if (!Object.prototype.hasOwnProperty.call(compatibilityTagSchemas, componentType)) {
    throw new Error(`Unknown Efficio component type "${componentType}".`);
  }
  return compatibilityTagSchemas[componentType];
}

export function listComponentCompatibilityTagSchemas(): CompatibilityTagSchema[] {
  return Object.keys(compatibilityTagSchemas).map((componentType) => compatibilityTagSchemas[componentType]);
}

// ---- Slide contract surface (re-exported generated constants) ----

export type SlideTagSchema = typeof slideTagSchema;
export type SlideDefaults = typeof slideDefaults;

export function getSlideTagContract(): SlideTagSchema {
  return slideTagSchema;
}

// Returns a copy with the precise generated literal types preserved, so callers
// can feed defaults into SlidePlacement / SlideInclusionPolicy slots.
export function getSlideTagDefaults(): SlideDefaults {
  return { ...slideDefaults };
}

export {
  SLIDE_ID_TAG,
  SLIDE_PLACEMENT_TAG,
  SLIDE_GROUP_ORDER_TAG,
  SLIDE_PURPOSE_TAG,
  SLIDE_CONTENT_DESCRIPTION_TAG,
  SLIDE_INCLUSION_POLICY_TAG,
  SLIDE_PLACEMENTS,
  SLIDE_INCLUSION_POLICIES,
  SLIDE_PURPOSE_MAX_LENGTH,
  SLIDE_CONTENT_DESCRIPTION_MAX_LENGTH,
  type SlidePlacement,
  type SlideInclusionPolicy,
};

// ---- Deck (presentation-level) contract surface ----

export type DeckTagSchema = typeof deckTagSchema;
export type DeckDefaults = typeof deckDefaults;

export function getDeckTagContract(): DeckTagSchema {
  return deckTagSchema;
}

// Returns a defensive copy so callers cannot mutate the generated defaults.
export function getDeckTagDefaults(): DeckDefaults {
  return { ...deckDefaults };
}

export { DECK_TEMPLATE_ID_TAG, DECK_INITIALIZED_TAG };

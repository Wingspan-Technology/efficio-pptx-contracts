// Slide + deck (presentation-level) contract surface: thin, typed accessors over the generated slide and
// deck tag schemas/defaults, plus a re-export of the generated tag-name constants and literal-union types.
// Explicit .js specifiers preserve native ESM behavior after TypeScript compilation.

import { slideDefaults } from "../../generated/ts/presentation/slideDefaults.js";
import { deckDefaults } from "../../generated/ts/presentation/deckDefaults.js";
import {
  deckTagSchema,
  DECK_TEMPLATE_ID_TAG,
  DECK_INITIALIZED_TAG,
  DECK_SLIDE_SELECTION_GROUPS_TAG,
} from "../../generated/ts/presentation/deckTagSchema.js";
import {
  slideTagSchema,
  SLIDE_ID_TAG,
  SLIDE_NAME_TAG,
  SLIDE_ROLE_TAG,
  SLIDE_PLACEMENT_TAG,
  SLIDE_GROUP_ORDER_TAG,
  SLIDE_PURPOSE_TAG,
  SLIDE_CONTENT_DESCRIPTION_TAG,
  SLIDE_INCLUSION_POLICY_TAG,
  SLIDE_ROLES,
  SLIDE_PLACEMENTS,
  SLIDE_INCLUSION_POLICIES,
  SLIDE_NAME_MAX_LENGTH,
  SLIDE_PURPOSE_MAX_LENGTH,
  SLIDE_CONTENT_DESCRIPTION_MAX_LENGTH,
  type SlideRole,
  type SlidePlacement,
  type SlideInclusionPolicy,
} from "../../generated/ts/presentation/slideTagSchema.js";
import { copyContractValue } from "./contract-copy.js";

// ---- Slide contract surface (re-exported generated constants) ----

export type SlideTagSchema = typeof slideTagSchema;
export type SlideDefaults = typeof slideDefaults;

export function getSlideTagContract(): SlideTagSchema {
  return copyContractValue(slideTagSchema);
}

// Returns a copy with the precise generated literal types preserved, so callers
// can feed defaults into SlideRole / SlidePlacement / SlideInclusionPolicy slots.
export function getSlideTagDefaults(): SlideDefaults {
  return { ...slideDefaults };
}

export {
  SLIDE_ID_TAG,
  SLIDE_NAME_TAG,
  SLIDE_ROLE_TAG,
  SLIDE_PLACEMENT_TAG,
  SLIDE_GROUP_ORDER_TAG,
  SLIDE_PURPOSE_TAG,
  SLIDE_CONTENT_DESCRIPTION_TAG,
  SLIDE_INCLUSION_POLICY_TAG,
  SLIDE_ROLES,
  SLIDE_PLACEMENTS,
  SLIDE_INCLUSION_POLICIES,
  SLIDE_NAME_MAX_LENGTH,
  SLIDE_PURPOSE_MAX_LENGTH,
  SLIDE_CONTENT_DESCRIPTION_MAX_LENGTH,
  type SlideRole,
  type SlidePlacement,
  type SlideInclusionPolicy,
};

// ---- Deck (presentation-level) contract surface ----

export type DeckTagSchema = typeof deckTagSchema;
export type DeckDefaults = typeof deckDefaults;

export function getDeckTagContract(): DeckTagSchema {
  return copyContractValue(deckTagSchema);
}

// Returns a defensive copy so callers cannot mutate the generated defaults.
export function getDeckTagDefaults(): DeckDefaults {
  return { ...deckDefaults };
}

export { DECK_TEMPLATE_ID_TAG, DECK_INITIALIZED_TAG, DECK_SLIDE_SELECTION_GROUPS_TAG };

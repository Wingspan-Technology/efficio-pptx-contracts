import { getRecord, mergeNativeTags, type JsonObject } from "./contractLib.js";

// AI component instruction artifacts are derived entirely from authored tag `ai`
// metadata (shared fragments + component tags) and the authored content contract.
// They are generated only; do not hand-edit the outputs.

export type AiInstructionSource = {
  componentType: string;
  label: string;
  schema: JsonObject;
  contentContract: JsonObject;
};

// Shared rule for component and slide instruction generation: include only tags
// whose entity declares `ai.purpose`, copying purpose and optional enum_descriptions.
// Preserves authored tag order.
export function extractAiTagInstructions(tags: JsonObject): JsonObject {
  const tagInstructions: JsonObject = {};

  for (const [tag, entity] of Object.entries(tags)) {
    const ai = getRecord(entity as JsonObject, "ai");
    if (typeof ai.purpose !== "string") {
      continue;
    }

    const instruction: JsonObject = { purpose: ai.purpose };
    if ("enum_descriptions" in ai) {
      instruction.enum_descriptions = ai.enum_descriptions;
    }
    tagInstructions[tag] = instruction;
  }

  return tagInstructions;
}

// Builds the per-component instruction artifact: tag instructions for tags that
// declare `ai`, plus the authored content contract copied directly as the
// expected content schema (a self-describing JSON Schema document; no wrapper).
export function buildComponentInstruction(sharedSchema: JsonObject, source: AiInstructionSource): JsonObject {
  const mergedTags = mergeNativeTags(sharedSchema, source.schema, source.label);

  return {
    component_type: source.componentType,
    tag_instructions: extractAiTagInstructions(mergedTags),
    expected_content_schema: source.contentContract,
  };
}

// Builds the static slide-selection instruction artifact from the authored
// description, slide tag ai metadata, and the authored slide-selection response
// schema (copied directly, no wrapper). Not template-specific catalog data.
export function buildSlideSelectionInstruction(
  slidesInstructions: JsonObject,
  slideTagsContract: JsonObject,
  slideSelectionSchema: JsonObject,
): JsonObject {
  return {
    description: slidesInstructions.description,
    slide_tag_instructions: extractAiTagInstructions(getRecord(slideTagsContract, "tags")),
    expected_slide_selection_schema: slideSelectionSchema,
  };
}

// Builds per-component artifacts and the aggregate catalog. `sources` must be in
// the deterministic (sorted) component order chosen by the caller. `instruction`
// is the authored general instruction prepended to the aggregate block.
export function buildComponentInstructions(
  sharedSchema: JsonObject,
  sources: AiInstructionSource[],
  instruction: string,
): { perComponent: Record<string, JsonObject>; aggregate: JsonObject } {
  const perComponent: Record<string, JsonObject> = {};
  const componentInstructions: JsonObject = {};

  for (const source of sources) {
    const built = buildComponentInstruction(sharedSchema, source);
    perComponent[source.componentType] = built;
    componentInstructions[source.componentType] = built;
  }

  return { perComponent, aggregate: { instruction, component_instructions: componentInstructions } };
}

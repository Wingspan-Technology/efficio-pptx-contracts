// Smoke-tests the packed npm artifact's public /editor entrypoint.
//
// Run by scripts/verify-release-artifacts.sh from inside a throwaway consumer
// project that has installed the freshly built tarball, so the import below
// resolves through that installation rather than this repository's sources.

const sdk = await import("@wingspan-technology/efficio-pptx-contracts/editor");
const types = sdk.listComponentTypes();
if (!types.includes("text") || !types.includes("table") || !types.includes("category_chart") || !types.includes("categorical_fill")) {
  throw new Error(`Unexpected component types: ${JSON.stringify(types)}`);
}
if (sdk.DECK_SLIDE_SELECTION_GROUPS_TAG !== "efficio_slide_selection_groups") {
  throw new Error("Missing slide-selection group deck tag export.");
}
if (sdk.DECK_CLASSIFICATION_SCHEMES_TAG !== "efficio_classification_schemes") {
  throw new Error("Missing classification-schemes deck tag export.");
}
if (sdk.SLIDE_ROLE_TAG !== "efficio_slide_role") {
  throw new Error("Missing slide role tag export.");
}
if (JSON.stringify(sdk.SLIDE_ROLES) !== JSON.stringify(["content", "separator"])) {
  throw new Error(`Unexpected slide roles: ${JSON.stringify(sdk.SLIDE_ROLES)}`);
}
if (sdk.getSlideTagDefaults().efficio_slide_role !== "content") {
  throw new Error("Slide role does not default to content.");
}
if (sdk.CURRENT_TEMPLATE_CONTRACT_REVISION !== 3) {
  throw new Error("Unexpected current template contract revision.");
}
if (sdk.getDeckTagDefaults().efficio_template_contract_revision !== "3") {
  throw new Error("Deck defaults do not carry template contract revision 3.");
}
if (sdk.DECK_SLIDE_ARCHETYPES_TAG !== "efficio_slide_archetypes") {
  throw new Error("Missing slide-archetype registry deck tag export.");
}
if (sdk.SLIDE_ARCHETYPE_IDS_TAG !== "efficio_slide_archetype_ids") {
  throw new Error("Missing slide-archetype assignment slide tag export.");
}
const archetypeRegistry = JSON.stringify([
  { archetype_id: "pitch_deck", name: "Pitch deck", description: "Investor narrative." },
  { archetype_id: "training", name: "Training" },
]);
const deckArchetypeTags = { [sdk.DECK_SLIDE_ARCHETYPES_TAG]: archetypeRegistry };
const archetypes = sdk.parseSlideArchetypes(archetypeRegistry);
if (archetypes.length !== 2 || archetypes[0].archetype_id !== "pitch_deck") {
  throw new Error("Slide archetype registry parser is unavailable.");
}
const archetype = archetypes[0];
if (archetype.name !== "Pitch deck" || archetype.description !== "Investor narrative.") {
  throw new Error("Slide archetype definitions lost authored fields.");
}
const trainingAssignment = JSON.stringify(["training"]);
if (JSON.stringify(sdk.parseSlideArchetypeIds(trainingAssignment)) !== trainingAssignment) {
  throw new Error("Slide archetype assignment parser is unavailable.");
}
const assignedSlide = { [sdk.SLIDE_ARCHETYPE_IDS_TAG]: trainingAssignment };
const resolved = sdk.resolveSlideArchetypeAssignment(assignedSlide, deckArchetypeTags);
if (resolved.length !== 1 || resolved[0].archetype_id !== "training") {
  throw new Error("Slide archetype resolver is unavailable.");
}
if (sdk.resolveSlideArchetypeAssignment({}, deckArchetypeTags).length !== 0) {
  throw new Error("A generic slide must resolve to no archetypes.");
}
if (!sdk.isSlideApplicableToArchetype({}, deckArchetypeTags, "pitch_deck")) {
  throw new Error("A generic slide must apply to every declared archetype.");
}
if (sdk.isSlideApplicableToArchetype(assignedSlide, deckArchetypeTags, "pitch_deck")) {
  throw new Error("An assigned slide must not apply to an unassigned archetype.");
}
if (!sdk.isSlideApplicableToArchetype(assignedSlide, deckArchetypeTags, "training")) {
  throw new Error("An assigned slide must apply to its own archetype.");
}
try {
  sdk.isSlideApplicableToArchetype({}, deckArchetypeTags, "board_update");
  throw new Error("An undeclared archetype must be rejected.");
} catch (error) {
  if (!(error instanceof sdk.SlideArchetypeContractError)) throw error;
}
const archetypeEntity = sdk.getDeckTagContract().tags.efficio_slide_archetypes;
if (archetypeEntity.required !== false || archetypeEntity.type !== "array") {
  throw new Error("Generated deck schema is missing the optional archetype registry.");
}
const assignmentEntity = sdk.getSlideTagContract().tags.efficio_slide_archetype_ids;
if (assignmentEntity.schema.minItems !== 1 || assignmentEntity.schema.uniqueItems !== true) {
  throw new Error("Generated slide schema is missing the archetype assignment rules.");
}
const migration = sdk.planTemplateContractMigration([
  { target_ref: "deck", scope: "deck", tags: {} },
  {
    target_ref: "shape:1",
    scope: "shape",
    tags: { efficio_render_behavior: "render_by_component_type" },
  },
]);
if (migration.patches.length !== 2) {
  throw new Error("Template contract migration planner is unavailable.");
}

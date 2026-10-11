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
if (sdk.CURRENT_TEMPLATE_CONTRACT_REVISION !== 5) {
  throw new Error("Unexpected current template contract revision.");
}
if (sdk.getDeckTagDefaults().efficio_template_contract_revision !== "5") {
  throw new Error("Deck defaults do not carry template contract revision 5.");
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
if (sdk.DECK_DATA_TOPICS_TAG !== "efficio_data_topics") {
  throw new Error("Missing data-topic registry deck tag export.");
}
if (sdk.SLIDE_DATA_TOPIC_IDS_TAG !== "efficio_slide_data_topic_ids") {
  throw new Error("Missing data-topic assignment slide tag export.");
}
const topicRegistry = JSON.stringify([
  { topic_id: "topic_revenue", name: "Revenue" },
  { topic_id: "topic_headcount", name: "Headcount" },
  { topic_id: "topic_revenue_eu", name: "Revenue" },
]);
const deckTopicTags = { [sdk.DECK_DATA_TOPICS_TAG]: topicRegistry };
const topics = sdk.parseDataTopics(topicRegistry);
if (
  JSON.stringify(topics.map((topic) => topic.topic_id)) !==
  JSON.stringify(["topic_revenue", "topic_headcount", "topic_revenue_eu"])
) {
  throw new Error("Data-topic registry parser lost authored order.");
}
if (sdk.parseDataTopics(undefined).length !== 0 || sdk.parseDataTopics("[]").length !== 0) {
  throw new Error("An absent or empty data-topic registry must declare no topics.");
}
const topicAssignment = JSON.stringify(["topic_headcount", "topic_revenue"]);
if (JSON.stringify(sdk.parseSlideDataTopicIds(topicAssignment)) !== topicAssignment) {
  throw new Error("Data-topic assignment parser is unavailable.");
}
const topicSlide = { [sdk.SLIDE_DATA_TOPIC_IDS_TAG]: topicAssignment };
const resolvedTopics = sdk.resolveSlideDataTopicAssignment(topicSlide, deckTopicTags);
if (
  JSON.stringify(resolvedTopics) !==
  JSON.stringify([
    { topic_id: "topic_headcount", name: "Headcount" },
    { topic_id: "topic_revenue", name: "Revenue" },
  ])
) {
  throw new Error("Data-topic resolver did not keep assignment order.");
}
if (sdk.resolveSlideDataTopicAssignment({}, deckTopicTags).length !== 0) {
  throw new Error("A slide without an assignment must resolve to no data topics.");
}
for (const rejected of [
  () => sdk.parseSlideDataTopicIds("[]"),
  () => sdk.parseSlideDataTopicIds(JSON.stringify(["topic_revenue\n"])),
  () => sdk.parseDataTopics(JSON.stringify([{ topic_id: "topic_revenue", name: "A", source: "crm" }])),
  () => sdk.resolveSlideDataTopicAssignment(
    { [sdk.SLIDE_DATA_TOPIC_IDS_TAG]: '["topic_margin"]' },
    deckTopicTags,
  ),
]) {
  try {
    rejected();
    throw new Error("Invalid data-topic metadata must be rejected.");
  } catch (error) {
    if (!(error instanceof sdk.DataTopicContractError)) throw error;
  }
}
const topicEntity = sdk.getDeckTagContract().tags.efficio_data_topics;
if (topicEntity.required !== false || topicEntity.type !== "array" || "ai" in topicEntity) {
  throw new Error("Generated deck schema is missing the optional advisory data-topic registry.");
}
const topicAssignmentEntity = sdk.getSlideTagContract().tags.efficio_slide_data_topic_ids;
if (
  topicAssignmentEntity.schema.minItems !== 1 ||
  topicAssignmentEntity.schema.uniqueItems !== true ||
  "ai" in topicAssignmentEntity
) {
  throw new Error("Generated slide schema is missing the data-topic assignment rules.");
}
const topicMigration = sdk.planTemplateContractMigration([
  {
    target_ref: "deck",
    scope: "deck",
    tags: { efficio_template_contract_revision: "4", [sdk.DECK_DATA_TOPICS_TAG]: topicRegistry },
  },
  { target_ref: "slide:slide_001", scope: "slide", tags: topicSlide },
]);
if (
  topicMigration.to_revision !== 5 ||
  JSON.stringify(topicMigration.patches) !==
    JSON.stringify([
      {
        target_ref: "deck",
        scope: "deck",
        set_tags: { efficio_template_contract_revision: "5" },
        remove_tags: [],
      },
    ])
) {
  throw new Error("The revision 4 to 5 migration must only advance the deck revision.");
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

# Named Data Topics: Template Editor Handoff

Read the [feature overview](README.md) for authoritative shapes and SDK behavior.
This is a required downstream implementation handoff, not completed Editor work.

## Author Experience And Scope

Authors create a data topic by entering its name at deck scope, rename without
changing its identity, and assign any number of existing topics to each slide.
No assignment means no topic guidance. This does not upload source data, edit
chunks, bind data, require matching, or initiate AI retrieval. There is no topic
description, required flag, source path, or business enum in this contract.

Inspected checkout on 2026-10-12:
`/home/Ivan/dev/projects/efficio/pptx-template-editor`.
The taskpane is `apps/editor`, not the legacy `apps/template-editor-office`.
Paths below are relative to that repository and must be rechecked for later work.

## Adopt The SDK

Use exact published `@wingspan-technology/efficio-pptx-contracts@0.10.0` in
`apps/editor/package.json`; regenerate `pnpm-lock.yaml`. Follow current private
registry/BuildKit-secret conventions. Never commit tokens, tarballs, source aliases,
or sibling `file:` dependencies. Import through the supported entrypoint:

```ts
import {
  DECK_DATA_TOPICS_TAG,
  SLIDE_DATA_TOPIC_IDS_TAG,
  DataTopicContractError,
  parseDataTopics,
  parseSlideDataTopicIds,
  resolveSlideDataTopicAssignment,
  type DataTopic,
} from "@wingspan-technology/efficio-pptx-contracts/editor";
```

Existing `getDeckTagContract`, `getSlideTagContract`, defaults, and the migration
planner expose the new metadata and revision. The SDK does not create topic IDs,
implement authoring UI, or wire persistence and configuration transfer.

## Required UI And Pure Domain Behavior

1. Add a deck topic list with create, rename, and delete commands. Creation asks
   for a name only; generate a collision-checked stable `topic_`-prefixed ID using
   existing identifier conventions. A rename never regenerates the ID. Normal
   authoring UI should not require raw JSON or manual ID editing.
2. Keep duplicate names legal. Identity and references use IDs; authors see names.
   Preserve registry and assignment order, without sorting or name-based merging.
3. Add a slide multiple-selection control populated from deck topics. Existing
   checkbox/select primitives and the archetype picker are reference patterns,
   but unchecked topics mean no guidance, not applicability to every topic.
4. Clearing the last assignment removes the persisted slide tag. Do not persist
   blank text or `[]`; use the existing draft-clear-to-remove patch behavior.
5. Validate drafts with SDK parsers and resolve against the projected registry.
   Surface malformed JSON, blank names, duplicate IDs, and unknown references.
   Do not silently discard invalid values or treat broken metadata as empty.
6. Keep assignment edits disabled while deck context is unavailable; distinguish
   loading, empty, invalid, and ready states. Empty registry is valid but cannot
   make dangling assignments valid.
7. Block deletion of a referenced topic until explicitly unassigned, following
   existing archetype guards. Delete unused definitions normally. Do not remove
   references during rename or invent cross-slide repair behavior.

Use SDK whitespace and Unicode code-point limits, not separate `.trim()` or
UTF-16-length validation. Serialize the exact objects/arrays into Office tag
strings and preserve unrelated tags and presentation content.

## Store, Office Writes, And Transfer

Extend existing mechanisms instead of adding another store, autosave runner,
or Office write lane. Include `DECK_DATA_TOPICS_TAG` in the explicit
presentation-owned tag list so loading, drafts, background sync, and verification
handle it intentionally. Keep UI in features, pure validation/patch rules in
domain modules, and Office I/O under the platform boundary.

Extend projected registry/assignment guards so deck edits cannot invalidate
slide references. Use coordinated writes and verified readback of owned tags.
Reuse existing partial-host-failure recovery; no silent reset or unmanaged retries.

Configuration transfer must also recognize this dependency:

- Export definitions referenced by an exported slide along with its assigned IDs.
- Accept the registry as a supported deck dependency during import.
- Merge by ID; reject differing same-ID definitions using existing conflict rules.
- Preserve unrelated topics, stable IDs, assignment order, and removal semantics.
- Cover Deck/Slide scope and the shared pipeline used by manual and AI-assisted
  configuration; do not add topic-based source selection to that pipeline.

## Existing Templates And Initialization

Use the existing SDK planner through the startup migration flow. Revision
`4 -> 5` advances only the marker, preserves values, and creates no topics.
Legacy slides remain usable with no guidance. Verify Office writes/readback and
repeat no-op behavior; do not duplicate migration rules in React.

A dependency upgrade that exposes a generic JSON field is not feature completion:
name-only controls, owned-tag persistence, reference guards, and configuration
dependencies still need integration.

## Relevant Existing Files

| Path | Where To Extend / Inspect |
| --- | --- |
| `apps/editor/src/features/deck/components/DeckPresentationPanel.tsx` | Compose named-topic authoring; archetype raw JSON is not the desired UX. |
| `apps/editor/src/features/deck/hooks/useDeckTags.ts` | Existing drafts, readiness, and sync binding. |
| `apps/editor/src/domain/tags/presentationAuthoringKeys.ts` | Explicit owned tags for persistence and verification. |
| `apps/editor/src/domain/forms/deckTagFormModelService.ts` | Metadata-driven forms; avoid duplicate generic topic controls. |
| `apps/editor/src/features/slide/components/SlideArchetypePicker.tsx` | Existing multiple-selection and clearing reference. |
| `apps/editor/src/domain/slide/slideArchetypeFormModel.ts` | Typed selection ready/error model reference. |
| `apps/editor/src/domain/slide/slideArchetypeValidation.ts` | SDK-backed registry and assignment validation reference. |
| `apps/editor/src/domain/slide/slideMetadataValidationService.ts` | Wire slide topic findings. |
| `apps/editor/src/domain/validation/deckTagValidationService.ts` | Wire deck topic findings. |
| `apps/editor/src/platform/office/authoring/authoring-archetype-guard.ts` | Existing projected-reference guard pattern. |
| `apps/editor/src/features/authoring/authoringSafePatch.ts` | Coordinated draft-patch checks before writes. |
| `apps/editor/src/domain/configuration-transfer/configurationDeckTagDependencies.ts` | Referenced definition export/merge/conflict behavior. |
| `apps/editor/src/platform/office/template-contract-migration/template-contract-migration.ts` | Shared patches, Office readback, and startup readiness. |
| `apps/editor/docs/feature-development.md` | Module boundaries and required System validation. |

Topic-specific modules are proposed, not already implemented. Reuse current UI
and host adapters and follow the Editor's nested `AGENTS.md` instructions.

## Acceptance And Validation

- Create with name only; assign across slides; rename with references stable;
  clear completely; block referenced deletion; delete unused definitions.
- Duplicate names are valid; invalid IDs/names/JSON and unknown references fail
  clearly before writes. Loading/empty/error states are distinguishable.
- Reload and Office save/reopen preserve values and unrelated tags.
- Configuration export/import includes referenced definitions, detects conflicts,
  and round-trips clearing without empty assignment arrays.
- Revision-4 initialization preserves existing topics, adds none, and re-runs as
  a no-op; old templates remain usable.
- Archetypes, groups, components, content schemas, and AI retrieval are unchanged.

This is a System change under `apps/editor/docs/feature-development.md` because
it changes SDK consumption, authoring state, Office writes, and transfer:

```bash
pnpm install --frozen-lockfile
pnpm editor:validate:system
pnpm editor:e2e
```

Regenerate the lock before validating frozen installs. Follow the current guide
for production builds/manifests and the protected Office-web canary after deployment.
Browser mocks do not prove real PowerPoint persistence. No Editor source changes,
validation runs, host writes, or deployments were performed for this contracts release.

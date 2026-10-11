# Named Data Topics

**Feature name:** Named Data Topics. **Slug:** `data-topics`.

**Package:** `0.10.0`. **Template contract revision:** `5`, previously `4`.

**Status:** both SDKs and generated resources implemented and locally verified.
Publication status is recorded in the
[release note](../../releases/2026-10-11-2131-v0.10.0-data-topics.md).
Slide Generator integration and published-pin adoption are locally implemented
and its normal full gate passes; those changes remain unmerged and undeployed.
Template Editor topic
authoring and DMS topic-based data selection are not included in this release.

## Problem And Intent

Authors need to name topics such as Baseline Spend or Market Insights and assign
them to relevant slides. Stable IDs allow renaming without changing references.
The vocabulary belongs to each template, not a central business enum. Topics
describe data subjects, whereas archetypes describe presentation variants.

This is optional advisory metadata. It does not store chunks, attach source data,
retrieve documents, call AI, require matching data, filter slides, or change
rendering. A later consumer may use or ignore the guidance. No source selector,
description, binding expression, or mandatory-topic flag is implemented.

## Exactly What Changed

Neither topic tag nor its public SDK APIs existed previously. Two optional tags
are added; component schemas and existing selection rules are unchanged.
PowerPoint stores these values as JSON text, not native objects.

Deck tag `efficio_data_topics` stores a direct array:

```json
[
  {"topic_id": "topic_baseline", "name": "Baseline Spend"},
  {"topic_id": "topic_market", "name": "Market Insights"}
]
```

Each definition has exactly the required `topic_id` and `name` fields. IDs are
unique, at most 120 characters, and match `^topic_[a-z0-9]+(?:_[a-z0-9]+)*$`
exactly. Names are nonblank, at most 120 Unicode code points, and may repeat.
SDK output trims names using the authored whitespace rule. IDs are never trimmed,
case-folded, or regenerated; registry order is preserved.

Slide tag `efficio_slide_data_topic_ids` stores ordered references:

```json
["topic_market", "topic_baseline"]
```

IDs are unique and must resolve against the deck registry. The same ID pattern
and length apply. Resolution returns definitions in assignment order, not
registry order. Missing assignment means no topic guidance, not all topics.

| Input | Deck Registry | Slide Assignment |
| --- | --- | --- |
| Absent tag | Empty registry | No guidance |
| Blank stored value | Empty registry | Invalid |
| Empty array | Empty registry | Invalid; remove the tag when clearing |
| JSON `null`, object, scalar, or malformed text | Invalid | Invalid |
| Extra definition properties / duplicate IDs | Invalid | Duplicate references invalid |
| Unknown referenced ID | Registry may remain valid | Invalid |

Python `None` and TypeScript `undefined` parser arguments mean absent values,
not stored JSON `null`. Full-string ID checks reject trailing newlines. The
explicit name whitespace class gives both SDKs consistent Unicode separator
and byte-order-mark handling rather than language-specific trim behavior.

Neither tag has `ai` metadata. Generated tag-level AI instructions, deck AI
context, expected output schemas, and component content constraints are unchanged.
An importer may carry topics as advisory catalog data in an AI input envelope;
that is separate from adding generated AI instructions.

## Public SDK Input And Output

Python imports from `efficio_pptx_contracts`:

- `DATA_TOPICS_TAG`, `SLIDE_DATA_TOPIC_IDS_TAG`;
- frozen `DataTopic(topic_id, name)`, `DataTopicContractError(ValueError)`;
- `parse_data_topics(raw_value)` -> ordered tuple of definitions;
- `parse_slide_data_topic_ids(raw_value)` -> ordered tuple of IDs;
- `resolve_slide_data_topic_assignment(slide_tags, deck_tags)` -> ordered definitions;
- existing `validate_deck_tags` and `validate_slide_tags(..., deck_tags=...)`.

TypeScript imports from `@wingspan-technology/efficio-pptx-contracts/editor`:
`DECK_DATA_TOPICS_TAG`, `SLIDE_DATA_TOPIC_IDS_TAG`, `DataTopic`,
`DataTopicContractError`, `parseDataTopics`, `parseSlideDataTopicIds`, and
`resolveSlideDataTopicAssignment`. Parsers/resolver return readonly arrays.

Both SDKs accept stored JSON strings or decoded arrays in parser calls. Typed
errors reject invalid metadata. These functions perform no PowerPoint writes.

Python presentation validation returns `TagValidationIssue(code, message,
tag_name)`. Existing structural findings (`invalid_json`, `invalid_json_type`,
`schema_violation`) suppress matching semantic findings to prevent duplicates:

| Semantic Code | Meaning |
| --- | --- |
| `invalid_data_topics` | Invalid registry semantics, including duplicate IDs. |
| `invalid_slide_data_topic_assignment` | Invalid assignment not already reported structurally, including blank. |
| `unknown_data_topic_reference` | Unknown ID, missing deck context, or unusable deck registry; the message distinguishes them. |

An unassigned slide needs no deck context. Whole-template validation still
validates the registry even when no slide references it.

## Compatibility And Migration

`0004-to-0005.json` has no operations: it sets the deck revision marker to `5`
without creating empty tags, inventing topics, or rewriting existing topic values.
Earlier revisions retain their ordered transformations and end at `5`.
Current-revision planning and apply-then-replan are no-ops. The deck default
revision changes from `4` to `5`; slide defaults do not change.

Previously valid templates without topics remain valid. Manually authored new
tags must satisfy the new rules when imported. Both planners return pure set/remove
patches; the importer and Editor own actual working-copy or Office mutation and
readback. SDK installation alone does not mutate templates sitting in storage.
See the separate handoffs for refresh sequencing, failures, and host acceptance.

## Relevant Files In Contracts

| Path | Responsibility |
| --- | --- |
| `contracts/presentation/deck/tags.contract.json` | Authoritative registry schema and semantics. |
| `contracts/presentation/slide/tags.contract.json` | Assignment schema. |
| `contracts/presentation/deck/tags.defaults.json` | Revision 5 without topic defaults. |
| `contracts/presentation/template/migrations/0004-to-0005.json` | Revision-only transition. |
| `src/efficio_pptx_contracts/data_topics.py` | Python typed parsers and resolver. |
| `src/efficio_pptx_contracts/_presentation_tag_validation.py` | Structured topic findings. |
| `src/efficio_pptx_contracts/__init__.py` | Public Python exports. |
| `ts/editor/data-topics.ts`, `ts/editor.ts` | TypeScript implementation and exports. |
| `generated/schemas/presentation/`, `generated/ts/presentation/`, `src/efficio_pptx_contracts/_generated/schemas/presentation/` | Regenerated internal schemas and migration resources. |
| `tests/fixtures/data-topic-cases.json` | Shared language-parity behavior cases. |
| `tests/dataTopics.test.ts`, `tests/test_data_topics.py` | Parser, resolver, and validator tests. |
| `tests/fixtures/template-contract-migration-cases.json` | Shared migration preservation cases. |
| `tests/templateContractMigrations.test.ts`, `tests/test_template_contract_migrations.py`, `tests/generated.test.ts` | Idempotence and generated-output independence. |
| `scripts/verify-installed-editor.mjs`, `scripts/verify-installed-python-sdk.py` | Installed package smoke proof. |

## Verification And Integration

Local checks on 2026-10-11 passed: 534 TypeScript tests, 561 Python tests, ruff,
mypy, SDK builds, generated resources, checksums, and installed-package smoke
checks. These results do not prove remote publication or deployed consumers.

The same contracts checks passed again on 2026-10-12. Release publication,
remote CI, downloaded-asset checksums, and installed-SDK proof are now recorded
in the linked release note. Consumer deployment and live migrations remain separate.

- [Slide Generator: exact adoption, artifacts, migration, and acceptance](slide-generator.md).
- [Template Editor: authoring, persistence, transfer, migration, and acceptance](template-editor.md).
- [Release status and evidence](../../releases/2026-10-11-2131-v0.10.0-data-topics.md).

---
name: efficio-contract-feature-handoff
description: Name and document every Efficio contracts feature or behavior change with its own folder and separate actionable Slide Generator and Template Editor handoffs before completion or release.
---

# Named Feature Handoffs

Apply to every feature implementation or contract/SDK behavior change, including
migrations and features affecting only one consumer. This does not authorize
modifying or deploying consumers. Read paths from repository root.

## Required Structure

Choose a meaningful display name and stable lowercase hyphenated slug. Create
its documentation folder at implementation start and complete it before finishing:

```text
docs/features/<feature-slug>/
  README.md
  slide-generator.md
  template-editor.md
```

Use one folder per named feature; update it for follow-ups instead of creating
competing specifications. Both consumer documents are mandatory. An unaffected
consumer still gets its rationale, preservation requirements, and regression checks.
Link the folder from `docs/features/README.md` and the matching timestamped release
note; `docs/README.md` links the feature index. Multi-feature releases link all
affected folders. Release notes remain required and do not replace feature docs.

## Overview: README.md

Include:

- Display name, slug, intended package version, independent template revision,
  source implementation, verification, publication, and consumer status.
- Problem, intent, completed scope, non-goals, and deferred behavior.
- Exact old/new behavior: scope, requiredness, defaults, omission, empty/null
  handling, limits, enums, uniqueness, references, ordering, normalization, and
  AI/trust semantics. Show realistic input/output and failure shapes.
- Compatibility: old templates/clients, migration sequence, preservation,
  no-op/idempotence, failure conditions, deployment ordering, and rollback limits.
- Supported Python and TypeScript APIs; no generated-internal import recipes.
- Verified relevant-file map: authored contracts, SDKs, generated resources,
  tests, release/version files, and the responsibility of each.
- Exact checks and results, distinguishing source tests, mocks, installed packages,
  CI, publication, consumer integration, and live deployment.
- Links to both consumer handoffs and the release note.

Examples explain the authored schemas; they are not a second definition.

## Slide Generator: slide-generator.md

1. Explain what changed, why the server must match it, and unaffected surfaces.
2. List public Python SDK imports and exact adoption steps: publish first,
   published checksums, release lock, direct pins, build paths, and lockfile.
3. Inspect current consumer source. Map existing files and responsibilities;
   clearly label proposed files, and never invent paths.
4. Describe parsing, validation, references, normalization, artifacts, request and
   response shapes, omissions, errors, rendering and AI/trust boundaries.
5. Explain migration/re-import ownership, latest versus historical templates,
   working-copy save/readback, actual deployment sequencing, and failure gates.
   Do not promise pre-rollout blocking or automatic rollback without evidence.
6. Give ordered integration steps and behavior acceptance: old templates,
   invalid inputs, unchanged surfaces, and native PowerPoint proof when relevant.
7. Separate implemented consumer code, required adoption work, and live evidence.

## Template Editor: template-editor.md

1. Explain what authors can create, edit, assign, clear, or remove and why;
   do not promise automatic backend effects for advisory authoring tags.
2. List the exact published npm dependency, `/editor` exports, metadata APIs,
   lockfile/build requirements, and any APIs the SDK does not provide.
3. Inspect current UI, pure domain logic, authoring store, mutation coordination,
   Office reads/writes, migration, validation, and transfer. Map where to extend;
   do not prescribe duplicate stores or host-write mechanisms.
4. Specify stable identity, name rules, defaults, reference guards, loading/error
   states, removal/clearing, persistence, readback, and host failure behavior.
5. Cover initialization, old-template migration, copy/import dependency registries,
   conflict handling, and other affected authoring workflows.
6. Give domain, UI, transfer, and real-host acceptance criteria using the Editor's
   current validation guide. Mark unimplemented or unverified behavior explicitly.

## Completion Gate

Check all three documents exist, links and file maps resolve, examples match SDK
tests, and both handoffs answer what changed, why, what to do, where, how, and
how to verify. If consumer source is unavailable, disclose that limit and useful
entrypoint search targets rather than claiming inspection or implementation.
Incomplete handoffs mean the feature is not ready to finalize.

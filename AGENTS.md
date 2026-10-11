# Contracts Repository Rules

## Required Skills

Read the matching repository-local skill before work:

- Contracts, SDKs, validation, defaults, migrations, or generated outputs:
  [.agents/skills/efficio-contract-development/SKILL.md](.agents/skills/efficio-contract-development/SKILL.md).
- Every feature implementation or behavior change:
  [.agents/skills/efficio-contract-feature-handoff/SKILL.md](.agents/skills/efficio-contract-feature-handoff/SKILL.md).
- Package versions, release preparation, publication, and consumer adoption:
  [.agents/skills/efficio-contract-release/SKILL.md](.agents/skills/efficio-contract-release/SKILL.md).

These skills supplement the architecture in `README.md` and the index in
`docs/README.md`; they do not authorize external actions.

## Mandatory Feature Documentation

Name every implemented feature with a human-readable name and stable lowercase
hyphenated slug. Before completing it, create `docs/features/<feature-slug>/`:

1. `README.md`: intent, exact changes, technical details, examples, compatibility,
   relevant source and test files, and verification/release status.
2. `slide-generator.md`: separate Slide Generator implementation handoff.
3. `template-editor.md`: separate Template Editor implementation handoff.

Each consumer document explains what changed, why, what to do, where to look,
how to implement it within existing boundaries, and how to verify it. If a
consumer is unaffected, explain why and its regression checks; do not omit the
document. Follow-up changes update the same named feature folder. Link it from
`docs/features/README.md` and the matching timestamped release note. Release notes
do not replace these documents. Documentation-only corrections create no new feature.

## Engineering Boundaries

- Author rules under `contracts/`; never hand-edit `generated/` or Python `_generated/`.
- Regenerate with `npm run generate:ts`; test Python and TypeScript parity.
- Consumers use published public SDKs, not sibling source aliases or internals.
- Keep SDK behavior deterministic and free of Office, Aspose, AI, HTTP, and DB I/O.
- Keep authored production source at or below 400 lines; preserve unrelated work.
- Align both package versions; keep migration history append-only.
- Distinguish source checks, installed packages, CI, publication, consumer work,
  and live deployment. Never describe planned work as completed.
- No assistant, vendor, or tool attribution in commits, documentation, or metadata.
- Publish only when requested; use scoped branches and reviewed pull requests.

## Completion

Run the relevant skill's checks, inspect the scoped diff, complete the named
feature documents, and report remaining consumer or publication work explicitly.

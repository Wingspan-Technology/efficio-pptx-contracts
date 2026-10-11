# Efficio PPTX contracts documentation

This repository is the source of truth for PowerPoint template tags, component
content contracts, generated schemas, template migrations, and the Python and
TypeScript consumer SDKs.

- Author contract changes under `contracts/`.
- Regenerate derived files with `npm run generate:ts`; never edit `generated/`
  or the packaged `_generated/` mirrors manually.
- Add adjacent template migrations under
  `contracts/presentation/template/migrations/` when stored template tags change.
- Consume the published SDKs from downstream applications instead of reading
  repository internals.
- Read [release notes](releases/README.md) for versioned consumer handoffs.
- Read [named features](features/README.md) for technical overviews and separate
  Slide Generator and Template Editor integration documents.

Every feature needs its named folder and both consumer handoffs, following the
[feature skill](../.agents/skills/efficio-contract-feature-handoff/SKILL.md).

Every package release must have a timestamped document under `docs/releases/`
before it is tagged or published to GitHub.

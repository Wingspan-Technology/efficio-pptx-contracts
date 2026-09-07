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

Every package release must have a timestamped document under `docs/releases/`
before it is tagged or published to GitHub.

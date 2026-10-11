---
name: efficio-contract-development
description: Author or change Efficio PPTX contracts, shared Python and TypeScript SDK behavior, defaults, migrations, and generated outputs in this repository.
---

# Contract Development

Also read `../efficio-contract-feature-handoff/SKILL.md` for every feature or
behavior change and `../efficio-contract-release/SKILL.md` for package versions.
Read repository paths below from the repository root, not the skill directory.

## Inspect The Owner

- `README.md`: architecture and supported SDK entrypoints.
- `contracts/components/<component>/`: tags, content, and defaults for one component.
- `contracts/presentation/{deck,slide,template}/`: metadata and adjacent migrations.
- `contracts/shared/`: authored fragments, not runtime logic.
- `scripts/generate-ts-contracts.ts`, `scripts/contractValidation.ts`, and
  `scripts/contractLib.ts`: existing generation and validation composition.
- `src/efficio_pptx_contracts/`: typed Python loaders, validation, and pure planners.
- `ts/editor.ts`, `ts/editor/`: supported TypeScript consumer surface.
- `tests/fixtures/`: shared wire and migration cases consumed by both SDKs.
- `scripts/verify-installed-editor.mjs`, `scripts/verify-installed-python-sdk.py`:
  installed-artifact proof, not imports from this checkout.

Inspect the nearest existing feature before introducing a pattern. Registry and
reference features reuse typed parsers, resolvers, and structured validation.

## Implementation Rules

1. Author schemas and defaults under `contracts/`; never edit generated outputs manually.
2. Keep schema structure, semantic validation, normalization, and AI projection
   distinct. Classify metadata as advisory, trusted rendering input, AI guidance,
   or a hard content constraint and document that trust boundary.
3. Export public APIs through existing SDK entrypoints; generated internals are
   not supported consumer imports. Do not duplicate contracts downstream.
4. Test both languages against shared absence, empty, malformed, boundary, Unicode,
   duplicate, reference, ordering, and unknown-value cases as relevant.
5. Append adjacent migrations only for documented stored-template compatibility.
   Preserve historical definitions. Explain any revision-only transition and
   what it deliberately does not backfill.
6. Test old-to-current migration, preservation, current no-op, and
   apply-then-replan idempotence. Actual PowerPoint mutation belongs to consumers.
7. Keep source focused, strictly typed, and at or below 400 lines. Avoid I/O,
   undocumented fallbacks, speculative dependencies, and unnecessary abstractions.

## Verify

Remove machine-generated caches before contract generation. From repository root:

```bash
find contracts src -name __pycache__ -type d -exec rm -rf {} +
timeout 90s npm run check
timeout 60s uv run ruff check src tests
timeout 60s uv run mypy
timeout 120s uv run pytest -q
timeout 180s npm run release:verify
git diff --check
```

`npm run check` validates, regenerates both resource trees, typechecks, tests,
and builds. Inspect generated diffs for unintended instruction/schema/default
changes. CI regeneration must leave no diff after intended outputs are committed.
Extend installed-package smoke checks for changed exports or resources; source
tests alone do not prove the npm tarball or wheel works.

Complete the named feature handoffs and report checks not run, release state,
and downstream gaps before claiming completion.

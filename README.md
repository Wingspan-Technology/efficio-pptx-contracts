# Efficio PPTX Contracts

Source of truth for Efficio PowerPoint component and presentation contracts.
The repository generates the SDK data used by the PowerPoint template editor,
template importer, and slide generator.

## Repository Layout

```text
contracts/                    Authored cross-language contract sources
generated/                    Committed generated schemas, metadata, and instructions
scripts/                      Contract validation and generation
src/efficio_pptx_contracts/  Python SDK and bundled generated resources
ts/                           Handwritten TypeScript SDK surface
tests/                        TypeScript and Python contract tests
```

Each component under `contracts/components/<component>/` owns:

- `tags.contract.json`;
- `content.contract.json`;
- `tags.defaults.json`.

Presentation-level contracts live under `contracts/presentation/`, and reusable
tag fragments live under `contracts/shared/`. Generated files must never be
edited manually.

## Public SDKs

The npm package is `@wingspan-technology/efficio-pptx-contracts`. Its supported TypeScript entrypoint
is:

```ts
import {
  getComponentMetadata,
  listComponentTypes,
} from "@wingspan-technology/efficio-pptx-contracts/editor";
```

The Python distribution is `efficio-pptx-contracts`. Its import name is:

```python
from efficio_pptx_contracts import list_component_types
```

Generated TypeScript modules and bundled Python JSON resources are package
internals. Consumers must use the public SDK entrypoints instead of importing
generated files directly.

## Architecture and trust boundaries

Authored JSON under `contracts/` is validated before one generation pass writes
the committed `generated/` tree and the exact Python resource mirror. The
handwritten TypeScript and Python modules provide deterministic access,
validation, schema projection, and normalization around those artifacts; they do
not call AI providers, render PowerPoint content, or perform orchestration.

The Python V2 schema builder returns exactly `component_type`, `output_schema`,
and `normalization`. `output_schema` may be sent to an external structured-output
caller. `normalization` is trusted runtime metadata: it must remain private and
must not be accepted from or returned to that caller. Generated content is
validated against the output schema before the SDK normalization and semantic
validation APIs are applied.

All public TypeScript metadata accessors return independent values. Consumers
may modify a returned object locally without changing subsequent SDK results.

## Development

Requirements:

- Node.js 20, 22, or 24+
- Python 3.12+
- `uv`

Install dependencies:

```bash
npm ci
uv sync --extra test
```

Run the contract checks:

```bash
timeout 30s npm run validate:contracts
timeout 30s npm run generate:ts
timeout 30s npm run typecheck
timeout 30s npm test
timeout 30s uv run ruff check src tests
timeout 30s uv run mypy
timeout 30s uv run pytest -q
```

`npm run generate:ts` updates both `generated/` and the Python SDK's
`_generated/` resource mirror. Commit those outputs with their authored contract
changes. CI regenerates them and fails when the committed result is stale.

## Release Artifacts

Build the versioned release files locally:

```bash
timeout 60s npm run release:build
```

This creates `release/` with:

- the npm `.tgz` package;
- the Python wheel and source distribution;
- `SHA256SUMS` for downstream verification.

Build, checksum, install, and exercise both packages with:

```bash
timeout 120s npm run release:verify
```

The npm package contains only compiled JavaScript, declarations, and package
metadata. The Python wheel contains the SDK and its runtime schemas,
instructions, and component registry.

## Versioning

Both SDKs use the same semantic version. Update `package.json` and
`pyproject.toml` together; tests reject version drift.

For a manual release:

1. Update both versions.
2. Regenerate and run all checks.
3. Commit the source and generated outputs.
4. Create an annotated matching tag, for example `v0.1.0`.
5. Push the commit and tag.

Pushing a matching `vX.Y.Z` tag runs `.github/workflows/release.yml`. The
workflow verifies the tag and both package versions, rebuilds and installs the
artifacts, publishes the npm package to GitHub Packages, then creates a GitHub
Release containing all files from `release/`. It uses the repository-scoped
`GITHUB_TOKEN`; no publication secret is needed.

After creating the GitHub repository, connect and publish this local history:

```bash
git remote add origin git@github.com:Wingspan-Technology/efficio-pptx-contracts.git
git push -u origin main
git push origin v0.1.0
```

Downstream CI must download an exact tagged asset and validate it against that
release's `SHA256SUMS`. It must not download an unpinned latest release.

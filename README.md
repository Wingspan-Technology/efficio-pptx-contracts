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

Categorical-fill components reference reusable RGB classification schemes stored
in the optional presentation-level `efficio_classification_schemes` tag. The
generated or data-bound content is only `{"case_id":"..."}`; trusted colors stay
in private normalization/rendering metadata. Python consumers pass `deck_tags`
to the context-aware component builders. Editor consumers use the typed
`parseClassificationSchemes()` and `resolveCategoricalFillScheme()` exports.

Deck-level slide-selection groups are authored in the optional
`efficio_slide_selection_groups` tag as a direct JSON array. Python consumers
use `parse_slide_selection_groups()` and `normalize_slide_selection_groups()`
to build the validated graph, then call
`validate_slide_selection_group_selection()` on the final selected slide IDs.
Valid root wrappers containing one direct slide are normalized away and remain
ordinary standalone slides.

Optional slide archetypes let one template serve several presentation shapes.
A deck authors the registry in `efficio_slide_archetypes` as a direct JSON array
of `{archetype_id, name, description?}` objects; `archetype_id` is
lower-snake-case and unique, while names may repeat. A slide narrows itself with
`efficio_slide_archetype_ids`, a non-empty JSON array of unique IDs the registry
defines. A slide without that tag is generic and applies to every archetype, and
a slide may list several archetypes at once. Editor consumers use
`parseSlideArchetypes()`, `parseSlideArchetypeIds()`,
`resolveSlideArchetypeAssignment()`, and `isSlideApplicableToArchetype()`; Python
consumers use the equivalent `parse_slide_archetypes()`,
`parse_slide_archetype_ids()`, `resolve_slide_archetype_assignment()`, and
`is_slide_applicable_to_archetype()`, and pass `deck_tags` to
`validate_slide_tags()` whenever a slide carries an assignment.

Archetypes affect applicability only. A client filters its own slide catalog with
the applicability predicate *before* AI slide selection runs; inclusion policy,
choice/bundle group structure, slide role, placement, and ordering remain
independent and unchanged. Neither tag declares an `ai` block, so neither reaches
the generated slide-selection instruction. An empty or missing deck registry is
the legacy, unrestricted case: every slide stays applicable, and migration never
backfills archetype metadata into an existing template. Contract-wide archetype
enums do not exist — the vocabulary belongs to each template.

Every slide requires `efficio_slide_role`: `content` identifies a normal
presentation slide, while `separator` identifies a section divider. Role is
descriptive metadata only and does not control inclusion, placement, ordering,
or grouping; bundle groups remain responsible for all-or-none selection. The
revision-0 template migration assigns `content` when an existing slide has no
role.

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

Every component uses `efficio_content_mode`: `ai_generated`, `data_bound`,
`preserve`, or `remove`. The Python data-bound contract API keeps the renderer's
required structure while deliberately omitting AI sizing, count, sign, target,
and formatting limits from submitted content validation. The current component
configuration tags remain required; removing or hiding AI-only authoring fields
for data-bound components belongs to the later Template Editor integration.

Text components and rendered table cells share one estimated capacity model.
`max_lines` and `estimated_chars_per_line` describe the available visual space;
`min_items` and `max_items` bound semantic paragraphs or list entries, while
`target_items` is guidance only. Each item consumes at least one estimated line,
wrapping consumes additional lines, and explicit line breaks consume lines. The
calculation is deterministic content validation, not exact PowerPoint layout
measurement. Data-bound submission schemas remain intentionally limit-free.

Template file compatibility is tracked independently from the package version by
the required deck tag `efficio_template_contract_revision`. Append-only adjacent
migrations are authored under `contracts/presentation/template/migrations/`.
Both SDKs expose the derived current revision, immutable migration catalog data,
and a pure planner that returns explicit tag set/remove patches over opaque
deck, slide, and shape target references. Consumers apply patches to a copy,
then run normal contract validation and template import. A current-revision
template that still contains a retired source tag is rejected.
Revision 2 replaces independent aggregate and per-item character limits with
the shared estimated line-capacity fields, including capacity settings nested in
`efficio_table_config`. Revision 3 introduces the optional slide archetype tags;
it is a revision-only migration that advances the deck revision and writes no
archetype tags, so a migrated legacy template keeps its unrestricted behavior.

Detailed, timestamped consumer handoffs are recorded under
[`docs/releases/`](docs/releases/README.md). These notes explain what changed and
what downstream applications must implement; authored files under `contracts/`
remain the source of truth.

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

# Efficio PPT Components

This package is the source of truth for Efficio PowerPoint component contracts,
presentation contracts, shared contract fragments, generated JSON schemas, and
generated TypeScript exports.

For the full contract model, see
[`../../docs/contracts.md`](../../docs/contracts.md).

## Source Layout

Authored contracts are cross-language source for multiple runtimes (TypeScript
generation, Python SDK resources, editor metadata, importer validation, AI
artifacts). They are **not** Python modules, so they live at the package root
under `contracts/`, separate from the Python SDK under `src/`.

```text
contracts/            # authored source of truth (not Python modules)
  components/
    text/
    table/
    category_chart/
  presentation/
    slide/
    template/
  shared/

src/
  efficio_ppt_components/   # the Python SDK (the only thing under src/)
    _generated/             # wheel-safe runtime mirror of generated JSON

generated/                  # canonical generated outputs
  component-registry.json
  schemas/
  ts/

scripts/                    # the generator
  generate-ts-contracts.ts
  contractLib.ts
  contentContractLib.ts
  defaultsContractLib.ts
  slideTsOutput.ts

ts/                         # handwritten TypeScript SDK entrypoint (editor)
```

## Authored Files

Each component under `contracts/components/{component}/` must have:

- `tags.contract.json`;
- `content.contract.json`;
- `tags.defaults.json`.

`efficio_max_chars` and the item-level limits `efficio_min_items` /
`efficio_max_items` / `efficio_min_chars_per_item` / `efficio_max_chars_per_item`
are required with **no static default** — authored, entered manually, or populated
by the editor's auto sizing estimate. The item limits apply to every string in the
content's `items[]` and drive `validation.json` (item count + per-item length;
`plain` is exactly one item). `efficio_target_chars` and
`efficio_target_chars_per_item` are **optional** AI guidance (preferred lengths, not
maximums); when present they must fit within their strict bounds and never appear in
`validation.json`. Per-item line limits are intentionally deferred.

Tag entities are typed `string`, `integer`, `boolean`, `object`, or `array`.
Object/array tags (e.g. `table`'s `efficio_table_config`) are stored
as JSON text in the PowerPoint custom tag and must declare a `schema` (a JSON
Schema document, AJV-validated by the generator); scalar tags must not declare a
`schema`. The generated compatibility schema maps them to the logical types
`json_object` / `json_array` and exposes their schemas under a `json_schemas` map
keyed by tag name; the native metadata keeps the `schema` on the tag entity.

Components:

- `text` — text frame content (plain/paragraph/bullets/numbered), editor-estimated sizing.
- `table` — generic coordinate-anchored table (`efficio_table_config`: per-cell
  `{row, col}` config with an optional `render_action` of render/preserve, text
  format, and per-cell sizing limits; optional per-row/column `content_policy` —
  the AI is instructed to treat sizing limits as strict; the runtime does not enforce them).
- `category_chart` — chart component driven by flat tags (`efficio_chart_type`,
  `efficio_category_mode`/`efficio_series_mode`, the fixed `efficio_categories` /
  `efficio_series_names` arrays, count boundaries/targets, and value formatting — no
  config object tag). Rendered by `efficio-ppt-generation` for the six 2D column/bar
  chart types.

Slide and template contracts live under `contracts/presentation/`. Shared
reusable contract fragments live under `contracts/shared/`.

Do not put authored source files under `generated/`.

## Generated Files

Run the generator after contract/default changes:

```bash
npm run generate:ts
```

The generator emits:

- generated component registry;
- generated component schemas;
- generated presentation schemas;
- generated TypeScript exports for component metadata, tag schemas, defaults,
  slide contracts, and template contracts;
- generated AI component instructions: `generated/ai/component-instructions.json`,
  `generated/ai/components/{component}.instruction.json`, and
  `generated/ts/ai/componentInstructions.ts` (derived from authored tag `ai`
  metadata, content contracts, and the authored general instruction at
  `contracts/components/components.instructions.json`). The aggregate has the shape
  `{ instruction, component_instructions }`, and each `expected_content_schema`
  is the authored `content.contract.json` copied directly (a self-describing JSON
  Schema, no wrapper);
- generated static slide-selection AI instructions:
  `generated/ai/slide-selection.instruction.json` and
  `generated/ts/ai/slideSelectionInstructions.ts` (derived from authored
  `contracts/presentation/slide/slides.instructions.json`, slide tag `ai`
  metadata, and `contracts/presentation/slide/slide-selection.schema.json`).

Do not hand-edit generated files.

## TypeScript SDK (editor)

`ts/editor.ts` is the handwritten TypeScript SDK entrypoint, imported by the
Office editor as `@efficio/ppt-components/editor`. It wraps the generated TS under
`generated/ts/` (a package internal) behind stable accessors: component type
discovery, component metadata (`TagEntity` / `ComponentMetadata` types, tags,
defaults), the compatibility tag schemas the text form uses, and the slide tag
contract, defaults, and constants.

Run `npm run generate:ts` before consuming the SDK so the generated TS it wraps
exists. The editor resolves this entrypoint via path alias (tsconfig, webpack,
vitest); it is not published as a node dependency.

## Commands

```bash
timeout 30s npm run generate:ts
timeout 30s npm exec tsc -- --noEmit
timeout 30s npm test
```

Package shortcut:

```bash
npm run check
```

Use explicit `timeout` commands in agent runs.

## Python SDK

The importable package `efficio_ppt_components` (under `src/`, per the package
layout convention in [docs/conventions.md](../../docs/conventions.md)) is the
public Python surface. It reads generated runtime JSON that ships inside the
package under `src/efficio_ppt_components/_generated/` (mirrored from the
canonical top-level `generated/` JSON in the same `generate:ts` pass) via
`importlib.resources`.

Public API:

- `registry`: `load_component_registry`, `list_component_types`,
  `has_component_type`, `assert_component_type`;
- `instructions`: `load_component_instruction`, `load_component_instructions`,
  `load_slide_selection_instruction`, and
  `build_component_instruction_block(component_types)` — the entrypoint for
  runtime component-instruction selection. It deduplicates, sorts, and validates
  the requested types and returns
  `{ instruction, component_instructions }`. It does not assemble final prompt
  text — the orchestrator embeds the block in its generation-instructions
  response, and assembling the prompt / calling a model is the API client's job;
- tag validation/access: `load_component_tag_schema`,
  `load_slide_tag_contract`, `validate_component_tags`, and
  `validate_slide_tags`. These validate against generated component/presentation
  tag resources mirrored under `_generated/schemas/`; runtime/importer packages
  must use these helpers instead of duplicating required-tag, enum, type, and
  constraint rules. Object/array (`json_object` / `json_array`) tag values are
  parsed from JSON and validated against the generated `json_schemas` entry with
  `jsonschema` (the package's one runtime dependency), reporting readable
  `invalid_json` and `schema_violation` issues;
- `validation_schema`: `build_validation_content_schema(component_type, tags)` —
  the per-instance `content` JSON Schema the importer writes into the
  `slide-components/{slide_id}/validation.json` content-validation artifact. It deep-copies the
  type's authored `expected_content_schema` and applies instance limits parsed
  from the raw `efficio_*` tags (text: item count/length caps from the sizing
  tags; table: allowed render-cell coordinates, per-cell limits, and
  required-cell `contains` rules from `efficio_table_config`). Every registered
  type is supported, so a schema is always returned; an unknown type raises
  `UnknownComponentTypeError`, and missing/invalid limit tags raise instead of
  emitting a permissive schema.
  Multi-item text caps per-item length and item count but not the aggregate
  `max_chars` across items — JSON Schema cannot sum item lengths, so DMS enforces
  the total later.

There are no per-component Python builder modules or top-level Python scaffolds;
the `efficio_ppt_components` SDK is the only supported Python API. The old
`registry.py`, `schema_validator.py`, `component_models.py`, and
`component_errors.py` placeholders have been removed.

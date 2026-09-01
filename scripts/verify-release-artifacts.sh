#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
VERSION="$("$ROOT/scripts/verify-release-version.sh")"
ARTIFACTS="$ROOT/release"

cd "$ROOT"
"$ROOT/scripts/build-release-artifacts.sh"

cd "$ARTIFACTS"
sha256sum --check SHA256SUMS

NPM_PACKAGE="$ARTIFACTS/wingspan-technology-efficio-pptx-contracts-$VERSION.tgz"
WHEEL="$ARTIFACTS/efficio_pptx_contracts-$VERSION-py3-none-any.whl"

UNEXPECTED_NPM_FILES="$(tar -tzf "$NPM_PACKAGE" | grep -Ev '^package/(package.json|README.md|dist(/.*)?)$' || true)"
if [[ -n "$UNEXPECTED_NPM_FILES" ]]; then
  printf 'Unexpected files in npm package:\n%s\n' "$UNEXPECTED_NPM_FILES" >&2
  exit 1
fi

mkdir -p "$WORK/node-consumer"
cd "$WORK/node-consumer"
npm init --yes >/dev/null
npm install --ignore-scripts "$NPM_PACKAGE" >/dev/null
node --input-type=module -e '
  const sdk = await import("@wingspan-technology/efficio-pptx-contracts/editor");
  const types = sdk.listComponentTypes();
  if (!types.includes("text") || !types.includes("table") || !types.includes("category_chart")) {
    throw new Error(`Unexpected component types: ${JSON.stringify(types)}`);
  }
  if (sdk.DECK_SLIDE_SELECTION_GROUPS_TAG !== "efficio_slide_selection_groups") {
    throw new Error("Missing slide-selection group deck tag export.");
  }
'

uv venv --python 3.12 "$WORK/venv" >/dev/null
uv pip install --python "$WORK/venv/bin/python" "$WHEEL" >/dev/null
"$WORK/venv/bin/python" - <<'PY'
from importlib.resources import files

from efficio_pptx_contracts import (
    SlideSelectionGroupType,
    V2ComponentRepairReason,
    V2ComponentSemanticFinding,
    V2SemanticRule,
    build_v2_component_contract,
    list_component_types,
    load_component_instructions,
    normalize_v2_component_content,
    normalize_slide_selection_groups,
    parse_slide_selection_groups,
    validate_slide_selection_group_selection,
    validate_v2_component_semantics,
    validate_v2_executable_component_schema,
)

component_types = list_component_types()
assert {"text", "table", "category_chart"}.issubset(component_types)
assert load_component_instructions()["component_instructions"]
assert files("efficio_pptx_contracts").joinpath("_generated/component-registry.json").is_file()

selection_groups = parse_slide_selection_groups(
    [
        {
            "group_id": "group_release",
            "name": "Release smoke",
            "type": "choice",
            "inclusion_policy": "when_relevant",
            "members": ["slide_001", "slide_002"],
        }
    ]
)
assert selection_groups[0].group_type is SlideSelectionGroupType.CHOICE
selection_registry = normalize_slide_selection_groups(
    selection_groups,
    slide_inclusion_policies={
        "slide_001": "when_relevant",
        "slide_002": "when_relevant",
    },
)
assert validate_slide_selection_group_selection(selection_registry, ["slide_001"]) == ()

text_contract = build_v2_component_contract(
    "text",
    {
        "efficio_render_behavior": "render_by_component_type",
        "efficio_component_id": "release_smoke",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_chars": "40",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
        "efficio_min_chars_per_item": "1",
        "efficio_max_chars_per_item": "40",
    },
)
content = {"items": ["Release smoke"]}
validate_v2_executable_component_schema(
    text_contract["output_schema"], require_prompt_profile=True
)
validate_v2_component_semantics("text", content, text_contract["normalization"])
assert normalize_v2_component_content(
    "text", content, text_contract["normalization"]
) == content
finding = V2ComponentSemanticFinding(
    path=("items",),
    cell=None,
    rule=V2SemanticRule.AGGREGATE_CHARACTER_LIMIT,
    reason=V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT,
)
assert finding.reason is V2ComponentRepairReason.AGGREGATE_CHARACTER_LIMIT
PY

printf 'Release artifacts verified.\n'

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
VERSION="$("$ROOT/scripts/verify-release-version.sh")"
ARTIFACTS="$ROOT/release"

shopt -s nullglob
RELEASE_NOTES=("$ROOT"/docs/releases/*-v"$VERSION"-*.md)
shopt -u nullglob
if [[ "${#RELEASE_NOTES[@]}" -ne 1 ]]; then
  echo "Expected exactly one docs/releases release note for version $VERSION." >&2
  exit 1
fi

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
  if (!types.includes("text") || !types.includes("table") || !types.includes("category_chart") || !types.includes("categorical_fill")) {
    throw new Error(`Unexpected component types: ${JSON.stringify(types)}`);
  }
  if (sdk.DECK_SLIDE_SELECTION_GROUPS_TAG !== "efficio_slide_selection_groups") {
    throw new Error("Missing slide-selection group deck tag export.");
  }
  if (sdk.DECK_CLASSIFICATION_SCHEMES_TAG !== "efficio_classification_schemes") {
    throw new Error("Missing classification-schemes deck tag export.");
  }
  if (sdk.SLIDE_ROLE_TAG !== "efficio_slide_role") {
    throw new Error("Missing slide role tag export.");
  }
  if (JSON.stringify(sdk.SLIDE_ROLES) !== JSON.stringify(["content", "separator"])) {
    throw new Error(`Unexpected slide roles: ${JSON.stringify(sdk.SLIDE_ROLES)}`);
  }
  if (sdk.getSlideTagDefaults().efficio_slide_role !== "content") {
    throw new Error("Slide role does not default to content.");
  }
  if (sdk.CURRENT_TEMPLATE_CONTRACT_REVISION !== 2) {
    throw new Error("Unexpected current template contract revision.");
  }
  const migration = sdk.planTemplateContractMigration([
    { target_ref: "deck", scope: "deck", tags: {} },
    {
      target_ref: "shape:1",
      scope: "shape",
      tags: { efficio_render_behavior: "render_by_component_type" },
    },
  ]);
  if (migration.patches.length !== 2) {
    throw new Error("Template contract migration planner is unavailable.");
  }
'

uv venv --python 3.12 "$WORK/venv" >/dev/null
uv pip install --python "$WORK/venv/bin/python" "$WHEEL" >/dev/null
"$WORK/venv/bin/python" - <<'PY'
from importlib.resources import files
import json

from efficio_pptx_contracts import (
    CLASSIFICATION_SCHEMES_TAG,
    CLASSIFICATION_SCHEME_ID_TAG,
    CURRENT_TEMPLATE_CONTRACT_REVISION,
    ContentMode,
    SlideSelectionGroupType,
    TemplateTagScope,
    TemplateTagTarget,
    V2ComponentRepairReason,
    V2ComponentSemanticFinding,
    V2SemanticRule,
    build_data_bound_component_contract,
    build_component_render_metadata,
    build_validation_content_schema,
    build_v2_component_contract,
    list_component_types,
    load_component_instructions,
    load_slide_tag_contract,
    normalize_v2_component_content,
    normalize_slide_selection_groups,
    parse_slide_selection_groups,
    parse_classification_schemes,
    plan_template_contract_migration,
    resolve_content_mode,
    validate_slide_selection_group_selection,
    validate_slide_tags,
    validate_v2_component_semantics,
    validate_v2_executable_component_schema,
    project_component_context,
)

component_types = list_component_types()
assert {"text", "table", "category_chart", "categorical_fill"}.issubset(component_types)
assert load_component_instructions()["component_instructions"]
assert files("efficio_pptx_contracts").joinpath("_generated/component-registry.json").is_file()

slide_contract = load_slide_tag_contract()
slide_role = slide_contract["tags"]["efficio_slide_role"]
assert slide_role["required"] is True
assert slide_role["enum"] == ["content", "separator"]
for role in slide_role["enum"]:
    assert validate_slide_tags(
        {
            "efficio_slide_id": "slide_001",
            "efficio_slide_role": role,
            "efficio_slide_placement": "body",
            "efficio_slide_inclusion_policy": "when_relevant",
        }
    ) == []

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
        "efficio_content_mode": "ai_generated",
        "efficio_component_id": "release_smoke",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "auto",
        "efficio_max_lines": "1",
        "efficio_estimated_chars_per_line": "40",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
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

classification_schemes = [
    {
        "scheme_id": "selection_state",
        "instruction": "Decide whether the option should be selected.",
        "palette_mode": "rgb",
        "cases": [
            {
                "case_id": "selected",
                "label": "Selected",
                "description": "The option should be highlighted.",
                "fill": {"value": "17365D"},
            },
            {
                "case_id": "unselected",
                "label": "Unselected",
                "description": "The option should remain inactive.",
                "fill": {"value": "BFBFBF"},
            },
        ],
    }
]
deck_tags = {CLASSIFICATION_SCHEMES_TAG: json.dumps(classification_schemes)}
fill_tags = {
    "efficio_content_mode": "ai_generated",
    "efficio_component_id": "option_one",
    "efficio_component_type": "categorical_fill",
    "efficio_content_role": "Option one",
    CLASSIFICATION_SCHEME_ID_TAG: "selection_state",
}
assert parse_classification_schemes(deck_tags[CLASSIFICATION_SCHEMES_TAG])[0].scheme_id == "selection_state"
fill_contract = build_v2_component_contract(
    "categorical_fill", fill_tags, deck_tags=deck_tags
)
assert fill_contract["output_schema"]["properties"]["case_id"]["enum"] == [
    "selected",
    "unselected",
]
assert build_validation_content_schema(
    "categorical_fill", fill_tags, deck_tags=deck_tags
) == {
    "type": "object",
    "properties": {
        "case_id": {"type": "string", "enum": ["selected", "unselected"]}
    },
    "required": ["case_id"],
    "additionalProperties": False,
}
assert "'fill':" not in str(
    project_component_context("categorical_fill", fill_tags, deck_tags=deck_tags)
)
assert build_component_render_metadata(
    "categorical_fill", fill_tags, deck_tags=deck_tags
)["cases"]["selected"]["fill"] == {"kind": "rgb", "value": "17365D"}
fill_data_bound = build_data_bound_component_contract(
    "categorical_fill",
    {**fill_tags, "efficio_content_mode": "data_bound"},
    deck_tags=deck_tags,
)
assert normalize_v2_component_content(
    "categorical_fill",
    {"case_id": "selected"},
    fill_contract["normalization"],
) == {"case_id": "selected"}
assert fill_data_bound["submission_schema"]["properties"]["case_id"]["enum"] == [
    "selected",
    "unselected",
]
finding = V2ComponentSemanticFinding(
    path=("items",),
    cell=None,
    rule=V2SemanticRule.ESTIMATED_LINE_LIMIT,
    reason=V2ComponentRepairReason.ESTIMATED_LINE_LIMIT,
)
assert finding.reason is V2ComponentRepairReason.ESTIMATED_LINE_LIMIT

assert CURRENT_TEMPLATE_CONTRACT_REVISION == 2
assert resolve_content_mode({"efficio_content_mode": "data_bound"}) is ContentMode.DATA_BOUND
plan = plan_template_contract_migration(
    [
        TemplateTagTarget("deck", TemplateTagScope.DECK, {}),
        TemplateTagTarget(
            "shape:1",
            TemplateTagScope.SHAPE,
            {"efficio_render_behavior": "render_by_component_type"},
        ),
    ]
)
assert plan.from_revision == 0 and plan.to_revision == 2 and len(plan.patches) == 2
data_bound = build_data_bound_component_contract(
    "text",
    {
        "efficio_content_mode": "data_bound",
        "efficio_component_id": "release_smoke",
        "efficio_component_type": "text",
        "efficio_text_format": "plain",
        "efficio_sizing_mode": "manual",
        "efficio_max_lines": "1",
        "efficio_estimated_chars_per_line": "2",
        "efficio_min_items": "1",
        "efficio_max_items": "1",
    },
)
assert data_bound["submission_schema"]["properties"]["items"] == {
    "type": "array",
    "items": {"type": "string"},
    "minItems": 1,
}
PY

printf 'Release artifacts verified.\n'

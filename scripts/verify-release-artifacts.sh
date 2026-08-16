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

NPM_PACKAGE="$ARTIFACTS/efficio-pptx-contracts-$VERSION.tgz"
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
  const sdk = await import("@efficio/pptx-contracts/editor");
  const types = sdk.listComponentTypes();
  if (!types.includes("text") || !types.includes("table") || !types.includes("category_chart")) {
    throw new Error(`Unexpected component types: ${JSON.stringify(types)}`);
  }
'

uv venv --python 3.12 "$WORK/venv" >/dev/null
uv pip install --python "$WORK/venv/bin/python" "$WHEEL" >/dev/null
"$WORK/venv/bin/python" - <<'PY'
from importlib.resources import files

from efficio_pptx_contracts import list_component_types, load_component_instructions

component_types = list_component_types()
assert {"text", "table", "category_chart"}.issubset(component_types)
assert load_component_instructions()["component_instructions"]
assert files("efficio_pptx_contracts").joinpath("_generated/component-registry.json").is_file()
PY

printf 'Release artifacts verified.\n'

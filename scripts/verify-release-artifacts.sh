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
# Copy the checker beside the installed package so Node resolves the import
# through the freshly installed tarball, not this repository.
cp "$ROOT/scripts/verify-installed-editor.mjs" "$WORK/node-consumer/"
cd "$WORK/node-consumer"
npm init --yes >/dev/null
npm install --ignore-scripts "$NPM_PACKAGE" >/dev/null
node "$WORK/node-consumer/verify-installed-editor.mjs"

uv venv --python 3.12 "$WORK/venv" >/dev/null
uv pip install --python "$WORK/venv/bin/python" "$WHEEL" >/dev/null
"$WORK/venv/bin/python" "$ROOT/scripts/verify-installed-python-sdk.py"

printf 'Release artifacts verified.\n'

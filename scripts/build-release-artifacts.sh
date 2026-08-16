#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT="$ROOT/release"
VERSION="$("$ROOT/scripts/verify-release-version.sh")"

cd "$ROOT"
rm -rf "$OUTPUT"
mkdir -p "$OUTPUT"

npm pack --pack-destination "$OUTPUT" >/dev/null
uv build --out-dir "$OUTPUT" >/dev/null
rm -f "$OUTPUT/.gitignore"

NPM_PACKAGE="wingspan-technology-efficio-pptx-contracts-$VERSION.tgz"
PYTHON_SDIST="efficio_pptx_contracts-$VERSION.tar.gz"
PYTHON_WHEEL="efficio_pptx_contracts-$VERSION-py3-none-any.whl"

for artifact in "$NPM_PACKAGE" "$PYTHON_SDIST" "$PYTHON_WHEEL"; do
  if [[ ! -f "$OUTPUT/$artifact" ]]; then
    printf 'Expected release artifact was not built: %s\n' "$artifact" >&2
    exit 1
  fi
done

cd "$OUTPUT"
sha256sum "$NPM_PACKAGE" "$PYTHON_SDIST" "$PYTHON_WHEEL" > SHA256SUMS

ARTIFACT_COUNT="$(find . -maxdepth 1 -type f | wc -l)"
if [[ "$ARTIFACT_COUNT" -ne 4 ]]; then
  printf 'Unexpected files were created in %s.\n' "$OUTPUT" >&2
  find . -maxdepth 1 -type f -print >&2
  exit 1
fi

printf 'Release artifacts built in %s\n' "$OUTPUT"

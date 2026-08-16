#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

NPM_VERSION="$(node -p "require('./package.json').version")"
PYTHON_VERSION="$(python - <<'PY'
from pathlib import Path
import tomllib

metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(metadata["project"]["version"])
PY
)"

if [[ "$NPM_VERSION" != "$PYTHON_VERSION" ]]; then
  printf 'Release version mismatch: npm=%s, python=%s\n' "$NPM_VERSION" "$PYTHON_VERSION" >&2
  exit 1
fi

if [[ $# -gt 1 ]]; then
  printf 'Usage: %s [vVERSION]\n' "$0" >&2
  exit 1
fi

if [[ $# -eq 1 && "$1" != "v$NPM_VERSION" ]]; then
  printf 'Release tag %s does not match package version v%s.\n' "$1" "$NPM_VERSION" >&2
  exit 1
fi

printf '%s\n' "$NPM_VERSION"

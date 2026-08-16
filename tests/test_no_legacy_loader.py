"""Guards that the legacy src/schema_loader.py path stays retired.

The only supported Python contract API is the efficio_pptx_contracts SDK.
"""

from __future__ import annotations

from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parents[1]


def test_legacy_schema_loader_is_removed() -> None:
    assert not (PKG_ROOT / "src" / "schema_loader.py").exists()


def test_no_schema_loader_references_in_package_source() -> None:
    # Scan the SDK package and the remaining src scaffolds (not tests/docs).
    offenders = [
        str(py.relative_to(PKG_ROOT))
        for py in (PKG_ROOT / "src").rglob("*.py")
        if "schema_loader" in py.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"stale schema_loader references: {offenders}"

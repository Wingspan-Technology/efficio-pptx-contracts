"""Package metadata must identify one synchronized SDK release."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_package_names_and_versions_are_synchronized() -> None:
    package_json = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert package_json["name"] == "@wingspan-technology/efficio-pptx-contracts"
    assert pyproject["project"]["name"] == "efficio-pptx-contracts"
    assert package_json["version"] == pyproject["project"]["version"]
    assert package_json["repository"]["url"] == (
        "git+https://github.com/Wingspan-Technology/efficio-pptx-contracts.git"
    )
    assert package_json["publishConfig"]["registry"] == "https://npm.pkg.github.com"
    assert pyproject["project"]["urls"]["Repository"] == (
        "https://github.com/Wingspan-Technology/efficio-pptx-contracts"
    )

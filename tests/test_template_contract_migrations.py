"""Python migration planner contract and parity-fixture coverage."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from efficio_pptx_contracts import (
    CURRENT_TEMPLATE_CONTRACT_REVISION,
    RenameTagOperation,
    TEMPLATE_CONTRACT_REVISION_TAG,
    TemplateContractMigrationPlan,
    TemplateContractMigrationError,
    TemplateTagScope,
    TemplateTagTarget,
    get_template_contract_migration_path,
    load_template_contract_migration_catalog,
    plan_template_contract_migration,
)

FIXTURE = Path(__file__).parent / "fixtures" / "template-contract-migration-cases.json"


def _targets(raw: list[dict[str, object]]) -> list[TemplateTagTarget]:
    return [
        TemplateTagTarget(
            target_ref=str(item["target_ref"]),
            scope=TemplateTagScope(str(item["scope"])),
            tags=item["tags"],  # type: ignore[arg-type]
        )
        for item in raw
    ]


def _plan_dict(plan: TemplateContractMigrationPlan) -> dict[str, object]:
    return {
        "from_revision": plan.from_revision,
        "to_revision": plan.to_revision,
        "patches": [
            {
                "target_ref": patch.target_ref,
                "scope": str(patch.scope),
                "set_tags": dict(patch.set_tags),
                "remove_tags": list(patch.remove_tags),
            }
            for patch in plan.patches
        ],
    }


def test_catalog_is_contiguous_immutable_and_derived() -> None:
    catalog = load_template_contract_migration_catalog()
    assert catalog.current_revision == CURRENT_TEMPLATE_CONTRACT_REVISION == 1
    assert catalog.revision_tag == TEMPLATE_CONTRACT_REVISION_TAG
    assert [(item.from_revision, item.to_revision) for item in catalog.migrations] == [
        (0, 1)
    ]
    assert get_template_contract_migration_path(0) == catalog.migrations
    rename = catalog.migrations[0].operations[2]
    assert isinstance(rename, RenameTagOperation)
    with pytest.raises(TypeError):
        rename.value_map["x"] = "y"  # type: ignore[index]


def test_python_planner_matches_shared_success_fixtures_without_mutation() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in fixture["successful_cases"]:
        raw = case["targets"]
        before = deepcopy(raw)
        assert _plan_dict(plan_template_contract_migration(_targets(raw))) == case["expected"]
        assert raw == before, case["name"]


def test_python_planner_matches_shared_error_fixtures() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in fixture["error_cases"]:
        with pytest.raises(TemplateContractMigrationError) as caught:
            plan_template_contract_migration(_targets(case["targets"]))
        assert case["error_contains"] in str(caught.value), case["name"]


@pytest.mark.parametrize("revision", ["", " 1", "1.0", "-1", "true"])
def test_planner_rejects_malformed_revision_strings(revision: str) -> None:
    with pytest.raises(TemplateContractMigrationError, match="integer string"):
        plan_template_contract_migration(
            [
                TemplateTagTarget(
                    "deck",
                    TemplateTagScope.DECK,
                    {TEMPLATE_CONTRACT_REVISION_TAG: revision},
                )
            ]
        )


def test_planner_rejects_future_revision_and_duplicate_targets() -> None:
    with pytest.raises(TemplateContractMigrationError, match="newer than supported"):
        plan_template_contract_migration(
            [
                TemplateTagTarget(
                    "deck",
                    TemplateTagScope.DECK,
                    {TEMPLATE_CONTRACT_REVISION_TAG: "2"},
                )
            ]
        )
    with pytest.raises(TemplateContractMigrationError, match="unique"):
        plan_template_contract_migration(
            [
                TemplateTagTarget("deck", TemplateTagScope.DECK, {}),
                TemplateTagTarget("deck", TemplateTagScope.DECK, {}),
            ]
        )

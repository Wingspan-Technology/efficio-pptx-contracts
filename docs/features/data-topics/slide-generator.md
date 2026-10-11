# Named Data Topics: Slide Generator Handoff

Read the [feature overview](README.md) for authoritative shapes and SDK behavior.
This is Python-service integration, not a requirement to build AI source retrieval.

## Status And Consumer Location

Import validation, normalized catalog publication, and typed catalog reading
are prepared in the separate Slide Generator repository and verified against
the built `0.10.0` wheel. Published-pin adoption and normal validation follow
publication; deployment is separate. DMS and AI conversation changes are not included.

Inspected checkout on 2026-10-12:
`/home/Ivan/dev/projects/efficio/rfp-document-generator/cdt-slide-generator`.
Paths below are relative to that repository; recheck them for later implementations.

## Release Adoption

After upstream publication:

1. Verify the public `0.10.0` wheel against the release's `SHA256SUMS`.
2. Update `pptx-contracts.lock.json`: exact tag, package version, filename, and
   published SHA-256. Do not substitute an unpublished local artifact.
3. Align the root `pyproject.toml` wheel source and direct pins in
   `apps/orchestrator-api/pyproject.toml`, importer `pyproject.toml`, and
   generation `pyproject.toml`.
4. Update literal paths in both `Dockerfile` and
   `apps/orchestrator-api/Dockerfile`, `.dockerignore`, and
   `scripts/check-generation-aspose.sh`.
5. Fetch via `scripts/fetch-pptx-contracts.sh`, regenerate `uv.lock`, then run
   `scripts/check-contracts.sh` and `scripts/check-all.sh` under a timeout.

Import public APIs from `efficio_pptx_contracts`, as listed in the overview.
Do not duplicate rules, alias sibling SDK source, or alter verified release caches.

## What The Service Must Do

- Apply the shared migration before discovery and validation.
- Validate deck and slide tags with shared SDK validators, passing deck context
  for assigned slides. Reject invalid references before any artifact write.
- Parse and normalize once into importer-owned typed values after validation.
- Publish definitions as catalog `data_topics`; publish assigned IDs as per-slide
  `data_topic_ids`. Remove the raw assignment tag from catalog `tags`.
- Omit topics for an empty registry and IDs for unassigned slides. Templates with
  no topics keep their previous catalog shape.
- Retain typed metadata in the generation catalog reader, validating explicit
  optional fields and references rather than silently dropping malformed input.

Raw `slide-selection-catalog.json` example:

```json
{
  "data_topics": [{"topic_id": "topic_baseline", "name": "Baseline Spend"}],
  "slides": {
    "slide_001": {
      "slide_index": 0,
      "tags": {"efficio_slide_id": "slide_001"},
      "data_topic_ids": ["topic_baseline"]
    },
    "slide_002": {"slide_index": 1, "tags": {"efficio_slide_id": "slide_002"}}
  }
}
```

The existing `slide-selection-ai-input.json` envelope embeds this unchanged under
`catalog`. `GET /api/templates/{template_id}/slide-catalog` and
`GET /api/templates/{template_id}/versions/{version}/slide-catalog` retain these
fields in the published envelope. No request field, route, or generated AI
instruction is added. Clients may use or ignore the advisory catalog metadata.

Selected-slide order, rendering, generation submissions, limits, and repairs
are unchanged. Per-slide `ai.json`, `private.json`, `validation.json`, and
`generation-v2.json` retain their shapes. Topics must not become implicit
selection filters, mandatory source requirements, or content constraints.

## Migration And Deployment

Revision `4 -> 5` changes only the marker: no backfill, no presentation-content
changes, and existing topic values preserved. The importer owns working-copy
mutation and verified save/readback before publishing a new immutable source.
Historic published versions are not rewritten in place.

The deployment sweep compares template and artifact revisions independently.
No artifact-bundle bump is needed solely to trigger revision-5 refresh. The sweep
rebuilds each outdated template's latest successful published source, not all
historical versions or unimported uploads. Current templates and repeat sweeps skip.

The inspected dev/test/staging CI rolls out the service first, then runs Alembic
and re-import using the same task-definition revision. Any migration/import
failure returns nonzero and fails the deployment job; the new service is already
deployed. There is no automatic rollback or pre-rollout guarantee. Manual jobs
use `allow_failure: true`, so failure need not fail the pipeline. Recheck the
actual environment flow before promising production behavior.

## Relevant Consumer Files

| Path | Responsibility / Required Extension |
| --- | --- |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/validation/template_validation.py` | Shared validation with deck context. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/validation/data_topics.py` | Prepared topic normalization. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/domain/models.py` | Prepared normalized topic values. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/application/import_service.py` | Validation/normalization before publication. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/artifacts/slide_selection_catalog.py` | Normalized optional catalog projection. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/artifacts/slide_selection_ai_input.py` | Unchanged envelope wrapping. |
| `packages/efficio-ppt-template-importer/src/efficio_ppt_template_importer/adapters/aspose_template_migration.py` | SDK patch application and readback. |
| `packages/efficio-ppt-generation/src/efficio_ppt_generation/artifacts/models.py`, `packages/efficio-ppt-generation/src/efficio_ppt_generation/artifacts/slide_selection_catalog.py` | Typed metadata retention and validation. |
| `apps/orchestrator-api/src/orchestrator_api/core/template_reimports.py` | Latest-source revision comparison and skip/retry semantics. |
| `apps/orchestrator-api/src/orchestrator_api/jobs/template_reimport.py` | Locked sweep through the normal importer. |
| `apps/orchestrator-api/src/orchestrator_api/reimport_outdated_templates.py` | Nonzero exit on failed sweep. |
| Parent repository `.gitlab-ci.yml` | Real rollout sequencing and environment gates. |

## Acceptance And Verification

- Legacy catalogs remain unchanged; topics and ordered assignments round-trip
  through import and both catalog routes without duplicate raw tags.
- Invalid JSON, extra fields, duplicate/unknown IDs, blank/empty assignments, and
  malformed explicit published fields fail; an invalid import writes no artifacts.
- Selection order, generation instructions, rendering inputs, and content schemas
  are unchanged by topics.
- Revision-4 files with/without topics save/reopen at 5, preserve content/tags,
  and do not save on a second migration.
- An outdated latest source refreshes once and is skipped subsequently.

Tests: importer `tests/test_data_topic_artifacts.py`,
`tests/test_template_contract_migration.py`, and
`tests/test_template_contract_migration_aspose.py`; generation
`tests/test_data_topic_catalog.py`; orchestrator `tests/test_generation_routes.py`
and `tests/test_template_reimports.py`.

Built-wheel evidence: 340 generation, 177 importer, and 1,642 API tests passed
with environment-gated skips; three native migration checks passed on Python
3.12/Aspose 26.8.0. Run normal full validation again after published adoption.
These checks are not proof of migrated templates in live AWS.

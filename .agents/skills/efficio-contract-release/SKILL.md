---
name: efficio-contract-release
description: Prepare, validate, publish, and verify exact Efficio contracts SDK releases and consumer adoption while preserving dirty worktrees and reviewed shared branches.
---

# Contracts Releases

Use for version bumps, finalization, tagging, publication, and adoption.
Preparation does not authorize external mutations; follow the requested scope.
Read repository paths from repository root.

## Prepare

- Read `README.md`, `.github/workflows/{ci,release}.yml`, and
  `scripts/{verify-release-version,verify-release-artifacts,build-release-artifacts}.sh`.
- Inspect status, branch, remote ancestry, tags, and release state. Preserve
  unrelated edits and exclude them from scoped commits and release content.
- Align `package.json`, `package-lock.json`, `pyproject.toml`, and regenerated
  `uv.lock`; both SDKs publish the same exact version.
- Run the development skill's full checks, generation, and installed-artifact
  proof. Check source size, scoped diff, and generated reproducibility.
- Complete the feature-handoff skill for every affected feature. Create exactly
  one `docs/releases/YYYY-MM-DD-HHMM-vX.Y.Z-short-topic.md` for the version,
  using UTC. Link affected feature folders and record compatibility, consumer
  work, validation results, and truthful publication status.
- Never replace an existing immutable release/tag or publish different contents
  under an already published version.

## Publish When Authorized

1. Fetch current `origin/main`; use a scoped branch without losing dirty work.
   Stage only owned files and use the human author's normal Git identity.
2. Create a GitHub pull request, inspect CI and branch policy, and merge through
   the allowed reviewed flow. Do not bypass protections.
3. Verify remote `main` contains the reviewed changes. Create the matching
   annotated `vX.Y.Z` tag on that exact commit and push only that tag.
4. Follow the existing Release workflow: version/generation validation,
   artifact checks, installed SDK smoke checks, npm publication to GitHub
   Packages, and the public wheel/source assets plus `SHA256SUMS`.
5. Verify completed workflow, tag target, published assets, package version,
   downloaded checksums, and isolated installed-package behavior independently.
   A local build is not publication proof.
6. Update release status with primary evidence after publication, preserving
   historical decisions; use a scoped docs PR when needed.

After an uncertain mutating command, inspect remote state before retrying.
For partial publication, identify exactly what is public and follow safe
workflow recovery; do not delete or recreate released tags to hide the failure.

## Consumer Adoption

Publish upstream first. Use published assets/checksums, never sibling source
aliases or local-wheel injection into a verified release cache.

- Slide Generator: follow the feature's `slide-generator.md`; align release lock,
  direct Python pins, literal image/check paths, and regenerated `uv.lock`, then
  run its normal full repository gate.
- Template Editor: follow `template-editor.md`; use the exact private npm release
  through `/editor` and its own system-level dependency/Office validation.
- Do not publish or deploy a consumer unless the user requested it.

## Finish

Report release URL/tag SHA, remote and installed-artifact evidence, feature-doc
locations, adoption actually completed, and remaining consumer/deployment work.
Do not attribute commits or artifacts to tooling.

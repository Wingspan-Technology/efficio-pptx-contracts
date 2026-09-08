# Contract release notes

This directory contains timestamped implementation handoffs for contract releases.
The notes are written for engineers and agents updating downstream consumers such
as the Template Editor and Slide Generator.

Use the filename format:

```text
YYYY-MM-DD-HHMM-vX.Y.Z-short-topic.md
```

The timestamp is UTC. A release note must be created before its package is tagged
or published to GitHub. Each note must state:

- why the contract changed;
- the completed contract behavior;
- compatibility and migration behavior;
- concrete work required in each affected consumer;
- verification completed in the contracts repository.

The release is not ready to publish until its note records the intended package
version, template contract revision, compatibility impact, consumer work, and
completed verification. After publication, update its release status without
rewriting the historical contract decisions.

`npm run release:verify` enforces exactly one matching release note for the
package version before it builds the publishable artifacts.

These notes explain a release, but they are not a second contract definition.
The authored files under `contracts/` remain authoritative, generated files must
still be rebuilt, and consumers must use the published SDK rather than reading
authored or generated internals directly.

## Releases

- [0.8.0 — strict character limits](2026-09-08-0705-v0.8.0-strict-character-limits.md)
- [0.7.0 — template-authored slide archetypes](2026-09-07-1703-v0.7.0-slide-archetypes.md)
- [0.6.1 — plain-text capacity migration correction](2026-09-07-1053-v0.6.1-plain-text-capacity-migration.md)
- [0.6.0 — text capacity and categorical fill](2026-09-06-1859-v0.6.0-text-capacity-and-categorical-fill.md)

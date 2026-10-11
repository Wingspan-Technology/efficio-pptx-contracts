# Contract Features

Each feature has a stable name and dedicated folder containing `README.md`,
`slide-generator.md`, and `template-editor.md`. The overview explains intent,
exact technical behavior, compatibility, relevant files, and verification;
the two separate handoffs explain how each consumer must match the feature.

Follow the [mandatory feature skill](../../.agents/skills/efficio-contract-feature-handoff/SKILL.md)
and [repository rules](../../AGENTS.md). These documents do not replace authored
contracts or timestamped [release notes](../releases/README.md).

| Feature | Package | Template Revision | Consumer Handoffs |
| --- | --- | --- | --- |
| [Named Data Topics](data-topics/README.md) | `0.10.0` | `5` | [Slide Generator](data-topics/slide-generator.md), [Template Editor](data-topics/template-editor.md) |

The workflow applies to new features and follow-up changes to named features.
Earlier features retain their historical release notes; this index does not
claim they were retroactively reimplemented or documented in the new format.

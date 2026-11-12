# Provider role policy - draft (WP2)

Status: draft, not approved. Baseline: main @ 2026-10-26.
Author: AI-CEO. Reviewers: Codex, Claude. Merge: owner.

`docs/PROVIDERS_INVENTORY.md` records what is connected. This file records
what each provider is allowed to do. That is a policy question, not a
connection question, and the two must not be confused.

## Roles (hypotheses until the bake-off runs)

| Role | Primary | Backup | Why |
|---|---|---|---|
| Intake questions | Gemini Flash | Venice | cheap, no taste needed |
| Spec decomposition | Claude | GPT | long instructions, taste |
| Code generation | Claude | GPT | proven pair |
| Code review | GPT | Gemini | must differ from the builder |
| Assets: image | Venice | xAI | uncensored, single key |
| Assets: video | Venice | xAI | quality vs speed |
| Voice / TTS | Venice | - | present in catalog |
| Music / songs | MISSING | - | needs a separate engine |
| Final judge / QA | Gemini | GPT | must not judge its own output |
| Router and cost control | code | - | not an LLM |

## Non-negotiable

1. No provider is the sole judge of its own output.
2. No provider enters the registry without a price row and a licence check.
3. A provider that cannot produce a rights-clean artefact is excluded.
4. Prices are keyed by (provider, model). Model id alone is ambiguous:
   Venice and Anthropic share Claude model ids.

## Bake-off metrics (harness not built)

first-pass acceptance rate; repair rounds to green; cost per accepted
artefact; wall clock; rejection rate on 10 deliberately edgy briefs;
determinism; licence cleanliness.

Admission bar: wins at least one role on cost-per-accepted without losing
on acceptance rate.
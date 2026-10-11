# Wave A — baseline and source of truth (2026-10-11)

Read-only discovery done before any Wave A change. The historical references
(`claude/g0-baseline-2026-10-09` @ `c874998`, `milestone/pre-staging-2026-10-05`
@ `67a0765`) were treated as inputs and re-verified, not assumed.

## Repository state (git fetch of all 25 remote heads)

| Ref | SHA | Committed (UTC) | Relation |
|---|---|---|---|
| `claude/g0-baseline-2026-10-09` | `c874998` | 2026-10-10 22:13 | 1 commit on top of `67a0765` (docs, evidence registry, regenerated registries only) |
| `chatgpt/release-policy-fail-closed-2026-10-11` (PR #7, open) | `223206d` | 2026-10-10 21:25 | 3 commits on top of `67a0765`: fail closed when the quality report is missing; enforced visual failures are mandatory. CI green (v24-ci 38087621415, V11 38087621378) |
| `milestone/pre-staging-2026-10-05` (integration) | `67a0765` | 2026-10-10 20:15 | ancestor of both branches above |
| `docs/partner-review-gap-map-2026-10-09` | `40cdb61` | 2026-10-08 23:23 | 1 docs-only commit (`docs/PARTNER_REVIEW_GAP_MAP_HE.md`), not merged; no code |
| `feature/{infisical,r2,qstash}-…-2026-10-06` | — | 2026-10-06 | content present in `67a0765` (file-identical); PRs #2–#4 merged before the integration branch history was rewritten (no merge base) |
| `main`, `milestone/pre-staging-2026-10-05-{final,source,upload,work}`, `tmp/*` | `e8f2949` | 2026-09-22 | old; not a base, not a merge target |

Working tree at start: clean.

## Deployed runtime

| Surface | What runs | Evidence |
|---|---|---|
| Worker (Oracle host, self-hosted runner) | `67a0765` | deploy-worker run 38083162363 (success); worker writes `OMNI_SOURCE_COMMIT=$GITHUB_SHA` |
| Vercel `148aiv28` — Preview, integration branch | `67a0765` (`dpl_6efTDg9LK2JsXYHvMds5TZxJ9mpu`, READY) | Vercel deployments list |
| Vercel `148aiv28` — Preview, task branch | `c874998` (`dpl_73zkTZjAsYHz1166VT5iwoq1gmh1`, READY) | same |
| Vercel `148aiv28` — Preview, PR #7 | `223206d` READY; `8f0f72c` ERROR (failing tests commit) | same |
| Vercel `148aiv28` — **target=production** | **`e8f2949` (old `main`, 2026-09-22)** | 3 production deployments, all `main` @ `e8f2949` |
| Vercel `148ai` (old project) | ignored by founder decision | — |

A READY Vercel deployment proves the bundle built, not that the product works.
The last real-server verification runs are on `67a0765`: free checks 38083312245
(18/18), gate replay 38083647077, verify replay 38083686082, economics 38083624196.

## Latest successful CI

`c874998`: v24-ci 38090586855, V11 38090586913 (both success).
`223206d` (PR #7): v24-ci 38087621415 success.

## Chosen base for Wave A

`claude/wave-a-intelligence-platform-2026-10-11` = `c874998` + merge of PR #7
(`223206d`), merge commit `c20503a`. Reasons: `c874998` is the newest validated
Claude state (docs/evidence on top of the deployed `67a0765`); PR #7 is a
small, CI-green fail-closed fix on the same base with no conflicts, and Wave A
builds on the release policy it hardens. Nothing was rebased, reset or force
pushed; PR #7 stays open and can still be merged on its own. The partner gap
map branch is docs-only and was left untouched.

## Test baseline on the base (`c20503a`)

Local (no PyPI access; fastapi/boto3/httpx fetched from their GitHub sources
for the full run): see `STATUS.md` Wave A section for the exact numbers and
the environment-only failures. CI (`v24-ci`, pinned requirements) is the
authority.

## Known blockers at baseline (unchanged by Wave A)

- Paid 10-build Golden E2E gate (≥90 %): NOT RUN (budget not approved).
- OpenAI (HTTP 429 no credits) and Anthropic (HTTP 400 credit balance) accounts
  have no credit: no second provider, no independent model review.
- Gemini invoice reconciliation: needs the billing export (founder).
- No LLM key on Vercel: live AI conversation in the API is not possible today.
- Contrast/label WCAG rules advisory pending a founder decision.

## Pending migrations

`036_intelligence_plane.sql` (Wave A, additive: provider_health,
intake_messages, execution_plans). Applied by the deploy-worker workflow only
when the integration branch moves; not applied to any shared database by
this work.

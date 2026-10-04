# M5-UX01 — creator golden-path workspace evidence (2026-10-04)

Scope: LOCAL ONLY, memory persistence. The real `omni_prod.investor_app` route functions were served through a scratchpad Starlette adapter (the fastapi wheel is not installable in the implementer sandbox) and driven with headless Chromium 141. No durable backend, preview router, model provider or image provider was configured, so no real build, preview, modification or download could complete here.

## Verified in the browser
- Signed-out page: Hebrew RTL default, honest scope copy ("web apps and SaaS; mobile, games and media not available yet"), no "Build anything". `ux01/01_signed_out_he.png`
- Register with email/password -> workspace; first-project form -> project created and selected.
- Prompt -> **plan + quote** via `POST /api/v28/projects/{id}/build-contracts`: understood product, roles, data, integrations, grouped capabilities, per-kind infrastructure readiness, estimate and approved maximum, named blockers with operator details. Confirm button disabled because blockers exist (durable backend, generated-app infrastructure, image provider). `ux01/07_plan_viewport.png`
- Publish shows "Publishing is not configured on this server yet" and never claims a deploy.
- English toggle switches to LTR. `ux01/04_plan_en.png`
- 390px mobile: no horizontal scroll (scrollWidth 390). `ux01/06_mobile_plan.png`

## Implemented but not exercised end to end here (needs durable backend)
Build polling with real worker phases (PLANNING / INFRASTRUCTURE / ASSETS / GENERATING / VERIFYING), automatic preview launch and iframe (CSP frame-src limited to the PREVIEW_DOMAIN_TEMPLATE wildcard), modification request -> review -> accept/reject, version list with rollback, ZIP download via authenticated fetch, evidence drawer (gates, repair rounds, request IDs, tokens, actual cost or "cannot be calculated").

## Found while testing (pre-existing, not fixed here)
The existing unified planner matches targets by substring: an English prompt containing "appointments" produced an `Android source target` requirement, which would block a web build as an unconfigured external capability.

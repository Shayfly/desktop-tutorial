# 148AI System Completion Implementation Plan — תוכנית המשך עד השקה

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. משימות אלה יבוצעו בסבב העבודה הבא; הסבב הנוכחי הוא סקירה ושמירת מסמכים בלבד. אין חובה להפעיל subagents.

**Goal:** להשלים Web/SaaS אמיתי: חשבון → בקשה → חוזה ועלות → יצירת קוד ונכסים → תשתית מבודדת → build/test/repair → preview → שינוי וגרסה → export/publish → חיוב, ניטור ושחזור מוכחים.

**Architecture:** נשמרים ה־FastAPI/V28 והמסלול האסינכרוני `/builds`. Vercel ממשק/control plane; Neon/R2/Redis שומרים מצב durable. עובד חיצוני והרצה מבודדת אינם בתוך בקשת הממשק. Infisical שומר סודות של המוצרים הנוצרים; Neon ו־R2 שלהם מופרדים מהפלטפורמה.

**Tech Stack:** Python 3.12 ב־CI, FastAPI, psycopg, PostgreSQL/Neon, Redis/RQ, boto3/R2, Infisical Universal Auth/v4, existing provider/contracts/cost/evidence layer, Vercel web/API. ספק model/image ו־worker host נבחרים ומאומתים לפני חיוב.

**Spec:** `PRODUCT_MISSION_AND_ACCEPTANCE.md`; `docs/superpowers/specs/2026-10-04-m5-production-vertical-slice-design.md`; המצב בפועל והחריגים ב־`docs/148AI_SYSTEM_AUDIT_AND_HANDOFF_2026-10-06_HE.md`. תוכנית זו משלימה את תוכנית M5 הקיימת; אינה מבטלת את ה־security/infrastructure floor שלה.

## Global Constraints

- `M5_PARTIAL` עד external staging proofs. שום enum/adapter/key/plan לבדו אינו LIVE.
- Source baseline: `79b9ba785aff5e2c29c068ade94bbdf2f24d8f33`; branch `milestone/pre-staging-2026-10-05`.
- אין להחליף OMNI_DATABASE_URL ב־GENAPP DSN, אין rerun bootstrap ריק, ואין register מחדש כדי לעקוף חשבון קיים.
- Secrets אינם בצ'אט/Git/log/export. refs/status בלבד יוצאים מ־control plane.
- `UNKNOWN is never zero`; `actual=NULL` אינו estimate. reservation לפני paid effects.
- תשתית generated app מבודדת per tenant/project/environment; operator keys אינם נמסרים ל־app.
- generated code אינו רץ ב־API process ולא מקבל host Docker socket, credentials של הפלטפורמה או תור RQ.
- public ready מחייב את קריטריוני המשימה, כולל שני משתמשים ושלושה apps ממשיים.
- Native/mobile/media expansion נשאר scope נפרד אחרי Web verified; אין להצהיר על apps חתומים.
- אין יצירת שירות בתשלום בלי תקציב ומסלול מורשים. משימות חשבון שלא ניתן לבצע מהמאגר מרוכזות עבור שי.
- לא לשנות Production הלילה; כל implementation מבודד בענף, CI ו־Preview לפני promotion.

## Review Focus

1. credential פג/נשלל בין שתי בניות: בדיקת freshness/renewal, ללא reuse LIVE שקרי — Task 2.
2. worker קורס אחרי external side effect לפני כתיבת state: operation journal/idempotency, ללא double charge או orphan credential — Tasks 2, 8, 11.
3. owner A מנחש project/version/object/schema של B: DENY אמיתי, לא רק prefix convention — Tasks 4, 5, 13.
4. login401 או QUEUED ללא worker: שגיאה מדויקת והתאוששות, בלי „session expired”/progress מזויף — Tasks 1, 6, 7.
5. restore/rollback/promote משתמשים ב־source/DB/artifacts לא תואמים: גרסה/SHA/hash נעולים — Tasks 12, 15, 17.

---

## 1. סדר העבודה ותלות

| מסלול | משימות | תלות | תוצר |
|---|---|---|---|
| נעילת אמת ואבחון | 1–3 | בסיס קוד/CI | health/evidence ללא סימולציה |
| סודות ותשתית המוצר | 4–5, 9–10 | 2–3; חלק מה־probes עצמאיים | DB/R2/secret/scheduler/assets עובדים ומבודדים |
| תורי בנייה והרצה | 6–8 | host credentials; ניתן לפתח לצד adapters | worker/model/sandbox/preview פעילים |
| מסלול Web מלא | 11–13 | 4–10 + quotes | 3 apps, repair, persistence, versions/export/isolation |
| מסחרי ופרסום | 14–16 | 11–13 | auth lifecycle, billing, actual publish |
| מוכנות production | 17–18 | כל האמור | restore/rollback/alerts/release evidence |
| הרחבת המוצר | 19 | Web release | native ותחומי יצירה נוספים |

„עצמאיים” כאן פירושו שאפשר להכין בדיקות וקוד בלי לחכות ל־UI של ספק אחר, לא הרשאה אוטומטית לבצע side effects במקביל.

## 2. יעד הסבב הבא וזמנים

אין הבטחה לסיום מלא ביום אחד. התכנון לפי שעות הנדסיות ממוקדות, **אינו SLA**:

| חלון | יעד | טווח תכנון | תנאי עצירה |
|---|---|---:|---|
| פתיחה | אמת, baseline, מיפוי env שמות, health | 30–60 דקות | source שונה או config לא מוסבר |
| בלוק א׳ | תיקוני A1/A2/A3 + live Infisical/Neon | 2–4 שעות | אין credentials/runtime probe מאומת |
| בלוק ב׳ | R2 adapter והפרדה; worker/queue/sandbox ADR | 3–6 שעות | חסר host או delegation permission |
| בלוק ג׳ | model/image/scheduler + quotes, build ראשון | 3–6 שעות | עלות לא מאושרת או worker לא פעיל |
| אחריו | 3 prompts, edit/export/publish, reliability/commercial | כמה סבבים | כל gate חסר נשאר incomplete |

המטרה המקצועית לסבב הבא: לפחות להוכיח סודות+DB+אחסון ותשתית execution, ולהגיע לבנייה הראשונה אם host/providers זמינים. אם לא, לסיים adapters+tests ולהשאיר blocker אחד מדויק, בלי שעות של ניסוי UI.

## Task 1: baseline, inventory ו־runtime preflight

**Files**
- Modify: `omni_prod/investor_app.py`, `omni_prod/integration_center.py`, `omni_prod/worker_health.py`.
- Create: `scripts/run_m5_preflight.py`, `tests/test_m5_runtime_preflight.py`.
- Modify: `STATUS.md`; add evidence under `docs/evidence/`.

**Interfaces**
- Existing: `_m5_status_payload() -> dict`.
- Planned: `collect_m5_preflight(*, environment: str, commit_sha: str, probes: Mapping) -> dict`; fields component/status/configured/live_verified/checked_at/error_code, no secrets.
- API health remains bounded; paid model/image generation excluded from passive preflight.

- [ ] Fetch active branch/head and pinned source; compare to deployed SHA/URL before changing code.
- [ ] Map every skipped live test to prerequisites and acceptance criterion; preserve existing skips outside selected scope.
- [ ] Write failing tests: configured-but-unprobed component never live_verified; stale worker BLOCKED; missing queue URL never falls back to localhost in intended staging; evidence contains no secret values.
- [ ] Run focused tests and observe failures; implement passive probes, safe error codes and environment/source identity.
- [ ] Verify Postgres SELECT1, Redis PING, R2 safe unique probe in authorized staging; use cleanup/finally. Record every result, including failures.
- [ ] Commit only after focused/regression checks; dashboard separates „configured”, „probed” and „behavior verified”.

**Exit:** one report shows all actual dependencies; queued work cannot be approved while worker capability is absent/stale.

## Task 2: infrastructure freshness, concurrent provisioning ו־recovery

**Files**
- Modify: `omni_prod/infrastructure_provisioner.py`, `omni_prod/providers/managed_web_saas.py`.
- Test: `tests/test_m5_managed_web_saas_profile.py`, `tests/test_m5_generated_app_storage_isolation.py`.
- Create: `tests/test_m5_infrastructure_recovery.py`.
- If durable journal/lease needs schema: use a new migration number after surveying migrations; never reuse 022–025 or invent a number without checking runner.

**Interfaces**
- Existing: `InfrastructureProvisioningService._provision_one(...)`, `cost_quotes(...)`, `ManagedWebSaaSProvisioner.status(binding, *, now=None)`.
- Existing resource identity: `provisioning_idempotency_key`.
- Preserve `InfrastructureBinding` ownership and refs-only persistence.

- [ ] RED: LIVE stored binding expired now must not satisfy require_ready; revoked key/DB role must fail freshness.
- [ ] RED: two concurrent calls for one key produce one effective credential lifecycle; crash after DB role change before secret write is recoverable and does not silently invalidate another active runtime.
- [ ] Implement status/freshness check before reuse; persist fresh status. Quote may label zero *additional provisioning* only for fresh reusable owned binding; recurring usage costs remain separate.
- [ ] Add durable operation identity and lease/locking covering external effects, with retry/compensation rules. Token/DSN never enters journal.
- [ ] Run focused tests and real disposable integration with injected failure boundaries; verify no orphan role/secrets, no double reserve.
- [ ] Commit and record bounded recovery behavior.

**Exit:** reuse is safe under expiry, revocation, crash and concurrency; renewal is explicit, authorized and traceable.

## Task 3: provider-aware live-test gates ו־Infisical lifecycle

**Files**
- Modify: `tests/integration/test_m5_managed_web_saas_live.py`.
- Create: `tests/integration/test_infisical_secret_store_live.py`.
- Test/modify as needed: `tests/test_infisical_secret_store.py`, `omni_prod/secrets_manager.py`.
- Modify: `docs/INFISICAL_GENERATED_APP_SECRETS.md`.

**Interfaces**
- Existing: `InfisicalHttpSecretWriter.write(reference,value)`, `resolve(reference)`, `delete(reference)`.
- Logical scope: vault:secret/data/148ai/generated-apps/<probe-unique>/preview/<kind>/<name>.
- No public endpoint that accepts arbitrary secret refs/returns values.

- [ ] RED: valid Infisical config does not require Vault URL/token; AWS/R2 gates differ; unsupported provider fails closed.
- [ ] Include malformed HTTPS URL parse failure in sanitized config-status tests.
- [ ] Implement provider-specific prerequisite checks; no token values printed in skip/error.
- [ ] In staging, authenticate → unique secret create → read compare → rotate → read compare → delete → absence. Run from fresh process to exercise token lifecycle; cleanup in finally.
- [ ] Live negative permission test in test identity or fixture; verify 403 never triggers create; token expiry refresh tested with controlled clock.
- [ ] Focused tests PASS; live probe must PASS, not SKIP; save evidence and commit.

**Exit:** Infisical credentials are actually valid and secret lifecycle works on EU/dev.

## Task 4: Neon generated-app role/schema ובידוד

**Files**
- Modify if failure reproduces: `omni_prod/providers/managed_web_saas.py`.
- Test: `tests/integration/test_m5_managed_web_saas_live.py`.
- Create: `tests/integration/test_m5_neon_generated_isolation.py`.
- Existing: `infra/staging/verify_neon_bootstrap.py`; no rerun of empty bootstrap.

**Interfaces**
- Existing: `PostgresAdminBackend.ensure_role_and_schema(admin_dsn,role,schema,password)`, `verify_login(app_dsn, schema=...)`, `disable_role(...)`.
- Admin ref: `env:GENAPP_DATABASE_URL_UNPOOLED`; differs from OMNI_DATABASE_URL.

- [ ] Read-only confirm env resolution, host/database identity and admin privilege capabilities without printing credentials.
- [ ] Verify existing platform migrations; use separate disposable generated schemas/roles for tests.
- [ ] Create two resources A/B with distinct project IDs; perform role login and CRUD for each; read secret back from Infisical and verify same connection works.
- [ ] Negative tests: A cannot read/write B schema, create/alter roles or access platform DB; generated runtime has no admin role membership. Check PUBLIC/default grants explicitly.
- [ ] If permissions fail, implement minimal grants/search_path/ownership corrections with focused RED→PASS tests; do not give generated users neon_superuser.
- [ ] Cleanup: disable/revoke role, remove test objects/secrets under defined ownership; record actual SQL outcomes/classes only.

**Exit:** live database and cross-project DENY evidence. Mere role creation is insufficient.

## Task 5: R2 generated-app scoped credentials והחלפה שקופה ל־STS

**Files**
- Create: `omni_prod/providers/r2_credentials.py`, `tests/test_m5_r2_credentials.py`.
- Modify: `omni_prod/providers/managed_web_saas.py`, `.env.example`.
- Test/modify: `tests/test_m5_generated_app_storage_isolation.py`.
- Create: `tests/integration/test_m5_r2_generated_storage_live.py`, `docs/R2_GENERATED_APP_STORAGE.md`.

**Interfaces**
- Planned config switch: `OMNI_GENAPP_S3_PROVIDER=cloudflare_r2`; default `aws_sts` preserves current path.
- Planned issuer uses existing `issue(*, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds) -> dict` contract; output access_key_id/secret_access_key/session_token/expires_at.
- Cloudflare API path: /accounts/<account_id>/r2/temp-access-credentials; scope bucket+prefix and object-read-write. API parent token remains operator-side; config names fixed in adapter documentation before founder setup.
- Strictly validate the policy subset produced by scoped_object_policy; unsupported/wider policy fails closed, never ignored. R2 path does not require fictional role ARN.
- Prefer documented Temporary Credentials API first. Local JWT signing is an alternate future optimization, not a second implementation in this task.

- [ ] RED: AWS config still requires ROLE_ARN; R2 doesn't. Unsupported provider, unrestricted policy, invalid account/host, empty tokens, excessive TTL fail closed.
- [ ] RED: token/body are not in error/log; redirect refused; response fields validated; malformed/expired credential cannot be marked LIVE.
- [ ] Implement issuer and factory selection. Document exact new env refs and account-id. Secrets resolve server-side through approved resolver, not frontend.
- [ ] Founder batch: create private `148ai-generated-assets` Bucket and dedicated token limited to that bucket; configure Preview only. Keep omni-artifacts/operator keys separated. Review displayed price before service changes.
- [ ] Strengthen probe: PUT→GET exact bytes/checksum→DELETE; test known existing sentinel outside allowed prefix returns permission denial. Cross-app and cross-environment tests both required.
- [ ] Test expiry, refresh/revoke behavior via Task2; active runtime renewal cannot depend on stale immutable exported credentials.
- [ ] Run focused tests, real R2 negative probes and cleanup; commit evidence.

**Exit:** provider-level isolation, not just path names; no parent credentials in generated source/ZIP.

## Task 6: Redis/RQ worker ותורי ניקוי

**Files**
- Modify: `omni_prod/worker.py`, `omni_prod/queueing.py`, `omni_prod/build_outbox_relay.py`.
- Create: `tests/test_m5_worker_topology.py`, `infra/worker/README.md`.
- Deployment manifests belong to selected external host; retain exact SHA image provenance.

**Interfaces**
- Existing queues: `omni-builds`, `preview_host_queue(runtime_host)`.
- Existing jobs: execute_live_build_job, execute_preview_launch, stop_preview_task, execute_modification_job.
- Existing relay: `relay_once(pool, redis_url, ...)`.

- [ ] Select host that can run persistent RQ worker and isolated execution, document cost/current constraints; use existing code topology before proposing broad rewrite.
- [ ] RED: worker with runtime_host H consumes build + host-H queue; never consumes host-B cleanup.
- [ ] Wire worker launcher; verify OMNI_REDIS_URL is TLS Redis protocol URL, not Upstash REST URL. Verify RQ command semantics on actual service, not only PING.
- [ ] Use actual external worker process: enqueue harmless job → dequeue → durable result; heartbeat identifies host/SHA.
- [ ] Stop/restart worker and break queue briefly; transactional outbox redispatches exactly once by build ID. Alert/stale worker state visible.
- [ ] Run cleanup job on correct host; physical container/workdir removal proved. Record manifests/service restart/credentials names.

**Exit:** durable jobs are executed and recoverable, not merely accepted202.

## Task 7: bounded model route, usage ו־אבחון

**Files**
- Modify only as needed: `omni_prod/model_runtime_config.py`, `model_gateway.py`, `routed_gateway.py`, `provider_usage.py`, `model_policy.py`.
- Test: `tests/integration/test_m5_live_llm_usage.py`, `tests/test_m5_llm_usage_evidence.py`.
- Modify UI error handling: `omni_prod/assets/app.js`; test `tests/test_m5_creator_workspace.py`.

**Interfaces**
- Existing: ModelEndpoint.external, ModelUsePolicy, RoutedModelGateway.complete_json, provider usage ledger.
- Model primary defaults localhost:8001; that is not valid proof of cloud model.
- Paid route must preserve external classification and budget; never disguise paid API as local to bypass controls.

- [ ] Founder/provider batch: select one actual code model, exact API/model/version, secret ref and official prices; verify license/use scope.
- [ ] RED: paid call blocked without durable ceiling; bad JSON billed attempt recorded; malformed output triggers bounded repair; invalid credentials401 message differs from session expiry.
- [ ] Implement only needed adapter/config wiring and errors; sanitize URLs/query/error chains where sensitive.
- [ ] Run one explicit budgeted call from worker, record provider request id/model/token usage and result hash; no fake deterministic fallback.
- [ ] Verify quota429/backoff, timeout/cancel and no double accounting; focused regression PASS.

**Exit:** actual code-model call usable by canonical build engine, with spend evidence and truthful failure.

## Task 8: isolated build runtime ותצוגה מקדימה

**Files**
- Review/modify: `omni_prod/remote_sandbox.py`, `sandbox_executor.py`, `sandbox.py`, `preview_runtime.py`, `worker_tasks.py`, `preview_repository.py`.
- Deployment: `infra/sandbox/Dockerfile`, `infra/sandbox-runner/Dockerfile`, `docker-compose.international.yml` or selected isolated provider adapter.
- Test: `tests/integration/test_live_sandbox_security.py`, `test_live_preview_runtime.py`.
- Create: `docs/EXECUTION_TOPOLOGY_ADR.md`, `tests/integration/test_m5_external_execution_path.py`.

**Interfaces**
- Existing: RemoteSandboxRepositoryExecutor.execute(repository=..., spec=...); DockerPreviewProvider.start/stop; execute_preview_launch.
- Preview route binds exact project/version/host/port; URL template/router must point to that verified runtime.

- [ ] ADR compares current external Docker host path with managed sandbox using current pricing/access. Pick one for this slice; do not add two execution stacks.
- [ ] Reproduce install/build/test in chosen production image with exact pins. Network for dependency install is allowlisted and separated from untrusted runtime access; no operator secrets in code execution.
- [ ] Run hostile limits: filesystem escape, network/metadata/private IP, CPU/RAM/PID/timeout, secret access; failures denied without loosening isolation.
- [ ] Launch web preview through real router/TLS; health200 plus business behavior, not static splash alone; correlate source version/hash.
- [ ] TTL/stop/crash/restart cleanup and worker-host ownership proven; add physical expiry sweep if missing.
- [ ] Commit passing tests/evidence/image digest; record resource cost and logs.

**Exit:** generated source runs safely at a real per-project URL and cleans up completely.

## Task 9: scheduler/outbound behavior ו־readiness truth

**Files**
- Modify: `omni_prod/providers/managed_web_saas.py`, `infrastructure_contracts.py` only if evidence shape requires.
- Create: `omni_prod/providers/scheduled_http.py`, `tests/test_m5_scheduled_delivery.py`, `tests/integration/test_m5_scheduled_delivery_live.py`.
- Existing `identity_lifecycle.py` is not a generated-app email service.

**Interfaces**
- Planned SchedulerClient.create/cancel/get consumes owned callback+schedule+idempotency key and returns external task ID persisted by caller.
- Callback verification uses generated-app secret, delivery ID/timestamp and replay protection.
- Evidence separates scheduler_health_verified, delivery_verified, webhook_verified, email_live_verified.

- [ ] Choose scheduler compatible with real callback delivery and official price; founder account step only after adapter contract pinned.
- [ ] RED: health200 alone cannot claim delivery verified; duplicate/replayed/tampered callback rejected; cancelled task never accepted as pending.
- [ ] Implement create/run/retry/cancel wiring and durable provider ID; error-safe credential resolution.
- [ ] Live test schedules one controlled callback, proves receipt/signature/delivery ID, failure retry and cancellation; teardown.
- [ ] Webhook roundtrip separately; if email requested, send to controlled test inbox using generated-app scoped key and verified domain. No email claim without delivery evidence.
- [ ] PASS tests and record capability-level truth.

**Exit:** required jobs/outbound actually work; binding labels are not broader than evidence.

## Task 10: image generation ו־price catalog

**Files**
- Existing: `omni_prod/providers/image_provider.py`, `provider_pricing.py`, `build_cost_plan.py`.
- Test: `tests/test_m5_media_provider_adapters.py`, `tests/integration/test_m5_live_media_provider.py`.
- Modify: `COST_MODEL.md`, provider config docs.

**Interfaces**
- Existing prediction-job API protocol and PostgresSubmissionJournal; no direct assumption that OpenAI image API speaks /predictions.
- quote fields estimated/maximum/pricing_version/price_source; actual provider figure or NULL.

- [ ] Select compatible image provider/model with price/license; if protocol differs, new adapter tested against provider's documented API.
- [ ] RED: unknown price blocks before submit; crash INTENT without ID does not blindly pay again; provider idempotency declared only when actually supported.
- [ ] Configure per-image maximum and price-source date/version, infra one-time and recurring cost dimensions; do not fill invented0.
- [ ] Perform one authorized icon generation; validate MIME/dimensions/size/hash/provenance and store artifact durable.
- [ ] Fresh-process collect/cancel/resume plus spend reconciliation tests PASS; record price and measured/unknown cost honestly.

**Exit:** required asset generation works, quotes are supported by evidence.

## Task 11: first complete canonical build

**Files**
- Existing pipeline: `investor_app.py`, `worker_tasks.py`, `build_contract_repository.py`, `job_repository.py`, `workspace.py`.
- Test: `tests/test_m5_build_contract_binding.py`, `tests/test_m5_build_economics.py`, `tests/test_m5_web_saas_acceptance.py`.
- Create: `scripts/run_m5_staging_acceptance.py` with secured runtime auth, no credentials arguments printed.

**Interfaces**
- POST /api/v28/projects/{project_id}/builds →202 durable build_id.
- status → actual phases/evidence; READY only if all real gates passed.
- Bind approved contract fingerprint and quote to execution; worker reloads exact data.

- [ ] Before execution: all dependencies and required gates ready, budget approved, no internal sample generator substituted.
- [ ] Submit canonical task prompt with test account; capture request/build/contract/reservation IDs and source SHA.
- [ ] Observe real INFRASTRUCTURE→ASSETS→GENERATING→VERIFYING, bounded repair, persisted repository/spec/version/evidence.
- [ ] Force one provider/build failure and worker crash boundary: terminal status and credits truthful, no duplicate provider spend/versions.
- [ ] Validate generated app CRUD via actual browser/API and generated DB; refresh/redeploy persists task data.
- [ ] Save immutable evidence JSON with timestamps/provider IDs/hashes and redacted logs.

**Exit:** one working task app end-to-end; no gate bypass.

## Task 12: versions, modify/repair/rollback ו־ZIP

**Files**
- Existing: `modification_engine.py`, `modification_repository.py`, `spec_repository.py`, `workspace.py`, `investor_app.py`, `assets/app.js`.
- Test: `tests/test_m4_acceptance.py`, `test_workspace_version_conflict.py`.
- Create: `tests/integration/test_m5_deployed_version_lifecycle.py`.

**Interfaces**
- Existing exact version/spec modification routes; optimistic expected-version accept.
- System bug/missing original requirement free policy; change_request charged by contract policy.

- [ ] Live natural-language change produces real diff and separate candidate; original version unchanged until accept.
- [ ] Broken app triggers actual repair; retry bound and cost policy recorded.
- [ ] Two concurrent candidates: conflict is explicit, no silent overwrite. Accept/reject/rollback verified from DB and running source hash.
- [ ] ZIP exports full runnable source/manifest/requirements/README with artifact hash, **no operator secrets**; test clean install/build from ZIP.
- [ ] Reload/redeploy UI recovers project/current version/active build; incorrect login/session errors fixed via Task7.
- [ ] Commit live lifecycle evidence.

**Exit:** edit/export/restore are usable and durable.

## Task 13: three apps ושני משתמשים

**Files**
- Create: `tests/integration/test_m5_deployed_tenant_journeys.py`.
- Existing: `web_saas_acceptance.py`, `project_lifecycle.py`, `creator_accounts.py`, `account_tenant.py`.
- Evidence under docs/evidence for each prompt.

- [ ] Prompt A: task board with roles, persisted CRUD/completion/filter.
- [ ] Prompt B: booking calendar with admin/member and double-booking prevention.
- [ ] Prompt C: inventory with stock movements and low-stock view; upload/scheduled action if contract includes.
- [ ] Each must use actual model, repository/build/preview, real server/data behavior, saved versions and downloadableZIP; canned page is not success.
- [ ] Two real controlled accounts: A/B cannot list/read/edit/delete/export/preview each other's projects; check guessed IDs, archived projects, object refs and schema boundaries.
- [ ] Pass phone/desktop Hebrew RTL and English LTR, keyboard/navigation/error/empty states; document current scope accurately.

**Exit:** mission's three distinct nontrivial prompts and live tenant isolation pass.

## Task 14: full identity lifecycle ו־OAuth

**Files**
- Existing: `identity_lifecycle.py`, `browser_session.py`, `investor_app.py`, `assets/app.js`.
- Test: `tests/test_m5_identity_lifecycle.py`, `tests/test_m5_browser_session.py`.
- Create provider-specific OAuth adapter/routes tests only after confirming current registration approach; don't assume installed Clerk is wired.

- [ ] Resolve current email verification/reset delivery wiring; token creation without actual email flow cannot satisfy acceptance.
- [ ] Email: verified link, expiry, single-use, reset, revoke sessions, account enumeration-safe errors; deletion/export results not only queued request.
- [ ] Google account registration/callback, state/PKCE/linking/tenant rules live; Preview/Production callback URLs explicit.
- [ ] Apple requires founder developer/OAuth setup; if unavailable, disabled honest UI + precise blocker; don't mark identity fully finished.
- [ ] Deployed HTTPS cookie HttpOnly/Secure/SameSite/CSRF, logout and revocation proved; no tokens in JS/localStorage.
- [ ] Two real test-user browser journeys PASS; save redacted evidence.

**Exit:** identity requirements that are enabled work fully, disabled providers precisely disclosed.

## Task 15: publish actual generated product

**Files**
- Existing: `omni_prod/deployments.py`, `release_manifest.py`, `rollback.py`, `investor_app.py`.
- Create/modify adapter after reading actual existing deploy implementation; name `omni_prod/providers/vercel_deployment.py` if a dedicated adapter is needed.
- Create: `tests/integration/test_m5_generated_publish_live.py`.

**Interfaces**
- Consumes immutable repository/version/artifact manifest and authorized target, never mutable current head.
- Produces deployment_id/url/source_version/hash, terminal outcome and log reference.
- Generated env bindings resolve server-side; operator credentials excluded.

- [ ] RED: failed gates reject publish; cross-tenant deploy/rollback denied; network retry cannot create uncontrolled duplicate deployment.
- [ ] Implement selected Vercel target compatibility, dependency build/env mapping and terminal status polling.
- [ ] Publish one generated Web app to a real URL; behavioral HTTP/browser tests and DB/storage bindings work there.
- [ ] Promote/rollback exact verified versions; mutable source drift fails closed.
- [ ] Record current Vercel plan/usage terms and required domain/TLS/account decisions before public commercial traffic.

**Exit:** publishing changes a generated product accessible at a real deployment URL; button alone is insufficient.

## Task 16: subscriptions, costs ו־billing reconciliation

**Files**
- Existing: `stripe_billing.py`, `subscription_store.py`, `worker_tasks.py::resolve_m5_billing`, `provider_usage.py`, `pricing.py`.
- Test: `tests/test_m5_economics_reconciliation.py`.
- Create: `tests/integration/test_m5_stripe_lifecycle_live.py`.
- Modify: `COST_MODEL.md`.

- [ ] Stripe test-mode checkout→signed event→server entitlement; duplicate/out-of-order/bad-signature events, cancellation/upgrade/failure handled.
- [ ] Exhausted quota or missing reservation cannot trigger paid provider.
- [ ] Reconcile successful build, paid failure, retry, cancellation, heavy user across model/image/infra/storage/egress/sandbox fees.
- [ ] Distinguish provider actual, usage-derived actual and conservative reserve; unknown stays NULL; charge/settlement idempotent.
- [ ] Include verified repair-free cases; don't award arbitrary free credits to bypass revenue guard.
- [ ] Save ledger evidence and pricing source/effective date; only then configure production payment credentials through secure channel.

**Exit:** entitlement and unit economics are supported by measurements and trusted events.

## Task 17: operations, backups ושחזור אמיתי

**Files**
- Modify: `omni_prod/recovery_drill.py`, `backup_manifest.py`, `observability.py`, `structured_event.py`, `request_id.py`.
- Create: `scripts/run_m5_restore_drill.py`, `docs/OPERATIONS_RUNBOOK.md`, `tests/integration/test_m5_restore_live.py`.

- [ ] Keep simulated manifest exercise labeled simulation; create real backup path with provider snapshot/dump and artifact/secret-reference manifest.
- [ ] Restore to separate DB/environment, never overwrite live account DB; verify schema/migrations/rows/current versions/artifact hashes and generated secret references.
- [ ] Measure restore/recovery time; document retention, RPO/RTO target and observed value.
- [ ] Correlate UI error reference→API→queue→worker→provider→preview; ensure secret redaction.
- [ ] Alert on stale workers, queue delay, retry storms, sandbox leaks, cost spikes, provider quotas and DB saturation; test one deliberate failure.
- [ ] Run deploy rollback and incident drill; log owner/actions/results.

**Exit:** production loss/failure recovery is exercised, not inferred from backup module.

## Task 18: release gate ו־promotion

**Files**
- Existing: `release_gate.py`, `launch_readiness_v28.py`, `truth_lock.py`, `STATUS.md`, `M5_VALIDATION.md`.
- Create: `docs/evidence/M5_DEPLOYED_RELEASE_EVIDENCE.md`.

- [ ] Full clean CI: requirements install, compileall, pytest, hostile static, international gate, compose config. No new unexplained skips.
- [ ] Required live tests run with selected service prerequisites; CI green without them remains partial.
- [ ] Verify all mission acceptance rows: account/3apps/repair/preview/versions/ZIP/tenant/cost/backup/rollback.
- [ ] Vulnerability/dependency/secret scans, accessibility, rate limits, quotas, public copy/pricing/privacy/support flows verified on same release.
- [ ] Reconcile main vs milestone histories before any promotion; no blind merge or migration rerun.
- [ ] Record exact source/env/deploy URL/image hashes, measured costs, known limitations and rollback.
- [ ] Production release only after authorized release decision and passing gates; any incomplete criterion stays visible.

**Exit:** verified public Web product; broad „Build Anything” claims remain scoped to reality.

## Task 19: native ותחומים נוספים — אחרי Web

**Scope:** Android/iOS, Desktop, Agent/Automation, multiplayer/3D/media families.
- [ ] Separate design/acceptance for cross-platform code and API/data reuse.
- [ ] Android: source/build/device tests/keystore/Play account/internal release/signing.
- [ ] iOS: macOS build/Xcode/provisioning/developer account/TestFlight/device verification.
- [ ] Stores/payment/privacy/accessibility/release channels assessed using current official rules before each release.
- [ ] Per-target real providers/prices/licensing/artifact integrity and platform signing.
- [ ] Claim only targets verified through install/use/update/rollback lifecycle.

זו roadmap עתידית; פרטי implementation לכל target ייכתבו מול הקוד והחשבונות הזמינים. אין לסמן משימות אלה complete מכיוון שקיים source-target enum.

## 3. בדיקות ובקרה קבועות לכל שינוי

לשינוי logic:
1. RED רלוונטי לכשל אמיתי.
2. שינוי קטן, ללא החלפת stack כללית.
3. focused PASS ואז full required gates.
4. side effects נבדקים ב־staging עם unique IDs, budget ceiling ו־cleanup.
5. evidence עם environment, SHA, timestamp, actual URL/results, לא screenshots של success בלבד.
6. commit/PR מתאר problem→behavior→validation→remaining blockers.
7. source changes לא מתערבבים עם account config לא מתועדת.

פקודות regression הקיימות:
```bash
python -m pip install -r requirements-production.txt -r requirements-test.txt
python -m compileall -q omni_prod tests
python -m pytest -q
python scripts/run_hostile_static_suite.py
python scripts/run_international_gate.py
docker compose -f docker-compose.international.yml config
```

בדיקות חיות אינן מקבלות env secrets דרך command-line argument/log.Prerequisites נמסרים דרך secret manager/secure runtime. קובצי הבדיקות החדשים במסמך הם **planned**, לא קיימים או passing כעת.

## 4. משימות המשתמש המרוכזות

| שי מבצע כשהקוד מוכן | ההנדסה מכינה קודם | הוכחה לאחר מכן |
|---|---|---|
| R2 Bucket/token ייעודיים | adapter + env reference names + isolation tests | allowed/denied/roundtrip |
| בחירת/חיבור worker host | ADR, manifest, cost envelope, restart/cleanup | enqueue/dequeue/heartbeat/sandbox |
| code model/image credentials | exact API/model/prices + adapters | actual invocation/usage/assets |
| scheduler/email/domain | callback/delivery contract, env names | run/retry/cancel/send |
| OAuth/Apple/Stripe/domain | callback URLs/scopes/setup instructions | live end-to-end callbacks/events |
| Production access/release | complete gate evidence/rollback | production verification |

לא מבקשים משי צילום לאחר כל קליק אם אפשר למסור רצף אחד בטוח. לא מבקשים סודות בצ'אט. תחילה מסיימים עבודה טכנית שאינה תלויה בגישה לחשבון.

## 5. הגדרת „סיימנו” ובקרת omissions

| דרישת mission | Tasks |
|---|---|
| onboarding/RTL/LTR/responsive/truthful UX | 1,7,12,13,18 |
| email/Google/Apple/session/recovery/deletion/export | 14 |
| persistent projects/versions/two-user isolation | 4,11,12,13 |
| real generation/repair/budget/cancel/idempotency | 2,6,7,10,11 |
| safe preview + publish + ZIP | 8,12,15 |
| commercial controls/costs/entitlements | 10,16 |
| observability/admin/rate limits/restore/rollback | 1,6,17,18 |
| long-term native scope | 19 |

**Self-review:** covered mission Web acceptance; separated source/fixture proof from external live; identified fresh credentials, crash/concurrency, tenant attacks, stale workers and restore consistency; preserved interfaces of existing pipeline. Tasks1–18 are executable deliverables. Task19 is explicitly future scope requiring target-specific specs, not an executable native completion promise.

**Handoff:** start with audit document then Tasks1–3; keep unknown status honest. This turn saves the plan only. No implementation runs while the founder has asked to pause.

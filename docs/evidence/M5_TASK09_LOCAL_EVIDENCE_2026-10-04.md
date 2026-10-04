# M5 Task 9 — local evidence (2026-10-04)

Scope: LOCAL ONLY. No real image provider credentials or outbound network were available in the implementer sandbox. `tests/integration/test_m5_live_media_provider.py` SKIPs (`M5_LIVE_IMAGE=1 not set`). `media.image.generate` is therefore NOT LIVE.

## Unit / contract (python -m unittest tests.test_m5_media_provider_adapters) — 21 tests OK
- quote from operator-configured per-image estimate/maximum with a named price source; NOT_CONFIGURED without price
- submit/poll/collect/cancel against an in-test prediction-job HTTP double
- durable journal: same idempotency key reuses the recorded task; crash window without a declared provider idempotency header raises AmbiguousSubmission and performs no paid submit; with a declared header it resubmits with the same key
- 429 on submit -> ProviderRateLimited(retry_after) and journal intent cleared; poll waits between requests
- output MIME sniffed (PNG/JPEG/WebP), size-limited, sha256 + provenance (task id, model, prompt hash, output host); API key never in evidence
- actual_cost_usd only from an explicit provider cost field, otherwise None
- commercial-use must be declared; a non-commercial provider is never routed for a commercial build
- end-to-end through the real CapabilityExecutor + MemoryCapabilityRepository: requirement VERIFIED, PNG stored, png-signature + sha256 checks, estimated cost recorded, actual cost NULL; authorization ceiling blocks before any submit

## Migration 022 on local PostgreSQL 16.15
```
INSERT ... ON CONFLICT DO NOTHING RETURNING  -> cap_1|img|INTENT|      (new intent)
second INSERT same key                       -> INSERT 0 0             (preexisting)
UPDATE bind task pred_1                      -> UPDATE 1
UPDATE re-bind to pred_OTHER                 -> UPDATE 0               (adapter raises)
INSERT SUBMITTED without task id             -> ERROR check media_provider_submissions_task
DELETE intent for submitted row              -> DELETE 0               (never clears a submitted job)
```

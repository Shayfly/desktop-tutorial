# 148AI — Secrets & Environment Registry

This file is the canonical **name/scope registry** for environment variables. It intentionally contains **no real credentials**.

## Rules

1. Never commit real secrets to Git, `.env`, documentation, tests, screenshots, or issue text.
2. `.env.example` contains placeholders only and is safe to commit.
3. Local `.env` files are ignored by Git.
4. Production secrets belong in the platform secret store (Vercel Environment Variables, GitHub Actions secrets, or HashiCorp Vault depending on the runtime).
5. Generated-app credentials are written to Vault through `SecretWriter`; only `vault:` references should be persisted by the control plane.
6. Rotate any credential immediately if it is ever exposed in source/history/logs.

## Control-plane secrets

| Variable | Secret | Required for | Canonical storage |
|---|---:|---|---|
| `OMNI_SECRET_KEY` | Yes | production auth/signing | production secret manager |
| `POSTGRES_PASSWORD` | Yes | bundled PostgreSQL container | deployment secret manager |
| `OMNI_DATABASE_URL` | Yes | durable PostgreSQL mode | deployment secret manager |
| `OMNI_S3_ACCESS_KEY` | Yes | S3/MinIO artifacts | deployment secret manager |
| `OMNI_S3_SECRET_KEY` | Yes | S3/MinIO artifacts | deployment secret manager |
| `OMNI_SANDBOX_SHARED_SECRET` | Yes | HMAC-authenticated sandbox runner | deployment secret manager |
| `OMNI_BILLING_ADMIN_KEY` | Yes | billing administration | deployment secret manager |
| `STRIPE_SECRET_KEY` | Yes | Stripe server API | deployment secret manager |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook verification | deployment secret manager |
| `RESEND_API_KEY` | Yes | transactional email | deployment secret manager |
| `RUNPOD_API_KEY` | Yes | GPU/media provider | deployment secret manager |
| `ANDROID_KEYSTORE_PASSWORD` | Yes | Android release signing | CI secret store only |
| `ANDROID_KEY_PASSWORD` | Yes | Android release signing | CI secret store only |
| `APP_STORE_CONNECT_PRIVATE_KEY` | Yes | iOS/App Store signing/release | CI secret store only |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | Yes | Google Play release | CI secret store only |

## Secret references / Vault

| Variable | Secret | Purpose |
|---|---:|---|
| `OMNI_VAULT_TOKEN` | Yes | read control-plane Vault references |
| `OMNI_GENAPP_VAULT_TOKEN` | Yes | write/read/delete generated-app secrets |

Vault tokens must never be stored in the repository. Generated application database passwords/session keys/webhook keys must be stored as Vault values; database/application records should keep only the `vault:` reference.

## Sensitive provider credentials

Model/provider credentials (OpenAI, Anthropic, Google/Gemini and other external providers) must be handled through the 148AI connection/secret layer or a deployment secret store. They must **not** be embedded in provider catalogs, source code, registry JSON, or generated projects.

The exact environment-variable contract for a provider must be documented by its adapter before a variable is added here. Do not invent or duplicate credential names.

## Non-secret runtime configuration

These are configuration values and may appear in `.env.example`: `OMNI_ENV`, `OMNI_ALLOWED_ORIGINS`, `OMNI_PUBLIC_BASE_URL`, `OMNI_REDIS_URL`, `OMNI_S3_ENDPOINT`, `OMNI_S3_BUCKET`, `OMNI_S3_REGION`, sandbox resource limits, model endpoint/model IDs, budget limits, quality thresholds, public brand/domain, plan prices/provider caps, Stripe price IDs, mobile public IDs, and readiness flags.

Even non-secret values should use separate Preview/Staging/Production values where environment isolation matters.

## Vercel

Use Vercel Environment Variables with separate scopes for **Preview** and **Production**. Never place credentials in `vercel.json`.

Vercel can host the web/API surface that is compatible with its runtime, but the complete 148AI production topology also requires durable PostgreSQL, Redis/RQ workers, S3-compatible storage, and an isolated sandbox runner. Those services must remain external/dedicated unless a verified compatible managed provider is configured.

## GitHub Actions

CI validation uses synthetic test values only. Real production secrets are not required for unit/static/config validation. Release/signing workflows that genuinely need credentials must use GitHub Actions secrets/environments and should require protected-environment approval.

## Rotation checklist

- Revoke/rotate the old credential at the provider.
- Update the appropriate secret manager scope.
- Redeploy/restart only the workloads that consume it.
- Verify health/auth/webhook/signing behavior.
- Confirm secret scan and CI remain green.
- Never commit the replacement value.

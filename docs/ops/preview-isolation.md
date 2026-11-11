# Preview isolation (72)

Signed by Michael 2026-11-11.

| Resource | Production | Preview |
|---|---|---|
| Database | 148ai-db-v2 `main` (`OMNI_DATABASE_URL`) | its own Neon branch `preview/<git branch>` (`DB2_DATABASE_URL`, created by the Neon–Vercel integration from Production's data); no branch → no database, never Production (#313) |
| Build queue | Redis (`OMNI_REDIS_URL`) + the Oracle worker | **none**: a build is closed at once as `preview_no_build_queue` — the customer reads "הבנייה לא רצה בגרסה הזאת — זו גרסת בדיקה בלי תור בנייה. הקרדיטים הוחזרו." — an environment outcome, not a product failure; credits released; `environment` recorded on the job |
| Branch hygiene | — | deleted when its PR closes; daily alert over 50 (#314) |

## What the Preview smoke covers — and what it does NOT

`deployment-verify` on a Preview checks identity (SHA), schema, register → project → conversation → persistence → memory, anonymous denial and cross-user isolation — against the preview's own database.

**The Preview smoke does NOT cover the builder.** No build runs on a Preview until warehouse item 82 exists. A builder regression (e.g. the stub-UI placeholder of 2026-11-10) is caught only by a build on Production / the founder runs, not by the Preview smoke.

## Warehouse

- **82** — table-based build queue per Preview: a jobs table in the preview branch + a worker that polls it = builds run on a Preview, without Redis and without touching Production. The worker exists per Preview already; the missing piece is the queue.
- Branch data: preview branches copy Production data (`parent-data`). Kept while there are three customers (realistic tests, zero cost); schema-only needs migrations per branch — revisit with real customers.

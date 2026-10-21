# bot-reports

Report files written by CI bots (founder decision 2026-10-21, route A). The bots push here, never to `main`:
`main` is protected (required `test` + `validate`), so a bot's direct push to `main` is rejected by GitHub (GH006).

- `smoke/ci-last-run.md` — v24-ci `publish-report` (latest main CI result)
- `smoke/last-run.md` — Production Smoke `publish results`
- `smoke/db-identity.md` — db-identity
- `smoke/failure-taxonomy.jsonl`, `smoke/rehearsal-builds.jsonl` — golden-rehearsal `publish-taxonomy` (appended)
- `docs/venice_prices_snapshot.raw.md` — venice-snapshot (raw pricing page, byte-exact)

Seeded from `main` @ 8634a57 (the last bot reports that landed there: ea7fdff, 5e4cdf0; the other three files as of 8634a57). Reports only; no code.

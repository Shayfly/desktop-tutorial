# bot-reports

Report files written by CI bots (founder decision 2026-10-21, route A). The bots push here, never to `main`:
`main` is protected (required `test` + `validate`), so a bot's direct push to `main` is rejected by GitHub (GH006).

- `smoke/ci-last-run.md` — v24-ci `publish-report` (latest main CI result)
- `smoke/last-run.md` — Production Smoke `publish results`

Seeded from `main` @ 8634a57 (the last bot reports that landed there: ea7fdff, 5e4cdf0). Reports only; no code.

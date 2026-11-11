# Frozen run frozen-2026-11-10b — result (closed 2026-11-11T08:16Z)

**Bottom line, without spin: 1 of 3 build arms passed. The decision gate (5 of 6) was not reached.**
The stop condition was met at arm 3 (identical failure in arms 2 and 3). Arms 4-5 were skipped (correction 2).
Run-level limitation: `routing-open` (correction 1). All costs are `founder-account`.

| # | arm | result | human decisions | cost |
|---|---|---|---|---|
| 1 | locksmith-hard | PASS -- but NOT AUTONOMOUS (13 decisions >= 12). Strict two-phone gate passed. data_create covered by a refusal check (POST -> 405): no unrequested data writes | 13 | $1.549 |
| 2 | florist-details | FAIL -- behavioural acceptance: missing `data_create` after 5 repair rounds; contract demanded data modules for a static page | 7 | $1.137 |
| 3 | florist-nodetails | FAIL TWICE -- (a) reproduction of arm 2; (b) SEVERE: the warned path did not fire (no CANON_INCOMPLETE, no tick, free approval) | 4 | $1.310 |
| 4 | restaurant-a | skipped | - | - |
| 5 | restaurant-b | skipped | - | - |
| 6 | refusal-control (scripted) | PASS -- clean refusal, no build, alternatives as information only; late (7 turns), text mixes internal English names | 8 | intake only |

Build spend: $3.997. Human code fixes: 0. Quarantined probes: none. Gate-waste metric: 0 (but see finding 6).

## What worked
- Truth: a call button with no number -> no number invented (arm 3). No testimonials, bouquets or prices invented (arms 2-3).
- The strict two-phone canon gate (arm 1). The refusal of an unbuildable product (arm 6).

## Findings for triage (none fixed during the run)
1. ROOT (likely shared): `classify_family("תבנה לי דף לחנות/לעסק ...")` -> web_app; only "דף נחיתה" -> website. Feeds 2, 3, 10, 12.
2. Contract: keyword "הזמנה" (also inside marketing copy, e.g. a WhatsApp template) -> customers/availability/bookings
   modules -> data_create required; an explicit "static page" decision does not override it (findings 7, 8).
3. SEVERE: the warned path (Michael condition 2) is off for web_app briefs: canon_view warns only for website/landing/content.
4. Reviews in a "— author ;" brief format never enter the canon -> the truth gate cannot check them (arm 1).
5. Intake: shorthand read as refusal; re-asks settled questions; promises a summary while a silent gate waits for
   unconfirmed required fields (personal_data, login) it never names.
6. The gate-waste metric counts only quarantine loops: 9 rounds burned on an impossible requirement counted 0.
7. Pricing: exact credits come only from the account plan (Studio -> 500), while the message cites plan complexity.
   Deferred by the owner until pricing is set.
8. Draft pages show developer instructions to visitors (TESTIMONIALS / content_config.py) and an "app data is saved" banner.
9. Refusal late (7 turns) and partly in internal English.
10. Pinning was not enforced (routing-open): runtime catalog choices answered in every build arm.
11. Infra: the intake enqueue failed once with "Redis URL must specify scheme" (another account, 2026-11-10 22:38Z).

Per-arm machine-readable rows: kept with the run evidence (23 fields + modelsUsed, findings, timelines).

## Freeze
The run ended with arm 6. Per docs/gate-freeze.json ("until the end of the LAST arm"), the freeze is lifted by this PR.

# Cleanup 73 — pre-deletion counts and sample (2026-11-11, before any delete)

Approved by Michael 2026-11-11 17:27. Production DB `148ai-db-v2`. Emails are masked; `row_sha256` =
sha256(`id|email|created_at`) so a row can be matched later without storing the address. No password hashes or
salts are exported (they are secrets, not evidence).

## Step 1 — counts by category
| category | count |
|---|---|
| `@example.com` accounts with the smoke brief ("An internal tool for my team to track equipment loans…") | 447 |
| `@example.com` accounts with no message at all (verify / smoke / qa) | 572 |
| `@example.com` accounts with any OTHER message | 0 |
| accounts NOT `@example.com` (real) | 3 |
| total | 1022 |

Anomaly found before deleting (excluded, reported): `usr_knIkBG9zfcBTlbQy` (`qa-pos***@example.com`, no messages)
holds an `INTERNAL_QA` entitlement granted by `claude:postdeploy` ("post-deploy verification, synthetic account") and
one build + contract + approval. It is tooling, not smoke residue: KEPT until someone decides what post-deploy needs.

## Step 2 — sample (kept, not deleted)
| kind | account | created | email | row_sha256 | project |
|---|---|---|---|---|---|
| smoke | usr_e9BtFZJyps9TM5HQ | 2026-10-25T20:44:06Z | verify***@example.com | 2e9ccda6296884518d371bd83a0f3f0d7ec945be3b5bdf1f9a01f8b7bdac2f14 | prj_qJY-ISUp2k3Z0Q |
| smoke | usr_uY4u-6byxykEA_fk | 2026-10-25T21:00:18Z | verify***@example.com | 449601587f484b0a9116fd9ae44df127de45fb94ff7c508102f8296e5665a950 | prj_r9KwWQ58xhm7Jg |
| smoke | usr_vW8z1iVzRnJeIMAF | 2026-10-25T21:07:16Z | verify***@example.com | 9d09e77a297015d334f523f580aee8c52c78550a9744bd8732ad6de5beb0d5e4 | prj_Q4cn8R2CLeSCZw |
| smoke | usr_-kjfgcNHKDiRteAm | 2026-10-25T22:32:31Z | verify***@example.com | 586c9aad2a90b21065f6c7e4f693f1617639ec945ccd642167050e4c23b43a82 | prj_FFQT0oAaEzkyfA |
| smoke | usr_ocmaW2J2h_7-5Xsr | 2026-10-26T06:03:50Z | verify***@example.com | f0ce67bd7ceb01e189f104bdf33f90be21fae4792cfb8845b74150246b84149c | prj_QFeL8ck-R-S_-Q |
| verify | usr_90o9dyb2VDSdem_Y | 2026-10-25T20:44:29Z | verify***@example.com | 3a399741b7a7b817f414475c959be215f701ae4210b3ff26b5e80fe1779ec963 | — |
| verify | usr_RvPz-S_rzaaYZCVw | 2026-10-25T20:53:20Z | smoke-***@example.com | ed897f92852aabe00046bfc601c9d2ab94f9b86c38c2bbdb23b9223b5a247850 | — |
| verify | usr_LWuBq5kyvYryBcFB | 2026-10-25T21:00:42Z | verify***@example.com | 012494c7e66f48194280a7978e6d69c4cebbbe7e85a2faa02b76718fbe975f9c | — |
| verify | usr_YnAzRKSjPAVNENXn | 2026-10-25T21:07:39Z | verify***@example.com | b72af750bd6a14e1ff9fa2fcb76e72972c6fceb2cf5cf2142d846891bec5ca6e | — |
| verify | usr__RoqvdQIvLmqTpjL | 2026-10-25T22:32:54Z | verify***@example.com | 5d8cb0d7566384126f57f9d8e9d603d86e83939c0a9fe39f2d3962a3cda81640 | — |

Per Michael's step 3 only the 5 SMOKE sample accounts (and their projects) are kept; the 5 verify rows above are a
sample of what is deleted.

## Steps 3-6 — executed 2026-11-11T15:29Z, one transaction
Safety copy first: Neon branch `backup-before-cleanup-73-2026-11-11` (`br-hidden-dawn-b98gvmud`, copy-on-write of the
production branch at LSN 0/13CB7DC0). Everything below can be restored from it.

The transaction re-derived the delete set and aborted by itself if it was not exactly 1013 accounts / 442 projects,
or if any non-`@example.com` account was in it. Order as ordered: messages -> briefs -> projects -> accounts ->
storage.

| step | deleted |
|---|---|
| intake messages | 1213 |
| project briefs | 442 |
| creator projects | 442 |
| creator accounts | 1013 (sessions, consents, identity tokens, privacy requests, subscriptions cascade) |
| storage | 0 — the deleted projects had no attachment rows, so no object files to remove |

**After: 9 accounts.**
- 3 real (not `@example.com`), complete: the founder (426 messages, 33 projects, 137 brief revisions, 24 builds),
  `usr_w61pl3sRDqHjJoXi` (61 / 1 / 14 / 2), `usr_3u73fHQ5kJWmgm6z` (45 / 1 / 13 / 0). 0 orphan messages.
- 5 smoke sample accounts with their projects (table above) — kept as evidence, per step 3.
- 1 `qa-pos***@example.com` — post-deploy tooling with an INTERNAL_QA entitlement and a build; kept until decided.

**Deliberately NOT deleted:** 388 `intake_reservations` rows of the deleted accounts. They are the money ledger
(quotes, settlements, releases); a ledger is not cleaned with its customers. They reference account ids as text (no
foreign key), so nothing dangles structurally.

**Not fixed by this:** every preview deployment still creates a new smoke account in the production DB (item 72).
The count will grow again until previews are isolated.

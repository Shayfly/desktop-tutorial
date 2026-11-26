# 148AI — Shared Tasks

| ID | Owner | Status | Evidence |
|---|---|---|---|
| CAPS-A | Claude Code | Implemented, verified locally; branch not pushed | `claude/practical-hopper-oi3qj2-caps-a`; tests/test_content_corrections.py, test_item_maxima.py, test_silent_cuts.py, test_preview_lifetime.py, test_approval_lifetime.py, test_conversation_history.py, test_upload_counts.py, test_plan_view_promises.py; controls 34/34 new; STATUS.md 2026-11-26 |
| RED-EVIDENCE | Claude Code | Local commits, not pushed; HOLD for CI, the main session's dispatches and the owner's answer on S4.2 (money) | `claude/practical-hopper-oi3qj2-red-evidence`: vision 43689691749 and model 42527017456 re-cited (green, read 2026-11-26); crash evidence removed, Golden 5 FAIL, crash-verify checks S4.2; 39377332673 still listed; controls vision_probe_step 3/3, model_probe_runs 3/3, postdeploy_crash_agent_graph 2/2, postdeploy_crash_resume 5/5, paid_build_red_run 4/4, evidence_runs 52/52; STATUS.md 2026-11-26; review of 78d3b79 fixed in separate commits (stage read tested, R4b/R4c caught; records corrected; nits), declarations 712 -> 713 |
| A1-RELEASE | Claude Code | Released | #531 `8b7d204` -> `ac10e94` [release], #533 `91290f8` -> `8911e32` [release]; runs 45702506669, 45702519795; deploy-worker 45699791750, 45709671445; STATUS.md 2026-11-26 |
| LAWS-5-6 | Claude Code | Merged | #534 `9d04b99` -> `4690d01`; STATUS.md 2026-11-26 |
| LAWS-2-6 | Claude Code | Merged (CI only, no release) | #535 `5bf1522` -> `fa41a5d`; CI 25 passed; supersedes the rows LAW2-EVIDENCE-RUNS and LAW6-FRESHNESS-ISSUES below; STATUS.md 2026-11-26 |
| REPLAY-530 | Claude Code (the owner merged #530) | Merged with a defect, not deployed; fix in the sites bundle | #530 `be137fd` -> `5bcfefe`; fix `9272dee`; 19 pg tests; controls 15/15 and 7/7; STATUS.md 2026-11-26 |
| S1-GOV | Claude Code (the owner merged #532) | Merged; 23 review fixes on a follow-up branch | #532 `d7b861d` -> `18dba53`; v24-ci negative-controls timeout, run 45713038574; STATUS.md 2026-11-26 |
| GOA-ROUTE | Claude Code | In progress | bld_3938e570; branch route-honesty |
| FLEET-ROOTS | Claude Code | In progress | diagnosis w2fwdjhzk; branches image-subject, repair-converge |
| TENANT-S4.5 | Claude Code | In progress | branch tenant-isolation |
| MEDIA-137 | the owner | In the warehouse (item 137) | the owner, 2026-11-26: music and video wait; STATUS.md 2026-11-26 |
| LAW2-EVIDENCE-RUNS | Claude Code | Implemented with review fixes, verified locally; branch not pushed; real read-only run exit 0 (18 of 22 green, 4 known red listed in docs/evidence-runs-known-red.json, not fixed) | `claude/practical-hopper-oi3qj2-law2-evidence`; `scripts/resolve_evidence_runs.py`, `.github/workflows/evidence-runs.yml`; tests 76 passed, controls 52/52; STATUS.md 2026-11-25 |
| LAW6-FRESHNESS-ISSUES | Claude Code | Implemented with review fixes, verified locally; branch not pushed | `.github/workflows/critical-path-freshness.yml` issue step (not-verified titles, close on PASS); tests 22 + 8 passed, controls 25/25 + 3/3; STATUS.md 2026-11-25 |
| AGENT-SKILLS-525-APPROVAL | Codex | Owner approved exact declarations; HOLD for CI and independent merge review | #525, approved candidate `e1c8a7d7`, base `042253f5`; STATUS.md 2026-11-25 |
| AGENT-SKILLS-525-REVIEW | Codex, independent automated reviewer | HOLD — follow-up verified locally, pending refreshed declarations, CI and independent review | #525 head `2cda8073`, base `042253f5`; `test_terminal_skill_execution_evidence.py`, `test_repair_request_fidelity_routes.py`, `test_intake_checklist_priority.py`; STATUS.md 2026-11-25 |
| AGENT-SKILLS-525 | chatgpt-integration | Owner declarations approved; exact-head CI and independent review pending | #525; prior head `4edde619`, main `042253f`; STATUS.md 2026-11-25 |
| AGENT-A1-524 | chatgpt-integration | Owner declaration approved; fresh CI and independent review pending | #524, previous head `a5fe405`, base `4e45b3a`; STATUS.md 2026-11-24 |
| WH-133 | Codex (design and integration, `4457710`), Claude Code (independent review, fixes, release) | Merged and released | #503 `adea624` -> `e5bf2ac` [release]; Vercel `dpl_Ax13GhrAyzxY4Bv7DcbHo9LY6MCk` READY, deploy-worker 45072002228; `tests/platform_a11y_browser.cjs`, `tests/workspace_review_fixes_browser.cjs`; review T1-T3 in UI-TESTS |
| IMG-DEFAULT-HERO | Claude Code | Merged (#519 `c43095c`); awaiting `[release]` and the worker run | `tests/test_default_hero_never_fails_the_build.py`; controls default_hero_never_fatal 5/5; STATUS.md 2026-11-23 |
| CHAT-PHONE | Claude Code | Merged (#518 `e93d01b`); awaiting `[release]` | `tests/phone_chat_browser.cjs` 6/6; STATUS.md 2026-11-23 |
| CONV-ADD-NOT-ASK | Claude Code | Not started | ShayFly prj_5wRH_CceL2aSeQ lost its packages to "what is right?" |
| UI-EVERYONE | Claude (the owner's order, 2026-11-22) | PR pending CI and the owner's SHA approval | `claude/platform-for-everyone`; `tests/platform_for_everyone_browser.cjs`, `tests/test_platform_for_everyone_in_ci.py`; STATUS.md 2026-11-22 |
| GOV-01 | Codex | In review | `VISION_LAW_HE.md`, PR pending independent verification |
| GOV-02 | Codex | In review | `AGENTS.md`, `NORTH_STAR.md`, SHA c8827818e3ffeb9ac49ba00c5d2b6efa6f8ff0d8 |
| GOV-03 | Codex | In progress | Root `STATUS.md`, `TASKS.md`, `OWNERS.md` |
| QA-152 | Matt | Pending verification | PR #152; negative controls, approval boundary, multilingual cost range |
| BENCH-01 | Codex | Blocked: keys and approved budget | Landing page with intro song; cost per accepted output |
| ITEM-3 | Codex | Draft; independent review required | plan reserve allowance boundary tests; item3 NC |
| ITEM-5 | Codex | Draft; independent review required | visible delegated default, history replay and item5 NC |
| ITEM-4 | Codex | Draft; independent review required | structured allowance error, real JS explain tests and item4 NC |
| ITEM-2 | Codex | Draft; PostgreSQL evidence pending CI | zero-contact refund test and item2 NC; independent review required |
| WH-01 | Claude Code | In review | `WAREHOUSE.md` created from the owner's list (2026-11-15); label `warehouse` on #323 |
| WH-111 | Claude Code | Merged | #413 (`00ccc19` -> `c38fbb4`) worker deploys only on a release; #414 (`c824c13` -> `ba2a934`) the mark counts only at the end of the merge title; live: Vercel CANCELED on `ba2a934`, worker `deploy` skipped on `d3c5e6b`, `b5b36a2` |
| GATES-1 | Claude Code | Merged | #415 (`b257030` -> `d3c5e6b`) G3 (falls on the real butcher page), G4 warn until WH-114, G6; every gate states its mode on every build |
| WH-112 | Claude Code | Merged | #416 (`9c3869a` -> `aee07af`) every test file is run by a CI job; 13 pg files run alone; 3 named in `tests/pg_not_yet_run.txt` |
| WH-107 | Claude Code | Merged; blocked on the owner's secret | #417 (`48d616c` -> `27d19b1`); the secret `CUSTOMER_STORAGE_STATE` is the owner's to create |
| WIN-APPROVE | Claude Code | Merged | #418 (`5a552a9` -> `b5b36a2`) window approval; v24-ci reads its own pytest report (test job 20+ -> 13 min) |
| WH-105 | Claude Code | Merged | #419 (`62e164f` -> `4498ec6`) colours by business category from a data file |
| GATES-2 | Claude Code | Merged | #420 (`0e0f5fa` -> `72735ef`) HE, G10, G11, G1, BRAND, SHARE; each falls on the real page |
| DOORS-ASSET | Claude Code | Merged; reaches production only on a release | #421 (`32cac99` -> `b761003`); Vercel production CANCELED on `b761003`, worker `deploy` skipped |
| FAST-402 | Claude Code | Merged | #402 (`b7f4980` -> `a4a0845`) the fast suite: 172 files, 21.7 s of a 30 s budget; NC 2/2 |
| OPS-403 | Claude Code | In review | #403 (orphaned) `scripts/commit_resolved.sh`: the CLAUDE.md conflict with main resolved and committed with the script itself (exit 0) |
| PRELIVE-405 | Claude Code | Waiting for the owner's signature on 5 declarations | #405 (orphaned) checked against main: needs_env, the `light` CI job (blocks an undeclared deleted line; the owner 2026-11-16), a2 109/110, the capture message, photo places; the draft skip of `test` is not carried |
| WH-114 | Claude Code | Open | the hero image inlined as 1.7MB base64; G4 warns on it |
| WH-118 | Claude Code | Implemented locally; not pushed; needs the owner's identity signature (preview_smoke) | images as files (`repository_assets`), five points plus gate regression, visual-edit host and the download carried; the smoke checks every resolved reference; `images_as_files` NC 19/19; G4 stays warn (STATUS 2026-11-21, 2026-11-22); branch `claude/practical-hopper-oi3qj2-images-as-files-2` |
| REL-1116 | Claude Code | Done | #422 `349d729` -> `4e16eeb` (worker: run 43973795367); #405 `795bbae` -> `1dc1fbd` |
| GATE-G5 | Claude Code | In review | the rights gate: 3 units (image, font, media and frames), registry `rights_sources.json` with a basis per source; an unknown source blocks; reads every served file as written; rewritten after an independent review found holes; NC 20/20 |
| AGENT-A7 | Claude Code | Next | the rights agent, after its gate G5 |
| STAGE-A-456 | Claude Code | Done | #423 `0ebb903` -> `dfe6817` |
| STAGE-A-3 | Claude Code | In review | worker death: build ends itself; NC 9/9; warehouse 115 |
| DEAD-END | Claude Code | In review | 80 of 252 walks stuck -> 0; NC 5/5 |
| GATES-WARN | Claude Code | In review | six uncalibrated gates warn; rehearsal runs the worker gates; NC 6/6 |
| W114-A | Claude Code | In review | web-sized rendition of uploaded and generated images; NC 8/8 |
| G5-WARN | Claude Code | In review | rights gate rewritten; enters at warn; NC 20/20 |
| A4-1 | Claude Code | In review | asset plan: one place per image; warn check; NC 10/10 |
| G8-1 | Claude Code | In review | runtime and load gate on real servers; enters at warn |
| G-APPLE | Claude Code | In review | design contract + static + render + two reviewers, warn; mutations and block tomorrow (owner) |
| PR-426 | Claude Code | Done | #426 `95f851c` -> `609929e` (G-APPLE, G5, A4-1, G8-1, game gate, registry) |
| A4-2 | Claude Code | In review | A4 decides the picture count (up to 3); planner writes quantity; NC 7/7 |
| PR-427 | Claude Code | Done | #427 `360080d` -> `d29d8da` (A4 picture count) |
| SYNTAX-LINE | Claude Code | In review | a syntax failure carries the line itself; NC 4/4; found by rehearsal 44042316516 |
| PR-428 | Claude Code | Done | #428 `8e26a8f` -> `4d9b1fb` (syntax message carries the line) |
| APPLE-CARRIED | Claude Code | In review | the design contract rides the spec word for word; rehearsal installs the request; reviewers told they see one screen; NC 8/8 + 2/2 |
| PR-429 | Claude Code | Done | #429 `7b45e1d` -> `b38b471` (contract carried; rehearsal installs the request) |
| GATE-RULES | Claude Code | In review | the generator is told what the installed gates check; NC 6/6 |
| PR-430 | Claude Code | Done | #430 `4b925d1` -> `1da851d` (gate checks reach the generator) |
| CONTRACT-LINES | Claude Code | In review | the contract keeps the approved text line by line; NC 10/10; full suite 3764/0 |
| PR-431 | Claude Code | Done | #431 `d3e1dd2` -> `4071192` (contract keeps lines) |
| CALIB-3 | Claude Code | In review | three calibration builds P0=0; hero rule; notice says what was measured; NC 3/3 |
| PR-432 | Claude Code | Done | #432 `e49b3c0` -> `a9c97b6` (hero rule; notice says what was measured) |
| CHAIN-BOUND | Claude Code | Done | #433 `96958b3` -> `7596591`, released |
| BRIEF-KEPT | Claude Code | Done | #434 `01e39ab` -> `69a308c`, released |
| REHEARSAL-POLICY | Claude Code | In review | the rehearsal asks the release policy; NC 5/5 |
| REHEARSAL-POLICY-DONE | Claude Code | Done | #435 `cdc0bb3` -> `0316cbe` |
| DOORS-FOLLOWUP | Claude Code | In review | doors palette; measure rule 35rem; no phone from a hash; NC 3/3 + 1/1 (content-only fix withdrawn: DECISIONS 9) |
| DOORS-FOLLOWUP-DONE | Claude Code | Done | #436 `6ad3eed` -> `227d23c`, released |
| CONTENT-ONLY-ASKED | Claude Code | In review | the content-only / personal-details conflict is asked in words, not dropped; NC 5/5 |
| AGENT-1 | Claude Code | In review | conversation agent phase 1: no question cards, questions in words, typed answers; NC 6/6 |
| AGENT-1-DONE | Claude Code | Done | #438 `f22c53d` -> `acbbbc8`, released |
| AGENT-2 | Claude Code | In review | the model asks customer decisions in its own words (ask_next); checklist from the request; NC 5/5 |
| AGENT-2-DONE | Claude Code | Done | #439 `a10a0a7` -> `ee2d7ca`, released |
| AGENT-3 | Claude Code | In review | exact hand-off: facts and page structure reach the generator; NC 6/6 + 6/6 |
| AGENT-3-DONE | Claude Code | Done | #440 `7087e3c` -> `8d37478`, released |
| AGENT-4-PREP | Claude Code | In review | Sonnet for conversation; per-account flag; classification corpus (101); Hebrew whole words; rehearsal tool |
| D5-HERO | Claude Code | In review | default hero for content sites; the brief's text-logo line no longer orders an icon; NC 5/5 |
| D8-TEST-EDITS | Claude Code | In review | `omni_prod/test_edit_guard.py`: expected values only, customer facts frozen, counted, twice escalates; NC 7/7 |
| D7-NEAREST | Claude Code | In review (part 1) | nearest-category palette; part 2 (the colour question) after the owner's human test; NC 5/5 |
| AGENT-FLAG | Claude Code | Done | #441 `81e24c4` -> `f14b773`; Vercel `OMNI_INTAKE_AGENT=accounts`, owner's account only; redeploy `dpl_6cVPvSHA23juKTo3nQ1LETaGZUBD` |
| METER-CALL-ID | Claude Code | In review | the meter prices ONE call by its id (owner 2026-11-18): ten turns give ten sums; no id, no ledger or an untagged attempt is loud, never $0; every routed rehearsal cost to date invalid; review fixes (lane, warnings, dropped id, skip event); NC 24/24 (NC1 permanent) |
| METER-CALL-ID-DONE | Claude Code | Done | #451 `4b3b329` -> `9aee98a` |
| QUOTA-REPAIR-STOP | Claude Code | In review | a repair call with a no-credit route keeps the verified build (ProviderQuotaUnavailable by type, #448 follow-up); NC 4/4 |

| DIRECT-MODELS | Codex | PARTIAL; independent review and runtime canaries pending | Branch codex/add-provider-models-20261118; 109 passed, 1 skipped, 9 subtests; docs/DIRECT_MODEL_ENROLLMENT_HE.md |
| RUN-COSTS | Codex | Read-only export independently verified against production on PR #454 | [SQL](scripts/observed_model_costs.sql), based on `9bc130e` |
| QUOTA-REPAIR-STOP-DONE | Claude Code | Done | #452 `f961661` -> `9bc130e` |
| D10-FOLLOWUP | Claude Code | In review | the review's remaining findings: in-flight holds, sticky closed state, wording by kind, busy keeps the summary, EXECUTING is busy, unknown tokens None, fallback logged; NC 10/10 + pg 10/10 |
| D10-LIMIT | Claude Code | In review | a conversation at its limit stops gracefully: typed limit, closing reply with the summary or one open question in words (read for free), no 'provider busy'; NC 15/15 |
| D10-TURNS | Claude Code | In review | the agent's 8-turn cap in reserve() (contacted calls only, under the locks) and tokens and cost per conversation; NC 8/8 + pg 7/7 |
| D10-SONNET | Claude Code | In review | Sonnet for the conversation agent only (ordered Venice profile, Haiku when Sonnet is not offered); rehearsal agent path; NC 9/9 |
| FINDING-ATTRIBUTION | Codex | Done | #463 b327fb0 → 0ed3d0e (recorded by Claude Code 2026-11-22; Codex's #476 said the same and is closed) |
| CRITICAL-PATH-FRESHNESS | Codex | Done | #464 db1055a → 5ee4395 (recorded by Claude Code 2026-11-22; Codex's #476 said the same and is closed) |
| DIRECT-ENROLL-NC | Codex | Local controls passed, pending independent review | #453, tests/negative_controls/direct_model_enrollment.json |
| OVERLAY-ACCEPTANCE-W | Codex | Draft; awaiting CI and independent review | GitHub run 44479691814, job 135408636414 |
| DRILLS-2026-11 | Claude Code | Done | C16 PASS 44932418710; C19 PASS 44932702825; C11 PASS 44933990232; C18 FAIL on the alert 44935937685, alert half PASS 44942838520 after #487; recorded in #483 (`bed3fa6` -> `86dfb69`) |
| WH-121 | Claude Code | Merged | #487 (`6f5d1ff` -> `0625996`) the dead-worker alert every 5 minutes; drill run 44942838520 opened and closed #489; live run 44942942630: 1 live worker |
| CUST-LOGIN | Claude Code | PR #490 | Customer session logs in by itself; blocked on the owner's two secrets CUSTOMER_TEST_EMAIL / CUSTOMER_TEST_PASSWORD |
| CI-REPORT-146 | Claude Code (was Codex) | Branch ready | the main CI report goes to the run summary and an artifact; #146 closes when it merges |
| PATHS-FRESH | Claude Code (was Codex) | Branch ready | rehearsal publish-taxonomy never pushes to main; verify-replay run 44941296147 PASS (10 versions) |
| ACCEPT-W-477 | Claude Code (was Codex) | In review | #477 AcceptanceW offline; the 600 s ceiling to be measured here |
| DRILLS-AUTO | Claude Code (was Codex) | Not started | monthly C16/C19/C11 as scheduled workflows; an issue 7 days before a drill is due |
| NODE24 | Claude Code (was Codex) | Not started | 39 workflow files on actions/checkout@v4, 16 on setup-python@v5 |
| AGENTS-DRIFT | Claude Code (was Codex) | Not started | AGENTS.md rules 1 and 4 say NOT ENFORCED; C16 is live since 2026-10-20 and critical-path freshness runs daily |
| YIELD-DB | Claude Code | Not started | first_pass_yield (the founder's metric, 2026-10-19) from build_jobs, daily: 11 of 48 builds ready in 35 days, 0 first-pass (Neon, read-only, 2026-11-21) |
| SITE-CONTENT-1 | Claude Code | Local commits, not pushed; review fixes committed (0eae688..422f929); CTO's full suite pending | content-document route slice 1 behind OMNI_SITE_LIBRARY (off); real-chain engine tests 6/6 with Chromium (CI: browser-python job, not yet run); NC site_content 44/44, section_library 7/7 default + 10/10 browser |
| ASK-NAME | Claude Code | Merged and released | #502 `90fd284` -> `473a820` [release]: the agent asks the business name; Vercel `dpl_3mpTtvrCEMSx1cDqvTrEm65FQADP` READY |
| ASK-COLOURS | Claude Code | Merged and released | #504 `ebd34df` -> `396d571` [release]: a business we do not know is asked about its colours (the owner, 2026-11-22); a WhatsApp answer keeps its role (task 62); Vercel `dpl_8tCnYrswwopYXpScShjYFQcxHvnt` READY |
| UI-LANGS | Claude Code | Merged and released | #505 `526928a` -> `e35f1b4` [release]: the platform in Hebrew, English and Arabic; `tests/ui_languages_browser.cjs` in CI; the server's fixed texts still reach Arabic customers in English; Vercel `dpl_86kVjp5UbA22jsJZ8TyyLTSRfVeK` READY |
| PATH-GUARD | Claude Code | Merged | #506 `0918f2b` -> `74243bf`: `codex/` and `design/` branches may not change the platform UI shell or the site engine (OWNERS.md, the owner 2026-11-22 evening) |
| UI-TESTS | Claude Code | In review | `claude/practical-hopper-oi3qj2-ui-tests`: #503 review T1 (the sidebar test and its 9 mutations run in CI on a development server), T2 (`tests/workspace_guards_browser.cjs`, 7 guards), T3 (status not read from a 503) |
| PLAN-S1-5 | Claude Code | #532 merged (`d7b861d` -> `18dba53`); follow-up on `claude/practical-hopper-oi3qj2-s1-governance-fixes`, HOLD for CI | the mapping in `docs/SYSTEM_MAP.md`, the full map as the v24-ci artifact `system-map`; `tests/test_system_map.py`; controls system_map 22/22; STATUS.md 2026-11-26 |
| PLAN-S1-6 | Claude Code | Merged (#532 `18dba53`) | AGENTS.md, the eleven development laws with their enforcement today; the follow-up adds the 2026-11-25 merge notes after lines 18 and 34 |
| PLAN-S1-7 | Claude Code | #532 merged; follow-up HOLD for CI | `scripts/check_pr_report.py` (code before comments; a revert by its branch and this repository; invisible text is not content), `.github/workflows/pr-report.yml` (reads `$GITHUB_EVENT_PATH`), the template; `tests/test_pr_report.py`; controls pr_report 45/45 |
| PLAN-S1-8 | Claude Code | #532 merged; follow-up HOLD for CI | OWNERS.md rules 1-12, `inbox/002-2026-11-25-owner-plan-v3.md` (plan v3 and the owner's messages verbatim, with their send times) |
| CI-NC-SHARDS | Claude Code | Follow-up branch, HOLD for CI | v24-ci negative-controls in 3 shards (`NC_SHARD`); main run 45713038574 timed out at 18 min (1,186 of the 1,217 controls that run in v24-ci; 31 left); controls nc_shards 10/10 |
| CI-NC-4SHARDS | Claude Code | Branch claude/practical-hopper-oi3qj2-nc-4-shards, HOLD for CI | v24-ci negative-controls in 4 shards (`NC_SHARD` i/4), 343 of 1,372 controls each (was 458/457/457); #537 run 45829940347 shard 2 of 3 took 14 min 45 s of the 18; controls nc_shards 10/10 |

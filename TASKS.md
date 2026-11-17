# 148AI — Shared Tasks

| ID | Owner | Status | Evidence |
|---|---|---|---|
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

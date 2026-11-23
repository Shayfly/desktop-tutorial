# 148AI — Role Ownership

| Domain | Owner | Verification |
|---|---|---|
| Product and intake | Claude Code | Matt or independent reviewer |
| Governance, CI, documentation | Codex | Matt or independent reviewer |
| Independent verification | Matt | Must not verify own authored changes |
| Irreversible decisions, paid provider routing, new spend, client approval flow | CEO | Explicit CEO approval before execution |

Ownership is responsibility-based, not a permanent file-path prohibition. All changes require evidence and the review rules in `AGENTS.md`.

## 2026-11-21 — the owner: only Claude Code works

The owner, 2026-11-21: "עזוב תעשה את כל המשימות שלו אתה של קודקס תמשיך אתה בנוסף לכל מה שיש לך לעשות ככה רק אתה עובד", and later
"סומך עלייך מאשר לך הכול". From that day Claude Code also owns **governance, CI and documentation** (the Codex row
above). The table above stays as the record of the earlier split.

Verification while one agent works: AGENTS.md forbids an agent approving its own change, and there is no second
agent. Until the owner names a human reviewer (Matt) for a change, each PR carries instead: CI green on its exact
head SHA, mutations that prove its tests catch the fault (`tests/negative_controls/`), an adversarial review by
separate agents, and a sentence in the report saying that the review was not a person's. Irreversible decisions stay
the owner's (the last row above); a destructive database write still needs the owner's word naming its target.

## 2026-11-22 (evening) — the platform UI shell moves to Claude Code

The owner, after Codex's design (warehouse 133) was released by Claude Code: "כל מה שאמרת לקודקס לעשות, אני מעביר אלייך
להמשיך כי אני יודע שעלייך אני יכול לסמוך !!! ואני לא רוצה שהוא ימשיך את הנושא הזה אלא אתה מכאן, אני צריך שתמשיך לפתח אותו
אם אתה חושב ולהעלות את המעודכן לרשת כמו שצריך". From then on:

- the platform UI shell (the table below) is Claude Code's, together with the customers' sites and their engine;
- Codex does not continue the UI: a `codex/` or `design/` branch changes neither the shell nor the engine
  (`scripts/path_ownership.py`, the `path-ownership` workflow, on every pull request);
- the tasks proposed to Codex that evening are Claude Code's too: a blocking WCAG 2.2 AA check for the platform UI,
  the platform UI in more languages (RTL and LTR), and the triage of Codex's open PRs;
- a sketch from Matt, when one comes, is still followed, and a deviation is one line in the PR with its reason.

The section below is the record of the earlier split.

## Platform UI shell — Matt designs (the owner, 2026-11-22)

Matt designs the platform's screens and delivers a sketch and a spec for each one. Claude implements a screen only after
the owner approves its sketch; a deviation from the sketch is one line in the PR with its reason. While Matt works,
no other agent edits these files (main is merged into branches as usual):

| Path | What it is |
|---|---|
| `omni_prod/assets/index.html` | the platform page |
| `omni_prod/assets/app.js` | every screen: conversation, approval, builds, balance |
| `omni_prod/assets/app.css` | the styles |
| `omni_prod/assets/visual-edit.js` | the visual edit screen |
| `omni_prod/assets/sw.js`, `omni_prod/assets/manifest.webmanifest` | the installed-app shell |
| `omni_prod/assets/brand/` | logo and icons (the platform's tokens are Matt's) |
| `ui/` | the old UI, no longer served; marked so nobody edits it by mistake |

One exception (the owner, 2026-11-22, "1. א"): a line of text in `app.js` that repeats a message the server sends may
follow the server's text, so the screen says what the server says (warehouse 132). No layout, style or structure.

Not the shell, and Claude's: the server code that serves these files (`omni_prod/investor_app.py`), the texts the server
sends (Python), the internal diagnostic page `omni_prod/assets/replicate-test.*`, and the customers' sites
(`omni_prod/section_library`, `omni_prod/site_content` -- warehouse 125, the contract for customers' sites).

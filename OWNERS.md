# 148AI — Role Ownership

| Domain | Owner | Verification |
|---|---|---|
| Product and intake | Claude Code | Matt or independent reviewer |
| Governance, CI, documentation | Codex | Matt or independent reviewer |
| Independent verification | Matt | Must not verify own authored changes |
| Irreversible decisions, paid provider routing, new spend, client approval flow | CEO | Explicit CEO approval before execution |

Ownership is responsibility-based, not a permanent file-path prohibition. All changes require evidence and the review rules in `AGENTS.md`.

## 2026-11-25 (19:28) — the owner's plan v3: Claude Code executes, ChatGPT reviews

This section is the rule in force; the sections below it are the record of how it came to be (inbox/002, plan v3,
part 1).

| Who | Does | Does not |
|---|---|---|
| Claude Code | executes every task of the plan: code, tests, CI, documentation, pull requests | merge its own pull request; approve its own work |
| ChatGPT | reviews: one comment per pull request on its full head SHA, starting "ביקורת ChatGPT על <SHA>" and ending PASS or FAIL with findings (file, line, what breaks) | write code in the repository, push, merge, fix a bug it found |
| The owner (Shai) | decides which Claude Code session works, approves each merge, decides money, providers, deletions and the customer's approval flow | — |

1. **Merge conditions:** CI green on the head SHA, a ChatGPT PASS on the same SHA, and the owner's approval. A push
   after the review voids it; a review on another SHA does not count.
2. **One Claude Code session works on the repository at a time.** On 2026-11-25 two sessions worked in parallel on the
   same files (#529, session_01ERUbRcwv8hSRuXZnDuhCtB; #530, session_01ERUbRfJvVMhK1YSeUCTduG); the owner picks the
   one that continues, and the other stops.
3. **ChatGPT's open pull requests (#455, #526) move to Claude Code:** reviewed, their worth moved to a new branch from
   main, the old one closed with a link and the reason.
4. **Language with the owner:** plain Hebrew; whatever the owner must decide is one clear question with options.
5. Stop and ask the owner before: spend, a migration, a provider change, a change to the customer's approval flow,
   and a deletion in production.
6. **Open pull requests: no limit.** Plan v3 capped open pull requests at 3; the owner cancelled the cap on
   2026-11-25 at 19:05 UTC ("מבטל את חוק מגבלת ה-3 PR, מעכשיו זה ללא הגבלה"). Every other condition above still
   holds for each pull request.
7. **The session that works, and the owner's approval (2026-11-25, 19:06 UTC):** "מאשר לך הכול, הכול אתה נבחרת לבנות
   לתקן לשדרג הכול אתה!!". As Claude Code read it, and stated back to the owner the same hour:
   - The session that continues is session_01ERUbRcwv8hSRuXZnDuhCtB. #530 moves to it; session_01ERUbRfJvVMhK1YSeUCTduG
     stops (it was idle when the decision was made).
   - The owner's approval is given for the open questions put to him that hour: the S1.5 state mapping; the merge of
     each pull request once its CI is green and ChatGPT has given PASS on its full head SHA; and the live Golden E2E run
     (S1.2) inside the $2 cap per build.
   - ChatGPT's review stays the independent review: the author still does not approve its own work (rule 1; AGENTS.md).

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

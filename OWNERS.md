# 148AI — Role Ownership

| Domain | Owner | Verification |
|---|---|---|
| Product and intake | Claude Code | Matt or independent reviewer |
| Governance, CI, documentation | Codex | Matt or independent reviewer |
| Independent verification | Matt | Must not verify own authored changes |
| Irreversible decisions, paid provider routing, new spend, client approval flow | CEO | Explicit CEO approval before execution |

Ownership is responsibility-based, not a permanent file-path prohibition. All changes require evidence and the review rules in `AGENTS.md`.

> **Note, 2026-11-25 (the owner's decision governs merges now):** the independent review is cancelled and Claude Code
> merges on the owner's standing approval with CI green on the exact head SHA (rule 1 of the section below;
> inbox/002). The table above and the review rules of `AGENTS.md` it points to are kept as the record of the earlier
> rule; where they ask for an independent verifier, rule 1 governs.

## 2026-11-25 — the owner's plan v3, and his decisions of the same evening

This section is the rule in force; the sections below it are the record of how it came to be. The owner's words are
in inbox/002 (plan v3 verbatim, and every message quoted here, with the minute it was sent); the quotes
below are shortened or normalised in spacing and punctuation, and inbox/002 has them exactly. The times are UTC. Where a
later decision changed plan v3, the plan's wording is kept beside it.

| Who | Does | Does not |
|---|---|---|
| Claude Code | executes every task of the plan: code, tests, CI, documentation, pull requests; merges a pull request under rule 1 | merge a head whose CI is not green on that exact SHA; sign a declaration in a person's name without the owner's instruction (CLAUDE.md §8) |
| The owner (Shai) | decides money, providers, deletions, the customer's approval flow and what is in the warehouse; can stop or reverse any merge | — |

1. **Merge conditions (the owner, 19:10):** CI green on the head SHA, and the owner's standing approval ("מאשר לך
   הכול אתה יד ימיני"). Claude Code merges, and reports the SHA and the merge commit (CLAUDE.md §2).
   - Plan v3 (19:28 local) also required a ChatGPT PASS on the same SHA and said Claude Code does not merge. The owner
     cancelled that review at 19:10: "מבטל את הביקורת של מאט. אמרתי לך אני סומך עלייך שתעשה מה שצריך למען המטרה של
     148AI". "Matt" is the independent reviewer of the table at the top of this file; in plan v3 that role was
     ChatGPT's.
   - What replaces it is weaker and is named as such: before a merge Claude Code runs its own review of the branch by
     separate reviewer agents and skeptics, and writes the result in the pull request. That is the author checking
     its own work, not an independent approval (AGENTS.md, law 7).
2. **One Claude Code session works on the repository.** On 2026-11-25 two sessions worked in parallel on the same
   files (#529, session_01ERUbRcwv8hSRuXZnDuhCtB; #530, session_01ERUbRfJvVMhK1YSeUCTduG). The owner chose at 19:04:
   "מאשר לך הכול, הכול אתה נבחרת לבנות לתקן לשדרג הכול אתה". session_01ERUbRcwv8hSRuXZnDuhCtB continues and takes
   #530; the other session was idle and stops.
3. **ChatGPT's open pull requests (#455, #526) moved to Claude Code:** reviewed, their worth moved to a new branch from
   main, the old ones closed with a link and the reason.
4. **Language with the owner:** plain Hebrew; whatever the owner must decide is one clear question with options. From
   19:04: now and then, a plain explanation of what the work means in practice and how it affects the product.
5. **Stop and ask the owner before:** a provider change, a change to the customer's approval flow, and spend that he
   has not already decided. Until 21:54 this rule also named a migration and a deletion in production; those are now
   rule 9.
6. **Open pull requests: no limit.** Plan v3 capped them at 3; the owner cancelled the cap at 18:57 ("מבטל את חוק
   מגבלת ה-3 PR, מעכשיו זה ללא הגבלה").
7. **The state mapping of the system map (S1.5)** is approved by the owner's general approval of 19:04 ("מאשר לך
   הכול , הכול אתה נבחרת לבנות לתקן לשדרג הכול אתה!!"), not by a word on the table itself. The rules the review of
   #532 added later (blocked wins over a tested connection; a role with unit tests only is not CONNECTED; the words
   INSUFFICIENT_CREDIT and CREDIT_EXHAUSTED) rest on his standing approval of rule 1; docs/SYSTEM_MAP.md marks them.
8. **Build cost limits and pricing are in the warehouse (the owner, 19:10):** "לגבי הגולדן כרגע אני מבטל הגבלת בניה
   אלא רק ספירה. אחרי שאני יסיים כמה פרוייקטים אני ידע עלויות וידע מה לתמחר! עד אז להשאיר את הנושא במחסן!"
   (WAREHOUSE.md, item 136). Until he takes it out: cost is counted, no new cost limit or price is built, and the
   limits that exist in the code are not changed. Whether the live Golden E2E build (S1.2) runs meanwhile is an open
   question to the owner; it is not run until he answers.
9. **SQL, migrations and deletions on production are approved (the owner, 21:54 and 21:55):** "אז אני מאשר לך אמרתי
   לך כבר גם לגבי הצהרות אני מאשר גם sql" (21:54:06). That "sql" covers migrations as well as fixes to data is Claude
   Code's reading: it wrote it back to him at 21:54:24 and asked to be corrected if it was wrong ("ככה אני מבין את
   האישור, ואם הבנתי לא נכון, תתקן אותי"), and he did not correct it. His next message, at 21:55:09, answered that
   reply's line on deleting customer data: "אם צריך לעשות מחיקה תעשה אתה מבין בזה". inbox/002 part B quotes the reply,
   marked as Claude Code's. Every such write, a deletion included, still goes through CLAUDE.md section 5, in its
   order: a Neon backup branch `backup-before-<what>-<date>`, a dry count of the rows, one transaction that verifies the
   old value of every row, and a separate verification query. Each deletion is reported to the owner: the table, the
   rows and their count, the backup branch, and the old values. The same messages approve the declarations Claude Code
   types in his name (CLAUDE.md section 8), each with its `signature_note`.
10. **The order of work (the owner, 22:14:35, 22:14:54 and 22:15:09):** "בניית משחקים ואפליקציות הכי חשוב", then
    "אחרי אתרים מעדיף שתבנה הכול ביחד" and "תמזג מה שאפשר" (two messages, which reached the session together at
    22:16:16). The customers' sites are finished first; after them everything is built together, games and apps first
    among it, and changes that can share one pull request are merged as a bundle. Music and video wait (the owner,
    2026-11-26 08:34; WAREHOUSE.md item 137).
11. **No image cap (the owner, 2026-11-26 08:49):** "אין דבר כזה תקרת תמונות לבטל מיד !". The owner cancelled the cap
    on generated pictures per build (`a4.FIRST_CAP` = 3, set on his own "up to 3 to start" of 2026-11-17) and every
    other limit on the number of pictures. The code on main still has them (`a4.FIRST_CAP`, `a4.MAX_ASSETS`,
    `image_match.MAX_IMAGES`, the Google adapter's 1 to 3): their removal is in progress on the branch
    `claude/practical-hopper-oi3qj2-image-subject` and ships with the sites bundle. For pictures, this takes the limit
    out of rule 8 and WAREHOUSE.md item 136. He asked in the same message for the list of the other limits a customer
    meets; each of them stays until he decides it.
12. **The limits a customer meets that are not money are cancelled (the owner, 2026-11-26 10:01):** "לגבי התקרות א׳",
    his answer (א) to Claude Code's question of 09:17 UTC (asked again until 10:01). (א) covers: the content route's
    single correction, which fails the build when it is not enough, becomes several corrections; the limit of 8 items
    (services or questions) is raised; the preview lives longer than one hour; every silent cut of the customer's words
    ends; and the subscription plans stop promising what the code does not keep (a project quota, a number of users,
    "priority build"). The money limits (credits, the monthly provider budget, the model budget per build, the
    conversation's $0.15 a project and $1 a day) stay in WAREHOUSE.md item 136 until he has cost data (rule 8). The work
    is in progress on the branch `claude/practical-hopper-oi3qj2-caps-a`; until it ships, the code on main still has
    these limits.

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

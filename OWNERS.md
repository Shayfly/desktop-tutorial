# 148AI — Role Ownership

| Domain | Owner | Verification |
|---|---|---|
| Product and intake | Claude Code | Matt or independent reviewer |
| Governance, CI, documentation | Codex | Matt or independent reviewer |
| Independent verification | Matt | Must not verify own authored changes |
| Irreversible decisions, paid provider routing, new spend, client approval flow | CEO | Explicit CEO approval before execution |

Ownership is responsibility-based, not a permanent file-path prohibition. All changes require evidence and the review rules in `AGENTS.md`.

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

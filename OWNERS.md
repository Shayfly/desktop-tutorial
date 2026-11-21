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


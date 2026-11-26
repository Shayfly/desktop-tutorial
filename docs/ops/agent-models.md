# Agents, models and escalation (the owner, 2026-11-26)

The owner's order of 2026-11-26: maximum quality, minimum time to finish, efficient cost. Every task goes to the
**fastest model that does it at the required quality**. A stronger model is used only where the task needs it.

## The four agents (`.claude/agents/*.md`)

| Agent | Model | Effort | Use for | Never for |
|---|---|---|---|---|
| `scout` | Haiku 5.5 (`haiku`) | low | finding files and code, mapping a module, reading CI and build logs, counting, summarising, plain docs drafts | a decision, a fix, a review verdict, security |
| `implementer` | Sonnet 5.5 (`sonnet`) | medium | a well-specified change: code, tests, negative controls, declarations | architecture choices, security or release reviews |
| `reviewer` | Opus 5.5 (`opus`) | high | adversarial review: security, tenant isolation, money, release reviews, another agent's branch before merge | writing the fix it found (AGENTS.md rule 1) |
| `architect` | Fable 5.2 (`fable`) | high | designs across subsystems, choices with lasting cost, root causes the others could not find, escalations | routine work: it is the slowest and most expensive |

The main session (Claude Code) orchestrates. It merges under OWNERS.md rule 1 and runs the production read-only queries
itself. It hands agents their data.

## Escalation

An agent that cannot finish at the required quality does not guess. It ends its report with one line:

```
ESCALATE: <the reason> -> implementer|reviewer|architect
```

The main session then re-runs the task one tier up, with the findings so far:

- `scout` → `implementer` (a change is needed) or `reviewer` (a judgement is needed);
- `implementer` → `architect`, when the brief does not settle a design question or the same step failed twice;
- `reviewer` → `architect`, when the question is architectural.

The tiers are not skipped downwards: a security or release review is never given to `scout` or `implementer`.

## Parallel work

- Agents run in parallel only when they do not touch the same files or the same worktree.
- One full suite runs at a time (the `SUITE_RUNNING` marker in the session scratchpad).
- One browser test runs at a time per port.
- The account has a 5-hour usage limit. On 2026-11-26 ten Opus agents in parallel reached it at about 11:00 UTC, and
  every agent stopped until 12:40. Keep about four heavy agents at a time. Search, log and documentation work goes to
  `scout`.

## Verified (2026-11-26)

The model names and their availability were checked in real runs before this file was written. Each model got the
same read-only search task, and the served model was read from the agent's transcript. The results are in the pull
request that added this file.

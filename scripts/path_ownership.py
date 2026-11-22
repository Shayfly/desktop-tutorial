"""Path ownership between agents, enforced on every pull request (the owner, 2026-11-22: "Codex is starting the new look
and design; make sure you do not collide").

Every agent pushes as the same GitHub user, so the branch prefix is the only name the check can read: `claude/` and
`codex/` and `design/` (AGENTS.md, OWNERS.md "Platform UI shell"). The split is OWNERS.md's:
  * the platform UI shell (Matt designs, Codex implements) -- a `claude/` branch may not change it, except a line of
    text in app.js that repeats a server message (the owner's "1. א"); that exception is said as a notice for the
    reviewer, since a script cannot tell text from layout;
  * the customers' sites and the engine that builds them (Claude's: warehouse 125, the content route, the conversation)
    -- a `codex/` or `design/` branch may not change them.
Any other branch, and every other path, is not judged here. A violation fails with the path and its owner.

usage: python scripts/path_ownership.py BRANCH BASE_REF        (prints ::error / ::notice lines; exit 1 on a violation)
"""
from __future__ import annotations

import subprocess
import sys

UI_SHELL = ('omni_prod/assets/index.html', 'omni_prod/assets/app.js', 'omni_prod/assets/app.css',
            'omni_prod/assets/visual-edit.js', 'omni_prod/assets/sw.js', 'omni_prod/assets/manifest.webmanifest',
            'omni_prod/assets/brand/', 'ui/')
TEXT_ONLY_EXCEPTION = 'omni_prod/assets/app.js'
SITE_ENGINE = ('omni_prod/site_content/', 'omni_prod/section_library/', 'omni_prod/typography/',
               'omni_prod/conversation/', 'omni_prod/intake/', 'omni_prod/discovery.py', 'omni_prod/fact_canon.py',
               'omni_prod/vertical_palettes.py', 'omni_prod/vertical_palettes.json', 'omni_prod/gate_words.py',
               'omni_prod/customer_words.py', 'omni_prod/build_announcement.py', 'omni_prod/app_states.py')
RULES = {'claude/': ('the platform UI shell (OWNERS.md: Matt designs, Codex implements)', UI_SHELL),
         'codex/': ("the customers' sites and the engine that builds them (OWNERS.md: Claude's)", SITE_ENGINE),
         # Codex pushed the platform design as design/148ai-full-workspace-133 (2026-11-22): a design branch is the
         # UI side too, so it does not change the customers' sites either
         'design/': ("the customers' sites and the engine that builds them (OWNERS.md: Claude's)", SITE_ENGINE)}


def owned(path: str, prefixes) -> bool:
    return any(path == p or (p.endswith('/') and path.startswith(p)) for p in prefixes)


def judge(branch: str, paths) -> tuple[list[str], list[str]]:
    """(errors, notices) for one branch's changed paths."""
    errors, notices = [], []
    for prefix, (whose, guarded) in RULES.items():
        if not branch.startswith(prefix):
            continue
        for path in sorted(set(paths)):
            if not owned(path, guarded):
                continue
            if prefix == 'claude/' and path == TEXT_ONLY_EXCEPTION:
                notices.append(f'{path}: allowed only as lines of text that repeat a server message (the owner, "1. א")'
                               ' -- the reviewer checks there is no layout, style or structure change')
            else:
                errors.append(f'{path} is {whose}; a {prefix} branch does not change it')
    return errors, notices


def changed(base: str) -> list[str]:
    out = subprocess.run(['git', 'diff', '--name-only', f'{base}...HEAD'], capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p.strip()]


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        raise SystemExit('usage: python scripts/path_ownership.py BRANCH BASE_REF')
    branch, base = args
    errors, notices = judge(branch, changed(base))
    for n in notices:
        print(f'::notice title=path ownership::{n}')
    for e in errors:
        print(f'::error title=path ownership::{e}')
    if not errors:
        print(f'::notice title=path ownership::{branch}: no path of the other agent changed')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

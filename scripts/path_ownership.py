"""Path ownership between agents, enforced on every pull request.

The owner, 2026-11-22 (evening), after Codex's platform design (warehouse 133) was released by Claude Code: "כל מה שאמרת
לקודקס לעשות, אני מעביר אלייך להמשיך ... ואני לא רוצה שהוא ימשיך את הנושא הזה אלא אתה מכאן". From then on Claude Code owns
the platform UI shell as well as the customers' sites and the engine that builds them (OWNERS.md). The check reads the
branch prefix, the only name it can read (every agent pushes as the same GitHub user): a `codex/` or `design/` branch
(Codex pushed the design as design/148ai-full-workspace-133) changes neither the platform UI shell nor the customers'
sites' engine. A `claude/` branch is not restricted here. Any other branch, and every other path, is not judged here.
A violation fails with the path and its owner.

usage: python scripts/path_ownership.py BRANCH BASE_REF        (prints ::error / ::notice lines; exit 1 on a violation)
"""
from __future__ import annotations

import subprocess
import sys

UI_SHELL = ('omni_prod/assets/index.html', 'omni_prod/assets/app.js', 'omni_prod/assets/app.css',
            'omni_prod/assets/visual-edit.js', 'omni_prod/assets/sw.js', 'omni_prod/assets/manifest.webmanifest',
            'omni_prod/assets/brand/', 'ui/')
SITE_ENGINE = ('omni_prod/site_content/', 'omni_prod/section_library/', 'omni_prod/typography/',
               'omni_prod/conversation/', 'omni_prod/intake/', 'omni_prod/discovery.py', 'omni_prod/fact_canon.py',
               'omni_prod/vertical_palettes.py', 'omni_prod/vertical_palettes.json', 'omni_prod/gate_words.py',
               'omni_prod/customer_words.py', 'omni_prod/build_announcement.py', 'omni_prod/app_states.py')
GUARDED = (('the platform UI shell (OWNERS.md: Claude Code, from the owner 2026-11-22)', UI_SHELL),
           ("the customers' sites and the engine that builds them (OWNERS.md: Claude Code)", SITE_ENGINE))
RESTRICTED = ('codex/', 'design/')


def owned(path: str, prefixes) -> bool:
    return any(path == p or (p.endswith('/') and path.startswith(p)) for p in prefixes)


def judge(branch: str, paths) -> tuple[list[str], list[str]]:
    """(errors, notices) for one branch's changed paths."""
    errors = []
    prefix = next((p for p in RESTRICTED if branch.startswith(p)), None)
    if prefix is None:
        return [], []
    for path in sorted(set(paths)):
        for whose, guarded in GUARDED:
            if owned(path, guarded):
                errors.append(f'{path} is {whose}; a {prefix} branch does not change it')
    return errors, []


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

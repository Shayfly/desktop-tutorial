"""Additive only, with every deletion bound to its digest (Michael 2026-11-15).

identity.yml (blocking mode) requires every line deleted from the anchor to be declared in
docs/identity/allowed-deletions.json. Until 2026-11-15 a declaration was keyed by PATH only and held forever: once a
file had one, any later deletion in that file passed on the old reason (#371: test_site_auth_v2.py and
test_gate_mutations_20261110.py passed on #335's allowances, whose reasons describe another change).

Now a declaration covers exactly one change: `deleted_sha256` is the sha256 of the lines that change deletes from that
file (the '-' lines of `git diff -U0 ANCHOR HEAD -- PATH`, in order, joined by '\\n'). A declaration without it, or with
another digest, covers nothing. A path may hold several declarations (a list), one per change. Each still needs a
reason and a reviewer who is not the author (Michael fix 4).

    python scripts/deletions_declared.py ANCHOR                 # check HEAD against ANCHOR (identity.yml)
    python scripts/deletions_declared.py ANCHOR --digest PATH   # the digest to declare for PATH
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

DECLARATIONS = Path(__file__).resolve().parent.parent / 'docs' / 'identity' / 'allowed-deletions.json'
_NOT_A_REVIEWER = {'', 'claude', 'author', 'pending'}


def _git(*args: str, cwd: str | None = None) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True, cwd=cwd).stdout


def deleted_lines(anchor: str, path: str, cwd: str | None = None) -> list[str]:
    out = _git('diff', '-U0', '--no-color', anchor, 'HEAD', '--', path, cwd=cwd)
    return [l[1:] for l in out.splitlines() if l.startswith('-') and not l.startswith('---')]


def files_with_deletions(anchor: str, cwd: str | None = None) -> list[str]:
    out = _git('diff', '--numstat', anchor, 'HEAD', cwd=cwd)
    files = []
    for line in out.splitlines():
        added, removed, path = line.split('\t', 2)
        if removed not in ('0', '-'):
            files.append(path)
    return files


def digest(lines: list[str]) -> str:
    return hashlib.sha256('\n'.join(lines).encode('utf-8')).hexdigest()


def entries_for(allowed: dict, path: str) -> list[dict]:
    value = allowed.get(path)
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def judge(allowed: dict, deleted: dict[str, str]) -> tuple[list[str], list[str], list[str], list[str]]:
    """deleted: path -> digest of its deleted lines. Returns (notices, undeclared, stale, unreviewed)."""
    notices, undeclared, stale, unreviewed = [], [], [], []
    for path, actual in deleted.items():
        entries = entries_for(allowed, path)
        if not any(e.get('reason') for e in entries):
            undeclared.append(path)
            continue
        match = next((e for e in entries if e.get('deleted_sha256') == actual and e.get('reason')), None)
        if match is None:
            stale.append(f'{path} (deleted {actual[:12]}; declared '
                         f'{", ".join((e.get("deleted_sha256") or "no digest")[:12] for e in entries)})')
            continue
        who = str(match.get('reviewer') or '').strip()
        if who.lower() in _NOT_A_REVIEWER or who == match.get('author'):
            unreviewed.append(path)
        notices.append(f'{path}: {match.get("reason")} (digest {actual[:12]}, author {match.get("author")}, '
                       f'reviewer {who or "NONE"})')
    return notices, undeclared, stale, unreviewed


def main(argv: list[str], cwd: str | None = None, declarations: Path | None = None) -> int:
    anchor = argv[0]
    if len(argv) == 3 and argv[1] == '--digest':
        print(digest(deleted_lines(anchor, argv[2], cwd)))
        return 0
    allowed = json.loads((declarations or DECLARATIONS).read_text(encoding='utf-8'))['allowed']
    deleted = {p: digest(deleted_lines(anchor, p, cwd)) for p in files_with_deletions(anchor, cwd)}
    notices, undeclared, stale, unreviewed = judge(allowed, deleted)
    for n in notices:
        print(f'::notice title=deletion::{n}')
    if undeclared:
        print(f'::error title=additive only::lines deleted from the anchor in {", ".join(undeclared)} without a declared reason')
    if stale:
        print(f'::error title=additive only::a declaration covers one change, bound by deleted_sha256; none matches: '
              f'{"; ".join(stale)} (scripts/deletions_declared.py ANCHOR --digest PATH gives the digest to declare)')
    if unreviewed:
        print(f'::error title=additive only::deletions in {", ".join(unreviewed)} have no reviewer note (a reviewer '
              f'other than the author must sign in docs/identity/allowed-deletions.json)')
    if undeclared or stale or unreviewed:
        return 1
    print(f'::notice title=additive only::{len(deleted)} file(s) with deletions, each declared for this exact change and reviewed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

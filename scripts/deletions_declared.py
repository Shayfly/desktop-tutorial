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
    python scripts/deletions_declared.py --anchor PR_BASE        # the anchor identity.yml measures from
    python scripts/deletions_declared.py ANCHOR --blob PATH     # the blob to declare for a binary PATH (law 6)

Law 6, no deleting evidence (the owner's development laws; audit 2026-11-25): `git diff --numstat` gives a binary file
"-" for its lines, so an image or archive deleted or rewritten under docs/evidence/ or smoke/ passed undeclared. Now
every binary file a change deletes or rewrites -- any path, like every deleted line -- needs a declaration in the same
`allowed` map bound by `deleted_blob`: the git blob id of the version it removes (`git show BLOB` shows that version).
A line digest (deleted_sha256) covers no binary and a blob covers no line; the reason and reviewer rules are the same.
A rename is a deletion at the old path. An added binary removes nothing and needs nothing.
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


def removed_binaries(anchor: str, cwd: str | None = None) -> dict[str, str]:
    """Law 6: path -> blob id of the anchor's version, for every binary file (numstat "-") this change deletes or
    rewrites. --no-renames: a moved binary is a deletion at its old path. Output this cannot read raises, never {}."""
    binary = set()
    for record in _git('diff', '--numstat', '--no-renames', '-z', anchor, 'HEAD', cwd=cwd).split('\0'):
        if record:
            added, removed, path = record.split('\t', 2)
            if (added, removed) == ('-', '-'):
                binary.add(path)
    fields = _git('diff', '--raw', '--no-renames', '--no-abbrev', '-z', anchor, 'HEAD', cwd=cwd).split('\0')
    if fields[-1] != '' or len(fields) % 2 != 1:
        raise ValueError(f'git diff --raw -z: {len(fields)} fields, not path pairs ending in NUL')
    out = {}
    for meta, path in zip(fields[0:-1:2], fields[1::2]):
        if not meta.startswith(':'):
            raise ValueError(f'git diff --raw -z: unreadable record {meta[:80]!r}')
        _, _, old, new, status = meta[1:].split(' ')               # ':100644 100644 OLD NEW M'
        if path in binary and status in ('M', 'D', 'T') and old != new:
            out[path] = old
    return out


def blob_view(allowed: dict, removed: dict[str, str]) -> dict:
    """judge() matches an entry's deleted_sha256. A removed binary's declaration is matched by its deleted_blob, so
    judge() sees each entry of that path with deleted_blob in that place: an entry without deleted_blob covers no
    binary, and a blob declared for an earlier version covers no later rewrite."""
    return {p: [dict(e, deleted_sha256=e.get('deleted_blob')) for e in entries_for(allowed, p)] for p in removed}


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


def rolling_anchor(pr_base: str, cwd: str | None = None) -> str:
    """The commit a PR's changes are measured from. On pull_request, actions/checkout checks out GitHub's merge commit
    (refs/pull/N/merge): its FIRST parent is the base branch exactly as merged. The event's base.sha is not that commit
    once main moves after the PR was opened (#371, 2026-11-15: anchor f02404a while main was be831c6, so #374's own
    deletions were charged to #371). Not a merge commit (push, schedule): the given base, else origin/main."""
    parents = _git('rev-list', '--parents', '-n', '1', 'HEAD', cwd=cwd).split()
    if len(parents) == 3:
        return parents[1]
    return pr_base or _git('rev-parse', 'origin/main', cwd=cwd).strip()


def main(argv: list[str], cwd: str | None = None, declarations: Path | None = None) -> int:
    if argv and argv[0] == '--anchor':
        print(rolling_anchor(argv[1] if len(argv) > 1 else '', cwd))
        return 0
    anchor = argv[0]
    if len(argv) == 3 and argv[1] == '--blob':
        removed = removed_binaries(anchor, cwd)
        if argv[2] not in removed:
            raise SystemExit(f'{argv[2]}: not a binary file this change deletes or rewrites (nothing to declare by blob)')
        print(removed[argv[2]])
        return 0
    if len(argv) == 3 and argv[1] == '--digest' and argv[2] in removed_binaries(anchor, cwd):
        raise SystemExit(f'{argv[2]} is binary: it is declared by deleted_blob (--blob {argv[2]}), not by a line digest')
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
    removed = removed_binaries(anchor, cwd)                          # law 6: a binary has no lines to digest
    b_notices, b_undeclared, b_stale, b_unreviewed = judge(blob_view(allowed, removed), removed)
    for n in b_notices:
        print(f'::notice title=deletion (binary)::{n}')
    for p in b_undeclared + b_stale:
        print(f'::error title=no deleting evidence::binary {p} deleted or rewritten without a declaration bound to the '
              f'removed version (deleted_blob; scripts/deletions_declared.py ANCHOR --blob PATH gives it)')
    for p in b_unreviewed:
        print(f'::error title=no deleting evidence::binary {p}: the declaration has no reviewer note (a reviewer other '
              f'than the author must sign in docs/identity/allowed-deletions.json)')
    if b_undeclared or b_stale or b_unreviewed:
        return 1
    print(f'::notice title=no deleting evidence::{len(removed)} binary file(s) deleted or rewritten, each declared for '
          f'the removed version and reviewed')
    if undeclared or stale or unreviewed:
        return 1
    print(f'::notice title=additive only::{len(deleted)} file(s) with deletions, each declared for this exact change and reviewed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

"""Law 5, no test is weakened to get green (the owner's development laws; audit 2026-11-25).

scripts/deletions_declared.py makes every DELETED line declare itself. A weakening that only ADDS lines passed every
check: a new skip or xfail marker, a skipTest call, `continue-on-error: true`, or a shell line that swallows a failure
(`|| true`, `|| :`, `set +e`). This reads the lines a change ADDS under tests/ and .github/workflows/, measured from the
merge base of HEAD with ANCHOR -- the anchor `deletions_declared.py --anchor` gives (on a pull request the first parent
of GitHub's merge commit, i.e. main as merged, which is then also the merge base) -- and fails on each added line that
introduces one of WEAKENINGS unless that exact line is declared and signed. A line already on main is never read.

The declaration lives in the deletions' file (docs/identity/allowed-deletions.json), under the key "weakening":
{PATH: [{reason, line_sha256, pr, author, reviewer, reviewed_at, ...}]}. line_sha256 = sha256(PATH + "\\n" + the added
line exactly as committed) (line_digest; every ::error prints it). A declaration covers that line in that file only.
The signing rule is the deletions' rule: a reason, and a reviewer who is not the author and not one of
deletions_declared._NOT_A_REVIEWER ('', claude, author, pending).

    python3 scripts/weakening_declared.py ANCHOR      # the light job (v24-ci.yml)

Exit 0: every added weakening is declared and signed (one ::notice with the counts). Exit 1: one ::error per added
weakening that is not. Exit 2: nothing was measured -- a git command failed or printed what this cannot read (the
-U0 diff and --numstat must agree line for line). An unmeasured change is an error, never a pass.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deletions_declared as DD  # noqa: E402  (one declaration file, one anchor, one signing rule)

SCOPE = ('tests', '.github/workflows')
# Lines a reader may take for a test or a check that still runs and still decides. Each name is what ::error shows.
WEAKENINGS = (
    ('pytest.mark.skip', re.compile(r'\bmark\.skip')),                    # skip and skipif, `from pytest import mark` too
    ('pytest.skip(', re.compile(r'\bpytest\.skip\s*\(')),
    ('skipTest(', re.compile(r'\bskipTest\s*\(')),
    ('unittest.skip', re.compile(r'\bunittest\.skip')),                   # skip, skipIf, skipUnless
    ('skipIf(', re.compile(r'\bskipIf\s*\(')),
    ('skipUnless(', re.compile(r'\bskipUnless\s*\(')),
    ('pytest.mark.xfail', re.compile(r'\bmark\.xfail|\bpytest\.xfail\s*\(')),
    ('expectedFailure', re.compile(r'\bexpectedFailure\b')),
    # any value but a literal false: an expression may be true
    ('continue-on-error', re.compile(r'\bcontinue-on-error\s*:(?!\s*[\'"]?(?:false|False|FALSE)[\'"]?\s*(?:#.*)?$)')),
    ('|| true', re.compile(r'\|\|\s*(?:/usr)?(?:/bin/)?true\b')),
    ('|| :', re.compile(r'\|\|\s*:(?=\s|;|\)|$)')),
    ('set +e', re.compile(r'\bset\s+(?:\+[A-Za-z]*e[A-Za-z]*|\+o\s+errexit)\b')),
)
_HUNK = re.compile(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@')
_DIFF = ('--no-color', '--no-ext-diff', '--no-textconv', '--no-relative', '-M')


class Unreadable(Exception):
    """git failed or printed what this cannot read: the change was not measured, which is never a pass."""


def _git(*args: str, cwd: str | None = None) -> str:
    proc = subprocess.run(['git', '-c', 'core.quotePath=false', *args], capture_output=True, cwd=cwd)
    if proc.returncode != 0:
        raise Unreadable(f'git {" ".join(args[:3])} exited {proc.returncode}: '
                         f'{proc.stderr.decode("utf-8", "replace").strip()[:300]}')
    try:
        return proc.stdout.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise Unreadable(f'git {" ".join(args[:3])} printed bytes that are not UTF-8 ({exc})') from exc


def merge_base(anchor: str, cwd: str | None = None) -> str:
    return _git('merge-base', anchor, 'HEAD', cwd=cwd).strip()


def added_lines(base: str, cwd: str | None = None) -> list[tuple[str, int, str]]:
    """(path, line number in HEAD, text) of every line added since base under SCOPE, from `git diff -U0`."""
    out = _git('diff', '-U0', *_DIFF, '--src-prefix=a/', '--dst-prefix=b/', base, 'HEAD', '--', *SCOPE, cwd=cwd)
    lines = out.split('\n')                     # never splitlines(): a form feed or U+2028 inside a line is content
    if lines[-1] == '':
        lines.pop()
    rows, path, number, in_hunk = [], None, 0, False
    for raw in lines:
        if raw.startswith('diff --git '):       # inside a hunk every content line starts with + - or \
            path, in_hunk = None, False
        elif raw.startswith('@@'):
            m = _HUNK.match(raw)
            if not m:
                raise Unreadable(f'unreadable hunk header {raw[:120]!r}')
            number, in_hunk = int(m.group(1)), True
        elif not in_hunk:
            if raw.startswith('+++ '):
                target = raw[4:].removesuffix('\t')       # git appends a tab to a name with a space
                if target.startswith('b/'):
                    path = target[2:]
                elif target == '/dev/null':
                    path = None
                else:
                    raise Unreadable(f'unreadable file header {raw[:120]!r}')
        elif raw.startswith('+'):
            if path is None:
                raise Unreadable(f'an added line with no file: {raw[:120]!r}')
            rows.append((path, number, raw[1:]))
            number += 1
        elif not raw.startswith(('-', '\\')):
            raise Unreadable(f'unreadable diff line in {path}: {raw[:120]!r}')
    return rows


def added_counts(base: str, cwd: str | None = None) -> dict[str, int]:
    """path -> lines added since base under SCOPE, from `git diff --numstat` (binary files have none)."""
    tokens = _git('diff', '--numstat', '-z', *_DIFF, base, 'HEAD', '--', *SCOPE, cwd=cwd).split('\0')
    counts, i = {}, 0
    while i < len(tokens):
        if tokens[i] == '' and i == len(tokens) - 1:
            break
        try:
            added, _removed, path = tokens[i].split('\t', 2)
            if path == '':                      # a rename: the old and the new path follow
                path, i = tokens[i + 2], i + 3
            else:
                i += 1
            if added != '-' and int(added):
                counts[path] = int(added)
        except (ValueError, IndexError) as exc:
            raise Unreadable(f'unreadable numstat record {tokens[i][:80]!r} ({exc})') from exc
    return counts


def measured(base: str, cwd: str | None = None) -> list[tuple[str, int, str]]:
    """The added lines, only when two readings of git agree: a parse that lost a line fails here, never passes."""
    rows = added_lines(base, cwd)
    parsed: dict[str, int] = {}
    for path, _, _ in rows:
        parsed[path] = parsed.get(path, 0) + 1
    counted = added_counts(base, cwd)
    if parsed != counted:
        differ = sorted(p for p in set(parsed) | set(counted) if parsed.get(p) != counted.get(p))
        raise Unreadable(f'the -U0 diff and --numstat disagree on {", ".join(differ[:5])} '
                         f'({[(p, parsed.get(p), counted.get(p)) for p in differ[:5]]})')
    return rows


def line_digest(path: str, line: str) -> str:
    return hashlib.sha256(f'{path}\n{line}'.encode('utf-8')).hexdigest()


def weakenings(rows: list[tuple[str, int, str]]) -> list[tuple[str, int, str, list[str]]]:
    found = []
    for path, number, text in rows:
        names = [name for name, rx in WEAKENINGS if rx.search(text)]
        if names:
            found.append((path, number, text, names))
    return found


def judge(declared: dict, found: list) -> tuple[list[str], list[tuple[str, int, str]]]:
    """Returns (notices, errors); an error is (path, line, message), one per added weakening not declared and signed."""
    notices, errors = [], []
    for path, number, text, names in found:
        digest = line_digest(path, text)
        what = f'{path}:{number} adds {", ".join(names)}: {text.strip()[:160]}'
        match = next((e for e in DD.entries_for(declared, path)
                      if e.get('line_sha256') == digest and e.get('reason')), None)
        if match is None:
            errors.append((path, number, f'{what} -- not declared (declare line_sha256 {digest} under "weakening" '
                                         f'-> "{path}" in docs/identity/allowed-deletions.json, with a reason and a '
                                         f'reviewer who is not the author)'))
            continue
        who = str(match.get('reviewer') or '').strip()
        if who.lower() in DD._NOT_A_REVIEWER or who == match.get('author'):
            errors.append((path, number, f'{what} -- declared but not signed by a reviewer other than the author '
                                         f'(author {match.get("author")}, reviewer {who or "NONE"})'))
            continue
        notices.append(f'{what} -- {match.get("reason")} (line {digest[:12]}, author {match.get("author")}, '
                       f'reviewer {who})')
    return notices, errors


def _data(text: str) -> str:
    return str(text).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def _prop(text: str) -> str:
    return _data(text).replace(':', '%3A').replace(',', '%2C')


def main(argv: list[str], cwd: str | None = None, declarations: Path | None = None) -> int:
    if len(argv) != 1 or argv[0].startswith('-'):
        print('::error title=law 5 (weakening)::usage: scripts/weakening_declared.py ANCHOR')
        return 2
    try:
        data = json.loads((declarations or DD.DECLARATIONS).read_text(encoding='utf-8'))
        declared = data.get('weakening', {})
        if not isinstance(declared, dict):
            raise Unreadable('"weakening" in the declarations file is not an object of paths')
        base = merge_base(argv[0], cwd)
        rows = measured(base, cwd)
    except (Unreadable, OSError, ValueError, AttributeError) as exc:
        print(f'::error title=law 5 (weakening)::{_data(f"nothing measured, which is never a pass: {exc}")}')
        return 2
    found = weakenings(rows)
    notices, errors = judge(declared, found)
    for n in notices:
        print(f'::notice title=weakening declared::{_data(n)}')
    for path, number, message in errors:
        print(f'::error file={_prop(path)},line={number},title=law 5 (weakening)::{_data(message)}')
    if errors:
        return 1
    print(f'::notice title=law 5 (weakening)::{len(rows)} line(s) added under {" and ".join(SCOPE)} since the merge '
          f'base {base[:7]}; {len(found)} weakening(s), each declared and signed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

"""Law 5, no test is weakened to get green (the owner's development laws; audit 2026-11-25; review fixes 2026-11-25).

scripts/deletions_declared.py makes every DELETED line declare itself. A weakening that only ADDS lines passed every
check: a skip or xfail, a swallowed exit code, a line that removes a test from what runs. This reads what a change adds
and deletes in the files that decide whether a test runs and whether a check decides, measured from the merge base of
HEAD with ANCHOR -- the anchor `deletions_declared.py --anchor` gives (on a pull request the first parent of GitHub's
merge commit, i.e. main as merged, which is then also the merge base) -- and fails on each weakening the change adds
that is not declared and signed for this change. A line already on main is never read.

How each file is read (family(); SCOPE is the git pathspec of all of them):
  python    tests/**/*.py: the PYTHON kinds, in code only (tokenize on the blob: a comment or a string literal only
            mentions a pattern), plus a use of any name the file binds to a skip function (an alias). A file that does
            not tokenize is read as raw text (a mention then counts too), with a ::notice.
  workflow  .github/workflows/*: the PYTHON and SHELL kinds on the raw line; a comment-only line is not read.
  js        tests/**/*.js, *.cjs, *.mjs: the JS kinds.
  runs      the files that decide what runs: any conftest.py (every added line holding code), the pytest section of
            any pytest.ini, tox.ini, setup.cfg or pyproject.toml, scripts/test_fast.sh and tests/needs_env.txt (every
            added line that is not blank or a comment): each such line is a weakening of its own kind.
  text      any other file under tests/: every kind, on the raw line.
  not read  tests/negative_controls/*.json: mutation text the runner applies to a throw-away copy; nothing there runs
            in the tree (a .py file in that directory IS read). Measured over the last 80 first-parent merges of main.

Net new: per (path, text), the flagged occurrences this change adds minus those it deletes from the same file (a move,
or an edit around a line, adds nothing; an edited flagged line is a new text and counts).

Declared: docs/identity/allowed-deletions.json, key "weakening": {PATH: [record, ...]}, one mechanism with the
deletions. A record covers ONE change (rule_2026_11_15): only records NEW in this change -- absent from the file at the
merge base -- count, and their counts must add up to exactly the net-new occurrences of that line:
  {"line_sha256": sha256(PATH + "\\n" + the line exactly as committed), "count": N (1 when absent), "reason", "pr",
   "author", "reviewer", "reviewed_at", "signature_note"}
Signed: a reason; an author; a reviewer who is not one of deletions_declared._NOT_A_REVIEWER and whose identity (the
first word of the name, case-folded) is not the author's; and a non-empty signature_note when an agent (an author who is
not one of PERSONS) wrote a reviewer who is not one of AGENTS, i.e. a person's name (CLAUDE.md section 8). A new record
that covers no net-new weakening is an error too. The 670 deletion records keep deletions_declared's own rule.

    python3 scripts/weakening_declared.py ANCHOR      # the light job (v24-ci.yml)

Exit 0: every net-new weakening is declared for this change and signed (one ::notice with the counts). Exit 1: one
::error per weakening that is not, and per new record that covers nothing; each says what to declare (the key, the
digest, the count). Exit 2: nothing was measured -- a git command failed, git printed a binary diff (--text is always
passed), the -U0 diff, --numstat and the blobs disagree, or a declarations file cannot be read. Never a pass.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deletions_declared as DD  # noqa: E402  (one declaration file, one anchor)

SCOPE = ('tests', '.github/workflows', 'scripts/test_fast.sh', ':(glob)**/conftest.py', ':(glob)**/pytest.ini',
         ':(glob)**/tox.ini', ':(glob)**/setup.cfg', ':(glob)**/pyproject.toml')
PYTEST_CONFIGS = ('pytest.ini', 'tox.ini', 'setup.cfg', 'pyproject.toml')
RUNS = {'scripts/test_fast.sh': 'a line of the fast suite', 'tests/needs_env.txt': 'a needs_env entry'}
CONFTEST, PYTEST_SETTING, ALIAS = 'a line of conftest.py', 'a pytest setting', 'skip alias'
NOT_READ = re.compile(r'^tests/negative_controls/[^/]+\.json$')
# Lines a reader may take for a test or a check that still runs and still decides. Each name is what ::error shows.
PYTHON = (
    ('pytest.mark.skip', re.compile(r'\bmark\.skip')),                    # skip and skipif, `from pytest import mark` too
    ('pytest.skip(', re.compile(r'\bpytest\.skip\s*\(')),
    ('skipTest(', re.compile(r'\bskipTest\s*\(')),
    ('unittest.skip', re.compile(r'\bunittest\.skip')),                   # skip, skipIf, skipUnless
    ('skipIf(', re.compile(r'\bskipIf\s*\(')),
    ('skipUnless(', re.compile(r'\bskipUnless\s*\(')),
    ('pytest.mark.xfail', re.compile(r'\bmark\.xfail|\bpytest\.xfail\s*\(')),
    ('expectedFailure', re.compile(r'\bexpectedFailure\b')),
    ('SkipTest', re.compile(r'\bSkipTest\s*\(|\braise\s+(?:\w+\.)*SkipTest\b')),   # raise unittest.SkipTest(, SkipTest(
    ('importorskip(', re.compile(r'\bimportorskip\s*\(')),
    ('bare skip', re.compile(r'(?<![\w.])(?<!def )skip\s*\(|@\s*skip\b')),        # from unittest/pytest import skip
)
SHELL = (
    # any value but a literal false (a quoted key too): an expression may be true
    ('continue-on-error', re.compile(r'\bcontinue-on-error[\'"]?\s*:(?!\s*[\'"]?(?:false|False|FALSE)[\'"]?\s*(?:[,}#]|$))')),
    ('|| true', re.compile(r'\|\|\s*(?:/usr)?(?:/bin/)?true\b')),
    ('|| :', re.compile(r'\|\|\s*:(?=\s|;|\)|$)')),
    ('set +e', re.compile(r'\bset\s+(?:\+[A-Za-z]*e[A-Za-z]*|\+o\s+errexit)\b')),
    ('|| echo', re.compile(r'\|\|\s*echo\b')),
    ('|| exit 0', re.compile(r'\|\|\s*exit\s+0\b')),
    ('if: false', re.compile(r'(?<![\w-])[\'"]?if[\'"]?\s*:\s*[\'"]?(?:false|\$\{\{\s*false\s*\}\})[\'"]?\s*(?:[,}#]|$)')),
)
JS = (
    ('.skip(', re.compile(r'\.skip\s*\(')),                                # test.skip( it.skip( describe.skip(
    ('xit(', re.compile(r'\bxit\s*\(')),
    ('xdescribe(', re.compile(r'\bxdescribe\s*\(')),
)
WEAKENINGS = PYTHON + SHELL + JS
_ALIAS_SOURCES = tuple(rx for name, rx in PYTHON if name not in ('importorskip(', 'SkipTest'))  # these return no skip
_ASSIGN = re.compile(r'^\s*([A-Za-z_]\w*)\s*=(?!=)(.*)$')
_IMPORT_AS = re.compile(r'\b(?:skip|skipIf|skipUnless|expectedFailure|xfail)\s+as\s+([A-Za-z_]\w*)')
_SECTION = re.compile(r'^\s*\[\[?\s*([^\[\]]+?)\s*\]\]?\s*(?:[#;].*)?$')
PERSONS = {'shai', 'michael'}                       # who signs (CLAUDE.md sections 1 and 8), by identity()
AGENTS = {'claude', 'codex', 'chatgpt', 'copilot'}  # the agents that write in this repository, by identity()
_HUNK = re.compile(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')
_DIFF = ('--no-color', '--no-ext-diff', '--no-textconv', '--no-relative', '-M', '--text')
DECLARATIONS_IN_REPO = 'docs/identity/allowed-deletions.json'


class Unreadable(Exception):
    """git failed or printed what this cannot read: the change was not measured, which is never a pass."""


def _git(*args: str, cwd: str | None = None) -> str:
    proc = subprocess.run(['git', '-c', 'core.quotePath=false', *args], capture_output=True, cwd=cwd)
    if proc.returncode != 0:
        raise Unreadable(f'git {" ".join(args[:3])} exited {proc.returncode}: '
                         f'{proc.stderr.decode("utf-8", "replace").strip()[:300]}')
    # A text file in another encoding is still read (its bytes become U+FFFD, the same in the diff and in the blob);
    # it must never make every later change exit 2.
    return proc.stdout.decode('utf-8', 'replace')


def merge_base(anchor: str, cwd: str | None = None) -> str:
    return _git('merge-base', anchor, 'HEAD', cwd=cwd).strip()


def family(path: str) -> str | None:
    name = path.rsplit('/', 1)[-1]
    if NOT_READ.match(path):
        return None
    if name == 'conftest.py':
        return 'conftest'
    if name in PYTEST_CONFIGS:
        return 'pytest-config'
    if path in RUNS:
        return 'runs'
    if path.startswith('.github/workflows/'):
        return 'workflow'
    if path.startswith('tests/'):
        if name.endswith('.py'):
            return 'python'
        if name.endswith(('.js', '.cjs', '.mjs')):
            return 'js'
        return 'text'
    raise Unreadable(f'{path} is in SCOPE but has no family')


def _header(text: str, prefix: str) -> str | None:
    target = text.removesuffix('\t')                    # git appends a tab to a name with a space
    if target == '/dev/null':
        return None
    if not target.startswith(prefix):
        raise Unreadable(f'unreadable file header {text[:120]!r}')
    return target[len(prefix):]


def changes(base: str, head: str = 'HEAD', cwd: str | None = None) -> list[dict]:
    """One dict per file pair under SCOPE: old and new path (None for /dev/null), the deleted lines (number in base,
    text) and the added lines (number in head, text), from `git diff -U0 --text`."""
    out = _git('diff', '-U0', *_DIFF, '--src-prefix=a/', '--dst-prefix=b/', base, head, '--', *SCOPE, cwd=cwd)
    lines = out.split('\n')                     # never splitlines(): a form feed or U+2028 inside a line is content
    if lines[-1] == '':
        lines.pop()
    pairs, cur, in_hunk, old_no, new_no = [], None, False, 0, 0
    for raw in lines:
        if raw.startswith('diff --git '):       # inside a hunk every content line starts with + - or \
            cur, in_hunk = {'old': None, 'new': None, 'deleted': [], 'added': []}, False
            pairs.append(cur)
        elif cur is None:
            raise Unreadable(f'diff output before any file: {raw[:120]!r}')
        elif raw.startswith('@@'):
            m = _HUNK.match(raw)
            if not m:
                raise Unreadable(f'unreadable hunk header {raw[:120]!r}')
            old_no, new_no, in_hunk = int(m.group(1)), int(m.group(2)), True
        elif not in_hunk:
            if raw.startswith('--- '):
                cur['old'] = _header(raw[4:], 'a/')
            elif raw.startswith('+++ '):
                cur['new'] = _header(raw[4:], 'b/')
            elif raw.startswith(('rename from ', 'rename to ')):  # a rename with no hunk has no --- / +++ lines
                side, name = ('old', raw[12:]) if raw.startswith('rename from ') else ('new', raw[10:])
                if name.startswith('"'):
                    raise Unreadable(f'unreadable rename header {raw[:120]!r}')
                cur[side] = name
            elif raw.startswith('Binary files '):
                raise Unreadable(f'git printed a binary diff although --text was given: {raw[:120]!r}')
        elif raw.startswith('+'):
            if cur['new'] is None:
                raise Unreadable(f'an added line with no file: {raw[:120]!r}')
            cur['added'].append((new_no, raw[1:]))
            new_no += 1
        elif raw.startswith('-'):
            if cur['old'] is None:
                raise Unreadable(f'a deleted line with no file: {raw[:120]!r}')
            cur['deleted'].append((old_no, raw[1:]))
            old_no += 1
        elif not raw.startswith('\\'):
            raise Unreadable(f'unreadable diff line in {cur["new"] or cur["old"]}: {raw[:120]!r}')
    return pairs


def numstat(base: str, head: str = 'HEAD', cwd: str | None = None) -> dict[str, tuple[int, int] | None]:
    """path (the new one of a rename) -> (added, deleted) lines under SCOPE, from `git diff --numstat`; None for a file
    git counts as binary ('-'): --numstat ignores --text for a .gitattributes `-diff` or `binary` path and for a file
    with a NUL byte, while the -U0 diff reads its lines all the same (measure() then checks them against the blobs)."""
    tokens = _git('diff', '--numstat', '-z', *_DIFF, base, head, '--', *SCOPE, cwd=cwd).split('\0')
    counts, i = {}, 0
    while i < len(tokens):
        if tokens[i] == '' and i == len(tokens) - 1:
            break
        try:
            added, removed, path = tokens[i].split('\t', 2)
            if path == '':                      # a rename: the old and the new path follow
                path, i = tokens[i + 2], i + 3
            else:
                i += 1
            if (added, removed) == ('-', '-'):
                counts[path] = None
            elif int(added) or int(removed):
                counts[path] = (int(added), int(removed))
        except (ValueError, IndexError) as exc:
            raise Unreadable(f'unreadable numstat record {tokens[i][:80]!r} ({exc})') from exc
    return counts


def _line_count(rev: str, path: str | None, cwd: str | None) -> int:
    if path is None:
        return 0
    blob = _git('cat-file', 'blob', f'{rev}:{path}', cwd=cwd)
    return blob.count('\n') + (1 if blob and not blob.endswith('\n') else 0)


def code_view(text: str) -> list[str] | None:
    """The lines of a Python blob with every string literal and comment blanked (tokenize), or None when it does not
    tokenize. Lines are split on '\\n' only, as git numbers them."""
    lines = text.split('\n')
    chars = [list(line) for line in lines]
    feed = iter([line + '\n' for line in lines[:-1]] + ([lines[-1]] if lines[-1] else []))
    try:
        for tok in tokenize.generate_tokens(lambda: next(feed, '')):
            kind = tokenize.tok_name.get(tok.type, '')
            if kind in ('STRING', 'COMMENT') or kind.startswith(('FSTRING_', 'TSTRING_')):
                (srow, scol), (erow, ecol) = tok.start, tok.end
                for row in range(srow, erow + 1):
                    line = chars[row - 1]
                    for col in range(scol if row == srow else 0, min(ecol if row == erow else len(line), len(line))):
                        line[col] = ' '
    except (tokenize.TokenError, SyntaxError, IndexError):
        return None
    return [''.join(line) for line in chars]


def aliases(view: list[str]) -> set[str]:
    """Names this file binds to a skip function: `needs_node = unittest.skipUnless(...)`, `from unittest import skip
    as later`, and a name bound to one of those. Bounded: each pass adds a name or stops."""
    names = {m.group(1) for line in view if re.match(r'\s*(?:from\s+\S+\s+)?import\b', line)
             for m in _IMPORT_AS.finditer(line)}
    assigns = [(m.group(1), m.group(2)) for line in view if (m := _ASSIGN.match(line))]
    for _ in range(len(assigns) + 1):
        known = re.compile(r'(?<![\w.])(?:' + '|'.join(map(re.escape, sorted(names))) + r')\b') if names else None
        grown = {name for name, rhs in assigns if name not in names
                 and (any(rx.search(rhs) for rx in _ALIAS_SOURCES) or (known and known.search(rhs)))}
        if not grown:
            break
        names |= grown
    return names


def _pytest_sections(text: str) -> list[bool]:
    inside, out = False, []
    for line in text.split('\n'):
        m = _SECTION.match(line)
        if m:
            name = m.group(1).strip().strip('"\'')
            inside = name in ('pytest', 'tool:pytest', 'tool.pytest') or name.startswith('tool.pytest.')
        out.append(inside)
    return out


def flagged(fam: str, rev: str, path: str, numbered: list[tuple[int, str]], cwd: str | None,
            notes: list[str]) -> list[tuple[int, str, list[str]]]:
    """(number, text, kind names) of each line in `numbered` (lines of path at rev); names empty = not a weakening."""
    view, sections, alias_rx = None, None, None
    if fam in ('python', 'conftest', 'pytest-config'):
        blob = _git('cat-file', 'blob', f'{rev}:{path}', cwd=cwd)
        blob_lines = blob.split('\n')
        for number, text in numbered:           # the diff and the blob must agree line for line
            if not 1 <= number <= len(blob_lines) or blob_lines[number - 1] != text:
                raise Unreadable(f'the diff and the blob of {path} at {rev[:12]} disagree at line {number}')
        if fam == 'pytest-config':
            sections = _pytest_sections(blob)
        else:
            view = code_view(blob)
            if view is None:
                notes.append(f'{path} at {rev[:12]} does not tokenize: read as raw text (a mention counts too)')
                view = blob_lines
            found = aliases(view)
            if found:
                body = '|'.join(map(re.escape, sorted(found)))
                alias_rx = re.compile(rf'@\s*(?:{body})\b|(?<![\w.])(?<!def )(?:{body})\s*\(')
    out = []
    for number, text in numbered:
        stripped = text.strip()
        if fam in ('python', 'conftest'):
            code = view[number - 1]
            names = [name for name, rx in PYTHON if rx.search(code)]
            if alias_rx and alias_rx.search(code):
                names.append(ALIAS)
            if fam == 'conftest' and code.strip():
                names.append(CONFTEST)
        elif fam == 'pytest-config':
            names = [PYTEST_SETTING] if sections[number - 1] and stripped and not stripped.startswith(('#', ';')) else []
        elif fam == 'runs':
            names = [RUNS[path]] if stripped and not stripped.startswith('#') else []
        elif fam == 'workflow':
            names = [] if stripped.startswith('#') else [name for name, rx in PYTHON + SHELL if rx.search(text)]
        elif fam == 'js':
            names = [name for name, rx in JS if rx.search(text)]
        else:
            names = [name for name, rx in WEAKENINGS if rx.search(text)]
        out.append((number, text, names))
    return out


def measure(base: str, head: str = 'HEAD', cwd: str | None = None) -> tuple[dict, int, list[str]]:
    """({(path, text): {lines, names, net}} of every net-new weakening, lines read, notes). The -U0 diff and --numstat
    must agree file by file: a parse that lost a line fails here, never passes. Where --numstat says binary, the parsed
    lines must agree with the blobs instead (added - deleted = the line counts' difference; exact for a new or deleted
    file, which is how a .gitattributes line once hid a whole new file)."""
    pairs = changes(base, head, cwd)
    parsed = {p['new'] or p['old']: (len(p['added']), len(p['deleted'])) for p in pairs if p['added'] or p['deleted']}
    counted = numstat(base, head, cwd)
    for key in [k for k, v in counted.items() if v is None]:
        pair = next((p for p in pairs if (p['new'] or p['old']) == key), None)
        old, new = (pair['old'], pair['new']) if pair else (key, key)          # no pair: a mode change only
        added, deleted = parsed.get(key, (0, 0))
        grown = _line_count(head, new, cwd) - _line_count(base, old, cwd)
        if grown != added - deleted:
            raise Unreadable(f'the -U0 diff of {key} (+{added} -{deleted}) disagrees with its blobs ({grown:+d} '
                             f'lines), and --numstat counts it as binary')
        if key in parsed:
            counted[key] = parsed[key]
        else:
            del counted[key]
    if parsed != counted:
        differ = sorted(p for p in set(parsed) | set(counted) if parsed.get(p) != counted.get(p))
        raise Unreadable(f'the -U0 diff and --numstat disagree on {", ".join(differ[:5])} '
                         f'({[(p, parsed.get(p), counted.get(p)) for p in differ[:5]]})')
    found, read, notes = {}, 0, []
    for p in pairs:
        key = p['new'] or p['old']
        new_fam = family(p['new']) if p['new'] else None
        old_fam = family(p['old']) if p['old'] else None
        if new_fam and p['added']:
            read += len(p['added'])
            for number, text, names in flagged(new_fam, head, p['new'], p['added'], cwd, notes):
                if names:
                    entry = found.setdefault((key, text), {'lines': [], 'names': [], 'added': 0, 'deleted': 0})
                    entry['lines'].append(number)
                    entry['added'] += 1
                    entry['names'] += [n for n in names if n not in entry['names']]
        if old_fam and p['deleted']:
            for _, text, names in flagged(old_fam, base, p['old'], p['deleted'], cwd, notes):
                if names and (key, text) in found:
                    found[(key, text)]['deleted'] += 1
    net = {}
    for key, entry in found.items():
        if entry['added'] > entry['deleted']:
            net[key] = {'lines': entry['lines'], 'names': entry['names'], 'net': entry['added'] - entry['deleted']}
    return net, read, notes


def line_digest(path: str, line: str) -> str:
    return hashlib.sha256(f'{path}\n{line}'.encode('utf-8')).hexdigest()


def identity(name) -> str:
    """'Claude Code', 'claude-code' and 'CLAUDE' are one identity: the first word of the name, case-folded."""
    words = re.split(r'[\s_-]+', str(name or '').strip().casefold())
    return words[0] if words else ''


def unsigned(record: dict) -> list[str]:
    """What a weakening record lacks to be signed; [] when it is."""
    problems = []
    if not str(record.get('reason') or '').strip():
        problems.append('no reason')
    author = str(record.get('author') or '').strip()
    reviewer = str(record.get('reviewer') or '').strip()
    if not author:
        problems.append('no author')
    if identity(reviewer) in {identity(n) for n in DD._NOT_A_REVIEWER}:
        problems.append(f'reviewer {reviewer or "NONE"} is not a reviewer')
    elif author and identity(reviewer) == identity(author):
        problems.append(f'reviewer {reviewer} is the author {author}')
    elif (identity(author) not in PERSONS and identity(reviewer) not in AGENTS
          and not str(record.get('signature_note') or '').strip()):
        problems.append(f'the author {author or "NONE"} wrote the name {reviewer} with no signature_note recording '
                        f'that person\'s instruction and its date (CLAUDE.md section 8)')
    count = record.get('count', 1)
    if type(count) is not int or count < 1:
        problems.append(f'count {count!r} is not a whole number of at least 1')
    return problems


def records(weakening, where: str) -> dict[str, list[dict]]:
    if not isinstance(weakening, dict):
        raise Unreadable(f'"weakening" in the declarations file ({where}) is not an object of paths')
    out = {}
    for path, value in weakening.items():
        entries = value if isinstance(value, list) else [value]
        if not all(isinstance(e, dict) for e in entries):
            raise Unreadable(f'"weakening" -> {path} ({where}) is not a record or a list of records')
        out[path] = entries
    return out


def base_records(base: str, declarations: Path, cwd: str | None) -> dict[str, list[dict]]:
    """The weakening records of the declarations file as it was at the merge base ({} where it did not exist)."""
    top = Path(_git('rev-parse', '--show-toplevel', cwd=cwd).strip()).resolve()
    try:
        rel = declarations.resolve().relative_to(top).as_posix()
    except ValueError as exc:
        raise Unreadable(f'{declarations} is not in the repository {top}: its merge-base version cannot be read') from exc
    if not _git('ls-tree', '-z', base, '--', rel, cwd=cwd):
        return {}
    return records(json.loads(_git('cat-file', 'blob', f'{base}:{rel}', cwd=cwd)).get('weakening', {}),
                   f'the merge base {base[:7]}')


def new_in_change(head: dict[str, list[dict]], base: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """The records of HEAD that the merge base does not hold (as a multiset: a copy of an old record is new)."""
    out = {}
    for path, entries in head.items():
        old = Counter(json.dumps(e, sort_keys=True, ensure_ascii=False) for e in base.get(path, []))
        fresh = []
        for e in entries:
            canon = json.dumps(e, sort_keys=True, ensure_ascii=False)
            if old[canon]:
                old[canon] -= 1
            else:
                fresh.append(e)
        if fresh:
            out[path] = fresh
    return out


def how_to_declare(path: str, digest: str, net: int) -> str:
    return (f'declare it in {DECLARATIONS_IN_REPO} with a NEW record under "weakening" -> "{path}": '
            f'{{"line_sha256": "{digest}", "count": {net}, "reason": "...", "pr": "...", "author": "...", '
            f'"reviewer": "...", "reviewed_at": "YYYY-MM-DD", "signature_note": "..."}} -- the reviewer is not the '
            f'author; an agent that writes a person\'s name records that person\'s instruction and its date in '
            f'signature_note; a record kept from an earlier change covers nothing')


def judge(found: dict, new: dict[str, list[dict]]) -> tuple[list[str], list[tuple[str, int | None, str]]]:
    """Returns (notices, errors); an error is (path, line or None, message)."""
    notices, errors, used = [], [], set()
    for (path, text), f in sorted(found.items(), key=lambda kv: (kv[0][0], kv[1]['lines'][0])):
        digest = line_digest(path, text)
        what = (f'{path}:{",".join(map(str, f["lines"]))} adds {", ".join(f["names"])} ({f["net"]} net new): '
                f'{text.strip()[:160]}')
        mine = [r for r in new.get(path, []) if r.get('line_sha256') == digest]
        used.update(id(r) for r in mine)
        if not mine:
            errors.append((path, f['lines'][0], f'{what} -- not declared for this change: '
                                                f'{how_to_declare(path, digest, f["net"])}'))
            continue
        problems = sorted({p for r in mine for p in unsigned(r)})
        if problems:
            errors.append((path, f['lines'][0], f'{what} -- declared but not signed: {"; ".join(problems)}'))
            continue
        declared = sum(r.get('count', 1) for r in mine)
        if declared != f['net']:
            errors.append((path, f['lines'][0], f'{what} -- the new record(s) declare count {declared}, this change '
                                                f'adds {f["net"]}: a record covers exactly the occurrences of one '
                                                f'change (set "count": {f["net"]} for line_sha256 {digest})'))
            continue
        notices.append(f'{what} -- {"; ".join(str(r.get("reason")) for r in mine)} (line {digest[:12]}, count '
                       f'{declared}, author {", ".join(str(r.get("author")) for r in mine)}, reviewer '
                       f'{", ".join(str(r.get("reviewer")) for r in mine)})')
    for path, entries in sorted(new.items()):
        for r in entries:
            if id(r) not in used:
                errors.append((DECLARATIONS_IN_REPO, None,
                               f'a new "weakening" record for {path} (line_sha256 {str(r.get("line_sha256"))[:16]}) '
                               f'covers no weakening this change adds: remove it, or correct its path or digest'))
    return notices, errors


def _data(text: str) -> str:
    return str(text).replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')


def _prop(text: str) -> str:
    return _data(text).replace(':', '%3A').replace(',', '%2C')


def main(argv: list[str], cwd: str | None = None, declarations: Path | None = None) -> int:
    if len(argv) != 1 or argv[0].startswith('-'):
        print('::error title=law 5 (weakening)::usage: scripts/weakening_declared.py ANCHOR')
        return 2
    path = Path(declarations or DD.DECLARATIONS)
    try:
        head = records(json.loads(path.read_text(encoding='utf-8')).get('weakening', {}), 'this checkout')
        base = merge_base(argv[0], cwd)
        new = new_in_change(head, base_records(base, path, cwd))
        found, read, notes = measure(base, 'HEAD', cwd)
    except (Unreadable, OSError, ValueError, AttributeError) as exc:
        print(f'::error title=law 5 (weakening)::{_data(f"nothing measured, which is never a pass: {exc}")}')
        return 2
    notices, errors = judge(found, new)
    for n in notes:
        print(f'::notice title=law 5 (weakening)::{_data(n)}')
    for n in notices:
        print(f'::notice title=weakening declared::{_data(n)}')
    for file, number, message in errors:
        where = f'file={_prop(file)}' + (f',line={number}' if number else '')
        print(f'::error {where},title=law 5 (weakening)::{_data(message)}')
    if errors:
        return 1
    print(f'::notice title=law 5 (weakening)::{read} line(s) added in the files law 5 reads, since the merge base '
          f'{base[:7]}; {len(found)} weakening(s) ({sum(f["net"] for f in found.values())} occurrence(s)), each '
          f'declared for this change and signed')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

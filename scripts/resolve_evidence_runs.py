"""Law 2 -- no capability is marked active without proof of execution (2026-11-25).

An audit found that the evidence behind a verified status is a GitHub Actions run id typed into code (the `Evidence`
records of omni_prod/agent_os/evidence.py and their `ref`), and nothing looked the run up. This script collects every
run id cited as evidence and asks GitHub about each one (GET /repos/{owner}/{repo}/actions/runs/{id}).

Where the ids live:
- the evidence records the status generators read (SOURCES) -- `Evidence` (omni_prod.runtime_bindings; agent_os.audit
  and registry_audit compute statuses from them), the `observed` text of a `Requirement` (registry_audit reads it as
  configuration evidence) and `ProviderEvidence` (PROVIDER_MATRIX, omni_prod/intelligence/inventory.py). Every record
  reachable from the globals of a source module is read, through tuples, lists, sets, dicts and dataclasses. A run id
  is a number of 10 or more digits in the record's text.
- every other string constant of omni_prod/**.py that names a run ("run <10+ digits>"; docstrings and comments are not
  evidence and are not read). Review 2026-11-25: omni_prod/vision_models.py cites 'live probe run 43657047045' as a
  plain string, the only evidence for four image models, and the record walk never saw it (the run is red).
A file under omni_prod/ that builds a record but is not a source is an error: a new evidence file is never skipped.
It is found by name resolution, not by one import form: the class imported from its home or from any module that
re-exports it (also `import *`), a module alias (`rb.Evidence`, `omni_prod.runtime_bindings.Evidence`), the class used
as a value (`Mk = Evidence`), or dataclasses.replace in a file that imports a module holding records.

The first id of a record is the run the record is about: when the record names a commit, that run's head_sha must start
with it. A later id in the same text is a supporting run (e.g. 'postdeploy-checks run A (+ inspect B)'): it must be
green too, but its commit is not compared. When the text before an id names a workflow of .github/workflows (e.g.
'deploy-worker run N'), the run must belong to one of the workflows named there.

An id FAILS (one ::error each) when GitHub no longer has it (EXPIRED: run again and cite the new run), the run is not
completed, its conclusion is not success, its head_sha does not start with a commit cited for it, its workflow is not
the one the text names, or GitHub could not be asked (UNVERIFIED, never a pass).

Known red (KNOWN_RED, docs/evidence-runs-known-red.json): runs that were already red when this check was written. Each
is a capability marked verified on a failed run. They are not hidden and not passed: each prints a ::warning that says
so, the step summary has a section for them, and the list states what each id backs and why it is red. The list only
shrinks: a listed id that is green now, or no longer cited, fails the check; a red id that is not listed fails it; an
entry needs a reason and a reviewer who is not its author, checked like a deletion (scripts/deletions_declared.py).

    GITHUB_TOKEN=... python3 scripts/resolve_evidence_runs.py --repo OWNER/NAME    (the token is never printed)

Exit 0: every id resolved green, or red and listed. 1: an id is red, expired, or the list is not true. 2: not verified
(no token, an API error, nothing collected, an unreadable list, or an undeclared evidence file).
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import functools
import importlib
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


github_get = _load('drill_runs_from_github', ROOT / 'tools' / 'drill_runs_from_github.py').github_get   # C17's GET
# An entry of the known-red list is reviewed like a deletion: the same rule of who may not sign.
NOT_A_REVIEWER = _load('deletions_declared', ROOT / 'scripts' / 'deletions_declared.py')._NOT_A_REVIEWER

SOURCES = (
    'omni_prod.agent_os.evidence',
    'omni_prod.agent_os.agents',
    'omni_prod.agent_os.skills',
    'omni_prod.agent_os.truth_matrix',
    'omni_prod.runtime_bindings',
    'omni_prod.skill_catalog',
    'omni_prod.intelligence.inventory',
)
# The record classes and the module that defines each.
RECORDS = {'Evidence': 'omni_prod.runtime_bindings', 'Requirement': 'omni_prod.runtime_bindings',
           'ProviderEvidence': 'omni_prod.intelligence.inventory'}
RUN_ID = re.compile(r'\b\d{10,}\b')
NAMED_RUN = re.compile(r'\brun\s+(\d{10,})\b', re.IGNORECASE)      # a run cited in any string: "... run <id>"
API = 'https://api.github.com/repos/{repo}/actions/runs/{run_id}'
KNOWN_RED = ROOT / 'docs' / 'evidence-runs-known-red.json'
ENTRY_KEYS = {'run_id', 'workflow', 'cited_in', 'backs', 'why_red', 'listed_on', 'reason', 'author', 'reviewer',
              'reviewed_at'}
ENTRY_OPTIONAL = {'signature_note'}


@dataclasses.dataclass(frozen=True)
class Citation:
    run_id: str
    ref: str           # the text that names the id
    commit: str        # the commit the run must be on; '' when the text names none or the id is a supporting run
    primary: bool      # the first id of the text
    kind: str          # Evidence | Requirement | ProviderEvidence | Text (a string constant of omni_prod/**.py)
    where: str = ''    # file:line of a Text citation
    workflows: tuple[str, ...] = ()   # workflows of .github/workflows the text names before the id


def source_files(sources=SOURCES) -> list[str]:
    return sorted(m.replace('.', '/') + '.py' for m in sources)


@functools.lru_cache(maxsize=4)
def workflow_names(root: Path = ROOT) -> tuple[str, ...]:
    return tuple(sorted({p.stem for p in (root / '.github' / 'workflows').glob('*.y*ml')}, key=lambda s: (-len(s), s)))


def named_workflows(text: str, end: int, root: Path = ROOT) -> tuple[str, ...]:
    """Workflows of .github/workflows named as a whole word in text[:end] ('verify' is not in 'verify-replay')."""
    before = text[:end]
    return tuple(sorted(w for w in workflow_names(root) if re.search(rf'(?<![\w-]){re.escape(w)}(?![\w-])', before)))


def _records(value, seen: dict[int, object]):
    if id(value) in seen or isinstance(value, (str, bytes, int, float, bool, type(None))):
        return
    seen[id(value)] = value          # kept alive: an id is unique only while its object lives
    name = type(value).__name__
    if name in RECORDS and type(value).__module__ == RECORDS[name]:
        yield value
    if isinstance(value, dict):
        for v in value.values():
            yield from _records(v, seen)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for v in value:
            yield from _records(v, seen)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            yield from _records(getattr(value, f.name), seen)


def _text(record) -> tuple[str, str, bool]:
    """(text that cites runs, commit, live?) of one record."""
    kind = type(record).__name__
    if kind == 'Evidence':
        return record.ref, record.commit, record.kind == 'live'
    if kind == 'ProviderEvidence':
        return record.ref, record.commit, True
    return record.observed, '', bool(record.observed)          # Requirement: '' = not observed, nothing cited


def _modules(root: Path):
    """(module name, path relative to root, parsed tree) of every file under omni_prod/."""
    for path in sorted((root / 'omni_prod').rglob('*.py')):
        rel = path.relative_to(root).as_posix()
        yield rel[:-3].replace('/', '.').removesuffix('.__init__'), rel, ast.parse(path.read_text(encoding='utf-8'),
                                                                                      filename=rel)


def _docstrings(tree) -> set[int]:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


@functools.lru_cache(maxsize=4)
def string_citations(root: Path = ROOT) -> tuple[tuple[str, int, str, tuple[str, ...]], ...]:
    """(file, line, text, every 10+ digit number in it) for each non-docstring string constant of omni_prod/**.py
    that holds a 10+ digit number."""
    out = []
    for _, rel, tree in _modules(root):
        docs = _docstrings(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                numbers = tuple(RUN_ID.findall(node.value))
                if numbers:
                    out.append((rel, node.lineno, node.value, numbers))
    return tuple(sorted(out))


def cited_in(run_id: str, root: Path = ROOT) -> list[str]:
    """The files whose string constants hold the id (what the known-red list must name)."""
    return sorted({rel for rel, _, _, numbers in string_citations(root) if run_id in numbers})


def _cite(text: str, commit: str, kind: str, where: str, ids, root: Path) -> list[Citation]:
    out = []
    for i, m in enumerate(ids):
        run_id = m.group(m.lastindex or 0)
        out.append(Citation(run_id, text, commit if i == 0 else '', i == 0, kind, where,
                            named_workflows(text, m.start(), root)))
    return out


def collect(sources=SOURCES, root: Path = ROOT) -> tuple[dict[str, list[Citation]], list[str]]:
    """({run id: citations}, texts of live records that cite no run id)."""
    seen: dict[int, object] = {}
    records = []
    for name in sources:
        module = importlib.import_module(name)
        records += list(_records(tuple(vars(module).values()), seen))
    cited: dict[str, list[Citation]] = {}
    uncited: list[str] = []
    record_texts: set[tuple[str, str]] = set()
    for record in records:
        text, commit, live = _text(record)
        ids = list(RUN_ID.finditer(text or ''))
        if not ids:
            if live and text not in uncited:
                uncited.append(text)
            continue
        for c in _cite(text, commit, type(record).__name__, '', ids, root):
            record_texts.add((c.run_id, c.ref))
            if c not in cited.setdefault(c.run_id, []):
                cited[c.run_id].append(c)
    for rel, line, text, _ in string_citations(root):
        for c in _cite(text, '', 'Text', f'{rel}:{line}', list(NAMED_RUN.finditer(text)), root):
            if (c.run_id, c.ref) not in record_texts and c not in cited.setdefault(c.run_id, []):
                cited[c.run_id].append(c)
    return dict(sorted(cited.items())), uncited


# ---- the guard: a file that builds records is a source ---------------------------------------------------------

def _absolute(package: str, level: int, module: str | None) -> str:
    if not level:
        return module or ''
    parts = package.split('.')
    return '.'.join(parts[:len(parts) - level + 1] + ([module] if module else []))


def _dotted(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f'{base}.{node.attr}' if base else None
    return None


@functools.lru_cache(maxsize=4)
def _builders(root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """(file, how it builds records) for every file under omni_prod/ that builds a record: it uses a record class as a
    value (a call, an alias, an argument) under any name, or calls dataclasses.replace while it imports a module that
    holds records. Annotations and isinstance/issubclass checks only read the class and do not count."""
    modules = {name: (rel, tree) for name, rel, tree in _modules(root)}
    package = {name: (name if rel.endswith('__init__.py') else name.rsplit('.', 1)[0]) for name, (rel, _) in modules.items()}
    # the record classes in each module's namespace, local name -> class, to a fixed point (re-exports, import *)
    exports = {name: {n: n for n, home in RECORDS.items() if home == name} for name in modules}
    for _ in range(len(modules) + 1):                       # bounded: each pass that changes something adds a name
        changed = False
        for name, (_, tree) in modules.items():
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                base = _absolute(package[name], node.level, node.module)
                for a in node.names:
                    found = (dict(exports.get(base, {})) if a.name == '*' else
                             {a.asname or a.name: exports[base][a.name]} if a.name in exports.get(base, {}) else {})
                    for local, cls in found.items():
                        if exports[name].get(local) != cls:
                            exports[name][local] = cls
                            changed = True
        if not changed:
            break
    else:
        raise RuntimeError('record exports did not settle')
    out = []
    for name, (rel, tree) in modules.items():
        local = dict(exports[name])                          # names bound to a record class here
        aliases: dict[str, str] = {}                         # local name -> module it refers to
        replace_names, dc_modules, holds_records = set(), set(), bool(local)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == 'dataclasses':
                        dc_modules.add(a.asname or 'dataclasses')
                    if a.asname:
                        aliases[a.asname] = a.name
                    else:
                        aliases[a.name.split('.')[0]] = a.name.split('.')[0]
                    holds_records |= bool(exports.get(a.name))
            elif isinstance(node, ast.ImportFrom):
                base = _absolute(package[name], node.level, node.module)
                holds_records |= bool(exports.get(base))
                for a in node.names:
                    if base == 'dataclasses' and a.name == 'replace':
                        replace_names.add(a.asname or a.name)
                    sub = f'{base}.{a.name}'
                    if sub in modules:
                        aliases[a.asname or a.name] = sub
                        holds_records |= bool(exports.get(sub))
        exempt = set()                                       # nodes that only read the class
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs + [node.args.vararg, node.args.kwarg]
                exempt |= {id(n) for a in args if a and a.annotation for n in ast.walk(a.annotation)}
                if node.returns:
                    exempt |= {id(n) for n in ast.walk(node.returns)}
            elif isinstance(node, ast.AnnAssign):
                exempt |= {id(n) for n in ast.walk(node.annotation)}
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                  and node.func.id in ('isinstance', 'issubclass') and len(node.args) == 2):
                exempt |= {id(n) for n in ast.walk(node.args[1])}

        def record_class(node) -> str | None:
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                return local.get(node.id)
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
                base = _dotted(node.value)
                if base:
                    head, _, rest = base.partition('.')
                    target = aliases.get(head, '') + ('.' + rest if rest else '') if head in aliases else ''
                    return exports.get(target, {}).get(node.attr)
            return None
        how = set()
        for node in ast.walk(tree):
            if id(node) in exempt:
                continue
            cls = record_class(node)
            if cls:
                how.add(cls)
            if isinstance(node, ast.Call) and holds_records and (
                    (isinstance(node.func, ast.Name) and node.func.id in replace_names)
                    or (isinstance(node.func, ast.Attribute) and node.func.attr == 'replace'
                        and _dotted(node.func.value) in dc_modules)):
                how.add('dataclasses.replace')
        if how:
            out.append((rel, tuple(sorted(how))))
    return tuple(out)


def undeclared_sources(root: Path = ROOT, sources=SOURCES) -> list[str]:
    """Files under omni_prod/ that build an evidence record but are not a source."""
    declared = set(source_files(sources))
    return [f"{rel} builds records ({', '.join(how)})" for rel, how in _builders(root) if rel not in declared]


# ---- GitHub -------------------------------------------------------------------------------------------------------

def fetch_run(repo: str, run_id: str, token: str, urlopen=urllib.request.urlopen) -> dict:
    return github_get(API.format(repo=repo, run_id=run_id), token, urlopen)


def _stem(run: dict) -> str:
    name = str(run.get('path') or '').rsplit('/', 1)[-1]
    return re.sub(r'\.ya?ml$', '', name)


def judge(run_id: str, citations: list[Citation], fetch) -> tuple[str, list[str], dict]:
    """('green' | 'red' | 'expired' | 'unverified', problems, run)."""
    try:
        run = fetch(run_id)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 'expired', [f'evidence expired: GitHub no longer has run {run_id} (HTTP 404); run again and cite '
                               'the new run'], {}
        return 'unverified', [f'API error: HTTP {exc.code} {exc.reason}'], {}
    except Exception as exc:                 # network, timeout, bad JSON: unverified, never a pass
        return 'unverified', [f'API error: {type(exc).__name__}: {exc}'], {}
    if not isinstance(run, dict) or str(run.get('id')) != run_id:
        got = run.get('id') if isinstance(run, dict) else type(run).__name__
        return 'unverified', [f'API error: the answer is not run {run_id} (got {got})'], {}
    problems = []
    if run.get('status') != 'completed':
        problems.append(f"not completed (status {run.get('status')})")
    if run.get('conclusion') != 'success':
        problems.append(f"conclusion {run.get('conclusion')}")
    head = str(run.get('head_sha') or '').lower()
    for c in citations:
        if c.commit and not head.startswith(c.commit.lower()):
            problems.append(f"head_sha {head[:12] or 'none'} does not start with the cited commit {c.commit} "
                            f"({c.ref[:80]})")
    stem = _stem(run)
    for c in citations:
        if c.workflows and stem not in c.workflows:
            problems.append(f"workflow {stem or 'none'} is not the {' or '.join(c.workflows)} the text names "
                            f"({c.ref[:80]})")
    return ('red' if problems else 'green'), problems, run


# ---- the known-red list -----------------------------------------------------------------------------------------

def load_known_red(path: Path) -> list[dict]:
    """The entries; ValueError when the file cannot be read as a list of entries."""
    try:
        doc = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'{type(exc).__name__}: {exc}') from exc
    entries = doc.get('known_red') if isinstance(doc, dict) else None
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise ValueError("'known_red' is not a list of entries")
    return entries


def entry_problems(entries: list[dict], cited: dict[str, list[Citation]], root: Path = ROOT) -> list[str]:
    """What is not true or not reviewed in the list (the verdict of GitHub is judged in main)."""
    problems, seen = [], set()
    for i, e in enumerate(entries):
        run_id = str(e.get('run_id', ''))
        tag = f'entry {i} ({run_id or "no run_id"})'
        missing, extra = ENTRY_KEYS - set(e), set(e) - ENTRY_KEYS - ENTRY_OPTIONAL
        if missing or extra:
            problems.append(f'{tag}: ' + '; '.join(
                ([f"missing {', '.join(sorted(missing))}"] if missing else [])
                + ([f"unknown {', '.join(sorted(extra))}"] if extra else [])))
            continue
        if not RUN_ID.fullmatch(run_id):
            problems.append(f'{tag}: run_id is not a run id')
            continue
        if run_id in seen:
            problems.append(f'{tag}: listed twice')
        seen.add(run_id)
        empty = sorted(k for k in ('backs', 'why_red', 'listed_on', 'reason', 'workflow') if not str(e[k]).strip())
        if empty:
            problems.append(f"{tag}: empty {', '.join(empty)}")
        who = str(e['reviewer'] or '').strip()
        if who.lower() in NOT_A_REVIEWER or who == e['author']:
            problems.append(f'{tag}: no reviewer other than the author ({who or "none"}); an entry hides nothing only '
                            'when someone else signed it')
        if run_id not in cited:
            problems.append(f'{tag}: no longer cited by any evidence; remove it (the list only shrinks)')
            continue
        actual = cited_in(run_id, root)
        if sorted(e['cited_in'] or []) != actual:
            problems.append(f"{tag}: cited_in says {sorted(e['cited_in'] or [])}, the code cites it in {actual}")
    return problems


# ---- output -------------------------------------------------------------------------------------------------------

def _where(run: dict) -> str:
    return (f"{str(run.get('path') or '?').rsplit('/', 1)[-1]} on {run.get('head_branch') or '?'}, "
            f"{str(run.get('created_at') or '?')[:10]}")


def _cited_by(citations: list[Citation]) -> str:
    return '; '.join(dict.fromkeys(f"{c.kind} '{c.ref[:90]}'" + (f' ({c.where})' if c.where else '')
                                   + (f' @{c.commit}' if c.commit else '')
                                   + ('' if c.primary else ' (supporting run)') for c in citations))


def _clean(text: str) -> str:
    return ' '.join(str(text).replace('%', '%25').split())[:3800]


def _cell(text: str) -> str:
    return ' '.join(str(text).replace('|', '/').split())


def main(argv: list[str] | None = None, fetch=None, urlopen=urllib.request.urlopen, known_red: Path = KNOWN_RED) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repo', default=os.environ.get('GITHUB_REPOSITORY', ''))
    a = ap.parse_args(argv)
    undeclared = undeclared_sources()
    for line in undeclared:
        print(f'::error title=evidence runs::{line}, but it is not in SOURCES of scripts/resolve_evidence_runs.py')
    cited, uncited = collect()
    if not cited:
        print('::error title=evidence runs::no run id was collected from the evidence records; nothing was verified')
        return 2
    if undeclared:
        return 2
    list_name = known_red.relative_to(ROOT).as_posix() if known_red.is_relative_to(ROOT) else str(known_red)
    try:
        entries = load_known_red(known_red)
    except ValueError as exc:
        print(f'::error title=evidence runs::the known-red list {list_name} cannot be read ({exc}); nothing was verified')
        return 2
    if fetch is None:
        token = os.environ.get('GITHUB_TOKEN', '').strip()
        if not token or not a.repo:
            print('::error title=evidence runs::GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are needed; '
                  f'{len(cited)} cited run ids were not verified')
            return 2

        def fetch(run_id):
            return fetch_run(a.repo, run_id, token, urlopen)
    listed = {str(e.get('run_id')): e for e in entries if isinstance(e, dict)}
    results = {run_id: judge(run_id, citations, fetch) for run_id, citations in cited.items()}
    by = {v: [r for r, (verdict, _, _) in results.items() if verdict == v]
          for v in ('green', 'red', 'expired', 'unverified')}
    known = [r for r in results if r in listed and results[r][0] in ('red', 'expired')]
    turned_green = [r for r in by['green'] if r in listed]
    red = [r for r in by['red'] if r not in listed]
    expired = [r for r in by['expired'] if r not in listed]
    green = [r for r in by['green'] if r not in listed]
    problems = entry_problems(entries, cited)
    for i, e in enumerate(entries):
        run = results.get(str(e.get('run_id')), ('', [], {}))[2]
        if run and e.get('workflow') != str(run.get('path') or '').rsplit('/', 1)[-1]:
            problems.append(f"entry {i} ({e.get('run_id')}): workflow says {e.get('workflow')}, GitHub says "
                            f"{str(run.get('path') or 'none').rsplit('/', 1)[-1]}")
    print(f'::notice title=evidence runs::{len(green)} of {len(cited)} cited run ids resolved green'
          + (f'; KNOWN RED (capabilities marked verified on a failed run): {", ".join(known)}' if known else '')
          + (f'; not green: {", ".join(red)}' if red else '') + (f'; expired: {", ".join(expired)}' if expired else '')
          + (f'; listed as known red but green now: {", ".join(turned_green)}' if turned_green else '')
          + (f'; unverified: {", ".join(by["unverified"])}' if by['unverified'] else ''))
    if known:
        print(f'::warning title=evidence runs: known red::{len(known)} capabilities are marked verified on a run that '
              f'did not succeed: {", ".join(known)}. They are listed in {list_name}, not fixed; each must be re-run '
              'green and re-cited, or its capability marked unverified. The list only shrinks.')
    for run_id, (verdict, why, run) in results.items():
        if run_id in known:
            e = listed[run_id]
            print(f'::warning title=known red evidence run {run_id}::' + _clean(
                f"CAPABILITY MARKED VERIFIED ON A FAILED RUN: {e.get('backs')} | {verdict.upper()}: {'; '.join(why)}"
                + (f' | {_where(run)}' if run else '') + f" | listed {e.get('listed_on')}: {e.get('why_red')}"
                + f' | cited by: {_cited_by(cited[run_id])}'))
        elif run_id in turned_green:
            print(f'::error title=evidence run {run_id}::' + _clean(
                f'LISTED AS KNOWN RED BUT GREEN NOW: success on {str(run.get("head_sha"))[:12]} ({_where(run)}); '
                f'remove it from {list_name} (the list only shrinks) | cited by: {_cited_by(cited[run_id])}'))
        elif verdict != 'green':
            print(f'::error title=evidence run {run_id}::' + _clean(
                f"{verdict.upper()}: {'; '.join(why)}" + (f' | {_where(run)}' if run else '')
                + f' | cited by: {_cited_by(cited[run_id])}'))
    for problem in problems:
        print(f'::error title=evidence runs: known-red list::' + _clean(f'{list_name}: {problem}'))
    for run_id in green:
        run = results[run_id][2]
        print(f'::notice title=evidence run {run_id}::' + _clean(
            f"success on {str(run.get('head_sha'))[:12]} ({_where(run)}) | cited by: {_cited_by(cited[run_id])}"))
    if uncited:
        print('::warning title=evidence runs::' + _clean(
            f'{len(uncited)} live evidence records cite no GitHub Actions run id and are NOT checked here: '
            + '; '.join(t[:70] for t in uncited)))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        rows = ['## Evidence runs', '']
        if known:
            rows += ['### Known red: capabilities marked verified on a failed run', '',
                     f'Listed in `{list_name}`. Not fixed and not passed: each must be re-run green and re-cited, or '
                     'its capability marked unverified.', '',
                     '| Run | Backs | Now | Why red (listed) | Listed |', '|---|---|---|---|---|']
            for run_id in known:
                e, (verdict, why, _) = listed[run_id], results[run_id]
                rows.append(f'| [{run_id}](https://github.com/{a.repo}/actions/runs/{run_id}) | {_cell(e.get("backs"))} | '
                            f'{verdict.upper()}: {_cell("; ".join(why))} | {_cell(e.get("why_red"))} | '
                            f'{_cell(e.get("listed_on"))} |')
            rows.append('')
        rows += ['### Every cited run', '', '| Run | Verdict | Detail | Cited by |', '|---|---|---|---|']
        for run_id, (verdict, why, run) in results.items():
            shown = ('KNOWN RED' if run_id in known else 'LISTED BUT GREEN' if run_id in turned_green
                     else verdict.upper())
            detail = '; '.join(why) if why else f"success on `{str(run.get('head_sha'))[:12]}` ({_where(run)})"
            rows.append(f'| [{run_id}](https://github.com/{a.repo}/actions/runs/{run_id}) | {shown} | '
                        f'{_cell(detail)} | {_cell(_cited_by(cited[run_id]))} |')
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write('\n'.join(rows) + '\n')
    if by['unverified']:
        return 2
    return 1 if (red or expired or turned_green or problems) else 0


if __name__ == '__main__':
    sys.exit(main())

"""Law 2 -- no capability is marked active without proof of execution (2026-11-25).

An audit found that the evidence behind a verified status is a GitHub Actions run id typed into code (the `Evidence`
records of omni_prod/agent_os/evidence.py and their `ref`), and nothing looked the run up. This script collects every
run id cited as evidence and asks GitHub about each one (GET /repos/{owner}/{repo}/actions/runs/{id}).

Where the ids live (SOURCES): the evidence records the status generators read -- `Evidence` (omni_prod.runtime_bindings;
agent_os.audit and registry_audit compute statuses from them), the `observed` text of a `Requirement` (registry_audit
reads it as configuration evidence) and `ProviderEvidence` (PROVIDER_MATRIX, omni_prod/intelligence/inventory.py). Every
record reachable from the globals of a source module is read, through tuples, lists, sets, dicts and dataclasses. A
file under omni_prod/ that builds such a record but is not a source is an error: a new evidence file is never skipped.

A run id is a number of 10 or more digits in the record's text. The first id of a record is the run the record is
about: when the record names a commit, that run's head_sha must start with it. A later id in the same text is a
supporting run (an inspection of the first, e.g. 'postdeploy-checks run A (+ inspect B)'): it must be green too, but its
commit is not compared, because the record's commit is the code of the run it is about.

An id FAILS (one ::error each) when GitHub has no such run, the run is not completed, its conclusion is not success, its
head_sha does not start with a commit cited for it, or GitHub could not be asked (network or API error: unverified,
never a pass). Every green id prints a ::notice, and one summary ::notice comes first. Live records that name no run id
are listed in one ::warning: this script cannot check them, and says so.

    GITHUB_TOKEN=... python3 scripts/resolve_evidence_runs.py --repo OWNER/NAME    (the token is never printed)

Exit 0: every id resolved green. 1: an id is not green. 2: not verified (no token, an API error, nothing collected,
or an undeclared evidence file).
"""
from __future__ import annotations

import argparse
import ast
import dataclasses
import functools
import importlib
import importlib.util
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location('drill_runs_from_github', ROOT / 'tools' / 'drill_runs_from_github.py')
_drill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_drill)
github_get = _drill.github_get              # the drill tool's GET (C17): same headers, same API version

SOURCES = (
    'omni_prod.agent_os.evidence',
    'omni_prod.agent_os.agents',
    'omni_prod.agent_os.skills',
    'omni_prod.agent_os.truth_matrix',
    'omni_prod.runtime_bindings',
    'omni_prod.skill_catalog',
    'omni_prod.intelligence.inventory',
)
# The record classes and the module that defines each. A file that imports one of them from there and calls it
# builds evidence, and must be a source.
RECORDS = {'Evidence': 'omni_prod.runtime_bindings', 'Requirement': 'omni_prod.runtime_bindings',
           'ProviderEvidence': 'omni_prod.intelligence.inventory'}
RUN_ID = re.compile(r'\b\d{10,}\b')
API = 'https://api.github.com/repos/{repo}/actions/runs/{run_id}'


@dataclasses.dataclass(frozen=True)
class Citation:
    run_id: str
    ref: str           # the record's text that names the id
    commit: str        # the commit the run must be on; '' when the record names none or the id is a supporting run
    primary: bool      # the first id of the record's text
    kind: str          # Evidence | Requirement | ProviderEvidence


def source_files(sources=SOURCES) -> list[str]:
    return sorted(m.replace('.', '/') + '.py' for m in sources)


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


def collect(sources=SOURCES) -> tuple[dict[str, list[Citation]], list[str]]:
    """({run id: citations}, texts of live records that cite no run id)."""
    seen: dict[int, object] = {}
    records = []
    for name in sources:
        module = importlib.import_module(name)
        records += list(_records(tuple(vars(module).values()), seen))
    cited: dict[str, list[Citation]] = {}
    uncited: list[str] = []
    for record in records:
        text, commit, live = _text(record)
        ids = RUN_ID.findall(text or '')
        if not ids:
            if live and text not in uncited:
                uncited.append(text)
            continue
        for i, run_id in enumerate(ids):
            c = Citation(run_id, text, commit if i == 0 else '', i == 0, type(record).__name__)
            if c not in cited.setdefault(run_id, []):
                cited[run_id].append(c)
    return dict(sorted(cited.items())), uncited


@functools.lru_cache(maxsize=4)
def _builders(root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """(file, record classes it calls) for every file under omni_prod/ that calls a record class it defines or
    imports from the defining module."""
    out = []
    for path in sorted((root / 'omni_prod').rglob('*.py')):
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=rel)
        module = rel[:-3].replace('/', '.').removesuffix('.__init__')
        package = module if rel.endswith('__init__.py') else module.rsplit('.', 1)[0]
        known = {name for name, home in RECORDS.items() if home == module}         # defined here
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                base = node.module or ''
                if node.level:
                    parts = package.split('.')
                    base = '.'.join(parts[:len(parts) - node.level + 1] + ([base] if base else []))
                known |= {a.asname or a.name for a in node.names if RECORDS.get(a.name) == base}
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        if known & calls:
            out.append((rel, tuple(sorted(known & calls))))
    return tuple(out)


def undeclared_sources(root: Path = ROOT, sources=SOURCES) -> list[str]:
    """Files under omni_prod/ that build an evidence record but are not a source."""
    declared = set(source_files(sources))
    return [f"{rel} builds {', '.join(names)} records" for rel, names in _builders(root) if rel not in declared]


def fetch_run(repo: str, run_id: str, token: str, urlopen=urllib.request.urlopen) -> dict:
    return github_get(API.format(repo=repo, run_id=run_id), token, urlopen)


def judge(run_id: str, citations: list[Citation], fetch) -> tuple[str, list[str], dict]:
    """('green' | 'red' | 'unverified', problems, run)."""
    try:
        run = fetch(run_id)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return 'red', ['missing: GitHub has no such run (HTTP 404)'], {}
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
    return ('red' if problems else 'green'), problems, run


def _where(run: dict) -> str:
    return (f"{str(run.get('path') or '?').rsplit('/', 1)[-1]} on {run.get('head_branch') or '?'}, "
            f"{str(run.get('created_at') or '?')[:10]}")


def _cited_by(citations: list[Citation]) -> str:
    return '; '.join(dict.fromkeys(f"{c.kind} '{c.ref[:90]}'" + (f' @{c.commit}' if c.commit else '')
                                   + ('' if c.primary else ' (supporting run)') for c in citations))


def _clean(text: str) -> str:
    return ' '.join(str(text).replace('%', '%25').split())[:3800]


def main(argv: list[str] | None = None, fetch=None, urlopen=urllib.request.urlopen) -> int:
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
    if fetch is None:
        token = os.environ.get('GITHUB_TOKEN', '').strip()
        if not token or not a.repo:
            print('::error title=evidence runs::GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are needed; '
                  f'{len(cited)} cited run ids were not verified')
            return 2

        def fetch(run_id):
            return fetch_run(a.repo, run_id, token, urlopen)
    results = {run_id: judge(run_id, citations, fetch) for run_id, citations in cited.items()}
    green = [r for r, (v, _, _) in results.items() if v == 'green']
    red = [r for r, (v, _, _) in results.items() if v == 'red']
    unverified = [r for r, (v, _, _) in results.items() if v == 'unverified']
    print(f'::notice title=evidence runs::{len(green)} of {len(cited)} cited run ids resolved green'
          + (f'; not green: {", ".join(red)}' if red else '') + (f'; unverified: {", ".join(unverified)}' if unverified else ''))
    for run_id, (verdict, problems, run) in results.items():
        if verdict != 'green':
            print(f'::error title=evidence run {run_id}::' + _clean(
                f"{verdict.upper()}: {'; '.join(problems)}" + (f' | {_where(run)}' if run else '')
                + f' | cited by: {_cited_by(cited[run_id])}'))
    for run_id, (verdict, _, run) in results.items():
        if verdict == 'green':
            print(f'::notice title=evidence run {run_id}::' + _clean(
                f"success on {str(run.get('head_sha'))[:12]} ({_where(run)}) | cited by: {_cited_by(cited[run_id])}"))
    if uncited:
        print('::warning title=evidence runs::' + _clean(
            f'{len(uncited)} live evidence records cite no GitHub Actions run id and are NOT checked here: '
            + '; '.join(t[:70] for t in uncited)))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        rows = ['| Run | Verdict | Detail | Cited by |', '|---|---|---|---|']
        for run_id, (verdict, problems, run) in results.items():
            detail = '; '.join(problems) if problems else f"success on `{str(run.get('head_sha'))[:12]}` ({_where(run)})"
            rows.append(f'| [{run_id}](https://github.com/{a.repo}/actions/runs/{run_id}) | {verdict.upper()} | '
                        f"{detail.replace('|', '/')} | {_cited_by(cited[run_id]).replace('|', '/')} |")
        with open(summary, 'a', encoding='utf-8') as fh:
            fh.write('\n'.join(rows) + '\n')
    if unverified:
        return 2
    return 1 if red else 0


if __name__ == '__main__':
    sys.exit(main())

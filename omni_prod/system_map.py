"""The system map of 148AI, derived from the code and the existing registries (the owner's plan v3, S1.5, 2026-11-25).

    python -m omni_prod.system_map --write          # docs/SYSTEM_MAP.md + SYSTEM_MAP.json (the full map, not committed)
    python -m omni_prod.system_map --check          # exit 1 when docs/SYSTEM_MAP.md differs from the mapping below
    python -m omni_prod.system_map --json PATH      # the full map, written to PATH (CI: the artifact `system-map`)
    python -m omni_prod.system_map --summary PATH   # a short summary table appended to PATH (CI: $GITHUB_STEP_SUMMARY)

What is committed and checked is only what changes with this file: the mapping from each source's status word to the
plan's six states, its rules, and how the inventory is read (docs/SYSTEM_MAP.md). The full map -- every component with
its state, and the inventory -- changes with almost every pull request. A committed copy goes stale on main whenever a
branch cut before it, or two green pull requests that each regenerated it, merge: the required jobs test the pull
request's head, not the merge (the review of #532, 2026-11-25; CLAUDE.md section 4). So the full map is built on every
push to main and every pull request instead (v24-ci, job `light`: the artifact `system-map` and the run's summary), and
locally with --write, into a file git ignores.

Nothing here is a second registry. Every row is read from a source that already exists and is kept current by its own
generator or by the code itself:

  agents          AGENT_OS_REGISTRY.json            (python -m omni_prod.agent_os.audit --write)
  roles, skills   omni_prod.registry_audit           (docs/AGENT_SKILL_STATUS.md; audit({}) as its test runs it)
  models          PROVIDER_MATRIX.json              (python -m omni_prod.intelligence.matrix --write)
  endpoints       the route decorators of every omni_prod module, with the APIRouter and include_router prefixes
                  (read as source, so no import of FastAPI is needed)
  tables          CREATE TABLE in infra/postgres/<number>_*.sql; down files in infra/postgres/rollback/
  services        infra/worker-host/docker-compose.yml
  queues          the queue names in omni_prod/queueing.py and omni_prod/intake/reservation_worker.py; a name that
                  ends in '-' is a prefix of per-host queues, listed apart
  workflows       .github/workflows/*.yml (name, triggers, schedules)
  environment     the variable NAMES the code reads (never a value); how they are found is in ENV_METHOD
  dependencies    which omni_prod package imports which (package level)
  limitations     TRUTH_MATRIX.json customer-visible findings, PROVIDER_MATRIX.json capability gaps and legacy routes

The plan's six states are given to every agent, role, skill and model by ONE mapping (PLAN_STATE below) from the word
its own source uses. A word the mapping does not know raises: a new status in a source is classified by a person, never
guessed. LIVE cannot be derived from the repository: it needs evidence younger than 7 days on the SHA that is deployed,
which lives in GitHub runs and Vercel, not here. The map therefore gives LIVE to nothing and says why.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MD_OUT = ROOT / 'docs' / 'SYSTEM_MAP.md'
JSON_LOCAL = ROOT / 'SYSTEM_MAP.json'              # in .gitignore: the full map is never committed
SCHEMA = 'system-map/2'

PLAN_STATES = ('NOT_IMPLEMENTED', 'PARTIAL', 'IMPLEMENTED', 'CONNECTED', 'VERIFIED', 'LIVE')

# One mapping from every status word a source uses to the plan's six (plan v3, S1.5; OWNERS.md rule 7). The words the
# plan's table does not name are listed in MAPPING_DECISIONS with the reason.
PLAN_STATE = {
    # registry_audit (docs/AGENT_SKILL_STATUS.md)
    'DEFINED': 'NOT_IMPLEMENTED',
    'NOT_IMPLEMENTED': 'NOT_IMPLEMENTED',
    'IMPLEMENTED': 'IMPLEMENTED',
    'TESTED': 'IMPLEMENTED',
    'CONNECTED': 'CONNECTED',
    'VERIFIED': 'VERIFIED',
    'STALE': 'IMPLEMENTED',
    'BLOCKED': 'PARTIAL',
    # agent_os (AGENT_OS_REGISTRY.json)
    'UNIT_TESTED': 'IMPLEMENTED',
    'INTEGRATION_TESTED': 'IMPLEMENTED',
    'REAL_SERVER_VERIFIED': 'VERIFIED',
    'LIVE': 'VERIFIED',
    # intelligence (PROVIDER_MATRIX.json): verification_state / connection_state / availability / health
    'REAL_EXECUTION_VERIFIED': 'VERIFIED',
    'CONNECTION_TESTED': 'CONNECTED',
    'INSUFFICIENT_CREDIT': 'PARTIAL',
    'CREDIT_EXHAUSTED': 'PARTIAL',
}
# A source word that says the component cannot take work. It wins over a tested connection and a verification.
BLOCKED_WORDS = ('BLOCKED', 'INSUFFICIENT_CREDIT', 'CREDIT_EXHAUSTED')
MAPPING_DECISIONS = (
    ('STALE -> IMPLEMENTED', 'it was verified once and its code changed since, so the evidence no longer covers it'),
    ('TESTED, UNIT_TESTED, INTEGRATION_TESTED -> IMPLEMENTED', 'a test is not an execution check on a real server'),
    ('BLOCKED, INSUFFICIENT_CREDIT, CREDIT_EXHAUSTED -> PARTIAL, or NOT_IMPLEMENTED when no code is named',
     'code exists but a named dependency stops it'),
    ('a gap or missing contract fields turn IMPLEMENTED or CONNECTED into PARTIAL', 'the plan: PARTIAL follows the '
     "component's gap list"),
    ('LIVE in a source -> VERIFIED here', 'LIVE needs evidence on the deployed SHA younger than 7 days, which the '
     'repository does not hold'),
    ('CREDENTIAL_PRESENT alone is not CONNECTED', 'a key that was never used to call the provider proves no connection'),
    ('a model that is BLOCKED, has a blocking health (CREDIT_EXHAUSTED ...) or is INSUFFICIENT_CREDIT takes that word, '
     'before CONNECTION_TESTED and REAL_EXECUTION_VERIFIED', 'a model that cannot take work is neither connected nor '
     'verified, whatever answered before (PROVIDER_MATRIX ranks BLOCKED above IMPLEMENTED; intelligence/states.py: a '
     'route in a blocking health takes no work)'),
    ('a role that registry_audit calls CONNECTED with unit tests only (no configuration) is read as UNIT_TESTED',
     'registry_audit gives CONNECTED for "configuration observed or unit tests only"; a unit test is not a connection'),
)
# What the review of #532 added after the owner approved the mapping (OWNERS.md rule 7): the last rules above and
# these words. They rest on his standing approval (OWNERS.md rule 1), and the documentation says so.
RULES_ADDED_AFTER_APPROVAL = 2
WORDS_ADDED_AFTER_APPROVAL = ('INSUFFICIENT_CREDIT', 'CREDIT_EXHAUSTED')
LIVE_RULE = ('LIVE is never derived here: it needs evidence younger than 7 days on the SHA that is deployed, and that '
             'evidence is in GitHub Actions runs and Vercel deployments, not in the repository.')
ENV_METHOD = ('names read with os.environ.get / os.getenv / os.environ[...] / `in os.environ`, or through an env '
              'mapping (env, environ, self.env, self._env), with a string literal, a module or class constant, a constant '
              'imported from another omni_prod module, or a loop over such names; and the names passed to a package '
              'helper whose parameter reaches such a read (found from the code, listed in `helpers`). A name built at '
              'run time (an f-string, a concatenation) is not found: those reads are counted in `unresolved`.')


def plan_state(word: str, *, gaps: bool = False, has_code: bool = True) -> str:
    """The plan's state for a source's status word. An unknown word raises: a person classifies a new status."""
    if word not in PLAN_STATE:
        raise ValueError(f'system_map: no plan state for the status {word!r}; add it to PLAN_STATE with its reason')
    state = PLAN_STATE[word]
    if word in BLOCKED_WORDS and not has_code:
        return 'NOT_IMPLEMENTED'
    if gaps and state in ('IMPLEMENTED', 'CONNECTED'):
        return 'PARTIAL'
    return state


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _json(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


# ---- the components with a status --------------------------------------------------------------------------------
def agents() -> list[dict]:
    rows = []
    for a in _json('AGENT_OS_REGISTRY.json')['agents']:
        gaps = [g for g in [a.get('gap') or ''] if g] + [f'missing contract field: {f}' for f in
                                                          a.get('missing_contract_fields') or ()]
        rows.append({'key': a['agent_key'], 'name': a['name'], 'category': a['category'],
                     'location': list(a.get('implementation_location') or ()), 'source_status': a['status'],
                     'state': plan_state(a['status'], gaps=bool(gaps), has_code=bool(a.get('implementation_location'))),
                     'gaps': gaps, 'verified_at': a.get('last_verified_at') or None,
                     'verified_commit': a.get('last_verified_commit') or None})
    return sorted(rows, key=lambda r: r['key'])


def role_word(lifecycle: str, binding) -> str:
    """The word a role is read as. registry_audit gives CONNECTED for "configuration observed or unit tests only"
    (registry_audit.audit_role); with no configuration in its binding, CONNECTED came from unit tests alone."""
    if lifecycle == 'CONNECTED' and binding is not None and not binding.config:
        return 'UNIT_TESTED'
    return lifecycle


def roles() -> list[dict]:
    from . import registry_audit as ra
    rows = []
    for r in ra.audit({}):
        gap = '' if r.gap in ('—', 'not implemented') else r.gap
        word = role_word(r.lifecycle, ra.BY_ROLE.get(r.role.key))
        row = {'key': r.role.key, 'source_status': r.lifecycle,
               'state': plan_state(word, gaps=bool(gap), has_code=r.implementation not in ('—', '')),
               'location': r.implementation, 'gaps': [gap] if gap else []}
        if word != r.lifecycle:
            row['read_as'] = word
        rows.append(row)
    return sorted(rows, key=lambda r: r['key'])


def skills() -> list[dict]:
    from . import registry_audit as ra
    rows = []
    for key, area, kind, status, impl, depends, _v, gap in ra.catalog_skill_rows():
        g = '' if gap == '—' else gap
        rows.append({'key': key, 'catalog': 'skill_catalog', 'area': area, 'source_status': status,
                     'state': plan_state(status, gaps=bool(g), has_code=impl != '—'), 'location': impl,
                     'depends': [] if depends == '—' else depends.split(', '), 'gaps': [g] if g else []})
    for key, kind, status, injected, _v, _ev, gap in ra.skill_rows():
        g = '' if gap == '—' else gap
        rows.append({'key': key, 'catalog': 'skills_runtime', 'area': kind, 'source_status': status,
                     'state': plan_state(status, gaps=bool(g)), 'location': 'omni_prod/skills_runtime.py',
                     'depends': [], 'gaps': [g] if g else []})
    return sorted(rows, key=lambda r: (r['catalog'], r['key']))


def model_word(m: dict) -> tuple[str, list[str]]:
    """The status word of a PROVIDER_MATRIX row and what blocks it. Blocked wins: a model whose implementation is
    BLOCKED, whose health blocks work, or whose account has no credit is never CONNECTED or VERIFIED here, whatever
    answered before. Then a real execution, then a tested connection, then the implementation status."""
    from .intelligence import states as st
    blocked = []
    if m['implementation_status'] == 'BLOCKED':
        blocked.append(('BLOCKED', 'implementation_status'))
    if m.get('health') in st.BLOCKING_HEALTH:
        blocked.append((m['health'], 'health'))
    if m.get('availability') == st.INSUFFICIENT_CREDIT:
        blocked.append((m['availability'], 'availability'))
    if blocked:
        return blocked[0][0], [f'{field} {word}' for word, field in blocked]
    if m['verification_state'] == 'REAL_EXECUTION_VERIFIED':
        return 'REAL_EXECUTION_VERIFIED', []
    if m['connection_state'] == 'CONNECTION_TESTED':
        return 'CONNECTION_TESTED', []
    return m['implementation_status'], []


def models() -> list[dict]:
    rows = []
    for m in _json('PROVIDER_MATRIX.json')['models']:
        word, blocked_by = model_word(m)
        rows.append({'key': m['model_key'], 'provider': m['provider_key'], 'model_id': m['provider_model_id'],
                     'source_status': word, 'state': plan_state(word, has_code=bool(m.get('adapter_implementation_path'))),
                     'blocked_by': blocked_by, 'availability': m['availability'],
                     'tasks': list(m.get('eligible_tasks') or ()),
                     'location': m.get('adapter_implementation_path') or None,
                     'verified_at': m.get('last_verified_at') or None})
    return sorted(rows, key=lambda r: r['key'])


# ---- reading the source ------------------------------------------------------------------------------------------
def _dotted(node) -> str:
    """'os.environ' for os.environ, 'self.env' for self.env; '' for anything that is not a plain name chain."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return '.'.join(reversed(parts))
    return ''


def _all_nodes(tree: ast.AST) -> list:
    """Every node of a parsed tree, walked once and kept on the tree (the map reads each module several ways)."""
    nodes = getattr(tree, '_system_map_nodes', None)
    if nodes is None:
        nodes = list(ast.walk(tree))
        tree._system_map_nodes = nodes
    return nodes


def _sources() -> dict[str, tuple[str, ast.Module]]:
    """{module name: (repository path, parsed tree)} for every omni_prod module; a package's __init__ under the
    package's own name."""
    out = {}
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        parts = path.relative_to(ROOT).with_suffix('').parts
        name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
        out[name] = (_rel(path), ast.parse(path.read_text(encoding='utf-8')))
    return out


# ---- the inventory -----------------------------------------------------------------------------------------------
_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'websocket', 'api_route'}


def _str(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _routers(rel: str, tree: ast.Module) -> dict[str, str]:
    """{variable: prefix} for every `NAME = APIRouter(...)` in a module. A prefix that is not a string literal, or one
    name bound to two prefixes, raises: the map does not guess a path."""
    out: dict[str, str] = {}
    for node in _all_nodes(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                and _dotted(node.value.func).split('.')[-1] == 'APIRouter'):
            continue
        given = {k.arg: k.value for k in node.value.keywords}
        prefix = '' if 'prefix' not in given else _str(given['prefix'])
        if prefix is None:
            raise ValueError(f'system_map: {rel}:{node.lineno} APIRouter prefix is not a string literal')
        for target in node.targets:
            if isinstance(target, ast.Name):
                if out.get(target.id, prefix) != prefix:
                    raise ValueError(f'system_map: {rel}: router {target.id!r} has two prefixes')
                out[target.id] = prefix
    return out


def _returned_router(tree: ast.Module, function: str, routers: dict[str, str]) -> str | None:
    for node in _all_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function:
            for ret in ast.walk(node):
                if isinstance(ret, ast.Return) and isinstance(ret.value, ast.Name) and ret.value.id in routers:
                    return ret.value.id
    return None


def _include_prefixes(sources: dict, routers: dict[str, dict]) -> dict[tuple[str, str], list[str]]:
    """{(module, router variable): [prefix, ...]} for every include_router(..., prefix='...'). The router is a name of
    the same module or the call of an omni_prod function that returns one; anything else raises."""
    out: dict[tuple[str, str], list[str]] = {}
    for mod, (rel, tree) in sources.items():
        for node in _all_nodes(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'include_router' and node.args):
                continue
            given = {k.arg: k.value for k in node.keywords}
            if 'prefix' not in given:
                continue
            prefix = _str(given['prefix'])
            arg = node.args[0]
            found = None
            if prefix is not None and isinstance(arg, ast.Name) and arg.id in routers[mod]:
                found = (mod, arg.id)
            elif prefix is not None and isinstance(arg, ast.Call):
                name = _dotted(arg.func).split('.')[-1]
                hits = [(m, v) for m, (_r, t) in sources.items() for v in [_returned_router(t, name, routers[m])] if v]
                found = hits[0] if len(hits) == 1 else None
            if found is None:
                raise ValueError(f'system_map: {rel}:{node.lineno} include_router(prefix=...) names a router the map '
                                 'cannot resolve; extend endpoints()')
            out.setdefault(found, []).append(prefix)
    return out


def endpoints(sources: dict | None = None) -> list[dict]:
    sources = _sources() if sources is None else sources
    all_routers = {mod: _routers(rel, tree) for mod, (rel, tree) in sources.items()}
    included = _include_prefixes(sources, all_routers)
    rows = []
    for mod, (rel, tree) in sources.items():
        routers = all_routers[mod]
        for node in _all_nodes(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for d in node.decorator_list:
                if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in _METHODS
                        and d.args and _str(d.args[0]) is not None):
                    continue
                path = _str(d.args[0])
                owner = d.func.value.id if isinstance(d.func.value, ast.Name) else ''
                if owner in routers:
                    prefixes = [p + routers[owner] for p in included.get((mod, owner), [''])]
                elif path.startswith('/'):
                    prefixes = ['']
                else:
                    continue
                # no line number: a map that moved with every edit above a route would change on every pull request
                for prefix in prefixes:
                    rows.append({'method': d.func.attr.upper(), 'path': prefix + path, 'handler': node.name,
                                 'file': rel})
    return sorted(rows, key=lambda r: (r['path'], r['method'], r['file']))


_CREATE = re.compile(r'CREATE TABLE(?: IF NOT EXISTS)?\s+"?([\w.]+)"?', re.I)


def database() -> dict:
    migrations = sorted((ROOT / 'infra' / 'postgres').glob('[0-9]*.sql'))
    tables: dict[str, str] = {}
    for m in migrations:
        for name in _CREATE.findall(m.read_text(encoding='utf-8')):
            tables.setdefault(name, m.name)
    down = sorted(p.name for p in (ROOT / 'infra' / 'postgres' / 'rollback').glob('*.sql'))
    return {'migrations': [m.name for m in migrations], 'highest': migrations[-1].name if migrations else None,
            'rollback_files': down, 'tables': [{'name': k, 'created_in': v} for k, v in sorted(tables.items())]}


def services() -> list[dict]:
    compose = yaml.safe_load((ROOT / 'infra' / 'worker-host' / 'docker-compose.yml').read_text(encoding='utf-8'))
    rows = []
    for name, svc in sorted((compose.get('services') or {}).items()):
        cmd = svc.get('command')
        rows.append({'name': name, 'command': ' '.join(cmd) if isinstance(cmd, list) else cmd,
                     'profiles': list(svc.get('profiles') or ())})
    return rows


QUEUE_FILES = ('omni_prod/queueing.py', 'omni_prod/intake/reservation_worker.py')
_QUEUE = re.compile(r'omni-[a-z0-9-]+')


def queues() -> dict:
    """The queue names, and apart from them the prefixes of per-host queues (a name ending in '-', such as
    'omni-preview-host-', is never a queue a worker listens on)."""
    names, prefixes = [], []
    for rel in QUEUE_FILES:
        found = sorted({n.value for n in ast.walk(ast.parse((ROOT / rel).read_text(encoding='utf-8')))
                        if _str(n) is not None and _QUEUE.fullmatch(n.value)})
        names += [{'name': q, 'defined_in': rel} for q in found if not q.endswith('-')]
        prefixes += [{'prefix': q, 'defined_in': rel} for q in found if q.endswith('-')]
    return {'queues': names, 'queue_prefixes': prefixes}


def workflows() -> list[dict]:
    rows = []
    for path in sorted((ROOT / '.github' / 'workflows').glob('*.yml')):
        wf = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        on = wf.get('on', wf.get(True)) or {}
        on = {on: None} if isinstance(on, str) else ({k: None for k in on} if isinstance(on, list) else on)
        crons = [s.get('cron') for s in (on.get('schedule') or []) if isinstance(s, dict)]
        rows.append({'file': path.name, 'name': wf.get('name') or path.stem, 'triggers': sorted(on),
                     'schedules': crons, 'jobs': sorted((wf.get('jobs') or {}).keys())})
    return rows


# ---- environment variable names ----------------------------------------------------------------------------------
_ENV_NAME = re.compile(r'[A-Z][A-Z0-9_]{2,}')
_ENV_GETTERS = {'os.getenv', 'getenv'}                    # getenv(NAME)
_ENV_MAPPINGS = {'os.environ', 'environ', 'env', 'environment', 'self.env', 'self._env', 'self.environ'}
_MAPPING_READS = {'get', 'setdefault'}                    # <mapping>.get(NAME)
_NOT_A_HELPER = {'get', 'setdefault', 'pop', 'getenv'}    # a mapping's own methods: every dict.get('X') would count


def _scope_nodes(root):
    """The nodes of one scope: a function's body, or a module with its class bodies, never a nested function's."""
    stack = list(ast.iter_child_nodes(root))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, ast.ClassDef) and not isinstance(root, ast.Module):
            continue
        stack.extend(ast.iter_child_nodes(node))


def _params(fn) -> list[str]:
    names = [a.arg for a in fn.args.posonlyargs + fn.args.args]
    if names and names[0] in ('self', 'cls'):
        names = names[1:]
    return names


class _Module:
    """One module's constants and imports, for resolving the expression that names a variable."""

    def __init__(self, name: str, rel: str, tree: ast.Module, modules: dict):
        self.name, self.rel, self.tree, self.modules = name, rel, tree, modules
        self.constants: dict[str, set[str]] = {}     # NAME = 'X' / ('X', 'Y') at module or class level
        self.imported: dict[str, tuple[str, str]] = {}
        self.aliases: dict[str, str] = {}            # a local name for an omni_prod module

    def collect(self) -> None:
        for node in _scope_nodes(self.tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                values = _literal_strings(node.value)
                for t in targets:
                    if isinstance(t, ast.Name) and values:
                        self.constants.setdefault(t.id, set()).update(values)
        for node in _all_nodes(self.tree):               # an import inside a function names a constant too
            if isinstance(node, ast.ImportFrom):
                base = resolve(self.name + '.x' if self.rel.endswith('__init__.py') else self.name, node)
                for a in node.names:
                    target = base[0] if node.module else '.'.join(base[0].split('.')[:-1] + [a.name]) if base else ''
                    local = a.asname or a.name
                    if node.module:
                        self.imported[local] = (target, a.name)
                        if f'{target}.{a.name}' in self.modules:
                            self.aliases[local] = f'{target}.{a.name}'
                    elif target in self.modules:
                        self.aliases[local] = target
            elif isinstance(node, ast.Import):
                for a in node.names:
                    if a.asname and a.name in self.modules:
                        self.aliases[a.asname] = a.name

    def constant(self, name: str, depth: int = 0) -> set[str] | None:
        if name in self.constants:
            return self.constants[name]
        if name in self.imported and depth < 8:          # a chain of re-exports, bounded
            module, original = self.imported[name]
            other = self.modules.get(module)
            if other is not None:
                return other.constant(original, depth + 1)
        return None


def _literal_strings(node) -> set[str]:
    if _str(node) is not None:
        return {node.value}
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)) and node.elts and all(_str(e) is not None for e in node.elts):
        return {e.value for e in node.elts}
    return set()


class _Scope:
    """What each local name of one scope can hold: names of variables, or the scope's own parameters. A parameter
    marker 'p' means the parameter holds one name; 'p[]' means it holds several (a loop runs over it)."""

    def __init__(self, module: _Module, fn=None):
        self.module, self.params = module, (_params(fn) + [a.arg for a in fn.args.kwonlyargs] if fn else [])
        self.local: dict[str, tuple[set[str], set[str]]] = {}
        nodes = list(_scope_nodes(fn if fn is not None else module.tree))
        binds = [n for n in nodes if (isinstance(n, ast.Assign) and len(n.targets) == 1
                                      and isinstance(n.targets[0], ast.Name))
                 or (isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.target, ast.Name))]
        for _ in range(3):                               # a local that names another local: bounded passes
            for node in binds:
                if isinstance(node, ast.Assign):
                    self._bind(node.targets[0].id, node.value, iterate=False)
                else:
                    self._bind(node.target.id, node.iter, iterate=True)
        self.env_keys = [key for key in map(_env_keys, nodes) if key is not None]
        self.calls = [n for n in nodes if isinstance(n, ast.Call)]

    def _bind(self, name: str, value, *, iterate: bool) -> None:
        if iterate and _dotted(value) in _ENV_MAPPINGS:
            return                                       # the keys of the environment itself name nothing given
        found = self.resolve(value)
        if found is None:
            return
        names, markers = found
        if iterate and not isinstance(value, (ast.Tuple, ast.List, ast.Set)):
            if any(m.endswith('[]') for m in markers):
                return
            markers = {m + '[]' for m in markers}        # a loop over a parameter: each element is a name
        old = self.local.get(name, (set(), set()))
        self.local[name] = (old[0] | names, old[1] | markers)

    def resolve(self, node) -> tuple[set[str], set[str]] | None:
        """(names, parameter markers) the expression can be, or None when it is built at run time."""
        if _str(node) is not None:
            return {node.value}, set()
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            parts = [self.resolve(e) for e in node.elts]
            if not parts or any(p is None for p in parts):
                return None
            return set().union(*(p[0] for p in parts)), set().union(*(p[1] for p in parts))
        if isinstance(node, ast.Name):
            if node.id in self.params:
                return set(), {node.id}
            if node.id in self.local:
                return self.local[node.id]
            found = self.module.constant(node.id)
            return (set(found), set()) if found else None
        if isinstance(node, ast.Attribute):
            owner = _dotted(node.value)
            if owner in self.module.aliases:
                found = self.module.modules[self.module.aliases[owner]].constant(node.attr)
            else:
                found = self.module.constant(node.attr) if owner in ('self', 'cls') or owner[:1].isupper() else None
            return (set(found), set()) if found else None
        return None


def _env_keys(node):
    """The expression that names the variable, when `node` reads the environment directly."""
    if isinstance(node, ast.Call) and node.args and not isinstance(node.args[0], ast.Starred):
        if _dotted(node.func) in _ENV_GETTERS:
            return node.args[0]
        if (isinstance(node.func, ast.Attribute) and node.func.attr in _MAPPING_READS
                and _dotted(node.func.value) in _ENV_MAPPINGS):
            return node.args[0]
    if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and _dotted(node.value) in _ENV_MAPPINGS:
        return node.slice
    if (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn))
            and _dotted(node.comparators[0]) in _ENV_MAPPINGS):
        return node.left
    return None


def _callee(node, m: _Module, functions: dict[str, set]) -> tuple[str, str] | None:
    """(module, function) a call names, within the package: a function of the same module, one imported from another
    omni_prod module, a method called on self or cls, or a function called on an imported omni_prod module. Never a
    function of another module by its name alone: two helpers with one name in two modules are two helpers."""
    func = node.func
    if isinstance(func, ast.Name):
        if func.id in functions.get(m.name, ()):
            return m.name, func.id
        if func.id in m.imported:
            module, original = m.imported[func.id]
            return (module, original) if original in functions.get(module, ()) else None
        return None
    if isinstance(func, ast.Attribute):
        owner = _dotted(func.value)
        if owner in ('self', 'cls') and func.attr in functions.get(m.name, ()):
            return m.name, func.attr
        if owner in m.aliases and func.attr in functions.get(m.aliases[owner], ()):
            return m.aliases[owner], func.attr
    return None


def _helper_args(node, callee: tuple[str, str], helpers: dict):
    """(expression, marker) for each argument that a known helper takes as a name ('p') or a collection of names
    ('p[]'), when `node` calls one."""
    if callee not in helpers:
        return []
    out = []
    for index, marker in sorted(helpers[callee], key=lambda p: (p[0] is None, p[0] or 0, p[1])):
        param = marker[:-2] if marker.endswith('[]') else marker
        if index is not None and index < len(node.args) and not isinstance(node.args[index], ast.Starred):
            out.append((node.args[index], marker))
        else:
            out += [(k.value, marker) for k in node.keywords if k.arg == param]
    return out


def env_reads(sources: dict) -> dict:
    """{'names': {NAME: {file, ...}}, 'helpers': [...], 'unresolved': [file:line, ...]} for the given modules."""
    modules: dict[str, _Module] = {}
    for name, (rel, tree) in sources.items():
        modules[name] = _Module(name, rel, tree, modules)
    for m in modules.values():
        m.collect()
    functions = {name: {n.name for n in _all_nodes(m.tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                 for name, m in modules.items()}
    scopes = []                                          # (module, function or None, scope)
    for m in modules.values():
        scopes.append((m, None, _Scope(m)))
        for node in _all_nodes(m.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scopes.append((m, node, _Scope(m, node)))
    for m, _fn, scope in scopes:                         # the calls of a function of the package, found once
        scope.package_calls = [(n, c) for n in scope.calls for c in [_callee(n, m, functions)] if c]

    def reads(m, fn, scope, helpers):
        """(expression, the names it gives, the caller's parameter markers it passes on, whether it is unresolved)"""
        sites = [(key, 'name') for key in scope.env_keys]
        for node, callee in scope.package_calls:
            sites += _helper_args(node, callee, helpers)
        for expr, marker in sites:
            found = scope.resolve(expr)
            collection = marker.endswith('[]')
            if found is None:
                yield expr, set(), set(), not collection   # a collection the map cannot read is not counted
                continue
            names, markers = found
            if collection:                               # the caller passes its own parameter as the collection
                markers = {x + '[]' for x in markers if not x.endswith('[]')}
            yield expr, names, markers, False

    helpers: dict[tuple[str, str], set] = {}
    bound = sum(len(s.params) for _m, _f, s in scopes) * 2 + 2
    for _ in range(bound):                               # a helper that calls a helper: until nothing new is found
        changed = False
        for m, fn, scope in scopes:
            if fn is None or fn.name in _NOT_A_HELPER:
                continue
            positional = _params(fn)
            for _expr, _names, markers, _u in reads(m, fn, scope, helpers):
                for marker in markers:
                    param = marker[:-2] if marker.endswith('[]') else marker
                    entry = (positional.index(param) if param in positional else None, marker)
                    if entry not in helpers.setdefault((m.name, fn.name), set()):
                        helpers[(m.name, fn.name)].add(entry)
                        changed = True
        if not changed:
            break
    else:
        raise RuntimeError(f'system_map: helper detection did not settle in {bound} rounds')

    names: dict[str, set] = {}
    unresolved = set()
    for m, fn, scope in scopes:
        for expr, found, _markers, lost in reads(m, fn, scope, helpers):
            if lost:
                unresolved.add(f'{m.rel}:{expr.lineno}')
            for n in found:
                if _ENV_NAME.fullmatch(n):
                    names.setdefault(n, set()).add(m.rel)
    listed = sorted(f'{module}.{fn}({", ".join(sorted(x for _i, x in params))})'
                    for (module, fn), params in helpers.items() if params)
    return {'names': names, 'helpers': listed, 'unresolved': sorted(unresolved, key=lambda s: (s.split(':')[0],
                                                                                              int(s.split(':')[1])))}


def environment(sources: dict | None = None) -> tuple[list[dict], dict]:
    found = env_reads(_sources() if sources is None else sources)
    rows = [{'name': k, 'read_in': sorted(v)} for k, v in sorted(found['names'].items())]
    method = {'how': ENV_METHOD, 'helpers': found['helpers'], 'unresolved': len(found['unresolved']),
              'unresolved_at': found['unresolved']}
    return rows, method


def _package(module: str) -> str:
    parts = module.split('.')
    if parts[0] != 'omni_prod':
        return ''
    sub = ROOT.joinpath(*parts[:2])
    return '.'.join(parts[:2]) if len(parts) > 1 and sub.is_dir() else 'omni_prod (top-level modules)'


def resolve(module: str, node: ast.ImportFrom | ast.Import) -> list[str]:
    """The absolute modules an import statement in `module` names (Python's own rule for relative imports: the
    module's package, minus level-1 parts)."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    if not node.level:
        return [node.module] if node.module else []
    package = module.split('.')[:-1]                  # 'a.b.c' -> a.b ; 'a.b.__init__' -> a.b
    base = package[:len(package) - (node.level - 1)] if node.level > 1 else package
    if node.module:
        return ['.'.join(base + [node.module])]
    return ['.'.join(base + [a.name]) for a in node.names]


def dependencies(sources: dict | None = None) -> list[dict]:
    edges: dict[str, set] = {}
    for name, (rel, tree) in (_sources() if sources is None else sources).items():
        module = name + '.__init__' if rel.endswith('__init__.py') else name
        here = _package(module)
        for node in _all_nodes(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for target in resolve(module, node):
                    there = _package(target)
                    if there and there != here:
                        edges.setdefault(here, set()).add(there)
    return [{'package': k, 'imports': sorted(v)} for k, v in sorted(edges.items())]


def limitations() -> dict:
    truth, matrix = _json('TRUTH_MATRIX.json'), _json('PROVIDER_MATRIX.json')
    return {'customer_visible_findings': truth.get('customer_visible_findings') or [],
            'capability_gaps': matrix.get('capability_gaps') or [],
            'legacy_routes': matrix.get('legacy_routes') or []}


# ---- the map ------------------------------------------------------------------------------------------------------
def _counts(rows: list[dict]) -> dict:
    out = {s: 0 for s in PLAN_STATES}
    for r in rows:
        out[r['state']] += 1
    return out


def build() -> dict:
    """The full map. The same tree gives the same map: nothing here reads a clock, the network or the environment."""
    sources = _sources()
    a, r, s, m = agents(), roles(), skills(), models()
    db, q = database(), queues()
    env, env_method = environment(sources)
    inventory = {'endpoints': endpoints(sources), 'database': db, 'services': services(), 'queues': q['queues'],
                 'queue_prefixes': q['queue_prefixes'], 'workflows': workflows(), 'environment': env,
                 'environment_method': env_method, 'dependencies': dependencies(sources)}
    return {
        'schema': SCHEMA,
        'states': list(PLAN_STATES),
        'mapping': PLAN_STATE,
        'mapping_decisions': [{'rule': k, 'why': v} for k, v in MAPPING_DECISIONS],
        'live_rule': LIVE_RULE,
        'summary': {
            'agents': _counts(a), 'roles': _counts(r), 'skills': _counts(s), 'models': _counts(m),
            'endpoints': len(inventory['endpoints']), 'tables': len(db['tables']), 'migrations': len(db['migrations']),
            'rollback_files': len(db['rollback_files']), 'services': len(inventory['services']),
            'queues': len(q['queues']), 'queue_prefixes': len(q['queue_prefixes']),
            'workflows': len(inventory['workflows']), 'environment_names': len(env),
            'environment_reads_unresolved': env_method['unresolved'],
        },
        'agents': a, 'roles': r, 'skills': s, 'models': m,
        **inventory,
        'limitations': limitations(),
    }


def to_json(m: dict) -> str:
    return json.dumps(m, ensure_ascii=False, indent=1, sort_keys=False) + '\n'


def _md_counts(title: str, counts: dict) -> str:
    return f'| {title} | ' + ' | '.join(str(counts[s]) for s in PLAN_STATES) + f' | {sum(counts.values())} |'


def render_mapping() -> str:
    """docs/SYSTEM_MAP.md: the mapping and how the map is read. It depends on this file alone, never on the inventory,
    so no other pull request can make it stale."""
    added = len(MAPPING_DECISIONS) - RULES_ADDED_AFTER_APPROVAL
    out = ['# System map', '',
           'The state mapping of the system map (the owner\'s plan v3, S1.5). Generated by '
           '`python -m omni_prod.system_map --write` from `omni_prod/system_map.py` alone. Do not edit by hand: '
           '`tests/test_system_map.py` fails when this file differs from what the code gives.', '',
           '## Where the full map is', '',
           'The full map -- every agent, role, skill and model with its state, and the inventory (endpoints, tables and '
           'migrations, worker services, queues, workflows, environment variable names, package dependencies, known '
           'limitations) -- is not committed. It changes with almost every pull request, and a committed copy goes '
           'stale on main whenever a branch cut before it, or two green pull requests that each regenerated it, merge: '
           'the required jobs test the head of a pull request, not the merge (the review of #532, 2026-11-25; '
           'CLAUDE.md section 4).', '',
           '- **In CI**, on every push to main and every pull request: the job `light` of `v24-ci` builds it, keeps it '
           'as the artifact `system-map` (`SYSTEM_MAP.json`) of the run, and writes a summary table into the run\'s '
           'summary. A failure of the generator fails that step; `light` is not a required check.',
           '- **Locally:** `python -m omni_prod.system_map --write` writes it to `SYSTEM_MAP.json` at the root of the '
           'repository, which git ignores; `python -m omni_prod.system_map --json PATH` writes it anywhere.', '',
           '## States', '',
           'The plan\'s six states: ' + ', '.join(PLAN_STATES) + '.', '',
           LIVE_RULE, '',
           '### How a source word becomes a state', '',
           '| Source word | State |', '|---|---|']
    out += [f'| {k} | {v} |' for k, v in PLAN_STATE.items()]
    out += ['', 'A word that is not in this table raises: a new status in a source is classified by a person, never '
            'guessed.', '',
            'Rules beyond the table. OWNERS.md rule 7 records the owner\'s approval of the mapping on the evening of '
            '2026-11-25, given as a general approval ("מאשר לך הכול"). The rules marked "added later" and the words '
            + ', '.join(WORDS_ADDED_AFTER_APPROVAL) + ' were added after that by the review of #532; they rest on '
            'his standing approval (OWNERS.md rule 1):', '']
    out += [f'- {d[0]}: {d[1]}.' + (' (added later)' if i >= added else '')
            for i, d in enumerate(MAPPING_DECISIONS)]
    out += ['', '## How the inventory is read', '',
            '- Endpoints: the route decorators of every omni_prod module, with the prefix of their `APIRouter` and of '
            'an `include_router(..., prefix=...)`; a prefix the map cannot read raises.',
            '- Database: `CREATE TABLE` in `infra/postgres/<number>_*.sql`; down files in `infra/postgres/rollback/`.',
            '- Queues: the queue names in ' + ' and '.join(f'`{f}`' for f in QUEUE_FILES) + '; a name ending in `-` '
            'is a prefix of per-host queues and is listed apart, never as a queue.',
            f'- Environment variable names (names only, never values): {ENV_METHOD}',
            '- Agents, roles, skills and models: `AGENT_OS_REGISTRY.json`, `omni_prod.registry_audit`, '
            '`PROVIDER_MATRIX.json`, through the table above.']
    return '\n'.join(out) + '\n'


def summary(m: dict, sha: str | None = None) -> str:
    """A short table for the run's summary; the full rows are in the artifact."""
    s = m['summary']
    em = m['environment_method']
    out = [f'## System map{" of " + sha if sha else ""}', '',
           '| | ' + ' | '.join(PLAN_STATES) + ' | total |', '|---|' + '---|' * (len(PLAN_STATES) + 1),
           _md_counts('agents (AGENT_OS_REGISTRY)', s['agents']), _md_counts('roles (registry_audit)', s['roles']),
           _md_counts('skills (skill catalog + runtime)', s['skills']),
           _md_counts('models (PROVIDER_MATRIX)', s['models']), '', LIVE_RULE, '',
           '| Inventory | Count |', '|---|---|',
           f'| endpoints | {s["endpoints"]} |',
           f'| tables (migrations {s["migrations"]}, highest {m["database"]["highest"]}, rollback files '
           f'{s["rollback_files"]}) | {s["tables"]} |',
           f'| worker host services | {s["services"]} |',
           f'| queues ({", ".join(q["name"] for q in m["queues"])}; prefixes '
           f'{", ".join(p["prefix"] for p in m["queue_prefixes"]) or "none"}) | {s["queues"]} |',
           f'| workflows ({sum(1 for w in m["workflows"] if w["schedules"])} scheduled) | {s["workflows"]} |',
           f'| environment variable names (literals, constants and {len(em["helpers"])} helpers; '
           f'{em["unresolved"]} reads built at run time are not resolved) | {s["environment_names"]} |',
           f'| package dependency rows | {len(m["dependencies"])} |', '',
           'The full rows are in the artifact `system-map` of this run (`SYSTEM_MAP.json`); the mapping is in '
           '`docs/SYSTEM_MAP.md`.']
    return '\n'.join(out) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='148AI system map')
    ap.add_argument('--write', action='store_true', help='docs/SYSTEM_MAP.md and the local SYSTEM_MAP.json')
    ap.add_argument('--check', action='store_true', help='exit 1 when docs/SYSTEM_MAP.md is stale')
    ap.add_argument('--json', metavar='PATH', help='write the full map to PATH')
    ap.add_argument('--summary', metavar='PATH', help='append the summary table to PATH')
    args = ap.parse_args(argv)
    md = render_mapping()
    if args.check:
        if not MD_OUT.exists() or MD_OUT.read_text(encoding='utf-8') != md:
            print(f'::error title=system map::{_rel(MD_OUT)} is stale: python -m omni_prod.system_map --write')
            return 1
        print(f'::notice title=system map::{_rel(MD_OUT)} is the mapping of omni_prod/system_map.py')
        if not (args.write or args.json or args.summary):
            return 0
    full = build() if (args.write or args.json or args.summary or not args.check) else None
    if args.write:
        MD_OUT.write_text(md, encoding='utf-8')
        JSON_LOCAL.write_text(to_json(full), encoding='utf-8')
        print(f'wrote {_rel(MD_OUT)} and {_rel(JSON_LOCAL)} (ignored by git)')
    if args.json:
        Path(args.json).write_text(to_json(full), encoding='utf-8')
        print(f'::notice title=system map::wrote {args.json} ({full["summary"]["endpoints"]} endpoints, '
              f'{full["summary"]["environment_names"]} environment names, {full["summary"]["workflows"]} workflows)')
    if args.summary:
        with open(args.summary, 'a', encoding='utf-8') as fh:
            fh.write(summary(full, os.environ.get('GITHUB_SHA')))
    if not (args.write or args.json or args.summary or args.check):
        sys.stdout.write(summary(full))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

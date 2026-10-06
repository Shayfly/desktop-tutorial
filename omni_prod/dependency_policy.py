"""Dependency allowlist for generated code (founder decision 2026-10-07 #25).

Golden E2E #1 runs generated code only with what is pre-installed and pinned
in the sandbox image (infra/sandbox/Dockerfile). There is no package proxy,
no network and no install step. Anything else fails explicitly as
UNSUPPORTED_DEPENDENCY *before* the sandbox runs, so no compute is spent on a
build that cannot work.

Why the runtime allowlist is the standard library only: the preview container
(preview_runtime.DEFAULT_ALLOWED_RUNTIMES, stock python:3.11-slim) starts the
app with no install step. A runtime package present in the sandbox but not in
the preview image would let tests pass and preview fail. Widening the runtime
set means baking the same pinned packages into both images (a later,
deliberate change; see docs/DECISIONS_2026-10-07_HE.md #25).

Checks, in order:
* install steps in .omni/project.json build/verify commands (pip/npm/... install);
* a Node toolchain (package.json dependencies or a node runtime): the sandbox
  image has no Node;
* declared Python requirements (requirements*.txt, pyproject.toml) outside the
  allowlist or pinned to a different version than the image's;
* imports of anything that is not the standard library, a module of the
  repository itself, or an allowlisted test-only package used from test code.
  Imports guarded by `except ImportError` are optional and allowed.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import re
import sys
import tomllib

from .attempt_ledger import content_version
from .autonomous_core import AcceptanceFailure, ExecutionReport

UNSUPPORTED_DEPENDENCY = 'UNSUPPORTED_DEPENDENCY'

# Distribution name (PEP 503 normalized) -> exact version baked into the image.
TEST_ONLY_PACKAGES: dict[str, str] = {'pytest': '8.3.5'}
RUNTIME_PACKAGES: dict[str, str] = {}
# Import name -> distribution name, for the allowlisted packages.
_IMPORT_TO_DIST = {'pytest': 'pytest', '_pytest': 'pytest'}

POLICY_VERSION = content_version('dependency-policy', TEST_ONLY_PACKAGES, RUNTIME_PACKAGES, 'stdlib-runtime')

ALLOWED_SUMMARY = ('application code: Python standard library only; tests: '
                   + ', '.join(f'{k}=={v}' for k, v in sorted(TEST_ONLY_PACKAGES.items())))

GENERATION_CONSTRAINTS = (
    'Dependency policy (enforced before verification): the repository is verified in an offline Python sandbox with '
    'no network and no package installation. Write the product in Python; application code may import only the '
    f'Python standard library; tests may additionally use {", ".join(sorted(TEST_ONLY_PACKAGES))}. Do not add install '
    'steps, third-party packages or a Node toolchain; anything else fails the build as UNSUPPORTED_DEPENDENCY.'
)

_STDLIB = frozenset(sys.stdlib_module_names) | {'__future__'}
_INSTALLERS = {('pip', 'install'), ('pip3', 'install'), ('npm', 'install'), ('npm', 'ci'), ('npm', 'i'),
               ('yarn', 'install'), ('yarn', 'add'), ('pnpm', 'install'), ('pnpm', 'add'), ('poetry', 'install'),
               ('pipenv', 'install'), ('uv', 'pip'), ('uv', 'add'), ('uv', 'sync'), ('apt-get', 'install'),
               ('apk', 'add'), ('easy_install', None), ('conda', 'install')}
_REQ_LINE = re.compile(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*?)\s*(;.*)?$')
_SPEC = re.compile(r'^\s*(==|!=|<=|>=|~=|<|>)\s*([0-9][0-9A-Za-z.*+!-]*)\s*$')


@dataclass(frozen=True)
class UnsupportedDependency:
    name: str
    source: str
    reason: str

    def to_dict(self) -> dict:
        return {'name': self.name, 'source': self.source, 'reason': self.reason}


def _norm(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def _is_test_path(path: str) -> bool:
    parts = path.split('/')
    base = parts[-1]
    return (any(p in ('tests', 'test') for p in parts[:-1]) or base.startswith('test_')
            or base.endswith('_test.py') or base == 'conftest.py')


def _version_tuple(v: str):
    out = []
    for piece in v.split('.'):
        if not piece.isdigit():
            return None
        out.append(int(piece))
    return tuple(out)


def _spec_allows(spec: str, pinned: str) -> bool | None:
    """True/False when the specifier set can be evaluated, None when it cannot."""
    spec = spec.strip()
    if not spec:
        return True
    have = _version_tuple(pinned)
    for clause in spec.split(','):
        m = _SPEC.match(clause)
        if not m:
            return None
        op, raw = m.groups()
        if op in ('==', '!=') and raw.endswith('.*'):
            prefix = _version_tuple(raw[:-2])
            if prefix is None:
                return None
            hit = have[:len(prefix)] == prefix
            ok = hit if op == '==' else not hit
        else:
            want = _version_tuple(raw)
            if want is None:
                return None
            n = max(len(have), len(want))
            a, b = have + (0,) * (n - len(have)), want + (0,) * (n - len(want))
            if op == '~=':
                ok = a >= b and a[:len(want) - 1] == b[:len(want) - 1]
            else:
                ok = {'==': a == b, '!=': a != b, '<=': a <= b, '>=': a >= b, '<': a < b, '>': a > b}[op]
        if not ok:
            return False
    return True


def _check_requirement(line: str, source: str, *, test_scope: bool) -> UnsupportedDependency | None:
    line = line.split('#', 1)[0].strip()
    if not line:
        return None
    if line.startswith(('-', 'git+', 'http:', 'https:', 'file:')) or '@' in line.split(';')[0]:
        return UnsupportedDependency(line[:80], source, 'install options, URLs and direct references are not supported')
    m = _REQ_LINE.match(line)
    if not m:
        return UnsupportedDependency(line[:80], source, 'unparseable requirement')
    name, spec = _norm(m.group(1)), m.group(3) or ''
    allowed = {**RUNTIME_PACKAGES, **(TEST_ONLY_PACKAGES if test_scope else {})}
    if name not in allowed:
        where = 'test-only package required by application code' if name in TEST_ONLY_PACKAGES else 'not in the allowlist'
        return UnsupportedDependency(name, source, where)
    verdict = _spec_allows(spec, allowed[name])
    if verdict is None:
        return UnsupportedDependency(name, source, f'version specifier {spec!r} cannot be verified against the image')
    if not verdict:
        return UnsupportedDependency(name, source, f'requires {spec}; the sandbox image provides {allowed[name]}')
    return None


def _requirement_files(repository: dict[str, str]):
    for path, content in repository.items():
        base = path.rsplit('/', 1)[-1].lower()
        if base.endswith('.txt') and base.startswith('requirements'):
            test_scope = any(t in base for t in ('test', 'dev'))
            for line in content.splitlines():
                yield line, path, test_scope


def _pyproject(repository: dict[str, str], findings: list) -> None:
    for path, content in repository.items():
        if path.rsplit('/', 1)[-1] != 'pyproject.toml':
            continue
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            findings.append(UnsupportedDependency('pyproject.toml', path, 'unparseable pyproject.toml'))
            continue
        project = data.get('project') or {}
        for req in project.get('dependencies') or []:
            f = _check_requirement(str(req), path, test_scope=False)
            if f:
                findings.append(f)
        for group, reqs in (project.get('optional-dependencies') or {}).items():
            test_scope = any(t in group.lower() for t in ('test', 'dev'))
            for req in reqs or []:
                f = _check_requirement(str(req), f'{path}[{group}]', test_scope=test_scope)
                if f:
                    findings.append(f)
        if (data.get('tool') or {}).get('poetry', {}).get('dependencies'):
            findings.append(UnsupportedDependency('poetry', path, 'poetry dependency management is not supported'))


def _local_modules(repository: dict[str, str]) -> set[str]:
    names = set()
    for path in repository:
        parts = path.split('/')
        for i, part in enumerate(parts):
            if part.endswith('.py'):
                names.add(part[:-3])
            elif i < len(parts) - 1:
                names.add(part)
    return names


def _optional_import_nodes(tree) -> set[int]:
    """ids of Import/ImportFrom nodes inside a try whose handler catches ImportError."""
    optional = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        catches = False
        for h in node.handlers:
            names = []
            if h.type is None:
                catches = True
            elif isinstance(h.type, ast.Name):
                names = [h.type.id]
            elif isinstance(h.type, ast.Tuple):
                names = [e.id for e in h.type.elts if isinstance(e, ast.Name)]
            if any(n in ('ImportError', 'ModuleNotFoundError', 'Exception') for n in names):
                catches = True
        if catches:
            for stmt in node.body:
                for sub in ast.walk(stmt):
                    if isinstance(sub, (ast.Import, ast.ImportFrom)):
                        optional.add(id(sub))
    return optional


def _imports(repository: dict[str, str], findings: list) -> None:
    local = _local_modules(repository)
    for path, content in sorted(repository.items()):
        if not path.endswith('.py'):
            continue
        try:
            tree = ast.parse(content, filename=path)
        except (SyntaxError, ValueError):
            continue  # a syntax error is the tests' job to report
        optional = _optional_import_nodes(tree)
        test_scope = _is_test_path(path)
        seen = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                tops = [a.name.split('.')[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                tops = [node.module.split('.')[0]]
            else:
                continue
            if id(node) in optional:
                continue
            for top in tops:
                if top in seen or top in _STDLIB or top in local:
                    continue
                seen.add(top)
                dist = _IMPORT_TO_DIST.get(top)
                if dist in RUNTIME_PACKAGES or (test_scope and dist in TEST_ONLY_PACKAGES):
                    continue
                reason = ('test-only package imported by application code' if dist in TEST_ONLY_PACKAGES
                          else 'not in the standard library, the repository or the allowlist')
                findings.append(UnsupportedDependency(top, path, reason))


def _manifest(repository: dict[str, str], findings: list) -> None:
    raw = repository.get('.omni/project.json')
    if raw is None:
        return
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return  # manifest validity is checked by the executor
    runtime = data.get('runtime')
    if isinstance(runtime, str) and runtime.startswith('node'):
        findings.append(UnsupportedDependency('node', '.omni/project.json', 'the sandbox image has no Node toolchain'))
    commands = list(data.get('build') or [])
    if isinstance(data.get('start'), list):
        commands.append(data['start'])          # the preview start command runs with no install step too
    for check in data.get('verify') or []:
        if isinstance(check, dict):
            commands.append(check.get('argv') or [])
    for argv in commands:
        if isinstance(argv, list) and _is_install(argv):
            findings.append(UnsupportedDependency(' '.join(map(str, argv))[:80], '.omni/project.json',
                                                  'install steps are not allowed; the sandbox is offline'))


def _is_install(argv: list) -> bool:
    words = [str(w).rsplit('/', 1)[-1] for w in argv]
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (w, nxt) in _INSTALLERS or (w, None) in _INSTALLERS:
            return True
        if w.startswith('python') and words[i + 1:i + 4] == ['-m', 'pip', 'install']:
            return True
    return False


def _node(repository: dict[str, str], findings: list) -> None:
    for path, content in repository.items():
        if path.rsplit('/', 1)[-1] != 'package.json' or '/node_modules/' in f'/{path}':
            continue
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            data = {}
        deps = {**(data.get('dependencies') or {}), **(data.get('devDependencies') or {})}
        if deps:
            findings.append(UnsupportedDependency(', '.join(sorted(deps))[:80], path,
                                                  'the sandbox image has no Node toolchain'))


def scan(repository: dict[str, str]) -> tuple[UnsupportedDependency, ...]:
    findings: list[UnsupportedDependency] = []
    _manifest(repository, findings)
    _node(repository, findings)
    for line, source, test_scope in _requirement_files(repository):
        f = _check_requirement(line, source, test_scope=test_scope)
        if f:
            findings.append(f)
    _pyproject(repository, findings)
    _imports(repository, findings)
    unique = {}
    for f in findings:
        unique.setdefault((f.name, f.source, f.reason), f)
    return tuple(unique.values())


def unsupported_report(findings) -> ExecutionReport:
    detail = '; '.join(f'{f.name} ({f.source}): {f.reason}' for f in findings)
    message = f'unsupported dependency: {detail}'[:1500]
    evidence = json.dumps({'policy_version': POLICY_VERSION, 'allowed': ALLOWED_SUMMARY,
                           'findings': [f.to_dict() for f in findings]})[:4000]
    return ExecutionReport(False, (AcceptanceFailure(UNSUPPORTED_DEPENDENCY, message, evidence),),
                           f'[{UNSUPPORTED_DEPENDENCY}] sandbox not started. Allowed: {ALLOWED_SUMMARY}. {message}')


class DependencyGateExecutor:
    """Runs the allowlist check before the wrapped executor; an unsupported
    dependency returns an explicit failure without starting the sandbox."""

    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        findings = scan(repository)
        if findings:
            return unsupported_report(findings)
        return self._inner.execute(repository=repository, spec=spec)

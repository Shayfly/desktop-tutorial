"""Cross-file consistency gate (Executive directive 2026-10-10, P0 items 4/5/7).

Deterministic, model-free checks that run on a candidate repository BEFORE the
sandbox starts, so the most common integration mistakes of generated code are
reported with an exact `file:line` and a concrete fix instead of a generic
"unit tests failed" after a sandbox run:

  syntax        every .py compiles; every .json parses
  imports       `from local_module import name` -> name exists in that module
  routes        paths the page calls (fetch/XHR/form action) and paths the
                behavioural acceptance plan calls exist on the server side
  static        local scripts/styles/images the page references exist or are served
  manifest      files named in .omni/project.json commands exist
  plan_code     what the acceptance plan makes users do (create, update, delete) exists in the code: the server
                handles the method, and the page has a control and client code that sends it

Every check is conservative: when the repository's shape is not understood
(no server source, dynamic paths) the check is skipped, never guessed. The
replay tool (`python -m omni_prod.gate_replay`) runs this gate over every stored
real version so a check that would block a working product is caught before
the gate is enabled (OMNI_CONSISTENCY_GATE).

Accessibility findings (labels, lang/dir, alt text, button names) are reported
as advisories with their file and line; they do not block.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field

CONSISTENCY_FAILURE_ID = 'CONSISTENCY'

_CLIENT_SUFFIXES = ('.html', '.htm', '.js', '.mjs', '.jsx', '.ts', '.tsx', '.vue', '.svelte')
_PY_HTML = re.compile(r'<(?:html|form|input|script|link|div|body)\b', re.I)
_FETCH = re.compile(r'''\bfetch\(\s*(['"`])(.+?)\1''')
_XHR = re.compile(r'''\.open\(\s*['"][A-Z]+['"]\s*,\s*(['"`])(.+?)\1''')
_FORM_ACTION = re.compile(r'''<form\b[^>]*\baction\s*=\s*(['"])(.+?)\1''', re.I)
_ASSET = re.compile(r'''<(?:script|img|link|source)\b[^>]*\b(?:src|href)\s*=\s*(['"])([^'"]+)\1''', re.I)
_ASSET_EXT = ('.js', '.mjs', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico', '.json', '.woff', '.woff2')
_TEMPLATE = re.compile(r'\$\{[^}]*\}|\{\{[^}]*\}\}|\{[A-Za-z_][A-Za-z0-9_]*\}|<[A-Za-z_]+>|:[A-Za-z_][A-Za-z0-9_]*')
_TEST_PATH = re.compile(r'(^|/)(tests?|__tests__)/|(^|/)test_[^/]*\.py$|_test\.py$|\.(test|spec)\.[jt]sx?$')
_SERVER_JS = re.compile(r'createServer|express\(|\.listen\(|fastify|new Hono|Deno\.serve|Bun\.serve')


@dataclass(frozen=True)
class Finding:
    check: str
    path: str
    line: int | None
    message: str
    fix: str
    blocking: bool = True

    def where(self) -> str:
        return f'{self.path}:{self.line}' if self.line else self.path


@dataclass
class ConsistencyReport:
    findings: list[Finding] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if f.blocking]

    @property
    def advisories(self) -> list[Finding]:
        return [f for f in self.findings if not f.blocking]

    def to_dict(self) -> dict:
        return {'passed': not self.blocking, 'checks_run': self.checks_run, 'skipped': self.skipped,
                'blocking': [f.__dict__ for f in self.blocking][:40],
                'advisories': [f.__dict__ for f in self.advisories][:40]}


def _line_of(text: str, index: int) -> int:
    return text.count('\n', 0, index) + 1


def _is_test(path: str) -> bool:
    return bool(_TEST_PATH.search(path))


# ------------------------------------------------------------------ syntax --
def _syntax(repo: dict[str, str], out: list[Finding]) -> None:
    for path, text in sorted(repo.items()):
        if path.endswith('.py'):
            try:
                compile(text, path, 'exec', dont_inherit=True)
            except SyntaxError as exc:
                out.append(Finding('syntax', path, exc.lineno, f'Python syntax error: {exc.msg}',
                                   'fix the syntax so the file compiles'))
            except ValueError as exc:  # e.g. null bytes
                out.append(Finding('syntax', path, None, f'Python source cannot be compiled: {exc}',
                                   'remove invalid characters from the file'))
        elif path.endswith('.json'):
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                out.append(Finding('syntax', path, exc.lineno, f'invalid JSON: {exc.msg}', 'write valid JSON'))


# ----------------------------------------------------------------- imports --
def _module_index(repo: dict[str, str]) -> dict[str, str]:
    """module name -> path, for top-level and package modules in the repo."""
    idx = {}
    for path in repo:
        if not path.endswith('.py'):
            continue
        parts = path[:-3].split('/')
        if parts[-1] == '__init__':
            parts = parts[:-1]
        if parts:
            idx['.'.join(parts)] = path
            # src/ layout and test-time sys.path insertions: also index the tail
            if parts[0] in ('src', 'app', 'backend', 'server') and len(parts) > 1:
                idx.setdefault('.'.join(parts[1:]), path)
    return idx


def _top_level_names(tree: ast.Module) -> set[str] | None:
    """Names a module defines at top level; None when it cannot be known
    (star import, module __getattr__, dynamic globals())."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if node.name == '__getattr__':
                return None
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                if a.name == '*':
                    return None
                names.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            # conditional definitions: collect anything assigned/defined inside
            for n in ast.walk(node):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.add(n.name)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                    names.add(n.id)
                elif isinstance(n, (ast.Import, ast.ImportFrom)):
                    for a in n.names:
                        if a.name == '*':
                            return None
                        names.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, ast.Expr) and 'globals()' in ast.dump(node):
            return None
    return names


def _imports(repo: dict[str, str], out: list[Finding]) -> None:
    idx = _module_index(repo)
    parsed: dict[str, ast.Module | None] = {}

    def tree_of(path):
        if path not in parsed:
            try:
                parsed[path] = ast.parse(repo[path])
            except (SyntaxError, ValueError):
                parsed[path] = None
        return parsed[path]

    for path, text in sorted(repo.items()):
        if not path.endswith('.py'):
            continue
        tree = tree_of(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level or not node.module:
                continue
            target = idx.get(node.module)
            if target is None or target == path:
                continue
            ttree = tree_of(target)
            if ttree is None:
                continue
            defined = _top_level_names(ttree)
            if defined is None:
                continue
            submodules = {m.split('.')[-1] for m in idx if m.startswith(node.module + '.')}
            for alias in node.names:
                if alias.name != '*' and alias.name not in defined and alias.name not in submodules:
                    out.append(Finding('imports', path, node.lineno,
                                       f'imports {alias.name!r} from {node.module} ({target}), which does not define it',
                                       f'define {alias.name} in {target} or import the name that exists there'))


# ------------------------------------------------------------------ routes --
def _server_text(repo: dict[str, str]) -> str:
    parts = []
    for path, text in repo.items():
        if _is_test(path):
            continue
        if path.endswith('.py') or (path.endswith(('.js', '.mjs', '.ts')) and _SERVER_JS.search(text)):
            parts.append(text)
    return '\n'.join(parts)


def _static_prefix(raw: str) -> str | None:
    """'/api/items/${id}?x=1' -> '/api/items'; None when not a local path."""
    url = raw.strip()
    if url.startswith(('http://', 'https://')):
        m = re.match(r'https?://(?:localhost|127\.0\.0\.1)(?::\d+)?(/.*)?$', url)
        if not m:
            return None
        url = m.group(1) or '/'
    if not url.startswith('/') or url.startswith('//'):
        return None
    url = re.split(r'[?#]', url, maxsplit=1)[0]
    m = _TEMPLATE.search(url)
    if m:
        url = url[:m.start()]
    segments = [s for s in url.split('/') if s and not s.isdigit()]
    if not segments:
        return None
    return '/' + '/'.join(segments)


_GENERIC = {'api', 'v1', 'v2', 'static', 'assets', 'public'}


def _served(prefix: str, server: str) -> bool:
    if prefix in server or prefix.rstrip('/') + '/' in server:
        return True
    segments = prefix.strip('/').split('/')
    # a prefix handler for a specific parent: startswith('/team/') serves
    # /team/maccabi-tel-aviv (replay 38071176710: false positive otherwise)
    for k in range(len(segments) - 1, 0, -1):
        parent = segments[:k]
        if parent[-1] not in _GENERIC and '/' + '/'.join(parent) + '/' in server:
            return True
    # path dispatched by segments: parts[0] == 'api' and parts[1] == 'items'
    return all(re.search(r'''['"]%s['"]''' % re.escape(s), server) for s in segments)


def _routes(repo: dict[str, str], out: list[Finding], report: ConsistencyReport) -> None:
    server = _server_text(repo)
    if not server.strip():
        report.skipped['routes'] = 'no server source found'
        return
    seen = set()
    for path, text in sorted(repo.items()):
        if _is_test(path) or not (path.endswith(_CLIENT_SUFFIXES) or (path.endswith('.py') and _PY_HTML.search(text))):
            continue
        for rx in (_FETCH, _XHR, _FORM_ACTION):
            for m in rx.finditer(text):
                prefix = _static_prefix(m.group(2))
                if not prefix or (path, prefix) in seen:
                    continue
                seen.add((path, prefix))
                if not _served(prefix, server.replace(m.group(0), '')):
                    out.append(Finding('routes', path, _line_of(text, m.start()),
                                       f'the page calls {prefix} but no server route handles it',
                                       f'add a server handler for {prefix} or call the route the server provides'))
    manifest = repo.get('.omni/project.json')
    if manifest:
        try:
            plan = json.loads(manifest).get('web_saas_acceptance') or {}
        except (json.JSONDecodeError, AttributeError):
            return
        for persona in plan.get('personas') or []:
            for step in (persona or {}).get('steps') or []:
                prefix = _static_prefix(str((step or {}).get('path', '')))
                if prefix and not _served(prefix, server):
                    out.append(Finding('routes', '.omni/project.json', None,
                                       f"acceptance step {step.get('id')} calls {prefix} but no server route handles it",
                                       'make the step call a route the server provides, or add the missing route'))


# ------------------------------------------------------------------ static --
def _static(repo: dict[str, str], out: list[Finding]) -> None:
    server = _server_text(repo)
    names = {p.rsplit('/', 1)[-1] for p in repo}
    for path, text in sorted(repo.items()):
        if _is_test(path) or not path.endswith(('.html', '.htm')) and not (path.endswith('.py') and _PY_HTML.search(text)):
            continue
        for m in _ASSET.finditer(text):
            ref = m.group(2).strip()
            if ref.startswith(('http:', 'https:', '//', 'data:', '#', 'mailto:', 'tel:', 'javascript:')) or '{' in ref or '$' in ref:
                continue
            clean = re.split(r'[?#]', ref, maxsplit=1)[0]
            if not clean.lower().endswith(_ASSET_EXT):
                continue
            rel = clean.lstrip('./').lstrip('/')
            base = rel.rsplit('/', 1)[-1]
            # a route that serves exactly this path, not the reference itself
            if rel in repo or base in names or clean in server.replace(m.group(0), ''):
                continue
            out.append(Finding('static', path, _line_of(text, m.start()),
                               f'references {clean}, which is neither a file in the repository nor served',
                               f'add {rel} to the repository or remove the reference'))


# --------------------------------------------------------------- plan_code --
# Paid run 39473090833 (R2 read 39477884309, 2026-10-20): the plan had data_create (S3 POST /api/appointments) and
# data_delete (S4 DELETE /api/appointments/1); index.html said "you can book in the form below" and contained no form,
# no input, no button and no script. Preview rejected it twice and behaviour failed, for three rounds. All of that is
# visible by reading the files: plan against code, like the round pre-flight's plan checks (#85).
_UI_KINDS = {'data_create': ('POST',), 'data_update': ('PUT', 'PATCH'), 'data_delete': ('DELETE',)}
_CONTROL = re.compile(r'<(?:form|input|button|select|textarea)\b|createElement\(\s*[\'"`](?:form|input|button|select|textarea)'
                      r'[\'"`]\s*\)', re.I)


def _client_sends(method: str, text: str) -> bool:
    m = method.lower()
    return bool(re.search(r'[\'"`]%s[\'"`]' % method, text, re.I)                       # fetch(u, {method: 'DELETE'})
                or re.search(r'<form\b[^>]*\bmethod\s*=\s*[\'"]?%s' % m, text, re.I)  # <form method="post">
                or re.search(r'(?:axios|\$|http|api|client|request)\.%s\(' % m, text, re.I))


def _server_handles(method: str, server: str) -> bool:
    m = method.lower()
    return bool(re.search(r'def\s+do_%s\b' % method, server)                             # http.server
                or re.search(r'@\w+(?:\.\w+)*\.%s\(' % m, server)                       # @app.post( / @router.delete(
                or re.search(r'methods\s*=\s*[\[(][^\])]*[\'"]%s[\'"]' % method, server, re.I)
                or re.search(r'[\'"]%s[\'"]' % method, server)                             # dispatch on the method name
                or re.search(r'\b(?:app|router|server|r)\.%s\(' % m, server))               # express / hono


def _plan_code(repo: dict[str, str], out: list[Finding], report: ConsistencyReport) -> None:
    try:
        plan = json.loads(repo.get('.omni/project.json') or '{}').get('web_saas_acceptance') or {}
    except (json.JSONDecodeError, AttributeError):
        return                                                    # the syntax/manifest checks report it
    steps = [st for p in (plan.get('personas') or []) for st in ((p or {}).get('steps') or []) if isinstance(st, dict)]
    needed = {}                                                   # kind -> first step of that kind
    for st in steps:
        if st.get('kind') in _UI_KINDS:
            needed.setdefault(st['kind'], st)
    if not needed:
        return
    server = _server_text(repo)
    pages = {p: t for p, t in repo.items() if not _is_test(p) and (
        p.endswith(_CLIENT_SUFFIXES) or (p.endswith('.py') and _PY_HTML.search(t)))}
    if not server.strip() or not pages:
        report.skipped['plan_code'] = 'no server source' if not server.strip() else 'no page source'
        return
    def describe(st):
        return f"{st.get('id')} ({st.get('kind')}: {str(st.get('method', 'GET')).upper()} {st.get('path')})"
    for kind, st in sorted(needed.items()):
        method = str(st.get('method', _UI_KINDS[kind][0])).upper()
        if not _server_handles(method, server):
            out.append(Finding('plan_code', '.omni/project.json', None,
                               f'acceptance step {describe(st)}: the server has no {method} handler',
                               f'handle {method} for {st.get("path")} on the server (e.g. def do_{method}(self) '
                               'with http.server)'))
    ui_text = '\n'.join(pages.values())
    if not _CONTROL.search(ui_text):
        page = next((p for p in sorted(pages) if p.endswith(('.html', '.htm'))), sorted(pages)[0])
        out.append(Finding('plan_code', page, None,
                           'the plan makes users ' + ', '.join(
                               f"{k.split('_', 1)[1]} ({describe(needed[k])})" for k in sorted(needed))
                           + ', but no page contains an interactive control (<form>, <input>, <button>, <select>, '
                           '<textarea>, or createElement of one): there is nothing a user can use to do it',
                           'build the form/buttons on the page served at / and wire them with fetch to the routes the '
                           'plan calls; the page must be the working interface, not a description of it'))
        return
    for kind, st in sorted(needed.items()):
        methods = (str(st.get('method')).upper(),) if st.get('method') else _UI_KINDS[kind]
        if not any(_client_sends(m, ui_text) for m in methods):
            out.append(Finding('plan_code', '.omni/project.json', None,
                               f'acceptance step {describe(st)}: no page code sends {"/".join(methods)}',
                               f'make the page call {st.get("path")} with method {methods[0]} '
                               f"(fetch(url, {{method: '{methods[0]}'}}) or <form method=\"{methods[0].lower()}\">)"))


# ---------------------------------------------------------------- manifest --
def _manifest(repo: dict[str, str], out: list[Finding]) -> None:
    raw = repo.get('.omni/project.json')
    if raw is None:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return  # reported by syntax
    commands = []
    for key in ('build', 'verify'):
        for item in data.get(key) or []:
            argv = item.get('argv') if isinstance(item, dict) else item
            if isinstance(argv, list):
                commands.append(argv)
    for key in ('preview_command', 'start_command', 'preview'):
        v = data.get(key)
        if isinstance(v, dict):
            v = v.get('argv') or v.get('command')
        if isinstance(v, list):
            commands.append(v)
    for argv in commands:
        for arg in argv:
            if not isinstance(arg, str) or arg.startswith('-') or '*' in arg or '://' in arg:
                continue
            target = arg.split('::', 1)[0]
            if re.fullmatch(r'[\w./-]+\.(py|js|mjs|ts|sh)', target) and target not in repo:
                if any(p.startswith(target.rstrip('/') + '/') for p in repo):
                    continue
                out.append(Finding('manifest', '.omni/project.json', None,
                                   f'command {" ".join(map(str, argv))[:120]!r} names {target}, which does not exist',
                                   f'create {target} or point the command at an existing file'))


# ----------------------------------------------------------- accessibility --
_INPUT = re.compile(r'<(input|select|textarea)\b([^>]*)>', re.I)
_ATTR = lambda name: re.compile(r'''\b%s\s*=\s*(['"])(.*?)\1''' % name, re.I | re.S)
_HEBREW = re.compile(r'[֐-׿]')


def _accessibility(repo: dict[str, str], out: list[Finding]) -> None:
    for path, text in sorted(repo.items()):
        if _is_test(path) or not (path.endswith(('.html', '.htm')) or (path.endswith('.py') and '<html' in text.lower())):
            continue
        html = re.search(r'<html\b([^>]*)>', text, re.I)
        if html:
            attrs = html.group(1)
            if not _ATTR('lang').search(attrs):
                out.append(Finding('accessibility', path, _line_of(text, html.start()), '<html> has no lang attribute',
                                   'add lang (e.g. lang="he")', blocking=False))
            if _HEBREW.search(text) and not re.search(r'''dir\s*=\s*['"]rtl['"]''', text, re.I):
                out.append(Finding('accessibility', path, _line_of(text, html.start()), 'Hebrew page without dir="rtl"',
                                   'add dir="rtl" to <html>', blocking=False))
        for m in _INPUT.finditer(text):
            attrs = m.group(2)
            typ = _ATTR('type').search(attrs)
            kind = typ.group(2).lower() if typ else ''
            if kind in ('hidden', 'submit', 'button', 'reset', 'image'):
                continue
            if _ATTR('aria-label').search(attrs) or _ATTR('aria-labelledby').search(attrs) or _ATTR('title').search(attrs):
                continue
            ident = _ATTR('id').search(attrs)
            if ident and re.search(r'''<label\b[^>]*\bfor\s*=\s*['"]%s['"]''' % re.escape(ident.group(2)), text, re.I):
                continue
            before = text[max(0, m.start() - 400):m.start()]
            if before.lower().rfind('<label') > before.lower().rfind('</label'):
                continue  # wrapped in a <label>
            out.append(Finding('accessibility', path, _line_of(text, m.start()),
                               f'<{m.group(1).lower()}> without a label', 'add <label for=...> or aria-label', blocking=False))
        for m in re.finditer(r'<img\b([^>]*)>', text, re.I):
            if not _ATTR('alt').search(m.group(1)):
                out.append(Finding('accessibility', path, _line_of(text, m.start()), '<img> without alt text',
                                   'add alt (empty alt="" for decoration)', blocking=False))


# -------------------------------------------------------------------- API --
CHECKS = ('syntax', 'imports', 'routes', 'static', 'manifest', 'plan_code', 'accessibility')


def scan(repo: dict[str, str]) -> ConsistencyReport:
    report = ConsistencyReport()
    out = report.findings
    _syntax(repo, out); report.checks_run.append('syntax')
    _imports(repo, out); report.checks_run.append('imports')
    _routes(repo, out, report); report.checks_run.append('routes')
    _static(repo, out); report.checks_run.append('static')
    _manifest(repo, out); report.checks_run.append('manifest')
    _plan_code(repo, out, report); report.checks_run.append('plan_code')
    _accessibility(repo, out); report.checks_run.append('accessibility')
    return report


def failures(report: ConsistencyReport) -> tuple:
    from .autonomous_core import AcceptanceFailure
    return tuple(AcceptanceFailure(CONSISTENCY_FAILURE_ID, f'consistency ({f.check}): {f.where()} {f.message}',
                                   f'Fix: {f.fix}. This was found before running the app, by reading the files.')
                 for f in report.blocking[:12])


class ConsistencyGateExecutor:
    """Runs the consistency scan before the wrapped executor; blocking findings
    return a repairable failure without starting the sandbox. The last report
    is kept for build evidence (`last_consistency`)."""

    def __init__(self, inner, *, enabled: bool = True):
        self._inner = inner
        self.enabled = enabled
        self.last_consistency = None
        self.consistency_rounds: list[dict] = []

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        if self.enabled:
            report = scan(repository)
            self.last_consistency = report.to_dict()
            self.consistency_rounds.append({'passed': not report.blocking, 'blocking': len(report.blocking),
                                            'advisories': len(report.advisories)})
            if report.blocking:
                from .autonomous_core import ExecutionReport
                return ExecutionReport(False, failures(report), '')
        return self._inner.execute(repository=repository, spec=spec)

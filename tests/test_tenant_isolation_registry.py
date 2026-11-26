"""S4.5 (the owner's plan v3): the route registry of tenant isolation is derived from the app and compared here.

tests/tenant_isolation_routes.json names every route the served app (app.py: omni_prod.investor_app plus the live_core
router, FastAPI's docs routes and the /ui mount) answers, its kind and the gate that binds an identifier to the caller.
This file needs no database and runs in the general suite; it fails when
  - a route is added or removed without the registry saying so (a new route is never served unclassified);
  - a route takes a parameter the registry does not classify. Every parameter is read -- path, query, header, cookie
    and body, an embedded scalar, the fields of nested models -- and must be one of: an identifier the entry declares
    in "ids"; a path parameter or an id-like name (..._id, ..._ids, ...key, ...token, ...fingerprint) the entry declares
    in "fields" with its reason (any other parameter may be declared there too, such as a paging cursor that is a
    position in the caller's own rows); a free-form object (a dict, Any) the entry declares in "opaque" with its reason; or a
    name in the global "plain_fields" (free text, numbers, choices). A public or account route can take no identifier;
    a "param_map" may rename a parameter only into an identifier;
  - a kind is claimed by a route it does not fit: capability_url only for live_core's preview handles, legacy_ws only
    for the /runtime websockets, a plain Starlette route only for FastAPI's docs, a mount only as static files from the
    repository;
  - an entry's gate is not called by its endpoint. The gate must be a CALL reached from the endpoint (through functions
    of the same module, three calls deep), and for a route with an identifier in its path the chain of calls must carry
    that identifier into the gate. Limits, said: this is static -- it proves that the call exists and receives the id,
    not that it runs before the data is read or that its result is used; tests/test_tenant_isolation_pg.py is the
    behavioural proof;
  - a route that is not public does not check the session itself (the Bearer middleware production_auth runs only with
    OMNI_ENV=production, which Vercel production does not set): no gate may be a middleware;
  - any route takes an object-storage key: objects are reached only through rows the caller owns.
"""
from __future__ import annotations

import ast
import inspect
import json
import re
import textwrap
import types
import typing
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute
from pydantic import BaseModel

import app as served
from omni_prod import investor_app

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'tests' / 'tenant_isolation_routes.json').read_text(encoding='utf-8'))
ROUTES = REGISTRY['routes']
ID_LIKE = re.compile(r'(^|_)(id|ids|key|token|fingerprint)$')
SCOPED = {'tenant', 'admin', 'legacy_refused', 'legacy_ws', 'capability_url'}
SESSION_KINDS = {'tenant', 'account'}
# The session checks of each generation: a route that is not public reaches one of them (or live_core's dependency).
SESSION_CHECKS = {'_v26_bearer', '_v27_bearer', '_v28_bearer', '_signed_in', 'extract_session_token', '_runtime_bearer'}
# Gates that are not a call inside the endpoint: allowed for these kinds only, each checked by its own rule below.
NOT_A_CALL = {'none': {'public'}, 'credentials': {'public'}, 'single-use token': {'public'},
              'legacy_paths_guard': {'legacy_refused'}}
STORAGE_WORDS = re.compile(r'(^|_)(storage_key|artifact_key|object_key|s3_key|bucket|blob)$')


def served_routes() -> dict[str, object]:
    out = {}
    for r in served.app.routes:
        if isinstance(r, APIRoute):
            out.update({f'{m} {r.path}': r for m in sorted(r.methods)})
        elif isinstance(r, APIWebSocketRoute):
            out[f'WS {r.path}'] = r
        elif type(r).__name__ == 'Route':
            out.update({f'{m} {r.path}': r for m in sorted(r.methods)})
        elif type(r).__name__ == 'Mount':
            out[f'MOUNT {r.path}'] = r
        else:  # pragma: no cover - a new kind of route must be classified by a person
            raise AssertionError(f'unknown route type {type(r).__name__} at {getattr(r, "path", "?")}')
    return out


SERVED = served_routes()


def _model_of(annotation):
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if origin in (typing.Union, types.UnionType, list, tuple, set, frozenset):
        return next((m for m in map(_model_of, args) if m is not None), None)
    return None


def _opaque(annotation) -> bool:
    """A free-form object: its keys are not known here, so a person declares what it may carry."""
    origin, args = typing.get_origin(annotation), typing.get_args(annotation)
    if annotation in (dict, typing.Any, object) or origin is dict:
        return True
    if origin in (typing.Union, types.UnionType):
        return any(_opaque(a) for a in args if a is not type(None))
    if origin in (list, tuple, set, frozenset):
        return not args or _opaque(args[0])
    return False


def _fields(prefix: str, model, out: dict, where: str, depth: int = 0) -> None:
    assert depth < 6, f'model nesting deeper than 6 at {prefix}'
    for name, field in model.model_fields.items():
        sub = _model_of(field.annotation)
        if sub is not None:
            _fields(f'{prefix}{name}.', sub, out, where, depth + 1)
        else:
            out[f'{prefix}{name}'] = (where, 'opaque' if _opaque(field.annotation) else 'value')


def parameters(route) -> dict[str, tuple[str, str]]:
    """name -> (where, shape) for every parameter the route reads. Nested model fields are dotted (signals.title);
    shape is 'opaque' for a free-form object. A route without a FastAPI dependant (a plain Starlette route) has its
    path parameters read from its path."""
    out: dict[str, tuple[str, str]] = {}
    dependant = getattr(route, 'dependant', None)
    if dependant is None:
        for name in re.findall(r'\{(\w+)(?::[^}]*)?\}', getattr(route, 'path', '')):
            out[name] = ('path', 'value')
        return out
    out.update({p.name: ('path', 'value') for p in dependant.path_params})
    for where, params in (('query', dependant.query_params), ('header', dependant.header_params),
                          ('cookie', dependant.cookie_params)):
        out.update({p.alias or p.name: (where, 'opaque' if _opaque(p.field_info.annotation) else 'value') for p in params})
    body = dependant.body_params
    for p in body:
        model = _model_of(p.field_info.annotation)
        embedded = getattr(p.field_info, 'embed', False) or len(body) > 1
        if model is not None:
            _fields('' if not embedded else f'{p.alias or p.name}.', model, out, 'body')
        else:
            out[p.alias or p.name] = ('body', 'opaque' if _opaque(p.field_info.annotation) else 'value')
    return out


def canonical(name: str, entry: dict) -> str:
    leaf = name.split('.')[-1]
    return (entry.get('param_map') or {}).get(leaf) or REGISTRY['aliases'].get(leaf, leaf)


def test_the_registry_lists_every_route_the_served_app_answers():
    served, listed = set(SERVED), set(ROUTES)
    assert not served - listed, ('routes the app serves that tests/tenant_isolation_routes.json does not classify: '
                                 f'{sorted(served - listed)}')
    assert not listed - served, f'registry entries for routes the app no longer serves: {sorted(listed - served)}'
    assert all(entry['kind'] in REGISTRY['kinds'] for entry in ROUTES.values())


@pytest.mark.parametrize('key', sorted(SERVED))
def test_every_identifier_a_route_takes_is_declared(key):
    entry, route = ROUTES[key], SERVED[key]
    identifiers, plain = set(REGISTRY['identifiers']), REGISTRY['plain_fields']
    declared, fields, opaque = set(entry.get('ids', [])), entry.get('fields', {}), entry.get('opaque', {})
    unused = set(entry.get('unused', []))
    if unused:                                # a field of a shared request model the endpoint never reads
        assert entry.get('unused_note'), f'{key}: "unused" needs "unused_note"'
        assert not unused & reachable_names(_endpoint(route)), f'{key} reads a field it declares unused: {unused}'
    for target in (entry.get('param_map') or {}).values():
        assert target in identifiers, f'{key}: param_map may rename a parameter only into an identifier, not {target!r}'
    assert all(str(reason).strip() for reason in [*fields.values(), *opaque.values()]), f'{key}: a declaration has no reason'
    taken = set()
    for name, (where, shape) in parameters(route).items():
        if name in unused:
            continue
        leaf, ident = name.split('.')[-1], canonical(name, entry)
        if ident in identifiers:
            taken.add(ident)
            assert entry['kind'] in SCOPED, f'{key} is {entry["kind"]} but takes the identifier {name!r} ({where})'
            assert ident in declared, f'{key}: identifier {name!r} ({where}) is not in the entry\'s "ids"'
        elif shape == 'opaque':
            assert name in opaque, (f'{key}: {name!r} ({where}) is a free-form object; declare what it may carry in the '
                                    f'entry\'s "opaque"')
        elif where == 'path' or ID_LIKE.search(leaf):
            assert name in fields, (f'{key}: {name!r} ({where}) is a path parameter or named like an identifier; declare '
                                    f'it in "ids" or, with its reason, in the entry\'s "fields"')
        else:   # a global plain field, or a per-route declaration with its reason (a cursor that is a position)
            assert leaf in plain or name in fields, (f'{key}: parameter {name!r} ({where}) is not classified: add it to '
                                                     f'"plain_fields" (text, a number, a choice) or declare it on the entry')
    assert declared <= taken, f'{key}: "ids" names {sorted(declared - taken)}, which the route does not take'
    stale = (set(fields) | set(opaque)) - set(parameters(route))
    assert not stale, f'{key}: declarations for parameters the route does not take: {sorted(stale)}'
    assert set(entry.get('child', [])) <= declared, f'{key}: a "child" identifier is not in "ids"'


def test_no_route_takes_an_object_storage_key():
    """Objects (repositories, attachments, generated images, round snapshots) are found through a row the caller owns
    -- never through a key, path or bucket name the caller sends. The one archive path is inside a capability url."""
    for key, route in SERVED.items():
        for name, (where, _shape) in parameters(route).items():
            assert not STORAGE_WORDS.search(name.split('.')[-1]), f'{key} takes {name!r} ({where}): an object key'
            if name.split('.')[-1] == 'path':
                assert ROUTES[key]['kind'] == 'capability_url', f'{key} takes a file path'


@pytest.mark.parametrize('key', sorted(SERVED))
def test_each_kind_is_only_what_it_claims_to_be(key):
    """The kinds that skip the two-account matrix are closed lists, read from the routes themselves."""
    from starlette.staticfiles import StaticFiles
    route = SERVED[key]
    kind, endpoint = ROUTES[key]['kind'], getattr(route, 'endpoint', None)
    module = getattr(endpoint, '__module__', '') or ''
    if key.startswith('MOUNT '):
        assert kind == 'public' and isinstance(route.app, StaticFiles), f'{key}: a mount serves only static files'
        assert ROOT in Path(route.app.directory).resolve().parents, f'{key}: static files from outside the repository'
    elif getattr(route, 'dependant', None) is None:
        assert kind == 'public' and module.startswith('fastapi.'), f'{key}: a plain route is only FastAPI\'s docs'
    if kind == 'capability_url':
        assert module == 'live_core.api' and endpoint.__name__ in ('preview_root', 'preview_asset'), \
            f'{key}: capability_url is only the live_core preview handle (an unguessable link)'
    if kind == 'legacy_ws':
        assert key.startswith('WS /runtime/') and isinstance(route, APIWebSocketRoute), f'{key}: not a legacy websocket'
    if kind in ('public', 'account'):
        assert not ROUTES[key].get('ids'), f'{key}: a {kind} route has no identifier'


# --------------------------------------------------------------------------------------------- gates, from source

@lru_cache(maxsize=None)
def _module_functions(module_name: str) -> dict[str, list[ast.AST]]:
    import importlib
    module = importlib.import_module(module_name)
    tree = ast.parse(inspect.getsource(module))
    out: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(node)
    return out


def _call_name(call: ast.Call) -> str:
    f = call.func
    return f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ''


def _mentions(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(n, ast.Name) and n.id in names for n in ast.walk(node))


def _function_tree(endpoint) -> ast.AST:
    return ast.parse(textwrap.dedent(inspect.getsource(endpoint))).body[0]


def reachable_names(endpoint, depth: int = 3) -> set[str]:
    """Every name, attribute and string the endpoint's body uses, and those of the functions of its own module it
    calls, `depth` calls deep (used for "a field declared unused is never read")."""
    functions = _module_functions(endpoint.__module__)
    seen, frontier, names = set(), [_function_tree(endpoint)], set()
    for _ in range(depth + 1):
        nxt = []
        for node in frontier:
            for n in ast.walk(node):
                if isinstance(n, ast.Name):
                    names.add(n.id)
                elif isinstance(n, ast.Attribute):
                    names.add(n.attr)
                elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                    names.add(n.value)
            for name in names & set(functions) - seen:
                seen.add(name)
                nxt.extend(functions[name])
        frontier = nxt
    return names


def gate_calls(endpoint, carried: set[str] | None = None, depth: int = 3) -> set[str]:
    """The names of the functions CALLED from the endpoint, following calls into functions of its module. With
    `carried`, only calls that receive one of those names in an argument count, and the parameter it lands in is carried
    on into that function: a gate reached this way receives the route's identifier."""
    functions = _module_functions(endpoint.__module__)
    found: set[str] = set()
    frontier = [(_function_tree(endpoint), carried)]
    seen = set()
    for _ in range(depth + 1):
        nxt = []
        for fn, names in frontier:
            for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
                name = _call_name(call)
                args = list(call.args) + [k.value for k in call.keywords]
                if names is not None and not any(_mentions(a, names) for a in args):
                    continue
                found.add(name)
                for target in functions.get(name, ()):
                    if (name, id(target)) in seen:
                        continue
                    seen.add((name, id(target)))
                    if names is None:
                        nxt.append((target, None))
                        continue
                    params = [a.arg for a in target.args.args]
                    landed = {params[i] for i, a in enumerate(call.args) if i < len(params) and _mentions(a, names)}
                    landed |= {k.arg for k in call.keywords if k.arg and _mentions(k.value, names)}
                    if landed:
                        nxt.append((target, landed))
        frontier = nxt
    return found


def _endpoint(route):
    return getattr(route, 'endpoint', None)


@pytest.mark.parametrize('key', sorted(k for k, e in ROUTES.items() if e['gate'] not in NOT_A_CALL))
def test_every_gate_is_called_by_its_endpoint(key):
    entry, route = ROUTES[key], SERVED[key]
    if entry['gate'] == 'require_user':           # live_core: a FastAPI dependency of the endpoint
        deps = {getattr(d.call, '__name__', '') for d in route.dependant.dependencies}
        assert 'require_user' in deps, f'{key}: live_core route without require_user'
        return
    endpoint = _endpoint(route)
    if entry['kind'] == 'admin':                  # the staff key is compared before anything else is read
        assert entry['gate'] in reachable_names(endpoint), f'{key}: the admin key {entry["gate"]} is not read'
        return
    assert entry['gate'] in gate_calls(endpoint), f'{key}: the gate {entry["gate"]!r} is never called by {endpoint.__name__}'
    path_ids = {name for name, (where, _s) in parameters(route).items()
                if where == 'path' and canonical(name, entry) in REGISTRY['identifiers']}
    if entry['kind'] == 'tenant' and path_ids:
        assert entry['gate'] in gate_calls(endpoint, path_ids), \
            f'{key}: the gate {entry["gate"]!r} is called, but no call chain carries {sorted(path_ids)} into it'


@pytest.mark.parametrize('key', sorted(k for k, e in ROUTES.items()))
def test_no_gate_is_a_middleware_or_missing(key):
    entry = ROUTES[key]
    if entry['gate'] in NOT_A_CALL:
        assert entry['kind'] in NOT_A_CALL[entry['gate']], f'{key}: gate {entry["gate"]!r} is not allowed for a {entry["kind"]} route'
    assert entry['gate'] not in ('production_auth', 'legacy_paths_guard') or entry['kind'] == 'legacy_refused', \
        f'{key}: a middleware is not a gate -- production_auth does not run in production (no OMNI_ENV there)'
    if 'anonymous' in entry:                      # an answer to a caller with no session other than its kind's
        assert entry.get('anonymous_note'), f'{key}: "anonymous" needs "anonymous_note" saying why'


@pytest.mark.parametrize('key', sorted(k for k, e in ROUTES.items() if e['kind'] in SESSION_KINDS))
def test_every_route_that_is_not_public_checks_the_session_itself(key):
    route = SERVED[key]
    if isinstance(route, APIRoute) and any(getattr(d.call, '__name__', '') == 'require_user'
                                           for d in route.dependant.dependencies):
        return
    calls = gate_calls(_endpoint(route))
    assert calls & SESSION_CHECKS, f'{key}: no session check is called ({sorted(SESSION_CHECKS)})'


def test_the_legacy_guard_covers_every_route_said_to_be_refused_by_it():
    for key, entry in ROUTES.items():
        if entry['gate'] != 'legacy_paths_guard':
            continue
        path = re.sub(r'\{[^}]+\}', 'x', key.split(' ', 1)[1])
        assert path.startswith(investor_app._LEGACY_PREFIXES) or investor_app._LEGACY_PATCH.match(path), key


LEGACY = sorted(k for k, e in ROUTES.items() if e['kind'] == 'legacy_refused')
_PLACEHOLDER = {'engine': 'godot', 'platform': 'android', 'collection': 'items', 'path': 'index.html'}


def _placeholders(value):
    if isinstance(value, str):
        return re.sub(r'\{(\w+)(?::\w+)?\}', lambda m: _PLACEHOLDER.get(m.group(1), 'ffffffff-0000-4000-8000-000000000000'), value)
    if isinstance(value, list):
        return [_placeholders(v) for v in value]
    if isinstance(value, dict):
        return {k: _placeholders(v) for k, v in value.items()}
    return value


@pytest.mark.parametrize('vercel_env', ('production', 'preview'))
@pytest.mark.parametrize('key', LEGACY)
def test_deployed_but_not_durable_still_refuses_every_legacy_route(key, vercel_env, monkeypatch):
    """A Vercel deployment whose durable backend is incomplete (no OMNI_ENV, memory persistence, no S3 workspace --
    this process) must still refuse the legacy routes: they read and write one in-process store that is not scoped to
    an account. The refusal used to follow the S3 workspace, so a missing S3 variable opened them (review of 0384bbb)."""
    from fastapi.testclient import TestClient
    monkeypatch.delenv('OMNI_ENV', raising=False)
    monkeypatch.setenv('VERCEL_ENV', vercel_env)
    assert not investor_app._async_build_mode(), 'this test needs a deployment without the durable backend'
    entry, (method, template) = ROUTES[key], key.split(' ', 1)
    client = TestClient(served.app, raise_server_exceptions=False)
    got = client.request(method, _placeholders(template), params=_placeholders(entry.get('query')),
                         json=_placeholders(entry.get('body')), headers=_placeholders(entry.get('headers') or {}))
    assert got.status_code == entry['refused'], \
        f'{key} answered {got.status_code} with VERCEL_ENV={vercel_env} and no durable backend, not {entry["refused"]}: {got.text[:200]}'


@pytest.mark.parametrize('vercel_env,refused', ((None, False), ('development', False), ('preview', True),
                                                ('production', True), ('Production ', True), ('staging-x', True)))
def test_the_legacy_refusal_reads_the_vercel_environment_and_fails_closed(vercel_env, refused, monkeypatch):
    """Only local development (VERCEL_ENV unset or 'development') keeps the legacy demo paths; any other value,
    including one nobody expected, refuses them."""
    monkeypatch.delenv('OMNI_ENV', raising=False)
    if vercel_env is None:
        monkeypatch.delenv('VERCEL_ENV', raising=False)
    else:
        monkeypatch.setenv('VERCEL_ENV', vercel_env)
    assert not investor_app._async_build_mode()
    assert investor_app._legacy_refused() is refused


PLATFORM_GATES = {'history', 'export', 'restore', 'rights_status', 'add_rights_evidence', 'verify_rights_evidence',
                  'original_alternative', 'set_project_branding', 'authorize_live_usage'}


@pytest.mark.parametrize('gate', sorted(PLATFORM_GATES))
def test_platform_methods_named_as_gates_bind_the_project_to_the_caller(gate):
    """A route whose gate is a platform method (v26-v28) relies on that method calling self._key, which checks the
    project's owner and derives the owner-bound internal key."""
    used = {e['gate'] for e in ROUTES.values()}
    assert gate in used, f'{gate} is no longer a gate of any route: remove it from PLATFORM_GATES'
    method = getattr(investor_app.V28Platform, gate)
    tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
    calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert '_key' in calls, f'V28Platform.{gate} does not call self._key'


def test_the_internal_key_binds_the_owner():
    """Every v26-v28 store is keyed by the internal key, so it must differ per owner for the same public id."""
    key = investor_app._v28.accounts.internal_project_key
    assert key(owner_id='usr_a', project_id='prj_x') != key(owner_id='usr_b', project_id='prj_x')
    assert key(owner_id='usr_a', project_id='prj_x') == key(owner_id='usr_a', project_id='prj_x')


# ----------------------------------------------------------------- file names cannot leave their tenant's place

ESCAPES = ('../x', '../../tenant_other/index.html', '/etc/passwd', 'a/../../b', 'a\\..\\b', 'nul\x00.txt', '..')


@pytest.mark.parametrize('name', ESCAPES)
def test_a_repository_path_cannot_escape(name, tmp_path):
    """Every repository a customer's change produces passes normalize_repo_path (commit, patch, export, work
    directories); materialize() -- the one writer of sandbox and preview work directories -- checks again and writes
    nothing outside its root."""
    from omni_prod.repository_assets import materialize
    from omni_prod.repository_patch import PatchValidationError, normalize_repo_path
    from omni_prod.workspace import MemoryProjectWorkspace
    with pytest.raises(PatchValidationError):
        normalize_repo_path(name)
    root = tmp_path / 'tenant'
    root.mkdir()
    with pytest.raises(PatchValidationError):
        materialize(root, {'index.html': 'ok', name: 'escaped'})
    assert not any(p.name == 'x' or p.name == 'b' for p in tmp_path.rglob('*') if root not in p.parents)
    with pytest.raises(PatchValidationError):
        MemoryProjectWorkspace().commit(project_id='tenant_a', repository={name: 'escaped'}, message='m')


@pytest.mark.parametrize('segment', ('..', '../tenant_b', 'tenant_a/../tenant_b', '', 'a b', 'x' * 121))
def test_object_key_segments_cannot_escape_their_prefix(segment):
    from omni_prod.artifact_keys import build_artifact_key, build_capability_artifact_key
    with pytest.raises(ValueError):
        build_capability_artifact_key(project_id=segment, build_id='bld_1', requirement_id='r1', filename='a.webp')
    with pytest.raises(ValueError):
        build_artifact_key(project_id='tenant_a', version_id=segment, build_id='bld_1')


def test_a_preview_data_directory_is_named_by_a_digest_of_the_internal_key(tmp_path):
    from omni_prod.preview_runtime import project_data_dir
    paths = {project_data_dir(str(tmp_path), key) for key in ('tenant_a', 'tenant_b', '../../etc', '/abs')}
    assert len(paths) == 4
    assert all(Path(p).parent == tmp_path and re.fullmatch(r'p-[0-9a-f]{32}', Path(p).name) for p in paths)

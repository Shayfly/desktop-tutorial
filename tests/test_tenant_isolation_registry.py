"""S4.5 (the owner's plan v3): the route registry of tenant isolation is derived from the app and compared here.

tests/tenant_isolation_routes.json names every route the served app (app.py: omni_prod.investor_app plus the live_core
router and the /ui mount) answers, its kind and the gate that binds an identifier to the caller. This file needs no
database and runs in the general suite; it fails when
  - a route is added or removed without the registry saying so (a new route is never served unclassified);
  - a route takes an identifier (a path parameter, or a query or body field named like one) that its entry does not
    declare, or a public/account route takes an identifier of another customer;
  - an entry names a gate the endpoint never calls (read from the endpoint's source and the module functions it
    calls), or a platform method named as a gate does not bind the project to the caller (self._key);
  - any route takes an object-storage key: objects are reached only through rows the caller owns.
What each kind means at run time -- two real accounts on PostgreSQL -- is tests/test_tenant_isolation_pg.py.
"""
from __future__ import annotations

import ast
import inspect
import json
import re
import textwrap
from functools import lru_cache
from pathlib import Path

import pytest
from fastapi.routing import APIRoute, APIWebSocketRoute

import app as served
from omni_prod import investor_app

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'tests' / 'tenant_isolation_routes.json').read_text(encoding='utf-8'))
ROUTES = REGISTRY['routes']
ID_LIKE = re.compile(r'(^|_)(id|ids|key|token|fingerprint)$')
SCOPED = {'tenant', 'admin', 'legacy_refused', 'legacy_demo', 'legacy_ws', 'capability_url'}
# Gates that are not a call inside the endpoint, each checked by its own rule below.
NOT_A_CALL = {'none', 'credentials', 'single-use token', 'production_auth', 'legacy_paths_guard'}
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


def parameters(route) -> dict[str, str]:
    """name -> where (path, query, body) for every parameter the route reads."""
    out = {}
    dependant = getattr(route, 'dependant', None)
    if dependant is None:
        return out
    out.update({p.name: 'path' for p in dependant.path_params})
    out.update({p.name: 'query' for p in dependant.query_params})
    for p in dependant.body_params:
        model = getattr(p.field_info, 'annotation', None)
        for field in getattr(model, 'model_fields', {}) or {}:
            out[field] = 'body'
    return out


def canonical(name: str, entry: dict) -> str:
    return (entry.get('param_map') or {}).get(name) or REGISTRY['aliases'].get(name, name)


def test_the_registry_lists_every_route_the_served_app_answers():
    served, listed = set(SERVED), set(ROUTES)
    assert not served - listed, ('routes the app serves that tests/tenant_isolation_routes.json does not classify: '
                                 f'{sorted(served - listed)}')
    assert not listed - served, f'registry entries for routes the app no longer serves: {sorted(listed - served)}'
    assert all(entry['kind'] in REGISTRY['kinds'] for entry in ROUTES.values())


@pytest.mark.parametrize('key', sorted(k for k in SERVED if not k.startswith('MOUNT')))
def test_every_identifier_a_route_takes_is_declared(key):
    entry, route = ROUTES[key], SERVED[key]
    known = set(REGISTRY['identifiers']) | set(REGISTRY['not_identifiers'])
    declared = set(entry.get('ids', []))
    unused = set(entry.get('unused', []))
    if unused:                                # a field of a shared request model the endpoint never reads
        assert entry.get('unused_note'), f'{key}: "unused" needs "unused_note"'
        assert not unused & reachable_names(_endpoint(route)), f'{key} reads a field it declares unused: {unused}'
    taken = set()
    for name, where in parameters(route).items():
        if where != 'path' and not ID_LIKE.search(name):
            continue                          # a prompt, a title, an email: not an identifier
        if name in unused:
            continue
        name = canonical(name, entry)
        assert name in known, (f'{key}: parameter {name!r} ({where}) is neither in "identifiers" nor in '
                               f'"not_identifiers" of tests/tenant_isolation_routes.json')
        if name in REGISTRY['identifiers']:
            taken.add(name)
            assert entry['kind'] in SCOPED, f'{key} is {entry["kind"]} but takes the identifier {name!r} ({where})'
            assert name in declared, f'{key}: identifier {name!r} ({where}) is not in the entry\'s "ids"'
    assert declared <= taken, f'{key}: "ids" names {sorted(declared - taken)}, which the route does not take'
    assert set(entry.get('child', [])) <= declared, f'{key}: a "child" identifier is not in "ids"'


def test_no_route_takes_an_object_storage_key():
    """Objects (repositories, attachments, generated images, round snapshots) are found through a row the caller owns
    -- never through a key, path or bucket name the caller sends. The one archive path is inside a capability url."""
    for key, route in SERVED.items():
        for name, where in parameters(route).items():
            assert not STORAGE_WORDS.search(name), f'{key} takes {name!r} ({where}): an object key from the caller'
            if name == 'path':
                assert ROUTES[key]['kind'] == 'capability_url', f'{key} takes a file path'


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


def _names(node: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.add(n.id)
        elif isinstance(n, ast.Attribute):
            out.add(n.attr)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)
    return out


def reachable_names(endpoint, depth: int = 3) -> set[str]:
    """Every name, attribute and string the endpoint's body uses, and those of the functions of its own module it
    calls, `depth` calls deep."""
    functions = _module_functions(endpoint.__module__)
    tree = ast.parse(textwrap.dedent(inspect.getsource(endpoint)))
    seen, frontier, names = set(), [tree], set()
    for _ in range(depth + 1):
        nxt = []
        for node in frontier:
            found = _names(node)
            names |= found
            for name in found & set(functions) - seen:
                seen.add(name)
                nxt.extend(functions[name])
        frontier = nxt
    return names


def _endpoint(route):
    return getattr(route, 'endpoint', None)


@pytest.mark.parametrize('key', sorted(k for k, e in ROUTES.items() if e['gate'] not in NOT_A_CALL))
def test_every_gate_is_called_by_its_endpoint(key):
    entry, route = ROUTES[key], SERVED[key]
    if entry['gate'] == 'require_user':           # live_core: a FastAPI dependency of the endpoint
        deps = {getattr(d.call, '__name__', '') for d in route.dependant.dependencies}
        assert 'require_user' in deps, f'{key}: live_core route without require_user'
        return
    names = reachable_names(_endpoint(route))
    assert entry['gate'] in names, f'{key}: the gate {entry["gate"]!r} is not reached from {_endpoint(route).__name__}'


def test_the_legacy_guard_covers_every_route_said_to_be_refused_by_it():
    for key, entry in ROUTES.items():
        if entry['gate'] != 'legacy_paths_guard':
            continue
        path = re.sub(r'\{[^}]+\}', 'x', key.split(' ', 1)[1])
        assert path.startswith(investor_app._LEGACY_PREFIXES) or investor_app._LEGACY_PATCH.match(path), key


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

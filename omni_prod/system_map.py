"""The system map of 148AI, derived from the code and the existing registries (the owner's plan v3, S1.5, 2026-11-25).

    python -m omni_prod.system_map --write    # SYSTEM_MAP.json + docs/SYSTEM_MAP.md
    python -m omni_prod.system_map --check    # exit 1 when the committed files differ from what the code gives

Nothing here is a second registry. Every row is read from a source that already exists and is kept current by its own
generator or by the code itself:

  agents          AGENT_OS_REGISTRY.json            (python -m omni_prod.agent_os.audit --write)
  roles, skills   omni_prod.registry_audit           (docs/AGENT_SKILL_STATUS.md; audit({}) as its test runs it)
  models          PROVIDER_MATRIX.json              (python -m omni_prod.intelligence.matrix --write)
  endpoints       the route decorators of every omni_prod module (read as source, so no import of FastAPI is needed)
  tables          CREATE TABLE in infra/postgres/<number>_*.sql; down files in infra/postgres/rollback/
  services        infra/worker-host/docker-compose.yml
  queues          the queue names in omni_prod/queueing.py and omni_prod/intake/reservation_worker.py
  workflows       .github/workflows/*.yml (name, triggers, schedules)
  environment     the variable NAMES the code reads with os.environ / os.getenv (never a value)
  dependencies    which omni_prod package imports which (package level, so an import inside one package does not
                  change the map)
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
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / 'SYSTEM_MAP.json'
MD_OUT = ROOT / 'docs' / 'SYSTEM_MAP.md'
SCHEMA = 'system-map/1'

PLAN_STATES = ('NOT_IMPLEMENTED', 'PARTIAL', 'IMPLEMENTED', 'CONNECTED', 'VERIFIED', 'LIVE')

# One mapping from every status word a source uses to the plan's six. Proposed in plan v3 (S1.5) and approved by the
# owner before merge; the words the plan's table does not name are listed in MAPPING_DECISIONS with the reason.
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
    # intelligence (PROVIDER_MATRIX.json): verification_state / connection_state
    'REAL_EXECUTION_VERIFIED': 'VERIFIED',
    'CONNECTION_TESTED': 'CONNECTED',
}
MAPPING_DECISIONS = (
    ('STALE -> IMPLEMENTED', 'it was verified once and its code changed since, so the evidence no longer covers it'),
    ('TESTED, UNIT_TESTED, INTEGRATION_TESTED -> IMPLEMENTED', 'a test is not an execution check on a real server'),
    ('BLOCKED -> PARTIAL, or NOT_IMPLEMENTED when no code is named', 'code exists but a named dependency stops it'),
    ('a gap or missing contract fields turn IMPLEMENTED or CONNECTED into PARTIAL', 'the plan: PARTIAL follows the '
     "component's gap list"),
    ('LIVE in a source -> VERIFIED here', 'LIVE needs evidence on the deployed SHA younger than 7 days, which the '
     'repository does not hold'),
    ('CREDENTIAL_PRESENT alone is not CONNECTED', 'a key that was never used to call the provider proves no connection'),
)
LIVE_RULE = ('LIVE is never derived here: it needs evidence younger than 7 days on the SHA that is deployed, and that '
             'evidence is in GitHub Actions runs and Vercel deployments, not in the repository.')


def plan_state(word: str, *, gaps: bool = False, has_code: bool = True) -> str:
    """The plan's state for a source's status word. An unknown word raises: a person classifies a new status."""
    if word not in PLAN_STATE:
        raise ValueError(f'system_map: no plan state for the status {word!r}; add it to PLAN_STATE with its reason')
    state = PLAN_STATE[word]
    if word == 'BLOCKED' and not has_code:
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


def roles() -> list[dict]:
    from . import registry_audit as ra
    rows = []
    for r in ra.audit({}):
        gap = '' if r.gap in ('—', 'not implemented') else r.gap
        rows.append({'key': r.role.key, 'source_status': r.lifecycle,
                     'state': plan_state(r.lifecycle, gaps=bool(gap), has_code=r.implementation not in ('—', '')),
                     'location': r.implementation, 'gaps': [gap] if gap else []})
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


def models() -> list[dict]:
    rows = []
    for m in _json('PROVIDER_MATRIX.json')['models']:
        if m['verification_state'] == 'REAL_EXECUTION_VERIFIED':
            word = 'REAL_EXECUTION_VERIFIED'
        elif m['connection_state'] == 'CONNECTION_TESTED':
            word = 'CONNECTION_TESTED'
        else:
            word = m['implementation_status']
        rows.append({'key': m['model_key'], 'provider': m['provider_key'], 'model_id': m['provider_model_id'],
                     'source_status': word, 'state': plan_state(word, has_code=bool(m.get('adapter_implementation_path'))),
                     'availability': m['availability'], 'tasks': list(m.get('eligible_tasks') or ()),
                     'location': m.get('adapter_implementation_path') or None,
                     'verified_at': m.get('last_verified_at') or None})
    return sorted(rows, key=lambda r: r['key'])


# ---- the inventory -----------------------------------------------------------------------------------------------
_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'websocket', 'api_route'}


def endpoints() -> list[dict]:
    rows = []
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for d in node.decorator_list:
                if (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in _METHODS
                        and d.args and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str)
                        and d.args[0].value.startswith('/')):
                    # no line number: a committed map that moved with every edit above a route would make every
                    # pull request touching that file regenerate it
                    rows.append({'method': d.func.attr.upper(), 'path': d.args[0].value, 'handler': node.name,
                                 'file': _rel(path)})
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


def queues() -> list[dict]:
    rows = []
    for rel in ('omni_prod/queueing.py', 'omni_prod/intake/reservation_worker.py'):
        text = (ROOT / rel).read_text(encoding='utf-8')
        for m in sorted(set(re.findall(r"""['"](omni-[a-z0-9-]+)""", text))):
            rows.append({'name': m, 'defined_in': rel})
    return rows


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


_ENV = re.compile(r"""(?:os\.environ\.get|os\.getenv|os\.environ\.setdefault|environ\.get)\(\s*['"]([A-Z][A-Z0-9_]{2,})['"]"""
                  r"""|os\.environ\[\s*['"]([A-Z][A-Z0-9_]{2,})['"]\s*\]""")


def environment() -> list[dict]:
    names: dict[str, set] = {}
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        for a, b in _ENV.findall(path.read_text(encoding='utf-8')):
            names.setdefault(a or b, set()).add(_rel(path))
    return [{'name': k, 'read_in': sorted(v)} for k, v in sorted(names.items())]


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


def dependencies() -> list[dict]:
    edges: dict[str, set] = {}
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        module = '.'.join(path.relative_to(ROOT).with_suffix('').parts)
        here = _package(module)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
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
    a, r, s, m = agents(), roles(), skills(), models()
    db = database()
    inventory = {'endpoints': endpoints(), 'database': db, 'services': services(), 'queues': queues(),
                 'workflows': workflows(), 'environment': environment(), 'dependencies': dependencies()}
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
            'queues': len(inventory['queues']), 'workflows': len(inventory['workflows']),
            'environment_names': len(inventory['environment']),
        },
        'agents': a, 'roles': r, 'skills': s, 'models': m,
        **inventory,
        'limitations': limitations(),
    }


def _md_counts(title: str, counts: dict) -> str:
    return f'| {title} | ' + ' | '.join(str(counts[s]) for s in PLAN_STATES) + f' | {sum(counts.values())} |'


def render(m: dict) -> tuple[str, str]:
    js = json.dumps(m, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    s = m['summary']
    out = ['# System map', '',
           'Generated by `python -m omni_prod.system_map --write` from the code and the existing registries '
           '(the owner\'s plan v3, S1.5). Do not edit by hand: `tests/test_system_map.py` fails when this file differs '
           'from what the code gives.', '',
           '## States', '',
           '| | ' + ' | '.join(PLAN_STATES) + ' | total |', '|---|' + '---|' * (len(PLAN_STATES) + 1),
           _md_counts('agents (AGENT_OS_REGISTRY)', s['agents']), _md_counts('roles (registry_audit)', s['roles']),
           _md_counts('skills (skill catalog + runtime)', s['skills']), _md_counts('models (PROVIDER_MATRIX)', s['models']),
           '', m['live_rule'], '',
           '### How a source word becomes a state', '',
           '| Source word | State |', '|---|---|']
    out += [f'| {k} | {v} |' for k, v in m['mapping'].items()]
    out += ['', 'Rules beyond the table (to be approved by the owner with this map):', '']
    out += [f'- {d["rule"]}: {d["why"]}.' for d in m['mapping_decisions']]
    out += ['', '## Inventory', '',
            f'- Endpoints: {s["endpoints"]} (route decorators in omni_prod).',
            f'- Database: {s["migrations"]} migrations (highest {m["database"]["highest"]}), {s["tables"]} tables, '
            f'{s["rollback_files"]} rollback files ({", ".join(m["database"]["rollback_files"]) or "none"}).',
            f'- Worker host services: {", ".join(x["name"] for x in m["services"])}.',
            f'- Queues: {", ".join(q["name"] for q in m["queues"])}.',
            f'- Workflows: {s["workflows"]}; scheduled: '
            + ', '.join(f'{w["file"]} ({"; ".join(w["schedules"])})' for w in m['workflows'] if w['schedules']) + '.',
            f'- Environment variable names read by the code: {s["environment_names"]} (names only, never values).',
            '', '## Package dependencies', '', '| Package | Imports |', '|---|---|']
    out += [f'| {d["package"]} | {", ".join(d["imports"])} |' for d in m['dependencies']]
    lim = m['limitations']
    out += ['', '## Known limitations (from the registries)', '',
            f'- Customer-visible findings (TRUTH_MATRIX): {len(lim["customer_visible_findings"])}.',
            f'- Capability gaps (PROVIDER_MATRIX): {len(lim["capability_gaps"])}.',
            f'- Legacy routes (PROVIDER_MATRIX): {len(lim["legacy_routes"])}.', '',
            'The full rows (agents, roles, skills, models, endpoints, tables, workflows, environment names) are in '
            '`SYSTEM_MAP.json`.']
    return js, '\n'.join(out) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='148AI system map')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args(argv)
    js, md = render(build())
    if args.write:
        JSON_OUT.write_text(js, encoding='utf-8')
        MD_OUT.write_text(md, encoding='utf-8')
        print(f'wrote {_rel(JSON_OUT)} and {_rel(MD_OUT)}')
        return 0
    if args.check:
        stale = [p for p, t in ((JSON_OUT, js), (MD_OUT, md)) if not p.exists() or p.read_text(encoding='utf-8') != t]
        for p in stale:
            print(f'::error title=system map::{_rel(p)} is stale: python -m omni_prod.system_map --write')
        return 1 if stale else 0
    sys.stdout.write(md)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

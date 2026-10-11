"""Read-only, redacted evidence export of ONE build (founder directive 2026-10-11, failed build "חגית").

    python -m omni_prod.evidence_export bld_<hex> [--out file.json]

Run on the worker host (``docker compose run --rm --no-deps -T worker python -m omni_prod.evidence_export <id>``),
it opens a READ ONLY transaction, writes nothing, calls no model and prints no secret (known secret shapes are
redacted; flags are shown only from an allow-list of non-secret names). It gathers what the root-cause analysis
needs: the approved brief revision/fingerprint, the approved contract (+ the acceptance scope computed from it),
the product-spec acceptance ids, the acceptance plan outcome of every repair round, stop reason, model usage and
spend, runtime commit, schema versions and active flags.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

NON_SECRET_FLAGS = (
    'OMNI_ENV', 'OMNI_PLAN_DRIVEN', 'OMNI_INTAKE_VIA_WORKER', 'OMNI_PREVIEW_INSPECTOR', 'OMNI_VISUAL_QA',
    'OMNI_VISUAL_QA_ENFORCE', 'OMNI_ZERO_COST_MODE', 'OMNI_MIN_QUALITY_SCORE', 'OMNI_SOURCE_COMMIT',
    'OMNI_CREATOR_PERSISTENCE', 'OMNI_EXTERNAL_CALLS_PER_BUILD', 'OMNI_EXTERNAL_BUDGET_USD', 'OMNI_WORKER_TTL_SECONDS',
)


def redact(text: str) -> str:
    text = re.sub(r'AIza[0-9A-Za-z_-]{20,}', '[redacted-google-key]', text)
    text = re.sub(r'(rediss?|postgres(?:ql)?)://\S+', r'\1://[redacted]', text)
    text = re.sub(r'(?i)(key|token|secret|password|authorization)(["\' :=]+)[^\s"\',]+', r'\1\2[redacted]', text)
    return re.sub(r'[A-Za-z0-9+/_-]{48,}', '[redacted-long-value]', text)


def _clean(value: Any, limit: int = 1500) -> Any:
    if isinstance(value, str):
        return redact(value)[:limit]
    if isinstance(value, dict):
        return {str(k): _clean(v, limit) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v, limit) for v in value[:60]]
    return value


def _json(value: Any) -> Any:
    return value if isinstance(value, (dict, list)) else json.loads(value or '{}')


def runtime(env: dict[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    return {'source_commit': env.get('OMNI_SOURCE_COMMIT'),
            'flags': {k: env.get(k) for k in NON_SECRET_FLAGS if k != 'OMNI_SOURCE_COMMIT'},
            'flags_unset': [k for k in NON_SECRET_FLAGS if not env.get(k)]}


def summarise_rounds(behavior: dict | None) -> list[dict]:
    """Per repair round: which checks failed and what stayed uncovered, to see stagnation."""
    out = []
    for i, r in enumerate((behavior or {}).get('rounds') or []):
        r = r or {}
        checks = r.get('checks') or []
        out.append({'round': i, 'status': r.get('status'), 'summary': r.get('summary'),
                    'failed_steps': sorted({f"{c.get('step_id')}:{c.get('kind')}" for c in checks if not c.get('passed')}),
                    'missing_acceptance_ids': r.get('missing_acceptance_ids'), 'missing_kinds': r.get('missing_kinds'),
                    'not_required_kinds': r.get('not_required_kinds'), 'covered_kinds': r.get('covered_kinds')})
    return out


def export(conn, build_id: str, env: dict[str, str] | None = None) -> dict:
    from .web_saas_acceptance import acceptance_scope
    conn.execute('SET TRANSACTION READ ONLY')
    row = conn.execute(
        'SELECT id, project_id, status, phase, error_code, error_message, repair_rounds, version_id, created_at, finished_at, '
        'actual_provider_cost_usd, estimated_provider_cost_usd, evidence_json FROM build_jobs WHERE id = %s', (build_id,)).fetchone()
    if not row:
        raise SystemExit('build not found')
    (bid, project_id, status, phase, code, message, rounds, version_id, created, finished, actual, estimated, ev) = row
    ev = _json(ev)
    out: dict[str, Any] = {
        'build': {'id': bid, 'project_id': project_id, 'status': status, 'phase': phase, 'error_code': code,
                  'error_message': _clean(message or ''), 'repair_rounds': rounds, 'version_id': version_id,
                  'created_at': str(created), 'finished_at': str(finished)},
        'spend': {'actual_provider_cost_usd': str(actual), 'estimated_provider_cost_usd': str(estimated),
                  'evidence_provider_spend_usd': ev.get('provider_spend_usd'), 'basis': ev.get('provider_spend_basis'),
                  'external_model_calls': ev.get('external_model_calls'),
                  'model_routes': _clean([{k: e.get(k) for k in ('model', 'ok', 'elapsed_ms', 'max_estimated_cost_usd', 'error')}
                                         for e in (ev.get('model_route_events') or []) if isinstance(e, dict)][-30:])},
        'repair': {'rounds': ev.get('repair_rounds'), 'stop_reason': ev.get('repair_stop_reason'),
                   'release_ready': ev.get('release_ready'), 'snapshots': _clean(ev.get('repair_snapshots') or ev.get('round_snapshots'))},
        'evidence_keys': sorted(ev),
        'runtime': runtime(env),
    }
    beh = ev.get('behavior_acceptance') or (ev.get('gates') or {}).get('behavior_acceptance')
    out['behavior_acceptance'] = {'last': _clean((beh or {}).get('last'), 900), 'per_round': _clean(summarise_rounds(beh))}
    out['verification_failures'] = _clean(((ev.get('gates') or {}).get('verification') or ev.get('verification') or {}).get('failures'), 900)
    out['approved_acceptance'] = _clean(ev.get('approved_acceptance'))
    appr = conn.execute(
        'SELECT id, brief_revision, brief_fingerprint, build_contract_id, contract_fingerprint, status, created_at '
        'FROM build_approvals WHERE used_by_build_id = %s OR (project_id = %s AND used_by_build_id IS NULL) '
        'ORDER BY created_at DESC LIMIT 3', (bid, project_id)).fetchall()
    out['approvals'] = [dict(zip(('id', 'brief_revision', 'brief_fingerprint', 'build_contract_id', 'contract_fingerprint', 'status', 'created_at'),
                                 map(str, a))) for a in appr]
    briefs = conn.execute('SELECT revision, fingerprint, complete, created_at FROM project_briefs WHERE project_id = %s ORDER BY revision',
                          (project_id,)).fetchall()
    out['brief_revisions'] = [dict(zip(('revision', 'fingerprint', 'complete', 'created_at'), map(str, b))) for b in briefs]
    used = next((a for a in appr if a[2]), None)
    if used:
        b = conn.execute('SELECT brief_json FROM project_briefs WHERE project_id = %s AND revision = %s', (project_id, used[1])).fetchone()
        if b:
            bj = _json(b[0])
            out['approved_brief'] = {'prompt': _clean(bj.get('prompt'), 2000),
                                     'fields': {k: {'value': _clean(f.get('value'), 600), 'source': f.get('source')}
                                                for k, f in (bj.get('fields') or {}).items()}}
        c = conn.execute('SELECT contract_json, contract_fingerprint FROM m5_build_contracts WHERE id = %s AND project_id = %s',
                         (used[3], project_id)).fetchone()
        if c:
            cj = _json(c[0])
            required, waived = acceptance_scope(cj)
            out['approved_contract'] = {
                'fingerprint': c[1], 'defaults_applied': cj.get('defaults_applied'), 'user_roles': cj.get('user_roles'),
                'required_integrations': cj.get('required_integrations'),
                'infrastructure_kinds': [i.get('kind') for i in cj.get('infrastructure') or []],
                'prompt_tail': _clean((cj.get('prompt') or '')[-1200:], 1200),
                'contract_acceptance': _clean(cj.get('acceptance'), 400),
                'acceptance_scope_now': {'required': list(required), 'not_required': list(waived)}}
    if version_id:
        s = conn.execute('SELECT spec_json FROM project_version_specs WHERE version_id = %s', (version_id,)).fetchone()
        if s:
            out['product_spec_acceptance'] = _clean([{'id': a.get('id'), 'requirement_id': a.get('requirement_id'), 'text': a.get('text')}
                                                     for a in _json(s[0]).get('acceptance', [])], 500)
    out['schema_versions'] = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()]
    return out


def main(argv: list[str]) -> int:
    import psycopg
    args = [a for a in argv if not a.startswith('--')]
    if not args or not re.fullmatch(r'bld_[0-9a-f]+', args[0]):
        print('usage: python -m omni_prod.evidence_export bld_<hex> [--out file.json]', file=sys.stderr)
        return 2
    with psycopg.connect(os.environ['OMNI_DATABASE_URL'], connect_timeout=10) as conn:
        data = export(conn, args[0])
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if '--out' in argv:
        with open(argv[argv.index('--out') + 1], 'w', encoding='utf-8') as fh:
            fh.write(text)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

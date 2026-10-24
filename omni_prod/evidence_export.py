"""Read-only, redacted evidence export of ONE build (founder directive 2026-10-11, failed build "חגית").

    python -m omni_prod.evidence_export bld_<hex> [--out file.json] [--files-dir DIR]

ONE-OFF, with NO merge and NO worker deployment: the deployed image already contains psycopg and omni_prod, so the file
itself can be piped in from a checkout of this branch on the worker host:

    docker compose run --rm --no-deps -T worker python - bld_<hex> < omni_prod/evidence_export.py

It opens a READ ONLY transaction, writes nothing, calls no model and prints no secret (known secret shapes are
redacted; flags come from an allow-list of non-secret names). It reports the approved brief revision/fingerprint and
contract ONLY from an approval linked to exactly this build (a missing or ambiguous link is reported, never replaced by
another approval), the product-spec acceptance ids, the acceptance outcome of every repair round, stop reason, model
usage and spend, runtime commit, schema versions and flags. It also exports the generated files of the build (manifest
`.omni/project.json`, file list with sizes and sha256, redacted text of the source files) read from the stored artifact
with one S3 GET per build; `--files-dir DIR` additionally extracts the artifact UNREDACTED into DIR for offline
reproduction (keep that directory private: generated code is not configuration but could contain secret-like text).
The failed checks of every repair round are listed with their evidence (HTTP status, response excerpts) and the
acceptance ids each check covers; the cost comes from the build row and its credit reservation.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import PurePosixPath
from typing import Any

NON_SECRET_FLAGS = (
    'OMNI_ENV', 'OMNI_PLAN_DRIVEN', 'OMNI_INTAKE_VIA_WORKER', 'OMNI_PREVIEW_INSPECTOR', 'OMNI_VISUAL_QA',
    'OMNI_VISUAL_QA_ENFORCE', 'OMNI_ZERO_COST_MODE', 'OMNI_MIN_QUALITY_SCORE', 'OMNI_SOURCE_COMMIT',
    'OMNI_CREATOR_PERSISTENCE', 'OMNI_EXTERNAL_CALLS_PER_BUILD', 'OMNI_EXTERNAL_BUDGET_USD', 'OMNI_WORKER_TTL_SECONDS',
)


def redact(text: str) -> str:
    # C27: this file must run on its own (python - < evidence_export.py, no package import), so it cannot call
    # omni_prod.secret_redaction; it covers at least the same secret shapes, and
    # tests/test_redaction_single_layer.py::...parity fails if the two drift apart.
    text = re.sub(r'AIza[0-9A-Za-z_-]{20,}', '[redacted-google-key]', text)
    text = re.sub(r'\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|\br8_[A-Za-z0-9]{20,}\b'
                  r'|\b(?:sk|pk|rk)-[A-Za-z0-9_-]{12,}\b', '[redacted-token]', text)
    text = re.sub(r'(?i)\b([a-z][a-z0-9+.-]*://)[^/\s:@]*:[^@\s/]+@', r'\1[redacted]@', text)
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


TEXT_SUFFIXES = ('.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.md', '.txt', '.sql', '.yml', '.yaml', '.toml',
                 '.cfg', '.ini', '.sh', '.svg', '.env.example')


def failed_checks(behavior: dict | None) -> list[dict]:
    """Every failed check of every round with its evidence and the acceptance ids it was meant to cover."""
    out = []
    for i, r in enumerate((behavior or {}).get('rounds') or []):
        for c in (r or {}).get('checks') or []:
            if not c.get('passed'):
                out.append({'round': i, **_clean(c, 700)})
    return out[:80]


def files_section(zip_bytes: bytes, files_dir: str | None = None, total_budget: int = 240_000, per_file: int = 24_000) -> dict:
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = sorted(n for n in z.namelist() if not n.endswith('/'))
    manifest = None
    if '.omni/project.json' in names:
        try:
            manifest = _json(z.read('.omni/project.json').decode('utf-8', 'replace'))
        except Exception:
            manifest = 'UNPARSEABLE: ' + redact(z.read('.omni/project.json').decode('utf-8', 'replace'))[:1500]
    listing, texts, used = [], {}, 0
    for n in names:
        data = z.read(n)
        listing.append({'path': n, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        if n.lower().endswith(TEXT_SUFFIXES) and used < total_budget:
            txt = redact(data.decode('utf-8', 'replace'))
            texts[n] = txt[:per_file] + (f'\n... [truncated, {len(txt)} characters]' if len(txt) > per_file else '')
            used += len(texts[n])
    out = {'manifest': manifest, 'files': listing, 'file_texts_redacted': texts,
           'texts_omitted': [f['path'] for f in listing if f['path'] not in texts]}
    if files_dir:
        root = os.path.realpath(files_dir)
        os.makedirs(root, exist_ok=True)
        for n in names:
            if PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts:
                continue                                         # never write outside the target directory
            dst = os.path.realpath(os.path.join(root, n))
            if not dst.startswith(root + os.sep):
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as fh:
                fh.write(z.read(n))
        out['extracted_to'] = root
    return out


def _default_store(env):
    keys = ('OMNI_S3_ENDPOINT', 'OMNI_S3_BUCKET', 'OMNI_S3_ACCESS_KEY', 'OMNI_S3_SECRET_KEY')
    if not all(env.get(k) for k in keys):
        return None
    from omni_prod.storage import S3ArtifactStore
    return S3ArtifactStore(endpoint=env['OMNI_S3_ENDPOINT'], bucket=env['OMNI_S3_BUCKET'],
                           access_key=env['OMNI_S3_ACCESS_KEY'], secret_key=env['OMNI_S3_SECRET_KEY'])


def export(conn, build_id: str, env: dict[str, str] | None = None, store: Any = None, files_dir: str | None = None) -> dict:
    try:
        from omni_prod.web_saas_acceptance import acceptance_scope  # the code deployed on this host
    except Exception:  # pragma: no cover - stdin use on an older image
        acceptance_scope = None
    conn.execute('SET TRANSACTION READ ONLY')
    row = conn.execute(
        'SELECT id, project_id, status, phase, error_code, error_message, repair_rounds, version_id, created_at, finished_at, '
        'actual_provider_cost_usd, estimated_provider_cost_usd, evidence_json, artifact_key FROM build_jobs WHERE id = %s', (build_id,)).fetchone()
    if not row:
        raise SystemExit('build not found')
    (bid, project_id, status, phase, code, message, rounds, version_id, created, finished, actual, estimated, ev, artifact_key) = row
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
    out['behavior_failed_checks'] = failed_checks(beh)
    out['verification_failures'] = _clean(((ev.get('gates') or {}).get('verification') or ev.get('verification') or {}).get('failures'), 900)
    res = conn.execute('SELECT status, credits_reserved, estimated_provider_cost_usd, actual_provider_cost_usd, '
                       'settled_provider_cost_usd, resolved_at FROM credit_reservations WHERE build_id = %s', (bid,)).fetchone()
    out['spend']['credit_reservation'] = (dict(zip(('status', 'credits_reserved', 'estimated_usd', 'actual_usd', 'settled_usd', 'resolved_at'),
                                                   map(str, res))) if res else 'MISSING: no credit reservation row for this build')
    out['approved_acceptance'] = _clean(ev.get('approved_acceptance'))
    # ONLY an approval whose used_by_build_id is exactly this build counts. No fallback to "the project's latest
    # approval": a different approval would describe a different brief/contract and mislead the analysis.
    appr = conn.execute(
        'SELECT id, brief_revision, brief_fingerprint, build_contract_id, contract_fingerprint, status, created_at '
        'FROM build_approvals WHERE used_by_build_id = %s AND project_id = %s ORDER BY created_at DESC', (bid, project_id)).fetchall()
    keys = ('id', 'brief_revision', 'brief_fingerprint', 'build_contract_id', 'contract_fingerprint', 'status', 'created_at')
    out['approvals'] = [dict(zip(keys, map(str, a))) for a in appr]
    other = conn.execute('SELECT id, used_by_build_id, status, created_at FROM build_approvals WHERE project_id = %s '
                         'AND (used_by_build_id IS DISTINCT FROM %s) ORDER BY created_at DESC LIMIT 5', (project_id, bid)).fetchall()
    out['other_project_approvals_not_used'] = [dict(zip(('id', 'used_by_build_id', 'status', 'created_at'), map(str, o))) for o in other]
    briefs = conn.execute('SELECT revision, fingerprint, complete, created_at FROM project_briefs WHERE project_id = %s ORDER BY revision',
                          (project_id,)).fetchall()
    out['brief_revisions'] = [dict(zip(('revision', 'fingerprint', 'complete', 'created_at'), map(str, b))) for b in briefs]
    if len(appr) != 1:
        out['approval_status'] = ('MISSING: no approval is linked to this build (used_by_build_id); the approved brief and contract '
                                  'are NOT reported, and no other approval was substituted' if not appr else
                                  f'AMBIGUOUS: {len(appr)} approvals are linked to this build; none was chosen')
    else:
        used = appr[0]
        out['approval_status'] = 'EXACT'
        b = conn.execute('SELECT brief_json FROM project_briefs WHERE project_id = %s AND revision = %s AND fingerprint = %s',
                         (project_id, used[1], used[2])).fetchone()
        if b:
            bj = _json(b[0])
            out['approved_brief'] = {'prompt': _clean(bj.get('prompt'), 2000),
                                     'fields': {k: {'value': _clean(f.get('value'), 600), 'source': f.get('source')}
                                                for k, f in (bj.get('fields') or {}).items()}}
        else:
            out['approved_brief'] = 'MISSING: no brief row matches the approval revision and fingerprint'
        c = conn.execute('SELECT contract_json, contract_fingerprint FROM m5_build_contracts WHERE id = %s AND project_id = %s '
                         'AND contract_fingerprint = %s', (used[3], project_id, used[4])).fetchone()
        if c:
            cj = _json(c[0])
            scope = None
            if acceptance_scope is not None:
                required, waived = acceptance_scope(cj)
                scope = {'required': list(required), 'not_required': list(waived)}
            out['approved_contract'] = {
                'fingerprint': c[1], 'defaults_applied': cj.get('defaults_applied'), 'user_roles': cj.get('user_roles'),
                'required_integrations': cj.get('required_integrations'),
                'infrastructure_kinds': [i.get('kind') for i in cj.get('infrastructure') or []],
                'prompt_tail': _clean((cj.get('prompt') or '')[-1200:], 1200),
                'contract_acceptance': _clean(cj.get('acceptance'), 400),
                'acceptance_scope_by_deployed_code': scope}
        else:
            out['approved_contract'] = 'MISSING: no contract row matches the approval contract id and fingerprint'
    if version_id:
        s = conn.execute('SELECT spec_json FROM project_version_specs WHERE version_id = %s', (version_id,)).fetchone()
        if s:
            out['product_spec_acceptance'] = _clean([{'id': a.get('id'), 'requirement_id': a.get('requirement_id'), 'text': a.get('text')}
                                                     for a in _json(s[0]).get('acceptance', [])], 500)
    key = artifact_key
    if not key and version_id:
        v = conn.execute('SELECT artifact_key FROM project_versions WHERE id = %s', (version_id,)).fetchone()
        key = v[0] if v else None
    env_ = os.environ if env is None else env
    if not key:
        out['generated_files'] = ('MISSING: neither the build nor its version has a stored artifact (artifact_key empty), so the '
                                  'generated files cannot be exported; only the evidence above exists')
    else:
        store = store or _default_store(env_)
        if store is None:
            out['generated_files'] = ('MISSING: OMNI_S3_ENDPOINT/BUCKET/ACCESS_KEY/SECRET_KEY are not set where this runs; run it '
                                      'on the worker host (its .env has them) to export the files of artifact ' + redact(str(key)))
        else:
            try:
                out['generated_files'] = files_section(store.get_bytes(key, verify=False), files_dir)
                out['generated_files']['artifact_key'] = key
            except Exception as exc:
                out['generated_files'] = f'MISSING: the artifact could not be read ({type(exc).__name__})'
    out['schema_versions'] = [r[0] for r in conn.execute('SELECT version FROM schema_migrations ORDER BY version').fetchall()]
    return out


def main(argv: list[str]) -> int:
    import psycopg
    skip = {argv[i + 1] for i, a in enumerate(argv[:-1]) if a in ('--out', '--files-dir')}
    args = [a for a in argv if not a.startswith('--') and a not in skip]
    if not args or not re.fullmatch(r'bld_[0-9a-f]+', args[0]):
        print('usage: python -m omni_prod.evidence_export bld_<hex> [--out file.json]', file=sys.stderr)
        return 2
    with psycopg.connect(os.environ['OMNI_DATABASE_URL'], connect_timeout=10) as conn:
        data = export(conn, args[0], files_dir=argv[argv.index('--files-dir') + 1] if '--files-dir' in argv else None)
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if '--out' in argv:
        with open(argv[argv.index('--out') + 1], 'w', encoding='utf-8') as fh:
            fh.write(text)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

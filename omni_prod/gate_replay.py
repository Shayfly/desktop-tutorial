"""Replay deterministic gates over every stored real product version (read-only).

    python -m omni_prod.gate_replay

For each version in project_versions: load the repository from object storage
(checksum-verified), then
  * run the consistency gate and count blocking findings / advisories
    -- a blocking finding on a version that worked is a false positive and
       must be fixed before the gate is enabled;
  * measure what a repair prompt would contain (repo_summary): source files
    and characters with content vs. without, whether the entry point is in.
Prints one JSON summary line (no repository contents, no customer data).
"""
from __future__ import annotations

import json
import sys
from collections import Counter

from .consistency_gate import scan
from .modifier_engine import repo_summary


_CODE = ('.py', '.js', '.mjs', '.ts', '.tsx', '.jsx', '.html', '.css', '.sql', '.vue', '.svelte', '.json')
_NOT_CODE = ('.148ai/', 'rights/', 'docs/', 'node_modules/', 'dist/', 'build/')


def coverage(repo: dict[str, str]) -> dict:
    """Code a repair prompt shows in full. Rights/provenance metadata and docs
    are excluded from the prompt on purpose and are not counted as code."""
    summary = repo_summary(repo)
    src = [f for f in summary['files'] if f['path'].lower().endswith(_CODE) and not f['path'].startswith(_NOT_CODE)
           and f['path'] not in ('package-lock.json',)]
    with_content = [f for f in src if 'content' in f]
    entry = [p for p in repo if '/' not in p and p in ('app.py', 'main.py', 'server.py', 'index.js', 'server.js', 'app.js')]
    return {
        'source_files': len(src), 'source_files_with_content': len(with_content),
        'source_chars': sum(f['chars'] for f in src), 'source_chars_with_content': sum(f['chars'] for f in with_content),
        'largest_file_chars': max((f['chars'] for f in src), default=0),
        'entry_present': bool(entry), 'entry_in_prompt': all(any(f['path'] == e and 'content' in f for f in src) for e in entry),
        'omitted': sorted(f['path'] for f in src if 'content' not in f)[:8],
    }


def replay(rows, load) -> dict:
    out = {'versions': 0, 'load_failures': 0, 'blocking_versions': 0, 'blocking_by_check': Counter(),
           'advisories_by_check': Counter(), 'examples': [], 'coverage': {'versions': 0, 'entry_in_prompt': 0,
           'all_source_in_prompt': 0, 'source_chars': 0, 'source_chars_with_content': 0, 'max_file_chars': 0,
           'omitted_examples': []}}
    for vid, key in rows:
        try:
            repo = load(key)
        except Exception as exc:
            out['load_failures'] += 1
            out['examples'].append({'version': vid, 'load_error': type(exc).__name__})
            continue
        out['versions'] += 1
        report = scan(repo)
        if report.blocking:
            out['blocking_versions'] += 1
            if len(out['examples']) < 12:
                out['examples'].append({'version': vid, 'blocking': [f'{f.check} {f.where()}: {f.message}' for f in report.blocking][:4]})
        out['blocking_by_check'].update(f.check for f in report.blocking)
        out['advisories_by_check'].update(f.check for f in report.advisories)
        c = coverage(repo)
        cov = out['coverage']
        cov['versions'] += 1
        cov['entry_in_prompt'] += int(c['entry_in_prompt'])
        cov['all_source_in_prompt'] += int(c['source_files'] == c['source_files_with_content'])
        cov['source_chars'] += c['source_chars']
        cov['source_chars_with_content'] += c['source_chars_with_content']
        cov['max_file_chars'] = max(cov['max_file_chars'], c['largest_file_chars'])
        if c['omitted'] and len(cov['omitted_examples']) < 8:
            cov['omitted_examples'].append({'version': vid, 'omitted': c['omitted']})
    out['blocking_by_check'] = dict(out['blocking_by_check'])
    out['advisories_by_check'] = dict(out['advisories_by_check'])
    return out


def verify_versions(limit: int, deadline_s: float = 2400) -> dict:
    """Run the production verification chain (no model review: free) over the
    newest `limit` stored versions that have a spec. Read-only for product
    data: the sandbox has no network and behavioural acceptance runs on a
    scratch data directory."""
    import time
    from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    from .investor_app import _v28, _v28_pool, _verification_executor
    from .spec_repository import PostgresSpecRepository
    from .worker_tasks import contract_scope_for_version
    ws = _v28.engine.workspace
    specs = PostgresSpecRepository(_v28_pool)
    with _v28_pool.connection() as conn:
        rows = conn.execute(
            'SELECT v.id, v.project_id, v.artifact_key FROM project_versions v '
            'JOIN project_version_specs s ON s.version_id = v.id ORDER BY v.created_at DESC LIMIT %s', (limit,)).fetchall()
    started, results = time.monotonic(), []
    for vid, pid, key in rows:
        if time.monotonic() - started > deadline_s:
            results.append({'version': vid, 'status': 'NOT_RUN', 'why': 'deadline'})
            continue
        try:
            repo = ws._unzip_repo(ws.storage.get_bytes(key, verify=True))
            spec = specs.get(vid, pid)
            chain = _verification_executor(None)
            target = find_in_chain(chain, BehaviorAcceptanceExecutor)
            scope = contract_scope_for_version(_v28_pool, project_id=pid, version_id=vid)
            if target is not None and scope:
                target.scope = {k: scope.get(k) for k in ('infrastructure', 'required_integrations', 'user_roles',
                                                          'defaults_applied', 'prompt')}
            t0 = time.monotonic()
            report = chain.execute(repository=repo, spec=spec)
            results.append({'version': vid, 'status': 'PASS' if report.passed else 'FAIL',
                             'seconds': round(time.monotonic() - t0),
                             'failing': [f'{f.acceptance_id}: {f.message}'[:200] for f in report.failures][:3]})
        except Exception as exc:
            results.append({'version': vid, 'status': 'ERROR', 'why': f'{type(exc).__name__}: {str(exc)[:200]}'})
    counts = Counter(r['status'] for r in results)
    return {'versions': len(results), 'counts': dict(counts), 'results': results}


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == '--verify':
        print('VERIFY_REPLAY ' + json.dumps(verify_versions(int(sys.argv[2])), ensure_ascii=False, default=str))
        return 0
    from .investor_app import _v28, _v28_pool
    ws = _v28.engine.workspace
    store = ws.storage
    with _v28_pool.connection() as conn:
        rows = conn.execute('SELECT id, artifact_key FROM project_versions ORDER BY created_at').fetchall()
    result = replay(rows, lambda key: ws._unzip_repo(store.get_bytes(key, verify=True)))
    print('GATE_REPLAY ' + json.dumps(result, ensure_ascii=False, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())

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
from .modifier_engine import _CONTENT_SUFFIXES, repo_summary


def coverage(repo: dict[str, str]) -> dict:
    summary = repo_summary(repo)
    src = [f for f in summary['files'] if f['path'].lower().endswith(_CONTENT_SUFFIXES)]
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


def main() -> int:
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

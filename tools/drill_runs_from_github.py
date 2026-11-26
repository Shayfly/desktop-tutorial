"""Drill runs read from GitHub, the global record (Michael 2026-11-15: "C17 -- קריאה מ-GitHub").

A drill that runs as a scheduled workflow (C17: backup-restore.yml, daily) already leaves its record where every branch
reads the same thing: the workflow's run history on main. Copying it by hand into CONTROLS.json `drills_run` lagged
behind the drill (11-09..11-14 ran green and only 11-14 was recorded; R3 failed every PR on 11-13 although the drill had
run). This tool turns that history into the `drills_run` entries registry_lint R3 reads (--drill-runs).

A control opts in with `"drill_workflow": "<file in .github/workflows>"`. A run counts only if it ran on main, from the
schedule or a manual dispatch, and its conclusion is success -- a red, cancelled or branch run is not a drill.
GitHub unreadable -> exit 2 and no file: the lint must not fall back to a stale record (#322).

    python tools/drill_runs_from_github.py CONTROLS.json --repo OWNER/NAME --out drill-runs.json   (GH_TOKEN in env)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

COUNTED_EVENTS = ('schedule', 'workflow_dispatch')
PER_PAGE = 30          # one page: the latest 30 runs; a daily drill needs the latest success only


def drill_entries(control_id: str, workflow: str, runs: list[dict]) -> list[dict]:
    out = []
    for r in runs:
        if (r.get('status') == 'completed' and r.get('conclusion') == 'success' and r.get('head_branch') == 'main'
                and r.get('event') in COUNTED_EVENTS and r.get('path', f'.github/workflows/{workflow}').endswith(workflow)):
            out.append({'control': control_id, 'date': str(r['created_at'])[:10], 'result': 'PASS (workflow success)',
                        'runs': [str(r['id'])], 'workflow': f'.github/workflows/{workflow}', 'source': 'github',
                        'head_sha': str(r.get('head_sha', ''))[:7]})
    return out


def github_get(url: str, token: str, urlopen=urllib.request.urlopen):
    """One GET of the GitHub REST API, answered as JSON. The token goes in the header only. Shared with
    scripts/resolve_evidence_runs.py (Law 2, 2026-11-25); any error propagates to the caller, never a default."""
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                               'Authorization': f'Bearer {token}', 'X-GitHub-Api-Version': '2022-11-28'})
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_runs(repo: str, workflow: str, token: str, urlopen=urllib.request.urlopen) -> list[dict]:
    url = (f'https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs'
           f'?branch=main&status=completed&per_page={PER_PAGE}')
    body = github_get(url, token, urlopen)
    runs = body.get('workflow_runs')
    if not isinstance(runs, list):
        raise ValueError(f'{workflow}: the GitHub answer has no workflow_runs list')
    return runs


def main(argv: list[str] | None = None, urlopen=urllib.request.urlopen) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('registry')
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    token = os.environ.get('GH_TOKEN', '').strip()
    registry = json.loads(Path(a.registry).read_text(encoding='utf-8'))
    wanted = [(c['id'], c['drill_workflow']) for c in registry.get('controls') or [] if c.get('drill_workflow')]
    if not wanted:
        print('::notice title=drill runs::no control declares drill_workflow; nothing read from GitHub')
        Path(a.out).write_text('[]\n', encoding='utf-8')
        return 0
    if not token:
        print('::error title=drill runs::GH_TOKEN is not set; the drill record cannot be read from GitHub')
        return 2
    entries = []
    for cid, workflow in wanted:
        try:
            got = drill_entries(cid, workflow, fetch_runs(a.repo, workflow, token, urlopen))
        except Exception as exc:                       # unreadable global record: loud, no file, no fallback
            print(f'::error title=drill runs::{cid}: cannot read {workflow} runs from GitHub: {exc}')
            return 2
        latest = max((e['date'] for e in got), default=None)
        print(f'::notice title=drill runs::{cid} from {workflow}: {len(got)} green runs on main in the latest '
              f'{PER_PAGE}; latest {latest or "none"}')
        entries += got
    Path(a.out).write_text(json.dumps(entries, indent=1) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())

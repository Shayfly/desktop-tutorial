"""Prepare ONE preview's database before deployment-verify judges it (Michael 2026-11-11, 319 fix 2).

Resetting a stale preview branch gives it main's schema. A PR that adds its own migration still fails `verify`
then, because nothing ran that migration. So, for the preview of commit SHA:
  1. its Neon branch `preview/<git branch>` is reset from main if its data predates the latest migration in main
     (same rule and same one-hour debounce as tools/neon_preview_branches.py);
  2. the PR's OWN migrations (infra/postgres at SHA) are applied to that branch, with main's checksum-verified runner;
  3. only then does deployment-verify run.

Only for a commit that is the head of a branch of THIS repository (never a fork), only on a preview/* branch, never
Production. The connection string is fetched from the Neon API, masked, and never printed. Each result line is its own
annotation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import neon_preview_branches as N  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _gh(path: str, token: str):
    req = urllib.request.Request('https://api.github.com' + path,
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def branch_of(repo: str, sha: str, token: str) -> str | None:
    heads = _gh(f'/repos/{repo}/commits/{sha}/branches-where-head', token)
    names = [h['name'] for h in heads if h.get('name') != 'main']
    return names[0] if names else None


def connection_uri(project: str, branch_id: str, key: str) -> str:
    st, roles = N._call(N.NEON, 'GET', f'/projects/{project}/branches/{branch_id}/roles', key)
    if st != 200:
        raise RuntimeError(f'roles: HTTP {st}')
    owner = next((r['name'] for r in roles.get('roles', []) if not r.get('protected')), 'neondb_owner')
    q = urllib.parse.urlencode({'branch_id': branch_id, 'database_name': 'neondb', 'role_name': owner, 'pooled': 'false'})
    st, data = N._call(N.NEON, 'GET', f'/projects/{project}/connection_uri?{q}', key)
    if st != 200:
        raise RuntimeError(f'connection_uri: HTTP {st}')
    return data['uri']


def apply_pr_migrations(sha: str, url: str) -> list[int]:
    """The PR's infra/postgres at SHA, applied by main's runner (checksum drift and gaps still abort)."""
    sys.path.insert(0, str(ROOT))
    import psycopg
    from omni_prod.migration_runner import apply_migrations
    from omni_prod.migrations import discover_migrations
    with tempfile.TemporaryDirectory() as d:
        listing = subprocess.run(['git', '-C', str(ROOT), 'ls-tree', '--name-only', f'{sha}:infra/postgres'],
                                 capture_output=True, text=True, check=True).stdout.split()
        for name in listing:
            if name.endswith('.sql'):
                blob = subprocess.run(['git', '-C', str(ROOT), 'show', f'{sha}:infra/postgres/{name}'],
                                      capture_output=True, check=True).stdout
                (pathlib.Path(d) / name).write_bytes(blob)
        with psycopg.connect(url, connect_timeout=15) as conn:
            return list(apply_migrations(conn, discover_migrations(d)).applied_versions)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--sha', required=True)
    a = ap.parse_args(argv)
    key, token = os.environ.get('NEON_API_KEY', ''), os.environ.get('GH_TOKEN', '')
    if not key:
        print('::warning title=preview database::NEON_API_KEY is not set; not prepared')
        return 0
    ref = branch_of(a.repo, a.sha, token)
    if not ref:
        print(f'::notice title=preview database::{a.sha[:7]} is not the head of a branch of this repository; not prepared')
        return 0
    name = N.PREFIX + ref
    branch = next((b for b in N.neon_branches(a.project, key) if b.get('name') == name), None)
    if branch is None:
        print(f'::warning title=preview database::{name} does not exist (the integration creates it on deploy)')
        return 0
    latest, at = N.latest_migration_at(str(ROOT))
    print(f'::notice title=latest migration::{latest} landed in main at {at}')
    if N.needs_reset([branch], N._ts(at), dt.datetime.now(dt.timezone.utc)):
        st, _ = N._call_json(N.NEON, 'POST', f'/projects/{a.project}/branches/{branch["id"]}/restore', key,
                             {'source_branch_id': branch['parent_id']})
        print(f'::{"notice" if st in (200, 201, 202) else "error"} title=reset::{name} from main '
              f'(data from {N.data_taken_at(branch).isoformat()}) HTTP {st}')
        if st not in (200, 201, 202):
            return 1
    else:
        print(f'::notice title=reset::{name} not needed (data from {N.data_taken_at(branch).isoformat()})')
    url = connection_uri(a.project, branch['id'], key)
    print(f'::add-mask::{url}')
    applied = apply_pr_migrations(a.sha, url)
    print(f'::notice title=PR migrations::{name}: applied {applied or "none (already current)"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

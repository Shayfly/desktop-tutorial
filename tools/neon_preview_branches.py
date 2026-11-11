"""Neon preview-branch hygiene (Michael 2026-11-11, after 72): 166 preview branches, none used.

The Neon-Vercel integration creates `preview/<git branch>` in 148ai-db-v2 for every preview deployment and never
removes it. This tool:
  * --only <git ref>   deletes that one branch's database (the PR-closed policy)
  * (default)          prunes every `preview/*` branch whose git branch has no open PR and is older than --min-age-hours
  * always             alerts (::error, exit 1) when more than --alert-over preview branches remain

Dry run unless --apply. Never touches a non-preview branch (main, backups), a protected or default branch, or the
branch of an open PR. Every result line is its own GitHub annotation. No secret is printed: NEON_API_KEY and
GH_TOKEN come from the environment and are only sent to their own APIs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

NEON = 'https://console.neon.tech/api/v2'
GITHUB = 'https://api.github.com'
PREFIX = 'preview/'


def _call(base: str, method: str, path: str, token: str, accept: str = 'application/json'):
    req = urllib.request.Request(base + path, method=method,
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': accept})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def neon_branches(project: str, token: str) -> list[dict]:
    out, cursor = [], None
    while True:
        path = f'/projects/{project}/branches?limit=400' + (f'&cursor={cursor}' if cursor else '')
        st, data = _call(NEON, 'GET', path, token)
        if st != 200:
            sys.exit(f'::error title=neon::listing branches failed: HTTP {st}')
        out += data.get('branches', [])
        cursor = (data.get('pagination') or {}).get('next')
        if not cursor or not data.get('branches'):
            return out


def open_pr_refs(repo: str, token: str) -> set[str]:
    refs, page = set(), 1
    while True:
        st, data = _call(GITHUB, 'GET', f'/repos/{repo}/pulls?state=open&per_page=100&page={page}', token,
                         'application/vnd.github+json')
        if st != 200:
            sys.exit(f'::error title=github::listing open PRs failed: HTTP {st}')
        refs |= {p['head']['ref'] for p in data}
        if len(data) < 100:
            return refs
        page += 1


def plan(branches: list[dict], open_refs: set[str], *, only: str | None, min_age_hours: float,
         now: dt.datetime) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(delete, keep-with-reason) over the preview branches. Pure: the tests drive it."""
    delete, keep = [], []
    for b in branches:
        name = b.get('name', '')
        if not name.startswith(PREFIX):
            continue                                   # main, backups: never ours
        ref = name[len(PREFIX):]
        created = dt.datetime.fromisoformat(b['created_at'].replace('Z', '+00:00'))
        if b.get('protected') or b.get('default') or b.get('primary'):
            keep.append((b, 'protected'))
        elif only is not None and ref != only:
            continue
        elif only is None and ref in open_refs:
            keep.append((b, 'open PR'))
        elif only is None and (now - created).total_seconds() < min_age_hours * 3600:
            keep.append((b, 'younger than the minimum age'))
        else:
            delete.append(b)
    return delete, keep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--only', help='git ref whose preview database to delete (PR closed)')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--min-age-hours', type=float, default=1.0)
    ap.add_argument('--alert-over', type=int, default=50)
    a = ap.parse_args(argv)
    neon_key, gh_token = os.environ.get('NEON_API_KEY', ''), os.environ.get('GH_TOKEN', '')
    if not neon_key:
        print('::error title=neon::NEON_API_KEY is not set (repository secret)')
        return 2
    branches = neon_branches(a.project, neon_key)
    open_refs = set() if a.only else open_pr_refs(a.repo, gh_token)
    delete, keep = plan(branches, open_refs, only=a.only, min_age_hours=a.min_age_hours,
                        now=dt.datetime.now(dt.timezone.utc))
    for b, why in keep:
        print(f'::notice title=keep::{b["name"]} ({why})')
    deleted = 0
    for b in delete:
        if not a.apply:
            print(f'::notice title=would delete::{b["name"]} {b["id"]} created {b["created_at"]}')
            continue
        st, _ = _call(NEON, 'DELETE', f'/projects/{a.project}/branches/{b["id"]}', neon_key)
        if st in (200, 202):
            deleted += 1
            print(f'::notice title=deleted::{b["name"]} {b["id"]} created {b["created_at"]}')
        else:
            print(f'::warning title=not deleted::{b["name"]} {b["id"]}: HTTP {st}')
    remaining = sum(1 for b in branches if b.get('name', '').startswith(PREFIX)) - deleted
    print(f'::notice title=summary::preview branches {remaining} remaining; '
          f'{deleted if a.apply else len(delete)} {"deleted" if a.apply else "would be deleted"}')
    if remaining > a.alert_over:
        print(f'::error title=too many preview branches::{remaining} preview branches (limit {a.alert_over})')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

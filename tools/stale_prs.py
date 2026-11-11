"""Rule (Michael 2026-11-11): a PR that has not reached main within two weeks of being opened is closed.

Closing is reversible: the branch is kept and the PR can be reopened. Exempt: the label `keep-open`, and the bot's
rolling report PR (head `ci/v24-report`). Dry run unless --apply. Every result line is its own annotation.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

API = 'https://api.github.com'
EXEMPT_LABEL = 'keep-open'
EXEMPT_HEADS = ('ci/v24-report',)
NOTE = ('נסגר לפי כלל השבועיים: PR שלא נכנס ל-main תוך שבועיים נסגר. הענף נשאר; פתחו מחדש אם עדיין רלוונטי.\n\n'
        'Closed by the two-week rule: a PR that has not reached main within two weeks is closed. '
        'The branch is kept; reopen if still relevant.')


def call(method, path, token, body=None):
    req = urllib.request.Request(API + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, None


def stale(prs: list[dict], now: dt.datetime, days: int = 14) -> tuple[list[dict], list[tuple[dict, str]]]:
    """(to close, kept with reason). Pure: the tests drive it."""
    close, keep = [], []
    for p in prs:
        opened = dt.datetime.fromisoformat(p['created_at'].replace('Z', '+00:00'))
        age = (now - opened).days
        if p['head']['ref'] in EXEMPT_HEADS:
            keep.append((p, 'bot report'))
        elif any(l.get('name') == EXEMPT_LABEL for l in p.get('labels') or []):
            keep.append((p, EXEMPT_LABEL))
        elif age >= days:
            close.append(p)
        else:
            keep.append((p, f'{age} days open'))
    return close, keep


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--days', type=int, default=14)
    a = ap.parse_args(argv)
    token = os.environ.get('GH_TOKEN', '')
    prs, page = [], 1
    while True:
        st, data = call('GET', f'/repos/{a.repo}/pulls?state=open&per_page=100&page={page}', token)
        if st != 200:
            print(f'::error title=github::listing open PRs failed: HTTP {st}')
            return 2
        prs += data
        if len(data) < 100:
            break
        page += 1
    close, keep = stale(prs, dt.datetime.now(dt.timezone.utc), a.days)
    for p, why in keep:
        print(f'::notice title=keep::#{p["number"]} {p["title"][:80]} ({why})')
    for p in close:
        if not a.apply:
            print(f'::warning title=would close::#{p["number"]} {p["title"][:80]} (opened {p["created_at"][:10]})')
            continue
        call('POST', f'/repos/{a.repo}/issues/{p["number"]}/comments', token, {'body': NOTE})
        st, _ = call('PATCH', f'/repos/{a.repo}/pulls/{p["number"]}', token, {'state': 'closed'})
        level = 'notice' if st == 200 else 'warning'
        print(f'::{level} title={"closed" if st == 200 else "not closed"}::#{p["number"]} {p["title"][:80]} HTTP {st}')
    print(f'::notice title=summary::{len(close)} {"closed" if a.apply else "would be closed"}; {len(keep)} kept')
    return 0


if __name__ == '__main__':
    sys.exit(main())

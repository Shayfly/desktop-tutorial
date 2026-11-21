"""Warehouse 121 (the C18 finding, 2026-11-21): an alert when the build worker is dead.

C18 killed the build worker (run 44935937685) and nothing noticed it but the drill. This check runs on a GitHub-hosted
runner (it survives the worker host itself dying), reads the RQ worker registry of the build queue from Redis with the
same rq the worker runs, and turns the answer into a GitHub issue -- a notification to the owner -- and a red run.

  python tools/worker_alert.py --repo OWNER/NAME [--queue omni-builds] [--drill]     (OMNI_REDIS_URL, GH_TOKEN in env)

Verdicts (exit code):
  0 alive       at least one worker registered on the queue whose last heartbeat is at most MAX_AGE_SECONDS old
  1 dead        no worker registered on the queue, or every registered worker's heartbeat is older / missing
  2 unverified  Redis unreachable, OMNI_REDIS_URL or GH_TOKEN missing, or the registry unreadable. Not knowing is never
                "alive": it alerts too, under its own title.
The idle worker heartbeats before every 120 s dequeue wait (worker ttl 135 s, omni_prod/worker.py) and every 30 s while
a job runs; rq lets the key expire 195 s after the last heartbeat. MAX_AGE_SECONDS = 180 leaves 60 s of margin.

Issues: dead/unverified opens ONE issue (label ALERT_LABEL) or comments on the open one; alive closes it with a
comment. --drill (C18's alert half, DECISIONS question 8) uses its own label and title and closes its issue at once
after opening it: the notification has been sent, and a drill never leaves an open alert behind. The Redis URL is never
printed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

MAX_AGE_SECONDS = 180
BUILD_QUEUE = 'omni-builds'
ALERT_LABEL = 'alert-worker-down'
DRILL_LABEL = 'alert-worker-down-drill'
ALIVE, DEAD, UNVERIFIED = 'alive', 'dead', 'unverified'
EXIT = {ALIVE: 0, DEAD: 1, UNVERIFIED: 2}


def verdict(workers: list[dict], now: datetime, max_age: int = MAX_AGE_SECONDS) -> tuple[str, str]:
    """workers: [{'name', 'state', 'last_heartbeat' (aware datetime or None)}] registered on the queue."""
    if not workers:
        return DEAD, 'no worker is registered on the queue'
    fresh, stale = [], []
    for w in workers:
        beat = w.get('last_heartbeat')
        if beat is None:
            stale.append(f"{w['name']} (no heartbeat)")
            continue
        age = (now - beat).total_seconds()
        (fresh if age <= max_age else stale).append(f"{w['name']} ({w.get('state')}, heartbeat {age:.0f}s ago)")
    if fresh:
        return ALIVE, f'{len(fresh)} live: ' + ', '.join(fresh) + (f'; stale: {", ".join(stale)}' if stale else '')
    return DEAD, f'no live worker (heartbeat older than {max_age}s or missing): ' + ', '.join(stale)


def read_workers(redis_url: str, queue_name: str) -> list[dict]:
    """The registry as the worker itself writes it: rq's Worker.all for the queue (expired keys are dropped by rq)."""
    from redis import Redis
    from rq import Queue, Worker
    conn = Redis.from_url(redis_url, socket_connect_timeout=10, socket_timeout=10)
    out = []
    for w in Worker.all(queue=Queue(queue_name, connection=conn)):
        beat = w.last_heartbeat
        if beat is not None and beat.tzinfo is None:
            beat = beat.replace(tzinfo=timezone.utc)                  # rq stores UTC
        out.append({'name': w.name, 'state': w.get_state(), 'last_heartbeat': beat})
    return out


def check(redis_url: str, queue_name: str, now: datetime | None = None, reader=read_workers) -> tuple[str, str]:
    if not redis_url:
        return UNVERIFIED, 'OMNI_REDIS_URL is not set'
    try:
        workers = reader(redis_url, queue_name)
    except Exception as exc:                       # unreachable or unreadable: never "alive"
        return UNVERIFIED, f'cannot read the worker registry: {type(exc).__name__}'
    return verdict(workers, now or datetime.now(timezone.utc))


class GitHub:
    def __init__(self, repo: str, token: str, urlopen=urllib.request.urlopen):
        self.root, self.token, self.urlopen = f'https://api.github.com/repos/{repo}', token, urlopen

    def call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(self.root + path, method=method,
                                     data=None if body is None else json.dumps(body).encode('utf-8'),
                                     headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
                                              'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'})
        with self.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode('utf-8')
        return json.loads(raw) if raw else None

    def open_issues(self, label: str) -> list[dict]:
        rows = self.call('GET', f'/issues?state=open&labels={label}&per_page=10') or []
        return [r for r in rows if 'pull_request' not in r]


def act(gh: GitHub, state: str, detail: str, queue_name: str, *, drill: bool, run_url: str) -> str:
    """Open, update or close the alert issue. Returns what was done (one line)."""
    label = DRILL_LABEL if drill else ALERT_LABEL
    open_now = gh.open_issues(label)
    if state == ALIVE:
        for issue in open_now:
            gh.call('POST', f"/issues/{issue['number']}/comments", {'body': f'Recovered: {detail}\n\n{run_url}'})
            gh.call('PATCH', f"/issues/{issue['number']}", {'state': 'closed', 'state_reason': 'completed'})
        return f"closed #{', #'.join(str(i['number']) for i in open_now)}" if open_now else 'nothing open'
    what = 'build worker down' if state == DEAD else 'build worker state cannot be verified'
    title = f"ALERT{' (drill)' if drill else ''}: {what} ({queue_name})"
    body = (f'**{what}** on queue `{queue_name}`.\n\n{detail}\n\nRun: {run_url}\n\n'
            'Recovery (C18): `docker start omni-worker-worker-1` on the worker host; if that does not bring it back, '
            'dispatch `deploy-worker.yml` on main.')
    if open_now and not drill:
        n = open_now[0]['number']
        gh.call('POST', f'/issues/{n}/comments', {'body': f'Still {state}: {detail}\n\n{run_url}'})
        return f'commented on #{n}'
    issue = gh.call('POST', '/issues', {'title': title, 'body': body, 'labels': [label]})
    if drill:
        gh.call('POST', f"/issues/{issue['number']}/comments",
                {'body': 'Drill: the alert was raised and its notification sent; closed by the drill itself.'})
        gh.call('PATCH', f"/issues/{issue['number']}", {'state': 'closed', 'state_reason': 'completed'})
        return f"opened and closed drill issue #{issue['number']}"
    return f"opened #{issue['number']}"


def main(argv: list[str] | None = None, urlopen=urllib.request.urlopen, reader=read_workers) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repo', required=True)
    ap.add_argument('--queue', default=BUILD_QUEUE)
    ap.add_argument('--drill', action='store_true')
    a = ap.parse_args(argv)
    if a.drill == (a.queue == BUILD_QUEUE):
        print('::error title=worker alert::--drill goes with a queue other than the build queue, and only then')
        return 2
    state, detail = check(os.environ.get('OMNI_REDIS_URL', '').strip(), a.queue, reader=reader)
    print(f'::notice title=worker alert {state}::{a.queue}: {detail}')
    token = os.environ.get('GH_TOKEN', '').strip()
    if not token:
        print('::error title=worker alert::GH_TOKEN is not set: the alert cannot be raised')
        return 2
    run_url = os.environ.get('RUN_URL', '')
    try:
        done = act(GitHub(a.repo, token, urlopen), state, detail, a.queue, drill=a.drill, run_url=run_url)
    except Exception as exc:
        print(f'::error title=worker alert::the issue could not be raised: {type(exc).__name__}: {exc}')
        return 2
    print(f'::notice title=worker alert issue::{done}')
    if state != ALIVE:
        print(f'::error title=ALERT {state}::{a.queue}: {detail}')
    return EXIT[state]


if __name__ == '__main__':
    sys.exit(main())

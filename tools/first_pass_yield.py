"""first_pass_yield of production builds, read every day from the database (the founder's metric, 2026-10-19).

The worker writes each build's `first_pass` and `failure_taxonomy` into build_jobs.evidence_json (C24, #95: True only
for a build the worker itself records as ready with no repair). Until 2026-11-21 nothing read it back: the last
first_pass_yield anywhere was the rehearsal record, a month old. This tool reads the global record -- the production
database, in a READ ONLY transaction -- and reports it; it writes nothing anywhere but its own output files.

    python tools/first_pass_yield.py --out fpy.json --summary "$GITHUB_STEP_SUMMARY"     (OMNI_DATABASE_URL in env)

Windows: the last 1, 7 and 30 days, by created_at. Denominator: finished builds (ready or failed); cancelled builds
are counted apart (a cancelled build delivered nothing and failed nothing). A finished build with no first_pass record
(the worker was lost; the reaper closed it) counts as NOT a first pass and is listed by error_code -- never silently
dropped. Exit codes:
  0  reported (a yield of 0% is a finding, not an error)
  1  the evidence wiring is broken: finished builds in the last 7 days and not one carries a first_pass record
  2  cannot read: OMNI_DATABASE_URL missing, the database unreachable, or the query failed
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

WINDOWS = (1, 7, 30)
# The owner, 2026-11-23 16:06: the earlier build numbers are no longer current; keep them aside and count anew from
# today. main() starts every window no earlier than this moment; builds before it stay in the database, untouched, and
# are simply not counted. A new count is a new value here, said in its commit.
COUNT_FROM = dt.datetime(2026, 11, 23, tzinfo=dt.timezone.utc)
FINISHED = ('ready', 'failed')
QUERY = """
SELECT id, status, created_at, error_code,
       evidence_json ? 'first_pass' AS recorded,
       CASE WHEN jsonb_typeof(evidence_json->'first_pass') = 'boolean'
            THEN (evidence_json->>'first_pass')::boolean ELSE false END AS first_pass,
       CASE WHEN jsonb_typeof(evidence_json->'failure_taxonomy') = 'array'
            THEN evidence_json->'failure_taxonomy' ELSE '[]'::jsonb END AS taxonomy
FROM build_jobs
WHERE created_at >= %s
ORDER BY created_at
"""


def first_round_blockers(taxonomy) -> set[str]:
    """What stopped this build's first pass: the distinct `layer:failure_type` of its round-0 failures (the worker's
    taxonomy items, omni_prod/failure_taxonomy.py). Counted once per build, so one noisy build cannot dominate."""
    out = set()
    for t in taxonomy or []:
        # a preflight event is a pre-round plan repair: it costs no round and first_pass ignores it
        # (autonomous_core: first_pass reads the chain failures of round 0 only), so it is not a blocker
        if isinstance(t, dict) and t.get('round_index', 0) == 0 and t.get('layer') != 'preflight':
            out.add(f"{t.get('layer') or '?'}:{t.get('failure_type') or '?'}")
    return out


def summarize(rows: list[dict], now: dt.datetime, windows=WINDOWS, count_from: dt.datetime | None = None) -> dict:
    """rows: {id, status, created_at (aware), error_code, recorded, first_pass, taxonomy}. Pure; no I/O.
    count_from: no window starts before it (the owner's new count); None counts every row in the window."""
    out = {'generated_at': now.isoformat(timespec='seconds'), 'windows': {}}
    if count_from is not None:
        out['count_from'] = count_from.date().isoformat()
    for days in windows:
        since = now - dt.timedelta(days=days)
        if count_from is not None:
            since = max(since, count_from)
        rs = [r for r in rows if r['created_at'] >= since]
        fin = [r for r in rs if r['status'] in FINISHED]
        fp = [r for r in fin if r['status'] == 'ready' and r['recorded'] and r['first_pass'] is True]   # #95
        unrecorded = collections.Counter(str(r.get('error_code') or 'none') for r in fin if not r['recorded'])
        cats = collections.Counter(b for r in fin for b in first_round_blockers(r.get('taxonomy')))
        out['windows'][str(days)] = {
            'builds': len(rs), 'finished': len(fin), 'cancelled': sum(1 for r in rs if r['status'] == 'cancelled'),
            'other': sum(1 for r in rs if r['status'] not in FINISHED + ('cancelled',)),
            'ready': sum(1 for r in fin if r['status'] == 'ready'), 'first_pass': len(fp),
            'first_pass_yield': round(len(fp) / len(fin), 4) if fin else None,
            'recorded': sum(1 for r in fin if r['recorded']),
            'unrecorded_by_error_code': dict(sorted(unrecorded.items())),
            'top_failure_categories': cats.most_common(5),
        }
    return out


def verdict(summary: dict) -> tuple[int, str]:
    week = summary['windows'].get('7')
    if week and week['finished'] and not week['recorded']:
        return 1, (f"{week['finished']} finished builds in the last 7 days and not one carries a first_pass record: "
                   'the worker evidence (C24) no longer reaches the database')
    return 0, 'reported'


def lines(summary: dict) -> list[str]:
    out = []
    for days, w in summary['windows'].items():
        y = 'n/a (no finished build)' if w['first_pass_yield'] is None else f"{w['first_pass_yield']:.0%}"
        out.append(f"::notice title=first_pass_yield {days}d::{w['first_pass']}/{w['finished']} finished builds = {y}; "
                   f"ready {w['ready']}, cancelled {w['cancelled']}, builds {w['builds']}"
                   + (f"; no worker record (not first pass): {w['unrecorded_by_error_code']}"
                      if w['unrecorded_by_error_code'] else '')
                   + (f"; what stopped the first pass (builds): {w['top_failure_categories']}" if w['top_failure_categories'] else ''))
    return out


def markdown(summary: dict) -> str:
    rows = ['## first_pass_yield (production, read-only)', '',
            f"Generated {summary['generated_at']} from build_jobs.evidence_json. Denominator: finished builds "
            '(ready or failed).'
            + (f" Counted from {summary['count_from']} (the owner's new count); earlier builds are kept in the "
               'database and not counted.' if summary.get('count_from') else ''), '',
            '| window | first pass / finished | yield | ready | cancelled | no worker record | what stopped the first pass (builds) |',
            '|---|---|---|---|---|---|---|']
    for days, w in summary['windows'].items():
        y = 'n/a' if w['first_pass_yield'] is None else f"{w['first_pass_yield']:.0%}"
        rows.append(f"| {days}d | {w['first_pass']}/{w['finished']} | {y} | {w['ready']} | {w['cancelled']} | "
                    f"{sum(w['unrecorded_by_error_code'].values())} | "
                    + ', '.join(f'{c} ({n})' for c, n in w['top_failure_categories']) + ' |')
    return '\n'.join(rows) + '\n'


def read_rows(url: str, since: dt.datetime, connect=None) -> list[dict]:
    if connect is None:
        import psycopg
        connect = psycopg.connect
    with connect(url, connect_timeout=15) as conn:
        conn.execute('SET TRANSACTION READ ONLY')            # first statement of the transaction: nothing can write
        cur = conn.execute(QUERY, (since,))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        conn.rollback()
    for r in rows:
        if isinstance(r.get('taxonomy'), str):
            r['taxonomy'] = json.loads(r['taxonomy'])
    return rows


def main(argv: list[str] | None = None, connect=None, now: dt.datetime | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True)
    ap.add_argument('--summary', default='')
    a = ap.parse_args(argv)
    url = os.environ.get('OMNI_DATABASE_URL', '').strip()
    if not url:
        print('::error title=first_pass_yield::OMNI_DATABASE_URL is not set: the metric cannot be read')
        return 2
    now = now or dt.datetime.now(dt.timezone.utc)
    # the owner's count applies from its own moment on; a run whose "now" is before it (a replay of an older day)
    # counts as that day did
    count_from = COUNT_FROM if now >= COUNT_FROM else None
    try:
        start = now - dt.timedelta(days=max(WINDOWS))
        rows = read_rows(url, max(start, count_from) if count_from else start, connect=connect)
    except Exception as exc:                       # unreadable: loud, no file, never a made-up number
        print(f'::error title=first_pass_yield::cannot read build_jobs: {type(exc).__name__}')
        return 2
    summary = summarize(rows, now, count_from=count_from)
    for line in lines(summary):
        print(line)
    Path(a.out).write_text(json.dumps(summary, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if a.summary:
        with open(a.summary, 'a', encoding='utf-8') as fh:
            fh.write(markdown(summary))
    code, why = verdict(summary)
    if code:
        print(f'::error title=first_pass_yield evidence::{why}')
    return code


if __name__ == '__main__':
    sys.exit(main())

"""Good builds on the new engine, counted from the production database (the owner, 2026-11-22, DECISIONS.md).

A build is good when all four hold:
  1. a real content-site build whose evidence says the new engine served it (site_route.route == 'section_library'),
     and the three good builds are in three different domains;
  2. READY with at most two repair rounds;
  3. no blocking gate failed (skill_gates: a gate in mode 'block' whose status is 'fail');
  4. the owner looked and said it is at level -- one line per build in DECISIONS.md. Only the owner decides this one.

This tool counts conditions 1-3 in a READ ONLY transaction and reads condition 4 from DECISIONS.md (a line that names
the build id under "הבניות הטובות"). It writes nothing but its own output. Exit codes:
  0  reported (zero good builds is a finding, not an error)
  2  cannot read: OMNI_DATABASE_URL missing, the database unreachable, or the query failed

    python tools/good_builds.py --since 2026-11-22 --out good-builds.json     (OMNI_DATABASE_URL in env)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = 'section_library'
MAX_REPAIR_ROUNDS = 2
NEEDED = 3

QUERY = """
SELECT id, status, created_at,
       evidence_json->'site_route' AS site_route,
       evidence_json->'repair_rounds' AS repair_rounds,
       evidence_json->'skill_gates' AS skill_gates
FROM build_jobs
WHERE created_at >= %s AND status IN ('ready', 'failed')
ORDER BY created_at
"""


def _json(value):
    return json.loads(value) if isinstance(value, str) else value


def blocking_failures(skill_gates) -> list[str]:
    """The gates that block and failed. A gate without a status (not run) is not a failure here; NOT_RUN is reported
    by the gates themselves."""
    gates = _json(skill_gates) or {}
    return sorted(k for k, g in gates.items()
                  if isinstance(g, dict) and g.get('mode') == 'block' and g.get('status') == 'fail')


def judge(row: dict) -> dict:
    """One build -> its verdict on conditions 1-3, with every reason it is not good."""
    route = _json(row.get('site_route')) or {}
    rounds = _json(row.get('repair_rounds'))
    why = []
    if route.get('route') != ENGINE:
        why.append(f"not the new engine (site_route: {route.get('route') or 'none'})")
    if row.get('status') != 'ready':
        why.append(f"status {row.get('status')}")
    if not isinstance(rounds, int):
        why.append('no repair_rounds in the evidence')
    elif rounds > MAX_REPAIR_ROUNDS:
        why.append(f'{rounds} repair rounds (at most {MAX_REPAIR_ROUNDS})')
    failed = blocking_failures(row.get('skill_gates'))
    if failed:
        why.append('blocking gate failed: ' + ', '.join(failed))
    domain = route.get('domain') or route.get('category')
    return {'id': row['id'], 'created_at': str(row.get('created_at')), 'domain': domain,
            'repair_rounds': rounds, 'db_conditions_hold': not why, 'why_not': why}


def owner_said(decisions_text: str) -> set[str]:
    """Build ids the owner judged at level: lines under the "הבניות הטובות" heading of the flag decision."""
    at = decisions_text.find('**הבניות הטובות**')
    if at < 0:
        return set()
    block = decisions_text[at:].split('\n- **', 1)[0]
    return set(re.findall(r'\bbld_[0-9a-f]{8,}\b', block))


def summarize(rows: list[dict], approved: set[str]) -> dict:
    judged = [judge(r) for r in rows]
    for j in judged:
        j['owner_said_at_level'] = j['id'] in approved
        j['good'] = j['db_conditions_hold'] and j['owner_said_at_level']
    good = [j for j in judged if j['good']]
    domains = sorted({j['domain'] for j in good if j['domain']})
    return {'engine_builds': sum(1 for j in judged if not any(w.startswith('not the new engine') for w in j['why_not'])),
            'db_conditions_hold': sum(1 for j in judged if j['db_conditions_hold']),
            'good': len(good), 'good_domains': domains,
            'done': len(domains) >= NEEDED,
            'builds': judged}


def lines(summary: dict) -> list[str]:
    out = [f"::notice title=good builds::{summary['good']} good, in {len(summary['good_domains'])} different domains "
           f"({', '.join(summary['good_domains']) or 'none'}); {NEEDED} in {NEEDED} domains are needed -- "
           f"{'reached' if summary['done'] else 'not reached'}. New-engine builds: {summary['engine_builds']}; "
           f"conditions 1-3 hold on {summary['db_conditions_hold']}."]
    for j in summary['builds']:
        if j['why_not'] and any(w.startswith('not the new engine') for w in j['why_not']):
            continue
        state = 'GOOD' if j['good'] else ('waiting for the owner' if j['db_conditions_hold'] else 'not good')
        out.append(f"::notice title={j['id']}::{state}; domain {j['domain']}; repair rounds {j['repair_rounds']}"
                   + (f"; {'; '.join(j['why_not'])}" if j['why_not'] else ''))
    return out


def read_rows(url: str, since: dt.datetime, connect=None) -> list[dict]:
    if connect is None:
        import psycopg
        connect = psycopg.connect
    with connect(url, connect_timeout=15) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        cur = conn.execute(QUERY, (since,))
        names = [d[0] for d in cur.description]
        rows = [dict(zip(names, r)) for r in cur.fetchall()]
        conn.rollback()
    return rows


def main(argv: list[str] | None = None, connect=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--since', default='2026-11-22', help='first day counted (the flag decision)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--decisions', default=str(ROOT / 'DECISIONS.md'))
    a = ap.parse_args(argv)
    url = os.environ.get('OMNI_DATABASE_URL', '').strip()
    if not url:
        print('::error title=good builds::OMNI_DATABASE_URL is not set: nothing can be counted')
        return 2
    since = dt.datetime.fromisoformat(a.since).replace(tzinfo=dt.timezone.utc)
    try:
        rows = read_rows(url, since, connect=connect)
    except Exception as exc:                       # unreadable: loud, no file, never a made-up number
        print(f'::error title=good builds::cannot read build_jobs: {type(exc).__name__}')
        return 2
    approved = owner_said(Path(a.decisions).read_text(encoding='utf-8'))
    summary = summarize(rows, approved)
    for line in lines(summary):
        print(line)
    Path(a.out).write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""One bounded collect run: 1.1 search -> 1.2 verify -> 1.3 capture (docs/spec/gemini-a2.md section 1).

A search that is `insufficient` stops the run before any page is opened. Every candidate is verified at most once
and captured only after a pass. Every document is schema-checked as it is made; the funnel counts each rejection
by its reason code. Nothing here is live: the session decides which hosts may be reached.
"""
from __future__ import annotations

from collections import Counter

from .capture import capture
from .verify import verify


def run(session, search_run: dict, store) -> dict:
    out = {'search': search_run, 'verified': [], 'captured': [], 'blocked_hosts': []}
    rejected: Counter = Counter()
    if search_run['coverage']['status'] != 'ok':
        out['stopped'] = 'search_insufficient'
    else:
        for cand in search_run['candidates'][:60]:          # bounded by the schema too
            v = verify(session, cand)
            out['verified'].append(v)
            if v['outcome'] != 'pass':
                rejected[v['rejection']['reason_code']] += 1
                continue
            c = capture(session, cand, store)
            out['captured'].append(c)
            if c['outcome'] != 'pass':
                rejected[c['rejection']['reason_code']] += 1
    out['blocked_hosts'] = sorted(set(session.blocked))
    out['funnel'] = {'candidates': len(search_run['candidates']),
                     'verified': sum(1 for v in out['verified'] if v['outcome'] == 'pass'),
                     'captured': sum(1 for c in out['captured'] if c['outcome'] == 'pass'),
                     'rejected': dict(rejected)}
    return out

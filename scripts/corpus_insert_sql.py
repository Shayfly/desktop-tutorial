"""SQL that inserts the accepted pages of one collected category into corpus_pages (migration 045).

usage: python scripts/corpus_insert_sql.py corpus/collected/<category>.json  -> prints ONE statement for a single
transaction. Run by hand under CLAUDE.md section 5 (backup branch, dry count, one transaction, verification).

Never overwritten: ON CONFLICT (url) DO NOTHING -- a page already collected keeps its first capture.
Hold-out (20%, the owner 2026-11-17): a page is held out when sha256(url) mod 5 == 0 -- deterministic, so the split
never depends on the order or the day of collection.
"""
from __future__ import annotations

import hashlib
import json
import sys

ACCEPT_KEYS = ('url', 'city', 'business', 'phone', 'address', 'pages', 'evidence')


def holdout(url: str) -> bool:
    return int(hashlib.sha256(url.encode('utf-8')).hexdigest(), 16) % 5 == 0


def _q(value) -> str:
    return 'NULL' if value is None else "'" + str(value).replace("'", "''") + "'"


def statement(collected: dict) -> str:
    rows = collected.get('accepted') or []
    if not rows:
        raise SystemExit('nothing accepted in this file')
    for r in rows:
        missing = [k for k in ACCEPT_KEYS if k not in r]
        if missing or not str(r['url']).startswith(('http://', 'https://')):
            raise SystemExit(f'row {r.get("url")!r}: missing {missing} or not a URL')
    values = []
    for r in rows:
        note = json.dumps({k: r[k] for k in ('business', 'phone', 'address', 'pages', 'evidence')}, ensure_ascii=False)
        values.append(f"({_q(r['url'])}, {_q(collected['category'])}, {_q(r['city'])}, {_q(collected['collected_at'])}, "
                      f"{'TRUE' if holdout(r['url']) else 'FALSE'}, {_q(note)})")
    return ('INSERT INTO corpus_pages (url, category, city, fetched_at, holdout, notes) VALUES\n  '
            + ',\n  '.join(values) + '\nON CONFLICT (url) DO NOTHING RETURNING url, holdout;')


if __name__ == '__main__':
    print(statement(json.load(open(sys.argv[1], encoding='utf-8'))))

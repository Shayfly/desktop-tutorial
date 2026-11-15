"""The shared reference store (Michael 2026-11-15, "מאגר דוגמאות משותף"; migration 043).

One store, two consumers: A2 (Gemini) writes cards, A1 reads them. A card is the ReferenceCard of #369
(docs/spec/reference_card.schema.json), validated before it is stored; the store adds its columns (decision 1: no
second table of references): category, adjacency_rank, source_url, fetched_at, extraction_version, status.

Adjacency (appendix B): a category has neighbours in rank order, each marked `cross_vertical` when it belongs to
another vertical (e.g. vets -> pet shops); the fallback itself (step 6) uses at most two links.

Read order for A1 (decision 5): a `stale` card (older than 90 days) is NOT removed -- it is ranked below every fresh
card and marked; `weak` is ranked last. Only the owner retires a card (rule: "רק הבעלים מבטל דוגמאות").

PostgresReferenceStore is the production store (same contract as MemoryReferenceStore, which the unit tests use).
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

STALE_AFTER = timedelta(days=90)
OWNER = 'shai'
CARD_SCHEMA = Path(__file__).resolve().parents[1] / 'docs' / 'spec' / 'reference_card.schema.json'
_RANK = {'fresh': 0, 'stale': 1, 'weak': 2}
COLLECT_REASONS = ('domain_rejected', 'empty_category', 'stale_category', 'weak_category')


class ReferenceStoreError(ValueError):
    pass


@lru_cache(maxsize=1)
def _card_validator():
    from jsonschema import Draft202012Validator, FormatChecker
    return Draft202012Validator(json.loads(CARD_SCHEMA.read_text(encoding='utf-8')), format_checker=FormatChecker())


def checked_card(card: dict) -> dict:
    errors = sorted(_card_validator().iter_errors(card), key=lambda e: list(e.absolute_path))
    if errors:
        where = '/'.join(str(p) for p in errors[0].absolute_path) or '(root)'
        raise ReferenceStoreError(f'card outside reference_card.schema.json at {where}: {errors[0].message[:200]}')
    return card


def card_sha256(card: dict) -> str:
    return hashlib.sha256(json.dumps(card, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                          .encode('utf-8')).hexdigest()


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


@dataclass(frozen=True)
class StoredCard:
    card: dict
    category: str
    adjacency_rank: int
    source_url: str
    fetched_at: datetime
    extraction_version: str
    status: str                   # as stored
    retired: bool

    def effective_status(self, now: datetime) -> str:
        """`fresh` older than 90 days reads as `stale` (marked, ranked lower, never dropped)."""
        if self.status == 'fresh' and now - self.fetched_at > STALE_AFTER:
            return 'stale'
        return self.status

    @property
    def card_id(self) -> str:
        return self.card['card_id']


def _row(card: dict, *, adjacency_rank: int, extraction_version: str, status: str) -> StoredCard:
    if status not in _RANK:
        raise ReferenceStoreError(f'status must be one of {tuple(_RANK)}')
    if adjacency_rank not in (0, 1, 2):
        raise ReferenceStoreError('adjacency_rank is 0 (the category itself), 1 or 2 -- never a third link')
    checked_card(card)
    return StoredCard(copy.deepcopy(card), card['vertical'], adjacency_rank, card['source']['url'],
                      _parse(card['source']['captured_at']), extraction_version, status, False)


def _check_rejection(signal: str, scope: str | None) -> None:
    if signal not in ('disliked', 'asked_another'):
        raise ReferenceStoreError("signal is 'disliked' or 'asked_another'")
    if scope not in (None, 'layer', 'domain', 'all'):
        raise ReferenceStoreError("scope is 'layer', 'domain' or 'all'")


def _check_neighbours(category: str, neighbours) -> None:
    names = [n for n, _ in neighbours]
    if category in names or len(set(names)) != len(names) or len(names) > 20:
        raise ReferenceStoreError('distinct neighbours (at most 20), never the category itself')


def _order(rows, now):
    """Approved, not retired: fresh before stale before weak, the category before its neighbours, best total first."""
    live = [r for r in rows if not r.retired and r.card['decision']['status'] == 'approved']
    return sorted(live, key=lambda r: (_RANK[r.effective_status(now)], r.adjacency_rank,
                                       -r.card['judge']['total'], r.card_id))


class MemoryReferenceStore:
    def __init__(self):
        self.rows: dict[str, StoredCard] = {}
        self.adjacency: dict[str, list[tuple[str, int]]] = {}
        self.collect: list[dict] = []
        self.offers: list[dict] = []
        self.rejections: list[dict] = []
        self.alerts: list[dict] = []

    def add_card(self, card: dict, *, extraction_version: str, adjacency_rank: int = 0, status: str = 'fresh'):
        row = _row(card, adjacency_rank=adjacency_rank, extraction_version=extraction_version, status=status)
        if row.card_id in self.rows:
            raise ReferenceStoreError(f'{row.card_id} is already stored')
        self.rows[row.card_id] = row
        return row

    def approved_for(self, category: str, *, now: datetime | None = None) -> list[StoredCard]:
        now = now or datetime.now(timezone.utc)
        return _order([r for r in self.rows.values() if r.category == category], now)

    def retire(self, card_id: str, *, by: str):
        if by != OWNER:
            raise ReferenceStoreError('only the owner retires a reference card')
        r = self.rows[card_id]
        self.rows[card_id] = StoredCard(r.card, r.category, r.adjacency_rank, r.source_url, r.fetched_at,
                                        r.extraction_version, r.status, True)

    def set_adjacent(self, category: str, neighbours: list[tuple[str, bool]]):
        _check_neighbours(category, neighbours)
        self.adjacency[category] = [(n, cross, i + 1) for i, (n, cross) in enumerate(neighbours)]

    def adjacent(self, category: str) -> list[dict]:
        return [{'category': n, 'cross_vertical': cross, 'rank': r}
                for n, cross, r in sorted(self.adjacency.get(category, []), key=lambda x: x[2])]

    def request_collect(self, category: str, reason: str, brief_id: str | None = None):
        if reason not in COLLECT_REASONS:
            raise ReferenceStoreError(f'reason must be one of {COLLECT_REASONS}')
        if not any(q['category'] == category and q['reason'] == reason for q in self.collect):
            self.collect.append({'category': category, 'reason': reason, 'brief_id': brief_id})

    def open_collect_requests(self) -> list[dict]:
        return list(self.collect)

    # ---- offers, rejections and alerts (step 7) ----
    def record_offer(self, *, brief_id: str, category: str, card_id: str | None = None,
                     component_key: str | None = None, at: datetime | None = None):
        self.offers.append({'brief_id': brief_id, 'category': category, 'card_id': card_id,
                            'component_key': component_key, 'at': at or datetime.now(timezone.utc)})

    def record_rejection(self, *, brief_id: str, category: str, component_key: str | None, signal: str,
                         scope: str | None = None, at: datetime | None = None):
        _check_rejection(signal, scope)
        self.rejections.append({'brief_id': brief_id, 'category': category, 'component_key': component_key,
                                'signal': signal, 'scope': scope, 'at': at or datetime.now(timezone.utc)})

    def rejected_keys(self, brief_id: str) -> set[str]:
        return {r['component_key'] for r in self.rejections if r['brief_id'] == brief_id and r['component_key']}

    def counts_since(self, category: str, since: datetime | None) -> tuple[list[datetime], list[datetime]]:
        ok = lambda r: r['category'] == category and (since is None or r['at'] > since)
        return (sorted(o['at'] for o in self.offers if ok(o)), sorted(r['at'] for r in self.rejections if ok(r)))

    def alerts_for(self, category: str) -> list[dict]:
        return [dict(a) for a in self.alerts if a['category'] == category]

    def record_alert(self, *, category: str, window_start: datetime, rejections: int, offers: int,
                     at: datetime | None = None, changed_at: datetime | None = None):
        self.alerts.append({'category': category, 'window_start': window_start, 'rejections': rejections,
                            'offers': offers, 'fired_at': at or datetime.now(timezone.utc), 'changed_at': changed_at})


class PostgresReferenceStore:
    """Same contract as MemoryReferenceStore, on migration 043's tables. The database repeats the hard rules as
    CHECK constraints (an approved card needs a human, only the owner retires, at most two neighbours)."""

    def __init__(self, pool):
        self.pool = pool

    def add_card(self, card: dict, *, extraction_version: str, adjacency_rank: int = 0, status: str = 'fresh'):
        row = _row(card, adjacency_rank=adjacency_rank, extraction_version=extraction_version, status=status)
        d = card['decision']
        with self.pool.connection() as conn:
            conn.execute(
                'INSERT INTO reference_cards (card_id, category, adjacency_rank, source_url, fetched_at, '
                'extraction_version, status, decision, reason_code, decided_by, card, card_sha256) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)',
                (row.card_id, row.category, adjacency_rank, row.source_url, row.fetched_at, extraction_version,
                 status, d['status'], d['reason_code'], d['decided_by'], json.dumps(card, ensure_ascii=False),
                 card_sha256(card)))
        return row

    def approved_for(self, category: str, *, now: datetime | None = None) -> list[StoredCard]:
        now = now or datetime.now(timezone.utc)
        with self.pool.connection() as conn:
            rows = conn.execute(
                'SELECT card, adjacency_rank, extraction_version, status, retired_at IS NOT NULL, card_sha256 '
                "FROM reference_cards WHERE category = %s AND decision = 'approved' AND retired_at IS NULL",
                (category,)).fetchall()
        out = []
        for card, rank, version, status, retired, digest in rows:
            card = card if isinstance(card, dict) else json.loads(card)
            if card_sha256(card) != digest:          # a card changed in place is never served
                raise ReferenceStoreError(f'{card.get("card_id")}: stored card does not match its sha256')
            out.append(StoredCard(card, category, rank, card['source']['url'], _parse(card['source']['captured_at']),
                                  version, status, retired))
        return _order(out, now)

    def retire(self, card_id: str, *, by: str):
        if by != OWNER:
            raise ReferenceStoreError('only the owner retires a reference card')
        with self.pool.connection() as conn:
            done = conn.execute('UPDATE reference_cards SET retired_at = now(), retired_by = %s '
                                'WHERE card_id = %s AND retired_at IS NULL', (by, card_id)).rowcount
        if done != 1:
            raise ReferenceStoreError(f'{card_id}: not found or already retired')

    def set_adjacent(self, category: str, neighbours: list[tuple[str, bool]]):
        _check_neighbours(category, neighbours)
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute('DELETE FROM category_adjacency WHERE category = %s', (category,))
                for i, (n, cross) in enumerate(neighbours):
                    conn.execute('INSERT INTO category_adjacency (category, adjacent_category, rank, cross_vertical) '
                                 'VALUES (%s, %s, %s, %s)', (category, n, i + 1, bool(cross)))

    def adjacent(self, category: str) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT adjacent_category, cross_vertical, rank FROM category_adjacency '
                                'WHERE category = %s ORDER BY rank', (category,)).fetchall()
        return [{'category': n, 'cross_vertical': cross, 'rank': r} for n, cross, r in rows]

    def request_collect(self, category: str, reason: str, brief_id: str | None = None):
        if reason not in COLLECT_REASONS:
            raise ReferenceStoreError(f'reason must be one of {COLLECT_REASONS}')
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO collect_queue (category, reason, brief_id) SELECT %s, %s, %s WHERE NOT EXISTS '
                         '(SELECT 1 FROM collect_queue WHERE category = %s AND reason = %s AND resolved_at IS NULL)',
                         (category, reason, brief_id, category, reason))

    def open_collect_requests(self) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT category, reason, brief_id FROM collect_queue WHERE resolved_at IS NULL '
                                'ORDER BY requested_at').fetchall()
        return [{'category': c, 'reason': r, 'brief_id': b} for c, r, b in rows]

    # ---- offers, rejections and alerts (step 7) ----
    def record_offer(self, *, brief_id: str, category: str, card_id: str | None = None,
                     component_key: str | None = None, at: datetime | None = None):
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO reference_offers (brief_id, category, card_id, component_key, created_at) '
                         'VALUES (%s, %s, %s, %s, COALESCE(%s, now()))', (brief_id, category, card_id, component_key, at))

    def record_rejection(self, *, brief_id: str, category: str, component_key: str | None, signal: str,
                         scope: str | None = None, at: datetime | None = None):
        _check_rejection(signal, scope)
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO offer_rejections (brief_id, category, component_key, signal, scope, created_at) '
                         'VALUES (%s, %s, %s, %s, %s, COALESCE(%s, now()))',
                         (brief_id, category, component_key, signal, scope, at))

    def rejected_keys(self, brief_id: str) -> set[str]:
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT DISTINCT component_key FROM offer_rejections WHERE brief_id = %s '
                                'AND component_key IS NOT NULL', (brief_id,)).fetchall()
        return {r[0] for r in rows}

    def counts_since(self, category: str, since: datetime | None) -> tuple[list[datetime], list[datetime]]:
        with self.pool.connection() as conn:
            offers = conn.execute('SELECT created_at FROM reference_offers WHERE category = %s AND '
                                  '(%s::timestamptz IS NULL OR created_at > %s) ORDER BY created_at',
                                  (category, since, since)).fetchall()
            rejections = conn.execute('SELECT created_at FROM offer_rejections WHERE category = %s AND '
                                      '(%s::timestamptz IS NULL OR created_at > %s) ORDER BY created_at',
                                      (category, since, since)).fetchall()
        return [r[0] for r in offers], [r[0] for r in rejections]

    def alerts_for(self, category: str) -> list[dict]:
        with self.pool.connection() as conn:
            rows = conn.execute('SELECT window_start, rejections, offers, fired_at, changed_at FROM offer_alerts '
                                'WHERE category = %s ORDER BY fired_at, id', (category,)).fetchall()
        return [{'category': category, 'window_start': w, 'rejections': r, 'offers': o, 'fired_at': f, 'changed_at': c}
                for w, r, o, f, c in rows]

    def record_alert(self, *, category: str, window_start: datetime, rejections: int, offers: int,
                     at: datetime | None = None, changed_at: datetime | None = None):
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO offer_alerts (category, window_start, rejections, offers, fired_at, changed_at) '
                         'VALUES (%s, %s, %s, %s, COALESCE(%s, now()), %s)',
                         (category, window_start, rejections, offers, at, changed_at))

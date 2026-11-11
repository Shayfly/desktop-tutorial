"""Opt-in PostgreSQL checks. Never connect to a live/non-loopback database.

Set OMNI_PROFIT_TEST_DATABASE_URL to a disposable local database whose name
starts with profit_test, then run this file directly with pytest. No default
connection or service credentials are used. Every test owns a private schema.
"""
import os
import re
import uuid
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from omni_prod.billing import BillingEntitlementEvent
from omni_prod.subscription_store import PostgresSubscriptionService


def _local_test_connection(url):
    from psycopg.conninfo import conninfo_to_dict
    params = conninfo_to_dict(url)
    allowed = {'host', 'hostaddr', 'port', 'dbname', 'user', 'password', 'sslmode'}
    if set(params) - allowed:
        raise ValueError('connection services and overrides are not supported')
    host = params.get('host')
    address = params.get('hostaddr')
    if host not in {'localhost', '127.0.0.1', '::1'} or (
        address is not None and address not in {'127.0.0.1', '::1'}
    ) or not re.fullmatch(r'profit_test[A-Za-z0-9_]*', params.get('dbname', '')):
        raise ValueError('requires a disposable loopback profit_test database')
    # Pin the effective address as well as the hostname, and connect with
    # sanitized keywords rather than re-expanding a caller-supplied DSN.
    params['hostaddr'] = address or ('::1' if host == '::1' else '127.0.0.1')
    port = params.get('port', '5432')
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError('invalid test database port')
    params['port'] = port
    return params


@pytest.mark.parametrize('url', [
    'postgresql://localhost/profit_test?host=remote.example',
    'postgresql://localhost/profit_test?hostaddr=192.0.2.1',
    'postgresql://localhost/profit_test?dbname=production',
    'postgresql://localhost/profit_test?service=production',
    'postgresql://localhost/profit_test?host=127.0.0.1,remote.example',
])
def test_database_guard_rejects_connection_overrides(url):
    with pytest.raises(ValueError):
        _local_test_connection(url)


@pytest.fixture
def pool():
    url = os.getenv('OMNI_PROFIT_TEST_DATABASE_URL')
    if not url:
        pytest.skip('disposable local PostgreSQL not configured; no live DB accessed')
    params = _local_test_connection(url)
    import psycopg
    from psycopg import sql
    schema = 'profit_test_' + uuid.uuid4().hex
    with psycopg.connect(**params, connect_timeout=2) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))

    class IsolatedPool:
        @contextmanager
        def connection(self):
            with psycopg.connect(**params, connect_timeout=2, options=f'-c search_path={schema}') as conn:
                yield conn

    result = IsolatedPool()
    try:
        with result.connection() as conn:
            conn.execute('CREATE TABLE creator_subscriptions ('
                         'user_id TEXT PRIMARY KEY, plan_code TEXT NOT NULL, cycle TEXT NOT NULL, '
                         'credits_used INTEGER NOT NULL DEFAULT 0, '
                         'provider_spend_usd NUMERIC NOT NULL DEFAULT 0)')
            migration = Path(__file__).resolve().parents[2] / 'infra/postgres/039_billing_event_idempotency.sql'
            conn.execute(migration.read_text(encoding='utf-8'))
            conn.execute(migration.read_text(encoding='utf-8'))  # additive/idempotent
        yield result
    finally:
        with psycopg.connect(**params, connect_timeout=2) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def payment(eid='evt_paid', source='sub_1', created=100, plan='basic'):
    return BillingEntitlementEvent(eid, 'u', plan, 'checkout.session.completed', source, created)


def test_duplicate_and_usage_survive_service_restart(pool):
    first = PostgresSubscriptionService(pool=pool)
    assert first.apply_billing_entitlement(payment())['processed']
    with pool.connection() as conn:
        conn.execute("UPDATE creator_subscriptions SET credits_used=75, provider_spend_usd=0.25 WHERE user_id='u'")
    second = PostgresSubscriptionService(pool=pool)
    assert second.apply_billing_entitlement(payment())['duplicate']
    with pool.connection() as conn:
        assert conn.execute("SELECT credits_used FROM creator_subscriptions WHERE user_id='u'").fetchone()[0] == 75


def test_simultaneous_deliveries_apply_once(pool):
    def apply(_):
        return PostgresSubscriptionService(pool=pool).apply_billing_entitlement(payment())
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(apply, range(8)))
    assert sum(r['processed'] for r in results) == 1
    assert sum(r.get('duplicate', False) for r in results) == 7


def test_source_revocation_tombstone_survives_service_restart(pool):
    service = PostgresSubscriptionService(pool=pool)
    service.apply_billing_entitlement(payment())
    cancel = BillingEntitlementEvent('evt_cancel', 'u', 'free', 'customer.subscription.deleted', 'sub_new', 300)
    assert service.apply_billing_entitlement(cancel)['source_mismatch']
    late = PostgresSubscriptionService(pool=pool).apply_billing_entitlement(
        payment('evt_new', 'sub_new', 200, 'pro'))
    assert late['stale']
    with pool.connection() as conn:
        assert conn.execute("SELECT plan_code FROM creator_subscriptions WHERE user_id='u'").fetchone()[0] == 'amateur'  # legacy event plan 'basic' is stored canonically (CEO 2026-10-19)


def test_conflicting_event_id_does_not_mutate_entitlement(pool):
    service = PostgresSubscriptionService(pool=pool)
    service.apply_billing_entitlement(payment())
    with pytest.raises(ValueError, match='different contents'):
        service.apply_billing_entitlement(payment(plan='pro'))
    with pool.connection() as conn:
        assert conn.execute("SELECT plan_code FROM creator_subscriptions WHERE user_id='u'").fetchone()[0] == 'amateur'  # legacy event plan 'basic' is stored canonically (CEO 2026-10-19)

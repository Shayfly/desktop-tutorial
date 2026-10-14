"""G3 acceptance: opt-in, disposable loopback DB, deliberately red on base SHA."""
import json
import os
from pathlib import Path
import uuid
from decimal import Decimal

import pytest

from tests.financial_fault_harness import run_case, validate_database


DATABASE_URL = os.environ.get('FINANCIAL_FAULT_DATABASE_URL')


@pytest.mark.skipif(not DATABASE_URL, reason='requires an explicit disposable financial-fault database')
@pytest.mark.parametrize('fail_ledger', [False, True], ids=['durable-ledger', 'failed-ledger'])
def test_crashed_worker_preserves_provider_liability(fail_ledger: bool):
    validate_database(DATABASE_URL)
    output = Path(os.environ.get('FINANCIAL_FAULT_OUTPUT_DIR', 'work/financial-fault-acceptance')) / uuid.uuid4().hex
    output.mkdir(parents=True)
    result = run_case(DATABASE_URL, output, fail_ledger=fail_ledger, expect_prevention=fail_ledger)
    (output / 'result.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf-8')
    failures = [name for name, passed in result['checks'].items() if not passed]
    assert result['provider_requests'] == (0 if fail_ledger else 1)
    assert result['provider_cost_usd'] == ('0' if fail_ledger else '0.02')
    assert result['final']['reservation'][0] == ('RELEASED' if fail_ledger else 'RESERVED')
    assert Decimal(str(result['final']['balance'][1])) == (Decimal('0') if fail_ledger else Decimal('0.10'))
    assert result['deliveries'] == []
    assert not failures, json.dumps({'failed_acceptance': failures, 'result': result}, default=str)


@pytest.mark.skipif(not DATABASE_URL, reason='requires an explicit disposable financial-fault database')
def test_recovery_rechecks_heartbeat_after_candidate_scan(monkeypatch):
    from contextlib import contextmanager
    from unittest.mock import MagicMock
    from omni_prod import maintenance, subscription_store
    from omni_prod.db import DatabasePool

    validate_database(DATABASE_URL)
    pool = DatabasePool(DATABASE_URL)
    bid = 'bld_fault_heartbeat_' + uuid.uuid4().hex[:12]
    with pool.connection() as conn:
        conn.execute("INSERT INTO build_jobs(id, project_id, status, started_at, heartbeat_at) "
                     "VALUES (%s, 'fixture', 'running', now(), now()-interval '20 minutes')", (bid,))
    exposure = MagicMock(return_value=True)
    monkeypatch.setattr(subscription_store, 'provider_exposure', exposure)

    class RacingPool:
        @contextmanager
        def connection(self):
            with pool.connection() as conn:
                class Proxy:
                    def __getattr__(self, name):
                        return getattr(conn, name)

                    def execute(self, sql, args=None):
                        cursor = conn.execute(sql, args)
                        if sql == maintenance._LOST['build']:
                            rows = cursor.fetchall()
                            with pool.connection() as heartbeat:
                                heartbeat.execute("UPDATE build_jobs SET heartbeat_at=now() WHERE id=%s", (bid,))
                            return type('Candidates', (), {'fetchall': lambda self: rows})()
                        return cursor
                yield Proxy()

    subs, enqueue = MagicMock(), MagicMock()
    try:
        outcome = maintenance.recover_lost_running(RacingPool(), subscriptions=subs, enqueue=enqueue)
        with pool.connection() as conn:
            status = conn.execute('SELECT status FROM build_jobs WHERE id=%s', (bid,)).fetchone()[0]
        assert status == 'running'
        assert bid not in sum(outcome.values(), [])
        exposure.assert_not_called()
        subs.release.assert_not_called()
        enqueue.assert_not_called()
    finally:
        with pool.connection() as conn:
            conn.execute('DELETE FROM build_events WHERE build_id=%s', (bid,))
            conn.execute('DELETE FROM build_jobs WHERE id=%s', (bid,))
        pool.close()

import json
from decimal import Decimal

import pytest

from omni_prod import company_loss

class FakeCursor:
    def __init__(self):
        self.calls = []
        self.rows = []

    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params))

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

def test_no_overrun_writes_nothing():
    cur = FakeCursor()
    assert company_loss.record_overrun(
        cur, source='intake_reservation', idempotency_key='r1',
        quoted_usd=Decimal('0.04'), actual_usd=Decimal('0.04'),
        cause=company_loss.METERED_OVERRUN) is None
    assert cur.calls == []

def test_saving_is_not_a_loss():
    cur = FakeCursor()
    assert company_loss.record_overrun(
        cur, source='intake_reservation', idempotency_key='r1',
        quoted_usd=Decimal('0.04'), actual_usd=Decimal('0.01'),
        cause=company_loss.METERED_OVERRUN) is None

def test_overrun_is_written_with_the_exact_amount():
    cur = FakeCursor()
    loss = company_loss.record_overrun(
        cur, source='intake_reservation', idempotency_key='r1',
        quoted_usd=Decimal('0.04'), actual_usd=Decimal('0.10'),
        cause=company_loss.METERED_OVERRUN, build_id='b1',
        evidence={'metering': {'input_tokens': 10}})
    assert loss == Decimal('0.06000000')
    sql, params = cur.calls[0]
    assert 'ON CONFLICT (source, idempotency_key) DO NOTHING' in sql
    assert params[9] == Decimal('0.04000000')
    assert params[10] == Decimal('0.10000000')
    assert json.loads(params[13])['metering'] == {'input_tokens': 10}

def test_unknown_cause_is_rejected():
    cur = FakeCursor()
    with pytest.raises(ValueError):
        company_loss.record_overrun(cur, source='s', idempotency_key='k',
                                    quoted_usd=1, actual_usd=2, cause='whatever')

def test_rollup_groups_by_cause():
    cur = FakeCursor()
    cur.rows = [('metered_overrun', 2, Decimal('0.11')),
                ('budget_capped_shortfall', 1, Decimal('0.50'))]
    out = company_loss.rollup(cur)
    assert out['total_loss_usd'] == '0.61000000'
    assert out['total_events'] == 3
    assert set(out['by_cause']) == {'metered_overrun', 'budget_capped_shortfall'}

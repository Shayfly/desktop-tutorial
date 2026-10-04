import unittest
from decimal import Decimal

from omni_prod.subscription_store import PostgresSubscriptionService


class Ctx:
    def __init__(self, value): self.value=value
    def __enter__(self): return self.value
    def __exit__(self, *args): return False


class Cursor:
    def __init__(self):
        self.calls=[]
        self._fetch=[('u1','RESERVED',Decimal('2.00'))]
    def execute(self, sql, params=None):
        self.calls.append((' '.join(sql.split()), params))
        self.rowcount=1
    def fetchone(self):
        return self._fetch.pop(0) if self._fetch else None
    def __enter__(self): return self
    def __exit__(self,*args): return False


class Conn:
    def __init__(self, cur): self.cur=cur
    def transaction(self): return Ctx(self)
    def cursor(self): return self.cur


class Pool:
    def __init__(self, cur): self.cur=cur
    def connection(self): return Ctx(Conn(self.cur))


class SettlementTruthTests(unittest.TestCase):
    def test_unknown_actual_cost_stays_null_while_settled_basis_remains_conservative(self):
        cur=Cursor()
        service=PostgresSubscriptionService(pool=Pool(cur))
        service.settle(build_id='b1', actual_provider_cost_usd=None)
        update=[call for call in cur.calls if "UPDATE credit_reservations SET status='SETTLED'" in call[0]][0]
        params=update[1]
        self.assertIsNone(params[0])
        self.assertEqual(params[1], Decimal('2.00'))


if __name__=='__main__':
    unittest.main()

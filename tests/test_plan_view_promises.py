"""The plan view promises only what the code keeps (the owner, 2026-11-26, WAREHOUSE 136 option a).

max_projects (no slot limit on project creation), seats (no seat counted anywhere) and priority (one build queue,
no priority) were shown to customers in every plan; 'priority builds' and '5 seats' were feature lines. They are not
in the public view any more; the money fields stay; the internal view keeps everything. The real pricing catalogue,
customer_usage_view and V28Platform subscription views."""
import json
import unittest
from pathlib import Path

from omni_prod.pricing import (PLAN_CATALOG, PUBLIC_PLAN_FIELDS, UNKEPT_PLAN_FIELDS, PlanCode, catalog_payload,
                               customer_usage_view)
from omni_prod.v28_platform import V28Platform

ROOT = Path(__file__).resolve().parent.parent
MONEY = ('monthly_price_usd', 'annual_price_usd', 'included_credits', 'allowed_cost_classes')


class ThePlanView(unittest.TestCase):
    def test_no_unkept_promise_is_shown(self):
        for plan in catalog_payload()['plans']:
            with self.subTest(plan['code']):
                self.assertFalse(set(UNKEPT_PLAN_FIELDS) & set(plan), sorted(set(plan)))
                for line in plan['features']:
                    self.assertNotIn('priority build', line)
                    self.assertNotRegex(line, r'\bseats?\b')
        self.assertFalse(set(UNKEPT_PLAN_FIELDS) & set(PUBLIC_PLAN_FIELDS))

    def test_the_money_fields_stay(self):
        pro = next(p for p in catalog_payload()['plans'] if p['code'] == 'pro')
        for key in MONEY:
            self.assertIn(key, pro)
        self.assertEqual(pro['monthly_price_usd'], str(PLAN_CATALOG[PlanCode.PRO].monthly_price_usd))

    def test_the_internal_view_still_has_them(self):
        full = PLAN_CATALOG[PlanCode.STUDIO].to_dict()
        for key in UNKEPT_PLAN_FIELDS:
            self.assertIn(key, full)

    def test_a_customers_subscription_view_does_not_promise_them(self):
        p = V28Platform(token_secret='x' * 48)
        reg = p.register(email='plan-view@example.com', password='Passw0rd!Passw0rd')
        for view in (reg['subscription'], p.subscription(token=reg['token']),
                     customer_usage_view(p.subscriptions.snapshot(reg['user']['id']))):
            self.assertFalse(set(UNKEPT_PLAN_FIELDS) & set(view['plan']), json.dumps(view['plan'])[:200])

    def test_no_server_route_raises_a_project_limit(self):
        for path in (ROOT / 'omni_prod').rglob('*.py'):
            self.assertNotIn('project_limit_reached', path.read_text(encoding='utf-8'), str(path))


if __name__ == '__main__':
    unittest.main()

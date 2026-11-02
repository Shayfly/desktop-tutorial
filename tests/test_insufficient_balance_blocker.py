"""A balance too low is `insufficient_balance`, not `plan_cannot_authorize_cost` (founder 2026-11-02 19:26).

The owner had 15 credits for a 45-credit build and was told "your current plan does not authorize paid variable
cost". subscription_store.authorize already knew why ('monthly credits exhausted'); the plan preview threw it away.
Now: 'monthly credits exhausted' / 'paid-provider budget exhausted' -> insufficient_balance (BLOCKED_BUDGET) with the
reason; anything else the plan refuses (e.g. 'cost class not included in plan') stays plan_cannot_authorize_cost.
Runs without fastapi (the plan preview is called directly, as investor_app does).
"""
import json
import re
import shutil
import subprocess
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.creator_plan import build_plan_preview
from omni_prod.product_architect import ProductArchitect

PROMPT = 'Build a simple static page for a flower shop, no login, no personal data.'


def preview(reason, allowed=False):
    quote = SimpleNamespace(total_authorized_variable_usd=Decimal('0.35'))
    return build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='p', prompt=PROMPT,
        economics=lambda: quote, authorize_quote=lambda q: SimpleNamespace(allowed=allowed, reason=reason),
        durable_backend=True, infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL'})


class Split(unittest.TestCase):
    def test_low_balance_is_its_own_blocker(self):
        for reason in ('monthly credits exhausted', 'paid-provider budget exhausted'):
            with self.subTest(reason=reason):
                p = preview(reason)
                print(f'\n[{reason}]', [(b['code'], b['message']) for b in p['blockers']], p['execution_readiness'])
                self.assertEqual([b['code'] for b in p['blockers']], ['insufficient_balance'])
                self.assertIn(reason, p['blockers'][0]['message'])
                self.assertEqual((p['can_build'], p['execution_readiness'], p['build_authorization']),
                                 (False, 'BLOCKED_BUDGET', 'PRICED'))   # priced; the balance is what blocks

    def test_a_plan_refusal_is_still_plan_cannot_authorize_cost(self):
        for reason in ('cost class not included in plan', '', None):
            with self.subTest(reason=reason):
                p = preview(reason)
                self.assertEqual([b['code'] for b in p['blockers']], ['plan_cannot_authorize_cost'])
                self.assertEqual(p['execution_readiness'], 'BLOCKED')

    def test_an_allowed_quote_has_no_blocker(self):
        p = preview('authorized', allowed=True)
        self.assertEqual((p['blockers'], p['can_build']), ([], True))

    @unittest.skipUnless(shutil.which('node'), 'node is required to read app.js translations')
    def test_the_ui_has_both_sentences_in_both_languages(self):
        source = (Path(__file__).resolve().parents[1] / 'omni_prod/assets/app.js').read_text()
        translations = source[source.index('const T ='):source.index('const S =')]
        js = translations + '\nconsole.log(JSON.stringify([T.he.b_insufficient_balance, T.en.b_insufficient_balance, ' \
                            'T.he.b_plan_cannot_authorize_cost, T.en.b_plan_cannot_authorize_cost]));'
        he, en, he_plan, en_plan = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True,
                                                             check=True).stdout)
        print('[ui]', he, '|', en)
        self.assertIn('קרדיטים', he)
        self.assertIn('credits', en)
        self.assertNotEqual(he, he_plan)
        self.assertNotEqual(en, en_plan)


if __name__ == '__main__':
    unittest.main()

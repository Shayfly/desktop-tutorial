"""Michael 2026-11-14 (butcher): after the build "הסתיימה בהצלחה", the readiness strip said in red "לא ניתן להתחיל
בבנייה כרגע: תקציב הבנייה של המסלול לחודש הזה נגמר" -- a contradiction. The refusal concerns ANOTHER build.

Path: the plan the server returns for a refused build (creator_plan.build_plan_preview refused by the plan service's own
authorize() on the butcher's numbers after the build: Studio, spend 23.256424, quote 2.003; build_readiness.primary_blocker
as blocked_reason) -> app.js readinessView() in node, with the build row as the UI holds it."""
import json
import re
import shutil
import subprocess
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_readiness import primary_blocker
from omni_prod.creator_plan import build_plan_preview
from omni_prod.pricing import PlanCode, SubscriptionService
from omni_prod.product_architect import ProductArchitect

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


class _Quote:
    total_estimated_variable_usd = Decimal('2.003')
    total_authorized_variable_usd = Decimal('2.003')

    def to_dict(self):
        return {}


def refused_plan():
    subs = SubscriptionService()
    subs.assign_plan('usr_b', PlanCode.STUDIO)
    subs._get('usr_b').provider_spend_usd = Decimal('23.256424')          # creator_subscriptions after the build
    p = build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='prj_fV8kB7FwuNimGw',
        prompt='אתר תדמית לאטליז: פרטי קשר, שעות פתיחה, מוצרים וכפתור התקשרות', economics=lambda: _Quote(),
        durable_backend=True, infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL', 'reason': 'configured'},
        authorize_quote=lambda q: subs.authorize(user_id='usr_b', cost_class='standard', credits=500,
                                                 estimated_provider_cost_usd=q.total_authorized_variable_usd))
    p['blocked_reason'] = primary_blocker(p, 'he')
    return p


def view(build, plan, lang='he'):
    source = APP.read_text()
    translations = source[source.index('const T ='):source.index('const S =')]
    fn = re.search(r'function readinessView\(build, p\) \{.*?\n\}', source, re.S).group()
    term = re.search(r'const isTerminal = .*?;\n', source).group()
    js = (translations + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' + term + fn +
          f'\nconsole.log(JSON.stringify(readinessView({json.dumps(build)}, {json.dumps(plan, ensure_ascii=False)})));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js readinessView()')
class ReadinessAfterSuccess(unittest.TestCase):
    def test_a_finished_build_is_not_contradicted(self):
        plan = refused_plan()
        self.assertFalse(plan['can_build'])
        v = view({'status': 'ready', 'build_id': 'bld_83529c132a864075945080e9390484cb'}, plan)
        self.assertEqual(v['mode'], 'built')                                   # not the failure colour
        self.assertTrue(v['label'].startswith('הבנייה האחרונה הסתיימה בהצלחה.'))
        self.assertIn('בנייה נוספת לא אפשרית כרגע: ' + plan['blocked_reason']['message'], v['label'])
        self.assertNotIn('לא ניתן להתחיל בבנייה כרגע', v['label'])

    def test_before_any_build_the_refusal_stays_a_refusal(self):
        plan = refused_plan()
        self.assertEqual(view(None, plan)['mode'], 'blocked')
        self.assertEqual(view({'status': 'failed'}, plan)['mode'], 'blocked')
        self.assertEqual(view({'status': 'running'}, plan)['mode'], 'running')

    def test_the_strip_and_the_plan_tab_use_the_same_view(self):
        source = APP.read_text()
        self.assertIn('const { mode, label } = readinessView(S.build, p);', source)
        self.assertIn("class: `readinessStatus ${readinessView(S.build, p).mode === 'built' ? 'built'", source)
        self.assertIn("h('strong', {}, readinessView(S.build, p).mode === 'built'", source)


if __name__ == '__main__':
    unittest.main()

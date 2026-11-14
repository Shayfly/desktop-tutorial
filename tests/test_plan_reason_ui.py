"""Michael 2026-11-14 (b2): the plan tab's blocker list (app.js blockerTitle) names the subscription's own reason.

Butcher, 2026-11-14 19:12: the strip said "תקציב הבנייה של המסלול לחודש הזה נגמר" while the blocker list said "המסלול
הנוכחי לא מאשר עלות משתנה בתשלום" -- the same refusal, the list contradicting the strip. The list rendered by code only
and ignored `detail`. Path here: the real plan preview (creator_plan.build_plan_preview) refused by the plan service's own
authorize() on the butcher's numbers (Studio, spend 24.916146, quote 2.003) -> the server's banner
(build_readiness.primary_blocker) -> the list text, computed by app.js's own blockerTitle() in node."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from decimal import Decimal
from pathlib import Path

from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.build_readiness import PLAN_REASONS, REASONS, primary_blocker
from omni_prod.creator_plan import build_plan_preview
from omni_prod.pricing import PlanCode, SubscriptionService
from omni_prod.product_architect import ProductArchitect

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'
PROMPT = 'אתר תדמית לאטליז: פרטי קשר, שעות פתיחה, מוצרים וכפתור התקשרות'


class _Quote:
    total_estimated_variable_usd = Decimal('2.003')
    total_authorized_variable_usd = Decimal('2.003')

    def to_dict(self):
        return {}


def butcher_preview():
    subs = SubscriptionService()
    subs.assign_plan('usr_butcher', PlanCode.STUDIO)
    state = subs._get('usr_butcher')
    state.credits_used, state.provider_spend_usd = 3545, Decimal('24.916146')
    return build_plan_preview(
        architect=ProductArchitect(), repository=MemoryBuildContractRepository(), project_id='prj_fV8kB7FwuNimGw',
        prompt=PROMPT, economics=lambda: _Quote(), durable_backend=True,
        infrastructure_readiness={'kinds': {}}, image_readiness={'status': 'PARTIAL', 'reason': 'configured'},
        authorize_quote=lambda quote: subs.authorize(user_id='usr_butcher', cost_class='standard', credits=500,
                                                     estimated_provider_cost_usd=quote.total_authorized_variable_usd))


def js_plan_reason(blockers, lang):
    source = APP.read_text()
    translations = source[source.index('const T ='):source.index('const S =')]
    fns = [re.search(r'function %s\(.*?\n\}' % name, source, re.S).group()
           for name in ('blockerTitle', 'planReason', 'capabilityBlockMessage')]
    js = (translations + f'\nconst S={{lang:{json.dumps(lang)}}};\nfunction t(k){{return T[S.lang][k];}}\n' +
          '\n'.join(fns) +
          f'\nconsole.log(JSON.stringify({json.dumps(blockers)}.map(b => blockerTitle(b, {{infrastructure: []}}))));')
    return json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js planReason()')
class PlanReasonInTheList(unittest.TestCase):
    def test_the_list_says_what_the_banner_says(self):
        preview = butcher_preview()
        refusal = [b for b in preview['blockers'] if b['code'] == 'plan_cannot_authorize_cost']
        self.assertEqual([b['detail'] for b in refusal], ['paid-provider budget exhausted'])
        for i, lang in ((0, 'he'), (1, 'en')):
            banner = primary_blocker(preview, lang)['message']
            listed = js_plan_reason(refusal, lang)
            self.assertEqual(listed, [PLAN_REASONS['paid-provider budget exhausted'][i]])
            self.assertEqual(listed, [banner])
        self.assertNotIn('עלות משתנה', ' '.join(js_plan_reason(refusal, 'he')))
        from tests.evidence_notice import notice
        notice('plan reason', f"butcher refusal: banner and list both say {js_plan_reason(refusal, 'he')[0]}")

    def test_every_server_reason_has_the_same_words_in_the_ui(self):
        blockers = [{'code': 'plan_cannot_authorize_cost', 'detail': k} for k in sorted(PLAN_REASONS)]
        for i, lang in ((0, 'he'), (1, 'en')):
            self.assertEqual(js_plan_reason(blockers, lang), [PLAN_REASONS[k][i] for k in sorted(PLAN_REASONS)])

    def test_an_unknown_reason_gets_the_servers_generic_line(self):
        blockers = [{'code': 'plan_cannot_authorize_cost', 'detail': ''},
                    {'code': 'plan_cannot_authorize_cost', 'detail': 'internal margin text'}]
        self.assertEqual(js_plan_reason(blockers, 'he'), [REASONS['plan_cannot_authorize_cost'][1]] * 2)
        self.assertEqual(js_plan_reason(blockers, 'en'), [REASONS['plan_cannot_authorize_cost'][2]] * 2)

    def test_the_plan_tab_renders_its_list_through_blocker_title(self):
        # renderPlan's list maps p.blockers through `title`, which is blockerTitle; the behaviour is tested above
        # on blockerTitle itself. This guards only that renderPlan did not get its own copy again.
        source = APP.read_text()
        self.assertIn('const title = b => blockerTitle(b, p);', source)


if __name__ == '__main__':
    unittest.main()

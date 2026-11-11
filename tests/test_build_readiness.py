"""79 (Michael 2026-11-11): `can_build=false` names ONE reason from a closed list; the chat never says "ready" when
the banner says "blocked"."""
from __future__ import annotations

import pathlib
import re
import unittest

from omni_prod import build_readiness as R
from omni_prod import discovery as d

ROOT = pathlib.Path(__file__).resolve().parents[1] / 'omni_prod'


def emitted_codes() -> set[str]:
    """Every literal blocker code creator_plan and the execution-plan gate can put in a preview."""
    plan = (ROOT / 'creator_plan.py').read_text()
    codes = set(re.findall(r'"code": "([a-z_]+)"', plan)) | set(re.findall(r'quote_error_code = "([a-z_]+)"', plan))
    codes |= set(re.findall(r'quote_error, quote_error_code = [^,]+, "([a-z_]+)"', plan))
    app = (ROOT / 'investor_app.py').read_text()
    gate = re.search(r"def _apply_execution_plan_gate.*?not in \{(.*?)\}", app, re.S).group(1)
    codes |= set(re.findall(r"'([a-z_]+)'", gate))
    return codes


class ClosedList(unittest.TestCase):
    def test_every_emitted_code_is_in_the_list(self):
        codes = emitted_codes()
        self.assertGreaterEqual(len(codes), 10, codes)        # the scan itself works
        self.assertEqual({c for c in codes if R.reason_key(c) is None}, set())

    def test_dynamic_codes_map_to_their_family(self):
        self.assertEqual(R.reason_key('infrastructure_database_not_configured'), 'infrastructure')
        self.assertEqual(R.reason_key('image_provider_not_configured'), 'image_provider')

    def test_every_subscription_refusal_has_wording(self):
        store = (ROOT / 'subscription_store.py').read_text()
        for reason in R.PLAN_REASONS:
            self.assertIn(reason, store)

    def test_only_listed_refusal_reasons_leave_creator_plan(self):
        plan = (ROOT / 'creator_plan.py').read_text()
        self.assertIn('str(exc) if str(exc) in PLAN_REASONS else ""', plan)   # margins never reach the customer

    def test_every_reason_has_both_languages_and_a_next_step(self):
        for code, (family, he, en, nhe, nen) in R.REASONS.items():
            self.assertIn(family, R._ORDER, code)
            self.assertTrue(all([he, en, nhe, nen]), code)


class PrimaryBlocker(unittest.TestCase):
    def test_ready_is_none(self):
        self.assertIsNone(R.primary_blocker({'can_build': True}))

    def test_three_families_say_three_different_things(self):
        req = R.primary_blocker({'can_build': False, 'status': 'NEEDS_CLARIFICATION', 'blockers': [],
                                 'clarification_questions': [{'question': 'האם צריך התחברות?'}]})
        gate = R.primary_blocker({'can_build': False, 'status': 'READY', 'blockers': [{'code': 'spec_not_approved'}]})
        quote = R.primary_blocker({'can_build': False, 'status': 'READY',
                                   'blockers': [{'code': 'plan_cannot_authorize_cost',
                                                 'detail': 'paid-provider budget exhausted'}]})
        self.assertEqual([b['family'] for b in (req, gate, quote)], ['requirements', 'gate', 'quote'])
        self.assertEqual(len({b['message'] for b in (req, gate, quote)}), 3)
        self.assertEqual(len({b['next'] for b in (req, gate, quote)}), 3)
        self.assertIn('האם צריך התחברות?', req['message'])
        self.assertIn('תקציב הבנייה', quote['message'])

    def test_requirements_before_gate_before_price(self):
        b = R.primary_blocker({'can_build': False, 'status': 'READY',
                               'blockers': [{'code': 'cost_quote_unavailable'}, {'code': 'brief_stale'}]})
        self.assertEqual(b['reason'], 'brief_stale')

    def test_an_unknown_code_is_never_shown_raw(self):
        b = R.primary_blocker({'can_build': False, 'status': 'READY', 'blockers': [{'code': 'weird_new_thing'}]})
        self.assertEqual(b['reason'], 'cost_quote_unavailable')
        self.assertNotIn('weird', b['message'])

    def test_unpriced_capability_is_named(self):
        b = R.primary_blocker({'can_build': False, 'status': 'READY',
                               'blockers': [{'code': 'cost_quote_unknown', 'capability_keys': ['auth.login']}]})
        self.assertIn('auth.login', b['message'])


class ChatAgreesWithBanner(unittest.TestCase):
    """If admission refuses, the chat says the banner's reason and offers no approve-build button."""

    def run_to_gate2(self, admission):
        from omni_prod.conversation.supervisor import ConversationSupervisor
        from tests.test_conversation_os import MemoryBriefs, MemoryConversationStore
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {},
                                     admission=admission)
        sup.turn(project_id='p1', account_id='a1', message='אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון')
        sup.turn(project_id='p1', account_id='a1', answers={'personal_data': 'yes'}, lang='he')
        sup.turn(project_id='p1', account_id='a1', answers={'access_scope': 'internal_link'}, lang='he')
        t4 = sup.turn(project_id='p1', account_id='a1', message='תחליט אתה')
        self.assertTrue(t4.brief_row.complete)
        return sup.approve_spec(project_id='p1', account_id='a1', brief_fingerprint=t4.brief_row.fingerprint, lang='he')

    def test_blocked_admission_wins(self):
        blocked = {'can_build': False, 'status': 'READY',
                   'blockers': [{'code': 'plan_cannot_authorize_cost', 'detail': 'paid-provider budget exhausted'}]}
        seen = []
        t = self.run_to_gate2(lambda pid, row, lang: seen.append((pid, lang)) or blocked)
        self.assertEqual(seen, [('p1', 'he')])
        self.assertNotIn('approve_build', [a['type'] for a in t.actions])
        self.assertIn('לא ניתן להתחיל בבנייה כרגע', t.reply)
        self.assertIn('תקציב הבנייה של המסלול לחודש הזה נגמר', t.reply)

    def test_typing_approve_gets_no_button_the_banner_refuses(self):
        blocked = {'can_build': False, 'status': 'READY', 'blockers': [{'code': 'cost_quote_unavailable'}]}
        self.run_to_gate2(lambda pid, row, lang: blocked)
        from omni_prod.conversation.supervisor import ConversationSupervisor
        sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {},
                                     admission=lambda pid, row, lang: blocked)
        t = sup.turn(project_id='p1', account_id='a1', message='מאשר, תתחיל לבנות', lang='he')
        self.assertNotIn('approve_build', [a['type'] for a in t.actions])

    def test_allowed_admission_keeps_the_button(self):
        t = self.run_to_gate2(lambda pid, row, lang: {'can_build': True})
        self.assertEqual([a['type'] for a in t.actions], ['show_plan', 'approve_build'])
        self.assertNotIn('לא ניתן להתחיל', t.reply)

    def test_a_crashing_check_never_silences_the_chat(self):
        def boom(*a):
            raise RuntimeError('x')
        with self.assertLogs('omni_prod.conversation.supervisor', level='WARNING'):
            t = self.run_to_gate2(boom)
        self.assertEqual([a['type'] for a in t.actions], ['show_plan', 'approve_build'])


if __name__ == '__main__':
    unittest.main()

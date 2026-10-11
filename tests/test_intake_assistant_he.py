"""Hebrew-first intake assistant (prepared, not activated): fail-closed mode
resolution, budget caps that a call can never overshoot, truthful UI label,
Hebrew-aware evidence validation, bounded model calls. $0: test doubles only."""
from __future__ import annotations

import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.intake import mode as M
from omni_prod.intake.interpreter import (MAX_MESSAGE_CHARS, MAX_OUTPUT_TOKENS, PROMPT_VERSION, SYSTEM,
                                          DeterministicInterpreter, ModelInterpreter, normalize_for_evidence,
                                          validate_model_output)

ALL = {'OMNI_INTAKE_MODEL': '1', 'OMNI_INTAKE_VIA_WORKER': '1', 'OMNI_INTAKE_MODEL_BUDGET_USD': '0.05',
       'OMNI_INTAKE_DAILY_BUDGET_USD': '0.50', 'OMNI_INTAKE_CALL_BUDGET_USD': '0.005'}
CLEAR = {k: '' for k in ALL}


def resolve(env, **kw):
    with mock.patch.dict(os.environ, {**CLEAR, **env}):
        return M.resolve(**kw)


class ModeTests(unittest.TestCase):
    def test_fully_authorized_routes_through_worker(self):
        m = resolve(ALL)
        self.assertEqual((m.mode, m.paid), (M.MODEL_WORKER, True))

    def test_every_missing_condition_fails_closed(self):
        for key in ('OMNI_INTAKE_MODEL', 'OMNI_INTAKE_MODEL_BUDGET_USD', 'OMNI_INTAKE_DAILY_BUDGET_USD'):
            with self.subTest(missing=key):
                self.assertEqual(resolve({**ALL, key: ''}).mode, M.DETERMINISTIC)
        for bad in ('abc', '-1', 'NaN', 'Infinity', '0', '-0.01'):
            with self.subTest(value=bad):
                self.assertEqual(resolve({**ALL, 'OMNI_INTAKE_DAILY_BUDGET_USD': bad}).mode, M.DETERMINISTIC)
                self.assertEqual(resolve({**ALL, 'OMNI_INTAKE_MODEL_BUDGET_USD': bad}).mode, M.DETERMINISTIC)
        self.assertEqual(resolve({**ALL, 'OMNI_INTAKE_MODEL': 'true'}).mode, M.DETERMINISTIC)   # only literal "1"

    def test_a_call_can_never_overshoot_the_caps(self):
        self.assertEqual(resolve(ALL, project_spent=Decimal('0.045')).mode, M.MODEL_WORKER)      # 0.045 + 0.005 == cap
        m = resolve(ALL, project_spent=Decimal('0.0451'))
        self.assertEqual((m.mode, m.reason), (M.DETERMINISTIC, 'project intake budget exhausted'))
        m = resolve(ALL, daily_spent=Decimal('0.4951'))
        self.assertEqual((m.mode, m.reason), (M.DETERMINISTIC, 'daily intake budget exhausted'))

    def test_route_selection(self):
        no_worker = {**ALL, 'OMNI_INTAKE_VIA_WORKER': ''}
        self.assertEqual(resolve(no_worker).mode, M.DETERMINISTIC)                    # no route at all
        m = resolve(no_worker, has_direct_gateway=True)                             # would bypass reservations
        self.assertEqual(m.mode, M.DETERMINISTIC)
        self.assertIn('reservations', m.reason)

    def test_cost_estimate_uses_the_source_backed_price(self):
        est = M.estimate_message_cost()
        self.assertEqual(est['model'], 'gemini-3.1-flash-lite')
        # (2200 x $0.25 + 700 x $1.50) / 1M = $0.0016
        self.assertEqual(est['usd_per_message'], '0.001600')
        self.assertTrue(est['price_source'].startswith('https://ai.google.dev/'))
        self.assertEqual(M.estimate_message_cost('no-such-model')['status'], 'PRICE_UNVERIFIED')
        self.assertLessEqual(Decimal(est['usd_per_message']), M.DEFAULT_CALL_RESERVE)   # reserve covers one call
        for model in ('gemini-3.1-flash-lite', 'gemini-3.5-flash-lite'):                 # verified conversation models
            with self.subTest(model=model):
                self.assertLessEqual(Decimal(M.estimate_message_cost(model)['usd_per_message']),
                                     M.DEFAULT_CALL_RESERVE)


class SupervisorBudgetTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.conversation.store import MemoryConversationStore
        from omni_prod.conversation.supervisor import ConversationSupervisor
        from omni_prod.intake.interpreter import DeterministicInterpreter
        from tests.test_conversation_os import MemoryBriefs
        self.calls = []
        calls = self.calls

        class FakeModel:
            def interpret(self, message, brief=None):
                calls.append(message)
                return DeterministicInterpreter().interpret(message, brief)
        fake = FakeModel()
        self.store = MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=MemoryBriefs(), store=self.store, worker_interpreter=fake)

    def turn(self, env, msg, project='p'):
        with mock.patch.dict(os.environ, {**CLEAR, **env}):
            self.sup.turn(project_id=project, account_id='a', message=msg)

    def test_switch_off_means_no_enqueue_and_no_db_reads(self):
        with mock.patch.object(self.store, 'daily_cost', side_effect=AssertionError('read while off')):
            self.turn({}, 'מערכת לניהול ציוד')
        self.assertEqual(self.calls, [])

    def test_daily_cap_across_projects_stops_the_model(self):
        self.store.add_message(project_id='other', account_id='a', role='assistant', content='x',
                               cost_usd=Decimal('0.4960'))
        self.turn(ALL, 'מערכת לניהול ציוד', project='p')
        self.assertEqual(self.calls, [])                       # 0.496 + 0.005 > 0.50
        self.turn({**ALL, 'OMNI_INTAKE_DAILY_BUDGET_USD': '1'}, 'מערכת לניהול ציוד', project='p')
        self.assertEqual(self.calls, ['מערכת לניהול ציוד'])

    def test_old_spend_leaves_the_24h_window(self):
        row = self.store.add_message(project_id='other', account_id='a', role='assistant', content='x',
                                     cost_usd=Decimal('0.49'))
        row['created_at'] -= 90000
        self.assertEqual(self.store.daily_cost(), Decimal('0'))


class HebrewEvidenceTests(unittest.TestCase):
    MSG = 'אני צריך אַפְּלִיקַצְיָה לניהול השאלת ציוד לצוות של צה״ל, ‏בלי התחברות, בעברית'

    def props(self, *evidence, field='login', value='none'):
        raw = {'language': 'he', 'product_family': 'web_app',
               'proposals': [{'field': field, 'value': value, 'confidence': 'high', 'evidence': e} for e in evidence]}
        it, _ = validate_model_output(raw, self.MSG)
        return it

    def test_harmless_hebrew_variants_are_not_dropped(self):
        for ev in ('בלי התחברות', 'אפליקציה לניהול', 'צה"ל', "צה''ל".replace("''", '״'), 'בלי  התחברות',
                   'בלי‏ התחברות'):
            with self.subTest(evidence=ev):
                self.assertEqual(len(self.props(ev).proposals), 1, ev)

    def test_fabricated_or_empty_evidence_is_still_dropped(self):
        for ev in ('עם התחברות', 'login required', '‏‎', 'ב', '', 'בלי התחברות!'):
            with self.subTest(evidence=ev):
                self.assertEqual(self.props(ev).proposals, [], ev)

    def test_letters_and_final_forms_are_never_rewritten(self):
        self.assertNotEqual(normalize_for_evidence('שלום'), normalize_for_evidence('שלומ'))
        self.assertEqual(normalize_for_evidence('שָׁלוֹם'), 'שלום')

    def test_deterministic_path_stays_hebrew(self):
        it = DeterministicInterpreter().interpret('אני רוצה אתר לחנות פרחים בלי הרשמה')
        self.assertEqual(it.language, 'he')


class ModelCallBoundsTests(unittest.TestCase):
    def test_prompt_is_hebrew_first_and_calls_are_bounded(self):
        self.assertIn('Hebrew as the primary language', SYSTEM)
        self.assertIn('never translate', SYSTEM)
        self.assertEqual(PROMPT_VERSION, 'intake-prompt/2-he-first')

        class Gateway:
            def __init__(self):
                self.seen = None

            def complete_json(self, **kw):
                self.seen = kw
                return {'language': 'he', 'product_family': 'web_app', 'proposals': []}
        g = Gateway()
        ModelInterpreter(g).interpret('א' * 10000)
        self.assertEqual(len(g.seen['user']), MAX_MESSAGE_CHARS)
        self.assertEqual(g.seen['max_tokens'], MAX_OUTPUT_TOKENS)
        self.assertEqual(g.seen['task'], 'conversation')

    def test_reserved_worker_call_carries_the_same_bounds(self):
        from omni_prod.intake import budget as B
        from tests.test_intake_worker_route import FakeService, interp
        svc = FakeService(never_settles=True)
        interp(svc, wait=0.2).interpret('ב' * 9000)
        payload = svc.reserved[0]['payload']
        self.assertEqual((len(payload['user']), payload['max_tokens']), (MAX_MESSAGE_CHARS, MAX_OUTPUT_TOKENS))
        self.assertEqual((payload['system'], payload['prompt_version']), (SYSTEM, PROMPT_VERSION))
        quote = svc.reserved[0]['quote_']
        self.assertEqual(quote.envelope['models'][0]['output_tokens_bound'], MAX_OUTPUT_TOKENS)
        self.assertIsInstance(quote, B.Quote)


class TruthfulLabelTests(unittest.TestCase):
    def setUp(self):
        try:
            from omni_prod import investor_app
        except ModuleNotFoundError as exc:
            self.skipTest(str(exc))
        self.app = investor_app

    def test_label_is_deterministic_unless_a_model_would_really_answer(self):
        with mock.patch.dict(os.environ, {**CLEAR, 'OMNI_INTAKE_MODEL': '1'}):
            self.assertEqual(self.app._intake_mode('p').mode, M.DETERMINISTIC)   # switch on, no budget
        with mock.patch.dict(os.environ, CLEAR):
            self.assertEqual(self.app._intake_mode('p').mode, M.DETERMINISTIC)
        # fully authorized but spend cannot be read (no durable store here) -> fail closed, no exception
        with mock.patch.dict(os.environ, {**CLEAR, **ALL}):
            m = self.app._intake_mode('p')
        self.assertEqual(m.mode, M.DETERMINISTIC)
        self.assertIn('spend unavailable', m.reason)

    def test_spend_is_not_read_when_no_model_could_run(self):
        def boom():
            raise AssertionError('spend read')
        with mock.patch.dict(os.environ, {**CLEAR, 'OMNI_INTAKE_MODEL': '1'}):
            self.assertEqual(M.resolve_with_spend(boom).mode, M.DETERMINISTIC)
        with mock.patch.dict(os.environ, {**CLEAR, **ALL}):
            self.assertEqual(M.resolve_with_spend(lambda: (Decimal('0'), Decimal('0'))).mode, M.MODEL_WORKER)


if __name__ == '__main__':
    unittest.main()

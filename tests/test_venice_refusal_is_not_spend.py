"""A provider refusal (Venice 402 insufficient credit, 401 key refused) is not spend, not a turn, and not "busy".

Rehearsals 44445874611 and 44453949615 (2026-11-19): Venice answered 402 "insufficient credit". The refusal was
recorded as a contacted call with no usage, so its cost was UNKNOWN -- held at the worst case and counted as a turn --
and four refusals closed a conversation at its $0.15 cap without one model answer. The customer read "the model
provider is busy, send again" while sending again could change nothing. Real VeniceIntakeGateway, real meter, real
supervisor; only Venice's HTTP is a fake.
"""
import os
import sys
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod import conversation_rehearsal as R
from omni_prod.conversation.supervisor import _TXT
from omni_prod.intake import reservation_worker as W
from omni_prod.intake.interpreter import ModelInterpreter
from omni_prod.providers import venice as VC
from omni_prod.providers import venice_gateway as V

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_agent_sonnet import KEY, TheRehearsalMeasuresTheAgent, Venice, models   # noqa: E402
from test_conversation_rehearsal import Scripted                                             # noqa: E402

HE = _TXT['he']


class Refusing(Venice):
    def __init__(self, listed, status):
        super().__init__(listed)
        self.status = status

    def __call__(self, method, url, headers, body, timeout):
        if method == 'POST':
            self.calls.append((method, body))
            return self.status, {'error': 'refused'}
        return super().__call__(method, url, headers, body, timeout)


def gateway(venice):
    """The gateway the worker builds for a reservation (build_gateway), on Venice's fake HTTP."""
    q = R.agent_quote(TheRehearsalMeasuresTheAgent.PROD)
    real = V.VeniceIntakeGateway
    with mock.patch.dict(os.environ, KEY), \
            mock.patch.object(V, 'VeniceIntakeGateway', lambda qq, **kw: real(qq, env=KEY, transport=venice, **kw)):
        return W.build_gateway(Decimal('0.05'), tuple(q['allowed_models']), quote=q)


class TheRefusalCostsNothing(unittest.TestCase):
    def test_402_and_401_are_metered_as_not_contacted(self):
        for status, exc in ((402, VC.VeniceInsufficientCredit), (401, VC.VeniceAuthError)):
            with self.subTest(status=status):
                venice = Refusing(models('gemini-3-5-flash-lite', 'claude-haiku-5-5'), status)
                g = gateway(venice)
                mark = W.ledger_mark(g)
                with self.assertRaises(exc):
                    g.complete_json(system='S', user='U', max_tokens=500, call_id='c1')
                self.assertEqual(len(venice.sent_model), 1)                  # it was sent, and refused
                m = W.meter(g, {'max_tokens': 500}, call_id='c1', before=mark)
                self.assertEqual((m['contacted'], m['cost_state'], m['actual_usd']),
                                 (False, 'CONFIRMED_ZERO', Decimal('0')))

    def test_a_server_error_after_sending_is_still_unknown(self):
        # only a refusal is known to cost nothing: a 500 after the request may have been processed stays UNKNOWN
        for model in ('gemini-3-5-flash-lite', 'claude-haiku-5-5'):
            with self.subTest(model=model):
                venice = Refusing(models(model), 500)
                g = gateway(venice)
                mark = W.ledger_mark(g)
                with self.assertRaises(VC.VeniceError):
                    g.complete_json(system='S', user='U', max_tokens=500, call_id='c1')
                self.assertEqual(venice.sent_model, [model])
                self.assertEqual(W.meter(g, {'max_tokens': 500}, call_id='c1', before=mark)['cost_state'], 'UNKNOWN')

    def test_refusals_never_fill_the_conversation_cap(self):
        g = R.ProductionPathGateway(R.agent_quote(TheRehearsalMeasuresTheAgent.PROD), cap_usd=Decimal('0.15'),
                                    max_turns=8)
        venice = Refusing(models('gemini-3-5-flash-lite', 'claude-haiku-5-5'), 402)
        real = V.VeniceIntakeGateway
        with mock.patch.dict(os.environ, KEY), \
                mock.patch.object(V, 'VeniceIntakeGateway', lambda q, **kw: real(q, env=KEY, transport=venice, **kw)):
            interp = ModelInterpreter(g)
            outs = [interp.interpret('אתר לחנות פרחים בחיפה') for _ in range(10)]
        self.assertEqual((g.spent, g.turns), (Decimal('0'), 0))
        self.assertTrue(all(o.limit is None for o in outs))                 # ten refusals, never "the cap"
        self.assertEqual(len(g.call_errors), 10)
        self.assertEqual(venice.sent_model, ['gemini-3-5-flash-lite'] * 10)


class TheCustomerIsToldTheTruth(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1', 'OMNI_INTAKE_MODEL': '1'})
        p.start()
        self.addCleanup(p.stop)

    def reply(self, note):
        class Failed(Scripted):
            def interpret(self, message, brief=None):
                out = super().interpret(message, brief)
                out.interpreter, out.reply = 'deterministic', ''
                out.dropped.append(note)
                return out
        sup = R._Supervisor(Failed())
        return sup.turn(project_id='r', account_id='a', message='אתר לחנות פרחים עם משלוחים בחיפה', lang='he').reply

    def test_a_refusal_says_refused_not_busy(self):
        for note in ('model unavailable: VeniceInsufficientCredit',
                     'model reply not available: VeniceInsufficientCredit: Venice: insufficient credit (402)'):
            with self.subTest(note=note), self.assertLogs('omni_prod.conversation.supervisor', 'ERROR') as logs:
                text = self.reply(note)
            self.assertTrue(text.startswith(HE['model_refused'][:20]), text)
            self.assertNotIn('העומס', text)
            self.assertIn('INTAKE_PROVIDER_REFUSED', logs.output[0])

    def test_a_slow_model_is_still_busy(self):
        text = self.reply('model reply not available in time; cost settles on the reservation')
        self.assertTrue(text.startswith(HE['model_unavailable'][:20]), text)


if __name__ == '__main__':
    unittest.main()

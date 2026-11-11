"""OMNI_VENICE_ALLOWED_MODELS (owner 2026-10-28): "Gemini family only through Venice, no Qwen".

The model list below has the shape and the prices of Venice's live /models answer (read 2026-10-28):
gemini-3-8-flash is "anonymized" at 0.9375 / 4.6875 USD per 1M tokens; Qwen models are "private" and CHEAPER
(qwen3-6-35b-a3b 0.1 / 1). Before this change the trait rule chose the cheapest PRIVATE model, so a Gemini
allowlist was impossible and Qwen ran. The list is enforced at two points, and each one alone rejects Qwen:
  1. the selection   -- venice.select_model(allowed=...)
  2. the pricing     -- VeniceIntakeGateway only exposes listed models under the reservation's ceiling
Fail closed: no list, or no listed model offered, is an explicit error before any chat request -- never Qwen.
"""
from __future__ import annotations

import os
import unittest
from decimal import Decimal
from unittest import mock

from omni_prod.intake import budget as B
from omni_prod.intake import reservation_worker as W
from omni_prod.providers import venice as V
from omni_prod.providers import venice_gateway as VG

GEMINI = 'gemini-3-8-flash'
QWEN = 'qwen3-6-35b-a3b'


def item(mid, privacy, cin, cout, tools=True, e2ee=False):
    return {'id': mid, 'model_spec': {'privacy': privacy,
                                      'capabilities': {'supportsFunctionCalling': tools, 'supportsE2EE': e2ee},
                                      'pricing': {'input': {'usd': cin, 'diem': cin}, 'output': {'usd': cout, 'diem': cout}}}}


LIVE = {'data': [item(GEMINI, 'anonymized', 0.9375, 4.6875),
                 item('gemini-3-5-flash-lite', 'anonymized', 0.375, 3.125),
                 item(QWEN, 'private', 0.1, 1),
                 item('e2ee-qwen-2-5-7b-p', 'private', 0.05, 0.15, tools=False, e2ee=True)]}
MODELS = [V.VeniceModel.from_api(m) for m in LIVE['data']]
KEY = {'VENICE_API_KEY1': 'test-key'}
ONLY_GEMINI = {**KEY, V.ALLOWED_ENV: GEMINI}


class Fake:
    def __init__(self):
        self.calls = []

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append((method, url, body))
        if method == 'GET':
            return 200, LIVE
        return 200, {'choices': [{'message': {'content': '{"ok": true}'}}],
                     'usage': {'prompt_tokens': 10, 'completion_tokens': 5}, 'cost': {'usd': '0.0001'}}

    @property
    def chats(self):
        return [c for c in self.calls if c[0] == 'POST']


class TheSelection(unittest.TestCase):
    def test_the_listed_gemini_is_chosen_over_a_cheaper_private_qwen(self):
        self.assertEqual(V.select_model(MODELS, allowed=(GEMINI,)).id, GEMINI)

    def test_qwen_in_the_price_range_is_rejected_by_the_selection(self):
        with self.assertRaises(V.NoAllowedModel):                      # listed id not offered: fail closed
            V.select_model([m for m in MODELS if m.id != GEMINI], allowed=(GEMINI,))

    def test_a_listed_model_must_be_private_or_anonymized(self):
        odd = [V.VeniceModel(GEMINI, 'unknown', False, True, Decimal('1'), Decimal('1'))]
        with self.assertRaises(V.NoAllowedModel):
            V.select_model(odd, allowed=(GEMINI,))

    def test_without_a_list_the_old_trait_rule_is_unchanged(self):
        self.assertEqual(V.select_model(MODELS).id, 'e2ee-qwen-2-5-7b-p')

    def test_the_list_is_exact_ids(self):
        self.assertEqual(V.allowed_models({V.ALLOWED_ENV: f' {GEMINI} , {GEMINI},x '}), (GEMINI, 'x'))
        self.assertIsNone(V.allowed_models({}))
        for bad in ('gemini-*', 'gemini 3', ','):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                V.allowed_models({V.ALLOWED_ENV: bad})

    def test_the_truth_tag_says_anonymized_not_private(self):
        tag = V.truth_tag(V.select_model(MODELS, allowed=(GEMINI,)))
        self.assertEqual((tag['model_private'], tag['privacy'], tag['end_to_end_encrypted']),
                         (False, 'anonymized', False))


class ThePricing(unittest.TestCase):
    def gw(self, ceiling=('1', '5'), env=ONLY_GEMINI, allowed=None, fake=None):
        return VG.VeniceIntakeGateway(Decimal('0.05'), ceiling=tuple(Decimal(x) for x in ceiling), env=env,
                                      transport=fake or Fake(), allowed=allowed)

    def test_the_pricing_layer_only_sees_listed_models(self):
        seen = [m.id for m in self.gw().client.models()]
        self.assertEqual(seen, [GEMINI])                               # Qwen (0.1/1, inside 1,5) is not even seen

    def test_the_call_goes_to_the_listed_gemini(self):
        fake = Fake()
        g = self.gw(fake=fake)
        g.complete_json(system='S', user='U', max_tokens=100)
        self.assertEqual([c[2]['model'] for c in fake.chats], [GEMINI])

    def test_a_ceiling_below_the_listed_model_fails_closed_without_contact(self):
        fake = Fake()
        g = self.gw(ceiling=('0.5', '3.5'), fake=fake)                  # Qwen fits, Gemini does not
        with self.assertRaises(V.NoAllowedModel):
            g.complete_json(system='S', user='U', max_tokens=100)
        self.assertEqual(fake.chats, [])

    def test_no_list_refuses_to_build(self):
        for env in (KEY, {**KEY, V.ALLOWED_ENV: ''}, {**KEY, V.ALLOWED_ENV: '   '}):   # missing or empty
            with self.subTest(env=env), self.assertRaises(V.NoAllowedModel):
                self.gw(env=env)

    def test_the_reservations_list_wins_over_the_workers_env(self):
        g = self.gw(env={**KEY, V.ALLOWED_ENV: QWEN}, allowed=(GEMINI,))
        self.assertEqual([m.id for m in g.client.models()], [GEMINI])


class TheReservationPath(unittest.TestCase):
    ENV = {'OMNI_INTAKE_PROVIDER': 'venice', VG.CEILING_ENV: '1,5'}

    def test_no_venice_quote_without_the_list(self):
        for extra in ({}, {V.ALLOWED_ENV: ''}, {V.ALLOWED_ENV: ','}):        # missing, empty, malformed
            with self.subTest(extra=extra), mock.patch.dict(os.environ, {**self.ENV, **extra}, clear=True):
                with self.assertRaises(B.QuoteUnavailable):                   # the Venice route is not taken
                    B.quote(system='S', user='U', max_tokens=100)

    def test_the_recommended_ceiling_covers_the_live_price(self):
        # live /models 2026-10-28: gemini-3-8-flash 0.9375 / 4.6875; ceiling = price x 1.2
        cin, cout = VG.price_ceiling({VG.CEILING_ENV: '1.125,5.625'})
        g = next(m for m in MODELS if m.id == GEMINI)
        self.assertTrue(g.input_usd_per_m <= cin and g.output_usd_per_m <= cout)

    def test_the_quote_carries_the_list_and_the_worker_runs_on_it(self):
        with mock.patch.dict(os.environ, {**self.ENV, V.ALLOWED_ENV: GEMINI}, clear=True):
            q = B.quote(system='S', user='U', max_tokens=100)
        self.assertEqual(q.envelope['venice_allowed_models'], [GEMINI])
        self.assertEqual(q.envelope['venice_ceiling_usd_per_m'], ['1', '5'])
        with mock.patch.dict(os.environ, {**KEY, V.ALLOWED_ENV: QWEN}, clear=True):   # the worker env drifted
            g = W.build_gateway(q.amount_usd, (), quote=dict(q.envelope))
        self.assertEqual(g.allowed, (GEMINI,))

    def test_an_old_quote_and_no_worker_list_is_released_not_run(self):
        quote = {'provider': 'venice', 'venice_ceiling_usd_per_m': ['1', '5'], 'max_tokens': 100}
        with mock.patch.dict(os.environ, KEY, clear=True):
            with self.assertRaises(V.NoAllowedModel):
                W.build_gateway(Decimal('0.05'), (), quote=quote)


if __name__ == '__main__':
    unittest.main()

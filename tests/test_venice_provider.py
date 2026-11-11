"""Venice provider (owner brief 2026-10-26): loud on a missing key, model by trait, an honest truth tag, enforced
budget caps, no key in logs or exports, and the customer's text direction. Only the HTTP transport is replaced."""
import io
import json
import logging
import threading
import unittest
from decimal import Decimal

from omni_prod.providers import venice as V

KEY = 'test-only-venice-key-' + 'Z' * 30          # synthetic; never a real key


def model(id, privacy='private', e2ee=False, tools=False, i=1, o=2):
    return {'id': id, 'type': 'text', 'model_spec': {'privacy': privacy,
            'capabilities': {'supportsE2EE': e2ee, 'supportsFunctionCalling': tools},
            'pricing': {'input': {'usd': i, 'diem': i}, 'output': {'usd': o, 'diem': o}}}}


MODELS = [model('cheap-anon', privacy='anonymized', i=0.1, o=0.1), model('plain-private', i=0.5, o=1),
          model('e2ee-private', e2ee=True, i=0.7, o=1.4), model('tools-private', tools=True, i=0.6, o=1.2)]


class Transport:
    def __init__(self, chat=None, models=MODELS):
        self.calls, self.chat_answers, self.models = [], list(chat or []), models

    def __call__(self, method, url, headers, body, timeout):
        self.calls.append({'method': method, 'url': url, 'headers': dict(headers), 'body': body, 'timeout': timeout})
        if url.endswith('/models?type=text'):
            return 200, {'data': self.models}
        answer = self.chat_answers.pop(0) if self.chat_answers else (200, ok())
        if isinstance(answer, Exception):
            raise answer
        return answer


def ok(text='שלום, נתחיל', cost='0.0004'):
    return {'choices': [{'message': {'content': text}}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5},
            'cost': {'usd': cost}}


def client(transport, per='0.05', total='0.10'):
    return V.VeniceClient({'VENICE_API_KEY1': KEY}, budget=V.VeniceBudget(Decimal(per), Decimal(total)),
                          transport=transport, sleep=lambda s: None)


def say(c, conv='c1', text='אני רוצה אתר', lang='he', **kw):
    return c.chat(conversation=conv, messages=[{'role': 'user', 'content': text}], lang=lang, **kw)


class LoudKey(unittest.TestCase):
    def test_missing_or_empty_key_fails_loudly_with_the_exact_variable(self):
        for env in ({}, {'VENICE_API_KEY1': ''}, {'VENICE_API_KEY1': '   '}, {'VENICE_API_KEY': KEY}):
            with self.subTest(env=list(env)), self.assertRaises(V.VeniceKeyMissing) as ctx:
                V.VeniceClient(env, budget=V.VeniceBudget(Decimal('1'), Decimal('1')))
            self.assertIn('VENICE_API_KEY1', str(ctx.exception))             # no second name is accepted

    def test_401_402_and_a_provider_that_stays_down_are_explicit(self):
        for answer, err in (((401, {}), V.VeniceAuthError), ((402, {}), V.VeniceInsufficientCredit)):
            with self.subTest(err=err.__name__), self.assertRaises(err):
                say(client(Transport(chat=[answer])))
        t = Transport(chat=[(503, {})] * 3)
        with self.assertRaises(V.VeniceUnavailable):
            say(client(t))
        self.assertEqual(sum(1 for c in t.calls if c['method'] == 'POST'), 3)    # bounded: 1 + 2 retries
        with self.assertRaises(V.VeniceError):                                    # never an empty "AI" answer
            say(client(Transport(chat=[(200, ok(text=''))])))


class TraitSelectionAndTag(unittest.TestCase):
    def test_only_private_models_e2ee_preferred_without_tools(self):
        models = [V.VeniceModel.from_api(m) for m in MODELS]
        chosen = V.select_model(models)
        self.assertEqual(chosen.id, 'e2ee-private')                              # not the cheaper anonymized one
        self.assertEqual(V.select_model(models, needs_tools=True).id, 'tools-private')
        self.assertEqual(V.select_model(models, prefer_e2ee=False).id, 'plain-private')
        with self.assertRaises(V.NoPrivateModel):
            V.select_model([V.VeniceModel.from_api(model('x', privacy='anonymized'))])

    def test_the_tag_reflects_the_selected_models_traits_and_never_claims_more(self):
        out = say(client(Transport()))
        self.assertEqual(out['model'], 'e2ee-private')
        self.assertEqual(out['tag'], {'provider': 'venice', 'model_private': True, 'privacy': 'private',
                                      'model_supports_e2ee': True, 'end_to_end_encrypted': False})
        plain = V.truth_tag(V.VeniceModel.from_api(model('p')))
        self.assertFalse(plain['model_supports_e2ee'])
        anon = V.truth_tag(V.VeniceModel.from_api(model('a', privacy='anonymized')))
        self.assertFalse(anon['model_private'])

    def test_prices_come_from_the_provider_answer(self):
        t = Transport()
        out = say(client(t))
        self.assertEqual(out['cost_usd'], '0.0004')                               # the reported cost.usd
        body = next(c['body'] for c in t.calls if c['method'] == 'POST')
        self.assertEqual(body['model'], 'e2ee-private')


class BudgetIsEnforced(unittest.TestCase):
    def test_conversation_and_aggregate_caps(self):
        # worst case per call ~0.00117 USD (reserved), each call settles to the reported 0.0004
        t = Transport()
        c = client(t, per='0.0018', total='0.0022')
        say(c, conv='a')
        say(c, conv='a')
        with self.assertRaises(V.VeniceBudgetExceeded) as ctx:
            say(c, conv='a')
        self.assertIn('conversation cap', str(ctx.exception))
        say(c, conv='b')
        with self.assertRaises(V.VeniceBudgetExceeded) as ctx:
            say(c, conv='c')
        self.assertIn('aggregate cap', str(ctx.exception))
        self.assertEqual(sum(1 for x in t.calls if x['method'] == 'POST'), 3)   # refused calls never reach Venice
        self.assertEqual(c.budget.spent, {'a': Decimal('0.0008'), 'b': Decimal('0.0004')})

    def test_unknown_cost_counts_as_the_worst_case_never_as_free(self):
        b = V.VeniceBudget(Decimal('1'), Decimal('1'))
        c = V.VeniceClient({'VENICE_API_KEY1': KEY}, budget=b, transport=Transport(chat=[(200, {**ok(), 'cost': {}})]),
                           sleep=lambda s: None)
        say(c)
        self.assertGreater(b.spent['c1'], Decimal('0'))

    def test_cancellation_and_idempotency_and_timeout(self):
        t = Transport()
        stop = threading.Event()
        stop.set()
        with self.assertRaises(V.VeniceCancelled):
            say(client(t), cancel=stop)
        self.assertFalse([c for c in t.calls if c['method'] == 'POST'])          # nothing was sent
        t = Transport(chat=[(503, {}), (200, ok())])
        say(client(t), idempotency_key='turn-7')
        posts = [c for c in t.calls if c['method'] == 'POST']
        self.assertEqual([p['headers']['Idempotency-Key'] for p in posts], ['turn-7', 'turn-7'])   # same key on retry
        self.assertTrue(all(c['timeout'] == 60.0 for c in t.calls))


class NoKeyAnywhere(unittest.TestCase):
    def test_no_key_in_logs_errors_reprs_or_results(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logging.getLogger().addHandler(handler)
        try:
            c = client(Transport(chat=[(401, {})]))
            try:
                say(c)
            except V.VeniceAuthError as exc:
                error = str(exc)
            out = say(client(Transport()))
        finally:
            logging.getLogger().removeHandler(handler)
        for blob in (stream.getvalue(), error, repr(c), json.dumps(out)):
            self.assertNotIn(KEY, blob)


class CustomerLanguage(unittest.TestCase):
    def test_rtl_and_the_reply_language_follow_the_customer(self):
        t = Transport()
        he = say(client(t), lang='he')
        self.assertEqual(he['dir'], 'rtl')
        system = next(c['body'] for c in t.calls if c['method'] == 'POST')['messages'][0]['content']
        self.assertIn('(he)', system)
        self.assertEqual(say(client(Transport()), lang='ar')['dir'], 'rtl')
        self.assertEqual(say(client(Transport(chat=[(200, ok(text='Hello'))])), lang='en')['dir'], 'ltr')


if __name__ == '__main__':
    unittest.main()

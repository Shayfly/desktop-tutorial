"""T3 (founder 2026-10-21): content after the first JSON object is not ignored.

Keep the raw answer, diagnose it, accept exactly one JSON value; the only deterministic cleanup is a known envelope
(whitespace/BOM, one complete markdown fence). Unexplained content is not success.
"""
import json
import unittest
from decimal import Decimal

from omni_prod.model_gateway import (ModelEndpoint, ModelGatewayError, ModelJSONRejected, OpenAICompatibleGateway,
                                     parse_model_json)


class _Resp:
    def __init__(self, payload):
        self.body, self.headers = json.dumps(payload).encode(), {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def gateway(content):
    gw = OpenAICompatibleGateway(ModelEndpoint(name='m', base_url='https://x.invalid', model='m', api_key='k', external=True))
    gw._urlopen = lambda req, timeout=None: _Resp({'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}]})
    return gw


class TrailingContentIsNotIgnored(unittest.TestCase):
    def rejected(self, content):
        gw = gateway(content)
        with self.assertRaises(ModelJSONRejected) as ctx:
            gw.complete_json(system='s', user='u')
        self.assertEqual(ctx.exception.raw, content)                 # the raw answer travels with the error
        self.assertEqual(gw.last_raw_response, content)             # and stays on the gateway
        self.assertEqual(gw.last_json_diagnostic['verdict'], 'rejected')
        return ctx.exception.diagnostic

    def test_an_explanation_after_the_object(self):
        obj, d = parse_model_json('{"files": [{"path": "a.py", "content": "x"}]}\n\nNote: I also changed b.py')
        self.assertEqual(obj['files'][0]['path'], 'a.py')
        self.assertEqual(d['tail_class'], 'prose')
        self.assertEqual(__import__('base64').b64decode(d['tail_raw_utf8_b64']).decode(), d['tail'])
        self.assertEqual(d['trailing_starts'], 'Note: I also changed b.py')

    def test_a_second_object(self):
        d = self.rejected('{"files": []}{"files": [{"path": "evil.py", "content": "x"}]}')
        self.assertEqual(d['tail_class'], 'conflict')
        self.assertTrue(d['trailing_chars'] > 0)

    def test_prose_before_the_object(self):
        d = self.rejected('Sure! Here it is:\n{"files": []}')
        self.assertIn('content before the JSON value', d['reason'])

    def test_a_fence_with_text_after_it_is_not_the_known_envelope(self):
        d = self.rejected('```json\n{"files": []}\n```\nHope this helps')
        self.assertIn('markdown fence', d['reason'])

    def test_a_non_object_root(self):
        d = self.rejected('[{"path": "a.py"}]')
        self.assertIn('object', d['reason'])


class TheKnownEnvelopeStillWorks(unittest.TestCase):
    def test_plain_and_fenced_with_whitespace_and_bom(self):
        for content in ('{"a": 1}', '  \n{"a": 1}\n ', '﻿{"a": 1}', '```json\n{"a": 1}\n```', '```\n{"a": 1}\n```  '):
            gw = gateway(content)
            self.assertEqual(gw.complete_json(system='s', user='u'), {'a': 1}, content)
            self.assertEqual(gw.last_json_diagnostic['verdict'], 'accepted')

    def test_the_two_character_repairs_are_recorded(self):
        obj, d = parse_model_json('{"re": "\\d+", "code": "a\nb"}')
        self.assertEqual(obj, {'re': '\\d+', 'code': 'a\nb'})
        self.assertEqual(set(d['repairs']), {'invalid_escapes_doubled', 'raw_control_characters'})


class TheRoutedGatewayKeepsTheRawAnswer(unittest.TestCase):
    def test_a_rejected_answer_is_kept_with_its_diagnosis(self):
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway
        ep = ModelEndpoint(name='m', base_url='https://x.invalid', model='m', api_key='k', external=False)
        content = '{"files": []}\nand one more thing'
        gw = RoutedModelGateway(primary=ProviderRoute(ep, declared_quality=90), policy=ModelUsePolicy(
            zero_cost_mode=True, allow_external_fallback=False, external_budget_usd=Decimal('0'),
            max_external_calls_per_build=0), gateway_factory=lambda endpoint: gateway(content))
        self.assertEqual(gw.complete_json(system='s', user='u', task='codegen'), {'files': []})
        self.assertEqual(gw.rejected_json, [])


if __name__ == '__main__':
    unittest.main()

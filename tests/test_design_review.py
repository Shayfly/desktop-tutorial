"""Design critic (CEO 2026-11-09): a vision model reviews the screenshots; one polish round at most."""
import json
import unittest
from unittest import mock

from omni_prod.design_review import DesignCritic, install_design_critic
from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway


class _Gw:
    accepts_task_tag = True
    last_usage = None

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete_json(self, **kw):
        self.calls.append(kw)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


class _Spec:
    title, summary, requirements = 'קפה', 'דף נחיתה', ()


SHOTS = {'desktop': b'\xff\xd8desk', 'mobile': b'\xff\xd8mob'}


class DesignCriticTests(unittest.TestCase):
    def test_sends_both_screenshots_and_the_request(self):
        gw = _Gw({'score': 82, 'summary': 's', 'findings': []})
        r = DesignCritic(gw, request_text='צבעים חום קרם וירוק').review(spec=_Spec(), shots=SHOTS)
        self.assertEqual((r['status'], r['score']), ('REVIEWED', 82))
        self.assertEqual(gw.calls[0]['images'], (SHOTS['desktop'], SHOTS['mobile']))
        self.assertIn('חום', json.loads(gw.calls[0]['user'])['customer_request'])

    def test_must_fix_blocks_once_then_only_advises(self):
        must = {'score': 40, 'findings': [{'severity': 'must_fix', 'area': 'colour', 'viewport': 'both',
                                           'problem': 'הכפתור לא ירוק', 'fix': 'background:#2e7d32'},
                                          {'severity': 'suggestion', 'area': 'spacing', 'problem': 'p', 'fix': 'f'}]}
        c = DesignCritic(_Gw(must))
        first = c.failures(c.review(spec=_Spec(), shots=SHOTS))
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].acceptance_id, 'DESIGN')
        self.assertEqual(c.failures(c.review(spec=_Spec(), shots=SHOTS)), ())

    def test_errors_and_missing_screenshots_never_block(self):
        c = DesignCritic(_Gw(RuntimeError('no vision route')))
        r = c.review(spec=_Spec(), shots=SHOTS)
        self.assertEqual(r['status'], 'NOT_RUN')
        self.assertEqual(c.failures(r), ())
        self.assertEqual(DesignCritic(_Gw({})).review(spec=_Spec(), shots={})['status'], 'NOT_RUN')


class GatewayImageTests(unittest.TestCase):
    def body(self, style, images):
        gw = OpenAICompatibleGateway(ModelEndpoint(name='m', base_url='https://x.invalid', model='m', api_key='k',
                                                   external=True, api_style=style))
        sent = {}

        class R:
            headers = {}

            def __init__(s, p): s.b = json.dumps(p).encode()
            def read(s): return s.b
            def __enter__(s): return s
            def __exit__(s, *a): return False

        def urlopen(req, timeout=None):
            sent.update(json.loads(req.data))
            if style == 'anthropic':
                return R({'content': [{'type': 'text', 'text': '{"ok": 1}'}], 'stop_reason': 'end_turn'})
            return R({'choices': [{'message': {'content': '{"ok": 1}'}, 'finish_reason': 'stop'}]})
        gw._urlopen = urlopen
        gw.complete_json(system='s', user='u', images=images)
        return sent

    def test_anthropic_and_openai_image_shapes(self):
        a = self.body('anthropic', (b'img',))['messages'][0]['content']
        self.assertEqual(a[0]['type'], 'image')
        self.assertEqual(a[-1], {'type': 'text', 'text': 'u'})
        o = self.body('openai', (b'img',))['messages'][1]['content']
        self.assertTrue(o[1]['image_url']['url'].startswith('data:image/jpeg;base64,'))

    def test_text_only_calls_are_unchanged(self):
        self.assertEqual(self.body('anthropic', ())['messages'][0]['content'], 'u')


class InstallTests(unittest.TestCase):
    def test_founder_only_by_default(self):
        from omni_prod.visual_qa import VisualQAExecutor
        vq = VisualQAExecutor(mock.Mock())

        class E:
            executor = vq
            repairer = mock.Mock(gateway=_Gw({}))
        with mock.patch.dict('os.environ', {'OMNI_FOUNDER_ACCOUNT_IDS': 'usr_f'}):
            self.assertFalse(install_design_critic(E(), {'user_id': 'usr_c'}, 'p'))
            self.assertTrue(install_design_critic(E(), {'user_id': 'usr_f'}, 'p'))
            self.assertIsInstance(vq.design_critic, DesignCritic)


if __name__ == '__main__':
    unittest.main()

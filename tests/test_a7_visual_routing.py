"""A7 uses its own measured vision route, with the existing plan review cap."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from omni_prod.agent_os.recorder import PlanBoundRecorder, PlanViolation
from omni_prod.agent_os.runtime import RuntimeViolation
from omni_prod.design_review import DesignCritic
from omni_prod.g_apple import reviewers
from omni_prod.model_gateway import ModelGatewayError
from omni_prod import vision_models
from tests.test_vision_route_guard import gateway, IMAGE


class A7Routing(unittest.TestCase):
    def test_flag_off_keeps_both_existing_review_call_sites(self):
        self.check_call_sites('0', 'review')

    def test_flag_on_separates_both_visual_review_call_sites(self):
        self.check_call_sites('1', 'visual_review')

    def check_call_sites(self, flag, expected):
        gw = mock.Mock(accepts_task_tag=True, last_usage=None)
        gw.complete_json.return_value = {'score': 90, 'findings': [], 'category_marks': ['test']}
        with mock.patch.dict('os.environ', {'OMNI_VISUAL_REVIEW_GEMINI': flag}):
            critic = DesignCritic(gw)
            self.assertEqual(critic.review(spec=SimpleNamespace(), shots={'desktop': IMAGE[0]})['status'], 'REVIEWED')
            self.assertEqual(reviewers.review(gw, 'brand_category', {'desktop': IMAGE[0]})['status'], 'REVIEWED')
        self.assertEqual([c.kwargs['task'] for c in gw.complete_json.call_args_list], [expected, expected])
        self.assertTrue(all(c.kwargs['images'] == IMAGE for c in gw.complete_json.call_args_list))

    def test_untagged_gateway_is_not_contacted_when_a7_is_enabled(self):
        gw = mock.Mock(accepts_task_tag=False)
        with mock.patch.dict('os.environ', {'OMNI_VISUAL_REVIEW_GEMINI': '1'}):
            self.assertEqual(DesignCritic(gw).review(spec=SimpleNamespace(), shots={'desktop': IMAGE[0]})['status'],
                             'NOT_RUN')
            self.assertEqual(reviewers.review(gw, 'brand_category', {'desktop': IMAGE[0]})['status'], 'NOT_RUN')
        gw.complete_json.assert_not_called()

    def test_real_gateway_routes_a7_only_to_measured_gemini_and_preserves_a6(self):
        gw, contacted = gateway()
        kw = dict(system='s', user='u', max_tokens=1000)
        self.assertEqual(gw.ranked_routes(kw, 'review')[0][0].endpoint.model, 'gpt-6.1-sol')
        self.assertEqual(gw.complete_json(**kw, task='visual_review', images=IMAGE), {'ok': 'gemini-3.8-flash'})
        self.assertEqual(contacted, [('gemini-3.8-flash', True)])
        self.assertEqual(gw.recorder.records[-1].task_type, 'visual_review')
        self.assertEqual(gw.ranked_routes(kw, 'review')[0][0].endpoint.model, 'gpt-6.1-sol')

    def test_no_screenshot_or_vision_evidence_never_contacts_provider(self):
        gw, contacted = gateway()
        kw = dict(system='s', user='u', max_tokens=1000, task='visual_review')
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(**kw)
        with mock.patch.dict(vision_models.VISION_MODELS):
            del vision_models.VISION_MODELS['gemini-3.8-flash']
            with self.assertRaises(ModelGatewayError):
                gw.complete_json(**kw, images=IMAGE)
        self.assertEqual(contacted, [])

    def test_failed_gemini_does_not_fall_back_to_an_unapproved_provider(self):
        gw, contacted = gateway(failing=['gemini-3.8-flash'])
        with self.assertRaises(ModelGatewayError):
            gw.complete_json(system='s', user='u', max_tokens=1000, task='visual_review', images=IMAGE)
        self.assertEqual(contacted, [('gemini-3.8-flash', True)])


class SharedReviewBudget(unittest.TestCase):
    def recorder(self, spend):
        rec = PlanBoundRecorder(object(), 'bld_a7', plan={'tasks': []}, enforce=True)
        rec.by_stage = {'review': 'review-task'}
        rec.cost_source = lambda: spend
        rec.rt = mock.Mock()
        return rec

    def test_a6_and_a7_charge_the_sum_once_across_rounds(self):
        spend = {'review': Decimal('.02'), 'visual_review': Decimal('.03')}
        rec = self.recorder(spend)
        rec._charge()
        rec._charge()
        spend['visual_review'] += Decimal('.01')
        rec._charge()
        self.assertEqual([c.args for c in rec.rt.charge.call_args_list],
                         [('review-task', Decimal('.05')), ('review-task', Decimal('.01'))])
        self.assertEqual(rec.charged['review-task'], Decimal('.06'))

    def test_shared_cap_violation_is_sticky(self):
        rec = self.recorder({'review': Decimal('.03'), 'visual_review': Decimal('.03')})
        def charge(tid, delta, **kw):
            if delta > Decimal('.05'):
                raise RuntimeViolation('review budget exceeded')
        rec.rt.charge.side_effect = charge
        with self.assertRaises(PlanViolation):
            rec._charge()
        with self.assertRaises(PlanViolation):
            rec.raise_if_violated()

    def test_visual_call_cannot_bypass_verification_admission(self):
        rec = self.recorder({})
        with self.assertRaisesRegex(PlanViolation, 'outside an admitted verification'):
            rec.on_model('visual_review')
        self.assertTrue(rec.violation)


if __name__ == '__main__':
    unittest.main()

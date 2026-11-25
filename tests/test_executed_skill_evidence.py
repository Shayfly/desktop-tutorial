"""Evidence distinguishes executed probes from configured guidance."""
import json
import unittest
from unittest.mock import patch

from omni_prod import skills_runtime as runtime
from omni_prod.autonomous_agents import _REPAIR_SYSTEM
from omni_prod.intake.interpreter import contextual_user
from omni_prod.product_review import ProductReviewExecutor
from tests.test_skills_runtime_and_review import CLEAN, BAD, _Inner, _Reviewer, _spec


class SkillExecutionEvidence(unittest.TestCase):
    def test_probes_run_once_and_evidence_matches_actual_results(self):
        invoked = []

        def finds(repository, context):
            invoked.append('finds')
            return [runtime.StaticFinding('example', 'blocking', 'secret.py', 'private data', 'fix')]

        def clear(repository, context):
            invoked.append('clear')
            return []

        common = dict(version='2', purpose='test', boundaries='test', roles=('reviewer',),
                      guidance='test', checklist=('test',))
        skills = (runtime.Skill(key='example', static_checks=(finds, clear), **common),
                  runtime.Skill(key='guidance', **common))
        evidence = []
        with patch.object(runtime, 'WEB_SKILLS', skills):
            findings = runtime.static_findings({}, {'private': 'customer-secret'}, evidence=evidence)
        self.assertEqual(invoked, ['finds', 'clear'])
        self.assertEqual([f.probe for f in findings], ['finds'])
        self.assertEqual(evidence, [
            {'key': 'example', 'version': '2', 'status': 'STATIC_CHECKS_COMPLETED',
             'checks': [{'probe': 'finds', 'status': 'FINDINGS', 'findings': 1, 'blocking': 1},
                        {'probe': 'clear', 'status': 'NO_FINDINGS', 'findings': 0, 'blocking': 0}]},
            {'key': 'guidance', 'version': '2', 'status': 'NO_STATIC_CHECKS', 'checks': []},
        ])
        self.assertNotIn('customer-secret', json.dumps(evidence))
        self.assertNotIn('secret.py', json.dumps(evidence))

    def test_real_review_carries_execution_not_just_skill_registry(self):
        ex = ProductReviewExecutor(_Inner(), gateway=_Reviewer())
        ex.execute(repository=BAD, spec=_spec())
        review = ex.reviews[-1]
        records = review['skill_execution']
        self.assertEqual({(r['key'], r['version']) for r in records},
                         {(s.key, s.version) for s in runtime.WEB_SKILLS})
        record = next(r for r in records if r['key'] == 'skill.request_fidelity')
        self.assertEqual(record['status'], 'NO_STATIC_CHECKS')
        self.assertTrue(any(c['blocking'] for r in records for c in r['checks']))

    def test_review_not_run_does_not_claim_skill_execution(self):
        ex = ProductReviewExecutor(_Inner(False), gateway=_Reviewer())
        ex.execute(repository=CLEAN, spec=_spec())
        self.assertEqual(ex.reviews, [])

    def test_repair_receives_approved_scope_and_business_fact_guidance(self):
        self.assertIn('skill.request_fidelity@2', _REPAIR_SYSTEM)
        self.assertIn('Preserve confirmed requirements, exclusions and acceptance ids', _REPAIR_SYSTEM)
        self.assertIn('business facts, prices and testimonials need approved sources', _REPAIR_SYSTEM)

    def test_intake_receives_context_specific_consultant_guidance(self):
        payload = contextual_user('Build a website for a florist')
        self.assertIn('read prior decisions and delegated choices before asking', payload)
        self.assertIn('business facts, prices and media rights tied to approved customer sources', payload)


if __name__ == '__main__':
    unittest.main()

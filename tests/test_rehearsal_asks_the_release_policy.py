"""The rehearsal asks the release policy (production 2026-11-17, bld_a875456f: every customer build failed
`release_policy_failed` for half a day while five rehearsals of the same code said "ready").

The worker's own policy function runs here on an engine whose deep stages cannot be read -- the production state."""
import unittest
from types import SimpleNamespace

from omni_prod import rehearsal as R
from omni_prod.autonomous_core import ExecutionReport
from omni_prod.product_spec import ProductSpec

SPEC = ProductSpec.from_dict({
    'title': 'קפה נחמה', 'summary': 'אתר לבית קפה', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'דף הבית מציג את שם בית הקפה', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'GET / returns 200 with the name'}]})
REPO = {'app.py': 'print("קפה נחמה")\n', 'README.md': '# קפה נחמה\n'}


def result():
    return SimpleNamespace(spec=SPEC, repository=dict(REPO), report=ExecutionReport(True, (), 'ok'), status='ready')


class Bare:
    """An executor chain in which the consistency gate, the preview check and the behavioural acceptance cannot be
    found -- what the worker's evidence readers saw in production."""
    def execute(self, *, repository, spec):
        raise AssertionError('not reached')


class ThePolicyIsAsked(unittest.TestCase):
    def test_the_production_state_is_a_failed_rehearsal_with_the_same_words(self):
        policy = R.release_policy(SimpleNamespace(executor=Bare()), SimpleNamespace(), result())
        self.assertEqual(policy['decision'], 'FAILED')
        said = ' | '.join(policy['blocking'])
        for check in ('files/cross_file_consistency: NOT_RUN', 'preview/preview_starts: NOT_RUN',
                      'acceptance/behavioural_acceptance: NOT_RUN'):
            self.assertIn(check, said)                                    # the words of bld_a875456f's error
        self.assertEqual(policy['rights_clear'], 'NOT_ASSESSED')

    def test_a_build_the_policy_blocks_is_not_a_ready_rehearsal(self):
        base = {'outcome': 'ready', 'quality': {'passed': True}}
        self.assertTrue(R.ready({**base, 'release_policy': {'decision': 'READY'}}))
        self.assertFalse(R.ready({**base, 'release_policy': {'decision': 'FAILED'}}))
        self.assertFalse(R.ready({**base, 'release_policy': {'decision': 'UNAVAILABLE'}}))
        self.assertFalse(R.ready(base))                                   # never asked is not ready
        self.assertFalse(R.ready({'outcome': 'failed', 'quality': {'passed': True},
                                  'release_policy': {'decision': 'READY'}}))

    def test_the_notice_says_a_customers_build_would_fail(self):
        policy = R.release_policy(SimpleNamespace(executor=Bare()), SimpleNamespace(), result())
        lines = R.annotations({'prompt': 'x', 'release_policy': policy})
        self.assertTrue([l for l in lines if l.startswith('::notice title=release policy::')])
        error = [l for l in lines if l.startswith('::error title=release policy::')]
        self.assertEqual(len(error), 1)
        self.assertIn("a customer's build would FAIL", error[0])
        self.assertIn('behavioural_acceptance', error[0])
        ok = R.annotations({'prompt': 'x', 'release_policy': {'decision': 'READY', 'blocking': [], 'not_run': []}})
        self.assertFalse([l for l in ok if l.startswith('::error title=release policy::')])

    def test_a_build_with_no_result_is_said_not_judged(self):
        self.assertEqual(R.release_policy(SimpleNamespace(executor=Bare()), SimpleNamespace(), None)['decision'],
                         'NOT_RUN')

    def test_run_asks_it_before_reporting(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertIn("report['release_policy'] = release_policy(engine, gateway, result)", source)
        self.assertIn('return 0 if ready(report) else 1', source)


if __name__ == '__main__':
    unittest.main()

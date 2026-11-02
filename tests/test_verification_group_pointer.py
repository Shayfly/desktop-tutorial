"""The repair prompt keeps the file:line signal (founder 2026-11-03, decision A).

VerificationGroup sends the repairer ONE stage in full plus one ALSO_FAILING line. The stage was the lowest
progress() rank, so a PREVIEW failure without a pointer (rank 4) buried a BEHAVIOR failure 'at app.py:23' (rank 5)
in a summary line cut at 220 characters from failures[0].
Now (omni_prod/verification_group.py): ranks 0-3 (build / tests) always come first; within 4-9 a stage carrying a
file:line pointer wins and the rank only breaks ties; the ALSO_FAILING line quotes a pointer-bearing failure and
keeps the pointer even past 220 characters.
"""
import unittest

from omni_prod.autonomous_core import SUMMARY_FAILURE_ID, AcceptanceFailure as F, ExecutionReport as R
from omni_prod.verification_group import VerificationGroup, _POINTER


class _Threshold:
    def execute(self, **kw):
        return R(True, (), 'threshold ok')


def _stage(name, report):
    return type(name, (), {'check': lambda self, **kw: report})()


def run(*stages):
    return VerificationGroup(_Threshold(), [_stage(n, r) for n, r in stages]).execute(repository={}, spec=None)


def repair_payload(report):
    """What the repairer receives: autonomous_agents.py:236-238 keeps failures[:20]."""
    return [{'acceptance_id': f.acceptance_id, 'message': f.message} for f in report.failures][:20]


def show(tag, out):
    print(f'\n== {tag}: passed={out.passed}')
    for f in out.failures:
        print(f'   [{f.acceptance_id}] {f.message[:240]}')


PREVIEW_PTR = R(False, (F('PREVIEW', 'preview exited at app.py:7'),))
PREVIEW_NO_PTR = R(False, (F('PREVIEW', 'preview did not start: health check timed out'),))
BEHAVIOR_PTR = R(False, tuple(F('BEHAVIOR', f'step S{i} expected 400 got 201') for i in range(1, 4))
                 + (F('BEHAVIOR', 'S4 a score of 2.9 is accepted at app.py:23'),))
BUILD = R(False, (F('A1', 'remote build failed: at app.py:3'),))


class Controls(unittest.TestCase):
    def test_1_preview_with_pointer_beats_behaviour_with_pointer(self):
        out = run(('PreviewReadyExecutor', PREVIEW_PTR), ('BehaviorAcceptanceExecutor', BEHAVIOR_PTR))
        show('1 preview(ptr) vs behaviour(ptr)', out)
        self.assertEqual(out.failures[0].acceptance_id, 'PREVIEW')                # both carry one: rank breaks the tie
        self.assertIn('app.py:23', out.failures[-1].message)                      # behaviour's pointer in ALSO_FAILING

    def test_1b_preview_without_pointer_loses_to_behaviour_with_pointer(self):
        out = run(('PreviewReadyExecutor', PREVIEW_NO_PTR), ('BehaviorAcceptanceExecutor', BEHAVIOR_PTR))
        show('1b preview(no ptr) vs behaviour(ptr)', out)
        self.assertEqual([f.acceptance_id for f in out.failures], ['BEHAVIOR'] * 4 + [SUMMARY_FAILURE_ID])
        self.assertIn('PREVIEW: preview did not start', out.failures[-1].message)
        sent = repair_payload(out)
        print('   repairer payload (failures[:20]):', len(sent), 'items; pointer present:',
              any(_POINTER.search(x['message']) for x in sent))
        self.assertTrue(any('app.py:23' in x['message'] for x in sent))           # survives the [:20] cut

    def test_2_build_beats_preview_even_with_a_pointer(self):
        out = run(('PreviewReadyExecutor', PREVIEW_PTR), ('BuildCheckExecutor', BUILD))
        show('2 build vs preview(ptr)', out)
        self.assertEqual(out.failures[0].acceptance_id, 'A1')
        self.assertIn('PREVIEW: preview exited at app.py:7', out.failures[-1].message)

    def test_3_healthy_product_passes_without_also_failing(self):
        out = run(('PreviewReadyExecutor', R(True, (), 'ok')), ('BehaviorAcceptanceExecutor', R(True, (), 'ok')))
        show('3 healthy product', out)
        self.assertTrue(out.passed)
        self.assertFalse(any(f.acceptance_id == SUMMARY_FAILURE_ID for f in out.failures))

    def test_4_the_second_failure_carries_the_pointer_and_survives_the_summary_line(self):
        long = 'x' * 300
        browser = R(False, (F('BROWSER', 'console error on load'), F('BROWSER', f'TypeError {long} at static/app.js:41')))
        same_rank = R(False, (F('BROWSER', 'form submit did nothing'),))
        out = run(('BrowserFlowExecutor', same_rank), ('BrowserFlowExecutor2', browser))
        show('4a same rank: stage whose 2nd failure carries the pointer', out)
        self.assertIn('static/app.js:41', out.failures[1].message)               # chosen stage, in full
        self.assertNotIn('form submit', out.failures[0].message)
        out = run(('BuildCheckExecutor', BUILD), ('BrowserFlowExecutor', browser))
        show('4b the same stage summarised in ALSO_FAILING (past 220 chars)', out)
        line = out.failures[-1].message
        print('   summary tail:', repr(line[-45:]), '| len', len(line))
        self.assertTrue(line.endswith('static/app.js:41 (+1 more)'))           # the pointer survives the 220 cut
        self.assertNotIn('console error', line)                                    # the pointer-bearing failure is quoted

    def test_5_review_with_pointer_loses_to_preview(self):
        review = R(False, (F('REVIEW', 'reviewer: unhandled input at app.py:31'),))
        out = run(('PreviewReadyExecutor', PREVIEW_PTR), ('ProductReviewExecutor', review))
        show('5 review(ptr) vs preview(ptr)', out)
        self.assertEqual(out.failures[0].acceptance_id, 'PREVIEW')
        self.assertIn('REVIEW:', out.failures[-1].message)


if __name__ == '__main__':
    unittest.main()

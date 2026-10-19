"""The four post-build checks report TOGETHER (founder decision 2026-10-19).

Before: preview -> behaviour -> browser -> visual were nested wrappers and each returned as soon as anything inside it
had failed, so a later check ran only in a round where every earlier one passed. Rehearsal 39295707756: behaviour
passed only after repair 3, the browser then ran for the first time, found a dead form, and no repair round was left.

Now the threshold (consistency gate, dependency gate, sandbox build + verify) still short-circuits: if it fails,
nothing below runs. When it passes, EVERY stage's check runs against it (preview, behaviour, browser, visual) and
the round produces ONE ExecutionReport: the most severe failing stage (by `AutonomousProductEngine.progress()`) in
full, plus one `ALSO_FAILING` line naming every other failing check, so nothing is swallowed and the repairer is not
handed four unrelated failure dumps. progress() skips that line, so the report ranks by its most severe failure.

The stages stay nested over the threshold (stage[i]._inner is stage[i-1]) so `find_in_chain`, attribute delegation
and `_run` resolve as before; only the order of execution changes.
"""
from __future__ import annotations

from .autonomous_core import SUMMARY_FAILURE_ID, AcceptanceFailure, ExecutionReport


def _stage_rank(report) -> int:
    from .autonomous_core import AutonomousProductEngine
    return AutonomousProductEngine.progress(report)[0]


def _summary_line(report) -> str:
    f = report.failures[0]
    more = f' (+{len(report.failures) - 1} more)' if len(report.failures) > 1 else ''
    return f'{f.acceptance_id}: {" ".join(f.message.split())[:220]}{more}'


_LAYER_IDS = {'PreviewReadyExecutor': 'PREVIEW', 'BehaviorAcceptanceExecutor': 'BEHAVIOR', 'BrowserFlowExecutor': 'BROWSER',
              'VisualQAExecutor': 'VISUAL', 'ProductReviewExecutor': 'REVIEW'}


def layer_id(stage) -> str:
    name = type(stage).__name__
    return _LAYER_IDS.get(name, name.replace('Executor', '').upper() or 'STAGE')


def _run_stage(stage, *, repository, spec, base, others_failed):
    """One stage's check that can neither stop the group nor pass by accident (red team, 2026-10-19):
    an exception becomes that stage's failure ('<LAYER>_EXCEPTION'), and passed=False without any failure record
    gets one ('<LAYER>_unspecified')."""
    lid = layer_id(stage)
    try:
        if getattr(type(stage), 'group_context', False):   # the review: told whether the others failed this round
            r = stage.check(repository=repository, spec=spec, report=base, others_failed=others_failed)
        else:
            r = stage.check(repository=repository, spec=spec, report=base)
    except Exception as exc:                                # e.g. TimeoutError in preview must not skip the rest
        return ExecutionReport(False, (AcceptanceFailure(
            f'{lid}_EXCEPTION', f'{lid.lower()} check raised {type(exc).__name__}: {str(exc)[:300]}',
            'The check itself crashed before it could judge the product; the other checks still ran.'),), base.build_log)
    if r is None or not isinstance(getattr(r, 'passed', None), bool):
        return ExecutionReport(False, (AcceptanceFailure(f'{lid}_unspecified', f'{lid.lower()} check returned no report'),),
                               base.build_log)
    if not r.passed and not r.failures:                     # a failure with no record is still a failure
        return ExecutionReport(False, (AcceptanceFailure(f'{lid}_unspecified',
                                                         f'{lid.lower()} check failed without saying why'),), r.build_log)
    return r


class VerificationGroup:
    def __init__(self, threshold, stages):
        if not stages:
            raise ValueError('VerificationGroup needs at least one stage')
        self._threshold = threshold
        self._stages = tuple(stages)
        self._inner = self._stages[-1]          # chain walkers (find_in_chain) and attribute lookups go through here
        self.group_failures = ()                # every failure of the last round, in full (failure taxonomy)

    def __getattr__(self, item):
        if item.startswith('__') or item in ('_inner', '_threshold', '_stages', 'group_failures'):
            raise AttributeError(item)
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        self.group_failures = ()
        base = self._threshold.execute(repository=repository, spec=spec)
        if not base.passed:
            return base                         # a threshold failure: the post-build checks do not run
        failed = []
        for order, stage in enumerate(self._stages):          # every stage runs; none returns early
            r = _run_stage(stage, repository=repository, spec=spec, base=base, others_failed=bool(failed))
            if not r.passed:                                    # _run_stage guarantees at least one failure record
                failed.append((_stage_rank(r), order, r))
        if not failed:
            return base
        failed.sort(key=lambda t: (t[0], t[1]))                 # most severe first (progress() rank), then chain order
        self.group_failures = tuple(f for _, _, r in failed for f in r.failures)
        worst = failed[0][2]
        failures = list(worst.failures)                         # the most severe stage in full
        if len(failed) > 1:                                     # + ONE line about everything else that failed
            failures.append(AcceptanceFailure(
                SUMMARY_FAILURE_ID,
                'also failing in this round: ' + ' | '.join(_summary_line(r) for _, _, r in failed[1:]),
                'Fix the failure above first; these other checks also failed on the same version.'))
        return ExecutionReport(False, tuple(failures), worst.build_log)

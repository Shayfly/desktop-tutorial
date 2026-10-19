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
            if getattr(type(stage), 'group_context', False):   # the review: told whether the others failed this round
                r = stage.check(repository=repository, spec=spec, report=base, others_failed=bool(failed))
            else:
                r = stage.check(repository=repository, spec=spec, report=base)
            if not r.passed and r.failures:
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

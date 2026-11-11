"""T4 (Matt's design, founder 2026-10-21): what a post-build check may conclude, so it can never pass by accident.

Verdicts of one check:
  PASS       at least one real check ran and every check that ran passed
  FAIL       a check failed, OR the check could not judge the product (timeout, no output, malformed or contradictory
             evidence, a non-zero exit under a PASS payload): "could not verify" is never "verified"
  NO_CHECKS  the evidence is well formed but reports ZERO checks executed. Not PASS and not enough to approve: it is
             recorded under its own failure id `<LAYER>_NO_CHECKS`, so it stays visible in the coverage and the
             taxonomy instead of disappearing into a pass. A check that runs nothing cannot fail; that is the
             false-success pattern.
An empty `failures` list is fine on its own: it does NOT mean that nothing ran.

Control exceptions (a cancelled build, a mandatory ledger that is down, the model budget) are not check results:
every stage and the group re-raise them, so they stop the build instead of becoming a failed stage.
"""
from __future__ import annotations

from .autonomous_core import AcceptanceFailure, ExecutionReport

NO_CHECKS = 'NO_CHECKS'
UNVERIFIED = 'UNVERIFIED'


def control_exceptions() -> tuple[type[BaseException], ...]:
    from .attempt_ledger import AttemptLedgerUnavailable
    from .build_control import BuildCancelled
    from .model_policy import ModelPolicyViolation
    return (BuildCancelled, AttemptLedgerUnavailable, ModelPolicyViolation)


def reraise_control(exc: BaseException) -> None:
    if isinstance(exc, control_exceptions()):
        raise exc


def no_checks(layer: str, why: str, build_log: str = '') -> ExecutionReport:
    return ExecutionReport(False, (AcceptanceFailure(
        f'{layer}_{NO_CHECKS}', f'{layer.lower()} check executed zero checks: {why}',
        'The check ran but judged nothing, so it cannot approve the product. Make the product exercisable by it '
        '(for example a form the browser can submit, or a behavioural step per acceptance criterion).'),), build_log)


def unverified(layer: str, why: str, build_log: str = '') -> ExecutionReport:
    return ExecutionReport(False, (AcceptanceFailure(
        f'{layer}_{UNVERIFIED}', f'{layer.lower()} check could not verify the product: {why}'[:600],
        'The check could not run or produced no usable evidence; nothing was verified, so the stage does not pass.'),),
        build_log)


def verdict(report) -> str:
    """PASS / NO_CHECKS / FAIL of one report (for probes and evidence)."""
    if report.passed is True and not report.failures:
        return 'PASS'
    ids = [f.acceptance_id for f in report.failures]
    if ids and all(i.endswith('_' + NO_CHECKS) for i in ids):
        return NO_CHECKS
    return 'FAIL'

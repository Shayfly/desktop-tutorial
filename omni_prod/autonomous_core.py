from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Protocol
from .product_spec import ProductSpec
from .repository_patch import apply_patch

@dataclass(frozen=True)
class AcceptanceFailure:
    acceptance_id: str
    message: str
    evidence: str = ''

# A one-line summary of the OTHER failing post-build checks of a round (VerificationGroup): it tells the repairer what
# else fails without counting as a verification stage, so progress() skips it.
SUMMARY_FAILURE_ID = 'ALSO_FAILING'
# Absolute cap on repair rounds whatever the plan (Studio = 8): bounds spend if a ceiling is ever misconfigured.
REPAIR_ROUNDS_HARD_MAX = 8


# #95: a failed report with no failures still yields a taxonomy row (layer sandbox, check_failed_unspecified).
UNSPECIFIED_ROUND_FAILURE_ID = 'ROUND_unspecified'


@dataclass(frozen=True)
class ExecutionReport:
    passed: bool
    failures: tuple[AcceptanceFailure, ...] = ()
    build_log: str = ''

@dataclass(frozen=True)
class AutonomousResult:
    status: str
    spec: ProductSpec
    repository: dict[str, str]
    repair_rounds: int
    report: ExecutionReport
    stop_reason: str = ''

class Executor(Protocol):
    def execute(self, *, repository: dict[str, str], spec: ProductSpec) -> ExecutionReport:
        ...

class AutonomousProductEngine:
    def __init__(self, *, architect, generator, repairer, executor: Executor,
                 max_repair_rounds: int = 3, repair_ceiling: int = 3):
        if isinstance(max_repair_rounds, bool) or not isinstance(max_repair_rounds, int) or max_repair_rounds < 0:
            raise ValueError('max_repair_rounds must be a non-negative integer')
        self.architect = architect
        self.generator = generator
        self.repairer = repairer
        self.executor = executor
        # J3/T05: initial build + at most three repair candidates, each verified.
        # Clamp even stale environment overrides; never spend on a fourth repair.
        # 2026-10-19 seam: a caller that knows the plan may pass repair_ceiling (pricing.repair_rounds_for_plan, up to
        # REPAIR_ROUNDS_HARD_MAX). No caller does yet, so the ceiling stays 3 everywhere.
        if isinstance(repair_ceiling, bool) or not isinstance(repair_ceiling, int) or not 0 <= repair_ceiling <= REPAIR_ROUNDS_HARD_MAX:
            raise ValueError(f'repair_ceiling must be an integer 0..{REPAIR_ROUNDS_HARD_MAX}')
        self.max_repair_rounds = min(max_repair_rounds, repair_ceiling)

    @staticmethod
    def _summary(repo: dict[str, str], failures=()) -> dict:
        # Golden E2E #1 build bld_85cc573b473341e9b3f10d248d743ff1: five repair
        # rounds could not list acceptance ids in .omni/project.json because the
        # repair agent saw only {path, chars}. Same bounded content summary the
        # modification path uses.
        from .modifier_engine import repo_summary
        return repo_summary(repo, failures)

    def _repair_summary(self, repo, failures=()):
        transform = getattr(self, 'repository_transform', None)
        original_fingerprint = self._fingerprint(repo)
        if transform is not None and hasattr(transform, 'redact'):
            repo = transform.redact(repo)
        summary = dict(self._summary(repo, failures))
        summary['base_repository_fingerprint'] = 'sha256:' + original_fingerprint
        from .repair_contracts import attributed_files
        diagnostic = '\n'.join(str(f.get('message', '')) + '\n' + str(f.get('evidence', ''))
                               for f in failures if isinstance(f, dict))
        summary['candidate_files'] = attributed_files(repo, stderr=diagnostic)
        return summary

    @staticmethod
    def _fingerprint(repo: dict[str, str]) -> str:
        return hashlib.sha256(json.dumps(sorted(repo.items())).encode('utf-8')).hexdigest()

    # Directive 2026-10-10 P0.3: every verified candidate is handed to this
    # hook (the worker stores it durably) before the next repair; the loop
    # itself rolls back to the best candidate when a repair goes backwards.
    round_hook = None

    def _snapshot(self, index: int, repo: dict, report, decision: str) -> None:
        if self.round_hook is None:
            return
        try:
            self.round_hook(index, repo, report, decision, self.progress(report))
        except Exception:  # a snapshot must never change the build
            import logging
            logging.getLogger(__name__).warning('round snapshot failed', exc_info=True)
            if getattr(self, 'require_durable_snapshots', False):
                # In verified strict mode, never claim READY without round evidence.
                raise

    def _preflight(self, repo, spec, round_index):
        """Remove statically visible defects before the chain runs, WITHOUT spending a repair round (round_preflight).
        A narrow repairer call may only touch the affected files; if it does not resolve the issue the repository goes
        on as it was for that issue and the chain reports the failure (a real round). Disabled: OMNI_ROUND_PREFLIGHT=0."""
        import os
        if os.getenv('OMNI_ROUND_PREFLIGHT', '1') == '0' or self.repairer is None:
            return repo
        from . import round_preflight as pf
        checks = (
            ('preflight_syntax', lambda r: pf.syntax_errors(r),
             lambda found: pf.syntax_failure(found), lambda found: {e['file'] for e in found}),
            ('preflight_plan_coverage', lambda r: pf.plan_coverage_gaps(r, spec),
             lambda found: pf.plan_failure(found), lambda found: {pf.PLAN_PATH}),
        )
        for kind, detect, describe, allowed in checks:
            found = detect(repo)
            if not found:
                continue
            fixed = False
            for _ in range(pf.MAX_FIXES_PER_ISSUE):
                failure = describe(found)
                transform = getattr(self, 'repository_transform', None)
                if transform is not None and hasattr(transform, 'redact_text'):
                    failure = {k: transform.redact_text(v) if isinstance(v, str) else v for k, v in failure.items()}
                try:
                    patch = self.repairer.repair(spec=spec, repo_summary=self._repair_summary(repo, [failure]),
                                                 failures=[failure])
                except Exception:   # the cheap fix is optional; the real round still runs
                    break
                keep = allowed(found)
                narrow = tuple(p for p in patch or () if getattr(p, 'path', None) in keep)
                if not narrow:
                    break
                candidate = apply_patch(repo, narrow)
                if transform is not None:
                    candidate = transform(candidate)
                if not detect(candidate):
                    repo, fixed = candidate, True
                    break
            self._preflight_events.append({'layer': 'preflight', 'failure_type': kind, 'round_index': round_index,
                                           'chain_depth': 0, 'was_repaired': fixed})
        return repo

    def _observed_failures(self, report):
        """Every failure of a verified round for the taxonomy: the post-build group's full list when the round's
        report summarised some of them (ALSO_FAILING), otherwise the report's own failures."""
        if report.passed:
            return []
        own = [f for f in report.failures if f.acceptance_id != SUMMARY_FAILURE_ID]
        if len(own) == len(report.failures):
            observed = own
        else:
            group = getattr(self.executor, 'group_failures', None) or ()
            seen = {(f.acceptance_id, f.message) for f in own}
            observed = own + [f for f in group if (f.acceptance_id, f.message) not in seen]
        # #95: a failed round that names no failure is still a failure in the taxonomy, never zero rows
        return observed or [AcceptanceFailure(UNSPECIFIED_ROUND_FAILURE_ID, 'round failed without a diagnostic',
                                              (report.build_log or '')[:500])]

    @staticmethod
    def progress(report) -> tuple[int, int]:
        """How far a candidate got through the verification chain (build ->
        unit tests -> acceptance tests -> preview -> behaviour -> browser ->
        quality -> review), then fewer failures. Higher is better."""
        if report.passed:
            return (11, 0)
        stage = 11
        # Chain order (investor_app): sandbox -> dependency gate -> preview ->
        # behaviour -> browser -> quality -> model review. A REVIEW failure
        # means everything before it passed (paid build bld_2be07937 ranked it
        # lowest and discarded the candidate whose behaviour had passed).
        later = {'REVIEW': 9, 'QUALITY': 8, 'VISUAL': 7, 'BROWSER': 6}
        for f in report.failures:
            msg, aid = (getattr(f, 'message', '') or '').lower(), getattr(f, 'acceptance_id', '')
            if aid == SUMMARY_FAILURE_ID:
                continue
            # A crashed or silent post-build check ranks as its own layer (VerificationGroup red-team fix).
            for suffix in ('_EXCEPTION', '_unspecified'):
                if aid.endswith(suffix):
                    aid = aid[:-len(suffix)]
            if aid in later:
                s = later[aid]
            elif aid == 'BEHAVIOR':
                s = 5
            elif aid == 'PREVIEW':
                s = 4
            elif 'acceptance tests' in msg:
                s = 3
            elif 'unit tests' in msg:
                s = 2
            elif 'build failed' in msg or 'install' in msg:
                s = 0
            else:
                s = 1
            stage = min(stage, s)
        return (stage, -len(report.failures))

    def build(self, prompt: str) -> AutonomousResult:
        """C24 (2026-10-20): the failure taxonomy and first_pass are written whatever happens. They used to be computed
        only at the very end of a successful _build(), so a build that raised (a model or sandbox error) left the
        previous build's values or nothing at all, and the rounds already verified were lost."""
        self._taxonomy_rounds, self._preflight_events = [], []
        self._round0_passed = None
        self.failure_taxonomy, self.first_pass = [], None
        result = None
        try:
            result = self._build(prompt)
            return result
        finally:
            self._refresh_taxonomy(result)

    def _refresh_taxonomy(self, result: 'AutonomousResult | None' = None) -> None:
        from .failure_taxonomy import records
        rounds = getattr(self, '_taxonomy_rounds', None) or []
        self.failure_taxonomy = sorted(records(rounds) + list(getattr(self, '_preflight_events', None) or []),
                                       key=lambda r: (r['round_index'], r['layer'] != 'preflight'))
        # #95 FAILED_BUILD_REPORTED_FIRST_PASS: first pass = round 0 was verified AND its report passed AND the build
        # returned ready. An empty failure list is not a pass (ExecutionReport(False, ()) is a failed round); a build
        # that raised has no result and is never a first pass.
        self.first_pass = (bool(rounds) and getattr(self, '_round0_passed', None) is True and not rounds[0][1]
                           and result is not None and result.status == 'ready')

    def _build(self, prompt: str) -> AutonomousResult:
        """Generate, verify, repair.

        Basic stop-loss (founder decision 2026-10-07): the sandbox is
        deterministic (pinned image, no network), so verifying a repository
        state that was already verified cannot change the outcome. A repair
        that leaves the repository unchanged, or returns it to an earlier
        state, stops the loop instead of paying for more identical rounds.
        `stop_reason` records why the loop ended.
        """
        spec = self.architect.create_spec(prompt)
        initial = self.generator.generate(spec)
        repo = apply_patch({}, initial)
        if getattr(self,'repository_transform',None):
            repo = self.repository_transform(repo)
        repo = self._preflight(repo, spec, 0)
        report = self.executor.execute(repository=repo, spec=spec)
        self._taxonomy_rounds = [(0, self._observed_failures(report))]
        self._round0_passed = bool(report.passed)
        self._snapshot(0, repo, report, 'passed' if report.passed else 'initial')
        rounds = 0
        seen = {self._fingerprint(repo)}
        stop_reason = 'passed' if report.passed else 'max_repair_rounds'
        self.trace = []  # per round: what failed and what the repair changed (diagnostics only)
        # Paid builds 2026-10-09: a weaker repair turned "1 behaviour check
        # fails" into "build fails" and later rounds drifted further. A repair
        # that goes backwards is discarded; the next one starts from the best.
        best_repo, best_report = repo, report
        discarded_note = None
        while not report.passed and rounds < self.max_repair_rounds:
            rounds += 1
            failures = [f.__dict__ for f in report.failures]
            if discarded_note:
                failures = failures + [discarded_note]
                discarded_note = None
            transform = getattr(self, 'repository_transform', None)
            if transform is not None and hasattr(transform, 'redact_text'):
                failures = [{k: transform.redact_text(v) if isinstance(v, str) else v
                             for k, v in f.items()} for f in failures]
            patch = self.repairer.repair(
                spec=spec,
                repo_summary=self._repair_summary(repo, failures),
                failures=failures,
            )
            candidate = apply_patch(repo, patch)
            if getattr(self,'repository_transform',None):
                candidate = self.repository_transform(candidate)
            self.trace.append({
                'round': rounds,
                'failing': sorted({f['acceptance_id'] for f in failures}),
                'first_failure': (failures[0].get('message', '') + ' | ' + (failures[0].get('evidence') or '')[-300:])
                                 if failures else '',
                'changed': sorted(p for p in set(candidate) | set(repo) if candidate.get(p) != repo.get(p))[:12],
            })
            fingerprint = self._fingerprint(candidate)
            if fingerprint in seen:
                # `repo` and `report` stay paired: the rejected candidate is not adopted.
                stop_reason = ('no_progress_repository_unchanged' if candidate == repo
                               else 'no_progress_repository_cycle')
                break
            seen.add(fingerprint)
            candidate = self._preflight(candidate, spec, rounds)
            new_report = self.executor.execute(repository=candidate, spec=spec)
            self._taxonomy_rounds.append((rounds, self._observed_failures(new_report)))
            worse = not new_report.passed and self.progress(new_report) < self.progress(best_report)
            self._snapshot(rounds, candidate, new_report,
                           'passed' if new_report.passed else ('discarded' if worse else 'adopted'))
            if new_report.passed:
                repo, report, stop_reason = candidate, new_report, 'passed'
                break
            if worse:
                failing = [f'{f.acceptance_id}: {f.message}' for f in new_report.failures][:4]
                self.trace[-1]['discarded'] = failing
                discarded_note = {'acceptance_id': 'REPAIR_REGRESSION',
                                  'message': 'Your previous change made the product worse and was discarded; this is '
                                             'the better version again. Do not repeat that change.',
                                  'evidence': '; '.join(failing)[:600]}
                repo, report = best_repo, best_report
                continue
            repo, report = candidate, new_report
            if self.progress(report) >= self.progress(best_report):
                best_repo, best_report = repo, report
        if not report.passed:
            repo, report = best_repo, best_report
        return AutonomousResult(                     # build()'s finally refreshes the taxonomy with this result
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
            stop_reason,
        )

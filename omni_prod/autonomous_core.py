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
# else fails without counting as a verification stage, so progress() skips it. The repair loop does not rank a round by
# that line: it ranks it by every failure the line stands for (the group keeps them in group_failures; rank()).
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
    # Audit 2026-11-02 findings 2+14: how many tests EXECUTED (passed/failed/error, not skipped) across the verify
    # commands, read from the runner's own summary. None = no recognised runner reported a count.
    tests_executed: int | None = None

class RepairDeclined(Exception):
    """A repairer that will not repair this round, with the reason the loop records as its stop_reason (the content
    route, omni_prod/site_content: a failure the platform owns -- 'platform_render_defect' -- is a library or fact-sheet
    bug, not something a paid model round can fix). The loop ends on its best version, exactly as a stop-loss does.
    `paid_call` says whether the repairer called a model before it declined: a round declined before any call is not
    counted as a repair round."""

    def __init__(self, stop_reason: str, detail: str = '', *, paid_call: bool = False):
        super().__init__(f'{stop_reason}: {detail}' if detail else stop_reason)
        self.stop_reason = stop_reason
        self.detail = detail
        self.paid_call = paid_call


@dataclass(frozen=True)
class AutonomousResult:
    status: str
    spec: ProductSpec
    repository: dict[str, str]
    repair_rounds: int
    report: ExecutionReport
    stop_reason: str = ''
    # Every failure of the version in `repository` (the kept one), in full: the post-build group's ALSO_FAILING line
    # replaced by the failures it summarises. Empty when the version passed. bld_cb2d1b90a90f430c98603d14f8afa1a8: the
    # customer's message cut the report at four items and dropped the summary line, so VISUAL never reached them.
    full_failures: tuple[AcceptanceFailure, ...] = ()


# S4.2 (plan v3; the owner chose to continue, 2026-11-26 10:13 UTC): a build whose worker dies continues from its last
# checkpoint. The engine hands every checkpoint to `checkpoint_hook` (the worker stores it: omni_prod/build_checkpoint)
# and continues from a ResumePoint the worker loaded and verified. Three stages, in build order:
#   spec      after the architect: the spec exists; code generation and everything after it still run
#   round     after round 0 and after every repair round: the verified repository and the repair loop's whole state
#   finished  after the loop: its result, returned as it was
RESUME_STAGES = ('spec', 'round', 'finished')
LOOP_STATE_VERSION = 2          # 2: the best version, its full failures, discarded signatures (#541)


@dataclass(frozen=True)
class ResumePoint:
    """Where a recovered build continues. `round` is the number of repair rounds the checkpoint covers (0 = round 0);
    `repository` is the verified repository of that round and `loop` the repair loop's state (loop_state below), both
    required for 'round' and 'finished'."""
    stage: str
    spec: ProductSpec
    round: int = 0
    repository: dict | None = None
    loop: dict | None = None
    best_repository: dict | None = None     # #541: the best version, when it is not the current one

    def __post_init__(self):
        if self.stage not in RESUME_STAGES:
            raise ValueError(f'unknown resume stage {self.stage!r} (one of {RESUME_STAGES})')
        if self.stage != 'spec' and (not isinstance(self.repository, dict) or not isinstance(self.loop, dict)):
            raise ValueError(f'a {self.stage!r} resume needs the verified repository and the loop state')
        if self.stage != 'spec' and self.loop.get('version') != LOOP_STATE_VERSION:
            raise ValueError(f"loop state version {self.loop.get('version')!r} is not {LOOP_STATE_VERSION}")
        if (self.stage != 'spec' and not (self.loop.get('best') or {}).get('same_as_current', True)
                and not isinstance(self.best_repository, dict)):
            raise ValueError('the loop state names a best version other than the current one, and it is missing')


def failure_to_dict(failure) -> dict:
    evidence = getattr(failure, 'evidence', '')
    return {'acceptance_id': str(failure.acceptance_id), 'message': str(failure.message),
            'evidence': evidence if evidence is None or isinstance(evidence, str) else str(evidence)}


def failure_from_dict(data: dict) -> AcceptanceFailure:
    return AcceptanceFailure(str(data['acceptance_id']), str(data['message']), data.get('evidence', ''))


def report_to_dict(report) -> dict:
    return {'passed': bool(report.passed), 'failures': [failure_to_dict(f) for f in report.failures],
            'build_log': str(getattr(report, 'build_log', '') or ''),
            'tests_executed': getattr(report, 'tests_executed', None)}


def report_from_dict(data: dict) -> ExecutionReport:
    return ExecutionReport(bool(data['passed']), tuple(failure_from_dict(f) for f in data.get('failures') or ()),
                           str(data.get('build_log') or ''), data.get('tests_executed'))


def edit_ledger_to_dict(ledger) -> dict:
    """The test-edit ledger of a build (DECISIONS 8): its counts decide when an edit escalates, so a resumed loop keeps
    them. The customer's facts are not stored: they are read again from the same approved prompt."""
    return {'builder_tests': sorted(ledger.builder_tests), 'counted': [dict(x) for x in ledger.counted],
            'refused': [dict(x) for x in ledger.refused],
            'seen': [[path, skeleton, int(n)] for (path, skeleton), n in ledger._seen.items()],
            'escalate': ledger.escalate or ''}


def edit_ledger_from_dict(data: dict, facts):
    from .test_edit_guard import TestEditLedger
    ledger = TestEditLedger(frozenset(data['builder_tests']), facts)
    ledger.counted = [dict(x) for x in data['counted']]
    ledger.refused = [dict(x) for x in data['refused']]
    ledger._seen = {(path, skeleton): int(n) for path, skeleton, n in data['seen']}
    ledger.escalate = data['escalate'] or ''
    return ledger


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
        # Agentic repair (2026-11-09): the working copy the repair agent reads and edits. Underscore key: never
        # serialised into a prompt (RepairAgent's _filter_repo_summary keeps only named keys). Already redacted.
        summary['_repository'] = dict(repo)
        return summary

    @staticmethod
    def failure_signature(report) -> frozenset:
        """What a round failed on, as the repairer is told it: the set of (acceptance_id, message), and nothing else
        (Brain 2 point 6, 2026-11-02). The repository is NOT part of it -- the point is to stop when different
        repositories keep failing the same way (bld_96ab03c8: four snapshots, one message); a repository that does
        not change is caught earlier by the fingerprint. Evidence is NOT part of it either: it carries timings and
        log tails that differ on every run of the same failure, so including it would never match."""
        return frozenset((f.acceptance_id, f.message) for f in report.failures)

    @staticmethod
    def _fingerprint(repo: dict[str, str]) -> str:
        return hashlib.sha256(json.dumps(sorted(repo.items())).encode('utf-8')).hexdigest()

    # Directive 2026-10-10 P0.3: every verified candidate is handed to this
    # hook (the worker stores it durably) before the next repair; the loop
    # itself rolls back to the best candidate when a repair goes backwards.
    round_hook = None

    def _snapshot(self, index: int, repo: dict, report, decision: str, failures=None) -> None:
        """`failures`: the round's FULL failure list (_observed_failures). The hook's progress is the rank the loop
        decided by; the list itself is in `round_failures[index]` for the hook to read."""
        if failures is None:
            failures = self._observed_failures(report)
        if not isinstance(getattr(self, 'round_failures', None), dict):
            self.round_failures = {}
        self.round_failures[index] = list(failures)
        if self.round_hook is None:
            return
        try:
            self.round_hook(index, repo, report, decision, self.rank(failures))
        except Exception:  # a snapshot must never change the build
            import logging
            logging.getLogger(__name__).warning('round snapshot failed', exc_info=True)
            if getattr(self, 'require_durable_snapshots', False):
                # In verified strict mode, never claim READY without round evidence.
                raise

    # S4.2: called after the spec, after round 0, after every repair round and after the loop, with what a recovered
    # build needs to continue from that point ({'spec'} or {'spec', 'repository', 'loop'}). The worker stores it
    # durably (omni_prod/build_checkpoint.CheckpointWriter); None = no checkpoints (tests, the rehearsal).
    checkpoint_hook = None

    def _checkpoint(self, stage: str, payload: dict) -> None:
        if self.checkpoint_hook is None:
            return
        try:
            self.checkpoint_hook(stage, payload)
        except Exception:  # a checkpoint must never change the build; the writer records its own failures
            import logging
            logging.getLogger(__name__).warning('checkpoint %s failed', stage, exc_info=True)

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
            fixed, said, outcome = False, '', 'not_attempted'
            for _ in range(pf.MAX_FIXES_PER_ISSUE):
                failure = describe(found)
                transform = getattr(self, 'repository_transform', None)
                if transform is not None and hasattr(transform, 'redact_text'):
                    failure = {k: transform.redact_text(v) if isinstance(v, str) else v for k, v in failure.items()}
                said = str(failure.get('message') or '')[:300]      # after redaction: what was wrong, for the record
                try:
                    patch = self.repairer.repair(spec=spec, repo_summary=self._repair_summary(repo, [failure]),
                                                 failures=[failure])
                except Exception:   # the cheap fix is optional; the real round still runs
                    outcome = 'repairer_error'
                    break
                keep = allowed(found)
                narrow = tuple(p for p in patch or () if getattr(p, 'path', None) in keep)
                if not narrow:
                    outcome = 'patch_outside_the_allowed_files'
                    break
                candidate = apply_patch(repo, narrow)
                if transform is not None:
                    candidate = transform(candidate)
                if not detect(candidate):
                    repo, fixed, outcome = candidate, True, 'repaired'
                    break
                outcome = 'still_failing_after_the_patch'
            # 2026-11-21: the message and the outcome are recorded. Without them nobody could say afterwards WHAT the
            # plan lacked in 18 production builds, or why 5 of them were not repaired (the investigation of that day).
            self._preflight_events.append({'layer': 'preflight', 'failure_type': kind, 'round_index': round_index,
                                           'chain_depth': 0, 'was_repaired': fixed, 'message': said,
                                           'outcome': outcome})
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
    def stage_rank(failure) -> int:
        """How far through the verification chain one failure sits (build -> unit tests -> acceptance tests ->
        preview -> behaviour -> browser -> visual -> quality -> review). Higher is later."""
        msg, aid = (getattr(failure, 'message', '') or '').lower(), getattr(failure, 'acceptance_id', '') or ''
        # A crashed or silent post-build check ranks as its own layer (VerificationGroup red-team fix).
        for suffix in ('_EXCEPTION', '_unspecified'):
            if aid.endswith(suffix):
                aid = aid[:-len(suffix)]
        # Chain order (investor_app): sandbox -> dependency gate -> preview ->
        # behaviour -> browser -> quality -> model review. A REVIEW failure
        # means everything before it passed (paid build bld_2be07937 ranked it
        # lowest and discarded the candidate whose behaviour had passed).
        later = {'REVIEW': 9, 'QUALITY': 8, 'VISUAL': 7, 'BROWSER': 6}
        if aid in later:
            return later[aid]
        if aid == 'BEHAVIOR':
            return 5
        if aid == 'PREVIEW':
            return 4
        if 'acceptance tests' in msg:
            return 3
        if 'unit tests' in msg:
            return 2
        if 'build failed' in msg or 'install' in msg:
            return 0
        return 1

    @classmethod
    def progress(cls, report) -> tuple[int, int]:
        """How far a candidate got through the verification chain, then fewer failures, read from the report's own
        failures (one stage's report; the ALSO_FAILING line is skipped). Higher is better. The repair loop ranks a
        round by ALL its failures instead: rank()."""
        if report.passed:
            return (11, 0)
        stages = [cls.stage_rank(f) for f in report.failures if getattr(f, 'acceptance_id', '') != SUMMARY_FAILURE_ID]
        return (min(stages, default=11), -len(report.failures))

    @classmethod
    def _checks(cls, failures) -> set:
        """The checks a list of failures fails: (stage, check id). One id can fail at different stages (a criterion's
        build, unit test or acceptance test), and each stage is its own check."""
        return {(cls.stage_rank(f), str(getattr(f, 'acceptance_id', '') or '')
                 .removesuffix('_EXCEPTION').removesuffix('_unspecified'))
                for f in failures if getattr(f, 'acceptance_id', '') != SUMMARY_FAILURE_ID}

    @classmethod
    def rank(cls, failures) -> tuple[int, int]:
        """A round's place by EVERY failure it has (the post-build group's ALSO_FAILING line expanded into the failures
        it stands for): the lowest stage any of them sits at, then fewer failures. Higher is better; no failure is
        (11, 0), a passed round."""
        own = [f for f in failures if getattr(f, 'acceptance_id', '') != SUMMARY_FAILURE_ID]
        if not own:
            return (11, 0)
        return (min(cls.stage_rank(f) for f in own), -len(own))

    @classmethod
    def judge(cls, candidate, best) -> tuple[bool, bool]:
        """(worse, best_now) for a FAILED candidate against the best version so far, both given as their FULL failure
        lists (bld_cb2d1b90a90f430c98603d14f8afa1a8, 2026-11-24: the round ranked by its head stage only, so a version
        that fixed all four review findings and still failed the layout check was called worse six times and thrown
        away). worse -> the candidate is discarded and the loop goes back to the best version; best_now -> the
        candidate becomes the best version.
          * failures that are a strict subset of the best version's are always adopted, and are the new best;
          * a candidate is worse only when it fails a check the best version did not fail AND ranks below it;
          * otherwise it is adopted, and is the new best when it ranks at least as high."""
        pairs = lambda fs: {(f.acceptance_id, f.message) for f in fs if f.acceptance_id != SUMMARY_FAILURE_ID}
        if pairs(candidate) < pairs(best):
            return False, True
        new_check = bool(cls._checks(candidate) - cls._checks(best))
        worse = new_check and cls.rank(candidate) < cls.rank(best)
        return worse, not worse and cls.rank(candidate) >= cls.rank(best)

    def build(self, prompt: str, resume: ResumePoint | None = None) -> AutonomousResult:
        """C24 (2026-10-20): the failure taxonomy and first_pass are written whatever happens. They used to be computed
        only at the very end of a successful _build(), so a build that raised (a model or sandbox error) left the
        previous build's values or nothing at all, and the rounds already verified were lost.

        S4.2: `resume` continues a recovered build from its last checkpoint. A checkpoint that has the spec means no
        architect call; one that has round 0 means no generator call either; the repair loop goes on from the
        checkpoint's round with the budgets it had (rounds, second chances, the test-edit ledger) and stops as it would
        have; a finished loop returns its result."""
        self._taxonomy_rounds, self._preflight_events = [], []
        self.round_failures = {}
        self._round0_passed = None
        self.failure_taxonomy, self.first_pass = [], None
        self.resumed_from = None
        result = None
        try:
            result = self._build(prompt, resume)
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

    def _build(self, prompt: str, resume: ResumePoint | None = None) -> AutonomousResult:
        """Generate, verify, repair.

        Basic stop-loss (founder decision 2026-10-07): the sandbox is
        deterministic (pinned image, no network), so verifying a repository
        state that was already verified cannot change the outcome. A repair
        that leaves the repository unchanged, or returns it to an earlier
        state, stops the loop instead of paying for more identical rounds.
        `stop_reason` records why the loop ended.

        S4.2: with `resume`, every stage the checkpoint covers is taken from it, never run again (build() says which).
        """
        from . import plan_floor
        from .test_edit_guard import TestEditLedger, customer_facts
        from .repair_contracts import _TEST_FILE
        if resume is None:
            spec = self.architect.create_spec(prompt)
            self._checkpoint('spec', {'spec': spec})
        else:
            spec = resume.spec
            self.resumed_from = {'stage': resume.stage, 'round': None if resume.stage == 'spec' else resume.round}
        loop = resume.loop if resume is not None and resume.stage != 'spec' else None
        if loop is None:
            initial = self.generator.generate(spec)
            repo = apply_patch({}, initial)
            if getattr(self,'repository_transform',None):
                repo = self.repository_transform(repo)
            repo = self._preflight(repo, spec, 0)
            report = self.executor.execute(repository=repo, spec=spec)
            observed = self._observed_failures(report)        # the round's full list, read right after its own execute
            self._taxonomy_rounds = [(0, observed)]
            self._round0_passed = bool(report.passed)
            self._snapshot(0, repo, report, 'passed' if report.passed else 'initial', observed)
            rounds = 0
            seen = {self._fingerprint(repo)}
            stop_reason = 'passed' if report.passed else 'max_repair_rounds'
            self.trace = []  # per round: what failed and what the repair changed (diagnostics only)
            # Paid builds 2026-10-09: a weaker repair turned "1 behaviour check
            # fails" into "build fails" and later rounds drifted further. A repair
            # that goes backwards is discarded; the next one starts from the best.
            # bld_cb2d1b90 (2026-11-24): "backwards" is judged on each version's FULL failure list (judge()), never on
            # the head stage of its report.
            best_repo, best_report, best_failures = repo, report, observed
            # Two discarded candidates that fail in exactly the same way (against the same best version) stop the loop:
            # the repairer is not reaching the cause, and a third identical regression would be paid for again.
            discarded_signatures: dict = {}
        else:
            # The checkpoint's round, exactly as the lost worker left it: the current version and its report, the best
            # version so far with its full failure list (they differ after a candidate that was adopted without
            # becoming the best: judge()), the discarded-candidate signatures, the states already verified (the
            # stop-loss), the round count and the taxonomy so far.
            repo, report = dict(resume.repository), report_from_dict(loop['report'])
            self._taxonomy_rounds = [(int(i), [failure_from_dict(f) for f in fs]) for i, fs in loop['taxonomy']]
            self._preflight_events = [dict(e) for e in loop['preflight']]
            self.round_failures = {int(i): [failure_from_dict(f) for f in fs] for i, fs in loop['round_failures']}
            self._round0_passed = loop['round0_passed']
            rounds = int(loop['rounds'])
            seen = set(loop['seen'])
            stop_reason = loop['stop_reason']
            self.trace = [dict(t) for t in loop['trace']]
            best = loop['best']
            best_repo = repo if best['same_as_current'] else dict(resume.best_repository)
            best_report = report_from_dict(best['report'])
            best_failures = [failure_from_dict(f) for f in best['failures']]
            discarded_signatures = {frozenset((str(a), str(m)) for a, m in pairs): int(n)
                                    for pairs, n in loop['discarded_signatures']}
            # the same budgets: never more rounds than the build had when it started
            self.max_repair_rounds = min(self.max_repair_rounds, int(loop['max_repair_rounds']))
        notes = (loop or {}).get('notes') or {}
        discarded_note = notes.get('discarded')
        # The plan verified in round 0 is a floor for every repair round (plan_floor, founder 2026-11-02).
        floor, plan_note = (plan_floor.plan_block(repo) if loop is None else loop['floor']), notes.get('plan')
        # DECISIONS 8 (the owner 2026-11-17): the repairer may fix an expected value in a test the builder wrote in
        # this build -- never a test of the customer's facts; every edit counted; the same value twice escalates.
        self.test_edits = (TestEditLedger(frozenset(p for p in repo if _TEST_FILE.search(p)), customer_facts(prompt))
                           if loop is None else edit_ledger_from_dict(loop['test_edits'], customer_facts(prompt)))
        test_note = notes.get('test')
        # Founder build bld_ca727ba7 (2026-11-08): the loop stopped after 2 of 6 rounds on one unchanged patch. The
        # stop-loss stays, but production gets `no_progress_retries` second chances: the next repair is told plainly
        # that its last answer changed nothing, before the loop gives up. 0 (the default) is the old behaviour.
        chances = int(getattr(self, 'no_progress_retries', 0) or 0) if loop is None else int(loop['chances'])
        progress_note = notes.get('progress')

        def loop_state() -> dict:
            """Everything the repair loop decides the next round with (S4.2: a checkpoint carries it, JSON only)."""
            return {'version': LOOP_STATE_VERSION, 'rounds': rounds, 'max_repair_rounds': self.max_repair_rounds,
                    'report': report_to_dict(report), 'seen': sorted(seen), 'stop_reason': stop_reason,
                    'notes': {'discarded': discarded_note, 'plan': plan_note, 'progress': progress_note,
                              'test': test_note},
                    'floor': floor, 'test_edits': edit_ledger_to_dict(self.test_edits), 'chances': chances,
                    'trace': [dict(t) for t in self.trace],
                    'taxonomy': [[i, [failure_to_dict(f) for f in fs]] for i, fs in self._taxonomy_rounds],
                    'preflight': [dict(e) for e in self._preflight_events], 'round0_passed': self._round0_passed,
                    'needs_input': list(getattr(self, 'needs_input', None) or ()),
                    'repair_model_error': getattr(self, 'repair_model_error', None),
                    # #541 (repair converges): the best version is judged on its FULL failure list and may differ from
                    # the current one; two identical discards stop the loop; the full list of every round is evidence
                    'best': {'same_as_current': best_repo is repo or best_repo == repo,
                             'report': report_to_dict(best_report),
                             'failures': [failure_to_dict(f) for f in best_failures]},
                    'discarded_signatures': [[sorted([a, m] for a, m in sig), n]
                                             for sig, n in discarded_signatures.items()],
                    'round_failures': [[i, [failure_to_dict(f) for f in fs]]
                                       for i, fs in sorted((getattr(self, 'round_failures', None) or {}).items())]}

        def payload() -> dict:
            out = {'spec': spec, 'repository': repo, 'loop': loop_state()}
            if not out['loop']['best']['same_as_current']:
                out['best_repository'] = best_repo        # stored and checked like the current version
            return out

        if resume is not None and resume.stage == 'finished':
            # the loop had ended: its result, with no model call and no check run again
            self.needs_input = list(loop.get('needs_input') or ())
            if loop.get('repair_model_error'):
                self.repair_model_error = loop['repair_model_error']
            return AutonomousResult('ready' if report.passed else 'failed', spec, repo, rounds, report, stop_reason,
                                    () if report.passed else tuple(best_failures))
        if loop is None:
            self._checkpoint('round', payload())
        checkpointed = rounds

        def second_chance(reason: str) -> bool:
            nonlocal chances, progress_note
            if chances <= 0 or rounds >= self.max_repair_rounds:
                return False
            chances -= 1
            self.trace[-1:] and self.trace[-1].setdefault('second_chance', reason)
            progress_note = {'acceptance_id': 'NO_PROGRESS',
                             'message': ('Your previous repair did not change the outcome (' + reason + '). Read the '
                                         'failing checks again, find the code they exercise, and change THAT code. '
                                         'If a check sends a request, make the endpoint return exactly what it expects.'),
                             'evidence': ''}
            return True

        # #335 (d), Michael 2026-11-13: a failure only the customer can fix (a fact the page needs and they never
        # gave) stops the repair rounds -- repairing could only invent it again. `missing_input` is set by the worker.
        self.needs_input = []
        missing_input = getattr(self, 'missing_input', None)
        out_of_time = getattr(self, 'out_of_time', None)
        while not report.passed and rounds < self.max_repair_rounds:
            if rounds > checkpointed:
                # S4.2: repair round `rounds` is done; a worker that dies from here on continues from this state
                checkpointed = rounds
                self._checkpoint('round', payload())
            if callable(out_of_time) and out_of_time():
                # the owner 2026-11-16: a build ends itself, on its best version, before the queue kills the worker
                stop_reason = 'time_budget'
                break
            if missing_input is not None:
                self.needs_input = list(missing_input([getattr(f, 'message', '') for f in report.failures]) or ())
                if self.needs_input:
                    stop_reason = 'needs_customer_input'
                    break
            rounds += 1
            failures = [f.__dict__ for f in report.failures]
            if discarded_note:
                failures = failures + [discarded_note]
                discarded_note = None
            if plan_note:
                failures = failures + [plan_note]
                plan_note = None
            if progress_note:
                failures = failures + [progress_note]
                progress_note = None
            if test_note:
                failures = failures + [test_note]
                test_note = None
            transform = getattr(self, 'repository_transform', None)
            if transform is not None and hasattr(transform, 'redact_text'):
                failures = [{k: transform.redact_text(v) if isinstance(v, str) else v
                             for k, v in f.items()} for f in failures]
            try:
                patch = self.repairer.repair(
                    spec=spec,
                    repo_summary=self._repair_summary(repo, failures),
                    failures=failures,
                )
            except RepairDeclined as exc:
                # the content route (omni_prod/site_content): a platform-owned failure stops without a paid round
                self.trace.append({'round': rounds, 'repair_declined': exc.stop_reason, 'detail': exc.detail[:400],
                                   'paid_call': exc.paid_call})
                if not exc.paid_call:
                    rounds -= 1          # declined before any model call: this repair round did not run
                stop_reason = exc.stop_reason
                break
            except Exception as exc:
                # The owner's butcher builds, 2026-11-17 (bld_6323468a, bld_c0b2b43b): three rounds were verified, then
                # no model route answered the repair with valid JSON (prose before it, an answer cut at its length, an
                # account with no credit). The exception ended the whole build: the verified work was thrown away and
                # the customer was told no check ran. Now the repair stops and the build ends on its best version with
                # its real checks. Only "no route answered"; any other error still ends the build as before.
                from .model_gateway import ModelGatewayError, ProviderQuotaUnavailable
                # 2026-11-18 (analysis of the same builds): when a route in the call had answered "no credit", the
                # router raises ProviderQuotaUnavailable instead -- also "no route answered", but its message lacks
                # the phrase, so this catch missed it and the build died the old way. Matched by type, not by text.
                no_route = isinstance(exc, ProviderQuotaUnavailable) or (
                    isinstance(exc, ModelGatewayError) and 'all model routes failed' in str(exc))
                if not no_route:
                    raise
                self.repair_model_error = str(exc)[:1200]
                self.trace.append({'round': rounds, 'repair_model_unavailable': str(exc)[:400]})
                stop_reason = 'repair_model_unavailable'
                break
            if not patch:
                # Brain 2 point 4 (2026-11-02): an empty patch is its own label; no_progress_repository_unchanged is
                # kept for a non-empty patch whose result is identical to the repository it was applied to.
                stop_reason = 'no_progress_empty_patch'
                if second_chance(stop_reason):
                    continue
                break
            candidate = apply_patch(repo, patch)
            if getattr(self,'repository_transform',None):
                candidate = self.repository_transform(candidate)
            candidate, refused_tests = self.test_edits.review(repo, candidate)
            if refused_tests:
                test_note = {'acceptance_id': 'TEST_EDIT_REVERTED', 'message': ' '.join(refused_tests)[:1500],
                             'evidence': ''}
            if self.test_edits.escalate:
                stop_reason = 'test_value_fixed_twice'
                self.trace.append({'round': rounds + 1, 'escalated': self.test_edits.escalate})
                break
            # Before the fingerprint: a repair that only cut the plan is then "unchanged", not a new state to verify.
            candidate, plan_lost = plan_floor.enforce(candidate, floor, repo)
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
                if second_chance(stop_reason):
                    continue
                break
            seen.add(fingerprint)
            candidate = self._preflight(candidate, spec, rounds)
            candidate, lost_in_preflight = plan_floor.enforce(candidate, floor, repo)   # the pre-flight may edit the plan
            plan_lost = plan_lost + [x for x in lost_in_preflight if x not in plan_lost]
            if plan_lost:
                self.trace[-1]['plan_restored'] = plan_lost
                plan_note = plan_floor.note(plan_lost)
            new_report = self.executor.execute(repository=candidate, spec=spec)
            observed = self._observed_failures(new_report)
            self._taxonomy_rounds.append((rounds, observed))
            worse, best_now = (False, True) if new_report.passed else self.judge(observed, best_failures)
            self._snapshot(rounds, candidate, new_report,
                           'passed' if new_report.passed else ('discarded' if worse else 'adopted'), observed)
            if new_report.passed:
                repo, report, stop_reason = candidate, new_report, 'passed'
                break
            if worse:
                # Only what this candidate broke: a failure the best version also has is not the repair's doing
                # (bld_cb2d1b90: the repairer was told its change made the product worse, with VISUAL failures that
                # existed before it touched anything).
                had = {(f.acceptance_id, f.message) for f in best_failures}
                introduced = [f for f in observed if (f.acceptance_id, f.message) not in had]
                failing = [f'{f.acceptance_id}: {f.message}' for f in introduced][:4]
                self.trace[-1]['discarded'] = failing
                if introduced:
                    discarded_note = {'acceptance_id': 'REPAIR_REGRESSION',
                                      'message': 'Your previous change made the product worse and was discarded; this '
                                                 'is the better version again. Do not repeat that change.',
                                      'evidence': '; '.join(failing)[:600]}
                repo, report = best_repo, best_report
                signature = frozenset((f.acceptance_id, f.message) for f in observed)
                discarded_signatures[signature] = discarded_signatures.get(signature, 0) + 1
                if discarded_signatures[signature] >= 2:
                    self.trace[-1]['stopped'] = 'two discarded candidates failed in exactly the same way'
                    stop_reason = 'no_progress_same_failure'
                    break
                continue
            same_failure = self.failure_signature(new_report) == self.failure_signature(report)
            repo, report = candidate, new_report
            if best_now:
                best_repo, best_report, best_failures = repo, report, observed
                discarded_signatures = {}
            if same_failure:
                # bld_96ab03c8 (founder 2026-11-01 23:33): the repository changed every round, but the failure did
                # not -- four paid rounds on one identical message. The same set of (acceptance_id, message) as the
                # round before means the repair is not reaching the cause; stop instead of paying again.
                stop_reason = 'no_progress_same_failure'
                if second_chance(stop_reason):
                    continue
                break
        else:
            # The loop ran out of rounds (no break): a second chance used earlier must not leave its no_progress label.
            if not report.passed:
                stop_reason = 'max_repair_rounds'
        if not report.passed:
            repo, report = best_repo, best_report
        # S4.2: the loop's result -- a worker that dies after this (gates, version, settlement) repeats no model call
        self._checkpoint('finished', payload())
        return AutonomousResult(                     # build()'s finally refreshes the taxonomy with this result
            'ready' if report.passed else 'failed',
            spec,
            repo,
            rounds,
            report,
            stop_reason,
            () if report.passed else tuple(best_failures),
        )

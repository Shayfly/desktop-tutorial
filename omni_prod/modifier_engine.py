from __future__ import annotations
from dataclasses import dataclass
from .product_spec import ProductSpec
from .change_policy import ChangeAssessment
from .autonomous_core import AcceptanceFailure, ExecutionReport, Executor
from .repository_patch import apply_patch


@dataclass(frozen=True)
class ModifierResult:
    status: str  # 'applied' | 'failed' | 'needs_clarification' | 'change_request_not_supported'
    assessment: ChangeAssessment
    repository: dict[str, str]
    repair_rounds: int
    report: ExecutionReport | None
    billable: bool
    stop_reason: str = ''          # why the repair loop ended (run_free_repair); '' when no loop ran


class ModifierEngine:
    """Applies a user's follow-up request against an *already generated and
    committed* project, instead of building one from scratch.

    Real, pre-existing gap this closes: `ChangeClassifierAgent`
    (omni_prod/autonomous_agents.py) and `ChangeAssessment`
    (omni_prod/change_policy.py) already classify a follow-up as
    system_bug / missing_requirement / change_request / ambiguous, and
    `ChangeAssessment.from_dict` is exercised by
    tests/test_v22_autonomous_core.py -- but nothing in this repository ever
    calls `ChangeClassifierAgent.classify()` outside that one test, and
    nothing turns a classification into an actual repository change.
    `POST /api/billing/classify` (investor_app.py) is not that path: it calls
    a different function, `billing.classify_charge()`, which prices a
    `category` string the *caller* already decided on -- it never invokes the
    LLM classifier and never touches a repository. Confirmed by grep before
    writing this: `ChangeClassifierAgent`/`ChangeAssessment` have exactly one
    call site outside their own definitions and this file, in that test.

    Scope of this stub, deliberately:

    - **system_bug / missing_requirement**: real, tested end-to-end here.
      These are the "free" categories (`ChangeAssessment.billable` is
      `False`) that `ChangeAssessment.from_dict` already requires to
      reference specific existing acceptance ids. Routed through the *same*
      `RepairAgent` + `Executor` + `repository_patch.apply_patch()` that
      `AutonomousProductEngine`'s own repair loop (autonomous_core.py) uses
      for the initial build -- no new agent, no new prompt, no new patch
      format invented for this.
    - **change_request**: classified (so billing/UI can show the right
      category and credit cost) but deliberately NOT executed here. A
      billable "add a new capability" request cannot be safely reduced to
      RepairAgent's "make the smallest safe patch that fixes supplied
      acceptance failures" framing -- `ChangeAssessment.from_dict` allows it
      to reference *no* acceptance id at all, since there may be nothing
      failing yet to point at. Executing it needs its own generation
      prompt and, usually, a spec update: a real product decision, not
      something to guess at silently. Returns
      `status='change_request_not_supported'` with the real
      `ChangeAssessment` attached, so a caller can bill/queue it once that
      path exists -- the same "flag the real gap instead of faking it"
      practice `PATCH_APPLICATION_REPORT.md` used for the M1 worker and the
      M3 generator-prompt gap.
    - **ambiguous**: classified, nothing executed,
      `status='needs_clarification'`.

    Also deliberately out of scope: persisting/retrieving the `ProductSpec`
    a project was originally built against. Nothing in this codebase
    currently does -- `ProjectVersion` (workspace.py) stores only the
    repository, and grepping job_repository.py, acceptance_pipeline.py,
    v27_platform.py and project_memory.py for a stored spec finds nothing.
    The caller of `.modify()` must supply the `spec` it already holds from
    build time. Adding durable spec storage is a separate, real change to
    the commit path, not something to invent inside a "modify" engine.

    Also not wired up here, for the same reason: no FastAPI route and no
    worker task call this. `execute_live_build_job` / `execute_preview_launch`
    (worker_tasks.py) were only written once a directive explicitly asked for
    them (see PATCH_APPLICATION_REPORT.md's M1 section); inventing route/queue
    wiring for a brand-new, previously-unspecified capability before that is
    asked for would be exactly the kind of unrequested addition this
    repository's AGENTS.md warns against.

    M4 update: the repair loop below is also used, unmodified, by
    `omni_prod.modification_engine.CandidateModificationEngine` for its own
    system_bug/missing_requirement path -- extracted to the module-level
    `run_free_repair()` function so that engine can reuse it with an
    `assessment` it already computed, instead of calling `self.classify()`
    a second time (which would spend a second real model call classifying
    the same followup twice, and could theoretically disagree with the first
    classification). `ModifierEngine.modify()` itself is unchanged in
    behavior -- this is a pure extraction, pinned by the fact every test in
    tests/test_modifier_engine.py still passes unmodified.
    """

    def __init__(self, *, classifier, repairer, executor: Executor, max_repair_rounds: int = 3):
        _check_repair_rounds(max_repair_rounds)    # Brain 2 (2026-11-02): same bounds as run_free_repair, at construction
        self.classifier = classifier
        self.repairer = repairer
        self.executor = executor
        self.max_repair_rounds = max_repair_rounds

    def modify(self, *, spec: ProductSpec, repository: dict[str, str], followup: str) -> ModifierResult:
        if not followup.strip():
            raise ValueError('followup cannot be empty')
        if not repository:
            raise ValueError('repository cannot be empty -- nothing to modify')

        assessment = self.classifier.classify(spec=spec, followup=followup)
        repo = dict(repository)

        if assessment.category == 'ambiguous':
            return ModifierResult('needs_clarification', assessment, repo, 0, None, assessment.billable)

        if assessment.category == 'change_request':
            return ModifierResult('change_request_not_supported', assessment, repo, 0, None, assessment.billable)

        # system_bug / missing_requirement. ChangeAssessment.from_dict already
        # guarantees assessment.acceptance_ids is non-empty and every id is a
        # real id in spec.acceptance for these two categories -- checked
        # there, at classification time, against the same spec passed in
        # above, so it is not re-validated here.
        repo, rounds, report, stop_reason = run_free_repair(
            spec=spec, repository=repository, assessment=assessment, followup=followup,
            repairer=self.repairer, executor=self.executor, max_repair_rounds=self.max_repair_rounds,
        )
        # Brain 2 blocker (2026-11-02): 'applied' means a repair was adopted. When the original already passes and
        # every candidate is discarded, the original comes back with a passing report -- that is not a change.
        status = 'applied' if report.passed and repo != dict(repository) else 'failed'
        return ModifierResult(status, assessment, repo, rounds, report, assessment.billable, stop_reason)


# Golden E2E #1 (2026-10-07): a modification ("add deleting a team") must
# change existing code, but the evolution and repair agents only ever saw
# {path, chars} -- they would have had to rewrite app.py without reading it.
# Source files now carry their content within a bounded budget; anything over
# the budget (or noise such as lockfiles/vendor) stays a {path, chars} entry.
_CONTENT_SUFFIXES = ('.py', '.js', '.mjs', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.md', '.toml',
                     '.txt', '.cfg', '.ini', '.yml', '.yaml', '.sql', '.svelte', '.vue')
_CONTENT_SKIP_PREFIXES = ('node_modules/', 'vendor/', 'dist/', 'build/', '.git/', '.148ai/', 'rights/', 'docs/')
_CONTENT_SKIP_NAMES = ('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock')
_MAX_FILE_CONTENT_CHARS = 16_000
_MAX_TOTAL_CONTENT_CHARS = 64_000


# Crash run 37962802899 (2026-10-09): a single-file web app (server +
# embedded page) is larger than 16k characters, so the main file was left out
# and the repair model answered "app.py was omitted from prompt content".
# Files the failures name, and the app entry point, may be larger and go first.
_MAX_FOCUS_FILE_CHARS = 48_000
_ENTRY_NAMES = ('app.py', 'main.py', 'server.py', 'index.js', 'server.js', 'app.js')


def _content_eligible(path: str, content: str, limit: int = _MAX_FILE_CONTENT_CHARS) -> bool:
    low = path.lower()
    return (low.endswith(_CONTENT_SUFFIXES) and not low.startswith(_CONTENT_SKIP_PREFIXES)
            and low.rsplit('/', 1)[-1] not in _CONTENT_SKIP_NAMES and len(content) <= limit)


def focus_paths(repo: dict[str, str], failures=(), explicit=None) -> set[str]:
    """Files a repair most needs to see: those named in the failure text, and
    the top-level app entry point. An explicit, non-empty focus wins: the text is not searched."""
    if explicit:
        return set(explicit)
    text = ' '.join(f"{f.get('message', '')} {f.get('evidence', '')}" if isinstance(f, dict) else str(f) for f in failures)
    focus = {p for p in repo if '/' not in p and p in _ENTRY_NAMES}
    for p in repo:
        name = p.rsplit('/', 1)[-1]
        if len(name) > 3 and (p in text or name in text):
            focus.add(p)
    return focus


def repo_summary(repo: dict[str, str], failures=(), focus=None) -> dict:
    files, budget = [], _MAX_TOTAL_CONTENT_CHARS
    focus = focus_paths(repo, failures, focus)
    # .omni/project.json, then the focus files, then smaller files first, so
    # the manifest and the code under repair fit before large ones exhaust the budget.
    order = sorted(repo, key=lambda p: (p != '.omni/project.json', p not in focus, len(repo[p]), p))
    included = set()
    for path in order:
        content = repo[path]
        limit = _MAX_FOCUS_FILE_CHARS if path in focus else _MAX_FILE_CONTENT_CHARS
        if _content_eligible(path, content, limit) and len(content) <= budget:
            included.add(path); budget -= len(content)
    for path, content in sorted(repo.items()):
        entry = {'path': path, 'chars': len(content)}
        if path in included:
            entry['content'] = content
        files.append(entry)
    return {
        'files': files,
        'file_count': len(repo),
        'total_chars': sum(len(c) for c in repo.values()),
        'content_note': 'entries with "content" hold the full current file; patch files by returning full new content',
    }


def _check_repair_rounds(max_repair_rounds) -> None:
    """The same bounds as AutonomousProductEngine: an int (a bool is not a round count) from 0 to the hard maximum."""
    from .autonomous_core import REPAIR_ROUNDS_HARD_MAX
    if (isinstance(max_repair_rounds, bool) or not isinstance(max_repair_rounds, int)
            or not 0 <= max_repair_rounds <= REPAIR_ROUNDS_HARD_MAX):
        raise ValueError(f'max_repair_rounds must be an integer from 0 to {REPAIR_ROUNDS_HARD_MAX}')


def run_free_repair(*, spec: ProductSpec, repository: dict[str, str], assessment: ChangeAssessment,
                     followup: str, repairer, executor: Executor,
                     max_repair_rounds: int = 3) -> tuple[dict[str, str], int, ExecutionReport, str]:
    """The system_bug/missing_requirement repair loop, shared by
    `ModifierEngine.modify()` and `modification_engine.CandidateModificationEngine`.

    Callers must have already classified `followup` into `assessment` and
    confirmed its category is one of the two free-repair categories --
    `ChangeAssessment.from_dict` guarantees `assessment.acceptance_ids` is
    non-empty and every id is real for those two categories, checked at
    classification time against this same `spec`, so it is not re-validated
    here. Returns `(candidate_repository, repair_rounds, final_report, stop_reason)`; the
    caller decides what a passing/failing report means for its own status
    vocabulary (`ModifierEngine` calls it 'applied'/'failed',
    `CandidateModificationEngine` calls it 'ready_for_review'/'failed').
    """
    _check_repair_rounds(max_repair_rounds)        # Brain 2 point 5 (2026-11-02)
    from .autonomous_core import AutonomousProductEngine
    failures = [
        AcceptanceFailure(acceptance_id=aid, message=assessment.reason, evidence=followup).__dict__
        for aid in assessment.acceptance_ids
    ]
    # Same stop-loss as AutonomousProductEngine's build loop (founder brief 2026-11-01, section 3): a repair that
    # leaves the repository unchanged, or returns it to an earlier state, ends the loop instead of paying for more
    # identical rounds; a candidate that gets less far than the best so far is discarded and the best is kept.
    _fingerprint, progress = AutonomousProductEngine._fingerprint, AutonomousProductEngine.progress
    # Stop condition 8 (founder 2026-11-01 23:33): the set of (acceptance_id, message) -- no repository, no evidence;
    # see AutonomousProductEngine.failure_signature for why (Brain 2 point 6).
    signature = AutonomousProductEngine.failure_signature
    repo = dict(repository)
    # Brain 2 point 1 (2026-11-02): verify the repository once before the loop and seed best_report from it, so the
    # first repair is compared against a real report (a first candidate that is worse is discarded and the original
    # is kept). `report` stays None until a repair has been verified, so the classifier's failures always get one
    # repair (point 2: the loop runs while report is None or not passed).
    initial = executor.execute(repository=repo, spec=spec)
    report: ExecutionReport | None = None
    rounds = 0
    seen = {_fingerprint(repo)}
    best_repo, best_report = repo, initial
    stop_reason = 'max_repair_rounds'
    while (report is None or not report.passed) and rounds < max_repair_rounds:
        rounds += 1
        patch = repairer.repair(spec=spec, repo_summary=repo_summary(repo, failures), failures=failures)
        if not patch:
            stop_reason = 'no_progress_empty_patch'       # Brain 2 point 4: its own label
            break
        candidate = apply_patch(repo, patch)
        fingerprint = _fingerprint(candidate)
        if fingerprint in seen:
            stop_reason = ('no_progress_repository_unchanged' if candidate == repo
                           else 'no_progress_repository_cycle')
            break
        seen.add(fingerprint)
        new_report = executor.execute(repository=candidate, spec=spec)
        if new_report.passed:
            repo, report, stop_reason = candidate, new_report, 'passed'
            break
        if progress(new_report) < progress(best_report):
            # discarded: this repair went backwards; the next round starts again from the best candidate
            failing = '; '.join(f'{f.acceptance_id}: {f.message}' for f in new_report.failures[:4])
            repo, report = best_repo, best_report
            failures = [f.__dict__ for f in report.failures] + [{
                'acceptance_id': 'REPAIR_REGRESSION',
                'message': 'Your previous change made the product worse and was discarded; this is the better '
                           'version again. Do not repeat that change.',
                'evidence': failing[:600]}]
            continue
        previous = report if report is not None else initial
        same_failure = signature(new_report) == signature(previous)
        repo, report = candidate, new_report
        if progress(report) >= progress(best_report):
            best_repo, best_report = repo, report
        if same_failure:
            stop_reason = 'no_progress_same_failure'   # the same (acceptance_id, message) set as the round before
            break
        failures = [f.__dict__ for f in report.failures]
    if report is None:
        report = initial                                # no repair was verified: the original's own report
    if not report.passed:
        repo, report = best_repo, best_report           # Brain 2 point 3: a failed loop returns the best, explicitly
    if report.passed:
        stop_reason = 'passed' if repo != dict(repository) else 'no_repair_adopted'
    return repo, rounds, report, stop_reason

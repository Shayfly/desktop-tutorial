"""QA Verifier: an independent review of a product that already passes its tests.

Agent OS spec §4 (2026-10-08): "QA does not accept 'done' from the developer
agent as proof; it checks the product." Tests written by the generator check
what the generator thought of; the founder's first product passed them and
still accepted year 2356, used alert() and hid new rows behind a filter.

After the inner executors pass (tests, preview start, quality), this executor
1. runs the skills' deterministic static checks over the repository, and
2. asks a reviewer model (task 'review'; the gateway prefers a model other
   than the one that wrote the code) to check the product against the spec
   and the skills' checklists.
Blocking findings become repairable REVIEW failures, at most `max_reviews`
times per build; after that they are kept as advisory evidence so a build is
never stuck in review. A reviewer outage is recorded as "not reviewed" and
does not fail the build (it never claims a review that did not happen).
"""
from __future__ import annotations

import json
from decimal import Decimal

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .skills_runtime import applied_skills, checklist_for_review, static_findings

# Gates whose quarantine must never pass silently (Michael 2026-11-10): a Hebrew page served LTR, a fabricated phone, a
# missing alt. Their quarantine keeps the build moving but withdraws release_ready and shows a banner on the preview.
CRITICAL_GATES = frozenset({'skill.text_locale', 'skill.copy_quality', 'skill.accessibility'})


def install_review_request(engine, prompt: str) -> bool:
    """Give the review the approved request so its fact canon is the one the customer approved."""
    from .behavior_acceptance import find_in_chain
    review = find_in_chain(getattr(engine, 'executor', None), ProductReviewExecutor)
    if review is None:
        return False
    review._request = prompt or ''
    review.canon = None
    return True

REVIEW_FAILURE_ID = 'REVIEW'

_REVIEW_SYSTEM = (
    'You are the QA Verifier of a product-building platform. You did not write this code. Review the repository '
    'against the approved spec and the checklist, as a demanding user of the running product would. Report only real '
    'problems you can point to in the code; do not restate passing checks and do not ask for new features beyond the '
    'spec and checklist. Return only JSON: {"findings": [{"skill": "<checklist skill key or spec>", "severity": '
    '"blocking" | "advisory", "file": "<path>", "problem": "<what a user would experience>", "fix": "<concrete '
    'change>"}]}. blocking = a user-visible defect against the spec or checklist (wrong data accepted, error shown in '
    'a browser dialog, an excluded feature present, data shown escaped or hidden, a crash, a security hole); '
    'advisory = everything else, including defects that need unusual timing, rapid repeated clicks or a slow '
    'network to appear, hostile or malformed input no real user sends (integers beyond 64 bits, lone surrogates, '
    'deeply nested JSON, whitespace-only bodies) unless it corrupts or leaks data, and polish beyond the checklist. '
    'When "previous_blocking" is given, this is a re-review after a repair: block only on a previous finding that '
    'is still present, a regression the repair introduced, data loss or corruption, or a security hole; every other '
    'new observation is advisory. At most '
    '6 findings, most important first. Write problem and fix in English.'
)


class ProductReviewExecutor:
    def __init__(self, inner, *, gateway=None, max_reviews: int = 2, request_text: str = ''):
        self._inner = inner
        self._gateway = gateway
        self._max_reviews = max_reviews
        self._request = request_text
        self.reviews: list[dict] = []
        # Michael 2026-11-10 §4: a static gate that repeats the same finding in three consecutive rounds is suspected
        # of judging the wrong artefact. It is quarantined: reported as advisory with the reason, and the rounds it
        # cost are counted as gate waste in the evidence.
        self.quarantined: list[dict] = []
        self.gate_waste_rounds = 0
        self.gate_waste_usd = Decimal('0')          # measured: gateway spend between the repeated reviews
        self.gate_waste_calls = 0
        self._spend_at_review: list[tuple[Decimal, int]] = []
        self.canon = None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def _context(self, spec) -> dict:
        text = ' '.join(str(x) for x in (self._request, getattr(spec, 'title', ''), getattr(spec, 'summary', '')))
        ctx = {'request': text}
        # The page the product SERVES (preview smoke, same round), so no gate judges a string inside page.py.
        from .behavior_acceptance import find_in_chain
        from .preview_smoke import PreviewReadyExecutor
        preview = find_in_chain(self._inner, PreviewReadyExecutor)
        pages = getattr(preview, 'last_pages', None) if preview is not None else None
        if isinstance(pages, dict):
            ctx['rendered_pages'] = pages
        if self.canon is None:
            from .fact_canon import build_canon
            self.canon = build_canon(self._request or text)
        ctx['canon'] = self.canon
        return ctx

    def _spend(self) -> tuple[Decimal, int]:
        state = getattr(self._gateway, 'state', None)
        if state is None:
            return Decimal('0'), 0
        return (Decimal(str(getattr(state, 'external_spend_usd', 0) or 0)), int(getattr(state, 'external_calls', 0) or 0))

    def _quarantine(self, static: list[dict]) -> list[dict]:
        """Michael 2026-11-10 condition 1. A gate is quarantined only when THREE consecutive rounds show the same finding
        AND the DOM node it points at is byte-identical across them (the `anchor`). If the product changed at that
        point, the repair is working on it and the finding is a product bug, never a probe bug. CRITICAL gates (dir,
        tel/contact truth, alt) never release silently: the finding stays listed, release_ready is withdrawn by the
        worker, the preview carries a banner. The quarantine lives for this build only (gates are stateless per
        build), so it expires on the next build by construction."""
        if len(self.reviews) < 2:
            return static
        def blocking_static(review):
            return {(f['skill'], f['problem'], f.get('anchor')) for f in review.get('findings', ())
                    if f.get('source') == 'static' and f.get('severity') == 'blocking' and f.get('anchor')}
        repeated = blocking_static(self.reviews[-1]) & blocking_static(self.reviews[-2])
        out = []
        for f in static:
            key = (f['skill'], f['problem'], f.get('anchor'))
            if f['severity'] == 'blocking' and f.get('anchor') and key in repeated:
                critical = f['skill'] in CRITICAL_GATES
                note = ('same static finding and identical DOM node in three consecutive rounds: the gate is suspected '
                        'of judging the wrong artefact')
                f = {**f, 'severity': 'advisory', 'quarantined': note, 'classification': 'probe_bug', 'critical': critical}
                if not any(q['skill'] == f['skill'] and q['problem'] == f['problem'] for q in self.quarantined):
                    self.quarantined.append({'skill': f['skill'], 'problem': f['problem'], 'anchor': f.get('anchor'),
                                             'round': len(self.reviews) + 1, 'critical': critical})
                    self.gate_waste_rounds += 2
                    # Measured, not estimated: spend and calls between the first repeat and now (the two wasted rounds).
                    if len(self._spend_at_review) >= 2:
                        now_usd, now_calls = self._spend()
                        base_usd, base_calls = self._spend_at_review[-2]
                        self.gate_waste_usd += max(now_usd - base_usd, Decimal('0'))
                        self.gate_waste_calls += max(now_calls - base_calls, 0)
            out.append(f)
        return out

    def _llm_findings(self, repository: dict, spec) -> tuple[list[dict], dict]:
        if self._gateway is None:
            return [], {'reviewer': 'not configured'}
        from .modifier_engine import repo_summary
        payload = {
            'spec': {'title': getattr(spec, 'title', ''), 'summary': getattr(spec, 'summary', ''),
                     'requirements': [{'id': r.id, 'text': r.text} for r in getattr(spec, 'requirements', ())],
                     'acceptance': [{'id': a.id, 'text': a.text} for a in getattr(spec, 'acceptance', ())]},
            'checklist': checklist_for_review(),
            'repository': repo_summary(repository),
        }
        previous = self._previous_blocking()
        if previous:
            payload['previous_blocking'] = previous
        kwargs = dict(system=_REVIEW_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=3000)
        try:
            if getattr(self._gateway, 'accepts_task_tag', False):
                data = self._gateway.complete_json(task='review', **kwargs)
            else:
                data = self._gateway.complete_json(**kwargs)
        except Exception as exc:  # outage: say so, never invent a review
            return [], {'reviewer': 'unavailable', 'error': f'{type(exc).__name__}: {exc}'[:300]}
        usage = getattr(self._gateway, 'last_usage', None)
        meta = {'reviewer': 'model', 'model': getattr(usage, 'model', None)}
        items = data.get('findings') if isinstance(data, dict) else None
        out = []
        for f in (items if isinstance(items, list) else [])[:6]:
            if not isinstance(f, dict) or not str(f.get('problem', '')).strip():
                continue
            sev = 'blocking' if str(f.get('severity', '')).lower() == 'blocking' else 'advisory'
            out.append({'skill': str(f.get('skill', ''))[:60], 'severity': sev, 'file': str(f.get('file', ''))[:200],
                        'problem': str(f.get('problem', ''))[:400], 'fix': str(f.get('fix', ''))[:400],
                        'source': 'reviewer'})
        return out, meta

    # Founder build bld_9bd3c1c4 (2026-11-09): every test and behaviour check passed, yet five review rounds each
    # found NEW edge cases (64-bit overflow, lone surrogates, deeply nested JSON) and the build failed on the last.
    # A re-review converges: a blocking finding stays blocking only when it repeats a previous blocking finding
    # (same skill and file), or concerns security or data integrity; anything else new becomes advisory.
    _ALWAYS_BLOCKING = frozenset({'skill.security_basics', 'skill.data_integrity'})

    def _served(self) -> bool:
        from .behavior_acceptance import find_in_chain
        from .preview_smoke import PreviewReadyExecutor
        preview = find_in_chain(self._inner, PreviewReadyExecutor)
        return bool(preview is not None and getattr(preview, 'last_pages', None))

    def _previous_blocking(self) -> list:
        prior = [f for r in self.reviews for f in r.get('findings', ())
                 if f.get('severity') == 'blocking' and f.get('source') == 'reviewer']
        return [{'skill': f['skill'], 'file': f['file'], 'problem': f['problem']} for f in prior][-12:]

    def _converge(self, llm: list) -> list:
        prior = {(f['skill'], f['file'].split(':')[0]) for f in self._previous_blocking()}
        if not self.reviews:
            return llm
        out = []
        for f in llm:
            key = (f['skill'], f['file'].split(':')[0])
            if f['severity'] == 'blocking' and key not in prior and f['skill'] not in self._ALWAYS_BLOCKING:
                f = {**f, 'severity': 'advisory', 'downgraded': 'new finding in a re-review'}
            out.append(f)
        return out

    # VerificationGroup (2026-10-19): the review is one of the post-build checks and tells the group it wants to know
    # whether the other checks failed in the same round.
    group_context = True

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        return self.check(repository=repository, spec=spec, report=report)

    def check(self, *, repository, spec, report, others_failed: bool = False):
        """The review on a report in which the build passed. `max_reviews` bounds the review ROUNDS that block: a round
        counts only when the review is what still blocks (others_failed=False), exactly as when it ran last. While
        other checks fail in the same round its blocking findings are reported alongside them without using the cap."""
        findings = self._quarantine([f.to_dict() for f in static_findings(repository, self._context(spec))])
        self._spend_at_review.append(self._spend())
        llm, meta = self._llm_findings(repository, spec)
        findings += self._converge(llm)
        blocking = [f for f in findings if f['severity'] == 'blocking']
        enforce = others_failed or len([r for r in self.reviews if r['enforced'] and not r.get('alongside')]) < self._max_reviews
        self.reviews.append({'round': len(self.reviews) + 1, 'enforced': bool(blocking) and enforce, **meta,
                             'alongside': others_failed, 'canon_hash': getattr(self.canon, 'hash', None),
                             'judged': 'served page' if self._served() else 'repository files',
                             'blocking': len(blocking), 'findings': findings, 'skills': applied_skills()})
        if not blocking or not enforce:
            return report
        failures = tuple(AcceptanceFailure(REVIEW_FAILURE_ID, f"QA review ({f['skill']}): {f['problem']}",
                                           f"file: {f['file']}\nfix: {f['fix']}") for f in blocking)
        return ExecutionReport(False, failures, report.build_log)

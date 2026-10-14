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

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .skills_runtime import applied_skills, checklist_for_review, static_findings

REVIEW_FAILURE_ID = 'REVIEW'

_REVIEW_SYSTEM = (
    'You are the QA Verifier of a product-building platform. You did not write this code. Review the repository '
    'against the approved spec and the checklist, as a demanding user of the running product would. Report only real '
    'problems you can point to in the code; do not restate passing checks and do not ask for new features beyond the '
    'spec and checklist. Return only JSON: {"findings": [{"skill": "<checklist skill key or spec>", "severity": '
    '"blocking" | "advisory", "file": "<path>", "problem": "<what a user would experience>", "fix": "<concrete '
    'change>"}]}. blocking = a user-visible defect against the spec or checklist (wrong data accepted, error shown in '
    'a browser dialog, an excluded feature present, data shown escaped or hidden); advisory = everything else. At most '
    '6 findings, most important first. Write problem and fix in English.'
)


class ProductReviewExecutor:
    def __init__(self, inner, *, gateway=None, max_reviews: int = 2, request_text: str = ''):
        self._inner = inner
        self._gateway = gateway
        self._max_reviews = max_reviews
        self._request = request_text
        self.reviews: list[dict] = []

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def _context(self, spec) -> dict:
        text = ' '.join(str(x) for x in (self._request, getattr(spec, 'title', ''), getattr(spec, 'summary', '')))
        return {'request': text}

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

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        findings = [f.to_dict() for f in static_findings(repository, self._context(spec))]
        llm, meta = self._llm_findings(repository, spec)
        findings += llm
        blocking = [f for f in findings if f['severity'] == 'blocking']
        enforce = len([r for r in self.reviews if r['enforced']]) < self._max_reviews
        self.reviews.append({'round': len(self.reviews) + 1, 'enforced': bool(blocking) and enforce, **meta,
                             'blocking': len(blocking), 'findings': findings, 'skills': applied_skills()})
        if not blocking or not enforce:
            return report
        failures = tuple(AcceptanceFailure(REVIEW_FAILURE_ID, f"QA review ({f['skill']}): {f['problem']}",
                                           f"file: {f['file']}\nfix: {f['fix']}") for f in blocking)
        return ExecutionReport(False, failures, report.build_log)

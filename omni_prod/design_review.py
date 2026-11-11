"""Design critic (CEO 2026-11-09): a vision model looks at the product the way a senior designer does.

Visual QA measures the page (overflow, contrast, touch size...) but nobody LOOKED at it. After visual QA has
taken its desktop and mobile screenshots, this critic sends both to a vision-capable model (routed like every
other call: the build budget and hard cap apply) with the customer's request and the design skills, and gets
back a score and concrete findings.

No new dead ends ("I don't want to see builds getting stuck"):
  * Only `must_fix` findings can block, and only ONCE per build: the first time, they become one repair round
    ("design polish"); after that every finding is advisory and recorded.
  * `must_fix` is limited to what a customer would reject at a glance: the page looks empty or broken, text is
    unreadable, an element the customer explicitly asked for is missing or invisible, colours contradict an
    explicit request. Taste is always a suggestion.
  * Any error (no vision route, model outage, unparsable answer) records the reason and passes.

Screenshots are sent to the routed model provider for this review. Rollout: founder builds only
(OMNI_DESIGN_REVIEW=founder, the default; 'all' for everyone; '0' off).
"""
from __future__ import annotations

import json

DESIGN_FAILURE_ID = 'DESIGN'

_SYSTEM = (
    'You are the senior product designer reviewing a generated product before the customer sees it. You get two '
    'screenshots (first desktop 1440x900, then mobile 390x844) of the first screen, and the customer\'s request. '
    'Judge it as a demanding art director: visual hierarchy (one clear focal point and primary action), spacing and '
    'alignment, typography (sizes, line length, Hebrew/RTL correctness), colour (matches what the customer asked '
    'for, enough contrast, a coherent palette), imagery and polish, and whether the first screen tells a visitor '
    'what this is and what to do. For a game: readability of the play area, controls and score; for a landing '
    'page: offer, trust and the call to action above the fold.\n'
    'Answer ONE JSON object: {"score": <0-100>, "summary": "<one sentence>", "findings": [{"severity": '
    '"must_fix" | "suggestion", "area": "hierarchy|spacing|typography|colour|content|layout|accessibility|brand", '
    '"viewport": "desktop|mobile|both", "problem": "<what a visitor experiences>", "fix": "<concrete CSS/HTML-level '
    'change>"}]}. At most 6 findings, most important first.\n'
    'must_fix ONLY for what a customer would reject at a glance: the page looks empty, broken or unstyled; text is '
    'unreadable; an element the customer explicitly asked for is missing or not visible on the first screen; '
    'colours contradict an explicit request. Everything else, including taste, is a suggestion.'
)


class DesignCritic:
    def __init__(self, gateway, *, request_text: str = ''):
        self.gateway = gateway
        self.request_text = (request_text or '')[:6000]
        self.reviews: list[dict] = []
        self.polish_rounds_used = 0

    def review(self, *, spec, shots: dict[str, bytes]) -> dict:
        images = tuple(shots[v] for v in ('desktop', 'mobile') if shots.get(v))
        if not images:
            return self._record({'status': 'NOT_RUN', 'reason': 'no screenshots'})
        payload = {
            'customer_request': self.request_text,
            'product': {'title': getattr(spec, 'title', ''), 'summary': getattr(spec, 'summary', ''),
                        'requirements': [r.text for r in getattr(spec, 'requirements', ())][:20]},
            'screenshots': [v for v in ('desktop', 'mobile') if shots.get(v)],
        }
        kwargs = dict(system=_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=2500, images=images)
        try:
            if getattr(self.gateway, 'accepts_task_tag', False):
                data = self.gateway.complete_json(task='review', **kwargs)
            else:
                data = self.gateway.complete_json(**kwargs)
        except Exception as exc:
            return self._record({'status': 'NOT_RUN', 'reason': f'{type(exc).__name__}: {exc}'[:300]})
        if not isinstance(data, dict):
            return self._record({'status': 'NOT_RUN', 'reason': 'not a JSON object'})
        findings = []
        for f in (data.get('findings') or [])[:6]:
            if not isinstance(f, dict) or not str(f.get('problem', '')).strip():
                continue
            findings.append({'severity': 'must_fix' if f.get('severity') == 'must_fix' else 'suggestion',
                             'area': str(f.get('area', ''))[:30], 'viewport': str(f.get('viewport', ''))[:10],
                             'problem': str(f.get('problem', ''))[:400], 'fix': str(f.get('fix', ''))[:400]})
        try:
            score = max(0, min(100, int(data.get('score'))))
        except (TypeError, ValueError):
            score = None
        usage = getattr(self.gateway, 'last_usage', None)
        return self._record({'status': 'REVIEWED', 'score': score, 'summary': str(data.get('summary', ''))[:300],
                             'findings': findings, 'model': getattr(usage, 'model', None)})

    def _record(self, review: dict) -> dict:
        review['round'] = len(self.reviews) + 1
        self.reviews.append(review)
        return review

    def failures(self, review: dict) -> tuple:
        """The one design-polish round: must_fix findings, the first time only."""
        from .autonomous_core import AcceptanceFailure
        must = [f for f in review.get('findings', ()) if f['severity'] == 'must_fix']
        if not must or self.polish_rounds_used >= 1:
            return ()
        self.polish_rounds_used += 1
        review['polish_round'] = True
        return tuple(AcceptanceFailure(DESIGN_FAILURE_ID, f"design ({f['area']}, {f['viewport']}): {f['problem']}",
                                       f"fix: {f['fix']}. Keep everything that already works; change styles and "
                                       f"markup only where this finding points.") for f in must[:5])


def install_design_critic(engine, request: dict, prompt: str) -> bool:
    """Founder builds by default (OMNI_DESIGN_REVIEW=founder|all|0)."""
    import os
    mode = os.getenv('OMNI_DESIGN_REVIEW', 'founder').strip().lower()
    if mode in ('0', 'off', 'false', ''):
        return False
    if mode != 'all':
        from .pricing import m5_founder_account
        if not m5_founder_account((request or {}).get('user_id')):
            return False
    from .behavior_acceptance import find_in_chain
    from .visual_qa import VisualQAExecutor
    target = find_in_chain(getattr(engine, 'executor', None), VisualQAExecutor)
    gateway = getattr(getattr(engine, 'repairer', None), 'gateway', None)
    if target is None or gateway is None:
        return False
    from .attempt_ledger import TaskTaggedGateway
    inner = getattr(gateway, '_inner', gateway)
    target.design_critic = DesignCritic(TaskTaggedGateway(inner, 'review'), request_text=prompt)
    return True

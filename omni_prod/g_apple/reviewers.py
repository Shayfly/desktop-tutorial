"""G-APPLE, part 4: two separate vision reviewers (the owner, 2026-11-17).

Each one LOOKS at the screenshots visual QA took (desktop 1440, phone 390) and answers with findings only. They are
two calls with two instructions and no shared context, so one cannot agree with the other out of habit:

  typography_layout   hierarchy, type sizes and rhythm, alignment, spacing, line length, what is cut or crowded
  brand_category      does the page carry THIS business's marks -- its name, its trade, its own offer -- or could
                      the same page belong to any business; the category clause: it must name the marks it sees

A finding is {selector, severity, viewport, problem}. Severity is P0 (a customer would reject the page at a glance),
P1 (a designer would send it back) or P2 (polish). Only P0 can block, and only when the gate blocks. A reviewer
never proposes code and never touches it: the repair round gets the problem and where it is, nothing more.

A reviewer that cannot run -- no vision route, an error, an answer that is not the expected JSON -- is NOT_RUN with
its reason, said in the evidence; it is never counted as "no findings".
"""
from __future__ import annotations

import json

SEVERITIES = ('P0', 'P1', 'P2')
MAX_FINDINGS = 8
_SHAPE = ('Answer ONE JSON object: {"findings": [{"selector": "<the CSS selector or plain name of the element, e.g. '
          'header h1, .hero, the menu table>", "severity": "P0" | "P1" | "P2", "viewport": "desktop" | "phone" | "both", '
          '"problem": "<what a visitor sees, one sentence>"}]%s}. At most 8 findings, the worst first. P0 ONLY for what a '
          'customer would reject at a glance. P1: a designer would send it back. P2: polish. Describe the problem; do '
          'NOT write code, CSS or a fix. An empty findings list means you looked and found nothing.')
SYSTEM = {
    'typography_layout': (
        'You are a typography and layout reviewer. You get screenshots of one web page (first desktop 1440 px wide, '
        'then phone 390 px wide) and nothing else matters to you but type and layout: is there one clear hierarchy '
        '(one dominant heading, a second level, body text); are sizes on a consistent scale; is spacing rhythmic and '
        'aligned to a grid; are lines of body text a comfortable length; is anything cut, overlapping, crowded, '
        'orphaned or misaligned; is right-to-left text set correctly. P0 examples: text unreadable or cut, elements '
        'overlapping, a page that looks unstyled, no visible hierarchy at all. ' + _SHAPE % ''),
    'brand_category': (
        'You are a brand reviewer. You get screenshots of one web page (first desktop, then phone) and the business '
        'it was built for. Your only question: does this page belong to THIS business? List the marks of the business '
        'you can actually SEE on the page -- its name, its trade (what it sells or does), its own offer, prices, '
        'place, people or products. A page that could be any business with the name swapped has no marks. P0 '
        'examples: the business name is not visible, the page shows a different trade than the business, the first '
        'screen says nothing about what the business does, the imagery contradicts the trade. '
        + _SHAPE % ', "category_marks": ["<each mark of this business you see, in a few words>"]'),
}
REVIEWERS = tuple(SYSTEM)


def review(gateway, name: str, shots: dict, *, business: str = '') -> dict:
    """One reviewer's verdict: {'reviewer', 'status': 'REVIEWED'|'NOT_RUN', 'findings', 'p0', ...}."""
    if name not in SYSTEM:
        raise ValueError(f'unknown reviewer: {name!r}')
    base = {'reviewer': name}
    images = tuple(shots[v] for v in ('desktop', 'mobile') if shots.get(v))
    if not images:
        return {**base, 'status': 'NOT_RUN', 'reason': 'no screenshots'}
    if gateway is None:
        return {**base, 'status': 'NOT_RUN', 'reason': 'no vision gateway'}
    user = {'screenshots': [v for v in ('desktop', 'mobile') if shots.get(v)]}
    if name == 'brand_category':
        user['business'] = (business or '')[:1500]
    kwargs = dict(system=SYSTEM[name], user=json.dumps(user, ensure_ascii=False), max_tokens=1800, images=images)
    try:
        data = gateway.complete_json(task='review', **kwargs) if getattr(gateway, 'accepts_task_tag', False) \
            else gateway.complete_json(**kwargs)
    except Exception as exc:
        from ..verification_verdict import reraise_control
        reraise_control(exc)                   # a cancel, a deadline or a budget stop ends the build
        return {**base, 'status': 'NOT_RUN', 'reason': f'{type(exc).__name__}: {exc}'[:300]}
    if not isinstance(data, dict) or not isinstance(data.get('findings'), list):
        return {**base, 'status': 'NOT_RUN', 'reason': 'the answer is not {"findings": [...]}'}
    findings = []
    for f in data['findings'][:MAX_FINDINGS]:
        if not isinstance(f, dict) or f.get('severity') not in SEVERITIES or not str(f.get('problem', '')).strip():
            return {**base, 'status': 'NOT_RUN', 'reason': f'a finding is not in the expected shape: {str(f)[:120]}'}
        findings.append({'selector': str(f.get('selector', ''))[:120], 'severity': f['severity'],
                         'viewport': str(f.get('viewport', ''))[:10], 'problem': str(f['problem'])[:400]})
    out = {**base, 'status': 'REVIEWED', 'findings': findings,
           'p0': sum(1 for f in findings if f['severity'] == 'P0'),
           'model': getattr(getattr(gateway, 'last_usage', None), 'model', None)}
    if name == 'brand_category':
        marks = data.get('category_marks')
        if not isinstance(marks, list):
            return {**base, 'status': 'NOT_RUN', 'reason': 'the brand reviewer did not list category_marks'}
        out['category_marks'] = [str(m)[:120] for m in marks[:10] if str(m).strip()]
        if not out['category_marks']:
            # the category clause: a page with no mark of its business is generic, whatever else was said
            out['findings'].insert(0, {'selector': 'page', 'severity': 'P0', 'viewport': 'both',
                                       'problem': 'the page carries no visible mark of this business: it could belong '
                                                  'to any business'})
            out['p0'] += 1
    return out

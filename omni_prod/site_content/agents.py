"""The content route's three engine parts and its two model agents.

  ContentSpecArchitect   no model call: the content-only floor spec (ProductArchitect._content_only_spec); the worker's
                         wrappers add CUSTOMER-FACTS, the outline, PLATFORM-CHECKS and DESIGN-CONTRACT as today
  ContentSiteGenerator   one ContentAgent call (copy only, one JSON document), validated; up to MAX_CORRECTIONS (3)
                         corrective calls in all -- a whole-document correction for a blocking validation problem, or
                         a rewrite of the named paths for a blocking gate finding inside the copy -- each one logged
                         in the build evidence (site_route.correction_rounds); then the platform renders, runs the
                         gates that judge a page before any sandbox time (each in its own mode: a warn finding goes to
                         the evidence), and writes the repository. The owner, 2026-11-26 (WAREHOUSE 136, option a):
                         one correction and then a failed build was a limit that is not money; it became three
  ContentSiteRepairer    after a failed round: attribute every failure with the OWNER table. Platform -> RepairDeclined
                         ('platform_render_defect'), zero model calls. Customer -> needs_customer_input. Content -> one
                         ContentRepairAgent call that may set ONLY the JSON paths the findings point at; validated,
                         re-rendered; the patch holds content/site.json and public/index.html only
  AdvisoryFilterExecutor the design critic's must_fix and the model reviewer's findings are recorded as library feedback
                         (core.site_feedback) and taken out of the round's failures: never a decline, never a repair
  SiteParityExecutor     the served GET / is the rendered page (cut where the preview cuts it), and the repository
                         holds no other page; a new check, so it enters gate.CALIBRATING (SITE_PARITY) at warn

After a correction, a document whose only blocking problems are invented facts (INVENTED: a price, a number, a
count, a channel, a review the customer never gave) loses exactly the sentences that state them, deterministically,
recorded in the evidence ('stripped'), before another correction is spent on them; a required field that would be
left empty, or any other problem, goes on to the next correction and, once the MAX_CORRECTIONS are spent, fails
(strip_invented).

Every loop is bounded (at most MAX_CORRECTIONS corrective calls per generation, one rewrite call per repair round, the
engine's own round bounds), every failure is loud (SiteContentInvalid, SiteRenderDefect, RepairDeclined), and there is
no fallback to the legacy generator once the route was chosen.

Tokens (the owner, 2026-11-26 ~16:10 UTC: "לבטל מגבלה על טוקנים כרגע רק מדידה"): there is no product-chosen
output cap on the content path. Each call asks for its model's own documented maximum (output_maximum: the catalogue's
max_output_tokens; the router then gives each model exactly its own), and every call is MEASURED -- its real input and
output tokens, its metered cost, its model and why it stopped -- into the build evidence (site_route.content_usage:
every call and the build's totals); the same attempts are in the attempt ledger. A call that stops at the model's
maximum is said loudly there (truncated_at_model_maximum, SITE_CONTENT_TRUNCATED in the log). What a correction costs is
that measurement, per build. The money caps stay (the build's reservation and the per-build ceiling, warehouse 136):
the router still authorizes every call against the build's budget.
"""
from __future__ import annotations

import ast
import html as _html
import json
import logging
import re
from dataclasses import replace

from ..autonomous_core import AcceptanceFailure, ExecutionReport, RepairDeclined
from ..preview_smoke import served_cut
from ..domain_registry import domain_by_slug
from ..repository_patch import FilePatch
from . import facts as Fx
from . import legal as LG
from . import owners as O
from . import render as R
from . import schema as K
from . import validate as V

_LOG = logging.getLogger(__name__)
PREVIEW_CUT = 45_000                  # preview_smoke keeps the first 45,000 characters of GET / for the truth gate
PREPASS_GATES = ('G1', 'G3', 'G10', 'G11', 'HE', 'BRAND', 'SHARE', 'PRO')
# The owner, 2026-11-26 (WAREHOUSE 136, option a): corrective calls per generation -- a fixed, stated bound (CLAUDE.md
# section 3). It was 1. Each round is logged in the build evidence (site_route.correction_rounds) and the bound is
# said there (site_route.correction_bound) and in the failure message.
MAX_CORRECTIONS = 3
# Review S5, narrowed by the owner's order of 2026-11-26 16:10: the only room left is the model's own output maximum.
# The model is told that room and, only when a list would really not fit in it, names the list in the document's
# `shortened`; the evidence records it with the sentence for the customer (site_route.shortened, .shortened_said):
# recorded and returned by the API, on screen once the apps bundle shows it. ESTIMATE: about 2.5 characters of Hebrew
# JSON per token (not measured on a tokenizer here).
CHARS_PER_TOKEN_ESTIMATE = 2.5
_REPO_CATALOG = __import__('pathlib').Path(__file__).resolve().parents[2] / 'infra' / 'worker-host' / 'model-catalog.json'


def output_maximum(gateway) -> int:
    """The model's own documented output maximum to ask for: the largest max_output_tokens of the catalogue the
    gateway routes over (RoutedModelGateway.ranked -- each route is then clamped to ITS model's maximum by
    ranked_routes); with no routed catalogue, the runtime catalogue (OMNI_MODEL_CATALOG_JSON), else the repository's
    (infra/worker-host/model-catalog.json). A catalogue entry without the field counts 8,192, as model_catalog reads it."""
    import os
    ranked = getattr(gateway, 'ranked', None)
    if isinstance(ranked, (list, tuple)) and ranked:
        return max(int(m.max_output_tokens) for m in ranked)
    raw = os.environ.get('OMNI_MODEL_CATALOG_JSON', '').strip()
    items = json.loads(raw) if raw else json.loads(_REPO_CATALOG.read_text(encoding='utf-8'))
    return max(int(i.get('max_output_tokens', 8192)) for i in items)


_TRUNCATED = ('length', 'max_tokens')


def _measured(gateway, start, role: str, max_tokens: int) -> dict:
    """One content call as the router recorded it: every attempt's model, tokens, metered cost and why it stopped."""
    recorder = getattr(gateway, 'recorder', None)
    records = getattr(recorder, 'records', None)
    if start is None or not isinstance(records, list):
        return {'role': role, 'max_tokens': max_tokens, 'measured': False,
                'why': 'the gateway keeps no attempt records (not a routed gateway)'}
    output = getattr(gateway, 'attempt_output', None) or {}
    attempts = []
    for r in records[start:]:
        if getattr(r, 'kind', None) != 'provider_call':
            continue
        seen = output.get(r.attempt_seq) or {}
        reason, sent, maximum = seen.get('finish_reason'), seen.get('max_tokens_sent'), seen.get('model_maximum')
        failure = str(getattr(r, 'failure_reason', '') or '')
        truncated = reason in _TRUNCATED or any(f'finish_reason={t}' in failure for t in _TRUNCATED)
        # stopped at the model's own maximum, or at a smaller allowance the build's money left (fit_to_budget)
        at_maximum = truncated and (maximum is None or sent is None or int(sent) >= int(maximum))
        attempts.append({'model': r.model, 'outcome': r.outcome, 'input_tokens': r.input_tokens,
                         'output_tokens': r.output_tokens,
                         'metered_cost_usd': None if r.metered_cost_usd is None else str(r.metered_cost_usd),
                         'max_tokens_sent': sent, 'model_maximum': maximum, 'finish_reason': reason,
                         'truncated_at_model_maximum': at_maximum,
                         'truncated_at_budget_allowance': truncated and not at_maximum})
        if truncated:
            _LOG.error('SITE_CONTENT_TRUNCATED role=%s model=%s output_tokens=%s max_tokens_sent=%s model_maximum=%s '
                       'at=%s', role, r.model, r.output_tokens, sent, maximum,
                       'model_maximum' if at_maximum else 'budget_allowance')
    return {'role': role, 'max_tokens': max_tokens, 'measured': True, 'attempts': attempts}


def usage_summary(calls: list[dict]) -> dict:
    """The build's content calls and their totals (site_route.content_usage). A total is None when any attempt did not
    report its number -- never a silent 0."""
    attempts = [a for c in calls if c.get('measured') for a in c['attempts']]
    unmeasured = any(not c.get('measured') for c in calls)

    def total(key, cast):
        values = [a[key] for a in attempts]
        if unmeasured or any(v is None for v in values):       # an unmeasured call makes the total unknown, not 0
            return None
        return sum(values) if cast is int else str(sum(cast(v) for v in values))
    from decimal import Decimal
    return {'calls': len(calls), 'attempts': len(attempts), 'unmeasured_calls': sum(1 for c in calls if not c.get('measured')),
            'input_tokens': total('input_tokens', int), 'output_tokens': total('output_tokens', int),
            'metered_cost_usd': total('metered_cost_usd', Decimal),
            'truncated_at_model_maximum': [c['role'] for c in calls if any(a['truncated_at_model_maximum']
                                                                           for a in c.get('attempts', ()))],
            'truncated_at_budget_allowance': [c['role'] for c in calls if any(a['truncated_at_budget_allowance']
                                                                              for a in c.get('attempts', ()))],
            'per_call': calls}


class SiteContentInvalid(RuntimeError):
    """The model's content document is still invalid after its corrections (at most MAX_CORRECTIONS). failure_code
    'site_content_invalid'."""

    def __init__(self, message: str, problems=()):
        super().__init__(message)
        self.problems = [p.to_dict() if hasattr(p, 'to_dict') else dict(p) for p in problems]


SiteRenderDefect = R.SiteRenderDefect

_CONTENT_SYSTEM = (
    "You write the Hebrew copy of a small business's website for 148AI. You write COPY ONLY, as ONE JSON object in "
    "the exact shape you are given; the platform designs and renders the page and fills every fact itself. Rules, "
    "each one checked by a program before anything is shown:\n"
    "- Never write a phone number, e-mail, street address, opening hours, link or price: the platform shows them in "
    "their own places. The customer's text shows them blanked («טלפון», «כתובת» ...); never copy a blanked label.\n"
    "- A price is written only as its reference, right after its own label from prices, e.g. \"ייעוץ ראשון: "
    "@price:1\". Every price in prices is shown at least once, never next to another service, and nothing the "
    "customer priced is called free. A review is never written: testimonials list review references only.\n"
    "- Never name a contact channel the page does not have (WhatsApp only when facts_the_platform_shows has it), a "
    "person, a title, a credential, a city, a day or a rating the customer did not write; never quote anyone.\n"
    "- Every number you write -- in digits or in words (שלושה, עשרים, מאות) -- is one of numbers_you_may_use, as the "
    "customer wrote it, and it counts what that number 'counts' (3 lawyers stay lawyers, a year stays a year). Never "
    "add a year, a count, a percentage, '24/7', a duration or a size ('מאות לקוחות') the customer did not write.\n"
    "- The business name is one of business_names_quoted exactly (or the part of one before its ' – ').\n"
    "- No superlatives or promises no fact supports (מוביל, הטוב ביותר, מס׳ 1, מובטח).\n"
    "- Natural, correct Hebrew: gender and number agreement, no translationese, no filler, no placeholders. Address "
    "visitors in the plural (אתם).\n"
    "- When the customer listed the page's sections, follow what they wrote for each section, in their words where "
    "they gave words (a hero title or a button text in quotes is used as written).\n"
    "- trade_words are this trade's own Hebrew words. Use them to name what the customer wrote, the way the trade "
    "says it; never use one to add a service, a product or a claim the customer did not write.\n"
    "- Respect every bound (characters, items). Leave an optional field out rather than inventing content for it.\n"
    "Return only the JSON object."
)

_CONTENT_CORRECTION = (
    'Your content document has problems a program found (path, code, why). Return the WHOLE corrected document as '
    'one JSON object in the same shape, changing only what the problems require.'
)

_CONTENT_REPAIR_SYSTEM = (
    "You fix specific Hebrew copy strings of a business website for 148AI. You get JSON paths, the current text of "
    "each, and the findings a checker reported. Return ONLY {\"set\": {\"<path>\": \"<new text>\"}} with a new text "
    "for some or all of the given paths -- never another path. The same rules hold: no phone, e-mail, address, hours, "
    "link or price (a price only as its @price:N reference), only numbers the customer wrote, no superlatives, "
    "natural correct Hebrew, the same length bound as the current text allows."
)


def content_shape_guard(data) -> None:
    """A document with no sections object is not a content document: rejected as model output, so the router moves
    on to its next model (the same mechanism as autonomous_agents._code_shape_guard)."""
    from ..model_gateway import ModelJSONRejected
    if not isinstance(data, dict) or not isinstance(data.get('sections'), dict):
        raise ModelJSONRejected('not a content document: no "sections" object', raw='',
                                diagnostic={'reason': 'content_shape', 'keys': sorted(data)[:12] if isinstance(data, dict) else []})


def rewrite_shape_guard(data) -> None:
    from ..model_gateway import ModelJSONRejected
    if not isinstance(data, dict) or not isinstance(data.get('set'), dict):
        raise ModelJSONRejected('not a rewrite: no "set" object', raw='', diagnostic={'reason': 'rewrite_shape'})


def _complete(gateway, *, system: str, user: str, max_tokens: int, guard, usage: list | None = None,
              role: str = 'content') -> dict:
    kwargs = dict(system=system, user=user, max_tokens=max_tokens)
    if getattr(gateway, 'accepts_task_tag', False):
        kwargs['validate'] = guard
    records = getattr(getattr(gateway, 'recorder', None), 'records', None)
    start = len(records) if isinstance(records, list) else None
    try:
        data = gateway.complete_json(**kwargs)
        guard(data)                    # a plain gateway has no router to escalate; the shape is still enforced
        return data
    finally:                           # measured on success and on failure alike (the owner: "רק מדידה")
        if usage is not None:
            usage.append(_measured(gateway, start, role, max_tokens))


class ContentAgent:
    """Writes the content document: one call, and corrective calls within the generator's MAX_CORRECTIONS (counted in
    `calls`)."""

    def __init__(self, gateway):
        self.gateway = gateway
        self.calls = 0
        self.usage: list[dict] = []       # every call, measured (site_route.content_usage)

    def write(self, payload: dict) -> dict:
        self.calls += 1
        return _complete(self.gateway, system=_CONTENT_SYSTEM, user=json.dumps(payload, ensure_ascii=False),
                         max_tokens=output_maximum(self.gateway), guard=content_shape_guard, usage=self.usage,
                         role='content')

    def correct(self, payload: dict, doc: dict, problems) -> dict:
        self.calls += 1
        user = json.dumps({**payload, 'instruction': _CONTENT_CORRECTION, 'your_document': doc,
                           'problems': [p.to_dict() for p in problems]}, ensure_ascii=False)
        return _complete(self.gateway, system=_CONTENT_SYSTEM, user=user, max_tokens=output_maximum(self.gateway),
                         guard=content_shape_guard, usage=self.usage, role='correction')


class ContentRepairAgent:
    """Rewrites only the named paths: one call; a path it was not given is refused (the test-edit guard's discipline)."""

    def __init__(self, gateway):
        self.gateway = gateway
        self.calls = 0
        self.usage: list[dict] = []       # every call, measured (site_route.content_usage)

    def rewrite(self, doc: dict, paths: dict[str, str], findings: list[str], sheet) -> dict[str, str]:
        self.calls += 1
        user = json.dumps({'paths': paths, 'findings': findings[:12],
                           'numbers_you_may_use': [{'value': n['value'],
                                                    'counts': 'a year' if n['kind'] == 'year' else n['noun']}
                                                   for n in sheet.numbers],
                           'prices': [p['id'] for p in sheet.prices]}, ensure_ascii=False)
        data = _complete(self.gateway, system=_CONTENT_REPAIR_SYSTEM, user=user,
                         max_tokens=output_maximum(self.gateway), guard=rewrite_shape_guard, usage=self.usage,
                         role='rewrite')
        outside = sorted(set(data['set']) - set(paths))
        if outside:
            raise SiteContentInvalid(f'the rewrite set paths it was not given: {outside}')
        bad = [p for p, v in data['set'].items() if not isinstance(v, str)]
        if bad:
            raise SiteContentInvalid(f'the rewrite gave non-text values for {bad}')
        return dict(data['set'])


# ---- paths ----------------------------------------------------------------------------------------------------------
_STEP = re.compile(r'\.?([A-Za-z_]+)|\[(\d+)\]')


def _steps(path: str) -> list:
    return [m.group(1) if m.group(1) is not None else int(m.group(2)) for m in _STEP.finditer(path)]


def set_path(doc: dict, path: str, value: str) -> dict:
    """A copy of the document with one copy leaf replaced. The path must already exist."""
    out = json.loads(json.dumps(doc, ensure_ascii=False))
    steps = _steps(path)
    node = out
    for s in steps[:-1]:
        node = node[s]
    if not isinstance(node[steps[-1]], str):
        raise SiteContentInvalid(f'{path} is not a copy string')
    node[steps[-1]] = value
    return out


# ---- an invented fact after the one correction ----------------------------------------------------------------------
# route-honesty (bld_3938e570, 2026-11-25): after the one correction, ONE sentence with a price the customer never gave
# (sections.process.lead PRICE_NOT_GIVEN) failed the whole build. A problem of this family says the copy STATES a fact
# the customer did not give; the sentence that states it can be taken out, and nothing has to be written in its place.
# Every other code -- shape, length, Hebrew, a customer fact in the wrong place (FACT_IN_COPY), a real price next to
# the wrong label (PRICE_CONTEXT), a reference, a placeholder, the name -- still fails the build loudly.
INVENTED = ('PRICE_NOT_GIVEN', 'PRICE_CONTRADICTED', 'INVENTED_NUMBER', 'INVENTED_COUNT', 'CHANNEL_NOT_GIVEN',
            'REVIEW_TEXT_WRITTEN', 'UNVERIFIABLE_CLAIM', 'UNSUPPORTED_DETAIL')
if set(INVENTED) - set(V.CODES):                      # a renamed validator code must not leave a dead entry here
    raise RuntimeError(f'INVENTED names codes the validator does not have: {sorted(set(INVENTED) - set(V.CODES))}')
_SENTENCE = re.compile(r'(?<=[.!?])\s+|\s*\n\s*')


def leaf_spec(path: str, outline_titles: dict):
    """The schema spec of one copy leaf (schema.SECTIONS / schema.TOP), or None for a path the schema does not have."""
    steps = _steps(path)
    if len(steps) == 1:
        return K.TOP.get(steps[0]) if steps[0] in ('tagline', 'description') else None
    if len(steps) < 3 or steps[0] != 'sections' or steps[1] not in K.SECTIONS:
        return None
    spec = K.spec_for(steps[1], outline_titles).get(steps[2])
    for s in steps[3:]:
        if isinstance(s, int) and isinstance(spec, K.Lst):
            spec = spec.item
        elif isinstance(s, str) and isinstance(spec, K.Obj):
            spec = spec.fields.get(s)
        else:
            return None
    return spec


def _drop(doc: dict, path: str) -> dict:
    out = json.loads(json.dumps(doc, ensure_ascii=False))
    steps = _steps(path)
    node = out
    for s in steps[:-1]:
        node = node[s]
    del node[steps[-1]]
    return out


def strip_invented(doc: dict, problems, check, outline_titles: dict) -> tuple[dict | None, list[dict], str | None]:
    """(the document without the sentences that state an invented fact, [what was removed and why], None) -- or
    (None, [], why not). `check(doc)` is the route's validation of a document.

    Only when EVERY blocking problem is of the INVENTED family on a model-written copy leaf: in each such leaf, the
    sentences that carry the problem on their own (validated alone in the leaf's place) are removed and the rest kept,
    in order, joined by a space. A leaf left with no sentence is removed when its field is optional
    (schema: Str(optional=True)); a required one refuses (an empty required field is never written). The result must
    validate with no blocking problem, or nothing is removed. No text is ever written in place of what is removed."""
    blocking = V.blocking(problems)
    other = sorted({p.code for p in blocking if p.code not in INVENTED})
    if other:
        return None, [], f'not an invented fact: {", ".join(other)}'
    copy = dict(V.leaves(doc))
    outside = sorted({p.path for p in blocking if p.path not in copy})
    if outside:
        return None, [], f'not on a copy string: {", ".join(outside)}'
    by_path: dict[str, list] = {}
    for p in blocking:
        by_path.setdefault(p.path, []).append(p)
    out, removed = doc, []
    for path in sorted(by_path):
        codes = {p.code for p in by_path[path]}
        sentences = [s for s in _SENTENCE.split(copy[path]) if s.strip()]
        bad = [i for i, s in enumerate(sentences)
               if any(q.path == path and q.code in codes for q in V.blocking(check(set_path(out, path, s))))]
        if not bad:
            return None, [], f'{path}: no single sentence carries {", ".join(sorted(codes))}'
        kept = [s for i, s in enumerate(sentences) if i not in bad]
        entry = {'path': path, 'codes': sorted(codes), 'why': [p.why for p in by_path[path]][:3],
                 'removed': [sentences[i][:300] for i in bad], 'field_removed': not kept}
        if kept:
            out = set_path(out, path, ' '.join(kept))
        elif getattr(leaf_spec(path, outline_titles), 'optional', False):
            out = _drop(out, path)
        else:
            return None, [], f'{path} is required: removing its only sentence would leave it empty'
        removed.append(entry)
    left = V.blocking(check(out))
    if left:
        return None, [], 'still invalid without those sentences: ' + '; '.join(f'{p.path} {p.code}' for p in left[:6])
    return out, removed, None


def _norm(text: str) -> str:
    return ' '.join(_html.unescape(str(text)).replace(' ', ' ').split())


def shown_leaves(doc: dict, sheet) -> list[tuple[str, str]]:
    """(path, the text as the page shows it) of every copy leaf: references replaced by the customer's spans."""
    out = []
    for path, text in V.leaves(doc):
        try:
            out.append((path, _norm(R._sub(text, sheet))))
        except R.SiteRenderDefect:
            out.append((path, _norm(text)))
    return out


_WHERE = re.compile(r"""'where': ('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""")


def snippets(failure: dict) -> list[str]:
    """The page text a failure points at: each finding's 'where' (skill gates), else the text after the finding's
    label (the truth gate's claims, a placeholder)."""
    message = str(failure.get('message', ''))
    found = []
    for m in _WHERE.finditer(message):
        try:
            found.append(str(ast.literal_eval(m.group(1))))
        except (ValueError, SyntaxError):
            continue
    if not found and ': ' in message:
        tail = message.split(': ', 2)[-1]
        found = [x.strip(" '\"") for x in re.split(r',\s*|;\s*', tail) if len(x.strip()) >= 4]
    return [s for s in (_norm(x) for x in found) if len(s) >= 3]


def attribute(failures: list[dict], doc: dict, sheet) -> tuple[dict[str, list[str]], list[dict]]:
    """({path: [finding messages]}, failures that point at no copy leaf). A finding is located in a model-written
    string only; one that points at a platform-filled slot or a fixed UI string ('דלגו לתוכן', 'שם מלא') is not
    the model's and stays unattributed."""
    leaves = shown_leaves(doc, sheet)
    paths: dict[str, list[str]] = {}
    missed = []
    for f in failures:
        hit = set()
        for s in snippets(f):
            for path, text in leaves:
                if s in text or (len(text) >= 8 and text in s):
                    hit.add(path)
        if not hit:
            missed.append(f)
        for path in sorted(hit):
            paths.setdefault(path, []).append(str(f.get('message', ''))[:400])
    return paths, missed


# ---- the architect ------------------------------------------------------------------------------------------------------
class ContentSpecArchitect:
    """No model call: the content-only floor (ProductArchitect._content_only_spec). Records the build prompt."""

    def __init__(self, core, route):
        self.core, self.route = core, route

    def create_spec(self, prompt, *args, **kwargs):
        from ..product_architect import ProductArchitect
        self.core.site_prompt = prompt
        return ProductArchitect._content_only_spec(prompt, self.route.title)


# ---- the generator ------------------------------------------------------------------------------------------------------
def _gate_failure(gate: str, f: dict) -> dict:
    from ..skill_units import manifest
    return {'acceptance_id': f"gate-{gate}-{f['unit']}",
            'message': f"{f['code']} ({manifest(f['unit'])['name']}) on {f['page']}: " + '; '.join(map(str, f['findings'])),
            'evidence': ''}


def prepass(core, route, html: str, sheet) -> dict:
    """The gates that judge a page, on the rendered page, before any sandbox time: {'block': [...], 'warn': [...]},
    each failure with its owner. A gate's mode decides (skill_units.gate.mode): a warn finding never blocks."""
    from ..g_apple import static as S
    from ..skill_units import gate as G
    from ..skills_runtime import _invented_contact
    out = {'block': [], 'warn': []}
    for gate in PREPASS_GATES:
        mode = G.mode(gate)
        if mode == 'off':
            continue
        result = G.check(gate, {R.PAGE: html})
        for f in result['failures']:
            failure = _gate_failure(gate, f)
            out['block' if mode == 'block' else 'warn'].append({**failure, 'owner': O.owner_of(failure['acceptance_id'])})
    apple_mode = G.mode('APPLE')
    if apple_mode != 'off':
        for f in S.check(html, route.contract):
            out['block' if apple_mode == 'block' else 'warn'].append(
                {'acceptance_id': 'gate-APPLE', 'message': f"{f['code']} at {f.get('where') or 'the page'}: {f['why']}",
                 'evidence': '', 'owner': 'platform'})
    # the truth gate, as the REVIEW stage will run it: on the page as served (the transform's data URIs in, cut at
    # 45,000 characters, preview_smoke) -- and on the whole page, so copy beyond the cut is still checked here
    transform = getattr(core, 'repository_transform', None)
    served = transform({R.PAGE: html})[R.PAGE] if callable(transform) else html
    from ..fact_canon import build_canon, needs_customer_input
    canon = build_canon(route.prompt)
    seen = set()
    # (the served cut is what the review stage reads: up to the last complete section, never a fact cut in half --
    # preview_smoke.served_cut, which the route switches on for its preview stage in site_content.install)
    for label, ctx in (('served cut', {'request': route.prompt, 'canon': canon,
                                       'rendered_pages': {'/': served_cut(served)}}),
                       ('whole page', {'request': route.prompt, 'canon': canon})):
        for f in _invented_contact({R.PAGE: served}, ctx):
            if f.severity != 'blocking':
                continue
            message = f'QA review ({f.skill}): {f.problem}'
            if message in seen:
                continue
            seen.add(message)
            listed = bool(needs_customer_input([message], route.prompt))
            owner = O.review_owner(message, source='static', missing_listed=listed)
            out['block'].append({'acceptance_id': 'REVIEW', 'message': message, 'evidence': f'truth gate on the {label}',
                                 'owner': owner})
    return out


def skipped_report(skipped: list[tuple[str, str]], lib_skipped: list[str], offered: dict, doc: dict) -> list[str]:
    """Every section the page does not show, each with its reason: the sections never offered (schema.offered_sections
    says why), and every section the library left out -- an offered optional section the model did not write, a
    numbers strip whose numbers are all in the hero panel, the library's own notes ('about.facts:...'). A section the
    library left out with no known reason is a platform defect, raised: never an unexplained gap."""
    said = {k for k, _ in skipped}
    given = doc.get('sections') or {}
    out = [f'{k}: {why}' for k, why in skipped]
    for s in lib_skipped:
        if ':' in s:
            out.append(s)
        elif s in said:
            continue
        elif offered.get(s) == 'optional' and s not in given:
            out.append(f'{s}: offered, the model left it out')
        elif s == 'stats' and 'stats' in given:
            out.append('stats: every number is already shown in the hero panel')
        else:
            raise SiteRenderDefect(f'the section library left out {s!r} with no known reason')
    return out


_LIST_NAMES = {'stats.items': 'המספרים', 'services.items': 'השירותים', 'about.paragraphs': 'הפסקאות על העסק',
               'about.facts': 'העובדות על העסק', 'process.steps': 'שלבי העבודה', 'faq.items': 'השאלות הנפוצות',
               'testimonials.items': 'ההמלצות', 'pricelist.groups': 'קבוצות המחירון', 'contact.topics': 'נושאי הפנייה'}


def shortened_said(s: dict) -> str:
    """A list the model shortened to fit one answer, in the customer's words (Hebrew: the route's pages are Hebrew)."""
    return (f'ברשימת {_LIST_NAMES[s["list"]]} נכנסו פחות פריטים ממה שכתבתם ({s["left_out"]} לא נכנסו), כי כל התוכן '
            'לא נכנס בתשובה אחת של המודל. אפשר לבקש שינוי ולהוסיף אותם.')


class ContentSiteGenerator:
    def __init__(self, core, agent: ContentAgent, repair_agent: ContentRepairAgent):
        self.core, self.agent, self.repair_agent = core, agent, repair_agent

    def _payload(self, route, sheet, offered) -> dict:
        from ..section_library import LAYOUTS
        from ..skill_units import gate as G
        # a generator built without its agent (tests/test_domain_registry builds one with __new__) has no routed
        # gateway: output_maximum then reads the runtime or repository catalogue, as for any unrouted gateway
        gateway = getattr(getattr(self, 'agent', None), 'gateway', None)
        # a palette's name is a trade's ('counsel'): the model is given it only for a business the brief names, so the
        # neutral palette of an unnamed business never reads as "a law firm" (bld_3938e570)
        named = getattr(route, 'category', None) is not None
        return {'request': sheet.for_model(), 'palette': route.palette if named else None,
                'direction': route.direction, 'voice': route.voice,
                'trade_words': list(getattr(route, 'domain_words', None) or []),
                'schema': K.schema_for_model(offered, route.outline_titles, name_given=bool(sheet.name),
                                             layouts=LAYOUTS),
                'checks': G.rules_text(('HE', 'G10', 'BRAND')),
                'output_room': {'characters': int(output_maximum(gateway) * CHARS_PER_TOKEN_ESTIMATE),
                                'rule': (
                    'Your whole answer must stay under about this many characters. If it would not: shorten '
                    'descriptions first; if a list must still be shorter, keep the customer\'s own items first, never '
                    'leave out a price, and name each list you shortened in "shortened" with how many items it leaves '
                    'out.')}}

    def generate(self, spec):
        core = self.core
        route = core.site_route
        images = list(getattr(core, 'uploaded_images', None) or ()) + list(getattr(core, 'generated_images', None) or ())
        sheet = Fx.fact_sheet(route.prompt, asset_plan=getattr(core, 'asset_plan', None), images=images)
        if sheet.problems:
            raise SiteRenderDefect(f'the fact sheet cannot be rendered on this route: {sheet.problems}')
        if sheet.canon_hash != route.canon_hash:
            raise SiteRenderDefect(f'canon {sheet.canon_hash} is not the route\'s {route.canon_hash}')
        held = getattr(core, 'design_contract', None)
        if held is not None and held.get('fingerprint') != route.contract_fp:
            raise SiteRenderDefect(f"the G-APPLE gate holds contract {held.get('fingerprint')}, the route rendered "
                                   f"{route.contract_fp}")
        offered, skipped = K.offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)
        payload = self._payload(route, sheet, offered)
        report = core.site_report
        rounds: list[dict] = []                            # every corrective call of this generation, in order
        report.update(correction_bound=MAX_CORRECTIONS, correction_rounds=rounds)
        doc = self.agent.write(payload)
        # Bounded: a pass that neither breaks nor raises spends one correction, and at most MAX_CORRECTIONS are spent,
        # so the loop body runs at most MAX_CORRECTIONS + 1 times; the `else` below is unreachable and raises.
        for _ in range(MAX_CORRECTIONS + 1):
            problems = V.validate(doc, sheet, offered, route.outline_titles)
            block = V.blocking(problems)
            if block and rounds:
                # after a correction, invented facts alone lose their sentences (strip_invented, free and
                # deterministic) before another paid correction is spent on them
                doc, problems = self._without_invented(doc, problems, sheet, offered, route)
                block = V.blocking(problems)
            if block:
                if len(rounds) >= MAX_CORRECTIONS:
                    report['problems'] = [p.to_dict() for p in problems]
                    raise SiteContentInvalid(f'{len(block)} problem(s) after {MAX_CORRECTIONS} corrections: '
                                             + '; '.join(f'{p.path} {p.code}' for p in block[:6]), problems)
                report.setdefault('corrected', [p.to_dict() for p in block])     # what the first correction was asked
                rounds.append({'round': len(rounds) + 1, 'kind': 'validation', 'call': 'content',
                               'asked': [{'path': p.path, 'code': p.code} for p in block]})
                _LOG.info('SITE_CONTENT_CORRECTION round=%s/%s kind=validation problems=%s', len(rounds),
                          MAX_CORRECTIONS, len(block))
                doc = self.agent.correct(payload, doc, block)
                continue
            html, lib_skipped = self._render(doc, sheet, route)
            found = prepass(core, route, html, sheet)
            blocking = found['block']
            if any(f['owner'] != 'content' for f in blocking):
                report['prepass'] = found
                raise SiteRenderDefect('a check failed outside the model\'s copy before the sandbox: '
                                       + '; '.join(f"{f['acceptance_id']}: {f['message'][:160]}"
                                                   for f in blocking if f['owner'] != 'content')[:1500])
            if not blocking:
                break
            paths, missed = attribute(blocking, doc, sheet)
            if missed:
                report['prepass'] = found
                raise SiteRenderDefect('a copy finding points at no model-written text: '
                                       + '; '.join(f['message'][:160] for f in missed)[:1500])
            if len(rounds) >= MAX_CORRECTIONS:
                report['prepass'] = found
                raise SiteContentInvalid(f'a copy finding remains after {MAX_CORRECTIONS} corrections: '
                                         + '; '.join(f['message'][:160] for f in blocking)[:1500])
            rounds.append({'round': len(rounds) + 1, 'kind': 'copy_check', 'call': 'rewrite',
                           'asked': [{'path': p, 'findings': [m[:300] for m in ms]} for p, ms in sorted(paths.items())]})
            _LOG.info('SITE_CONTENT_CORRECTION round=%s/%s kind=copy_check paths=%s', len(rounds), MAX_CORRECTIONS,
                      len(paths))
            current = dict(V.leaves(doc))
            changes = self.repair_agent.rewrite(doc, {p: current[p] for p in paths},
                                                [m for ms in paths.values() for m in ms], sheet)
            report['prepass_rewrite'] = sorted(changes)
            for path, text in changes.items():
                doc = set_path(doc, path, text)
        else:
            raise RuntimeError(f'the content corrections ran past their bound of {MAX_CORRECTIONS}')
        report['shortened'] = list(doc.get('shortened') or [])
        report['shortened_said'] = [shortened_said(s) for s in report['shortened']]
        if report['shortened']:
            _LOG.warning('SITE_CONTENT_SHORTENED %s', report['shortened'])
        report.update(prepass=found, warnings=[p.to_dict() for p in problems if p.severity == 'warn'],
                      skipped=skipped_report(skipped, lib_skipped, offered, doc),
                      content_calls=self.agent.calls + self.repair_agent.calls,
                      content_sha256=Fx.fingerprint(doc), canon_hash=sheet.canon_hash, page_chars=len(html))
        core.site_sheet = sheet
        bound = R.binds(sheet, route.contract, route.year)
        names = [route.outline_titles[k] for k in (route.order or []) if k in route.outline_titles]
        domain = domain_by_slug(route.domain)
        produced = R.legal_files(doc, sheet, route.contract, html, domain=domain, direction=route.direction,
                                 year=route.year, outline_titles=route.outline_titles, order=route.order)
        report['legal'] = LG.summary(domain, produced)             # warehouse 127: the legal page, said in the evidence
        files = R.repository(doc, sheet, html, spec=spec, contract=route.contract, bound=bound, order_names=names,
                             legal=produced)
        return tuple(FilePatch(path, text) for path, text in sorted(files.items()))

    def _without_invented(self, doc, problems, sheet, offered, route):
        """(document, problems) after strip_invented: the sentences removed are in the evidence ('stripped'), and
        when nothing may be removed, why ('not_stripped') -- the document and its problems are then returned as they
        were, and the caller fails the build as before."""
        def check(d):
            return V.validate(d, sheet, offered, route.outline_titles)
        stripped, removed, why = strip_invented(doc, problems, check, route.outline_titles)
        report = self.core.site_report
        if stripped is None:
            report['not_stripped'] = why
            return doc, problems
        report.setdefault('stripped', []).extend(removed)
        _LOG.info('SITE_STRIPPED %s', '; '.join(f"{r['path']} {','.join(r['codes'])}" for r in removed))
        return stripped, check(stripped)

    def _render(self, doc, sheet, route):
        return R.render(doc, sheet, route.contract, expect_fp=route.contract_fp, direction=route.direction,
                        year=route.year, outline_titles=route.outline_titles, legal=route.domain is not None,
                        order=route.order, windows=route.windows)


# ---- after a failed round -------------------------------------------------------------------------------------------------
def _review_source(core, message: str) -> str:
    from ..behavior_acceptance import find_in_chain
    from ..product_review import ProductReviewExecutor
    review = find_in_chain(getattr(core, 'executor', None), ProductReviewExecutor)
    for r in reversed(getattr(review, 'reviews', None) or []):
        for f in r.get('findings', ()):
            if f"QA review ({f['skill']}): {f['problem']}" == message:
                return f.get('source') or 'unknown'
    return 'unknown'


def classify(core, failure: dict) -> str:
    """The owner of one failure on this route (owners.OWNER; REVIEW per finding). Raises owners.Unowned."""
    aid = str(failure.get('acceptance_id', ''))
    owner = O.owner_of(aid)
    if owner != O.BY_FINDING:
        return owner
    from ..fact_canon import needs_customer_input
    message = str(failure.get('message', ''))
    listed = bool(needs_customer_input([message], getattr(core.site_route, 'prompt', '')))
    return O.review_owner(message, source=_review_source(core, message), missing_listed=listed)


def expand(core, failures: list[dict]) -> list[dict]:
    """The round's failures in full: the group's summary line (ALSO_FAILING) is replaced by what it summarises."""
    if not any(f.get('acceptance_id') == 'ALSO_FAILING' for f in failures):
        return list(failures)
    group = getattr(getattr(core, 'executor', None), 'group_failures', None) or ()
    own = [f for f in failures if f.get('acceptance_id') != 'ALSO_FAILING']
    seen = {(f.get('acceptance_id'), f.get('message')) for f in own}
    return own + [dict(g.__dict__) for g in group if (g.acceptance_id, g.message) not in seen]


class ContentSiteRepairer:
    """Repair works on content, not code (the proposal's section 7, with the OWNER table)."""

    def __init__(self, core, agent: ContentRepairAgent):
        self.core, self.agent = core, agent
        self.gateway = agent.gateway         # the design critic reviews through the repairer's gateway (design_review)
        self.trace: list[dict] = []

    def repair(self, *, spec, repo_summary, failures):
        core = self.core
        failures = expand(core, [dict(f) for f in failures])
        by_owner: dict[str, list[dict]] = {k: [] for k in O.OWNERS}
        for f in failures:
            try:
                by_owner[classify(core, f)].append(f)
            except O.Unowned as exc:
                self.trace.append({'declined': 'unowned_finding', 'why': str(exc)[:300]})
                raise RepairDeclined('unowned_finding', str(exc)) from exc
        core.site_feedback.extend({'source': 'repair', 'acceptance_id': f.get('acceptance_id'),
                                   'message': str(f.get('message', ''))[:400]} for f in by_owner['advisory'])
        if by_owner['platform']:
            detail = '; '.join(f"{f.get('acceptance_id')}: {str(f.get('message', ''))[:200]}"
                               for f in by_owner['platform'][:6])
            self.trace.append({'declined': 'platform_render_defect', 'failures': detail[:1500]})
            raise RepairDeclined('platform_render_defect', detail)
        if by_owner['customer']:
            from ..fact_canon import needs_customer_input
            core.needs_input = list(needs_customer_input([f.get('message', '') for f in by_owner['customer']],
                                                         core.site_route.prompt) or ())
            raise RepairDeclined('needs_customer_input', '; '.join(str(f.get('message', ''))[:200]
                                                                   for f in by_owner['customer']))
        if not by_owner['content']:
            raise RepairDeclined('platform_render_defect', 'only advisory findings reached the repairer: the route\'s '
                                                           'advisory filter is not installed')
        # After verified rounds, a refusal never throws the verified work away: every refusal below ends the loop on
        # its best version through RepairDeclined (a model fault -> 'site_content_invalid'; a bind or render fault ->
        # 'platform_render_defect'), with the round's real checks kept. Before the sandbox the generator still raises
        # SiteContentInvalid: nothing has been verified there.
        from ..model_gateway import ModelJSONRejected
        called = self.agent.calls
        try:
            repository = repo_summary.get('_repository') or {}
            stored = json.loads(repository[R.SITE_JSON])
            route, sheet = core.site_route, core.site_sheet
            R.check_binds(stored.get('binds') or {}, R.binds(sheet, route.contract, route.year))
            doc = stored['document']
            paths, missed = attribute(by_owner['content'], doc, sheet)
            if missed:
                detail = '; '.join(str(f.get('message', ''))[:200] for f in missed[:6])
                self.trace.append({'declined': 'platform_render_defect', 'unattributed': detail[:1500]})
                raise RepairDeclined('platform_render_defect', 'a copy finding points at no model-written text: '
                                     + detail)
            current = dict(V.leaves(doc))
            changes = self.agent.rewrite(doc, {p: current[p] for p in paths},
                                         [m for ms in paths.values() for m in ms], sheet)
            for path, text in changes.items():
                doc = set_path(doc, path, text)
            offered, _ = K.offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)
            problems = V.validate(doc, sheet, offered, route.outline_titles)
            if V.blocking(problems):
                raise SiteContentInvalid('the repair rewrite made the document invalid', problems)
            html, _ = R.render(doc, sheet, route.contract, expect_fp=route.contract_fp, direction=route.direction,
                               year=route.year, outline_titles=route.outline_titles, order=route.order,
                               windows=route.windows, legal=route.domain is not None)
            # the legal page depends on what the home page collects (a form, a cookie window), not on its copy: a
            # copy repair leaves it as it is (it has also been through the repository transform), and re-writes it
            # only when what the page collects changed or the page is not there
            produced = R.legal_files(doc, sheet, route.contract, html, domain=domain_by_slug(route.domain),
                                     direction=route.direction, year=route.year, outline_titles=route.outline_titles,
                                     order=route.order)
            try:
                kept = json.loads(repository.get(LG.LEGAL_JSON) or 'null')
            except ValueError:
                kept = None
            if kept is not None and kept.get('collects') == LG.collects(html) and LG.LEGAL_PAGE in repository:
                produced = {}
        except SiteRenderDefect as exc:
            self.trace.append({'declined': 'platform_render_defect', 'why': str(exc)[:1500]})
            raise RepairDeclined('platform_render_defect', str(exc), paid_call=self.agent.calls > called) from exc
        except SiteContentInvalid as exc:
            self.trace.append({'declined': 'site_content_invalid', 'why': str(exc)[:1500], 'problems': exc.problems[:12]})
            raise RepairDeclined('site_content_invalid', str(exc), paid_call=self.agent.calls > called) from exc
        except ModelJSONRejected as exc:                       # a rewrite that is not {"set": {...}} (plain gateway)
            self.trace.append({'declined': 'site_content_invalid', 'why': str(exc)[:1500]})
            raise RepairDeclined('site_content_invalid', str(exc), paid_call=True) from exc
        except (KeyError, ValueError, TypeError) as exc:      # a stored document the platform cannot read back
            self.trace.append({'declined': 'platform_render_defect', 'why': f'{type(exc).__name__}: {exc}'[:1500]})
            raise RepairDeclined('platform_render_defect', f'content/site.json cannot be read back: '
                                 f'{type(exc).__name__}: {exc}', paid_call=self.agent.calls > called) from exc
        self.trace.append({'rewrote': sorted(changes)})
        core.site_report['repairs'] = core.site_report.get('repairs', 0) + 1
        core.site_report['content_calls'] = core.site_report.get('content_calls', 0) + 1
        return (FilePatch(R.SITE_JSON, R.site_json(doc, stored['binds'])), FilePatch(R.PAGE, html),
                *(FilePatch(path, text) for path, text in sorted(produced.items())))


# ---- route-level executors --------------------------------------------------------------------------------------------------
class ThresholdRecorder:
    """Keeps the verification group's threshold report (the sandbox build and the fixed tests): when the advisory filter
    turns a round whose only failures were advisory into a pass, the pass carries the threshold's own test count --
    the group's failure report has none (release_policy would read the tests as UNKNOWN)."""

    def __init__(self, inner):
        self._inner = inner
        self.last = None

    def __getattr__(self, item):
        if item in ('_inner', 'last'):
            raise AttributeError(item)
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        self.last = self._inner.execute(repository=repository, spec=spec)
        return self.last


class AdvisoryFilterExecutor:
    """Takes advisory failures (the OWNER table) out of a round and records them as library feedback. Installed
    INSIDE the quality gate, around the verification group (site_content.install): a round it turns into a pass still
    meets the in-loop quality assessment, and carries the threshold's test count. Every round it also reconciles the
    QA review's record with the route's ownership: the model reviewer's blocking findings are counted as 'advisory',
    not 'blocking', so the release policy does not fail a build on what the route records as library feedback."""

    def __init__(self, inner, core, recorder: ThresholdRecorder | None = None):
        self._inner, self._core, self._recorder = inner, core, recorder

    def __getattr__(self, item):
        if item in ('_inner', '_core', '_recorder'):
            raise AttributeError(item)
        return getattr(self._inner, item)

    def _reconcile_review(self, *, record: bool) -> None:
        from ..behavior_acceptance import find_in_chain
        from ..product_review import ProductReviewExecutor
        review = find_in_chain(self._inner, ProductReviewExecutor)
        last = (getattr(review, 'reviews', None) or [None])[-1]
        if not isinstance(last, dict) or last.get('route_reconciled'):
            return
        moved = []
        for f in last.get('findings') or ():
            if f.get('severity') != 'blocking' or f.get('source') != 'reviewer':
                continue
            message = f"QA review ({f.get('skill')}): {f.get('problem')}"
            if O.review_owner(message, source='reviewer', missing_listed=False) == 'advisory':
                f['route_owner'] = 'advisory'
                moved.append(message)
        last['route_reconciled'] = True
        if moved:
            last['blocking'] = max(0, int(last.get('blocking') or 0) - len(moved))
            last['advisory'] = len(moved)
            if record:
                self._core.site_feedback.extend({'source': 'review', 'acceptance_id': 'REVIEW', 'message': m[:400]}
                                                for m in moved)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        self._reconcile_review(record=report.passed)
        if report.passed:
            return report
        failures = expand(self._core, [dict(f.__dict__) for f in report.failures])
        keep, advisory = [], []
        for f in failures:
            try:
                owner = classify(self._core, f)
            except O.Unowned:
                owner = 'unowned'                       # kept: the repairer stops on it loudly
            (advisory if owner == 'advisory' else keep).append(f)
        if not advisory:
            return report
        self._core.site_feedback.extend({'source': 'round', 'acceptance_id': f.get('acceptance_id'),
                                         'message': str(f.get('message', ''))[:400]} for f in advisory)
        _LOG.info('SITE_ADVISORY recorded=%d kept=%d', len(advisory), len(keep))
        if not keep:
            base = getattr(self._recorder, 'last', None)
            tests = base.tests_executed if base is not None and base.passed else report.tests_executed
            return ExecutionReport(True, (), report.build_log, tests_executed=tests)
        return replace(report, failures=tuple(AcceptanceFailure(f['acceptance_id'], f.get('message', ''),
                                                                f.get('evidence', '') or '') for f in keep))


class SiteParityExecutor:
    """The served page is the rendered page (as far as the preview reads it) and the only page of the repository."""

    GATE = 'SITE_PARITY'

    def __init__(self, inner, core, mode: str):
        self._inner, self._core, self.mode = inner, core, mode
        self.last_parity = None

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        from ..behavior_acceptance import find_in_chain
        from ..preview_smoke import PreviewReadyExecutor
        preview = find_in_chain(self._inner, PreviewReadyExecutor)
        pages = getattr(preview, 'last_pages', None) if preview is not None else None
        findings = []
        others = sorted(p for p in repository if p.lower().endswith(('.html', '.htm')) and p not in (R.PAGE, LG.LEGAL_PAGE))
        if others:
            findings.append(f'other HTML documents in the repository: {others}')
        legal = LG.findings(repository, domain_by_slug(getattr(getattr(self._core, 'site_route', None), 'domain', None)))
        if not isinstance(pages, dict) or not isinstance(pages.get('/'), str):
            self.last_parity = {'status': 'NOT_RUN', 'mode': self.mode, 'reason': 'no served page from the preview',
                                'findings': findings}
        else:
            # both sides as the preview returns them: a long page up to its last complete section (served_cut)
            page = str(repository.get(R.PAGE, ''))
            if served_cut(pages['/'], full_length=len(page)) != served_cut(page):
                findings.append('the served GET / is not the rendered public/index.html')
            self.last_parity = {'status': 'fail' if findings else 'pass', 'mode': self.mode, 'findings': findings}
        self._core.site_report['parity'] = self.last_parity
        if legal:                                   # the legal page is not a mode: a business with a domain has one
            self._core.site_report['legal_findings'] = legal
            return ExecutionReport(False, tuple(AcceptanceFailure('gate-SITE_LEGAL', f) for f in legal), report.build_log)
        if findings and self.mode == 'block':
            return ExecutionReport(False, tuple(AcceptanceFailure('gate-SITE_PARITY', f) for f in findings),
                                   report.build_log)
        whole = self._whole_page_review(repository)
        if whole:
            return replace(report, passed=False, failures=tuple(report.failures) + whole)
        return report

    def _whole_page_review(self, repository) -> tuple:
        """Review S7 (2026-11-26): the review stage reads a long page up to its last complete section (served_cut),
        and a repair round may rewrite copy past it. Every round, a page longer than the preview's capture is read
        whole by the same truth gate the pre-pass runs, and a blocking finding fails the round as the review's own
        would -- so the copy checked is never less than on main, where the raw 45,000 characters were read."""
        from ..preview_smoke import SERVED_CUT
        route = getattr(self._core, 'site_route', None)
        page = str(repository.get(R.PAGE, ''))
        if route is None or len(page) < SERVED_CUT:
            return ()
        from ..fact_canon import build_canon
        from ..skills_runtime import _invented_contact
        out = tuple(AcceptanceFailure('REVIEW', f'QA review ({f.skill}): {f.problem}', 'truth gate on the whole page')
                    for f in _invented_contact({R.PAGE: page}, {'request': route.prompt, 'canon': build_canon(route.prompt)})
                    if f.severity == 'blocking')
        self._core.site_report['whole_page_review'] = {'chars': len(page), 'blocking': [f.message for f in out]}
        return out

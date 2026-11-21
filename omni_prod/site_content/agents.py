"""The content route's three engine parts and its two model agents.

  ContentSpecArchitect   no model call: the content-only floor spec (ProductArchitect._content_only_spec); the worker's
                         wrappers add CUSTOMER-FACTS, the outline, PLATFORM-CHECKS and DESIGN-CONTRACT as today
  ContentSiteGenerator   one ContentAgent call (copy only, one JSON document), validated; ONE corrective call for a
                         blocking validation problem or a blocking gate finding inside the copy; then the platform
                         renders, runs the gates that judge a page before any sandbox time (each in its own mode:
                         a warn finding goes to the evidence), and writes the repository
  ContentSiteRepairer    after a failed round: attribute every failure with the OWNER table. Platform -> RepairDeclined
                         ('platform_render_defect'), zero model calls. Customer -> needs_customer_input. Content -> one
                         ContentRepairAgent call that may set ONLY the JSON paths the findings point at; validated,
                         re-rendered; the patch holds content/site.json and public/index.html only
  AdvisoryFilterExecutor the design critic's must_fix and the model reviewer's findings are recorded as library feedback
                         (core.site_feedback) and taken out of the round's failures: never a decline, never a repair
  SiteParityExecutor     the served GET / is the rendered page (cut where the preview cuts it), and the repository
                         holds no other page; a new check, so it enters gate.CALIBRATING (SITE_PARITY) at warn

Every loop is bounded (one corrective call per generation, one rewrite call per repair round, the engine's own round
bounds), every failure is loud (SiteContentInvalid, SiteRenderDefect, RepairDeclined), and there is no fallback to
the legacy generator once the route was chosen.
"""
from __future__ import annotations

import ast
import html as _html
import json
import logging
import re
from dataclasses import replace

from ..autonomous_core import AcceptanceFailure, ExecutionReport, RepairDeclined
from ..repository_patch import FilePatch
from . import facts as Fx
from . import owners as O
from . import render as R
from . import schema as K
from . import validate as V

_LOG = logging.getLogger(__name__)
PREVIEW_CUT = 45_000                  # preview_smoke keeps the first 45,000 characters of GET / for the truth gate
PREPASS_GATES = ('G1', 'G3', 'G10', 'G11', 'HE', 'BRAND', 'SHARE', 'PRO')
MAX_CONTENT_TOKENS = 8000
MAX_REWRITE_TOKENS = 3000


class SiteContentInvalid(RuntimeError):
    """The model's content document is still invalid after its one correction. failure_code 'site_content_invalid'."""

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
    "- A price is written only as its reference, e.g. \"ייעוץ ראשון: @price:1\". A review is never written: "
    "testimonials list review references only.\n"
    "- Every number you write is one of numbers_you_may_use, as the customer wrote it. Never add a year, a count, a "
    "percentage, '24/7' or a duration the customer did not write.\n"
    "- The business name is written exactly as the customer wrote it (a part of the customer's text).\n"
    "- No superlatives or promises no fact supports (מוביל, הטוב ביותר, מס׳ 1, מובטח).\n"
    "- Natural, correct Hebrew: gender and number agreement, no translationese, no filler, no placeholders. Address "
    "visitors in the plural (אתם).\n"
    "- When the customer listed the page's sections, follow what they wrote for each section, in their words where "
    "they gave words (a hero title or a button text in quotes is used as written).\n"
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


def _complete(gateway, *, system: str, user: str, max_tokens: int, guard) -> dict:
    kwargs = dict(system=system, user=user, max_tokens=max_tokens)
    if getattr(gateway, 'accepts_task_tag', False):
        kwargs['validate'] = guard
    data = gateway.complete_json(**kwargs)
    guard(data)                        # a plain gateway has no router to escalate; the shape is still enforced
    return data


class ContentAgent:
    """Writes the content document: one call, and at most one corrective call (counted in `calls`)."""

    def __init__(self, gateway):
        self.gateway = gateway
        self.calls = 0

    def write(self, payload: dict) -> dict:
        self.calls += 1
        return _complete(self.gateway, system=_CONTENT_SYSTEM, user=json.dumps(payload, ensure_ascii=False),
                         max_tokens=MAX_CONTENT_TOKENS, guard=content_shape_guard)

    def correct(self, payload: dict, doc: dict, problems) -> dict:
        self.calls += 1
        user = json.dumps({**payload, 'instruction': _CONTENT_CORRECTION, 'your_document': doc,
                           'problems': [p.to_dict() for p in problems]}, ensure_ascii=False)
        return _complete(self.gateway, system=_CONTENT_SYSTEM, user=user, max_tokens=MAX_CONTENT_TOKENS,
                         guard=content_shape_guard)


class ContentRepairAgent:
    """Rewrites only the named paths: one call; a path it was not given is refused (the test-edit guard's discipline)."""

    def __init__(self, gateway):
        self.gateway = gateway
        self.calls = 0

    def rewrite(self, doc: dict, paths: dict[str, str], findings: list[str], sheet) -> dict[str, str]:
        self.calls += 1
        user = json.dumps({'paths': paths, 'findings': findings[:12],
                           'numbers_you_may_use': [n['value'] for n in sheet.numbers],
                           'prices': [p['id'] for p in sheet.prices]}, ensure_ascii=False)
        data = _complete(self.gateway, system=_CONTENT_REPAIR_SYSTEM, user=user, max_tokens=MAX_REWRITE_TOKENS,
                         guard=rewrite_shape_guard)
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
    for label, ctx in (('served cut', {'request': route.prompt, 'canon': canon,
                                       'rendered_pages': {'/': served[:PREVIEW_CUT]}}),
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


class ContentSiteGenerator:
    def __init__(self, core, agent: ContentAgent, repair_agent: ContentRepairAgent):
        self.core, self.agent, self.repair_agent = core, agent, repair_agent

    def _payload(self, route, sheet, offered) -> dict:
        from ..section_library import LAYOUTS
        from ..skill_units import gate as G
        return {'request': sheet.for_model(), 'palette': route.palette, 'direction': route.direction,
                'voice': route.voice,
                'schema': K.schema_for_model(offered, route.outline_titles, name_given=bool(sheet.name),
                                             layouts=LAYOUTS),
                'checks': G.rules_text(('HE', 'G10', 'BRAND'))}

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
        doc = self.agent.write(payload)
        problems = V.validate(doc, sheet, offered, route.outline_titles)
        corrections = 1                                    # the one corrective call of this generation
        if V.blocking(problems):
            corrections -= 1
            report['corrected'] = [p.to_dict() for p in V.blocking(problems)]
            doc = self.agent.correct(payload, doc, V.blocking(problems))
            problems = V.validate(doc, sheet, offered, route.outline_titles)
            if V.blocking(problems):
                report['problems'] = [p.to_dict() for p in problems]
                raise SiteContentInvalid(f'{len(V.blocking(problems))} problem(s) after the one correction: '
                                         + '; '.join(f'{p.path} {p.code}' for p in V.blocking(problems)[:6]), problems)
        html, lib_skipped = self._render(doc, sheet, route)
        found = prepass(core, route, html, sheet)
        blocking = found['block']
        if any(f['owner'] != 'content' for f in blocking):
            report['prepass'] = found
            raise SiteRenderDefect('a check failed outside the model\'s copy before the sandbox: '
                                   + '; '.join(f"{f['acceptance_id']}: {f['message'][:160]}"
                                               for f in blocking if f['owner'] != 'content')[:1500])
        if blocking:
            paths, missed = attribute(blocking, doc, sheet)
            if missed:
                report['prepass'] = found
                raise SiteRenderDefect('a copy finding points at no model-written text: '
                                       + '; '.join(f['message'][:160] for f in missed)[:1500])
            if corrections < 1:
                report['prepass'] = found
                raise SiteContentInvalid('a copy finding remains after the one correction: '
                                         + '; '.join(f['message'][:160] for f in blocking)[:1500])
            corrections -= 1
            current = dict(V.leaves(doc))
            changes = self.repair_agent.rewrite(doc, {p: current[p] for p in paths},
                                                [m for ms in paths.values() for m in ms], sheet)
            report['prepass_rewrite'] = sorted(changes)
            for path, text in changes.items():
                doc = set_path(doc, path, text)
            problems = V.validate(doc, sheet, offered, route.outline_titles)
            if V.blocking(problems):
                raise SiteContentInvalid('the rewrite made the document invalid', problems)
            html, lib_skipped = self._render(doc, sheet, route)
            found = prepass(core, route, html, sheet)
            if found['block']:
                report['prepass'] = found
                raise SiteContentInvalid('the copy still fails a blocking check after the one correction: '
                                         + '; '.join(f['message'][:160] for f in found['block'])[:1500])
        report.update(prepass=found, warnings=[p.to_dict() for p in problems if p.severity == 'warn'],
                      skipped=[f'{k}: {why}' for k, why in skipped] + [s for s in lib_skipped if ':' in s],
                      content_calls=self.agent.calls + self.repair_agent.calls,
                      content_sha256=Fx.fingerprint(doc), canon_hash=sheet.canon_hash, page_chars=len(html))
        core.site_sheet = sheet
        bound = R.binds(sheet, route.contract, route.year)
        names = [route.outline_titles[k] for k in (route.order or []) if k in route.outline_titles]
        files = R.repository(doc, sheet, html, spec=spec, contract=route.contract, bound=bound, order_names=names)
        return tuple(FilePatch(path, text) for path, text in sorted(files.items()))

    def _render(self, doc, sheet, route):
        return R.render(doc, sheet, route.contract, expect_fp=route.contract_fp, direction=route.direction,
                        year=route.year, outline_titles=route.outline_titles, order=route.order)


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
        repository = repo_summary.get('_repository') or {}
        stored = json.loads(repository[R.SITE_JSON])
        route, sheet = core.site_route, core.site_sheet
        R.check_binds(stored.get('binds') or {}, R.binds(sheet, route.contract, route.year))
        doc = stored['document']
        paths, missed = attribute(by_owner['content'], doc, sheet)
        if missed:
            detail = '; '.join(str(f.get('message', ''))[:200] for f in missed[:6])
            self.trace.append({'declined': 'platform_render_defect', 'unattributed': detail[:1500]})
            raise RepairDeclined('platform_render_defect', 'a copy finding points at no model-written text: ' + detail)
        current = dict(V.leaves(doc))
        changes = self.agent.rewrite(doc, {p: current[p] for p in paths}, [m for ms in paths.values() for m in ms],
                                     sheet)
        for path, text in changes.items():
            doc = set_path(doc, path, text)
        offered, _ = K.offered_sections(sheet, route.palette_entry, route.order, route.outline_titles)
        problems = V.validate(doc, sheet, offered, route.outline_titles)
        if V.blocking(problems):
            raise SiteContentInvalid('the repair rewrite made the document invalid', problems)
        html, _ = R.render(doc, sheet, route.contract, expect_fp=route.contract_fp, direction=route.direction,
                           year=route.year, outline_titles=route.outline_titles, order=route.order)
        self.trace.append({'rewrote': sorted(changes)})
        core.site_report['repairs'] = core.site_report.get('repairs', 0) + 1
        core.site_report['content_calls'] = core.site_report.get('content_calls', 0) + 1
        return (FilePatch(R.SITE_JSON, R.site_json(doc, stored['binds'])), FilePatch(R.PAGE, html))


# ---- route-level executors --------------------------------------------------------------------------------------------------
class AdvisoryFilterExecutor:
    """Takes advisory failures (the OWNER table) out of a round and records them as library feedback."""

    def __init__(self, inner, core):
        self._inner, self._core = inner, core

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
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
            return ExecutionReport(True, (), report.build_log, tests_executed=report.tests_executed)
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
        others = sorted(p for p in repository if p.lower().endswith(('.html', '.htm')) and p != R.PAGE)
        if others:
            findings.append(f'other HTML documents in the repository: {others}')
        if not isinstance(pages, dict) or not isinstance(pages.get('/'), str):
            self.last_parity = {'status': 'NOT_RUN', 'mode': self.mode, 'reason': 'no served page from the preview',
                                'findings': findings}
        else:
            if pages['/'] != str(repository.get(R.PAGE, ''))[:PREVIEW_CUT]:
                findings.append('the served GET / is not the rendered public/index.html')
            self.last_parity = {'status': 'fail' if findings else 'pass', 'mode': self.mode, 'findings': findings}
        self._core.site_report['parity'] = self.last_parity
        if findings and self.mode == 'block':
            return ExecutionReport(False, tuple(AcceptanceFailure('gate-SITE_PARITY', f) for f in findings),
                                   report.build_log)
        return report

"""Versioned structured requirements contract (Wave A §5.2).

`intake-requirements/1` is a projection of the approved-to-be ProjectBrief
(the brief stays the single source of truth and its fingerprint binds the
approval). It is what the Chief Architect consumes. Every field is validated;
malformed or unstructured model output never becomes a requirement: model
proposals enter the brief only through `intake.agent` and this projection.

Each requirement carries its source:
  explicit   the customer said it (message) or answered it (answer)
  inferred   148AI chose a documented default (delegated / default)
and a confidence: stated | confirmed | recommended | inferred.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

from .. import discovery as d
from .families import FAMILIES, classify_family

SCHEMA = 'intake-requirements/1'
CONFIDENCE = ('stated', 'confirmed', 'recommended', 'inferred')
PLATFORMS = ('web', 'mobile_web', 'ios', 'android', 'desktop')
LANGS = ('he', 'en')


class ContractInvalid(ValueError):
    def __init__(self, problems):
        super().__init__('; '.join(problems))
        self.problems = list(problems)


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    kind: str          # functional | nonfunctional | data | security | design
    source: str        # explicit | inferred
    confidence: str

    def to_dict(self):
        return dict(self.__dict__)


@dataclass
class RequirementsContract:
    project_goal: str
    product_family: str
    target_users: str
    functional_requirements: list[Requirement]
    nonfunctional_requirements: list[Requirement]
    supported_platforms: list[str]
    languages: list[str]
    design_preferences: dict
    integrations: list[dict]
    authentication_requirements: dict
    data_requirements: dict
    compliance_requirements: list[str]
    acceptance_criteria: list[dict]
    explicit_constraints: list[str]
    inferred_defaults: list[str]
    unresolved_questions: list[str]
    confidence_by_requirement: dict
    customer_approved_decisions: list[str]
    expected_deliverables: list[str]
    cost_constraints: dict
    complexity: str
    brief_fingerprint: str
    schema: str = SCHEMA

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            out[k] = [x.to_dict() if isinstance(x, Requirement) else x for x in v] if isinstance(v, list) else v
        return out

    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate(c: RequirementsContract) -> list[str]:
    p = []
    if c.schema != SCHEMA:
        p.append('unknown schema')
    if not c.project_goal.strip() or len(c.project_goal) > 2000:
        p.append('project_goal must be 1..2000 characters')
    if c.product_family not in FAMILIES:
        p.append(f'unknown product_family {c.product_family}')
    for r in c.functional_requirements + c.nonfunctional_requirements:
        if not re.fullmatch(r'[A-Z]{1,3}\d{1,3}', r.id):
            p.append(f'bad requirement id {r.id}')
        if r.source not in ('explicit', 'inferred') or r.confidence not in CONFIDENCE:
            p.append(f'{r.id}: bad source/confidence')
        if not r.text.strip() or len(r.text) > 2000:
            p.append(f'{r.id}: text must be 1..2000 characters')
    ids = [r.id for r in c.functional_requirements + c.nonfunctional_requirements]
    if len(ids) != len(set(ids)):
        p.append('duplicate requirement ids')
    if not c.functional_requirements:
        p.append('at least one functional requirement')
    if not set(c.supported_platforms) <= set(PLATFORMS) or not c.supported_platforms:
        p.append('supported_platforms invalid')
    if not set(c.languages) <= set(LANGS) or not c.languages:
        p.append('languages invalid')
    if c.authentication_requirements.get('mode') not in ('none', 'simple', 'roles'):
        p.append('authentication mode invalid')
    for a in c.acceptance_criteria:
        if not re.fullmatch(r'AC\d{1,3}', a.get('id', '')) or not a.get('given_when_then'):
            p.append(f'bad acceptance criterion {a}')
        if a.get('covers') and a['covers'] not in ids:
            p.append(f'{a.get("id")}: covers unknown requirement {a["covers"]}')
    if set(c.confidence_by_requirement) != set(ids):
        p.append('confidence_by_requirement must cover exactly the requirement ids')
    if c.complexity not in ('simple', 'standard', 'complex'):
        p.append('complexity invalid')
    if not re.fullmatch(r'[0-9a-f]{64}', c.brief_fingerprint):
        p.append('brief_fingerprint invalid')
    if c.cost_constraints.get('max_usd') is not None:
        try:
            if float(c.cost_constraints['max_usd']) < 0:
                p.append('cost max negative')
        except (TypeError, ValueError):
            p.append('cost max not a number')
    return p


_INTEGRATION_WORDS = (
    ('payments', r'(תשלו[םמ]|סליקה|כרטיס אשראי|stripe|paypal|payment|checkout)'),
    ('email', r'(שליחת מייל|שליחת אימייל|newsletter|send email|email notification)'),
    ('sms', r'(sms|הודעת טקסט|וואטסאפ|whatsapp)'),
    ('maps', r'(מפה|google maps|mapbox|\bmap\b)'),
    ('calendar', r'(google calendar|יומן גוגל|outlook calendar)'),
    ('ai_model', r'(צ\'?אטבוט|chatbot|בינה מלאכותית|\bai\b|gpt|llm)'),
)


def from_brief(brief: d.Brief, *, cost_max_usd=None) -> RequirementsContract:
    v = brief.values()
    src = {k: f.get('source') for k, f in brief.fields.items()}
    conf = {k: f.get('confidence', 'inferred') for k, f in brief.fields.items()}

    def origin(field_):
        return 'explicit' if src.get(field_) in ('message', 'answer') else 'inferred'

    def confidence(field_):
        c = conf.get(field_, 'inferred')
        return c if c in CONFIDENCE else 'inferred'

    text_all = brief.prompt + ' ' + ' '.join(str(x) for x in v.values())
    family = classify_family(brief.prompt)
    fr: list[Requirement] = [Requirement('F1', (v.get('goal') or brief.prompt)[:2000], 'functional',
                                         origin('goal') if v.get('goal') else 'explicit',
                                         confidence('goal') if v.get('goal') else 'stated')]
    if v.get('screens'):
        fr.append(Requirement('F2', 'Screens: ' + v['screens'][:1980], 'functional', origin('screens'), confidence('screens')))
    if v.get('content') and not str(v['content']).startswith('ללא'):
        fr.append(Requirement('F3', 'Initial content: ' + v['content'][:1960], 'functional', origin('content'), confidence('content')))
    nfr: list[Requirement] = []
    lang = v.get('languages', 'he')
    nfr.append(Requirement('N1', {'he': 'Hebrew, right-to-left', 'he_en': 'Hebrew (RTL) with English',
                                  'en': 'English'}.get(lang, lang), 'nonfunctional',
                           origin('languages') if 'languages' in v else 'inferred',
                           confidence('languages') if 'languages' in v else 'inferred'))
    nfr.append(Requirement('N2', 'Responsive on desktop and mobile; layout rules enforced by visual QA', 'nonfunctional',
                           'inferred', 'inferred'))
    if v.get('dates') and v['dates'] != 'none':
        nfr.append(Requirement('N3', f'Date range rule: {v["dates"]}', 'data', origin('dates'), confidence('dates')))
    if v.get('duplicates') == 'block':
        nfr.append(Requirement('N4', 'Duplicates are blocked on the server with an explanation', 'data',
                               origin('duplicates'), confidence('duplicates')))
    login = 'simple' if v.get('access_scope') == 'add_login' else v.get('login', 'none')
    personal = v.get('personal_data') == 'yes' and v.get('access_scope') != 'no_personal'
    if personal:
        nfr.append(Requirement('S1', 'Personal details are visible only to authorized people', 'security',
                               origin('personal_data'), confidence('personal_data')))
    integrations = [{'kind': k, 'detected_from': 'request text', 'status': 'requires capability check'}
                    for k, pat in _INTEGRATION_WORDS if re.search(pat, text_all, re.I)]
    reqs = fr + nfr
    ac = [{'id': 'AC1', 'covers': 'F1',
           'given_when_then': f'Given the product is open, when the user performs the main action, then it succeeds and persists'}]
    n = 2
    for r in reqs[1:]:
        ac.append({'id': f'AC{n}', 'covers': r.id, 'given_when_then': f'Verified: {r.text[:200]}'})
        n += 1
    explicit = [f'{k}={val}' for k, val in v.items() if src.get(k) in ('message', 'answer')]
    inferred = [f'{k}={val}' for k, val in v.items() if src.get(k) in ('delegated', 'default')]
    unresolved = [q.id for q in d.pending(brief)] + d.contradictions(brief)
    weight = len(fr) + len(integrations) * 2 + (2 if login == 'roles' else 1 if login == 'simple' else 0) + (1 if personal else 0)
    complexity = 'simple' if weight <= 3 and family == 'web_app' else ('complex' if weight >= 7 or family not in ('web_app', 'website') else 'standard')
    return RequirementsContract(
        project_goal=(v.get('goal') or brief.prompt)[:2000], product_family=family,
        target_users=v.get('audience', 'unspecified'),
        functional_requirements=fr, nonfunctional_requirements=nfr,
        supported_platforms=['web', 'mobile_web'],
        languages=['he', 'en'] if lang == 'he_en' else [lang if lang in LANGS else 'he'],
        design_preferences={k: v[k] for k in ('style', 'color', 'font', 'logo', 'references') if k in v},
        integrations=integrations,
        authentication_requirements={'mode': login if login in ('none', 'simple', 'roles') else 'none',
                                     'source': origin('login')},
        data_requirements={'personal_data': personal, 'dates': v.get('dates'), 'duplicates': v.get('duplicates'),
                           'retention': 'preview data is temporary'},
        compliance_requirements=(['privacy: restrict access to personal details'] if personal else []),
        acceptance_criteria=ac, explicit_constraints=explicit, inferred_defaults=inferred,
        unresolved_questions=unresolved,
        confidence_by_requirement={r.id: r.confidence for r in reqs},
        customer_approved_decisions=[f'{k}={val}' for k, val in v.items() if src.get(k) == 'answer'],
        expected_deliverables=['working web application', 'automated tests', 'private preview', 'downloadable source (ZIP)'],
        cost_constraints={'max_usd': None if cost_max_usd is None else str(cost_max_usd), 'currency': 'USD'},
        complexity=complexity, brief_fingerprint=brief.fingerprint(),
    )


def build(brief: d.Brief, **kw) -> RequirementsContract:
    c = from_brief(brief, **kw)
    problems = validate(c)
    if problems:
        raise ContractInvalid(problems)
    return c

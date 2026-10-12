"""Capability Feasibility Gate (Unified Conversation OS §5).

Deterministic: given the structured requirements, walk the dependency closure
(product family -> engine, required agents/skills, model routes, verification
mechanisms, integrations, credentials, prices, deployment target) and decide:

  FEASIBLE                    everything required is implemented and verified on the real server
  FEASIBLE_WITH_CONSTRAINTS   buildable; named limitations apply (shown to the customer)
  BLOCKED                     something required exists but is not connected/authorized now
  UNSUPPORTED                 no execution path exists for a requirement
  UNKNOWN                     registries unreadable: never treated as feasible

Registered-but-not-implemented agents/skills count as missing. A build may be
approved only for FEASIBLE / FEASIBLE_WITH_CONSTRAINTS.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..intake.families import EXECUTABLE
from . import registry_view as R

FEASIBLE, WITH_CONSTRAINTS, BLOCKED, UNSUPPORTED, UNKNOWN = (
    'FEASIBLE', 'FEASIBLE_WITH_CONSTRAINTS', 'BLOCKED', 'UNSUPPORTED', 'UNKNOWN')
BUILDABLE = (FEASIBLE, WITH_CONSTRAINTS)

# The verification mechanisms every web build relies on (truth-matrix capability names).
CORE_CHECKS = ('code generation', 'sandbox verification', 'preview smoke', 'behavioural acceptance', 'browser check',
               'visual QA', 'release policy')
INTEGRATION_AGENT = {'payments': 'integration_agent', 'email': 'integration_agent', 'sms': 'integration_agent',
                     'maps': 'integration_agent', 'calendar': 'integration_agent', 'ai_model': 'integration_agent'}


@dataclass
class Finding:
    item: str
    outcome: str
    reason: str
    alternative: str = ''

    def to_dict(self):
        return dict(self.__dict__)


@dataclass
class Feasibility:
    outcome: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def buildable(self) -> bool:
        return self.outcome in BUILDABLE

    def to_dict(self):
        return {'outcome': self.outcome, 'buildable': self.buildable, 'findings': [f.to_dict() for f in self.findings]}


_RANK = {FEASIBLE: 0, WITH_CONSTRAINTS: 1, UNKNOWN: 2, BLOCKED: 3, UNSUPPORTED: 4}


def assess(contract) -> Feasibility:
    snap = R.snapshot()
    if not snap['loaded']:
        return Feasibility(UNKNOWN, [Finding('registries', UNKNOWN, 'generated registries are not readable here')])
    f: list[Finding] = []
    for question in contract.unresolved_questions:
        f.append(Finding('unresolved requirement', BLOCKED, question))
    fam = contract.product_family
    if fam not in EXECUTABLE:
        f.append(Finding(f'product family {fam}', UNSUPPORTED,
                         'no verified execution engine for this product family yet (only web apps and websites)',
                         'a web version of the product (runs in the browser on desktop and mobile)'))
    for check in CORE_CHECKS:
        st = R.capability_status(check)
        if st not in R.VERIFIED:
            f.append(Finding(check, WITH_CONSTRAINTS if st in R.EXECUTABLE else BLOCKED,
                             f'verification step status {st}'))
    if not R.models_for('codegen'):
        f.append(Finding('code-writing model', BLOCKED, 'no available model meets the code-writing quality floor'))
    if not R.models_for('conversation'):
        f.append(Finding('conversation model', WITH_CONSTRAINTS, 'conversation runs on the deterministic interpreter'))
    auth = contract.authentication_requirements.get('mode', 'none')
    if auth in ('simple', 'roles'):
        st = R.agent_status('identity_auth_agent')
        if st not in R.EXECUTABLE:
            f.append(Finding(f'sign-in ({auth})', BLOCKED,
                             f'generated-app sign-in is {st} (managed identity infrastructure not provisioned)',
                             'an internal tool without sign-in shared by private link, or wait for sign-in support'))
    for integ in contract.integrations:
        agent = INTEGRATION_AGENT.get(integ['kind'], 'integration_agent')
        st = R.agent_status(agent)
        if st not in R.EXECUTABLE:
            f.append(Finding(f'integration: {integ["kind"]}', BLOCKED, f'{agent} is {st}',
                             f'build without {integ["kind"]} now and add it when the integration is connected'))
    gap = snap['gaps'].get('review.independent_provider')
    if gap and gap.get('state') == 'BLOCKED':
        f.append(Finding('independent model review', WITH_CONSTRAINTS,
                         'the reviewing model may be the same provider as the author; deterministic checks still gate release'))
    pub = R.capability_status('publish')
    if pub not in R.VERIFIED:
        f.append(Finding('publishing', WITH_CONSTRAINTS, f'publishing to a permanent address is {pub}',
                         'private preview and downloadable source code'))
    if contract.data_requirements.get('personal_data') and auth == 'none':
        f.append(Finding('personal data without sign-in', WITH_CONSTRAINTS,
                         'anyone with the link can see the data; the customer decided this explicitly'))
    outcome = max((x.outcome for x in f), key=lambda o: _RANK[o], default=FEASIBLE)
    return Feasibility(outcome, f)


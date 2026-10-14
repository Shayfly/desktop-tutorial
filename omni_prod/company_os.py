from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class Department:
    id: str
    name: str
    mission: str
    recurring_work: tuple[str, ...]
    automation: tuple[str, ...]
    founder_decisions: tuple[str, ...]
    gates: tuple[str, ...]
    kpis: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


DEPARTMENTS: tuple[Department, ...] = (
    Department('ceo', 'Founder / CEO / Strategy', 'Own direction, capital allocation and final risk decisions.',
               ('weekly priorities', 'roadmap tradeoffs', 'partner/investor decisions'),
               ('decision briefs', 'weekly scorecard', 'risk register summaries'),
               ('company strategy', 'spend approval', 'contracts', 'public launch', 'legal-risk override'),
               ('strategy alignment',), ('runway', 'north-star build acceptance', 'release readiness')),
    Department('product', 'Product Management', 'Turn user problems into measurable product requirements.',
               ('specs', 'acceptance criteria', 'backlog', 'user feedback triage'),
               ('prompt-to-spec agent', 'acceptance-contract generator', 'feedback clustering'),
               ('priority conflicts', 'pricing/packaging intent'),
               ('acceptance coverage',), ('task success', 'activation', 'accepted builds')),
    Department('ai', 'AI / Research', 'Improve reasoning, routing, generation, repair and media quality.',
               ('model evaluation', 'router tuning', 'prompt/system policy', 'fine-tuning datasets'),
               ('benchmark runner', 'model router', 'training-data export', 'cost optimizer'),
               ('new model/vendor approval', 'training-data policy'),
               ('model eval gate',), ('first-pass success', 'repair rounds', 'cost per accepted build')),
    Department('engineering', 'Software Engineering', 'Build and maintain the universal creation platform.',
               ('features', 'APIs', 'migrations', 'refactors', 'code review'),
               ('specialist coding agents', 'CI', 'static analysis', 'repository intelligence'),
               ('architecture changes with business impact',),
               ('compile/test gate', 'backward compatibility'), ('defect escape rate', 'cycle time', 'test pass rate')),
    Department('design', 'Design / Creative', 'Make 148AI and generated products feel premium, distinct and accessible.',
               ('UX flows', 'design system', 'visual QA', 'asset direction'),
               ('creative director', 'design tokens', 'anti-template checks', 'media gateway'),
               ('brand identity changes',),
               ('accessibility gate', 'design-quality gate'), ('user completion rate', 'design acceptance', 'accessibility defects')),
    Department('qa', 'QA / Evals / Release', 'Prove behavior before release and prevent regressions.',
               ('unit/integration/E2E', 'benchmarks', 'regression', 'release evidence'),
               ('pytest/CI', '200+ benchmark suite', 'clean-ZIP verification', 'hostile tests'),
               ('exceptional release with failed gate'),
               ('all required release gates',), ('escaped bugs', 'benchmark success', 'rollback rate')),
    Department('security', 'Security / Privacy', 'Protect tenants, secrets, generated code and infrastructure.',
               ('threat modeling', 'secret scanning', 'tenant tests', 'abuse controls', 'incident response'),
               ('sandbox', 'secret scanner', 'RBAC tests', 'audit chain', 'rate limits'),
               ('security-risk acceptance', 'incident disclosure'),
               ('security gate', 'tenant isolation'), ('critical vulnerabilities', 'MTTR', 'unauthorized access incidents')),
    Department('legal', 'Legal / IP / Compliance', 'Track rights, consent, licenses, privacy and jurisdiction-specific launch risk.',
               ('rights manifest', 'license/consent records', 'policy updates', 'terms/privacy review'),
               ('Rights & IP Engine', 'jurisdiction profiles', 'provenance manifest'),
               ('legal advice', 'contract signature', 'high-risk rights override', 'regulatory filing'),
               ('rights publish gate', 'privacy/compliance gate'), ('unresolved rights blockers', 'provenance coverage')),
    Department('infra', 'DevOps / SRE / Platform', 'Keep builds and customer products available, recoverable and cost-controlled.',
               ('deploys', 'queues', 'DB/storage', 'backups', 'monitoring', 'capacity'),
               ('Docker/remote sandbox', 'Postgres/Redis/S3 adapters', 'metrics', 'recovery drills'),
               ('major vendor spend', 'regional/data-residency choice'),
               ('readiness gate', 'backup/restore gate'), ('uptime', 'p95 latency', 'build queue time', 'recovery point/time')),
    Department('data', 'Data / Analytics', 'Measure product quality, economics and behavior without misleading metrics.',
               ('event schema', 'funnels', 'cost attribution', 'experiment analysis'),
               ('product analytics', 'usage metering', 'human evaluation'),
               ('sensitive-data use',),
               ('data-quality/privacy gate',), ('activation', 'retention', 'cost/build', 'accepted-build rate')),
    Department('finance', 'Finance / Operations', 'Control runway, vendors, billing and operational records.',
               ('budget', 'vendor review', 'billing reconciliation', 'forecast'),
               ('usage/cost reports', 'budget alerts', 'invoice export'),
               ('payments', 'banking', 'tax filings', 'large purchases'),
               ('budget gate',), ('runway', 'gross margin', 'vendor spend')),
    Department('support', 'Customer Success / Support', 'Turn user problems into resolved incidents and product learning.',
               ('support triage', 'bug reproduction', 'docs', 'incident communication'),
               ('support classifier', 'known-issue search', 'diagnostic bundle'),
               ('refund exceptions', 'sensitive customer commitments'),
               ('support SLA gate',), ('time to resolution', 'repeat issue rate', 'CSAT')),
    Department('growth', 'Growth / Sales / Partnerships', 'Acquire users only after product truth is strong enough.',
               ('launch assets', 'partnerships', 'sales pipeline', 'case studies'),
               ('content drafts', 'CRM automation', 'experiment tracking'),
               ('public claims', 'partnership contracts', 'discount authority'),
               ('claim substantiation gate',), ('qualified users', 'conversion', 'retention', 'CAC/payback')),
)


@dataclass(frozen=True)
class CompanySignal:
    kind: str
    title: str
    severity: str = 'medium'
    detail: str = ''
    source: str = 'system'

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OperatingTask:
    id: str
    department_id: str
    title: str
    priority_score: int
    priority: str
    action_mode: str
    founder_approval_required: bool
    reason: str
    source_signal: dict

    def to_dict(self) -> dict:
        return asdict(self)


_SIGNAL_ROUTING: dict[str, tuple[str, int, bool]] = {
    'security_alert': ('security', 95, True),
    'rights_alert': ('legal', 92, True),
    'privacy_alert': ('security', 92, True),
    'production_incident': ('infra', 90, True),
    'release_failure': ('qa', 88, False),
    'build_failure': ('engineering', 82, False),
    'model_failure': ('ai', 80, False),
    'customer_blocker': ('support', 78, False),
    'customer_feedback': ('product', 62, False),
    'design_issue': ('design', 60, False),
    'cost_alert': ('finance', 76, True),
    'data_quality': ('data', 65, False),
    'growth_opportunity': ('growth', 45, True),
    'strategy_decision': ('ceo', 90, True),
}

_SEVERITY_BONUS = {'low': 0, 'medium': 5, 'high': 12, 'critical': 25}


class OnePersonCompanyOS:
    """Operating model for a one-founder company with automated departments.

    It intentionally separates reversible automated work from founder-only or
    professional-review decisions. The system can prepare evidence and execute
    bounded workflows; it must not silently assume authority over money,
    contracts, legal conclusions or public-launch risk acceptance.
    """

    def departments(self) -> list[dict]:
        return [d.to_dict() for d in DEPARTMENTS]

    def department(self, department_id: str) -> dict:
        for d in DEPARTMENTS:
            if d.id == department_id:
                return d.to_dict()
        raise KeyError(department_id)

    def release_council(self) -> dict:
        return {
            'required_departments': ['product', 'engineering', 'qa', 'security', 'legal', 'infra'],
            'required_gates': [
                'acceptance criteria satisfied',
                'tests and regression pass',
                'tenant/security gate pass',
                'rights/IP publish gate clear',
                'infrastructure readiness pass',
                'backup/restore evidence present',
            ],
            'founder_must_approve': ['public launch', 'material spend', 'legal-risk override', 'customer-impacting irreversible action'],
            'rule': 'Automation prepares evidence; the founder approves irreversible/high-risk business decisions.',
        }

    def daily_loop(self) -> tuple[str, ...]:
        return (
            'Collect failures, user feedback and security/rights alerts.',
            'Prioritize by customer impact, safety, revenue and strategic fit.',
            'Run build/test/repair agents on approved engineering work.',
            'Run QA, security, rights and readiness gates.',
            'Ship only green releases; create recovery artifact and checksum.',
            'Update scorecard: accepted builds, failures, cost, latency, incidents and blockers.',
        )

    def triage(self, signals: Iterable[CompanySignal | Mapping[str, Any]]) -> list[dict]:
        """Route company signals into a prioritized virtual-department work queue."""
        tasks: list[OperatingTask] = []
        for idx, raw in enumerate(signals, 1):
            if isinstance(raw, CompanySignal):
                signal = raw
            else:
                signal = CompanySignal(
                    kind=str(raw.get('kind', 'customer_feedback')),
                    title=str(raw.get('title', 'Untitled company signal'))[:300],
                    severity=str(raw.get('severity', 'medium')).lower(),
                    detail=str(raw.get('detail', ''))[:4000],
                    source=str(raw.get('source', 'system'))[:120],
                )
            department_id, base, founder = _SIGNAL_ROUTING.get(signal.kind, ('product', 55, False))
            score = min(100, base + _SEVERITY_BONUS.get(signal.severity, 5))
            priority = 'P0' if score >= 95 else 'P1' if score >= 82 else 'P2' if score >= 65 else 'P3'
            action_mode = 'founder-review' if founder else 'automated-workflow'
            reason = f'{signal.kind} routed to {department_id}; severity={signal.severity}; score={score}'
            tasks.append(OperatingTask(
                id=f'op-{idx:04d}', department_id=department_id, title=signal.title,
                priority_score=score, priority=priority, action_mode=action_mode,
                founder_approval_required=founder, reason=reason, source_signal=signal.to_dict(),
            ))
        tasks.sort(key=lambda t: (-t.priority_score, t.id))
        return [t.to_dict() for t in tasks]

    def ceo_brief(
        self,
        *,
        signals: Iterable[CompanySignal | Mapping[str, Any]] = (),
        metrics: Mapping[str, Any] | None = None,
        max_priorities: int = 7,
    ) -> dict:
        queue = self.triage(signals)
        priorities = queue[:max(1, min(int(max_priorities), 20))]
        approvals = [t for t in queue if t['founder_approval_required']]
        return {
            'operating_model': 'one-founder / automated departments',
            'top_priorities': priorities,
            'founder_approval_queue': approvals,
            'metrics': dict(metrics or {}),
            'release_council': self.release_council(),
            'decision_rule': 'Do not spend, sign, publish, override legal/security gates, or make irreversible customer-impacting changes without founder authorization.',
        }

    def evaluate_release(self, gate_results: Mapping[str, Any], *, founder_public_launch_approved: bool = False) -> dict:
        """Cross-functional release council evaluation.

        Expected logical gate keys are intentionally stable so automated systems
        can map richer evidence onto them without changing the council contract.
        """
        required = {
            'product_acceptance': 'product',
            'engineering_regression': 'engineering',
            'qa_evals': 'qa',
            'security_tenant_isolation': 'security',
            'rights_ip': 'legal',
            'infrastructure_readiness': 'infra',
            'backup_restore': 'infra',
        }
        normalized: dict[str, bool] = {}
        blockers: list[dict] = []
        for gate, department in required.items():
            raw = gate_results.get(gate, False)
            ok = bool(raw.get('ok')) if isinstance(raw, Mapping) else bool(raw)
            normalized[gate] = ok
            if not ok:
                blockers.append({'gate': gate, 'department': department})
        technical_green = not blockers
        return {
            'technical_green': technical_green,
            'public_launch_ready': technical_green and founder_public_launch_approved,
            'founder_public_launch_approved': bool(founder_public_launch_approved),
            'blockers': blockers,
            'gates': normalized,
            'rule': 'Technical green is necessary but public launch remains a founder decision.',
        }

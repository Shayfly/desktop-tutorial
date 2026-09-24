from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import time
from typing import Callable

@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    category: str
    prompt: str
    difficulty: str='standard'

_DOMAINS = {
    'web': 'responsive public website with CMS, forms, SEO, analytics and accessibility',
    'saas': 'multi-tenant SaaS with organizations, RBAC, audit history, billing boundaries and exports',
    'crm': 'CRM with contacts, companies, pipeline, tasks, notes, permissions and reporting',
    'marketplace': 'two-sided marketplace with listings, search, bookings/orders, reviews, payouts ledger and disputes',
    'commerce': 'ecommerce system with catalog, inventory, cart, checkout adapter, orders, refunds and admin',
    'booking': 'booking platform with resource calendars, availability, cancellation rules, reminders and admin',
    'realtime': 'realtime collaboration product with presence, event streams, reconnect logic and moderation',
    'mobile': 'mobile-first product with offline-safe state, camera/file flows, notifications design and sync conflicts',
    'analytics': 'analytics application with ingestion API, dashboards, cohorts, funnels, scheduled exports and retention',
    'operations': 'operations system with work orders, owners, SLAs, status history, attachments and dashboards',
    'finance': 'finance workflow with invoices, ledger entries, reconciliation, aging, exports and audit controls',
    'education': 'learning platform with courses, lessons, progress, quizzes, roles and teacher analytics',
    'creator': 'creator platform with memberships, gated content, moderation, notifications and subscription boundaries',
    'ai': 'AI application with retrieval/tool interfaces, citations, model routing, quotas and evaluation hooks',
    'automation': 'workflow automation system with triggers, actions, retries, idempotency, secrets and run history',
    'developer': 'developer platform with projects, environments, API keys, logs, webhooks, quotas and team roles',
    'support': 'customer support desk with inbox, assignment, SLAs, macros, knowledge base and analytics',
    'logistics': 'logistics platform with dispatch, drivers, routes, status events, proof of delivery and operations map',
    'game2d': '2D game project with player loop, menus, save state, controller input, audio hooks and testable game rules',
    'game3d': '3D game prototype with player controller, camera, physics, progression, menus, audio hooks and performance budget',
}
_VARIANTS = (
    ('01','standard','Make it production-structured, responsive and accessible.'),
    ('02','standard','Add multilingual English/Hebrew support with RTL and locale-safe formatting.'),
    ('03','advanced','Add organization/team permissions, audit history and immutable versioning.'),
    ('04','advanced','Add resilient background jobs, retries, idempotency and failure recovery.'),
    ('05','advanced','Add realtime updates, optimistic UI and reconnection behavior where appropriate.'),
    ('06','advanced','Add integrations through secret references only; never hard-code credentials.'),
    ('07','hard','Add load-aware architecture, caching, rate limits, observability and SLO instrumentation.'),
    ('08','hard','Add security threat controls, abuse prevention, least privilege and hostile-input tests.'),
    ('09','hard','Add mobile-friendly UX, offline/degraded-state behavior and export/import paths.'),
    ('10','hard','Add CI, deployment manifest, rollback plan, acceptance tests and cost-conscious architecture.'),
)

CASES = tuple(
    BenchmarkCase(f'{category}-{suffix}', category, f'Build a {description}. {extra}', difficulty)
    for category, description in _DOMAINS.items()
    for suffix, difficulty, extra in _VARIANTS
)

@dataclass
class BenchmarkResult:
    case_id: str
    category: str
    status: str
    repair_rounds: int
    duration_ms: int
    file_count: int
    error: str = ''
    difficulty: str = 'standard'

class BenchmarkRunner:
    def __init__(self, engine_factory: Callable[[], object]):
        self.engine_factory = engine_factory

    def run(self, cases: tuple[BenchmarkCase, ...] = CASES) -> list[BenchmarkResult]:
        out=[]
        for case in cases:
            started=time.monotonic()
            try:
                result=self.engine_factory().build(case.prompt)
                out.append(BenchmarkResult(case.id,case.category,result.status,result.repair_rounds,
                    int((time.monotonic()-started)*1000),len(result.repository),'',case.difficulty))
            except Exception as exc:
                out.append(BenchmarkResult(case.id,case.category,'error',0,
                    int((time.monotonic()-started)*1000),0,str(exc)[:500],case.difficulty))
        return out

    @staticmethod
    def summarize(results: list[BenchmarkResult]) -> dict:
        total=len(results)
        ready=sum(1 for r in results if r.status=='ready')
        durations=sorted(r.duration_ms for r in results)
        p95=durations[min(len(durations)-1,int((len(durations)-1)*.95))] if durations else 0
        by_category={}
        for r in results:
            d=by_category.setdefault(r.category,{'total':0,'ready':0})
            d['total']+=1; d['ready']+= int(r.status=='ready')
        return {'cases':total,'ready':ready,'success_rate':round(ready/total,4) if total else 0,
                'p95_duration_ms':p95,'by_category':by_category}

    @staticmethod
    def write(path: str | Path, results: list[BenchmarkResult]) -> None:
        payload={'schema':2,**BenchmarkRunner.summarize(results),'results':[asdict(r) for r in results]}
        Path(path).write_text(json.dumps(payload, indent=2), encoding='utf-8')

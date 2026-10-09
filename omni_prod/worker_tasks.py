from __future__ import annotations

"""RQ worker entrypoints: M1 durable async builds and M3 real running previews.

Each entrypoint is a thin wrapper that lazily imports `.investor_app` (so this
module stays importable without fastapi) and delegates to a `_run_*` function
whose dependencies are all injected. The `_run_*` functions hold every
decision -- billing, gates, state transitions, cleanup -- and are what
tests/test_m3_preview_logic.py exercises.

M1 history (still true): the worker drives the real AI engine
(`AutonomousProductEngine` via investor_app._live_components()), not
`_v28.engine` (`UnifiedOmniEngine`, the deterministic template engine) --
calling the latter would be the "deterministic template fallback that pretends
an AI build succeeded" the master directive forbids.

M3 Revision 2 / M1 blocker resolution changes, each verified against real code:

* Billing. Failures no longer blindly `release()`. The directive refers to a
  `budget.provider_cost_usd`; no such object exists anywhere in this codebase
  (`AutonomousResult` carries no cost, and `OpenAICompatibleGateway` discards
  the provider's `usage` block). The only real spend signal is
  `RoutedModelGateway.state` -- `external_spend_usd` / `external_calls`,
  incremented by `model_policy.authorize_model_call()` for every external
  model call the platform authorized and dispatched. That is what is used,
  and it is labelled in the build evidence as an authorized-estimate ledger,
  not provider-measured usage. Rule: READY -> settle(actual=spent);
  FAILED with spent > 0 or any external call -> settle(actual=spent);
  FAILED with no external spend -> release().
  `_live_engine()` discarded the gateway, so the worker now uses
  `_live_components()` (engine, gateway) -- the same call the synchronous
  live-build endpoints make.

* Gates. READY previously meant only `result.status == 'ready'` (sandbox
  verification). The canonical synchronous path (`v28_live_build`) computes
  release readiness as verification AND `assess_repository` AND
  `hostile_repository_scan` AND `rights.assess(...).publish_allowed`, and adds
  the creative manifest, rights manifest and plan branding/provenance to the
  committed repository. The async worker now does exactly the same, so it is
  a real replacement for that path rather than a weaker shadow of it.
"""

import json
import logging
import os
import socket
import time
from decimal import Decimal

from .models import BuildStatus
from .build_contract import BuildContract, BuildContractStatus
from .capability_worker import CapabilityStageBlocked
from .infrastructure_provisioner import InfrastructureStageBlocked
from .build_control import BuildCancelled, BuildControl, install as install_build_control


def set_acceptance_scope(engine, contract: dict | None) -> None:
    """Requirements-aware acceptance: hand the approved contract's scope to the
    in-build behavioural acceptance (no contract -> strict floor)."""
    from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    target = find_in_chain(getattr(engine, 'executor', None), BehaviorAcceptanceExecutor)
    if target is None or not contract:
        return
    target.scope = {k: contract.get(k) for k in ('infrastructure', 'required_integrations', 'user_roles',
                                                  'defaults_applied', 'prompt')}


def behavior_evidence(engine) -> dict | None:
    from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    target = find_in_chain(getattr(engine, 'executor', None), BehaviorAcceptanceExecutor)
    if target is None:
        return None
    return {'last': target.last_report, 'rounds': list(target.history)}
from .modification_engine import CandidateModificationEngine
from .provider_usage import ProviderUsageLedger
from .spec_repository import SpecNotFound

# Order matters: the first failing gate is the one reported as error_code.
GATE_ORDER = ('verification', 'quality', 'security', 'rights')

SPEND_BASIS = ('authorized external-model spend ledger (RoutedModelGateway.state.external_spend_usd): each call '
               'reserves its worst case and is settled down to reported tokens x catalog price when the provider '
               'reports usage; calls without reported usage stay at their worst case. Provider-reported usage is in '
               'provider_usage. A call the provider refused with an HTTP error status (quota, overload, bad key) '
               'is released to zero: it was not served and is not billed')


def _skills_applied() -> list:
    try:
        from .skills_runtime import applied_skills
        return applied_skills()
    except Exception:  # evidence must never fail a build
        return []


def failure_code(exc: BaseException) -> str:
    """Customer-meaningful error code for an exception that ended a job.

    bld_ccd38bd0 (2026-10-08) stopped on 'external model budget exceeded' and
    was reported as the generic worker_exception ("internal error")."""
    from .model_gateway import ModelGatewayError
    from .model_policy import ModelPolicyViolation
    text = str(exc)
    if isinstance(exc, ModelPolicyViolation):
        if 'budget exceeded' in text or 'call limit' in text:
            return 'model_budget_exhausted'
        return 'model_policy_blocked'
    if isinstance(exc, ModelGatewayError) and 'all model routes failed' in text:
        return 'model_unavailable'
    return 'worker_exception'


def _report_phase(jobs, build_id: str, phase: str, message: str = '') -> None:
    """M5-UX01: best-effort progress for the creator timeline; never fails a build."""
    update = getattr(jobs, 'update_phase', None)
    if update is None:
        return
    try:
        update(build_id, phase, message)
    except Exception:
        pass


def provider_usage_evidence(gateway) -> dict:
    """M5 Task 8: provider-reported usage summary for build evidence."""
    spent, calls = spend_snapshot(gateway)
    ledger = getattr(gateway, 'usage', None) if gateway is not None else None
    if isinstance(ledger, ProviderUsageLedger):
        return ledger.summary(authorized_external_calls=calls, authorized_estimate_usd=spent)
    return {
        'usage_events': [], 'request_ids': [], 'input_tokens': None, 'output_tokens': None,
        'cached_tokens': None, 'authorized_external_calls': calls, 'external_usage_records': 0,
        'actual_cost_usd': None if calls else '0',
        'actual_cost_basis': 'NOT_CAPTURED_BY_GATEWAY' if calls else 'NO_EXTERNAL_CALLS',
        'authorized_estimate_usd': str(spent),
        'truth_note': 'this gateway exposes no provider usage ledger; actual cost is unknown when external calls occurred.',
    }


# --------------------------------------------------------------------------
# M1: durable async build
# --------------------------------------------------------------------------

def spend_snapshot(gateway) -> tuple[Decimal, int]:
    state = getattr(gateway, 'state', None) if gateway is not None else None
    if state is None:
        return Decimal('0'), 0
    spent = getattr(state, 'external_spend_usd', Decimal('0')) or Decimal('0')
    calls = int(getattr(state, 'external_calls', 0) or 0)
    return Decimal(str(spent)), calls


def resolve_billing(subscriptions, *, build_id: str, ready: bool, spent: Decimal, external_calls: int) -> str:
    """settle() whenever real provider spend was incurred (or the build is
    READY); release() only when a failed build incurred no external spend."""
    if ready or spent > 0 or external_calls > 0:
        subscriptions.settle(build_id=build_id, actual_provider_cost_usd=spent)
        return 'settled'
    subscriptions.release(build_id=build_id)
    return 'released'


def _capability_actual_cost(capability_evidence) -> tuple[Decimal | None, bool]:
    usage = [] if not capability_evidence else list(capability_evidence.get('usage') or [])
    if not usage:
        return Decimal('0'), False
    total = Decimal('0')
    for event in usage:
        raw = event.get('actual_cost_usd')
        if raw is None:
            return None, True
        total += Decimal(str(raw))
    return total, True


def asset_capability_status(plan) -> dict | None:
    """REQUIRED / OPTIONAL / NOT_REQUIRED per asset capability (decision #28)."""
    if plan is None:
        return None
    from .capability_planner import asset_capability_status as _status
    return _status(plan)


def bind_model_budget_to_reservation(gateway, request: dict) -> dict:
    """Admission reserved `components.llm_maximum_usd` for model calls; the
    worker's gateway may not spend more than that, whatever its own
    environment says (the API and worker are configured separately).

    Requests without a component breakdown predate the M5 quote and are left
    unchanged, recorded as `legacy_unbound`.
    """
    components = (request.get('economics_quote') or {}).get('components') or {}
    if 'llm_maximum_usd' not in components:
        return {'binding': 'legacy_unbound'}
    if not hasattr(gateway, 'bind_budget'):
        return {'binding': 'not_applicable'}
    return {'binding': 'bound', **gateway.bind_budget(Decimal(str(components['llm_maximum_usd'])))}


def capability_authorization_ceiling(request: dict) -> Decimal:
    """Ceiling for the external capability stage.

    M5 remediation: when the durable quote carries a component breakdown, the
    capability stage may only spend the capability slice that was priced and
    reserved for it -- never the LLM budget. Legacy quotes without components
    keep the previous behaviour (the reservation amount).
    """
    components = (request.get('economics_quote') or {}).get('components') or {}
    if 'capability_authorization_usd' in components:
        return Decimal(str(components['capability_authorization_usd']))
    return Decimal(str(request.get('authorized_provider_cost_usd', '0.25')))


def resolve_m5_billing(
    subscriptions, *, build_id: str, ready: bool, gateway, capability_evidence, economics_quote: dict | None,
) -> tuple[str, dict, Decimal | None]:
    """Truth-preserving M5 settlement.

    RoutedModelGateway exposes an authorized estimate ledger, not provider-reported
    usage, so any external model call makes the overall actual provider cost unknown
    unless a later normalized usage adapter supplies it. Capability-provider events,
    by contrast, may carry real actual cost. Unknown actuals remain NULL and settle
    against the conservative reservation rather than being relabelled as actual.
    """
    _, external_calls = spend_snapshot(gateway)
    capability_actual, capability_activity = _capability_actual_cost(capability_evidence)
    paid_activity = external_calls > 0 or capability_activity
    if not ready and not paid_activity:
        subscriptions.release(build_id=build_id)
        return 'released', {'action': 'released'}, None

    # M5 Task 8: model spend is actual only when every authorized external call
    # left a provider-reported cost. Otherwise it stays unknown (NULL); the
    # authorized estimate is never relabelled as actual.
    if external_calls == 0:
        llm_actual = Decimal('0')
    else:
        ledger = getattr(gateway, 'usage', None)
        llm_actual = (ledger.actual_external_cost_usd(authorized_external_calls=external_calls)
                      if isinstance(ledger, ProviderUsageLedger) else None)
    quote = dict(economics_quote or {})
    # Generated-app/platform infrastructure is reserved at its conservative
    # maximum; no provider reports its actual per-build cost, so any non-zero
    # infrastructure maximum leaves the total actual unknown (NULL).
    infra_max = Decimal(str(quote.get('infrastructure_maximum_usd', '0') or '0'))
    infra_actual = Decimal('0') if infra_max == 0 else None
    actual = (None if llm_actual is None or capability_actual is None or infra_actual is None
              else llm_actual + capability_actual + infra_actual)
    revenue_raw = quote.get('revenue_usd')
    # Gross contribution is only computed when all non-provider variable cost
    # inputs are known. A non-zero infrastructure maximum is still a reserve,
    # not an actual, so suppress contribution rather than fabricate precision.
    revenue = None if revenue_raw is None or infra_max != 0 else Decimal(str(revenue_raw))
    settlement = subscriptions.settle(
        build_id=build_id, actual_provider_cost_usd=actual,
        revenue_usd=revenue, infra_cost_usd=Decimal('0'),
    )
    evidence = {'action': 'settled'}
    if settlement:
        evidence.update(settlement)
    return 'settled', evidence, actual


def evaluate_release_gates(*, result, quality, security, rights) -> tuple[bool, str | None, str | None]:
    if result.status != 'ready' or not result.report.passed:
        from .dependency_policy import UNSUPPORTED_DEPENDENCY
        from .quality_gate import QUALITY_FAILURE_ID
        report_failures = tuple(getattr(result.report, 'failures', ()) or ())
        from .preview_smoke import PREVIEW_FAILURE_ID
        if report_failures and all(getattr(f, 'acceptance_id', None) == PREVIEW_FAILURE_ID for f in report_failures):
            # Every acceptance check passed; the product would not start for preview.
            return False, 'preview_not_ready', ('the product passed its checks but did not start for preview '
                                                'after repair: ' + '; '.join(f.message for f in report_failures))[:2000]
        if report_failures and all(getattr(f, 'acceptance_id', None) == QUALITY_FAILURE_ID for f in report_failures):
            # Every acceptance check passed; only the quality bar was missed
            # after the repair rounds.
            return False, 'quality_gate_failed', (
                f'quality score {quality.score} below minimum {quality.minimum_score} after repair: '
                + '; '.join(f.message for f in report_failures))[:2000]
        unsupported = [f for f in getattr(result.report, 'failures', ()) or ()
                       if getattr(f, 'acceptance_id', None) == UNSUPPORTED_DEPENDENCY]
        if unsupported:
            return False, 'unsupported_dependency', unsupported[0].message[:2000]
        return False, 'verification_failed', 'build did not pass sandbox verification'
    if not quality.passed:
        blockers = '; '.join(getattr(quality, 'blockers', ()) or ()) or 'no blocker detail'
        return False, 'quality_gate_failed', (
            f'quality score {quality.score} below minimum {quality.minimum_score} ({blockers})')
    if not security.passed:
        return False, 'security_gate_failed', f'hostile repository scan: {len(security.findings)} finding(s)'
    if not rights.publish_allowed:
        status = getattr(rights.status, 'value', rights.status)
        return False, 'rights_gate_not_clear', (
            f'rights status {status}: the version was committed, but it is not releasable until rights '
            'evidence is added or the original alternative is used')
    return True, None, None


def _rights_evidence_from_dicts(items) -> tuple:
    from .rights_ip import RightKind, RightsEvidence
    out = []
    for item in items or ():
        if isinstance(item, RightsEvidence):
            out.append(item)
            continue
        out.append(RightsEvidence(
            id=str(item['id']), right_kind=RightKind(item['right_kind']), subject=str(item['subject']),
            evidence_type=str(item['evidence_type']), scope=str(item['scope']),
            source_reference=str(item.get('source_reference', '')), verified=bool(item.get('verified', False)),
        ))
    return tuple(out)


def _run_live_build_job(build_id: str, *, jobs, platform, workspace, components_factory,
                        quality_fn, security_fn, min_quality: int = 80, preflight=None,
                        capability_stage=None, infrastructure_stage=None,
                        infrastructure_environment: str = 'preview', spec_repo=None) -> str | None:
    """Returns the terminal BuildStatus value written, or None if nothing was
    done (unknown build id / already claimed by another delivery)."""
    try:
        request = jobs.get_request(build_id)
    except KeyError:
        return None
    if not jobs.transition(build_id=build_id, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING):
        return None  # duplicate delivery / already handled: idempotent no-op

    subscriptions = platform.subscriptions
    internal_project_id = request['internal_project_id']
    markets = tuple(request.get('target_markets') or ()) or ('US', 'EU', 'IL')
    contract_data = request.get('build_contract')
    build_contract = None
    contract_evidence = {
        'id': request.get('build_contract_id'),
        'fingerprint': request.get('build_contract_fingerprint'),
        'binding': request.get('build_contract_binding') or 'LEGACY_UNBOUND',
    }
    if contract_data is not None:
        build_contract = BuildContract.from_dict(contract_data)
        if build_contract.status != BuildContractStatus.READY:
            raise RuntimeError('bound build contract is not READY')
        if not build_contract.verify_fingerprint():
            raise RuntimeError('bound build contract fingerprint is invalid')
        if request.get('public_project_id') and build_contract.project_id != request.get('public_project_id'):
            raise RuntimeError('bound build contract project mismatch')
        prompt = build_contract.prompt
    else:
        prompt = request['prompt']

    gateway = None
    version_id = None
    artifact_key = None
    capability_evidence = None
    infrastructure_evidence = None
    model_budget_binding = None

    try:
        if preflight is not None:
            preflight()
        _report_phase(jobs, build_id, 'PLANNING', 'validating the build contract and product plan')
        # M5 Task 6: a contract-bound product cannot become READY without its
        # required generated-app infrastructure. Checked before any paid model
        # generation so a missing binding never burns provider budget.
        if infrastructure_stage is not None and build_contract is not None:
            _report_phase(jobs, build_id, 'INFRASTRUCTURE', 'provisioning and verifying app infrastructure')
            infrastructure_evidence = infrastructure_stage.require_ready(
                build_contract, tenant_id=str(request['user_id']),
                project_id=build_contract.project_id, environment=infrastructure_environment,
            )
        brain = platform.brain.decide(prompt, target_markets=markets)
        capability_plan = build_contract.capability_plan if build_contract is not None else getattr(brain, 'capabilities', None)
        if capability_stage is not None:
            _report_phase(jobs, build_id, 'ASSETS', 'generating and verifying required assets')
            if capability_plan is None:
                raise RuntimeError('capability stage requires a bound or planned capability plan')
            capability_evidence = capability_stage.prepare(
                build_id=build_id, project_id=internal_project_id, plan=capability_plan,
                authorized_maximum_usd=capability_authorization_ceiling(request),
                now=time.time(),
            )
        rights = platform.rights.assess(
            prompt, target_markets=markets,
            evidence=_rights_evidence_from_dicts(request.get('rights_evidence')),
            synthetic_person_media=bool(brain.rights.required_disclosures),
        )
        engine, gateway = components_factory()
        model_budget_binding = bind_model_budget_to_reservation(gateway, request)
        # Directive 2026-10-09 §10/§12: stop between steps; live log.
        control = BuildControl(jobs, build_id)
        install_build_control(engine, gateway, control)
        set_acceptance_scope(engine, build_contract.to_dict() if build_contract is not None else None)
        control.checkpoint()
        _report_phase(jobs, build_id, 'GENERATING', 'generating code, building, testing and repairing')
        result = engine.build(prompt)
        _report_phase(jobs, build_id, 'VERIFYING', 'running quality, security and rights gates')
        quality = quality_fn(spec=result.spec, repository=result.repository, minimum_score=min_quality)
        security = security_fn(result.repository)

        core_ready, error_code, error_message = evaluate_release_gates(
            result=result, quality=quality, security=security, rights=rights)
        if capability_stage is not None:
            capability_evidence = capability_stage.finalize_native(
                build_id=build_id, plan=capability_plan, core_ready=core_ready,
                evidence={'verification': bool(result.report.passed and result.status == 'ready'),
                          'quality': bool(quality.passed), 'security': bool(security.passed),
                          'rights': bool(rights.publish_allowed)},
            )
        capability_ready = True if capability_stage is None else bool(capability_evidence.get('required_ready'))
        ready = core_ready and capability_ready
        if core_ready and not capability_ready:
            error_code, error_message = 'capability_gate_failed', 'required capability evidence is not VERIFIED'

        repo = dict(result.repository)
        repo.update(platform.brain.creative.repository_files(
            brain.creative, capability_evidence=capability_evidence
        ))
        repo.update(platform.rights.repository_files(rights, original_prompt=prompt))
        plan = subscriptions.plan_for(request['user_id'])
        repo = platform.branding.decorate_repository(
            repo, plan=plan.code,
            # Rows written before migration 015 have no public id; the
            # internal tenant key is an opaque hash, so falling back to it
            # leaks nothing, it is just less friendly in provenance.json.
            project_id=request.get('public_project_id') or internal_project_id,
            requested_visible=request.get('branding_visible'),
            white_label_name=request.get('white_label_name'),
        )
        # Golden E2E #1 (2026-10-07): the first READY build could not be
        # modified ("predates spec tracking (M4B)") because the live build
        # never stored its ProductSpec. The version and its spec are written
        # in one transaction, the same pattern modification acceptance uses.
        # Golden E2E #1 (2026-10-07): a build that failed verification or
        # quality was still committed as the project's newest version, so the
        # next modification ran against the failed product. Only a build whose
        # code passed (READY, or blocked solely by rights evidence, which the
        # rights gate documents as committed-but-not-releasable) becomes a
        # version.
        commit_version = ready or error_code == 'rights_gate_not_clear'
        pool = getattr(workspace, 'pool', None)
        if not commit_version:
            version = None
        elif spec_repo is not None and pool is not None:
            with pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        version = workspace.commit(project_id=internal_project_id, repository=repo,
                                                   message=f'148AI async live build {build_id}', cur=cur)
                        spec_repo.save(version_id=version.id, project_id=internal_project_id,
                                       spec=result.spec, cur=cur)
        else:
            version = workspace.commit(project_id=internal_project_id, repository=repo,
                                       message=f'148AI async live build {build_id}')
        version_id = version.id if version is not None else None
        artifact_key = getattr(version, 'artifact_key', None) if version is not None else None

        spent, calls = spend_snapshot(gateway)
        evidence = {
            'gates': {
                'verification': {'passed': bool(result.report.passed and result.status == 'ready'),
                                 'failures': [{'acceptance_id': f.acceptance_id, 'message': f.message,
                                               'evidence': f.evidence} for f in result.report.failures]},
                'quality': quality.to_dict(),
                'security': security.to_dict(),
                'rights': rights.to_dict(),
            },
            'release_ready': ready,
            'build_contract': contract_evidence,
            'capabilities': capability_evidence,
            'infrastructure': infrastructure_evidence,
            'repair_rounds': result.repair_rounds,
            'repair_stop_reason': getattr(result, 'stop_reason', None) or None,
            'build_log_tail': result.report.build_log[-4000:],
            'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
            'provider_usage': provider_usage_evidence(gateway),
            'provider_spend_usd': str(spent), 'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
            'model_budget_binding': model_budget_binding,
            'asset_capabilities': asset_capability_status(capability_plan),
            # Agent OS §11: which skills shaped the build and what QA review found.
            'skills_applied': _skills_applied(),
            'product_review': list(getattr(getattr(engine, 'executor', None), 'reviews', None) or []),
            # Directive 2026-10-09 §17: real-browser flow check ('unavailable' is never read as passed).
            'browser_check': getattr(getattr(engine, 'executor', None), 'last_probe', None),
            # Autonomous completion §1: behavioural acceptance inside the build (last run + every round).
            'behavior_acceptance': behavior_evidence(engine),
        }
    except BuildCancelled as exc:
        spent, calls = spend_snapshot(gateway)
        economics_quote = request.get('economics_quote') or {}
        if economics_quote:
            billing, settlement_evidence, actual_cost = resolve_m5_billing(
                subscriptions, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence=capability_evidence, economics_quote=economics_quote,
            )
        else:
            billing = resolve_billing(subscriptions, build_id=build_id, ready=False, spent=spent, external_calls=calls)
            settlement_evidence, actual_cost = {'action': billing}, spent if billing == 'settled' else None
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.CANCELLED,
            error_code='cancelled_by_user', error_message=str(exc)[:500],
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence,
                           'provider_usage': provider_usage_evidence(gateway),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
                           'provider_spend_usd': str(spent), 'external_model_calls': calls,
                           'provider_spend_basis': SPEND_BASIS, 'model_budget_binding': model_budget_binding},
            actual_provider_cost_usd=actual_cost,
        )
        return BuildStatus.CANCELLED.value
    except InfrastructureStageBlocked as exc:
        spent, calls = spend_snapshot(gateway)
        economics_quote = request.get('economics_quote') or {}
        if economics_quote:
            billing, settlement_evidence, actual_cost = resolve_m5_billing(
                subscriptions, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence=capability_evidence, economics_quote=economics_quote,
            )
        else:
            billing = resolve_billing(subscriptions, build_id=build_id, ready=False, spent=spent, external_calls=calls)
            settlement_evidence, actual_cost = {'action': billing}, spent if billing == 'settled' else None
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
            error_code='infrastructure_not_configured', error_message=str(exc)[:2000],
            result_version_id=version_id, artifact_key=artifact_key,
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence,
                           'infrastructure': exc.evidence,
                           'provider_usage': provider_usage_evidence(gateway),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
                           'provider_spend_usd': str(spent), 'external_model_calls': calls,
                           'provider_spend_basis': SPEND_BASIS},
            actual_provider_cost_usd=actual_cost,
        )
        raise
    except CapabilityStageBlocked as exc:
        spent, calls = spend_snapshot(gateway)
        economics_quote = request.get('economics_quote') or {}
        if economics_quote:
            billing, settlement_evidence, actual_cost = resolve_m5_billing(
                subscriptions, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence=exc.evidence, economics_quote=economics_quote,
            )
        else:
            billing = resolve_billing(subscriptions, build_id=build_id, ready=False, spent=spent, external_calls=calls)
            settlement_evidence, actual_cost = {'action': billing}, spent if billing == 'settled' else None
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
            error_code='capability_not_configured', error_message=str(exc)[:2000],
            result_version_id=version_id, artifact_key=artifact_key,
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence, 'capabilities': exc.evidence,
                           'provider_usage': provider_usage_evidence(gateway),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
                           'provider_spend_usd': str(spent), 'external_model_calls': calls,
                           'provider_spend_basis': SPEND_BASIS},
            actual_provider_cost_usd=actual_cost,
        )
        raise
    except Exception as exc:
        spent, calls = spend_snapshot(gateway)
        economics_quote = request.get('economics_quote') or {}
        if economics_quote:
            billing, settlement_evidence, actual_cost = resolve_m5_billing(
                subscriptions, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence=capability_evidence, economics_quote=economics_quote,
            )
        else:
            billing = resolve_billing(subscriptions, build_id=build_id, ready=False, spent=spent, external_calls=calls)
            settlement_evidence, actual_cost = {'action': billing}, spent if billing == 'settled' else None
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
            error_code=failure_code(exc), error_message=f'{type(exc).__name__}: {exc}'[:2000],
            result_version_id=version_id, artifact_key=artifact_key,
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence,
                           'provider_usage': provider_usage_evidence(gateway),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
                           'provider_spend_usd': str(spent),
                           'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
                           'model_budget_binding': model_budget_binding},
            actual_provider_cost_usd=actual_cost,
        )
        raise

    economics_quote = request.get('economics_quote') or {}
    if economics_quote:
        billing, settlement_evidence, actual_cost = resolve_m5_billing(
            subscriptions, build_id=build_id, ready=ready, gateway=gateway,
            capability_evidence=capability_evidence, economics_quote=economics_quote,
        )
        evidence['billing'] = billing
        evidence['economics_quote'] = economics_quote
        evidence['economics_settlement'] = settlement_evidence
    else:
        evidence['billing'] = resolve_billing(subscriptions, build_id=build_id, ready=ready,
                                              spent=spent, external_calls=calls)
        actual_cost = spent if evidence['billing'] == 'settled' else None
    target = BuildStatus.READY if ready else BuildStatus.FAILED
    jobs.transition(
        build_id=build_id, expected=BuildStatus.RUNNING, target=target,
        error_code=error_code, error_message=error_message,
        result_version_id=version_id, artifact_key=artifact_key,
        repair_rounds=result.repair_rounds, evidence_json=evidence,
        actual_provider_cost_usd=actual_cost,
    )
    return target.value


def execute_live_build_job(build_id: str) -> None:
    from .investor_app import _v28, _v28_pool, _live_components
    from .job_repository import PostgresBuildRepository
    from .preview_runtime import ensure_durable_workspace
    from .quality_gate import assess_repository
    from .security_testing import hostile_repository_scan
    from .capability_repository import PostgresCapabilityRepository
    from .providers.image_provider import PostgresSubmissionJournal, build_image_capability_stage
    from .infrastructure_provisioner import (
        InfrastructureProvisioningService, PostgresInfrastructureBindingRepository)
    from .providers.managed_web_saas import build_managed_web_saas_provisioner

    if _v28_pool is None:
        raise RuntimeError(
            "execute_live_build_job requires OMNI_CREATOR_PERSISTENCE=postgres "
            "in the worker process (this process was not started with it)."
        )
    workspace = _v28.engine.workspace
    jobs = PostgresBuildRepository(_v28_pool)
    # Attempt Ledger: capture the gateway this build uses so its attempt
    # records are persisted whatever terminal path the build takes.
    captured = {}

    def components_factory():
        engine, gateway = _live_components()
        captured['gateway'] = gateway
        return engine, gateway

    try:
        _run_live_build_job_with_components(build_id, jobs=jobs, workspace=workspace,
                                            components_factory=components_factory)
    finally:
        _persist_build_attempts(_v28_pool, jobs, build_id, captured.get('gateway'))


def _persist_build_attempts(pool, jobs, build_id: str, gateway) -> None:
    """Best effort: telemetry must never change a build's outcome, but a
    failure to write it is logged loudly (telemetry completeness is a KPI)."""
    recorder = getattr(gateway, 'recorder', None)
    if recorder is None or not recorder.records:
        return
    try:
        from .attempt_ledger import persist_attempts
        status = jobs.get_status(build_id)
        try:
            request = jobs.get_request(build_id)
        except Exception:
            request = {}
        persist_attempts(pool, recorder.records, build_id=build_id,
                         tenant_id=request.get('user_id'), project_id=request.get('internal_project_id'),
                         reservation_id=build_id, final_outcome=getattr(status, 'value', None))
    except Exception:
        logging.getLogger(__name__).exception('attempt ledger write failed for %s', build_id)


def _run_live_build_job_with_components(build_id: str, *, jobs, workspace, components_factory) -> None:
    from .investor_app import _v28, _v28_pool
    from .quality_gate import assess_repository
    from .security_testing import hostile_repository_scan
    from .preview_runtime import ensure_durable_workspace
    from .capability_repository import PostgresCapabilityRepository
    from .providers.image_provider import PostgresSubmissionJournal, build_image_capability_stage
    from .infrastructure_provisioner import (
        InfrastructureProvisioningService, PostgresInfrastructureBindingRepository)
    from .providers.managed_web_saas import build_managed_web_saas_provisioner
    from .spec_repository import PostgresSpecRepository
    _run_live_build_job(
        build_id,
        jobs=jobs,
        platform=_v28,
        workspace=workspace,
        components_factory=components_factory,
        quality_fn=assess_repository,
        security_fn=hostile_repository_scan,
        min_quality=int(os.getenv('OMNI_MIN_QUALITY_SCORE', '80')),
        # M5 Task 9: when an image provider is configured, media.image.generate
        # (product icon / brand visual) is routed, executed, stored and verified;
        # otherwise the requirement stays explicitly NOT_CONFIGURED.
        capability_stage=build_image_capability_stage(
            env=os.environ, repository=PostgresCapabilityRepository(_v28_pool),
            artifact_store=getattr(workspace, 'storage', None),
            journal=PostgresSubmissionJournal(_v28_pool),
            worker_id=f'{socket.gethostname()}:{os.getpid()}',
        ),
        # M5 Task 6/7: contract-bound builds need their generated-app
        # infrastructure LIVE. Without OMNI_GENAPP_* configuration this is an
        # explicit NOT_CONFIGURED provisioner and the build fails closed.
        infrastructure_stage=InfrastructureProvisioningService(
            provisioner=build_managed_web_saas_provisioner(),
            repository=PostgresInfrastructureBindingRepository(_v28_pool),
        ),
        infrastructure_environment=os.getenv('OMNI_GENAPP_BUILD_ENVIRONMENT', 'preview'),
        # Checked after the job is claimed, so a misconfigured worker fails
        # the build (and releases its credits) instead of leaving it QUEUED
        # with credits reserved forever.
        preflight=lambda: ensure_durable_workspace(workspace, purpose='Durable async build'),
        spec_repo=PostgresSpecRepository(_v28_pool),
    )


# --------------------------------------------------------------------------
# M4: natural-language product modification (candidate build + gates)
# --------------------------------------------------------------------------
#
# Structurally this is `_run_live_build_job`'s M4 sibling: same claim
# (transition_running, conditional on QUEUED -> duplicate-delivery safe),
# same shape of exception handling (billing resolved from the real spend
# ledger, terminal status always written even on a worker crash), same
# evidence-dict convention. What's different: a modification's source is an
# *existing* ProjectVersion + its M4B-durable ProductSpec (never "the
# project's latest spec" -- see spec_repository.py's module docstring),
# gates run through CandidateModificationEngine (M4C/D/E) instead of
# evaluate_release_gates(), and the candidate this produces is deliberately
# NOT committed to project_versions here -- see modification_repository.py's
# complete()/accept() for why (the M4 concurrency requirement depends on it).

def resolve_modification_billing(subscriptions, *, modification_id: str, billable: bool,
                                 spent: Decimal, external_calls: int) -> str:
    """The classification-driven counterpart to resolve_billing(): whether a
    modification is free is a *product policy* decision already made by
    ChangeAssessment.billable (change_policy.py) -- system_bug/
    missing_requirement/ambiguous are free regardless of real spend incurred
    producing them, change_request settles for the real spend actually
    incurred, exactly as a build does. `subscriptions.reserve()` is called
    at request-creation time (investor_app.py) before classification is
    known, so it always reserves as billable; this is what turns that
    reservation into a real charge or a full refund once the real
    classification exists. Used only on the *normal* completion path, where
    a real ChangeAssessment exists -- the exception path (worker crashes
    before classification even runs) has no billable signal to key off and
    falls back to resolve_billing()'s spend-triggered rule instead."""
    if billable:
        subscriptions.settle(build_id=modification_id, actual_provider_cost_usd=spent)
        return 'settled'
    subscriptions.release(build_id=modification_id)
    return 'released'


_MODIFICATION_STATUS_MAP = {
    'needs_clarification': 'NEEDS_CLARIFICATION',
    'ready_for_review': 'READY_FOR_REVIEW',
    'failed': 'FAILED',
}


def _run_modification_job(modification_id: str, *, jobs, spec_repo, workspace, subscriptions,
                          components_factory, quality_fn, security_fn, rights_engine,
                          min_quality: int = 80, preflight=None) -> str | None:
    """Returns the terminal status written, or None if nothing was done
    (unknown modification id / already claimed by another delivery)."""
    try:
        request = jobs.get_request(modification_id)
    except KeyError:
        return None
    if not jobs.transition_running(modification_id):
        return None  # duplicate delivery / already handled: idempotent no-op

    project_id = request['project_id']
    source_version_id = request['source_version_id']
    gateway = None

    try:
        if preflight is not None:
            preflight()
        source_version = workspace.get(project_id=project_id, version_id=source_version_id)
        repository = source_version.repository()
        try:
            spec = spec_repo.get(source_version_id, project_id)
        except SpecNotFound as exc:
            # Real, expected failure mode (not a worker_exception): a version
            # committed before migration 016 / M4B has no stored spec, and
            # M4B's whole point is never guessing "the latest spec" instead.
            raise RuntimeError(
                f'version {source_version_id!r} has no stored ProductSpec (pre-M4B); '
                f'it cannot be modified through this pipeline: {exc}'
            ) from exc

        classifier, repairer, evolver, executor, gateway = components_factory()
        # Requirements-aware behavioural acceptance for the change too.
        from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
        acceptance_target = find_in_chain(executor, BehaviorAcceptanceExecutor)
        scope_pool = getattr(workspace, 'pool', None)
        if acceptance_target is not None and scope_pool is not None:
            acceptance_target.scope = contract_scope_for_version(scope_pool, project_id=project_id,
                                                                 version_id=source_version_id)
        engine = CandidateModificationEngine(
            classifier=classifier, repairer=repairer, executor=executor, evolver=evolver,
            quality_fn=quality_fn, security_fn=security_fn, rights_engine=rights_engine,
            min_quality=min_quality,
        )
        rights_evidence = _rights_evidence_from_dicts(request['rights_evidence'])
        outcome = engine.propose(
            spec=spec, repository=repository, followup=request['followup'],
            target_markets=request['target_markets'], rights_evidence=rights_evidence,
        )
        status = _MODIFICATION_STATUS_MAP.get(outcome.status)
        if status is None:
            # CandidateModificationEngine.propose() never actually returns
            # 'change_request_not_supported' (see its docstring); this is a
            # contract-violation guard, not a real code path.
            raise RuntimeError(f'unexpected CandidateModificationEngine outcome status: {outcome.status!r}')
    except Exception as exc:
        spent, calls = spend_snapshot(gateway)
        billing = resolve_billing(subscriptions, build_id=modification_id, ready=False, spent=spent, external_calls=calls)
        jobs.complete(
            modification_id, project_id=project_id, status='FAILED',
            error_code=failure_code(exc), error_message=f'{type(exc).__name__}: {exc}'[:2000],
            evidence_json={'billing': billing, 'provider_spend_usd': str(spent),
                           'provider_usage': provider_usage_evidence(gateway),
                           'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS},
        )
        raise

    spent, calls = spend_snapshot(gateway)
    evidence = outcome.to_evidence_dict()
    evidence['provider_usage'] = provider_usage_evidence(gateway)
    evidence['billing'] = resolve_modification_billing(
        subscriptions, modification_id=modification_id, billable=outcome.billable, spent=spent, external_calls=calls)
    evidence['provider_spend_usd'] = str(spent)
    evidence['external_model_calls'] = calls
    evidence['provider_spend_basis'] = SPEND_BASIS

    error_code = error_message = None
    if status == 'FAILED' and outcome.gates is not None:
        error_code, error_message = outcome.gates.blocking_gate, outcome.gates.detail
    elif status == 'FAILED':
        error_code, error_message = 'verification_failed', 'candidate did not pass sandbox verification'

    jobs.complete(
        modification_id, project_id=project_id, status=status,
        classification=outcome.assessment.category, classification_reason=outcome.assessment.reason,
        billable=outcome.billable,
        candidate_repository=outcome.candidate_repository if status == 'READY_FOR_REVIEW' else None,
        candidate_spec=outcome.candidate_spec if status == 'READY_FOR_REVIEW' else None,
        repair_rounds=outcome.repair_rounds, evidence_json=evidence,
        error_code=error_code, error_message=error_message,
    )
    return status


def execute_modification_job(modification_id: str) -> None:
    from .investor_app import _v28, _v28_pool, _modification_components
    from .modification_repository import PostgresModificationRepository
    from .preview_runtime import ensure_durable_workspace
    from .quality_gate import assess_repository
    from .security_testing import hostile_repository_scan
    from .spec_repository import PostgresSpecRepository

    if _v28_pool is None:
        raise RuntimeError(
            "execute_modification_job requires OMNI_CREATOR_PERSISTENCE=postgres "
            "in the worker process (this process was not started with it)."
        )
    workspace = _v28.engine.workspace
    _run_modification_job(
        modification_id,
        jobs=PostgresModificationRepository(_v28_pool),
        spec_repo=PostgresSpecRepository(_v28_pool),
        workspace=workspace,
        subscriptions=_v28.subscriptions,
        components_factory=_modification_components,
        quality_fn=assess_repository,
        security_fn=hostile_repository_scan,
        rights_engine=_v28.rights,
        min_quality=int(os.getenv('OMNI_MIN_QUALITY_SCORE', '80')),
        preflight=lambda: ensure_durable_workspace(workspace, purpose='Natural-language product modification'),
    )


# --------------------------------------------------------------------------
# M3: real running preview
# --------------------------------------------------------------------------

def preview_runtime_host() -> str:
    """Identity of this worker for host-scoped cleanup routing and for the
    external router's upstream address. Set OMNI_PREVIEW_RUNTIME_HOST to a
    name/IP the router can reach when it is not on this host."""
    return os.getenv('OMNI_PREVIEW_RUNTIME_HOST', '').strip() or socket.gethostname()


def preview_probe_host(bind_address: str) -> str:
    explicit = os.getenv('OMNI_PREVIEW_PROBE_HOST', '').strip()
    if explicit:
        return explicit
    return '127.0.0.1' if bind_address in {'0.0.0.0', '', '::'} else bind_address


def _teardown(provider, repo, preview_id: str, started) -> list[str]:
    """Best-effort removal of a container + its source dir. Returns errors
    instead of raising so the caller can still record the real outcome."""
    errors = []
    try:
        provider.stop(started.container_id)
    except Exception as exc:
        errors.append(f'docker rm: {exc}')
    try:
        provider.remove_workdir(started.workdir)
    except Exception as exc:
        errors.append(f'workdir: {exc}')
    if not errors:
        try:
            repo.mark_cleaned(preview_id)
        except Exception as exc:
            errors.append(f'mark_cleaned: {exc}')
    return errors


def _run_preview_launch(preview_id: str, project_id: str, version_id: str, *, repo, provider,
                        runtime_host: str, url_template: str | None, probe_host: str,
                        probe_timeout: float = 30.0, probe_interval: float = 1.0,
                        http_get=None, sleep=time.sleep, clock=time.monotonic,
                        preflight=None, acceptance_runner=None, acceptance_contract=None,
                        acceptance_personas=None) -> str:
    """Returns the final status this task observed/wrote. RUNNING is written
    in exactly one place -- after wait_until_healthy() succeeds -- and only
    if the preview is still STARTING (not stopped by the user meanwhile)."""
    from .preview_runtime import (HealthResult, NotPreviewable, PreviewBackendUnavailable,
                                  external_preview_url, wait_until_healthy)

    # Validate everything that doesn't need a container before starting one.
    try:
        if preflight is not None:
            preflight()
        url = external_preview_url(preview_id, url_template)
    except PreviewBackendUnavailable as exc:
        repo.mark_failed(preview_id, error=f'preview backend not configured: {exc}')
        return 'FAILED'

    try:
        started = provider.start(preview_id=preview_id, project_id=project_id, version_id=version_id)
    except NotPreviewable as exc:
        repo.mark_failed(preview_id, error=str(exc), status='NOT_PREVIEWABLE')
        return 'NOT_PREVIEWABLE'
    except Exception as exc:
        repo.mark_failed(preview_id, error=f'container start failed: {exc}')
        raise

    try:
        if not repo.record_runtime(preview_id, container_id=started.container_id, runtime_host=runtime_host,
                                   host_port=started.host_port, workdir=started.workdir,
                                   data_storage='persistent' if getattr(started, 'data_dir', None) else 'temporary'):
            _teardown(provider, repo, preview_id, started)  # stopped while starting
            return 'STOPPED'

        if started.host_port is None:
            # Crashed before Docker published its port (see
            # DockerPreviewProvider.start). Nothing to probe; report why.
            _, exit_code = provider.is_running(started.container_id)
            health = HealthResult(False, f'container exited before its port was published (exit code {exit_code})', 0)
        else:
            probe_url = f'http://{probe_host}:{started.host_port}{started.contract.health_path}'
            health = wait_until_healthy(
                url=probe_url, is_alive=lambda: provider.is_running(started.container_id),
                timeout_seconds=probe_timeout, interval_seconds=probe_interval,
                http_get=http_get, sleep=sleep, clock=clock,
            )
        if not health.ok:
            try:
                tail = provider.logs(started.container_id, tail=50)
            except Exception as exc:
                tail = f'(logs unavailable: {exc})'
            errors = _teardown(provider, repo, preview_id, started)
            message = f'health probe failed after {health.attempts} attempt(s): {health.detail}'
            if errors:
                message += f'\ncleanup errors: {"; ".join(errors)}'
            message += f'\n--- container logs (tail) ---\n{tail[-2500:]}'
            repo.mark_failed(preview_id, error=message)
            return 'FAILED'

        if not repo.mark_running(preview_id, url=url):
            _teardown(provider, repo, preview_id, started)  # stopped during the probe
            return 'STOPPED'

        # M5 Task 11: process health and release readiness are deliberately
        # separate. A RUNNING preview may remain inspectable even when
        # behavioral acceptance fails; only a PASS report is release-eligible.
        if acceptance_runner is not None:
            from dataclasses import replace
            from .web_saas_acceptance import AcceptanceReport

            def _error_report(summary):
                return AcceptanceReport(
                    status='ERROR', release_eligible=False, summary=summary, checks=(),
                    covered_acceptance_ids=(), missing_acceptance_ids=(),
                    covered_kinds=(), missing_kinds=(), runtime_logs=None,
                )

            # Directive 2026-10-09 §13: when the product's data is persistent,
            # the synthetic acceptance records must not land in it. The probes
            # run against a scratch copy of the same version (no data mount),
            # reached directly on the preview host, which is removed afterwards.
            target, target_url, scratch, report = started, url, None, None
            if getattr(provider, 'persistent_data', False):
                try:
                    sweep = getattr(provider, 'sweep_scratch', None)
                    if callable(sweep):
                        sweep()
                    scratch = provider.start(preview_id=f'{preview_id}-qa', project_id=project_id,
                                             version_id=version_id, persistent=False)
                    if scratch.host_port is None:
                        raise RuntimeError('the acceptance copy exited before its port was published')
                    scratch_health = wait_until_healthy(
                        url=f'http://{probe_host}:{scratch.host_port}{scratch.contract.health_path}',
                        is_alive=lambda: provider.is_running(scratch.container_id),
                        timeout_seconds=probe_timeout, interval_seconds=probe_interval,
                        http_get=http_get, sleep=sleep, clock=clock,
                    )
                    if not scratch_health.ok:
                        raise RuntimeError(f'the acceptance copy did not become healthy: {scratch_health.detail}')
                    target, target_url = scratch, f'http://{probe_host}:{scratch.host_port}'
                except Exception as exc:
                    report = _error_report(f'acceptance copy could not start: {type(exc).__name__}: {exc}'[:500])
            try:
                if report is None:
                    try:
                        report = acceptance_runner.verify(
                            {'id': preview_id, 'project_id': project_id, 'version_id': version_id,
                             'status': 'RUNNING', 'preview_url': target_url},
                            acceptance_contract, acceptance_personas or (),
                        )
                    except Exception as exc:
                        report = _error_report(f'acceptance runner error: {type(exc).__name__}: {exc}')

                    try:
                        alive, exit_code = provider.is_running(target.container_id)
                    except Exception:
                        alive, exit_code = True, None  # do not invent a crash if Docker status is unavailable
                    if not alive:
                        try:
                            tail = provider.logs(target.container_id, tail=100)
                        except Exception as exc:
                            tail = f'(logs unavailable: {exc})'
                        report = replace(
                            report, status='FAIL', release_eligible=False,
                            summary=report.summary + f'; preview crashed during acceptance (exit code {exit_code})',
                        ).with_runtime_logs(tail)
                        try:
                            repo.record_acceptance(preview_id, project_id, version_id, report)
                        finally:
                            crash_message = (f'preview crashed during behavioral acceptance (exit code {exit_code})'
                                             f'\n--- container logs (tail) ---\n{tail[-2500:]}')
                            repo.mark_crashed(preview_id, crash_message)
                            _teardown(provider, repo, preview_id, started)
                        return 'FAILED'

                # Persist after checking liveness so a PASS can never be recorded
                # for a process that died while the behavioral probes were running.
                repo.record_acceptance(preview_id, project_id, version_id, report)
            finally:
                if scratch is not None:
                    for step in (lambda: provider.stop(scratch.container_id),
                                 lambda: provider.remove_workdir(scratch.workdir)):
                        try:
                            step()
                        except Exception:
                            logging.getLogger(__name__).warning('acceptance copy cleanup failed for %s', preview_id,
                                                                exc_info=True)
        return 'RUNNING'
    except Exception as exc:
        errors = _teardown(provider, repo, preview_id, started)
        repo.mark_failed(preview_id, error=f'preview launch aborted: {exc}'
                         + (f'; cleanup errors: {"; ".join(errors)}' if errors else ''))
        raise


# The build contract that produced a version (directly, or through a chain of
# promoted modifications) decides the demand-driven acceptance scope. Read from
# the immutable contract, never from generated files.
_CONTRACT_SCOPE_FOR_VERSION_SQL = """
WITH RECURSIVE lineage(version_id, depth) AS (
    SELECT %s::text, 0
    UNION ALL
    SELECT m.source_version_id, l.depth + 1
    FROM modification_requests m
    JOIN lineage l ON m.promoted_version_id = l.version_id
    WHERE l.depth < 64
)
SELECT c.contract_json->'infrastructure', c.contract_json->'required_integrations',
       c.contract_json->'user_roles', c.contract_json->'defaults_applied', c.contract_json->>'prompt'
FROM lineage l
JOIN build_jobs j ON j.result_version_id = l.version_id
JOIN build_requests r ON r.build_id = j.id
JOIN m5_build_contracts c ON c.id = r.build_contract_id
WHERE r.public_project_id = %s OR r.internal_project_id = %s
ORDER BY l.depth
LIMIT 1
"""


def contract_scope_for_version(pool, *, project_id: str, version_id: str) -> dict | None:
    """Infrastructure and integrations of the contract behind a version, or
    None (the strict full acceptance floor applies). A lookup failure never
    weakens acceptance."""
    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(_CONTRACT_SCOPE_FOR_VERSION_SQL, (version_id, project_id, project_id))
                row = cur.fetchone()
        if not row or row[0] is None:
            return None
        def _j(value):
            return json.loads(value) if isinstance(value, str) else value
        infrastructure, integrations = _j(row[0]), _j(row[1])
        scope = {'infrastructure': infrastructure or [], 'required_integrations': integrations or []}
        if len(row) > 4 and row[4] is not None:
            # Requirements-aware acceptance: the approved roles and text.
            scope.update(user_roles=_j(row[2]) or [], defaults=_j(row[3]) or [], prompt=row[4])
        return scope
    except Exception:
        logging.getLogger(__name__).exception('contract scope lookup failed; strict acceptance floor applies')
        return None


def execute_preview_launch(preview_id: str, project_id: str, version_id: str) -> None:
    from .investor_app import _v28, _v28_pool
    from .preview_repository import PostgresPreviewRepository
    from .preview_runtime import (DockerPreviewProvider, NotPreviewable, ensure_durable_workspace,
                                  parse_web_saas_acceptance_plan)
    from .spec_repository import PostgresSpecRepository, SpecNotFound
    from .web_saas_acceptance import WebSaaSAcceptanceRunner

    if _v28_pool is None:
        raise RuntimeError(
            "execute_preview_launch requires OMNI_CREATOR_PERSISTENCE=postgres "
            "in the worker process."
        )
    workspace = _v28.engine.workspace
    provider = DockerPreviewProvider(workspace=workspace)

    acceptance_runner = acceptance_contract = acceptance_personas = None
    try:
        version = workspace.get(project_id=project_id, version_id=version_id)
        plan = parse_web_saas_acceptance_plan(version.repository())
        if plan is not None:
            acceptance_contract = PostgresSpecRepository(_v28_pool).get(version_id, project_id)
            acceptance_personas = plan.personas
            acceptance_runner = WebSaaSAcceptanceRunner(
                required_kinds=plan.required_kinds,
                build_contract=contract_scope_for_version(_v28_pool, project_id=project_id, version_id=version_id))
    except NotPreviewable as exc:
        PostgresPreviewRepository(_v28_pool).mark_failed(
            preview_id, error=f'invalid behavioral acceptance plan: {exc}', status='NOT_PREVIEWABLE'
        )
        return
    except (KeyError, SpecNotFound):
        # Legacy/non-M4B versions can still be previewed, but cannot produce a
        # false M5 acceptance PASS because no runner is configured.
        acceptance_runner = acceptance_contract = acceptance_personas = None

    _run_preview_launch(
        preview_id, project_id, version_id,
        repo=PostgresPreviewRepository(_v28_pool),
        provider=provider,
        runtime_host=preview_runtime_host(),
        url_template=os.getenv('PREVIEW_DOMAIN_TEMPLATE'),
        probe_host=preview_probe_host(provider.bind_address),
        probe_timeout=float(os.getenv('OMNI_PREVIEW_HEALTH_TIMEOUT_SECONDS', '30')),
        preflight=lambda: ensure_durable_workspace(workspace),
        acceptance_runner=acceptance_runner, acceptance_contract=acceptance_contract,
        acceptance_personas=acceptance_personas,
    )


def _run_preview_stop(preview_id: str, *, repo, provider, this_host: str) -> dict:
    info = repo.get_runtime(preview_id)
    if info is None:
        return {'cleaned': False, 'reason': 'unknown preview'}
    if info['status'] not in ('STOPPED', 'EXPIRED'):
        # Never tear down a STARTING/RUNNING preview from a (stale or
        # duplicate) cleanup job -- only the API's stop transition licenses it.
        return {'cleaned': False, 'reason': f'status is {info["status"]}'}
    if info.get('cleaned_at'):
        return {'cleaned': True, 'reason': 'already cleaned'}
    if info.get('runtime_host') and info['runtime_host'] != this_host:
        # Wrong Docker daemon / wrong filesystem. Surfacing this as a job
        # failure beats "cleaning" nothing and marking it clean.
        raise RuntimeError(f'preview {preview_id} runs on {info["runtime_host"]}, this worker is {this_host}; '
                           'the stop task must be consumed from that host\'s queue')
    if info.get('container_id'):
        provider.stop(info['container_id'])  # idempotent; raises on real docker failure
    if info.get('workdir'):
        provider.remove_workdir(info['workdir'])
    repo.mark_cleaned(preview_id)
    return {'cleaned': True, 'reason': 'container and workdir removed'}


def stop_preview_task(preview_id: str) -> None:
    from .investor_app import _v28, _v28_pool
    from .preview_repository import PostgresPreviewRepository
    from .preview_runtime import DockerPreviewProvider

    if _v28_pool is None:
        raise RuntimeError("stop_preview_task requires OMNI_CREATOR_PERSISTENCE=postgres in the worker process.")
    _run_preview_stop(
        preview_id,
        repo=PostgresPreviewRepository(_v28_pool),
        provider=DockerPreviewProvider(workspace=_v28.engine.workspace),
        this_host=preview_runtime_host(),
    )

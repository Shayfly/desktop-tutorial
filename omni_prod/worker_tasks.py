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

import os
import socket
import time
from decimal import Decimal

from .models import BuildStatus
from .build_contract import BuildContract, BuildContractStatus
from .capability_worker import CapabilityStageBlocked
from .infrastructure_provisioner import InfrastructureStageBlocked
from .modification_engine import CandidateModificationEngine
from .provider_usage import ProviderUsageLedger
from .spec_repository import SpecNotFound

# Order matters: the first failing gate is the one reported as error_code.
GATE_ORDER = ('verification', 'quality', 'security', 'rights')

SPEND_BASIS = ('authorized external-model spend ledger (RoutedModelGateway.state.external_spend_usd); '
               'an authorization estimate, not a cost -- provider-reported usage is in provider_usage')


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
    actual = None if llm_actual is None or capability_actual is None else llm_actual + capability_actual
    quote = dict(economics_quote or {})
    revenue_raw = quote.get('revenue_usd')
    infra_max = Decimal(str(quote.get('infrastructure_maximum_usd', '0') or '0'))
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
                        infrastructure_environment: str = 'preview') -> str | None:
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

    try:
        if preflight is not None:
            preflight()
        # M5 Task 6: a contract-bound product cannot become READY without its
        # required generated-app infrastructure. Checked before any paid model
        # generation so a missing binding never burns provider budget.
        if infrastructure_stage is not None and build_contract is not None:
            infrastructure_evidence = infrastructure_stage.require_ready(
                build_contract, tenant_id=str(request['user_id']),
                project_id=build_contract.project_id, environment=infrastructure_environment,
            )
        brain = platform.brain.decide(prompt, target_markets=markets)
        capability_plan = build_contract.capability_plan if build_contract is not None else getattr(brain, 'capabilities', None)
        if capability_stage is not None:
            if capability_plan is None:
                raise RuntimeError('capability stage requires a bound or planned capability plan')
            capability_evidence = capability_stage.prepare(
                build_id=build_id, project_id=internal_project_id, plan=capability_plan,
                authorized_maximum_usd=Decimal(str(request.get('authorized_provider_cost_usd', '0.25'))),
                now=time.time(),
            )
        rights = platform.rights.assess(
            prompt, target_markets=markets,
            evidence=_rights_evidence_from_dicts(request.get('rights_evidence')),
            synthetic_person_media=bool(brain.rights.required_disclosures),
        )
        engine, gateway = components_factory()
        result = engine.build(prompt)
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
        version = workspace.commit(project_id=internal_project_id, repository=repo,
                                   message=f'148AI async live build {build_id}')
        version_id = version.id
        artifact_key = getattr(version, 'artifact_key', None)

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
            'build_log_tail': result.report.build_log[-4000:],
            'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
            'provider_usage': provider_usage_evidence(gateway),
            'provider_spend_usd': str(spent), 'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
        }
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
            error_code='worker_exception', error_message=f'{type(exc).__name__}: {exc}'[:2000],
            result_version_id=version_id, artifact_key=artifact_key,
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence,
                           'provider_usage': provider_usage_evidence(gateway),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])],
                           'provider_spend_usd': str(spent),
                           'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS},
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
    _run_live_build_job(
        build_id,
        jobs=PostgresBuildRepository(_v28_pool),
        platform=_v28,
        workspace=workspace,
        components_factory=_live_components,
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
            error_code='worker_exception', error_message=f'{type(exc).__name__}: {exc}'[:2000],
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
                                   host_port=started.host_port, workdir=started.workdir):
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
            try:
                report = acceptance_runner.verify(
                    {'id': preview_id, 'project_id': project_id, 'version_id': version_id,
                     'status': 'RUNNING', 'preview_url': url},
                    acceptance_contract, acceptance_personas or (),
                )
            except Exception as exc:
                report = AcceptanceReport(
                    status='ERROR', release_eligible=False,
                    summary=f'acceptance runner error: {type(exc).__name__}: {exc}', checks=(),
                    covered_acceptance_ids=(), missing_acceptance_ids=(),
                    covered_kinds=(), missing_kinds=(), runtime_logs=None,
                )

            try:
                alive, exit_code = provider.is_running(started.container_id)
            except Exception:
                alive, exit_code = True, None  # do not invent a crash if Docker status is unavailable
            if not alive:
                try:
                    tail = provider.logs(started.container_id, tail=100)
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
        return 'RUNNING'
    except Exception as exc:
        errors = _teardown(provider, repo, preview_id, started)
        repo.mark_failed(preview_id, error=f'preview launch aborted: {exc}'
                         + (f'; cleanup errors: {"; ".join(errors)}' if errors else ''))
        raise


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
            acceptance_runner = WebSaaSAcceptanceRunner(required_kinds=plan.required_kinds)
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

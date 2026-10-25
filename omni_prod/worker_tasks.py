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
from .build_control import BuildCancelled, BuildControl, ControlledExecutor, install as install_build_control


def set_acceptance_scope(engine, contract: dict | None) -> None:
    """Requirements-aware acceptance: hand the approved contract's scope to the
    in-build behavioural acceptance (no contract -> strict floor)."""
    from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    target = find_in_chain(getattr(engine, 'executor', None), BehaviorAcceptanceExecutor)
    if target is None or not contract:
        return
    target.scope = {k: contract.get(k) for k in ('infrastructure', 'required_integrations', 'user_roles',
                                                  'defaults_applied', 'prompt')}


APPROVED_PREFIX = 'APPROVED-'


def merge_approved_criteria(spec, criteria: list[dict]):
    """ADWv1 G3: the customer-approved acceptance criteria (intake-requirements/1,
    bound to the build with its plan) become acceptance criteria of the build's
    spec under platform-owned ids (APPROVED-AC1 ...). The behavioural acceptance
    runner already requires a passing HTTP step for every spec acceptance id,
    so each approved criterion must be exercised; the model may enrich the spec
    but cannot drop these. Deterministic, no model call."""
    from .product_spec import ProductSpec
    d = spec.to_dict()
    req_ids = {r['id'] for r in d['requirements']}
    acc_ids = {a['id'] for a in d['acceptance']}
    for a in criteria or []:
        aid, text = str(a.get('id') or '').strip(), str(a.get('given_when_then') or '').strip()
        if not aid or not text:
            raise ValueError(f'approved acceptance criterion without id/text: {a!r}')
        rid = APPROVED_PREFIX + (str(a.get('covers') or '').strip() or aid)
        if rid not in req_ids:
            d['requirements'].append({'id': rid, 'text': f'Customer-approved requirement: {text}'[:2000],
                                      'kind': 'functional', 'mandatory': True})
            req_ids.add(rid)
        if APPROVED_PREFIX + aid not in acc_ids:
            d['acceptance'].append({'id': APPROVED_PREFIX + aid, 'requirement_id': rid, 'text': text[:2000]})
            acc_ids.add(APPROVED_PREFIX + aid)
    return ProductSpec.from_dict(d)


class ApprovedCriteriaArchitect:
    """Wraps the engine's architect: every spec it returns carries the approved criteria."""

    def __init__(self, inner, criteria: list[dict]):
        self._inner = inner
        self.criteria = list(criteria)
        self.approved_ids = [APPROVED_PREFIX + str(a.get('id')) for a in self.criteria]

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def create_spec(self, prompt, *args, **kwargs):
        return merge_approved_criteria(self._inner.create_spec(prompt, *args, **kwargs), self.criteria)


def install_approved_criteria(engine, plan_binding: dict | None) -> bool:
    """Plan-governed builds (OMNI_PLAN_DRIVEN=1) only: bind the approved criteria
    of the build's plan to its spec. Returns whether they were installed."""
    criteria = (plan_binding or {}).get('acceptance_criteria')
    if not criteria or getattr(engine, 'architect', None) is None:
        return False
    if not isinstance(engine.architect, ApprovedCriteriaArchitect):
        engine.architect = ApprovedCriteriaArchitect(engine.architect, criteria)
    return True


def approved_criteria_evidence(engine) -> dict | None:
    arch = getattr(engine, 'architect', None)
    if not isinstance(arch, ApprovedCriteriaArchitect):
        return None
    return {'ids': list(arch.approved_ids), 'criteria': list(arch.criteria)}


def behavior_evidence(engine) -> dict | None:
    from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
    target = find_in_chain(getattr(engine, 'executor', None), BehaviorAcceptanceExecutor)
    if target is None:
        return None
    return {'last': target.last_report, 'rounds': list(target.history)}


def install_round_snapshots(engine, workspace, build_id: str, sink: list, control=None) -> None:
    """Directive 2026-10-10 P0.3: store every verified candidate durably
    (object storage, checksum-verified on read) before the next repair, with
    its verification progress and what the loop decided. The loop rolls back
    to the best one; these keys make each round inspectable and restorable."""
    store = getattr(workspace, 'storage', None)
    zip_repo = getattr(workspace, '_zip_repo', None)
    if not hasattr(engine, 'round_hook'):
        return

    def hook(index, repo, report, decision, progress):
        from .workspace import _checksum
        entry = {'round': index, 'decision': decision, 'progress': list(progress), 'sha256': _checksum(repo),
                 'failing': sorted({getattr(f, 'acceptance_id', '?') for f in getattr(report, 'failures', ()) or ()})}
        if store is not None and zip_repo is not None:
            key = f'build-rounds/{build_id}/{index:02d}-{entry["sha256"][:12]}.zip'
            store.put_bytes(key, zip_repo(repo))
            entry['key'] = key
        sink.append(entry)
        if control is not None and decision == 'discarded':
            control.log('info', f'סבב תיקון {index} החמיר את המוצר ונזרק; ממשיכים מהגרסה הטובה ביותר.')
    engine.round_hook = hook


def install_rejected_json_sink(gateway, workspace, build_id: str) -> None:
    """T3 / Matt on #105: every model answer rejected as JSON is written to object storage at the moment it is
    rejected (the FULL raw text and its diagnosis), under build-model-json/<build>/; the build evidence carries the
    manifest (rejected_json_evidence). Without storage nothing is installed and the manifest says so."""
    store = getattr(workspace, 'storage', None)
    if gateway is None or store is None or not callable(getattr(store, 'put_bytes', None)):
        return
    import hashlib
    counter = {'n': 0}

    from .evidence_export import redact as export_redact      # covers Google keys (AIza...) on this base
    from .secret_redaction import redact as layer_redact

    def redact(text: str) -> str:
        return export_redact(layer_redact(text))

    def sink(entry: dict, raw: str) -> str:
        # Private build store (same access and retention as the round snapshots). The text is stored WHOLE (never
        # truncated), through the redaction layer: raw_sha256 is the digest of the original answer, and
        # stored_redacted says whether anything key-shaped was replaced.
        # Matt HOLD on #105 (T3_DIAGNOSTIC_REDACTION_BYPASS): EVERY text-bearing field of the stored object goes
        # through the same layer, not only the raw answer -- diagnostic.starts / trailing_starts are excerpts of it.
        text = redact(raw)
        plain = {k: v for k, v in entry.items() if k not in ('raw', 'raw_truncated')}
        meta = {**plain, **{k: redact_fields(plain[k]) for k in _REJECTED_TEXT_FIELDS if k in plain}}
        body = json.dumps({**meta, 'build_id': build_id,
                           'stored_text': text, 'stored_redacted': text != raw or meta != plain,
                           'stored_truncated': False},
                          ensure_ascii=False).encode()
        key = (f"build-model-json/{build_id}/{counter['n']:02d}-{entry['task']}-"
               f"{hashlib.sha256(body).hexdigest()[:12]}.json")
        counter['n'] += 1
        store.put_bytes(key, body)
        return key
    gateway.rejected_json_sink = sink


# Text-bearing fields of a rejection entry: excerpts of the model's answer (diagnostic.starts / trailing_starts /
# reason) and exception text (store_error). Identifiers (key, raw_sha256, model ids) are not text and are kept exact.
_REJECTED_TEXT_FIELDS = ('diagnostic', 'store_error')


def redact_fields(value):
    """The rejected-JSON redaction layer applied to every string inside a JSON-shaped value (keys kept)."""
    from .evidence_export import redact as export_redact
    from .secret_redaction import redact as layer_redact
    if isinstance(value, str):
        return export_redact(layer_redact(value))
    if isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            if k == 'tail_raw_utf8_b64' and isinstance(v, str):
                # Redact the decoded text, then re-encode. Applying the generic
                # long-token filter to Base64 destroys the retained evidence.
                import base64
                decoded = base64.b64decode(v, validate=True).decode('utf-8')
                cleaned[k] = base64.b64encode(redact_fields(decoded).encode('utf-8')).decode('ascii')
            else:
                cleaned[k] = redact_fields(v)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [redact_fields(v) for v in value]
    return value


def rejected_json_evidence(gateway) -> dict:
    """Manifest of the rejected JSON answers of THIS build (the raw text lives at each key).

    Matt HOLD on #105 (T3_DURABLE_FLAG_FALSE_SUCCESS): durability is what the writes ACHIEVED, not whether a sink is
    installed. `rejected_model_json_durable` is True only when there were rejections and every one was stored;
    None when nothing was rejected (nothing to make durable -- not a pass); False otherwise. The state names the
    case: NO_REJECTIONS | ALL_STORED | PARTIAL | NONE_STORED | NO_STORE."""
    rows = list(getattr(gateway, 'rejected_json_manifest', None) or [])
    installed = getattr(gateway, 'rejected_json_sink', None) is not None
    stored = sum(1 for r in rows if r.get('key') and not r.get('store_error'))
    if not rows:
        state, durable = 'NO_REJECTIONS', None
    elif not installed:
        state, durable = 'NO_STORE', False
    elif stored == len(rows):
        state, durable = 'ALL_STORED', True
    elif stored == 0:
        state, durable = 'NONE_STORED', False
    else:
        state, durable = 'PARTIAL', False
    return {'rejected_model_json': [{k: r.get(k) for k in ('model', 'provider_model', 'attempt_seq', 'task',
                                                           'raw_sha256', 'raw_chars', 'key')}
                                    | {'store_error': redact_fields(r.get('store_error')),
                                       'reason': redact_fields((r.get('diagnostic') or {}).get('reason'))} for r in rows],
            'rejected_model_json_durable': durable,
            'rejected_model_json_durability': {'state': state, 'rejected': len(rows), 'stored': stored,
                                               'failed': len(rows) - stored}}


def visual_evidence(engine) -> dict | None:
    from .behavior_acceptance import find_in_chain
    from .visual_qa import VisualQAExecutor
    target = find_in_chain(getattr(engine, 'executor', None), VisualQAExecutor)
    return None if target is None else target.last_visual


def install_visual_sink(engine, workspace, build_id: str) -> None:
    """Screenshots of each viewport go to object storage (never to a third party)."""
    from .behavior_acceptance import find_in_chain
    from .visual_qa import VisualQAExecutor
    target = find_in_chain(getattr(engine, 'executor', None), VisualQAExecutor)
    store = getattr(workspace, 'storage', None)
    if target is None or store is None:
        return
    import hashlib

    def sink(viewport: str, jpeg: bytes) -> str:
        key = f'build-visual/{build_id}/{viewport}-{hashlib.sha256(jpeg).hexdigest()[:12]}.jpg'
        store.put_bytes(key, jpeg)
        return key
    target.screenshot_sink = sink


def preview_smoke_evidence(engine) -> dict | None:
    from .behavior_acceptance import find_in_chain
    from .preview_smoke import PreviewReadyExecutor
    target = find_in_chain(getattr(engine, 'executor', None), PreviewReadyExecutor)
    return None if target is None else target.last_smoke


def author_models(gateway) -> set[str]:
    """Endpoint names and model ids that wrote or repaired code in this build."""
    names = set()
    for task in ('architecture', 'codegen', 'repair', 'modification'):
        names |= set((getattr(gateway, 'models_by_task', None) or {}).get(task, set()))
    for m in getattr(gateway, 'ranked', ()) or ():
        endpoint = getattr(m, 'endpoint', None)
        if endpoint is not None and endpoint.name in names:
            names.add(endpoint.model)
    return names


def persist_quality_report(pool, report, tenant_key) -> None:
    """Durable stage evidence (migration 035); best effort -- the decision is
    already made and also stored in the build's evidence."""
    if pool is None or report is None:
        return
    try:
        from .release_policy import persist
        persist(pool, report, tenant_key=tenant_key)
    except Exception:
        logging.getLogger(__name__).exception('stage evidence write failed for %s', report.build_id)


def release_quality_report(build_id, engine, gateway, result, quality, security, rights):
    """QualityReport of this build (None if it cannot be built: the policy then
    cannot have been evaluated and the build is not READY by policy)."""
    from .release_policy import build_report
    from .workspace import _checksum
    try:
        executor = getattr(engine, 'executor', None)
        evidence = {
            'consistency_gate': consistency_evidence(engine),
            'preview_smoke': preview_smoke_evidence(engine),
            'behavior_acceptance': behavior_evidence(engine),
            'browser_check': getattr(executor, 'last_probe', None),
            'product_review': list(getattr(executor, 'reviews', None) or []),
            'visual_qa': visual_evidence(engine),
            'approved_acceptance': approved_criteria_evidence(engine),
        }
        return build_report(build_id=build_id, artifact_sha256=_checksum(result.repository), result=result,
                            evidence=evidence, quality=quality, security=security, rights=rights,
                            author_models=author_models(gateway))
    except Exception:
        logging.getLogger(__name__).exception('release policy report failed for %s', build_id)
        return None


def consistency_evidence(engine) -> dict | None:
    from .behavior_acceptance import find_in_chain
    from .consistency_gate import ConsistencyGateExecutor
    target = find_in_chain(getattr(engine, 'executor', None), ConsistencyGateExecutor)
    if target is None or not target.enabled:
        return None
    return {'last': target.last_consistency, 'rounds': list(target.consistency_rounds)}
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
    from .model_gateway import ModelGatewayError, ProviderQuotaUnavailable
    from .model_policy import ModelPolicyViolation
    from .agent_os.recorder import PlanViolation
    from .attempt_ledger import AttemptLedgerUnavailable
    text = str(exc)
    if isinstance(exc, AttemptLedgerUnavailable):
        return 'attempt_ledger_unavailable'
    if isinstance(exc, PlanViolation):
        return 'plan_violation'
    if isinstance(exc, ProviderQuotaUnavailable):
        return 'provider_quota_exhausted'
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
    out = {'binding': 'bound', **gateway.bind_budget(Decimal(str(components['llm_maximum_usd'])))}
    # CEO 2026-10-19: the plan's cost class also limits WHICH models may run.
    if components.get('cost_class') and hasattr(gateway, 'restrict_to_cost_class'):
        out['model_allowlist'] = gateway.restrict_to_cost_class(components['cost_class'])
    return out


def llm_cap_overage(request: dict, spent) -> dict | None:
    """Soft class cap (CEO 2026-10-19): record how actual model spend compares
    with the class cap; above 2x the cap it is logged as an alert. Never refuses."""
    components = (request.get('economics_quote') or {}).get('components') or {}
    cap = components.get('llm_class_cap_usd')
    if cap in (None, 'None'):
        return None
    from .pricing import llm_overage
    result = llm_overage(spent, cap)
    if result['status'] == 'OVER_2X_CAP':
        logging.getLogger(__name__).warning('LLM_SPEND_ALERT build class=%s spent=%s cap=%s (>2x)',
                                            components.get('cost_class'), result['actual_usd'], result['cap_usd'])
    elif result['status'] == 'OVER_CAP':
        logging.getLogger(__name__).info('llm spend over class cap: class=%s spent=%s cap=%s',
                                         components.get('cost_class'), result['actual_usd'], result['cap_usd'])
    return result


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


def metered_llm_cost(gateway, external_calls: int) -> tuple[Decimal | None, dict]:
    """Exact model cost from usage: each external call's metered cost
    (provider-reported tokens x the catalog price of that model, recorded with
    the catalog version) or 0 for a call the provider refused. If any
    authorized external call has no metered cost (timeout without usage, model
    without a catalog price) the cost is UNKNOWN and None is returned: unknown
    pricing never silently becomes zero, and settlement keeps the explicit
    conservative policy (the reservation)."""
    records = [r for r in (getattr(getattr(gateway, 'recorder', None), 'records', None) or [])
               if getattr(r, 'kind', None) == 'provider_call' and (getattr(r, 'authorized_cost_usd', None) or 0) > 0]
    versions = sorted({r.price_catalog_version for r in records if getattr(r, 'price_catalog_version', None)})
    basis = {'llm': 'METERED_USAGE_X_PRICE_CATALOG', 'price_catalog_versions': versions,
             'external_calls': external_calls, 'metered_records': len(records)}
    if len(records) != external_calls or not versions:
        basis['llm'] = 'UNKNOWN_CALLS_WITHOUT_METERING'
        return None, basis
    if any(getattr(r, 'metered_cost_usd', None) is None for r in records):
        basis['llm'] = 'UNKNOWN_USAGE_NOT_REPORTED'
        return None, basis
    total = sum((Decimal(str(r.metered_cost_usd)) for r in records), Decimal('0'))
    basis['metered_usd'] = str(total)
    return total, basis


def prior_worker_metered_cost(pool, build_id: str) -> dict | None:
    """Metered model cost already recorded for this build by an earlier
    (lost) worker. None when nothing was recorded. `unknown` counts served
    calls without metered cost; the call in flight at the moment of a crash
    never reached the ledger and cannot be counted."""
    try:
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT count(*), COALESCE(sum(metered_cost_usd), 0), "
                "count(*) FILTER (WHERE metered_cost_usd IS NULL AND outcome IN ('ok', 'unknown') "
                "                 AND COALESCE(authorized_cost_usd, 0) > 0), "
                "COALESCE(sum(authorized_cost_usd) FILTER (WHERE metered_cost_usd IS NULL AND outcome IN ('ok', 'unknown')), 0) "
                "FROM task_attempts WHERE build_id = %s AND kind = 'provider_call'", (build_id,)).fetchone()
    except Exception:
        logging.getLogger(__name__).warning('prior attempt lookup failed for %s', build_id, exc_info=True)
        return None
    if not row or not row[0]:
        return None
    # unknown_calls includes the call that was in flight when the worker died
    # (write-ahead row still 'unknown'): its cost is unknown, bounded by its
    # authorization (unknown_exposure_usd) -- never counted as zero or exact.
    return {'calls': int(row[0]), 'metered_usd': Decimal(str(row[1])), 'unknown_calls': int(row[2]),
            'unknown_exposure_usd': Decimal(str(row[3] if len(row) > 3 else 0))}


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
    prior = getattr(gateway, 'prior_metered', None)
    prior = prior if isinstance(prior, dict) else None
    # A lost worker may have contacted a provider without reporting usage.
    # UNKNOWN is outstanding liability, never proof of zero spend.
    paid_activity = external_calls > 0 or capability_activity or bool(
        prior and (prior.get('calls', 0) or prior.get('unknown_calls', 0) or prior['metered_usd'] > 0))
    if not ready and not paid_activity:
        subscriptions.release(build_id=build_id)
        return 'released', {'action': 'released'}, None

    # M5 Task 8: model spend is actual only when every authorized external call
    # left a provider-reported cost. Otherwise it stays unknown (NULL); the
    # authorized estimate is never relabelled as actual.
    cost_basis = {'llm': 'NO_EXTERNAL_CALLS'}
    if external_calls == 0:
        llm_actual = Decimal('0')
    else:
        ledger = getattr(gateway, 'usage', None)
        llm_actual = (ledger.actual_external_cost_usd(authorized_external_calls=external_calls)
                      if isinstance(ledger, ProviderUsageLedger) else None)
        cost_basis = {'llm': 'PROVIDER_REPORTED'}
        if llm_actual is None:
            # Autonomous completion §3: usage x versioned price catalog when
            # every external call left reported usage (or was refused, = 0).
            llm_actual, cost_basis = metered_llm_cost(gateway, external_calls)
    if prior:
        cost_basis = {**cost_basis, 'earlier_workers': {k: str(v) for k, v in prior.items()}}
        llm_actual = (None if llm_actual is None or prior['unknown_calls']
                      else llm_actual + prior['metered_usd'])
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
    evidence = {'action': 'settled', 'cost_basis': cost_basis}
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
        # Name what still failed (the UI shows this under technical details).
        last = '; '.join(f'{getattr(f, "acceptance_id", "?")}: {getattr(f, "message", "")}'[:240]
                         for f in report_failures[:4])
        return False, 'verification_failed', (
            f'build did not pass sandbox verification after {getattr(result, "repair_rounds", "?")} repair round(s)'
            + (f'; still failing: {last}' if last else ''))[:2000]
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
                        infrastructure_environment: str = 'preview', spec_repo=None, agent_recorder=None,
                        attempt_pool=None) -> str | None:
    """Returns the terminal BuildStatus value written, or None if nothing was
    done (unknown build id / already claimed by another delivery)."""
    try:
        request = jobs.get_request(build_id)
    except KeyError:
        return None
    if not jobs.transition(build_id=build_id, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING):
        return None  # duplicate delivery / already handled: idempotent no-op
    beat = getattr(jobs, 'checkpoint', None)
    if callable(beat):  # crash recovery: the heartbeat starts at the claim
        try:
            beat(build_id)
        except Exception:
            logging.getLogger(__name__).warning('first heartbeat failed for %s', build_id, exc_info=True)

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
        from .uploaded_assets import install as install_uploaded_assets
        install_uploaded_assets(engine,prompt=prompt,pool=attempt_pool,store=getattr(workspace,'storage',None),
                                project_id=request.get('public_project_id'),account_id=str(request['user_id']))
        model_budget_binding = bind_model_budget_to_reservation(gateway, request)
        # Directive 2026-10-09 §10/§12: stop between steps; live log.
        control = BuildControl(jobs, build_id)
        install_build_control(engine, gateway, control)
        if attempt_pool is not None:
            control.flush = lambda: _persist_build_attempts(attempt_pool, jobs, build_id, gateway, required=True)
            if hasattr(gateway, 'on_attempt_start'):
                gateway.on_attempt_start = control.flush_attempts   # write-ahead ledger
            # A recovered build: calls a lost worker already made are still owed.
            gateway.prior_metered = prior_worker_metered_cost(attempt_pool, build_id)
        if agent_recorder is not None:  # Agent OS: the real build as a durable agent task graph
            control.recorder = agent_recorder
            agent_recorder.start(from_brief='Approved project brief' in (prompt or ''))
            if hasattr(agent_recorder, 'bind'):     # plan-governed builds: plan limits + per-task charging
                agent_recorder.bind(engine, gateway)
            if getattr(agent_recorder, 'enforce', False):   # ...and the approved criteria are the test basis (G3)
                install_approved_criteria(engine, {'acceptance_criteria': getattr(agent_recorder, 'acceptance_criteria', None)})
        round_snapshots: list[dict] = []
        # Keep original best-effort snapshots until independently proven in
        # the real R2/Oracle environment; strict mode is opt-in and fail-closed.
        engine.require_durable_snapshots = os.getenv('OMNI_STRICT_ROUND_EVIDENCE') == '1'
        if engine.require_durable_snapshots and not (
                callable(getattr(getattr(workspace, 'storage', None), 'put_bytes', None)) and
                callable(getattr(workspace, '_zip_repo', None))):
            raise RuntimeError('strict durable round evidence backend unavailable')
        install_round_snapshots(engine, workspace, build_id, round_snapshots, control)
        install_visual_sink(engine, workspace, build_id)
        install_rejected_json_sink(gateway, workspace, build_id)
        set_acceptance_scope(engine, build_contract.to_dict() if build_contract is not None else None)
        control.checkpoint()
        _report_phase(jobs, build_id, 'GENERATING', 'generating code, building, testing and repairing')
        result = engine.build(prompt)
        if agent_recorder is not None and hasattr(agent_recorder, 'raise_if_violated'):
            agent_recorder.raise_if_violated()   # plan-governed: a swallowed violation still fails closed
        _report_phase(jobs, build_id, 'VERIFYING', 'running quality, security and rights gates')
        quality = quality_fn(spec=result.spec, repository=result.repository, minimum_score=min_quality)
        security = security_fn(result.repository)

        core_ready, error_code, error_message = evaluate_release_gates(
            result=result, quality=quality, security=security, rights=rights)
        # Release policy (directive 2026-10-10): a check that did not run is not
        # a pass; mandatory checks must PASS for this exact repository.
        quality_report = release_quality_report(build_id, engine, gateway, result, quality, security, rights)
        persist_quality_report(attempt_pool, quality_report, request.get('internal_project_id'))
        if core_ready:
            from .release_policy import enforcement_mode, explain
            if enforcement_mode() == 'enforce':
                if quality_report is None:
                    core_ready, error_code, error_message = (
                        False, 'release_policy_unavailable',
                        'release policy: required quality report could not be generated')
                elif quality_report.blocking:
                    core_ready, error_code, error_message = False, 'release_policy_failed', explain(quality_report)
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
            'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
            'provider_usage': provider_usage_evidence(gateway),
            'provider_spend_usd': str(spent), 'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
            'model_budget_binding': model_budget_binding,
            'llm_cap_overage': llm_cap_overage(request, spent),
            'asset_capabilities': asset_capability_status(capability_plan),
            # Agent OS §11: which skills shaped the build and what QA review found.
            'skills_applied': _skills_applied(),
            'product_review': list(getattr(getattr(engine, 'executor', None), 'reviews', None) or []),
            # Directive 2026-10-09 §17: real-browser flow check ('unavailable' is never read as passed).
            'browser_check': getattr(getattr(engine, 'executor', None), 'last_probe', None),
            # Autonomous completion §1: behavioural acceptance inside the build (last run + every round).
            'behavior_acceptance': behavior_evidence(engine),
            'consistency_gate': consistency_evidence(engine),
            'preview_smoke': preview_smoke_evidence(engine),
            'visual_qa': visual_evidence(engine),
            'quality_report': quality_report.to_dict() if quality_report is not None else None,
            'round_snapshots': round_snapshots,
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
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
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
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
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
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
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
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
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

    recorder = None
    if os.getenv('OMNI_AGENT_RECORDER', '1') != '0':
        # Wave A: a build approved with an execution plan records that plan's
        # DAG (pre-created tasks with real dependencies); others stay reactive.
        from .agent_os.recorder import recorder_for
        recorder = recorder_for(_v28_pool, build_id, execution_plan_binding(_v28_pool, build_id),
                                enforce=os.getenv('OMNI_PLAN_DRIVEN') == '1')
    try:
        _run_live_build_job_with_components(build_id, jobs=jobs, workspace=workspace,
                                            components_factory=components_factory, agent_recorder=recorder)
    finally:
        _persist_build_attempts(_v28_pool, jobs, build_id, captured.get('gateway'))
        if recorder is not None and recorder.run_id is not None:
            try:
                with _v28_pool.connection() as conn:
                    row = conn.execute('SELECT status, evidence_json FROM build_jobs WHERE id = %s', (build_id,)).fetchone()
                recorder.finish(status=row[0] if row else 'failed', evidence=row[1] if row else None)
            except Exception:
                logging.getLogger(__name__).warning('agent recorder finish failed for %s', build_id, exc_info=True)


def execution_plan_binding(pool, build_id: str) -> dict | None:
    """The approved plan bound to this build at admission (evidence_json.execution_plan)."""
    try:
        with pool.connection() as conn:
            row = conn.execute("SELECT evidence_json -> 'execution_plan' FROM build_jobs WHERE id = %s", (build_id,)).fetchone()
    except Exception:
        logging.getLogger(__name__).warning('execution plan lookup failed for %s', build_id, exc_info=True)
        return None
    value = row[0] if row else None
    if isinstance(value, str):
        import json as _json
        value = _json.loads(value)
    return value if isinstance(value, dict) else None


def _persist_build_attempts(pool, jobs, build_id: str, gateway, *, required: bool = False) -> None:
    """Mandatory before dispatch; final terminal evidence remains best effort."""
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
                         reservation_id=build_id, final_outcome=getattr(status, 'value', None),
                         require_active_reservation=required)
    except Exception as exc:
        logging.getLogger(__name__).exception('attempt ledger write failed for %s', build_id)
        if required:
            from .attempt_ledger import AttemptLedgerUnavailable
            raise AttemptLedgerUnavailable('mandatory attempt ledger write failed') from exc


def _run_live_build_job_with_components(build_id: str, *, jobs, workspace, components_factory,
                                        agent_recorder=None) -> None:
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
        agent_recorder=agent_recorder,
        attempt_pool=_v28_pool,
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
                          min_quality: int = 80, preflight=None, control_jobs=None) -> str | None:
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
        # Autonomous completion §5: a change can be stopped and shows its live
        # log, like a build (heartbeat at every step boundary).
        control = None
        if control_jobs is not None:
            control = BuildControl(control_jobs, modification_id)
            if hasattr(gateway, 'before_call'):
                gateway.before_call = control.before_model_call
            executor = ControlledExecutor(executor, control)
            control.log('phase', 'מתחיל לעבד את בקשת השינוי')
            control.checkpoint()
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
    except BuildCancelled as exc:
        spent, calls = spend_snapshot(gateway)
        billing = resolve_billing(subscriptions, build_id=modification_id, ready=False, spent=spent, external_calls=calls)
        jobs.complete(
            modification_id, project_id=project_id, status='CANCELLED',
            error_code='cancelled_by_user', error_message=str(exc)[:500],
            evidence_json={'billing': billing, 'provider_spend_usd': str(spent),
                           'provider_usage': provider_usage_evidence(gateway),
                           'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS},
        )
        return 'CANCELLED'
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
        control_jobs=__import__('omni_prod.build_control', fromlist=['ModificationJobs']).ModificationJobs(_v28_pool),
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


def execute_intake_interpretation(message: str) -> dict:
    """RQ entrypoint on the 'omni-intake' queue (intake-worker service).
    Disabled unless the worker has OMNI_INTAKE_MODEL=1 and a per-message
    OMNI_INTAKE_CALL_BUDGET_USD; see omni_prod.intake.worker_route."""
    from .intake.worker_route import execute
    return execute(message)

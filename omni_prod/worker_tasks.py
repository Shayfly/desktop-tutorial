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
import re
import socket
import time
from decimal import Decimal

from .models import BuildStatus
from .build_contract import BuildContract, BuildContractStatus
from .capability_worker import CapabilityStageBlocked
from .image_match import ROLLOUT_NOT_RUN as IMAGE_ROLLOUT_NOT_RUN, enabled_for as image_match_enabled
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


class RoundEvidence:
    """The stage evidence each verified round produced, paired with that round's snapshot sha256 (round_snapshots).

    bld_cb2d1b90a90f430c98603d14f8afa1a8: the stored version was round 0, but every stage row was built from the
    executors' LAST state -- round 6, a discarded candidate: the review row read PASS (round 6 had no blocking
    finding) for a version that still had four. A stage that did not run in a round (the threshold failed before it)
    has None for that round, never the evidence of an earlier one: a new object (or a new review entry) is this
    round's, the same object as at the previous capture is not."""

    SOURCES = ('consistency_gate', 'preview_smoke', 'behavior_acceptance', 'browser_check', 'visual_qa')

    def __init__(self, engine):
        self._engine = engine
        self._seen: dict = {}
        self._reviews_seen = 0
        self.rounds: dict[str, dict] = {}        # sha256 -> {'round', 'evidence'}; a later round with the same sha wins

    def _current(self) -> dict:
        from .behavior_acceptance import BehaviorAcceptanceExecutor, find_in_chain
        from .consistency_gate import ConsistencyGateExecutor
        from .preview_smoke import PreviewReadyExecutor
        from .visual_qa import VisualQAExecutor
        chain = getattr(self._engine, 'executor', None)
        find = lambda cls: find_in_chain(chain, cls)
        return {'consistency_gate': getattr(find(ConsistencyGateExecutor), 'last_consistency', None),
                'preview_smoke': getattr(find(PreviewReadyExecutor), 'last_smoke', None),
                'behavior_acceptance': getattr(find(BehaviorAcceptanceExecutor), 'last_report', None),
                'browser_check': getattr(chain, 'last_probe', None),
                'visual_qa': getattr(find(VisualQAExecutor), 'last_visual', None)}

    def capture(self, index: int, sha256: str) -> None:
        ev = {}
        for name, obj in self._current().items():
            ev[name] = obj if obj is not None and obj is not self._seen.get(name) else None
            self._seen[name] = obj
        reviews = list(getattr(getattr(self._engine, 'executor', None), 'reviews', None) or [])
        ev['product_review'] = reviews if len(reviews) > self._reviews_seen else []   # this round's review is the last
        self._reviews_seen = len(reviews)
        self.rounds[sha256] = {'round': index, 'evidence': ev}

    def for_version(self, sha256: str) -> dict | None:
        return self.rounds.get(sha256)


def kept_round(engine, result) -> dict | None:
    """{'round', 'sha256'} of the round whose version the build kept (the one its stage rows judge), or None."""
    tracker = getattr(engine, 'round_evidence', None)
    if not isinstance(tracker, RoundEvidence) or result is None:
        return None
    from .workspace import _checksum
    sha = _checksum(result.repository)
    kept = tracker.for_version(sha)
    return {'round': kept['round'], 'sha256': sha} if kept is not None else {'round': None, 'sha256': sha}


def install_round_snapshots(engine, workspace, build_id: str, sink: list, control=None) -> None:
    """Directive 2026-10-10 P0.3: store every verified candidate durably
    (object storage, checksum-verified on read) before the next repair, with
    its verification progress and what the loop decided. The loop rolls back
    to the best one; these keys make each round inspectable and restorable."""
    store = getattr(workspace, 'storage', None)
    zip_repo = getattr(workspace, '_zip_repo', None)
    if not hasattr(engine, 'round_hook'):
        return
    tracker = RoundEvidence(engine)
    engine.round_evidence = tracker              # release_quality_report: the stage rows judge the KEPT round

    def hook(index, repo, report, decision, progress):
        from .workspace import _checksum
        entry = {'round': index, 'decision': decision, 'progress': list(progress), 'sha256': _checksum(repo),
                 'failing': sorted({getattr(f, 'acceptance_id', '?') for f in getattr(report, 'failures', ()) or ()})}
        full = (getattr(engine, 'round_failures', None) or {}).get(index)
        if full is not None:                     # every failing check of the round, the summary line expanded
            entry['failing_all'] = sorted({getattr(f, 'acceptance_id', '?') for f in full})
        tracker.capture(index, entry['sha256'])  # before any storage write: a failed upload never loses the pairing
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


def _install_quarantine_history(jobs, build_id: str) -> None:
    """Michael condition 5: the review asks whether an EARLIER build quarantined the same probe (read-only query)."""
    from . import product_review
    pool = getattr(jobs, 'pool', None) or getattr(jobs, '_pool', None)
    if pool is None:
        product_review._QUARANTINE_HISTORY = None
        return

    def lookup(probe: str):
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT id FROM build_jobs WHERE id <> %s AND evidence_json->'gate_waste'->'quarantined_gates' "
                "@> %s::jsonb ORDER BY created_at DESC LIMIT 1",
                (build_id, json.dumps([{'probe': probe}]))).fetchone()
        return row[0] if row else None

    product_review._QUARANTINE_HISTORY = lookup


def _gate_waste(engine, spent, repair_rounds) -> dict:
    from .behavior_acceptance import find_in_chain
    from .product_review import ProductReviewExecutor
    review = find_in_chain(getattr(engine, 'executor', None), ProductReviewExecutor)
    rounds = int(getattr(review, 'gate_waste_rounds', 0) or 0) if review is not None else 0
    quarantined = list(getattr(review, 'quarantined', []) or []) if review is not None else []
    measured = Decimal(str(getattr(review, 'gate_waste_usd', 0) or 0)) if review is not None else Decimal('0')
    calls = int(getattr(review, 'gate_waste_calls', 0) or 0) if review is not None else 0
    critical = [q for q in quarantined if q.get('critical')]
    return {'rounds': rounds, 'measured_usd': str(measured.quantize(Decimal('0.0001'))), 'model_calls': calls,
            'basis': 'gateway spend between the first repeated review and the quarantine (measured, not estimated)',
            'quarantined_gates': quarantined, 'critical_quarantine': bool(critical),
            # Michael condition 1: a critical gate in quarantine never releases silently.
            'banner': ('בדיקה קריטית הושעתה בבנייה הזו (' + ', '.join(q['skill'] for q in critical) +
                       '). התצוגה המקדימה זמינה; פרסום לפרודקשן חסום עד שהבדיקה תתוקן.') if critical else None}


def _design_reviews(engine) -> list:
    from .behavior_acceptance import find_in_chain
    from .visual_qa import VisualQAExecutor
    target = find_in_chain(getattr(engine, 'executor', None), VisualQAExecutor)
    critic = getattr(target, 'design_critic', None) if target is not None else None
    return list(getattr(critic, 'reviews', []) or [])[-8:]


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
        tracker = getattr(engine, 'round_evidence', None)
        if isinstance(tracker, RoundEvidence) and not tracker.rounds:
            # an engine that never reported a round (no round hook call): its executors' state is the only evidence
            logging.getLogger(__name__).warning('ROUND_EVIDENCE_NOT_RECORDED build=%s: the stage rows read the '
                                                'executors\' last state', build_id)
        elif isinstance(tracker, RoundEvidence):
            # The rows are bound to this repository's digest, so they read THIS version's round only. A version no
            # round recorded is said as not run -- never filled in from the last candidate.
            kept = tracker.for_version(_checksum(result.repository))
            if kept is None:
                logging.getLogger(__name__).error('KEPT_ROUND_UNKNOWN build=%s: no round recorded this version; its '
                                                  'stage rows say NOT_RUN', build_id)
            ev = kept['evidence'] if kept is not None else {}
            evidence.update({
                'consistency_gate': {'last': ev['consistency_gate']} if ev.get('consistency_gate') else None,
                'preview_smoke': ev.get('preview_smoke'),
                'behavior_acceptance': {'last': ev['behavior_acceptance']} if ev.get('behavior_acceptance') else None,
                'browser_check': ev.get('browser_check'),
                'product_review': list(ev.get('product_review') or []),
                'visual_qa': ev.get('visual_qa'),
            })
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
    from .build_control import BuildDeadline
    from .verification_verdict import queue_timeouts
    from .site_content.agents import SiteContentInvalid, SiteRenderDefect
    text = str(exc)
    if isinstance(exc, SiteContentInvalid):        # the model's content document, still invalid after its correction
        return 'site_content_invalid'
    if isinstance(exc, SiteRenderDefect):          # the platform's own render (library, fact sheet, contract)
        return 'site_render_defect'
    if isinstance(exc, (BuildDeadline, *queue_timeouts())):   # the build's own limit, or the queue's as the last resort
        return 'build_timeout'
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
        # warehouse 70 (bld_* 2026-11-17, gemini-3.8-flash: "model did not return valid JSON"): every model that was
        # tried answered, but none in the required format. That is not "load or quota", and the customer is told so.
        from .model_gateway import ModelJSONRejected
        tried = [k for k in getattr(exc, 'route_failures', ()) if k not in ('skipped', 'budget')]
        if tried and all(isinstance(k, type) and issubclass(k, ModelJSONRejected) for k in tried):
            return 'model_bad_output'
        return 'model_unavailable'
    return 'worker_exception'


def _site_route_evidence(engine):
    """The content route's report for a build that raised (site_content_invalid: the problems are in it)."""
    if engine is None:
        return None
    try:
        from .site_content import report
        return report(engine)
    except Exception:  # evidence must never fail a build
        logging.getLogger(__name__).warning('site route evidence failed', exc_info=True)
        return None


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


def taxonomy_evidence(engine, *, ready: bool = False) -> dict:
    """C24: the failure taxonomy and first_pass of THIS build, in its evidence, on success and on every failure exit
    (they were recorded only by rehearsals; live builds never reached first_pass_yield).
    #95: first_pass is True only for a build this worker records as release-ready; every failure exit passes
    ready=False, so a failed build is never counted as a first pass whatever the engine says."""
    if engine is None:
        return {'failure_taxonomy': [], 'first_pass': False, 'taxonomy_note': 'the engine was never built'}
    return {'failure_taxonomy': list(getattr(engine, 'failure_taxonomy', None) or []),
            'first_pass': bool(ready) and getattr(engine, 'first_pass', None) is True}


def _aborted_review_evidence(engine) -> dict:
    """Carry completed static probe records through a terminal exception."""
    executor = getattr(engine, 'executor', None)
    reviews = getattr(executor, 'reviews', None) or ()
    rounds = [{'round': review['round'], 'skill_execution': review['skill_execution']}
              for review in reviews if review.get('skill_execution')]
    return {'product_review_skill_execution': rounds} if rounds else {}


def resolve_billing(subscriptions, *, build_id: str, ready: bool, spent: Decimal, external_calls: int) -> str:
    """READY -> settle(). FAILED -> its credits are released (founder 2026-11-02, DELIVERY-001: a failed stage is
    not charged): release() when no external spend happened, release_failed() -- RELEASED with the real provider
    cost kept on record -- when it did. A failed build is never SETTLED."""
    if ready:
        subscriptions.settle(build_id=build_id, actual_provider_cost_usd=spent)
        return 'settled'
    if spent > 0 or external_calls > 0:
        subscriptions.release_failed(build_id=build_id, actual_provider_cost_usd=spent)
        return 'released'
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


def computed_provider_cost(*, llm_actual, gateway_spend: Decimal, prior, capability_evidence,
                           infra_max: Decimal) -> tuple[Decimal | None, dict]:
    """Michael 2026-11-14 (b1): the settlement basis when the provider did not report an actual.

    Before this, a build whose actual was unknown (an image whose provider reports no price, or one model call
    without reported usage) was settled at the whole reservation estimate (~$2), even when the model calls were
    metered at $0.48: four such builds charged the plan $3.66 more than was measured and stopped the next build.
    computed_from_usage = model spend (metered when every call reported usage, otherwise the gateway's spend
    ledger, where a call without reported usage stays at its authorized worst case) + each capability event's
    actual, else its catalog estimate, else its maximum + the infrastructure maximum (still a reserve). It is
    never relabelled as actual (COST_MODEL.md: computed != actual). None when a component has no number at all;
    the caller then settles at the reservation and says so loudly."""
    missing = []
    if llm_actual is not None:
        llm = Decimal(str(llm_actual))
        llm_basis = 'metered'
    else:
        llm = Decimal(str(gateway_spend))
        llm_basis = 'gateway_spend_ledger'
        if prior:
            llm += Decimal(str(prior.get('metered_usd') or 0)) + Decimal(str(prior.get('unknown_exposure_usd') or 0))
            if prior.get('unknown_calls') and not prior.get('unknown_exposure_usd'):
                missing.append('earlier_worker_unknown_call_without_exposure')
    cap = Decimal('0')
    usage = [] if not capability_evidence else list(capability_evidence.get('usage') or [])
    for event in usage:
        raw = next((event.get(k) for k in ('actual_cost_usd', 'estimated_cost_usd', 'maximum_cost_usd')
                    if event.get(k) is not None), None)
        if raw is None:
            missing.append(f"capability:{event.get('requirement_id') or event.get('provider') or '?'}")
            continue
        cap += Decimal(str(raw))
    basis = {'basis': 'computed_from_usage', 'llm_usd': str(llm), 'llm_basis': llm_basis,
             'capability_usd': str(cap), 'infrastructure_usd': str(infra_max)}
    if missing:
        return None, {**basis, 'missing': missing}
    return llm + cap + infra_max, basis


def asset_capability_status(plan) -> dict | None:
    """REQUIRED / OPTIONAL / NOT_REQUIRED per asset capability (decision #28)."""
    if plan is None:
        return None
    from .capability_planner import asset_capability_status as _status
    return _status(plan)


def _install_agentic_repair(engine, request) -> bool:
    """CEO order 2026-11-09 (b): the repair model works inside the repository with tools. Founder builds only for
    now (OMNI_AGENTIC_REPAIR=founder, the default); 'all' turns it on for every build, '0' turns it off."""
    import os
    mode = os.getenv('OMNI_AGENTIC_REPAIR', 'founder').strip().lower()
    from .site_content import on_route
    if on_route(engine):
        # the content route repairs the content document, never the HTML; an agent editing the page would be undone
        logging.getLogger(__name__).info('AGENTIC_REPAIR_OFF the content route (site_content) repairs content only')
        return False
    if mode in ('0', 'off', 'false', ''):
        return False
    if mode != 'all':
        from .pricing import m5_founder_account
        if not m5_founder_account((request or {}).get('user_id')):
            return False
    repairer = getattr(engine, 'repairer', None)
    gateway = getattr(repairer, 'gateway', None)
    if repairer is None or gateway is None or type(repairer).__name__ == 'AgenticRepairAgent':
        return False
    from .agentic_repair import AgenticRepairAgent
    engine.repairer = AgenticRepairAgent(gateway, fallback=repairer)
    return True


def bind_model_budget_to_reservation(gateway, request: dict) -> dict:
    """Fail closed before paid model calls; reuse the existing gateway budget.

    The durable admission quote is the authority. Cost-class caps additionally
    constrain LIGHT and STANDARD; neither worker environment nor legacy
    requests may enlarge their model-spend authorization.
    """
    from .pricing import CostClass, m5_class_llm_cap

    components = (request.get('economics_quote') or {}).get('components') or {}
    if 'llm_maximum_usd' not in components:
        raise PermissionError('model_budget_missing: legacy request has no authorized LLM budget')
    if not callable(getattr(gateway, 'bind_budget', None)):
        raise PermissionError('model_budget_unenforceable: gateway cannot bind authorization')

    try:
        reserved = Decimal(str(components['llm_maximum_usd']))
        if not reserved.is_finite() or reserved < 0:
            raise ValueError('invalid reserved LLM budget')
        class_name = components.get('cost_class')
        from .pricing import m5_founder_account, m5_founder_build_budget
        founder_test = bool(components.get('founder_test')) and m5_founder_account(request.get('user_id'))
        if founder_test:   # CEO 2026-11-08: the founder's admitted test budget, never above the founder cap
            reserved = min(reserved, m5_founder_build_budget())
        elif class_name in (CostClass.LIGHT.value, CostClass.STANDARD.value):
            reserved = min(reserved, m5_class_llm_cap(class_name))
        elif not class_name:
            # Older quotes with a valid reserved maximum remain supported;
            # they are never allowed to fall back to the worker env budget.
            pass
        out = {'binding': 'bound', **gateway.bind_budget(reserved)}
        if class_name:
            if not callable(getattr(gateway, 'restrict_to_cost_class', None)):
                raise PermissionError('model_class_unenforceable: gateway lacks class restriction')
            founder = m5_founder_account(request.get('user_id'))
            out['model_allowlist'] = (gateway.restrict_to_cost_class(class_name, unrestricted=True) if founder
                                      else gateway.restrict_to_cost_class(class_name))
        return out
    except (ValueError, ArithmeticError) as exc:
        raise PermissionError('invalid model budget authorization') from exc


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
    computed = None
    if actual is None:
        gateway_spend, _ = spend_snapshot(gateway)
        computed, computed_basis = computed_provider_cost(
            llm_actual=llm_actual, gateway_spend=gateway_spend, prior=prior,
            capability_evidence=capability_evidence, infra_max=infra_max)
        cost_basis = {**cost_basis, 'settlement': computed_basis}
        if computed is None:
            # Fails loudly, never silently: the reservation is the only number left, and the log and the evidence
            # name the component that had none.
            logging.getLogger(__name__).error('SETTLEMENT_WITHOUT_MEASUREMENT build=%s missing=%s; settled at the '
                                              'reservation', build_id, computed_basis.get('missing'))
    revenue_raw = quote.get('revenue_usd')
    # Gross contribution is only computed when all non-provider variable cost
    # inputs are known. A non-zero infrastructure maximum is still a reserve,
    # not an actual, so suppress contribution rather than fabricate precision.
    revenue = None if revenue_raw is None or infra_max != 0 else Decimal(str(revenue_raw))
    if not ready:
        # Founder 2026-11-02 (DELIVERY-001): a failed build releases its credits; the provider cost it really incurred
        # stays on record (reservation + plan provider-spend meter), it is never SETTLED to the customer.
        released = subscriptions.release_failed(build_id=build_id, actual_provider_cost_usd=actual,
                                                **({'computed_provider_cost_usd': computed} if computed is not None else {}))
        evidence = {'action': 'released_failed', 'cost_basis': cost_basis}
        if released:
            evidence.update(released)
        return 'released', evidence, actual
    settlement = subscriptions.settle(
        build_id=build_id, actual_provider_cost_usd=actual,
        **({'computed_provider_cost_usd': computed} if computed is not None else {}),
        revenue_usd=revenue, infra_cost_usd=Decimal('0'),
    )
    evidence = {'action': 'settled', 'cost_basis': cost_basis}
    if settlement:
        evidence.update(settlement)
    return 'settled', evidence, actual


_FOUNDER_DRAFT_CODES = frozenset({'verification_failed', 'quality_gate_failed', 'preview_not_ready',
                                  'release_policy_failed', 'capability_gate_failed'})


def _founder_draft_allowed(request, error_code) -> bool:
    """Founder-only draft version of a failed build (CEO 2026-11-08). Never for a security finding."""
    import os
    if os.getenv('OMNI_FOUNDER_DRAFT_VERSIONS', '1') == '0' or error_code not in _FOUNDER_DRAFT_CODES:
        return False
    from .pricing import m5_founder_account
    return bool(m5_founder_account((request or {}).get('user_id')))


def _version_message(build_id: str, founder_draft: bool, banner: str | None = None) -> str:
    if founder_draft:
        return f'148AI DRAFT (failed checks, founder preview only) build {build_id}'
    if banner:
        # Michael 2026-11-10 condition 1: a critical gate in quarantine is visible on the version, never silent.
        return f'148AI PREVIEW ONLY build {build_id} — {banner}'
    return f'148AI async live build {build_id}'


# 78: the preview smoke's verdicts for "the server answered, but GET / is not a real interface". The smoke script
# itself is a frozen gate input (pipeline_identity, smoke/t4 evidence), so the words are fixed HERE, not in it.
_EMPTY_UI = re.compile(r'returned a placeholder page|did not return an HTML page')
EMPTY_UI_PREFIX = 'the app started but the generated interface is empty'
_CONTROL_KINDS = (('form', ('<form',)), ('input', ('<input', '<select', '<textarea', "createelement('input", 'createelement("input')),
                  ('button', ('<button', "createelement('button", 'createelement("button')),
                  ('table', ('<table', "createelement('table", 'createelement("table')))


def _missing_controls(repository) -> list[str]:
    """Kinds of control none of the generated files contains (a proxy for the served page, read from the code)."""
    try:
        text = ' '.join(str(v) for k, v in dict(repository or {}).items()
                        if str(k).endswith(('.py', '.html', '.js', '.htm'))).lower()
    except (TypeError, ValueError):
        return []
    if not text:
        return []
    return [k for k, tags in _CONTROL_KINDS if not any(t in text for t in tags)]


def evaluate_release_gates(*, result, quality, security, rights) -> tuple[bool, str | None, str | None]:
    if result.status != 'ready' or not result.report.passed:
        from .dependency_policy import UNSUPPORTED_DEPENDENCY
        from .quality_gate import QUALITY_FAILURE_ID
        report_failures = tuple(getattr(result.report, 'failures', ()) or ())
        from .preview_smoke import PREVIEW_FAILURE_ID
        if report_failures and all(getattr(f, 'acceptance_id', None) == PREVIEW_FAILURE_ID for f in report_failures):
            # Every acceptance check passed; the product would not start for preview.
            if all(_EMPTY_UI.search(str(getattr(f, 'message', ''))) for f in report_failures):
                # 78 (Michael 2026-11-11): the app STARTED and served an empty page -- never "did not start". Same
                # code (same step); the right words, and what the generated code lacks.
                missing = _missing_controls(getattr(result, 'repository', None))
                return False, 'preview_not_ready', (
                    f'{EMPTY_UI_PREFIX} (missing: {",".join(missing) if missing else "content"}): '
                    + '; '.join(f.message for f in report_failures))[:2000]
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
        out_of_time = getattr(result, 'stop_reason', '') == 'time_budget'
        no_repair_model = getattr(result, 'stop_reason', '') == 'repair_model_unavailable'
        platform_defect = getattr(result, 'stop_reason', '') in ('platform_render_defect', 'unowned_finding')
        content_refused = getattr(result, 'stop_reason', '') == 'site_content_invalid'
        head = (
            f'build did not pass sandbox verification after {getattr(result, "repair_rounds", "?")} repair round(s)'
            + (' (stopped repairing: the build was out of time)' if out_of_time else '')
            + (' (stopped repairing: no model returned a valid repair)' if no_repair_model else '')
            + (' (stopped repairing: the failure is in the platform\'s own page renderer, not in the written content; '
               'no repair model was asked to fix it)' if platform_defect else '')
            + (' (stopped repairing: the repair model\'s rewrite of the copy was refused by the content checks)'
               if content_refused else ''))
        # Name what still failed (the UI shows this under technical details): the KEPT version's full list, lowest
        # stage first, and what does not fit is counted, never dropped (bld_cb2d1b90a90f430c98603d14f8afa1a8: the first
        # four items were kept, the fifth -- the ALSO_FAILING line that carried VISUAL, the real blocker -- was cut).
        from .verification_group import failure_list, kept_failures
        last = failure_list(kept_failures(result), 2000 - len(head) - len('; still failing: '))
        return False, 'verification_failed', (head + (f'; still failing: {last}' if last else ''))[:2000]
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


class BuildNotFound(RuntimeError):
    """The worker was asked to run a build its database does not have (error_code build_not_found)."""


BUILD_NOT_FOUND = 'build_not_found'


def _fail_build_not_found(jobs, platform, build_id: str, exc: Exception) -> bool:
    """Log the miss; if the build's job row exists (its request or reservation row is what is missing), mark it
    FAILED with build_not_found and release its credits. Returns whether a row was marked."""
    log = logging.getLogger(__name__)
    log.error('build %s: NOT FOUND in this worker\'s database (%s); failing it, not dropping it -- check that the '
              'worker and the web use the same OMNI_DATABASE_URL', build_id, exc)
    marked = False
    try:
        marked = bool(jobs.transition(
            build_id=build_id, expected=BuildStatus.QUEUED, target=BuildStatus.FAILED, error_code=BUILD_NOT_FOUND,
            error_message=(f"The build could not be started: the build worker did not find build {build_id} "
                           f"or its request in its database ({exc})")[:2000]))
    except Exception:
        log.error('build %s: could not mark it FAILED (%s)', build_id, BUILD_NOT_FOUND, exc_info=True)
    if marked:
        try:
            platform.subscriptions.release(build_id=build_id)
        except Exception:
            log.error('build %s: credits not released after %s', build_id, BUILD_NOT_FOUND, exc_info=True)
    else:
        log.error('build %s: no QUEUED job row here either -- nothing could be marked; the job fails', build_id)
    return marked


def _run_live_build_job(build_id: str, *, jobs, platform, workspace, components_factory,
                        quality_fn, security_fn, min_quality: int = 80, preflight=None,
                        capability_stage=None, infrastructure_stage=None,
                        infrastructure_environment: str = 'preview', spec_repo=None, agent_recorder=None,
                        attempt_pool=None) -> str | None:
    """Returns the terminal BuildStatus value written, or None if nothing was
    done (already claimed by another delivery). An unknown build id raises
    BuildNotFound after marking the build FAILED (build_not_found) where it can."""
    try:
        request = jobs.get_request(build_id)
    except KeyError as exc:
        # 2026-10-29 (production): two builds ended here in ~2.5 s as "Job OK" with no write and no log -- the worker
        # read a different database than the web -- and stayed QUEUED in the web's database for ever. A build this
        # worker cannot find fails LOUDLY: logged, marked FAILED where its job row exists, and the job raises.
        _fail_build_not_found(jobs, platform, build_id, exc)
        raise BuildNotFound(f'build {build_id} not found in this worker\'s database: {exc}') from exc
    if not jobs.transition(build_id=build_id, expected=BuildStatus.QUEUED, target=BuildStatus.RUNNING):
        # Duplicate delivery / already handled: an idempotent no-op that must NOT fail a build another delivery is
        # running -- but never silent.
        logging.getLogger(__name__).warning('build %s: not claimed (not QUEUED any more): duplicate delivery or '
                                            'already handled -- nothing done', build_id)
        return None
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
    engine = None
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
        if capability_stage is not None and capability_plan is None:
            raise RuntimeError('capability stage requires a bound or planned capability plan')
        rights = platform.rights.assess(
            prompt, target_markets=markets,
            evidence=_rights_evidence_from_dicts(request.get('rights_evidence')),
            synthetic_person_media=bool(brain.rights.required_disclosures),
        )
        engine, gateway = components_factory()
        # The content-document route (omni_prod/site_content; OMNI_SITE_LIBRARY, off by default): decided on every
        # build, logged and kept for the evidence; on the route it replaces the architect, generator and repairer --
        # before any install below wraps the architect.
        from . import site_content
        site_content.install(engine, prompt=prompt, gateway=gateway, request=request,
                             plan_governed=bool(agent_recorder is not None and getattr(agent_recorder, 'enforce', False)))
        from .uploaded_assets import install as install_uploaded_assets
        install_uploaded_assets(engine,prompt=prompt,pool=attempt_pool,store=getattr(workspace,'storage',None),
                                project_id=request.get('public_project_id'),account_id=str(request['user_id']))
        # CEO 2026-11-09: Hebrew/Arabic pages are right-to-left by construction (after the logo transform).
        from .page_locale import install as install_page_locale
        install_page_locale(engine, prompt)
        # 2026-11-19: SHARE failed on every production build with the rule in the spec -- the platform writes og tags
        from .share_preview import install as install_share_preview
        install_share_preview(engine)
        # bld_cb2d1b90 (2026-11-24): left:-9999px made a right-to-left page 9999px wide in every round. The hiding idiom
        # is rewritten to the platform's visually-hidden rule after generation and every repair (omni_prod/offscreen).
        from .offscreen import install as install_offscreen
        install_offscreen(engine)
        # Michael 2026-11-10 condition 2: the truth gate's canon comes from the APPROVED request, not the spec summary.
        from .product_review import install_review_request
        install_review_request(engine, prompt)
        # 2026-11-17: the generator is told the facts the review checks, before it writes (fact_canon.install_facts)
        from .fact_canon import install_facts
        install_facts(engine, prompt)
        # conversation agent phase 3: the customer's own page structure, in order, reaches the generator
        from .page_outline import install as install_page_outline
        install_page_outline(engine, prompt)
        _install_quarantine_history(jobs, build_id)
        model_budget_binding = bind_model_budget_to_reservation(gateway, request)
        agentic_repair = _install_agentic_repair(engine, request)
        # Directive 2026-10-09 §10/§12: stop between steps; live log.
        control = BuildControl(jobs, build_id)
        install_build_control(engine, gateway, control)
        if attempt_pool is not None:
            control.flush = lambda: _persist_build_attempts(attempt_pool, jobs, build_id, gateway, required=True)
            if hasattr(gateway, 'on_attempt_start'):
                gateway.on_attempt_start = control.flush_attempts   # write-ahead ledger
            # A recovered build: calls a lost worker already made are still owed.
            gateway.prior_metered = prior_worker_metered_cost(attempt_pool, build_id)
        if capability_stage is not None:
            _report_phase(jobs, build_id, 'ASSETS', 'generating and verifying required assets')
            # #324 (Michael 2026-11-13): an image is generated from an ENGLISH prompt translated once from the brief
            # (saved, never translated again) with a fixed negative list. The translation is a call through THIS
            # gateway -- after its budget and write-ahead ledger are bound -- so it is metered like any other call.
            from .image_prompt import gateway_translator, prepare_image_prompts
            artifact_store = getattr(getattr(capability_stage, 'executor', None), 'artifact_store', None)
            resolver = getattr(capability_stage, 'assignments_resolver', None)
            capability_plan = prepare_image_prompts(
                capability_plan, translate=gateway_translator(gateway), store=artifact_store,
                build_id=build_id, project_id=internal_project_id,
                only=set((resolver(capability_plan) if resolver else {}) or {}))
            capability_evidence = capability_stage.prepare(
                build_id=build_id, project_id=internal_project_id, plan=capability_plan,
                authorized_maximum_usd=capability_authorization_ceiling(request),
                now=time.time(),
            )
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
        from .design_review import install_design_critic
        design_review_on = install_design_critic(engine, request, prompt)
        install_rejected_json_sink(gateway, workspace, build_id)
        set_acceptance_scope(engine, build_contract.to_dict() if build_contract is not None else None)
        control.checkpoint()
        # #324 (Michael 2026-11-13): the plan's verified generated images go INTO the page -- with their purpose,
        # dimensions and an alt from the brief -- and the build is not accepted until each is visible with that alt.
        build_prompt = prompt
        if capability_stage is not None and capability_evidence is not None:
            from .generated_images import install as install_generated_images
            build_prompt = install_generated_images(
                engine, prompt=prompt, plan=capability_plan, evidence=capability_evidence,
                store=getattr(getattr(capability_stage, 'executor', None), 'artifact_store', None),
                vision=gateway if image_match_enabled(request) else None)   # lens 11 / I-01, before code
            image_match = getattr(getattr(engine, 'core', engine), 'image_match', None)
            if image_match is None and getattr(getattr(engine, 'core', engine), 'generated_images', None):
                # not run by rollout: said in the evidence and the log, never a silent pass
                logging.getLogger(__name__).warning('IMAGE_MATCH_NOT_RUN build=%s %s', build_id, IMAGE_ROLLOUT_NOT_RUN)
                image_match = [{'status': 'NOT_RUN', 'reason': IMAGE_ROLLOUT_NOT_RUN}]
                setattr(getattr(engine, 'core', engine), 'image_match', image_match)
            if image_match:
                capability_evidence = {**capability_evidence, 'image_match': image_match}
        # 2026-11-15 ("סבא שמעון"): the customer's own photo, chosen as the main image as is, goes in unchanged
        from .uploaded_assets import install_main_image
        from .window_catalog import install as install_window_gate   # A2 step 9: approved windows gate the build
        install_window_gate(engine, prompt=build_prompt)
        from .skill_units.gate import install as install_skill_gate   # owner 2026-11-16: skill units block (G3, G4, G6)
        install_skill_gate(engine, 'G3')                              # accessibility
        install_skill_gate(engine, 'G4')                              # performance budget
        install_skill_gate(engine, 'G6')                              # secrets
        install_skill_gate(engine, 'HE')                              # Hebrew: grammar, gender, translationese
        install_skill_gate(engine, 'G10')                             # copy: filler and placeholders
        install_skill_gate(engine, 'G11')                             # links: tel, anchors, address
        for g in ('G1', 'BRAND', 'SHARE'):                            # empty blocks, brand name, share preview
            install_skill_gate(engine, g)
        install_skill_gate(engine, 'G5')                              # rights: every font, image, audio has a known source
        install_skill_gate(engine, 'PRO')                             # professional minimum of a business site
        # #430 carried the gates' checks to the generator only in install_all, which the rehearsal calls and the worker
        # never did: 0 of 5 production specs carried them, and SHARE failed all five (2026-11-19). The same list.
        from .skill_units.gate import WORKER_GATES, carry_rules
        carry_rules(engine, WORKER_GATES)
        build_prompt = install_main_image(engine, prompt=build_prompt, pool=attempt_pool,
                                          store=getattr(workspace, 'storage', None),
                                          project_id=request.get('public_project_id'), account_id=str(request['user_id']))
        # G8 (stage F): the product keeps answering under load; warns until it is calibrated
        from .runtime_load import install as install_runtime_load
        install_runtime_load(engine)
        # Warehouse 130 (first slice): an APP's data screens show loading, empty and error, and a server error reaches
        # the customer as a sentence with an action. Decided from the approved request with the route's own test (never
        # on a content-only site); the decision and its reason are in the evidence of every build. Warns until calibrated.
        from .app_states import carry_rule as carry_app_states_rule, install as install_app_states
        install_app_states(engine, prompt=prompt)
        carry_app_states_rule(engine)
        # A4 (the owner 2026-11-16, stage D): one asset plan -- every image, uploaded or generated, has one place
        from .a4 import install as install_asset_plan
        build_prompt = install_asset_plan(engine, prompt=build_prompt)
        # production 2026-11-16 ("148 דלתות"): no raw 148ai-asset:// address reaches the browser (a broken image)
        from .asset_markers import install as install_asset_marker_gate
        install_asset_marker_gate(engine)
        # G-APPLE (the owner 2026-11-17): the design contract is locked and the gate installed LAST, right before the
        # build; it warns until it is calibrated. Its two reviewers use the build's own routed, budgeted gateway.
        from .g_apple import install as install_apple_gate
        from .attempt_ledger import TaskTaggedGateway as _ReviewGateway
        build_prompt = install_apple_gate(engine, prompt=build_prompt,
                                          gateway=_ReviewGateway(getattr(gateway, '_inner', gateway), 'review'))
        _report_phase(jobs, build_id, 'GENERATING', 'generating code, building, testing and repairing')
        from .fact_canon import needs_customer_input
        getattr(engine, 'core', engine).missing_input = (                    # #335 (d)
            lambda messages: needs_customer_input(messages, build_prompt))
        result = engine.build(build_prompt)
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
            verdicts = getattr(getattr(engine, 'core', engine), 'image_match', None)
            if verdicts:                                   # lens 11: the image check stays in the build's evidence
                capability_evidence = {**capability_evidence, 'image_match': verdicts}
        capability_ready = True if capability_stage is None else bool(capability_evidence.get('required_ready'))
        ready = core_ready and capability_ready
        gate_waste = _gate_waste(engine, None, result.repair_rounds)
        if core_ready and not capability_ready:
            error_code, error_message = 'capability_gate_failed', 'required capability evidence is not VERIFIED'
        if not core_ready and getattr(result, 'stop_reason', '') == 'needs_customer_input':
            # #335 (d): the customer is asked (the chat shows this code), not more repair rounds
            error_code = 'needs_customer_input'
            error_message = 'missing from the customer: ' + ', '.join(
                getattr(getattr(engine, 'core', engine), 'needs_input', None) or ())

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
        # CEO 2026-11-08 (bld_ca727ba7: a failed founder build left nothing to open): for the founder account only, the
        # best repaired candidate of a build that failed verification/quality is still committed as a DRAFT version,
        # so it can be opened in Preview next to the list of failed checks. The build stays FAILED and nothing is
        # released or billed as ready; customers are unchanged (Golden E2E #1 rule). OMNI_FOUNDER_DRAFT_VERSIONS=0 off.
        founder_draft = (not commit_version and _founder_draft_allowed(request, error_code)
                         and bool(getattr(result, 'repository', None)))
        commit_version = commit_version or founder_draft
        pool = getattr(workspace, 'pool', None)
        if not commit_version:
            version = None
        elif spec_repo is not None and pool is not None:
            with pool.connection() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        version = workspace.commit(project_id=internal_project_id, repository=repo,
                                                   message=_version_message(build_id, founder_draft, gate_waste.get('banner')), cur=cur)
                        spec_repo.save(version_id=version.id, project_id=internal_project_id,
                                       spec=result.spec, cur=cur)
        else:
            version = workspace.commit(project_id=internal_project_id, repository=repo,
                                       message=_version_message(build_id, founder_draft, gate_waste.get('banner')))
        version_id = version.id if version is not None else None
        artifact_key = getattr(version, 'artifact_key', None) if version is not None else None

        spent, calls = spend_snapshot(gateway)
        from .verification_group import kept_failures
        evidence = {
            'gates': {
                # failures: every failure of the kept version, lowest stage first -- what the customer's announcement
                # reads (build_announcement); reported: the report as the repair loop saw it, its summary line kept.
                'verification': {'passed': bool(result.report.passed and result.status == 'ready'),
                                 'failures': [{'acceptance_id': f.acceptance_id, 'message': f.message,
                                               'evidence': f.evidence} for f in kept_failures(result)],
                                 'reported': [{'acceptance_id': f.acceptance_id, 'message': f.message}
                                              for f in result.report.failures]},
                'quality': quality.to_dict(),
                'security': security.to_dict(),
                'rights': rights.to_dict(),
            },
            'release_ready': bool(ready) and not gate_waste['critical_quarantine'],
            'founder_draft_version': bool(founder_draft),
            'build_contract': contract_evidence,
            'capabilities': capability_evidence,
            'infrastructure': infrastructure_evidence,
            'repair_rounds': result.repair_rounds,
            'repair_stop_reason': getattr(result, 'stop_reason', None) or None,
            # DECISIONS 8: every edit the repairer made to a builder's test, and every one it was refused
            'test_edits': (lambda g: g.evidence() if g is not None else None)(
                getattr(getattr(engine, 'core', engine), 'test_edits', None)),
            **taxonomy_evidence(engine, ready=bool(ready and result.report.passed and result.status == 'ready')),
            'build_log_tail': result.report.build_log[-4000:],
            'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
            'provider_usage': provider_usage_evidence(gateway),
            'provider_spend_usd': str(spent), 'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
            'model_budget_binding': model_budget_binding,
            'design_review': {'enabled': bool(design_review_on), 'reviews': _design_reviews(engine)},
            'agentic_repair': {'enabled': bool(agentic_repair),
                               'trace': list(getattr(getattr(engine, 'repairer', None), 'trace', []) or [])[-60:]},
            'llm_cap_overage': llm_cap_overage(request, spent),
            'asset_capabilities': asset_capability_status(capability_plan),
            # Agent OS §11: which skills shaped the build and what QA review found.
            'skills_applied': _skills_applied(),
            'product_review': list(getattr(getattr(engine, 'executor', None), 'reviews', None) or []),
            # Michael 2026-11-10: gates that judged the wrong artefact, and what they cost -- a separate line, never
            # hidden inside the build's cost.
            'gate_waste': gate_waste,
            # Directive 2026-10-09 §17: real-browser flow check ('unavailable' is never read as passed).
            'browser_check': getattr(getattr(engine, 'executor', None), 'last_probe', None),
            # Autonomous completion §1: behavioural acceptance inside the build (last run + every round).
            'behavior_acceptance': behavior_evidence(engine),
            'consistency_gate': consistency_evidence(engine),
            'preview_smoke': preview_smoke_evidence(engine),
            'visual_qa': visual_evidence(engine),
            'site_route': site_content.report(engine),     # the content route: decided, why, and what it did
            'quality_report': quality_report.to_dict() if quality_report is not None else None,
            'round_snapshots': round_snapshots,
            'kept_round': kept_round(engine, result),     # the round whose evidence the stage rows read
            # offscreen.rewrite: every hiding rule the platform rewrote in the generated code ('path:line prop value')
            'offscreen_rewrites': list(getattr(getattr(engine, 'core', engine), 'offscreen_rewrites', None) or [])[:40],
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
        from .build_control import GateEscalation
        escalated = isinstance(exc, GateEscalation)
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.CANCELLED,
            error_code='gate_escalation' if escalated else 'cancelled_by_user', error_message=str(exc)[:500],
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           **({'gate_waste': _gate_waste(engine, None, 0), 'escalation': str(exc)[:500]}
                              if escalated else {}),
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence,
                           'provider_usage': provider_usage_evidence(gateway), **taxonomy_evidence(engine),
                           **_aborted_review_evidence(engine),
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
                           'provider_usage': provider_usage_evidence(gateway), **taxonomy_evidence(engine),
                           **_aborted_review_evidence(engine),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
                           'provider_spend_usd': str(spent), 'external_model_calls': calls,
                           'provider_spend_basis': SPEND_BASIS},
            actual_provider_cost_usd=actual_cost,
        )
        raise
    except CapabilityStageBlocked as exc:
        spent, calls = spend_snapshot(gateway)
        economics_quote = request.get('economics_quote') or {}
        # Lens 11 (2026-11-14): a block raised AFTER the capability stage (the image check) keeps that stage's evidence
        # -- the image was generated and paid for -- and adds its own; a block from the stage itself has only its own.
        blocked_evidence = {**(capability_evidence or {}), **exc.evidence}
        if economics_quote:
            billing, settlement_evidence, actual_cost = resolve_m5_billing(
                subscriptions, build_id=build_id, ready=False, gateway=gateway,
                capability_evidence=blocked_evidence, economics_quote=economics_quote,
            )
        else:
            billing = resolve_billing(subscriptions, build_id=build_id, ready=False, spent=spent, external_calls=calls)
            settlement_evidence, actual_cost = {'action': billing}, spent if billing == 'settled' else None
        jobs.transition(
            build_id=build_id, expected=BuildStatus.RUNNING, target=BuildStatus.FAILED,
            error_code=getattr(exc, 'error_code', 'capability_not_configured'), error_message=str(exc)[:2000],
            result_version_id=version_id, artifact_key=artifact_key,
            evidence_json={'billing': billing, 'economics_quote': economics_quote or None,
                           'economics_settlement': settlement_evidence, 'build_contract': contract_evidence, 'capabilities': blocked_evidence,
                           'provider_usage': provider_usage_evidence(gateway), **taxonomy_evidence(engine),
                           **_aborted_review_evidence(engine),
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
                           'provider_usage': provider_usage_evidence(gateway), **taxonomy_evidence(engine),
                           **_aborted_review_evidence(engine),
                           'model_route_events': [e.__dict__ for e in getattr(gateway, 'events', [])], **rejected_json_evidence(gateway),
                           'provider_spend_usd': str(spent),
                           'external_model_calls': calls, 'provider_spend_basis': SPEND_BASIS,
                           'site_route': _site_route_evidence(engine),
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
    from .skill_units.gate import report as skill_gate_report
    evidence['skill_gates'] = skill_gate_report(engine)       # every gate's mode (OFF included) and result
    from .g_apple import report as apple_gate_report
    evidence['g_apple'] = apple_gate_report(engine)           # the design contract and the gate's findings
    from .runtime_load import report as runtime_load_report
    evidence['runtime_load'] = runtime_load_report(engine)    # G8: the measurement of the last check
    from .app_states import report as app_states_report
    evidence['app_states'] = app_states_report(engine)        # warehouse 130: app or not (and why), the three states
    from .a4 import report as asset_plan_report
    evidence['asset_plan'] = asset_plan_report(engine)        # A4: which image is where, and the placement check
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
    from .build_announcement import FailureWitness, announce_if_failed
    from .conversation.store import PostgresConversationStore, schema_ready
    # warehouse 77c (owner 2026-11-16): a failed build is said in the conversation, with one action
    witness = FailureWitness(jobs)
    try:
        _run_live_build_job(
            build_id,
            jobs=witness,
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
    finally:
        conversation = PostgresConversationStore(_v28_pool) if _v28_pool is not None and schema_ready(_v28_pool) else None
        announce_if_failed(witness, conversation=conversation, request=_safe_request(jobs, build_id), build_id=build_id)


def _safe_request(jobs, build_id):
    try:
        return jobs.get_request(build_id)
    except Exception:
        logging.getLogger(__name__).exception('BUILD_FAILED_NOT_ANNOUNCED build=%s: the job request is unreadable', build_id)
        return None


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
#
# Lineage (2026-11-26). A version has at most ONE origin, so the walk is a single chain and its answer does not depend
# on row order. The first rule that applies names the origin:
#   1. a promoted change (modification_requests.promoted_version_id): the version the change was proposed on
#      (source_version_id). The change was built and judged on that version (execute_modification), also when it was
#      accepted with force on top of another head.
#   2. a restore, a rollback or an undo: the earliest EARLIER version of the SAME project with the SAME
#      repository_sha256. workspace.restore() commits the target's files unchanged and the checksum is computed from
#      the files alone (workspace._checksum), so equal content has an equal value. Which version was restored is not
#      stored anywhere else.
# A version neither rule covers has NO origin and, unless it is itself a build's result, no contract: the strict floor
# applies. parent_id is never followed -- it is the project's head at commit time, not where the content came from.
# The walk ends at the first version that is the result of a build (build_jobs.result_version_id) with a contract of
# this project; that contract gives the scope. 64 steps at most; past that, and for a cycle, there is no contract.
#
# Cost. `contracted` (this project's builds that have a contract) is read once per lookup; it is the last WITH item so
# that the three parameters stay in the caller's order (WITH RECURSIVE lets an earlier item refer to a later one).
# Each step computes its origin once (OFFSET 0 keeps the planner from copying the lateral subquery into both the
# filter and the output) and asks rule 2 only when rule 1 gave nothing. Rule 1 scans modification_requests and rule 2
# scans project_versions: neither has an index for it yet (a migration needs the owner's word). ORDER BY l.depth is a
# second guard: while the walk ends at the first build, only its last row can have a contract.
#
# History. Before #530 only rule 1 existed, so a version made by an undo or a rollback had no contract and a
# content site was judged on the strict floor (verify-replay run 45607249874: v_88812e8a4066448e and
# v_8fd6c2ad3b174200 required auth/role/data_* although their build, bld_c35b8332, was an approved content site).
# Two fixes followed parent_id and were wrong, both found by review:
#   - #530 (merged as 5bcfefe on 2026-11-26; no release had followed it when this replaced it) followed it for every
#     version: a data app restored after a later content-site build of the same project took the content site's
#     contract, with auth, role and data checks waived, and a change accepted with force had two edges at the same
#     depth, so LIMIT 1 picked one arbitrarily;
#   - the next version (never merged) kept it as a last rule: a build commits its version before it records
#     result_version_id (_run_live_build_job: commit, then jobs.transition). A job killed in between (queue timeout,
#     restart, the reaper) leaves a version with no build row, and parent_id lent it the PREVIOUS build's contract --
#     weaker than before #530, when it had none.
_CONTRACT_SCOPE_FOR_VERSION_SQL = """
WITH RECURSIVE lineage(version_id, depth) AS (
    SELECT %s::text, 0
    UNION ALL
    SELECT o.origin, l.depth + 1
    FROM lineage l
    LEFT JOIN project_versions v ON v.id = l.version_id
    CROSS JOIN LATERAL (
        SELECT COALESCE(
            (SELECT min(m.source_version_id) FROM modification_requests m WHERE m.promoted_version_id = l.version_id),
            (SELECT e.id FROM project_versions e
              WHERE e.project_id = v.project_id AND e.repository_sha256 = v.repository_sha256
                AND (e.created_at, e.id) < (v.created_at, v.id)
              ORDER BY e.created_at, e.id LIMIT 1)
        ) AS origin
        WHERE NOT EXISTS (SELECT 1 FROM contracted b WHERE b.version_id = l.version_id)
        OFFSET 0
    ) o
    WHERE l.depth < 64 AND o.origin IS NOT NULL
), contracted(version_id, job_id, contract_id) AS MATERIALIZED (
    SELECT j.result_version_id, j.id, c.id
    FROM build_requests r
    JOIN build_jobs j ON j.id = r.build_id
    JOIN m5_build_contracts c ON c.id = r.build_contract_id
    WHERE r.public_project_id = %s OR r.internal_project_id = %s
)
SELECT c.contract_json->'infrastructure', c.contract_json->'required_integrations',
       c.contract_json->'user_roles', c.contract_json->'defaults_applied', c.contract_json->>'prompt'
FROM lineage l
JOIN contracted b ON b.version_id = l.version_id
JOIN m5_build_contracts c ON c.id = b.contract_id
ORDER BY l.depth, b.job_id
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

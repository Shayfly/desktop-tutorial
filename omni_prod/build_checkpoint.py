"""S4.2 (plan v3): a build whose worker dies continues from its last checkpoint instead of starting over or failing.

The owner, 2026-11-26 10:13 UTC: option (א), continue -- and "את כל העניין של העלות אפשרית לשים בצד כרגע": no exposure or
liability accounting for the call that was in flight at the crash. What the ledger records is counted, nothing more.

Where a checkpoint lives
------------------------
build_jobs.evidence_json -> 'checkpoint' holds the LAST checkpoint of the build: a small, versioned record that names
everything else by durable key and sha256. Not a table, because the record has exactly the lifetime and the readers of
the build's evidence: one worker writes it, only while the build is RUNNING under that worker's recovery epoch
(write_record is fenced on status and recovery_attempts); the janitor decides on it in the same transaction that locks
the build_jobs row (maintenance.recover_lost_running); the worker reads it with the claim; and the terminal evidence
keeps it (CarryEvidence), so the build's record shows which checkpoint it reached. Nothing is migrated.

The bytes go to the build's object storage (the store the round snapshots already use), each object named by its own
content and checked by sha256 when it is read back:
  build-checkpoints/<build>/spec-<sha16>.json            the architect's spec (canonical JSON)
  build-checkpoints/<build>/repo-e<epoch>-<sha16>.zip     the verified repository of the round
  build-checkpoints/<build>/state-<round>-<sha16>.json    the repair loop's state and the verification history

The record (version 1):
  stage            'spec' | 'round' | 'finished'  (autonomous_core.RESUME_STAGES)
  round            repair rounds covered (0 = round 0); None for 'spec'
  spec             {key, sha256 of the bytes, fingerprint of the spec}
  snapshot, state  {key, sha256, ...} for 'round' and 'finished'
  contract_fingerprint, prompt_sha256   what the build was approved with and built from; a resume checks both
  paid_calls       the provider calls of the build that completed so far, as the attempt ledger records them
  resumable        False with `why_not` when the build cannot continue from it (the content route keeps its document in
                   memory): the janitor then does what it did before S4.2, by name
  epoch, worker, written_at (the database's clock)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

from .evidence_json import dumps_evidence

CHECKPOINT_VERSION = 1
KEY_PREFIX = 'build-checkpoints'
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_LOG = logging.getLogger(__name__)
# The calls of a build the record lists one by one (the count and the sum always cover all of them).
MAX_LISTED_CALLS = 60


class CheckpointUnusable(RuntimeError):
    """A recovered build that was requeued to continue cannot: its checkpoint is missing, of another version, does not
    belong to this build's approval or prompt, or its stored bytes do not match the sha256 it recorded. The build fails
    by name (checkpoint_unusable) -- it never starts over in silence, and never continues from bytes it cannot trust."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(json.loads(dumps_evidence(value)), sort_keys=True, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8')


def spec_fingerprint(spec) -> str:
    return sha256_hex(canonical(spec.to_dict()))


def prompt_sha256(prompt: str) -> str:
    return sha256_hex((prompt or '').encode('utf-8'))


def label(record: dict) -> str:
    """How a checkpoint is named in the evidence: 'spec', 'round 2', 'finished after round 3'."""
    stage, rounds = record.get('stage'), record.get('round')
    return 'spec' if stage == 'spec' else (f'round {rounds}' if stage == 'round' else f'finished after round {rounds}')


def usable(record) -> tuple[bool, str]:
    """Whether a build can continue from this record, read from the record alone (the janitor decides on it before any
    byte is read; the worker then checks every byte against its sha256). Never raises: the reason is the answer."""
    if record is None:
        return False, 'no checkpoint was written'
    if not isinstance(record, dict):
        return False, f'the checkpoint is a {type(record).__name__}, not a record'
    if record.get('version') != CHECKPOINT_VERSION:
        return False, f"checkpoint version {record.get('version')!r} is not {CHECKPOINT_VERSION}"
    if record.get('resumable') is not True:
        return False, f"the checkpoint says the build cannot continue from it: {record.get('why_not') or 'no reason'}"
    from .autonomous_core import RESUME_STAGES
    stage = record.get('stage')
    if stage not in RESUME_STAGES:
        return False, f'unknown checkpoint stage {stage!r}'
    spec = record.get('spec') if isinstance(record.get('spec'), dict) else {}
    if not (spec.get('key') and _HEX64.match(str(spec.get('sha256', ''))) and
            _HEX64.match(str(spec.get('fingerprint', '')))):
        return False, 'the checkpoint names no stored spec with its sha256'
    if stage != 'spec':
        rounds = record.get('round')
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 0:
            return False, f'the checkpoint names no round ({rounds!r})'
        for part, fields in (('snapshot', ('sha256', 'zip_sha256')), ('state', ('sha256',))):
            ref = record.get(part) if isinstance(record.get(part), dict) else {}
            if not ref.get('key') or not all(_HEX64.match(str(ref.get(f, ''))) for f in fields):
                return False, f'the checkpoint names no stored {part} with its sha256'
    return True, ''


def not_resumable_reason(engine) -> str:
    """'' when a build on this engine can continue from its checkpoints. The content route (omni_prod/site_content)
    keeps its fact sheet and content document on the engine in memory, set by its generator: a resumed loop would
    repair without them, so its checkpoints say so and a lost content-route build keeps the behaviour of before."""
    from .site_content import on_route
    if on_route(engine):
        return 'the content route (site_content) keeps its content document in the worker\'s memory'
    return ''


# ---------------------------------------------------------------------------------------------------------- database
def read_claim(pool, build_id: str) -> dict:
    """What the worker reads right after it claimed the build: the recovery epoch, the last checkpoint and the
    janitor's recovery record (maintenance.recover_lost_running writes it when it requeues)."""
    with pool.connection() as conn:
        row = conn.execute("SELECT recovery_attempts, evidence_json->'checkpoint', evidence_json->'recovery' "
                           "FROM build_jobs WHERE id = %s", (build_id,)).fetchone()
    if row is None:
        raise KeyError(f'build {build_id} has no job row')
    return {'epoch': int(row[0] or 0), 'checkpoint': row[1], 'recovery': row[2]}


def resume_record(claim: dict | None) -> dict | None:
    """The checkpoint to continue from, or None for a build that starts from the beginning. Only the janitor's
    'resume' decision for THIS recovery attempt continues; a usable-looking checkpoint without it (e.g. a requeue that
    restarted) is not read. A 'resume' decision whose checkpoint is not usable raises CheckpointUnusable."""
    recovery = (claim or {}).get('recovery')
    if not isinstance(recovery, dict) or recovery.get('decision') != 'resume':
        return None
    if recovery.get('recovery_attempt') != claim.get('epoch'):
        raise CheckpointUnusable(f"the recovery record is for recovery attempt {recovery.get('recovery_attempt')!r}; "
                                 f"the build is at attempt {claim.get('epoch')!r}")
    ok, why = usable(claim.get('checkpoint'))
    if not ok:
        raise CheckpointUnusable(f'the janitor requeued the build to continue, but {why}')
    return claim['checkpoint']


def write_record(pool, build_id: str, epoch: int, record: dict) -> dict | None:
    """Store the build's last checkpoint. Fenced: only while the build is RUNNING under this worker's recovery epoch, so
    a worker the janitor gave up on can never overwrite the checkpoint of the worker that continues. Returns the stored
    record (with the database's written_at), or None when this worker no longer owns the build."""
    with pool.connection() as conn:
        with conn.transaction():
            row = conn.execute(
                "UPDATE build_jobs SET evidence_json = jsonb_set(COALESCE(evidence_json, '{}'::jsonb), '{checkpoint}', "
                "%s::jsonb || jsonb_build_object('written_at', now()), true) "
                "WHERE id = %s AND status = 'running' AND recovery_attempts = %s "
                "RETURNING evidence_json->'checkpoint'",
                (dumps_evidence(record), build_id, int(epoch))).fetchone()
    return row[0] if row else None


def completed_paid_calls(pool, build_id: str) -> dict:
    """The provider calls of the build that completed with a cost so far, every worker's, as the ledger records them:
    a refused call (cost 0) is not paid, and the call that is in flight (outcome 'unknown') has not completed."""
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT attempt_id, trace_id, task_type, model, outcome, metered_cost_usd, authorized_cost_usd "
            "FROM task_attempts WHERE build_id = %s AND kind = 'provider_call' AND outcome <> 'unknown' "
            "AND (COALESCE(metered_cost_usd, 0) > 0 OR (metered_cost_usd IS NULL AND COALESCE(authorized_cost_usd, 0) > 0)) "
            "ORDER BY created_at, attempt_seq", (build_id,)).fetchall()
    calls = [{'attempt_id': r[0], 'trace_id': r[1], 'task_type': r[2], 'model': r[3], 'outcome': r[4],
              'metered_cost_usd': None if r[5] is None else str(r[5]),
              'authorized_cost_usd': None if r[6] is None else str(r[6])} for r in rows]
    metered = sum((Decimal(str(r[5])) for r in rows if r[5] is not None), Decimal('0'))
    return {'count': len(calls), 'metered_usd': str(metered), 'unmetered': sum(1 for r in rows if r[5] is None),
            'calls': calls[-MAX_LISTED_CALLS:]}


def recorded_spend(pool, build_id: str) -> dict:
    """What the ledger records of the build's earlier workers: their provider calls and the metered cost of those
    calls. A call without a metered cost (the one in flight at the crash) adds its call and no cost (the owner,
    2026-11-26: count what is recorded, nothing more)."""
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT count(*) FILTER (WHERE COALESCE(authorized_cost_usd, 0) > 0 OR COALESCE(metered_cost_usd, 0) > 0), "
            "COALESCE(sum(metered_cost_usd), 0) FROM task_attempts WHERE build_id = %s AND kind = 'provider_call'",
            (build_id,)).fetchone()
    return {'external_calls': int(row[0] or 0), 'metered_usd': Decimal(str(row[1] or 0))}


def carry_budget(gateway, spend: dict) -> dict:
    """The same model budget for a build that continues: the earlier workers' recorded calls and metered cost count
    against the build's call limit and its reserved budget, which bind_budget set for the whole build."""
    state = getattr(gateway, 'state', None)
    if state is None:
        return {'carried': False, 'why': 'the gateway keeps no budget state'}
    state.external_calls += int(spend['external_calls'])
    state.external_spend_usd += Decimal(str(spend['metered_usd']))
    return {'carried': True, 'external_calls': int(spend['external_calls']), 'metered_usd': str(spend['metered_usd'])}


# ------------------------------------------------------------------------------------------- the verification history
# State an executor of the chain keeps across rounds. The review's history decides later rounds (how many review rounds
# still block, which new finding is downgraded, the quarantine of a probe), as does the design critic's one polish
# round; the other three are the per-round evidence. Read and written as attributes, so the gate code is unchanged.
_CARRIED = (
    ('omni_prod.product_review', 'ProductReviewExecutor', None,
     {'reviews': 'json', 'quarantined': 'json', 'gate_waste_rounds': 'json', 'gate_waste_usd': 'decimal',
      'gate_waste_calls': 'json', '_spend_at_review': 'spend', 'escalate': 'json'}),
    ('omni_prod.visual_qa', 'VisualQAExecutor', 'design_critic', {'reviews': 'json', 'polish_rounds_used': 'json'}),
    ('omni_prod.visual_qa', 'VisualQAExecutor', None, {'visual_rounds': 'json'}),
    ('omni_prod.behavior_acceptance', 'BehaviorAcceptanceExecutor', None, {'history': 'json'}),
    ('omni_prod.consistency_gate', 'ConsistencyGateExecutor', None, {'consistency_rounds': 'json'}),
)


def _targets(engine):
    import importlib
    from .behavior_acceptance import find_in_chain
    chain = getattr(getattr(engine, 'core', engine), 'executor', None)
    for module, cls_name, via, fields in _CARRIED:
        cls = getattr(importlib.import_module(module), cls_name)
        found = find_in_chain(chain, cls)
        if found is not None and via is not None:
            found = getattr(found, via, None)
        yield f'{cls_name}.{via}' if via else cls_name, found, fields


def _dump(kind: str, value):
    if kind == 'decimal':
        return str(value)
    if kind == 'spend':
        return [[str(usd), int(calls)] for usd, calls in value]
    return json.loads(dumps_evidence(value))


def _load(kind: str, value):
    if kind == 'decimal':
        return Decimal(str(value))
    if kind == 'spend':
        return [(Decimal(str(usd)), int(calls)) for usd, calls in value]
    return value


def capture_executors(engine) -> dict:
    out = {}
    for name, target, fields in _targets(engine):
        if target is None:
            continue
        out[name] = {attr: _dump(kind, getattr(target, attr)) for attr, kind in fields.items() if hasattr(target, attr)}
    return out


def restore_executors(engine, saved: dict) -> list[str]:
    """Put the carried history back on the new worker's chain. Returns what could not be restored (named in the
    evidence and logged: a chain without that executor), never a silent drop."""
    missing = []
    targets = {name: (target, fields) for name, target, fields in _targets(engine)}
    for name, values in (saved or {}).items():
        target, fields = targets.get(name, (None, {}))
        if target is None:
            missing.append(name)
            continue
        for attr, value in values.items():
            setattr(target, attr, _load(fields.get(attr, 'json'), value))
    if missing:
        _LOG.warning('CHECKPOINT_HISTORY_NOT_RESTORED %s: the resumed chain has no such executor', ', '.join(missing))
    return missing


# ------------------------------------------------------------------------------------------------------- the writer
class CheckpointWriter:
    """The engine's checkpoint_hook in the worker. Each checkpoint: the bytes to object storage first, then the ledger
    flushed (so it holds every completed call), then the record into build_jobs.evidence_json (fenced). A checkpoint
    that cannot be written is logged and listed in `errors` (the terminal evidence carries it); the build goes on -- the
    previous checkpoint, if any, stays the one a recovery would use."""

    def __init__(self, *, pool, build_id: str, epoch: int, store, zip_repo, contract_fingerprint, prompt: str, engine,
                 round_snapshots: list, flush=None, worker: str | None = None, why_not: str = ''):
        self.pool, self.build_id, self.epoch = pool, build_id, int(epoch)
        self.store, self.zip_repo, self.engine = store, zip_repo, engine
        self.contract_fingerprint = contract_fingerprint
        self.prompt_sha256 = prompt_sha256(prompt)
        self.round_snapshots, self.flush, self.worker, self.why_not = round_snapshots, flush, worker, why_not
        self.last: dict | None = None
        self.errors: list[dict] = []
        self._spec: tuple[str, dict] | None = None
        self._repos: dict[str, dict] = {}

    def _put(self, key: str, data: bytes) -> None:
        try:
            self.store.put_bytes(key, data)
        except Exception:
            # an immutable store refuses a key it has; the same bytes under it are the same object
            existing = self.store.get_bytes(key)
            if sha256_hex(existing) != sha256_hex(data):
                raise

    def _spec_ref(self, spec) -> dict:
        fingerprint = spec_fingerprint(spec)
        if self._spec is None or self._spec[0] != fingerprint:
            data = canonical(spec.to_dict())
            digest = sha256_hex(data)
            key = f'{KEY_PREFIX}/{self.build_id}/spec-{digest[:16]}.json'
            self._put(key, data)
            self._spec = (fingerprint, {'key': key, 'sha256': digest, 'fingerprint': fingerprint})
        return dict(self._spec[1])

    def _snapshot_ref(self, repo: dict) -> dict:
        from .workspace import _checksum
        checksum = _checksum(repo)
        if checksum not in self._repos:
            data = self.zip_repo(repo)
            key = f'{KEY_PREFIX}/{self.build_id}/repo-e{self.epoch}-{checksum[:16]}.zip'
            self._put(key, data)
            self._repos[checksum] = {'key': key, 'sha256': checksum, 'zip_sha256': sha256_hex(data), 'files': len(repo)}
        return dict(self._repos[checksum])

    def record(self, stage: str, payload: dict) -> dict:
        loop = payload.get('loop')
        record = {'version': CHECKPOINT_VERSION, 'stage': stage, 'round': None if loop is None else int(loop['rounds']),
                  'spec': self._spec_ref(payload['spec']), 'contract_fingerprint': self.contract_fingerprint,
                  'prompt_sha256': self.prompt_sha256, 'epoch': self.epoch, 'worker': self.worker,
                  'resumable': not self.why_not, 'why_not': self.why_not or None}
        if stage != 'spec':
            state = {'loop': loop, 'executors': capture_executors(self.engine),
                     'round_snapshots': [dict(e) for e in self.round_snapshots]}
            data = canonical(state)
            digest = sha256_hex(data)
            key = f"{KEY_PREFIX}/{self.build_id}/state-{int(loop['rounds']):02d}-{digest[:16]}.json"
            self._put(key, data)
            record.update(snapshot=self._snapshot_ref(payload['repository']), state={'key': key, 'sha256': digest},
                          report_passed=bool(loop['report']['passed']), stop_reason=loop.get('stop_reason'))
        if self.flush is not None:
            self.flush()                     # the ledger first: the record counts what the ledger holds
        record['paid_calls'] = completed_paid_calls(self.pool, self.build_id)
        return record

    def __call__(self, stage: str, payload: dict) -> None:
        rounds = (payload.get('loop') or {}).get('rounds')
        try:
            stored = write_record(self.pool, self.build_id, self.epoch, self.record(stage, payload))
        except Exception as exc:
            self.errors.append({'stage': stage, 'round': rounds, 'error': f'{type(exc).__name__}: {exc}'[:300]})
            _LOG.warning('CHECKPOINT_NOT_WRITTEN build=%s stage=%s round=%s: %s', self.build_id, stage, rounds, exc)
            return
        if stored is None:
            self.errors.append({'stage': stage, 'round': rounds,
                                'error': 'the build is no longer running under this worker (epoch '
                                         f'{self.epoch}); the checkpoint was not written'})
            _LOG.warning('CHECKPOINT_FENCED build=%s stage=%s epoch=%s', self.build_id, stage, self.epoch)
            return
        self.last = stored


# ------------------------------------------------------------------------------------------------------- the loader
@dataclass(frozen=True)
class Loaded:
    resume: object              # autonomous_core.ResumePoint
    record: dict
    executors: dict
    round_snapshots: list

    def resumed_from(self, **extra) -> dict:
        r = self.record
        return {'checkpoint': label(r), 'stage': r['stage'], 'round': r.get('round'),
                'rounds_spent': r.get('round') or 0,
                'repository_sha256': (r.get('snapshot') or {}).get('sha256'),
                'snapshot_key': (r.get('snapshot') or {}).get('key'),
                'state_sha256': (r.get('state') or {}).get('sha256'),
                'spec_sha256': r['spec']['sha256'], 'spec_fingerprint': r['spec']['fingerprint'],
                'written_at': r.get('written_at'), 'written_by_worker': r.get('worker'), 'written_in_epoch': r.get('epoch'),
                'paid_calls_at_checkpoint': (r.get('paid_calls') or {}).get('count'), **extra}


def _read(store, key: str, sha256: str, what: str) -> bytes:
    try:
        data = store.get_bytes(key)
    except Exception as exc:
        raise CheckpointUnusable(f'the stored {what} {key} could not be read: {type(exc).__name__}: {exc}') from exc
    actual = sha256_hex(data)
    if actual != sha256:
        raise CheckpointUnusable(f'the stored {what} {key} has sha256 {actual}, the checkpoint recorded {sha256}')
    return data


def load(record: dict, *, store, unzip, contract_fingerprint, prompt: str) -> Loaded:
    """Read the checkpoint's bytes back and check each against the sha256 the checkpoint recorded: the spec (bytes and
    fingerprint), the repository archive (bytes, then the repository's own checksum after unzipping) and the loop
    state. Anything that does not match raises CheckpointUnusable."""
    from .autonomous_core import ResumePoint
    from .product_spec import ProductSpec
    from .workspace import _checksum
    ok, why = usable(record)
    if not ok:
        raise CheckpointUnusable(why)
    if store is None or not callable(getattr(store, 'get_bytes', None)):
        raise CheckpointUnusable('this worker has no object storage to read the checkpoint from')
    if record.get('contract_fingerprint') != contract_fingerprint:
        raise CheckpointUnusable(f"the checkpoint is of build contract {record.get('contract_fingerprint')!r}; the "
                                 f'build is bound to {contract_fingerprint!r}')
    if record.get('prompt_sha256') != prompt_sha256(prompt):
        raise CheckpointUnusable('the prompt this worker builds from is not the one the checkpoint was written from '
                                 f"(sha256 {prompt_sha256(prompt)[:16]} vs {str(record.get('prompt_sha256'))[:16]})")
    spec_ref = record['spec']
    raw = _read(store, spec_ref['key'], spec_ref['sha256'], 'spec')
    try:
        spec = ProductSpec.from_dict(json.loads(raw.decode('utf-8')))
    except (ValueError, TypeError, KeyError) as exc:
        raise CheckpointUnusable(f'the stored spec does not parse: {exc}') from exc
    if spec_fingerprint(spec) != spec_ref['fingerprint']:
        raise CheckpointUnusable('the stored spec is not the spec the checkpoint fingerprinted')
    if record['stage'] == 'spec':
        return Loaded(ResumePoint('spec', spec), record, {}, [])
    snap, state_ref = record['snapshot'], record['state']
    archive = _read(store, snap['key'], snap['zip_sha256'], 'repository archive')
    try:
        repo = unzip(archive)
    except Exception as exc:
        raise CheckpointUnusable(f"the stored repository archive {snap['key']} does not unzip: {exc}") from exc
    if _checksum(repo) != snap['sha256']:
        raise CheckpointUnusable(f"the repository in {snap['key']} has checksum {_checksum(repo)}, the checkpoint "
                                 f"recorded {snap['sha256']}")
    try:
        state = json.loads(_read(store, state_ref['key'], state_ref['sha256'], 'loop state').decode('utf-8'))
        resume = ResumePoint(record['stage'], spec, int(record['round']), repo, state['loop'])
    except CheckpointUnusable:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise CheckpointUnusable(f'the stored loop state does not load: {exc}') from exc
    if int(state['loop']['rounds']) != int(record['round']):
        raise CheckpointUnusable(f"the loop state is of round {state['loop']['rounds']}, the record of {record['round']}")
    return Loaded(resume, record, dict(state.get('executors') or {}), list(state.get('round_snapshots') or ()))


# ---------------------------------------------------------------------------------------- the terminal evidence
_TERMINAL = ('ready', 'failed', 'cancelled')


class CarryEvidence:
    """Wraps the jobs repository of one run: the terminal transition's evidence gains the keys `carried()` returns
    (the recovery record and the last checkpoint), whichever path ended the build. Keys the run's own evidence already
    has are left as the run wrote them. Every other call passes through unchanged."""

    def __init__(self, jobs, carried):
        self._jobs = jobs
        self._carried = carried

    def __getattr__(self, name):
        return getattr(self._jobs, name)

    def transition(self, **kw):
        target = getattr(kw.get('target'), 'value', kw.get('target'))
        evidence = kw.get('evidence_json')
        if target in _TERMINAL and isinstance(evidence, dict):
            try:
                extra = {k: v for k, v in (self._carried() or {}).items() if v is not None and k not in evidence}
            except Exception:                          # evidence never blocks a terminal state
                _LOG.warning('carried evidence failed', exc_info=True)
                extra = {}
            if extra:
                kw = {**kw, 'evidence_json': {**evidence, **extra}}
        return self._jobs.transition(**kw)

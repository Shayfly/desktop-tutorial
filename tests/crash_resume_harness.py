"""S4.2 harness: the real build worker, killed for real, on real PostgreSQL, with a scripted model behind the real gateway.

What is real: worker_tasks._run_live_build_job (and around it what execute_live_build_job does: the attempt ledger
written at the end, the agent recorder closed), the AutonomousProductEngine with the real ArchitectAgent,
GeneratorAgent and RepairAgent, the real RoutedModelGateway and OpenAICompatibleGateway (HTTP over loopback), the
write-ahead attempt ledger, PostgresBuildRepository, PostgresSubscriptionService, PostgresProjectWorkspace, the agent
recorder, maintenance.recover_lost_running, and a SIGKILL of the worker process -- nothing of the worker runs after it.

What stands in: the model (ScriptedModel answers each role from the request alone, so a resumed build and an
uninterrupted one get the same answers to the same questions), the sandbox (ProductChecks: a pure function of the
repository -- app.py's VERSION must reach 3), object storage (DirectoryArtifactStore keeps the S3 store's contract:
bytes plus their sha256, refused on read when they changed), and the quality and security scores (passing; they run
after the engine and are not what is tested here).

    python -m tests.crash_resume_harness --worker --database-url URL --build-id ID --model-url URL --store DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import threading
import time
import uuid
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

PROMPT = ('A reading list: add a book with its title and author, see the list, and mark a book as read. '
          'No sign-in. (crash recovery test)')
TARGET_VERSION = 3
SPEC = {'title': 'Reading list', 'summary': 'Add books, list them and mark them as read.', 'stack': ['python'],
        'requirements': [{'id': 'R1', 'text': 'Books can be added, listed and marked as read', 'kind': 'functional'}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': f'app.py reaches VERSION {TARGET_VERSION}'}]}
MODEL = 'scripted-model'
LLM_BUDGET = Decimal('1.00')


class DirectoryArtifactStore:
    """Object storage on a directory with S3ArtifactStore's contract (omni_prod/storage.py): put_bytes keeps the bytes
    and their sha256; get_bytes(verify=True) raises ArtifactIntegrityError when the bytes no longer match it."""

    def __init__(self, root):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        if key.startswith('/') or '..' in Path(key).parts:
            raise ValueError(f'unsafe key {key!r}')
        return self.root / key

    def put_bytes(self, key: str, data: bytes):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(data))
        path.with_name(path.name + '.sha256').write_text(hashlib.sha256(data).hexdigest())
        return SimpleNamespace(key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))

    def get_bytes(self, key: str, *, verify: bool = True) -> bytes:
        from omni_prod.storage import ArtifactIntegrityError
        path = self._path(key)
        data = path.read_bytes()
        if verify and hashlib.sha256(data).hexdigest() != path.with_name(path.name + '.sha256').read_text().strip():
            raise ArtifactIntegrityError(f'checksum mismatch for {key}')
        return data


def roles() -> dict:
    from omni_prod import autonomous_agents as agents
    return {agents._ARCHITECT_SYSTEM: 'architect', agents._GENERATOR_SYSTEM: 'generator', agents._REPAIR_SYSTEM: 'repair'}


def answer(role: str, user: str) -> dict:
    """What the scripted model returns, from the request alone: the same question always gets the same answer."""
    if role == 'architect':
        return SPEC
    if role == 'generator':
        return {'files': [{'path': 'app.py', 'content': 'VERSION = 0\n'}]}
    if role == 'repair':
        failures = json.loads(user).get('failures') or []
        for f in failures:
            m = re.search(r'VERSION is (\d+)', str(f.get('message', '')))
            if m:
                return {'files': [{'path': 'app.py', 'content': f'VERSION = {int(m.group(1)) + 1}\n'}]}
        return {'files': [{'path': 'app.py', 'content': 'VERSION = 0\n'}]}
    return {}


class ScriptedModel:
    """An OpenAI-compatible model on 127.0.0.1. Every request is recorded with its role (the counts are the calls on
    the real gateway seam); `kill_on = (role, n)` SIGKILLs the worker when the n-th request of that role arrives, so the
    worker dies with that call in flight -- its write-ahead ledger row stays without an answer."""

    def __init__(self):
        self.lock = threading.Lock()
        self.calls: list[tuple[str, int | None]] = []
        self.kill_on: tuple[str, int] | None = None
        self.worker_pid: int | None = None
        self.killed: list[tuple[str, int]] = []
        self._roles = roles()
        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                messages = body.get('messages') or []
                system = next((m['content'] for m in messages if m.get('role') == 'system'), '')
                user = next((m['content'] for m in messages if m.get('role') == 'user'), '')
                role = model._roles.get(system, 'other')
                with model.lock:
                    model.calls.append((role, model.worker_pid))
                    n = sum(1 for r, _ in model.calls if r == role)
                    kill = model.kill_on == (role, n) and model.worker_pid
                    if kill:
                        model.killed.append((role, n))
                if kill:
                    os.kill(model.worker_pid, signal.SIGKILL)
                    self.close_connection = True
                    return
                text = json.dumps(answer(role, user))
                payload = json.dumps({'id': f'resp_{uuid.uuid4().hex[:12]}', 'model': MODEL,
                                      'choices': [{'index': 0, 'finish_reason': 'stop',
                                                   'message': {'role': 'assistant', 'content': text}}],
                                      'usage': {'prompt_tokens': len(user) // 4 + 10,
                                                'completion_tokens': len(text) // 4 + 5}}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f'http://127.0.0.1:{self.server.server_port}/v1'

    def reset(self, kill_on=None):
        with self.lock:
            self.calls, self.kill_on, self.worker_pid, self.killed = [], kill_on, None, []

    def count(self, pid: int | None = None) -> dict:
        with self.lock:
            out: dict[str, int] = {}
            for role, who in self.calls:
                if pid is None or who == pid:
                    out[role] = out.get(role, 0) + 1
        return out

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def scripted_gateway(model_url: str):
    """The production gateway class with one catalog model behind it (priced, so every call is metered)."""
    from omni_prod.model_catalog import CatalogModel
    from omni_prod.model_gateway import ModelEndpoint
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.model_router import ModelOption, RoutingPolicy
    from omni_prod.routed_gateway import RoutedModelGateway
    model = CatalogModel(endpoint=ModelEndpoint(name=MODEL, base_url=model_url, model=MODEL, api_key='test-fixture-only',
                                                external=True, timeout_seconds=60),
                         option=ModelOption('scripted', MODEL, 90, 100, Decimal('1.00'), Decimal('2.00')),
                         max_output_tokens=65536, api_key_env='SCRIPTED_KEY')
    return RoutedModelGateway(ranked=(model,), routing_policy=RoutingPolicy(minimum_quality=0, prefer_cost=True),
                              policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                    external_budget_usd=LLM_BUDGET, max_external_calls_per_build=40),
                              transient_retries=0, sleep=lambda s: None)


class ProductChecks:
    """The sandbox's place: a pure function of the repository. app.py's VERSION must reach TARGET_VERSION; a lower one
    fails A1 with a message that names it (so each round fails differently and the loop goes on). `kill_on_version`:
    when that version is verified, write `marker` and wait -- the test kills the worker in the middle of the round."""

    def __init__(self, kill_on_version: int | None = None, marker: str | None = None):
        self.kill_on_version, self.marker = kill_on_version, marker

    def execute(self, *, repository, spec):
        from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
        m = re.search(r'VERSION = (\d+)', repository.get('app.py', ''))
        version = int(m.group(1)) if m else -1
        if self.kill_on_version is not None and version == self.kill_on_version:
            Path(self.marker).write_text(str(os.getpid()))
            time.sleep(120)
        if version >= TARGET_VERSION:
            return ExecutionReport(True, (), f'version {version}: all checks passed', 1)
        return ExecutionReport(False, (AcceptanceFailure('A1', f'VERSION is {version}; the reading list needs version '
                                                               f'{TARGET_VERSION}', f'app.py: VERSION = {version}'),),
                               f'version {version}', 1)


def create_build(pool, *, prompt: str = PROMPT) -> str:
    """One build as the API admits it: account, plan, reservation, request and QUEUED job (with its quote)."""
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.subscription_store import PostgresSubscriptionService
    case = uuid.uuid4().hex[:12]
    build_id, account, project = f'bld_crash_{case}', f'usr_crash_{case}', f'prj_crash_{case}'
    subs, jobs = PostgresSubscriptionService(pool=pool), PostgresBuildRepository(pool)
    with pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
        cur.execute("INSERT INTO creator_accounts(id, email, password_hash, salt_b64, created_at) "
                    "VALUES (%s, %s, 'fixture', 'eA==', now())", (account, account + '@example.invalid'))
        cur.execute("INSERT INTO creator_subscriptions(user_id, plan_code, cycle, credits_used, provider_spend_usd) "
                    "VALUES (%s, 'pro', to_char(now(), 'YYYY-MM'), 0, 0)", (account,))
        decision = subs.reserve(cur, build_id=build_id, user_id=account, project_id=project, cost_class='standard',
                                credits=10, estimated_provider_cost_usd=LLM_BUDGET)
        if not decision.allowed:
            raise AssertionError(f'reservation refused: {decision.reason}')
        jobs.create_request(cur, build_id=build_id, user_id=account, internal_project_id=project, prompt=prompt,
                            target_markets=('US',), branding_visible=True, white_label_name=None, rights_evidence=[],
                            public_project_id=f'prj_pub_{case}')
        jobs.create_with_cursor(cur, build_id=build_id, project_id=project, version_id='pending',
                                evidence_json={'economics_quote': {'components': {'llm_maximum_usd': str(LLM_BUDGET)}}},
                                estimated_provider_cost_usd=LLM_BUDGET)
    return build_id


def worker_env(base=None) -> dict:
    """The worker's environment: none of the caller's OMNI_ settings, loopback never through a proxy, and the release
    policy in shadow (it would refuse READY because preview/browser/behaviour never ran here; it is not tested here)."""
    env = {k: v for k, v in (base or os.environ).items()
           if not k.startswith(('OMNI_', 'OPENAI_', 'OPENROUTER_', 'ANTHROPIC_', 'M5_', 'M4D2_', 'GEMINI_'))}
    env.update(OMNI_RELEASE_POLICY='shadow', OMNI_AGENTIC_REPAIR='0', OMNI_DESIGN_REVIEW='0',
               NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
    return env


def _passing(**fields):
    data = {'passed': True, **fields}
    return SimpleNamespace(passed=True, to_dict=lambda: dict(data), **fields)


def worker(args) -> int:
    """What execute_live_build_job does, with the scripted model and the pure checks in place of _live_components."""
    from omni_prod.agent_os.recorder import recorder_for
    from omni_prod.attempt_ledger import RecordingExecutor, TaskTaggedGateway
    from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
    from omni_prod.autonomous_core import AutonomousProductEngine
    from omni_prod.db import DatabasePool
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.subscription_store import PostgresSubscriptionService
    from omni_prod.v28_platform import V28Platform
    from omni_prod.worker_tasks import _persist_build_attempts, _run_live_build_job
    from omni_prod.workspace import PostgresProjectWorkspace
    pool = DatabasePool(args.database_url, min_size=1, max_size=4).open()
    gateway = scripted_gateway(args.model_url)
    checks = ProductChecks(args.kill_on_version, args.marker)
    engine = AutonomousProductEngine(
        architect=ArchitectAgent(TaskTaggedGateway(gateway, 'architecture')),
        generator=GeneratorAgent(TaskTaggedGateway(gateway, 'codegen')),
        repairer=RepairAgent(TaskTaggedGateway(gateway, 'repair')),
        executor=RecordingExecutor(checks, gateway.recorder), max_repair_rounds=6, repair_ceiling=6)
    engine.no_progress_retries = 1                       # as _live_components
    jobs = PostgresBuildRepository(pool)
    platform = V28Platform(token_secret='crash-resume-harness-' + 'x' * 32,
                           subscription_service=PostgresSubscriptionService(pool=pool))
    recorder = recorder_for(pool, args.build_id, None)
    outcome = None
    try:
        outcome = _run_live_build_job(
            args.build_id, jobs=jobs, platform=platform,
            workspace=PostgresProjectWorkspace(pool, DirectoryArtifactStore(args.store)),
            components_factory=lambda: (engine, gateway),
            quality_fn=lambda **kw: _passing(score=100, minimum_score=80, blockers=()),
            security_fn=lambda repo: _passing(findings=()),
            agent_recorder=recorder, attempt_pool=pool)
    except Exception as exc:
        print(f'WORKER_RAISED {type(exc).__name__}: {exc}', flush=True)
    finally:
        _persist_build_attempts(pool, jobs, args.build_id, gateway)
        if recorder.run_id is not None:
            with pool.connection() as conn:
                row = conn.execute('SELECT status, evidence_json FROM build_jobs WHERE id = %s',
                                   (args.build_id,)).fetchone()
            recorder.finish(status=row[0] if row else 'failed', evidence=row[1] if row else None)
        pool.close()
    print(f'WORKER_DONE {outcome}', flush=True)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--worker', action='store_true', required=True)
    p.add_argument('--database-url', required=True)
    p.add_argument('--build-id', required=True)
    p.add_argument('--model-url', required=True)
    p.add_argument('--store', required=True)
    p.add_argument('--kill-on-version', type=int, default=None)
    p.add_argument('--marker', default=None)
    return worker(p.parse_args(argv))


if __name__ == '__main__':
    raise SystemExit(main())

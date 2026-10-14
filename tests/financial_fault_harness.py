"""Isolated financial failure experiment; never calls a commercial provider.

Uses the production build worker, reservation service, attempt persistence and
maintenance with real PostgreSQL, a loopback HTTP provider and killed processes.
Queue delivery is a controlled callback, not a claim of deployed Redis/RQ E2E.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.parse import urlsplit

import psycopg

BASE_SOURCE_SHA = 'e0feac91d181605fac57aeea830c02f883501059'
PROVIDER_COST = Decimal('0.02')
RESERVATION = Decimal('0.10')


def validate_database(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('experiment requires a loopback PostgreSQL endpoint')
    if not parsed.path.lstrip('/').startswith('fault_'):
        raise ValueError('experiment database name must start with fault_')
    with psycopg.connect(url, connect_timeout=5) as conn:
        marker = conn.execute("SELECT to_regclass('financial_fault_database_marker')").fetchone()[0]
        if not marker or conn.execute('SELECT source_sha FROM financial_fault_database_marker').fetchall() != [(BASE_SOURCE_SHA,)]:
            raise ValueError('experiment requires its disposable-database ownership marker')
        if conn.execute("SELECT count(*) FROM build_jobs WHERE id NOT LIKE 'bld_fault_%'").fetchone()[0]:
            raise ValueError('non-experiment builds present; maintenance is forbidden')
        if conn.execute('SELECT count(*) FROM modification_requests').fetchone()[0] or conn.execute('SELECT count(*) FROM project_previews').fetchone()[0]:
            raise ValueError('non-experiment modification/preview rows present')


def wait_for(predicate, *, timeout: float = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise TimeoutError('experiment transition was not observed before deadline')


def worker(url: str, build_id: str, provider_url: str) -> None:
    validate_database(url)
    if urlsplit(provider_url).hostname != '127.0.0.1':
        raise ValueError('fake provider must use the IPv4 loopback endpoint')
    from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
    from omni_prod.autonomous_core import AutonomousProductEngine
    from omni_prod.db import DatabasePool
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.model_gateway import ModelEndpoint
    from omni_prod.model_policy import ModelUsePolicy
    from omni_prod.rights_ip import RightsEngine
    from omni_prod.routed_gateway import ProviderRoute, RoutedModelGateway
    from omni_prod.subscription_store import PostgresSubscriptionService
    from omni_prod.universal_brain import OmniUniversalBrain
    from omni_prod.worker_tasks import _run_live_build_job
    from omni_prod.workspace import PostgresProjectWorkspace

    class UnreachableExecutor:
        def execute(self, **kwargs):
            raise AssertionError('provider response must not reach code execution')

    pool = DatabasePool(url, min_size=1, max_size=4).open()
    gateway = RoutedModelGateway(
        fallback=(ProviderRoute(ModelEndpoint('fault-loopback', provider_url, 'fault-model',
                                             api_key='test-fixture-only', external=True,
                                             timeout_seconds=90), Decimal('0.05')),),
        policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                              external_budget_usd=RESERVATION, max_external_calls_per_build=2),
        transient_retries=0,
    )
    engine = AutonomousProductEngine(architect=ArchitectAgent(gateway),
                                     generator=GeneratorAgent(gateway), repairer=RepairAgent(gateway),
                                     executor=UnreachableExecutor(), max_repair_rounds=0)
    platform = SimpleNamespace(subscriptions=PostgresSubscriptionService(pool=pool),
                               brain=OmniUniversalBrain(), rights=RightsEngine())
    _run_live_build_job(build_id, jobs=PostgresBuildRepository(pool), platform=platform,
                       workspace=PostgresProjectWorkspace(pool, None),
                       components_factory=lambda: (engine, gateway),
                       quality_fn=lambda **kwargs: (_ for _ in ()).throw(AssertionError('unreachable quality')),
                       security_fn=lambda *args: (_ for _ in ()).throw(AssertionError('unreachable security')),
                       attempt_pool=pool)


def run_case(url: str, output: Path, *, fail_ledger: bool, expect_prevention: bool = False) -> dict:
    validate_database(url)
    from omni_prod import maintenance
    from omni_prod.db import DatabasePool
    from omni_prod.job_repository import PostgresBuildRepository
    from omni_prod.preview_repository import PostgresPreviewRepository
    from omni_prod.subscription_store import PostgresSubscriptionService

    case_id = uuid.uuid4().hex[:12]
    build_id, account, project = 'bld_fault_' + case_id, 'usr_fault_' + case_id, 'prj_fault_' + case_id
    journal = output / (case_id + '-provider.sqlite')
    with sqlite3.connect(journal) as conn:
        conn.execute('CREATE TABLE charges (request_id TEXT PRIMARY KEY, build_id TEXT, cost TEXT, received_at REAL)')
    stop_response = threading.Event()

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            if self.path != '/v1/chat/completions':
                self.send_error(404)
                return
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            if body.get('model') != 'fault-model' or not body.get('messages'):
                self.send_error(400)
                return
            with sqlite3.connect(journal) as conn:
                conn.execute('INSERT INTO charges VALUES (?, ?, ?, ?)',
                             ('req_' + uuid.uuid4().hex, build_id, str(PROVIDER_COST), time.time()))
            # Receipt/cost is committed independently before a response exists.
            stop_response.wait(60)
            self.close_connection = True

    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    server.daemon_threads = True
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    pool = DatabasePool(url, min_size=1, max_size=4).open()
    jobs, subs = PostgresBuildRepository(pool), PostgresSubscriptionService(pool=pool)
    children = []
    deliveries = []
    recoveries = []
    snapshots = []

    def provider_rows():
        with sqlite3.connect(journal) as conn:
            return conn.execute('SELECT request_id, cost, received_at FROM charges ORDER BY received_at').fetchall()

    def snapshot():
        with pool.connection() as conn:
            reservation = conn.execute('SELECT status, estimated_provider_cost_usd, actual_provider_cost_usd, '
                                       'settled_provider_cost_usd, credits_reserved '
                                       'FROM credit_reservations WHERE build_id=%s', (build_id,)).fetchone()
            balance = conn.execute('SELECT credits_used, provider_spend_usd FROM creator_subscriptions '
                                   'WHERE user_id=%s', (account,)).fetchone()
            job = conn.execute('SELECT status, recovery_attempts, error_code FROM build_jobs WHERE id=%s', (build_id,)).fetchone()
            attempts = conn.execute('SELECT outcome, authorized_cost_usd, metered_cost_usd FROM task_attempts '
                                    'WHERE build_id=%s', (build_id,)).fetchall()
        return {'reservation': list(reservation), 'balance': list(balance), 'job': list(job),
                'attempts': [list(x) for x in attempts], 'provider_requests': len(provider_rows())}

    try:
        with pool.connection() as conn, conn.transaction(), conn.cursor() as cur:
            cur.execute("INSERT INTO creator_accounts(id,email,password_hash,salt_b64,created_at) "
                        "VALUES (%s,%s,'fixture','eA==',now())", (account, account + '@example.invalid'))
            cur.execute("INSERT INTO creator_subscriptions(user_id,plan_code,cycle,credits_used,provider_spend_usd) "
                        "VALUES (%s,'basic',to_char(now(),'YYYY-MM'),0,0)", (account,))
            decision = subs.reserve(cur, build_id=build_id, user_id=account, project_id=project,
                                    cost_class='standard', credits=10, estimated_provider_cost_usd=RESERVATION)
            if not decision.allowed:
                raise AssertionError(decision.reason)
            jobs.create_request(cur, build_id=build_id, user_id=account, internal_project_id=project,
                                prompt='Build a simple Hebrew task list', target_markets=('IL',),
                                branding_visible=True, white_label_name=None, rights_evidence=[])
            jobs.create_with_cursor(cur, build_id=build_id, project_id=project, version_id='pending',
                                    evidence_json={'economics_quote': {'components': {'llm_maximum_usd': '0.10'}}},
                                    estimated_provider_cost_usd=RESERVATION)
            jobs.create_outbox(cur, build_id=build_id)
            if fail_ledger:
                from psycopg import sql
                fn = 'fault_reject_' + case_id
                cur.execute(sql.SQL("CREATE FUNCTION {}() RETURNS trigger LANGUAGE plpgsql AS $$ "
                                    "BEGIN IF NEW.build_id = {} THEN RAISE EXCEPTION 'fault_injected_attempt_write'; "
                                    "END IF; RETURN NEW; END $$").format(sql.Identifier(fn), sql.Literal(build_id)))
                cur.execute(sql.SQL('CREATE TRIGGER {} BEFORE INSERT OR UPDATE ON task_attempts '
                                    'FOR EACH ROW EXECUTE FUNCTION {}()').format(sql.Identifier(fn), sql.Identifier(fn)))
        snapshots.append(snapshot())
        for index in range(2):
            if index == 1 and not deliveries:
                break  # A safe UNKNOWN quarantine must be allowed to pass.
            log_path = output / (case_id + '-worker-' + str(index) + '.log')
            with log_path.open('w', encoding='utf-8') as log:
                env = {k: v for k, v in os.environ.items()
                       if not k.startswith(('OMNI_', 'OPENAI_', 'OPENROUTER_', 'ANTHROPIC_', 'M5_', 'M4D2_'))}
                child = subprocess.Popen([sys.executable, '-m', 'tests.financial_fault_harness', '--worker',
                                          '--database-url', url, '--build-id', build_id,
                                          '--provider-url', f'http://127.0.0.1:{server.server_port}/v1'],
                                         stdout=log, stderr=log, env=env)
                children.append(child)
                wait_for(lambda: len(provider_rows()) >= index + 1 or child.poll() is not None)
                if index == 0 and child.poll() is not None and not expect_prevention:
                    raise AssertionError('charge-then-crash window was not exercised; worker stopped before first receipt: '
                                         + log_path.read_text(encoding='utf-8'))
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)
            if fail_ledger and index == 0 and 'fault_injected_attempt_write' not in log_path.read_text(encoding='utf-8'):
                raise AssertionError('the database write fault was not exercised')
            snapshots.append(snapshot())
            with pool.connection() as conn, conn.transaction():
                conn.execute("UPDATE build_jobs SET heartbeat_at=now()-interval '20 minutes' WHERE id=%s AND status='running'", (build_id,))
            recovery = maintenance.run_once(pool=pool, preview_repo=PostgresPreviewRepository(pool),
                                            jobs=jobs, subscriptions=subs,
                                            stop_preview=lambda pid: (_ for _ in ()).throw(AssertionError('unexpected preview')),
                                            runtime_host='fault-test-only', queued_ids=lambda: (),
                                            enqueue=lambda function, bid: deliveries.append((function, bid)),
                                            busy_ids=lambda: ())
            if recovery['errors']:
                raise AssertionError(recovery['errors'])
            recoveries.append(recovery)
            snapshots.append(snapshot())
            if len(deliveries) > 1 or any(x != (maintenance.BUILD_JOB, build_id) for x in deliveries):
                raise AssertionError('unexpected or repeated recovery delivery')
        final = snapshot()
        if expect_prevention and not provider_rows() and final['job'][2] != 'attempt_ledger_unavailable':
            raise AssertionError('no dispatch, but the financial journal guard was not the stopping reason')
        cost = sum((Decimal(row[1]) for row in provider_rows()), Decimal('0'))
        held = Decimal(str(final['balance'][1]))
        status, quoted, actual, settled, reserved_credits = final['reservation']
        unknown = sum((Decimal(str(a[1])) for a in final['attempts']
                       if a[0] == 'unknown' and a[1] is not None and a[2] is None), Decimal('0'))
        reconciled = actual is not None and Decimal(str(actual)) == cost and status == 'SETTLED'
        exposed = actual is None and unknown >= cost and status in {'RESERVED', 'SETTLED'}
        expected_held = (Decimal('0') if status == 'RELEASED' else
                         Decimal(str(quoted)) if status == 'RESERVED' else Decimal(str(settled)))
        expected_credits = 0 if status == 'RELEASED' else reserved_credits
        checks = {'no_uncontrolled_provider_replay': len(provider_rows()) <= 1,
                  'exposure_unknown_or_reconciled': cost == 0 or exposed or reconciled,
                  'reservation_not_released_as_free': cost == 0 or status != 'RELEASED',
                  'balance_matches_provider_liability': held == expected_held and held >= cost
                      and final['balance'][0] == expected_credits}
        return {'case': 'journal_guard_prevention' if expect_prevention else
                       'ledger_write_failure' if fail_ledger else 'durable_ledger_control',
                'window': 'pre-dispatch journal guard' if expect_prevention else 'provider receipt then worker crash',
                'source_sha': BASE_SOURCE_SHA, 'build_id': build_id,
                'provider_cost_usd': str(cost), 'provider_requests': len(provider_rows()),
                'worker_exit_codes': [p.returncode for p in children], 'deliveries': deliveries,
                'snapshots': snapshots, 'recoveries': recoveries, 'final': final,
                'checks': checks, 'verdict': 'PASS' if all(checks.values()) else 'FAIL',
                'boundary': 'real PostgreSQL/HTTP/build worker/maintenance; controlled queue delivery; no Redis/RQ or sandbox E2E'}
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=10)
        stop_response.set()
        server.shutdown()
        server.server_close()
        pool.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--database-url', required=True)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--build-id')
    parser.add_argument('--provider-url')
    parser.add_argument('--output-dir', type=Path, default=Path('work/financial-fault-evidence'))
    args = parser.parse_args()
    if args.worker:
        worker(args.database_url, args.build_id, args.provider_url)
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = [run_case(args.database_url, args.output_dir, fail_ledger=value) for value in (False, True)]
    result = {'source_sha': BASE_SOURCE_SHA, 'cases': cases,
              'verdict': 'PASS' if all(c['verdict'] == 'PASS' for c in cases) else 'FAIL'}
    (args.output_dir / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())

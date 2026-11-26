"""S4.2 on real PostgreSQL with a real kill: the build worker is SIGKILLed at four points, the janitor decides, and a
second worker continues from the last checkpoint (the owner chose to continue, 2026-11-26 10:13 UTC).

Kill points (tests/crash_resume_harness.py runs the real worker in its own process; the scripted model or the checks
kill it, so nothing of the worker runs after the kill):
  before any checkpoint   during the architect's call          -> no checkpoint: FAILED provider_liability_unknown
  after the spec          during the generator's call          -> continues from 'spec'
  after round 0           during the first repair call          -> continues from 'round 0'
  in a repair round       while round 2 is being verified       -> continues from 'round 1' (repair 2 is made again)
Each continued build must end as the uninterrupted one did, never call the architect again (nor the generator after
round 0), name its checkpoint in evidence_json.recovery.resumed_from, carry the lost worker's finished agent tasks, and
pass postdeploy_checks.resume_verdict -- which still fails the real ledger of run 37955419872 (started over).

Runs in intake-budget-pg (M4D2_DATABASE_URL); every test class creates and drops its own database.
Mutations: tests/negative_controls/crash_resume.json.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from decimal import Decimal

DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
ROOT = pathlib.Path(__file__).resolve().parents[1]


class Database:
    """One throw-away database with every migration of the repository."""

    def __init__(self, prefix: str):
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        self.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        self.name = f'{prefix}_{uuid.uuid4().hex[:10]}'
        self.admin.execute(f'CREATE DATABASE {self.name}')
        self.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + self.name
        with psycopg.connect(self.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        self.pool = DatabasePool(self.url)

    def close(self):
        self.pool.close()
        self.admin.execute(f'DROP DATABASE IF EXISTS {self.name} WITH (FORCE)')
        self.admin.close()

    def one(self, sql, *args):
        with self.pool.connection() as conn:
            return conn.execute(sql, args).fetchone()

    def all(self, sql, *args):
        with self.pool.connection() as conn:
            return conn.execute(sql, args).fetchall()


def janitor(pool):
    from omni_prod import maintenance
    from omni_prod.subscription_store import PostgresSubscriptionService
    sent = []
    out = maintenance.recover_lost_running(pool, subscriptions=PostgresSubscriptionService(pool=pool),
                                           enqueue=lambda f, i: sent.append((f, i)), busy_ids=lambda: [], minutes=0)
    return out, sent


class KilledWorkersContinue(unittest.TestCase):
    """The five builds run once for the class (each is two worker processes); the tests read what they left."""

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        from tests import crash_resume_harness as H
        cls.H = H
        cls.db = Database('crash')
        cls.model = H.ScriptedModel()
        cls.store = tempfile.mkdtemp(prefix='crash-store-')
        cls.runs = {}
        try:
            cls.runs['uninterrupted'] = cls.scenario()
            cls.runs['before any checkpoint'] = cls.scenario(kill_on=('architect', 1))
            cls.runs['after the spec'] = cls.scenario(kill_on=('generator', 1))
            cls.runs['after round 0'] = cls.scenario(kill_on=('repair', 1))
            cls.runs['in a repair round'] = cls.scenario(kill_on_version=2)
            cls.runs['tampered checkpoint'] = cls.scenario(kill_on=('repair', 1), tamper='state')
        except BaseException:
            cls.tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        model, db = getattr(cls, 'model', None), getattr(cls, 'db', None)
        if model is not None:
            model.close()
        if db is not None:
            db.close()
        shutil.rmtree(getattr(cls, 'store', '') or '/nonexistent', ignore_errors=True)

    @classmethod
    def worker(cls, build_id: str, *, kill_on=None, kill_on_version=None) -> dict:
        marker = os.path.join(cls.store, f'marker-{uuid.uuid4().hex[:8]}')
        cmd = [sys.executable, '-m', 'tests.crash_resume_harness', '--worker', '--database-url', cls.db.url,
               '--build-id', build_id, '--model-url', cls.model.url, '--store', cls.store]
        if kill_on_version is not None:
            cmd += ['--kill-on-version', str(kill_on_version), '--marker', marker]
        env = cls.H.worker_env()
        env['PYTHONPATH'] = os.pathsep.join(p for p in (str(ROOT), os.environ.get('PYTHONPATH', '')) if p)
        cls.model.reset(kill_on=kill_on)
        proc = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        cls.model.worker_pid = proc.pid
        if kill_on_version is not None:
            deadline = time.monotonic() + 120
            while not os.path.exists(marker) and proc.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            if os.path.exists(marker):
                os.kill(proc.pid, signal.SIGKILL)
        try:
            out, _ = proc.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            raise AssertionError(f'worker for {build_id} did not end: {out[-2000:]}')
        return {'pid': proc.pid, 'returncode': proc.returncode, 'output': out, 'calls': cls.model.count(proc.pid),
                'killed': list(cls.model.killed) or (['verify'] if kill_on_version is not None else [])}

    @classmethod
    def scenario(cls, *, kill_on=None, kill_on_version=None, tamper=None) -> dict:
        build_id = cls.H.create_build(cls.db.pool)
        run = {'build_id': build_id, 'first': cls.worker(build_id, kill_on=kill_on, kill_on_version=kill_on_version)}
        if kill_on or kill_on_version is not None:
            run['checkpoint_at_kill'] = cls.db.one("SELECT evidence_json->'checkpoint' FROM build_jobs WHERE id=%s",
                                                   build_id)[0]
            if tamper:
                key = run['checkpoint_at_kill'][tamper]['key']
                path = pathlib.Path(cls.store) / key
                data = path.read_bytes().replace(b'"rounds":0', b'"rounds":0 ')
                path.write_bytes(data)                                      # the store's own sha256 updated too:
                path.with_name(path.name + '.sha256').write_text(__import__('hashlib').sha256(data).hexdigest())
            run['janitor'], run['enqueued'] = janitor(cls.db.pool)
            if any(i == build_id for _, i in run['enqueued']):
                run['second'] = cls.worker(build_id)
        row = cls.db.one('SELECT status, error_code, error_message, repair_rounds, recovery_attempts, evidence_json '
                         'FROM build_jobs WHERE id = %s', build_id)
        run.update(status=row[0], error_code=row[1], error_message=row[2], repair_rounds=row[3], recovery_attempts=row[4],
                   evidence=row[5] or {})
        run['attempts'] = cls.db.all("SELECT trace_id, attempt_seq, task_type, outcome, created_at FROM task_attempts "
                                     "WHERE build_id = %s AND kind = 'provider_call' ORDER BY created_at, attempt_seq",
                                     build_id)
        run['events'] = [r[0] for r in cls.db.all("SELECT message FROM build_events WHERE build_id = %s AND kind = 'info' "
                                                  "ORDER BY seq", build_id)]
        run['runs'] = cls.db.all('SELECT id, outcome FROM agent_runs WHERE subject_id = %s ORDER BY created_at', build_id)
        run['reservation'] = cls.db.one('SELECT status FROM credit_reservations WHERE build_id = %s', build_id)[0]
        return run

    # ------------------------------------------------------------------------------------------------- the result
    def result(self, run) -> dict:
        ev = run['evidence']
        return {'status': run['status'], 'repair_rounds': run['repair_rounds'], 'stop': ev.get('repair_stop_reason'),
                'verification': (ev.get('gates') or {}).get('verification'),
                'final_repository': ((ev.get('checkpoint') or {}).get('snapshot') or {}).get('sha256'),
                'rounds': [(s['round'], s['decision'], s['sha256'], s['failing']) for s in ev.get('round_snapshots') or []]}

    def test_the_uninterrupted_build_is_the_reference(self):
        run = self.runs['uninterrupted']
        self.assertEqual((run['status'], run['repair_rounds']), ('ready', 3), run['first']['output'][-1500:])
        self.assertEqual(run['first']['calls'], {'architect': 1, 'generator': 1, 'repair': 3})
        self.assertEqual((run['evidence']['checkpoint']['stage'], run['evidence']['checkpoint']['round']), ('finished', 3))
        self.assertNotIn('recovery', run['evidence'])

    def test_each_continued_build_ends_as_the_uninterrupted_one(self):
        reference = self.result(self.runs['uninterrupted'])
        for name in ('after the spec', 'after round 0', 'in a repair round'):
            with self.subTest(name):
                run = self.runs[name]
                self.assertEqual(run['first']['returncode'], -signal.SIGKILL, run['first']['output'][-800:])
                self.assertEqual(run['janitor']['resumed'], [run['build_id']])
                self.assertEqual(self.result(run), reference, run.get('second', {}).get('output', '')[-1500:])
                self.assertEqual((run['recovery_attempts'], run['reservation']), (1, 'SETTLED'))

    def test_the_continued_worker_never_calls_a_stage_the_checkpoint_covers(self):
        expected = {  # (checkpoint at the kill, the first worker's calls, the second worker's calls)
            'after the spec': ('spec', {'architect': 1, 'generator': 1}, {'generator': 1, 'repair': 3}),
            'after round 0': ('round 0', {'architect': 1, 'generator': 1, 'repair': 1}, {'repair': 3}),
            'in a repair round': ('round 1', {'architect': 1, 'generator': 1, 'repair': 2}, {'repair': 2}),
        }
        from omni_prod.build_checkpoint import label
        for name, (checkpoint, first, second) in expected.items():
            with self.subTest(name):
                run = self.runs[name]
                self.assertEqual(label(run['checkpoint_at_kill']), checkpoint)
                self.assertEqual(run['first']['calls'], first)
                self.assertEqual(run['second']['calls'], second)
                second_trace = [a for a in run['attempts'] if a[0] != run['attempts'][0][0]]
                self.assertNotIn('architecture', {a[2] for a in second_trace})

    def test_the_record_names_the_checkpoint_it_continued_from(self):
        for name, stage, rounds in (('after the spec', 'spec', None), ('after round 0', 'round', 0),
                                    ('in a repair round', 'round', 1)):
            with self.subTest(name):
                run = self.runs[name]
                recovery = run['evidence']['recovery']
                self.assertEqual((recovery['decision'], recovery['recovery_attempt']), ('resume', 1))
                at_kill = run['checkpoint_at_kill']
                resumed = recovery['resumed_from']
                self.assertEqual((resumed['stage'], resumed['round']), (stage, rounds))
                self.assertEqual(resumed['spec_sha256'], at_kill['spec']['sha256'])
                self.assertEqual(resumed['repository_sha256'], (at_kill.get('snapshot') or {}).get('sha256'))
                self.assertEqual(recovery['from_checkpoint']['checkpoint'], resumed['checkpoint'])
                # one row without an answer in each: the call in flight, or -- killed while round 2 was verified -- the
                # repair call of round 2, completed but not yet flushed (the ledger writes a completion at the next step)
                self.assertEqual(recovery['ledger']['without_an_answer'], 1)
                first = [a for a in self.db.all("SELECT metered_cost_usd FROM task_attempts WHERE build_id=%s AND "
                                                 "kind='provider_call' AND trace_id=%s", run['build_id'], run['attempts'][0][0])]
                self.assertEqual(resumed['carried_budget'], {'carried': True, 'external_calls': len(first), 'metered_usd':
                                 str(sum((Decimal(str(m)) for m, in first if m is not None), Decimal('0')))})
                self.assertEqual(run['events'][-1], __import__('omni_prod.maintenance', fromlist=['x'])
                                 .RECOVERY_LINES['resumed']['he'])

    def test_resume_verdict_passes_every_continued_build_and_still_fails_the_logged_ledger(self):
        from omni_prod.postdeploy_checks import resume_verdict
        from tests.test_postdeploy_crash_resume import LOGGED
        for name in ('after the spec', 'after round 0', 'in a repair round'):
            with self.subTest(name):
                run = self.runs[name]
                ok, detail = resume_verdict(run['attempts'], run['evidence'].get('recovery'))
                self.assertTrue(ok, detail)
        ok, detail = resume_verdict(LOGGED, None)
        self.assertFalse(ok)
        self.assertIn('started over', detail)

    def test_a_kill_before_any_checkpoint_keeps_the_behaviour_of_before_by_name(self):
        run = self.runs['before any checkpoint']
        self.assertIsNone(run['checkpoint_at_kill'])
        self.assertEqual(run['janitor']['failed'], [run['build_id']])
        self.assertEqual((run['status'], run['error_code']), ('failed', 'provider_liability_unknown'))
        self.assertEqual(run['reservation'], 'RESERVED')          # held for reconciliation, as before S4.2
        self.assertNotIn('second', run)

    def test_a_checkpoint_whose_bytes_changed_fails_by_name_and_never_starts_over(self):
        run = self.runs['tampered checkpoint']
        self.assertEqual((run['status'], run['error_code']), ('failed', 'checkpoint_unusable'))
        self.assertIn('sha256', run['error_message'])
        self.assertEqual(run['second']['calls'], {})               # not one model call in the second worker
        self.assertEqual(run['evidence']['recovery']['decision'], 'resume')

    def test_the_agent_run_carries_the_lost_workers_finished_tasks(self):
        from omni_prod.agent_os.runtime import AgentRuntime
        rt = AgentRuntime(self.db.pool)
        start = {'requirements_agent', 'product_planner'}            # the run's opening tasks (approved request)
        for name, carried_agents in (('after the spec', start | {'architecture_agent'}),
                                     ('after round 0', start | {'architecture_agent', 'coding_agent', 'qa_agent'})):
            with self.subTest(name):
                run = self.runs[name]
                self.assertEqual([o for _, o in run['runs']], ['superseded', 'ready'])
                tasks = rt.tasks(run['runs'][1][0])
                carried = [t for t in tasks if 'carried_from' in (t['evidence'] or {})]
                self.assertEqual({t['agent_key'] for t in carried}, carried_agents)
                self.assertTrue(all(t['evidence']['carried_from']['run'] == run['runs'][0][0] for t in carried))
                # the architect's task exists once in the new run: carried, never opened again
                self.assertEqual([t for t in tasks if t['agent_key'] == 'architecture_agent'],
                                 [t for t in carried if t['agent_key'] == 'architecture_agent'])
                self.assertTrue(all(t['state'] in ('SUCCEEDED', 'FAILED') for t in carried))


class JanitorDecides(unittest.TestCase):
    """maintenance.recover_lost_running on real rows: what it does with a lost build, by its checkpoint."""

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        cls.db = Database('crashjan')

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def lost(self, *, checkpoint=None, paid=True, stop=False, attempts=0):
        import json
        from omni_prod.attempt_ledger import AttemptRecord, persist_attempts
        from tests.crash_resume_harness import create_build
        bid = create_build(self.db.pool)
        with self.db.pool.connection() as conn:
            conn.execute("UPDATE build_jobs SET status='running', started_at=now(), heartbeat_at=now() - interval '1 minute', "
                         "recovery_attempts=%s, cancel_requested_at = CASE WHEN %s THEN now() END, "
                         "evidence_json = evidence_json || %s::jsonb WHERE id=%s",
                         (attempts, stop, json.dumps({'checkpoint': checkpoint} if checkpoint else {}), bid))
            conn.commit()
        if paid:
            persist_attempts(self.db.pool, [AttemptRecord(task_type='codegen', attempt_seq=0, kind='provider_call',
                                                          outcome='unknown', authorized_cost_usd=Decimal('0.05'))],
                             build_id=bid)
        return bid

    def state(self, bid):
        return self.db.one("SELECT status, error_code, recovery_attempts, evidence_json->'recovery' FROM build_jobs "
                           "WHERE id=%s", bid)

    def checkpoint(self, **over):
        h = 'a' * 64
        return {'version': 1, 'stage': 'round', 'round': 1, 'resumable': True, 'worker': 'trc_lost', 'epoch': 0,
                'spec': {'key': 'k/spec', 'sha256': h, 'fingerprint': h},
                'snapshot': {'key': 'k/repo', 'sha256': h, 'zip_sha256': h}, 'state': {'key': 'k/state', 'sha256': h},
                'written_at': '2026-11-26T10:00:00+00:00', **over}

    def test_a_lost_build_with_a_usable_checkpoint_is_requeued_to_continue_even_after_a_paid_call(self):
        bid = self.lost(checkpoint=self.checkpoint())
        out, sent = janitor(self.db.pool)
        self.assertEqual((out['resumed'], out['recovered'], sent), ([bid], [bid], [(sent[0][0], bid)]))
        status, code, attempts, recovery = self.state(bid)
        self.assertEqual((status, code, attempts), ('queued', None, 1))
        self.assertEqual((recovery['decision'], recovery['recovery_attempt'], recovery['from_checkpoint']['checkpoint']),
                         ('resume', 1, 'round 1'))
        self.assertEqual(recovery['ledger'], {'provider_calls': 1, 'without_an_answer': 1})   # what the ledger shows

    def test_no_usable_checkpoint_keeps_the_behaviour_of_before(self):
        for checkpoint in (None, self.checkpoint(resumable=False, why_not='the content route'),
                           self.checkpoint(version=7)):
            with self.subTest(checkpoint=checkpoint and checkpoint.get('why_not') or checkpoint and 'version'):
                bid = self.lost(checkpoint=checkpoint)
                out, sent = janitor(self.db.pool)
                self.assertEqual((out['failed'], out['resumed'], sent), ([bid], [], []))
                self.assertEqual(self.state(bid)[:2], ('failed', 'provider_liability_unknown'))
        bid = self.lost(checkpoint=None, paid=False)                 # no paid call: requeued to start over, said so
        out, _ = janitor(self.db.pool)
        self.assertEqual((out['recovered'], out['resumed']), ([bid], []))
        recovery = self.state(bid)[3]
        self.assertEqual((recovery['decision'], recovery['why_not_resumed']), ('restart', 'no checkpoint was written'))

    def test_a_stop_request_or_a_second_loss_is_never_continued(self):
        bid = self.lost(checkpoint=self.checkpoint(), paid=False, stop=True)
        self.assertEqual(janitor(self.db.pool)[0]['cancelled'], [bid])
        bid = self.lost(checkpoint=self.checkpoint(), attempts=1)
        out, _ = janitor(self.db.pool)
        self.assertEqual((out['failed'], out['resumed']), ([bid], []))
        self.assertEqual(self.state(bid)[:2], ('failed', 'provider_liability_unknown'))


class PlanGraphCarries(unittest.TestCase):
    """The plan-governed recorder (OMNI_PLAN_DRIVEN=1): a build that continues after round 1 is admitted for repair
    round 2 and never for the architect again."""

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        cls.db = Database('crashplan')

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_the_plan_admits_the_next_repair_round_and_not_the_architect(self):
        from omni_prod.agent_os.recorder import PlanViolation, recorder_for
        from omni_prod.agent_os.runtime import AgentRuntime
        from tests.test_plan_driven_execution import plan_graph
        bid = f'bld_{uuid.uuid4().hex}'
        binding = {'graph': plan_graph(), 'plan_id': 'pln_crash'}
        lost = recorder_for(self.db.pool, bid, binding, enforce=True)
        lost.start(from_brief=True)
        for step in ('architecture', 'codegen'):
            lost.on_model(step)
        lost.on_check_start()
        lost.on_check(False, 'round 0 failed')
        lost.on_model('repair')
        lost.on_check_start()
        lost.on_check(False, 'round 1 failed')                    # the checkpoint 'round 1' is written here
        rec = recorder_for(self.db.pool, bid, binding, enforce=True)
        rec.start(from_brief=True, resume={'checkpoint': 'round 1', 'stage': 'round', 'round': 1, 'written_at': None,
                                           'report_passed': False})
        rt = AgentRuntime(self.db.pool)
        states = {t['evidence'].get('stage'): t['state'] for t in rt.tasks(rec.run_id)}
        self.assertEqual({s: states[s] for s in ('architecture', 'codegen', 'unit_tests', 'repair')},
                         {'architecture': 'SUCCEEDED', 'codegen': 'SUCCEEDED', 'unit_tests': 'REPAIRING',
                          'repair': 'REPAIRING'})
        rec.on_model('repair')                                        # repair round 2 is admitted
        self.assertEqual(rec.repair_rounds, 2)
        with self.assertRaises(PlanViolation):
            rec.on_model('architecture')                              # the spec is in the checkpoint
        superseded = [r for r in self.db.all("SELECT outcome FROM agent_runs WHERE subject_id=%s", bid)]
        self.assertIn(('superseded',), superseded)


if __name__ == '__main__':
    unittest.main()

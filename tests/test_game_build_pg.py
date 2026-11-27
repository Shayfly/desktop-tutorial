"""The game builder on the REAL worker path (the owner, 2026-11-27, answer 11; warehouse 134, plan S12.1).

What is real: worker_tasks._run_live_build_job and worker_tasks.game_engine_for (the function execute_live_build_job's
components factory calls to choose the engine), the AutonomousProductEngine with the game agents, the real RoutedModelGateway
over loopback HTTP, PostgresBuildRepository, PostgresSubscriptionService, PostgresProjectWorkspace, the attempt ledger, the
spend and billing tail, and game_probe in a REAL Chromium (the game is played at a computer's width and a phone's).
What stands in: the model (a scripted OpenAI-compatible server answering the game definition from the request alone), object
storage (DirectoryArtifactStore, the S3 contract), the quality and security scores (they judge a web page and are not what is
tested here), and the build contract (the request carries `product_family: game`; a real BuildContract of a game needs the
conversation's approval flow, which is tested separately in tests/test_game_profile_routing.py).

Needs M4D2_DATABASE_URL and a Chromium (OMNI_CHROMIUM or CHROMIUM_PATH, or Playwright's own); otherwise NOT_RUN, said.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
import unittest
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()
PROMPT = 'משחק פלטפורמות קטן לילדים: קופצים על פלטפורמות, אוספים מטבעות ומגיעים לדגל'


def _problem():
    if not DATABASE_URL:
        return 'NOT_RUN: needs M4D2_DATABASE_URL (runs in browser-python game-build)'
    try:
        import fastapi  # noqa: F401
        import playwright  # noqa: F401
        import psycopg
    except ImportError as exc:
        return f'NOT_RUN: {exc.name} is not installed'
    try:
        psycopg.connect(DATABASE_URL, connect_timeout=5).close()
    except Exception as exc:
        return f'NOT_RUN: PostgreSQL unreachable ({type(exc).__name__})'
    return None


PROBLEM = _problem()


def sample(kind='platformer'):
    return json.loads((ROOT / 'omni_prod/game_kit/samples' / f'{kind}.json').read_text(encoding='utf-8'))


class ScriptedGameModel:
    """An OpenAI-compatible model on 127.0.0.1 that answers the game builder's calls from a script: each entry is the JSON the
    n-th call returns. Every request is recorded (its user message), so a test can see what the repairer was told."""

    def __init__(self, answers: list):
        from omni_prod.game_kit.builder import _SYSTEM
        self.answers, self.requests, self.lock = list(answers), [], threading.Lock()
        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                messages = body.get('messages') or []
                system = next((m['content'] for m in messages if m.get('role') == 'system'), '')
                user = next((m['content'] for m in messages if m.get('role') == 'user'), '')
                with model.lock:
                    model.requests.append((system == _SYSTEM, user))
                    n = len(model.requests) - 1
                if system != _SYSTEM or n >= len(model.answers):
                    self.send_response(500)
                    self.end_headers()
                    return
                text = json.dumps(model.answers[n], ensure_ascii=False)
                payload = json.dumps({'id': f'resp_{uuid.uuid4().hex[:12]}', 'model': 'scripted-model',
                                      'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': text}}],
                                      'usage': {'prompt_tokens': len(user) // 4 + 10, 'completion_tokens': len(text) // 4 + 5}}).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.server.server_port}/v1'

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def answer(defn, theme='bright friendly pixel art'):
    return {'definition': defn, 'art_theme': theme}


class Tap:
    """Passes every verification through and keeps (repository, report) per round."""
    def __init__(self, inner):
        self.inner, self.rounds = inner, []

    def execute(self, *, repository, spec):
        report = self.inner.execute(repository=repository, spec=spec)
        self.rounds.append((dict(repository), report))
        return report


@unittest.skipIf(PROBLEM, PROBLEM or '')
class TheGameBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'game_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url, min_size=1, max_size=4).open()

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def build(self, answers, *, art=None, env=None):
        """One game build through the worker's own code. Returns (build_id, model, the evidence row)."""
        from omni_prod.attempt_ledger import RecordingExecutor  # noqa: F401  (the real ledger is installed by the worker)
        from omni_prod.job_repository import PostgresBuildRepository
        from omni_prod.subscription_store import PostgresSubscriptionService
        from omni_prod.v28_platform import V28Platform
        from omni_prod.worker_tasks import _persist_build_attempts, _run_live_build_job, game_engine_for
        from omni_prod.workspace import PostgresProjectWorkspace
        from tests.crash_resume_harness import DirectoryArtifactStore, _passing, create_build, scripted_gateway
        model = ScriptedGameModel(answers)
        self.addCleanup(model.close)
        build_id = create_build(self.pool, prompt=PROMPT)
        jobs = PostgresBuildRepository(self.pool)
        account = jobs.get_request(build_id)['user_id']
        gateway = scripted_gateway(model.url)

        class AsGame:          # the request the factory reads: the real one, with the approved contract's family
            def get_request(self, bid):
                return {**jobs.get_request(bid), 'build_contract': {'product_family': 'game'}}

        keep = {k: os.environ.get(k) for k in ('OMNI_OUTPUT_GAME', 'OMNI_GAME_ART', 'OMNI_FOUNDER_ACCOUNT_IDS', 'OMNI_RELEASE_POLICY', 'OMNI_MAX_REPAIR_ROUNDS')}
        os.environ.update({'OMNI_OUTPUT_GAME': 'owner', 'OMNI_FOUNDER_ACCOUNT_IDS': account, 'OMNI_RELEASE_POLICY': 'shadow', **(env or {})})
        self.addCleanup(lambda: [os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v) for k, v in keep.items()])
        platform = V28Platform(token_secret='game-build-test-' + 'x' * 32, subscription_service=PostgresSubscriptionService(pool=self.pool))
        with tempfile.TemporaryDirectory() as store:
            engine = game_engine_for(AsGame(), build_id, SimpleNamespace(web=True), gateway)
            if art is not None:
                engine.game_state.art_source = art
            tap = Tap(engine.executor)                      # what the engine verified in each round, to read back below
            engine.executor = tap
            workspace = PostgresProjectWorkspace(self.pool, DirectoryArtifactStore(store))
            raised = None
            try:
                outcome = _run_live_build_job(
                    build_id, jobs=jobs, platform=platform, workspace=workspace, components_factory=lambda: (engine, gateway),
                    quality_fn=lambda **kw: _passing(score=100, minimum_score=80, blockers=()),
                    security_fn=lambda repo: _passing(findings=()), attempt_pool=self.pool)
            except Exception as exc:        # the worker marks the build failed and re-raises: the job itself fails, loudly
                outcome, raised = None, exc
            _persist_build_attempts(self.pool, jobs, build_id, gateway)
        with self.pool.connection() as conn:
            row = conn.execute('SELECT status, evidence_json, error_code FROM build_jobs WHERE id = %s', (build_id,)).fetchone()
        return SimpleNamespace(build_id=build_id, model=model, outcome=outcome, status=row[0], evidence=row[1] or {}, error=row[2],
                               engine=engine, rounds=tap.rounds, raised=raised)

    def test_the_dispatch_gives_a_game_its_own_engine_and_any_other_build_the_web_engine(self):
        from omni_prod.job_repository import PostgresBuildRepository
        from omni_prod.worker_tasks import game_engine_for
        from tests.crash_resume_harness import create_build
        build_id = create_build(self.pool, prompt='אתר לעסק')
        jobs, web = PostgresBuildRepository(self.pool), object()
        self.assertIs(game_engine_for(jobs, build_id, web, gateway=None), web)

    def test_a_game_is_refused_by_the_worker_for_an_account_the_rollout_does_not_allow(self):
        from omni_prod.job_repository import PostgresBuildRepository
        from omni_prod.worker_tasks import game_engine_for
        from tests.crash_resume_harness import create_build
        build_id = create_build(self.pool, prompt=PROMPT)
        jobs = PostgresBuildRepository(self.pool)

        class AsGame:
            def get_request(self, bid):
                return {**jobs.get_request(bid), 'build_contract': {'product_family': 'game'}}
        for mode in ('off', 'owner'):          # `owner`: this account is not the owner's
            with self.subTest(mode):
                os.environ['OMNI_OUTPUT_GAME'] = mode
                self.addCleanup(os.environ.pop, 'OMNI_OUTPUT_GAME', None)
                with self.assertRaises(PermissionError):
                    game_engine_for(AsGame(), build_id, object(), gateway=None)

    def test_a_game_is_written_validated_played_and_released(self):
        run = self.build([answer(sample())])
        self.assertEqual(run.status, 'ready', (run.status, run.error, run.evidence.get('build_log_tail')))
        self.assertEqual(len(run.model.requests), 1, 'one model call writes the whole game')
        self.assertTrue(run.evidence['skill_gates']['G5']['status'] == 'pass', run.evidence['skill_gates']['G5'])
        art = json.loads(self.repo_file(run, '.omni/art.json'))
        self.assertEqual(set(art['sources'].values()), {'procedural'})
        self.assertEqual(art['dropped'], [])
        defn = json.loads(self.repo_file(run, 'game.json'))
        self.assertEqual(defn['schema'], '148ai.game/2')
        for role, path in defn['art'].items():                       # the images are files of the build, carried as the platform carries every image
            self.assertTrue(self.repo_file(run, path).startswith('148ai-binary:v1;mime=image/png;sha256='), path)
            self.assertIn(path, self.repo_file(run, 'index.html'))
        self.assertEqual(len(run.rounds), 1)
        self.assertTrue(run.rounds[0][1].passed)
        probe = json.loads(run.rounds[0][1].build_log)['game_probe']
        self.assertGreaterEqual(probe['computer']['fps'], 30)
        self.assertGreater(probe['phone']['score'], 0)

    def test_an_invalid_definition_gets_one_corrective_call_that_names_every_problem(self):
        bad = sample()
        bad['palette']['bg'] = 'red'
        bad['player']['lives'] = 9
        run = self.build([answer(bad), answer(sample())])
        self.assertEqual(run.status, 'ready', (run.status, run.error))
        self.assertEqual(len(run.model.requests), 2)
        correction = json.loads(run.model.requests[1][1])
        self.assertIn('palette.bg must be a colour', ' '.join(correction['problems']))
        self.assertIn('player.lives must be', ' '.join(correction['problems']))

    def test_a_definition_invalid_twice_fails_the_build_before_anything_is_played(self):
        bad = sample()
        bad['kind'] = 'rpg'
        run = self.build([answer(bad), answer(bad)])
        self.assertEqual(run.status, 'failed')
        self.assertIn('invalid game definition twice', str(run.raised))
        self.assertEqual(run.rounds, [], 'an invalid game must never reach the browser')
        self.assertEqual(len(run.model.requests), 2)

    def test_a_game_the_probe_cannot_win_is_repaired_with_the_probes_findings_and_then_played_again(self):
        weak = sample()
        for lv in weak['levels']:
            lv['rows'] = [r.replace('o', '.').replace('E', '.') for r in lv['rows']]         # nothing to score on
        run = self.build([answer(weak), answer(sample())])
        self.assertEqual(run.status, 'ready', (run.status, run.error))
        self.assertEqual([r[1].passed for r in run.rounds], [False, True])
        self.assertIn('score_never_rose', run.rounds[0][1].failures[0].message)
        told = json.loads(run.model.requests[1][1])
        self.assertIn('score_never_rose', json.dumps(told['probe_findings']))
        self.assertEqual(told['current_definition']['levels'], weak['levels'], 'the repairer is shown the definition it wrote')

    def test_a_game_that_is_never_playable_never_shows_as_ready(self):
        weak = sample()
        for lv in weak['levels']:
            lv['rows'] = [r.replace('o', '.').replace('E', '.') for r in lv['rows']]
        run = self.build([answer(weak)] * 8, env={'OMNI_MAX_REPAIR_ROUNDS': '1'})
        self.assertNotEqual(run.status, 'ready')
        self.assertTrue(all(not r[1].passed for r in run.rounds))

    def test_with_the_release_policy_enforcing_a_game_that_passed_its_probe_is_still_refused(self):
        """Pinned, not endorsed: release_policy.build_report knows only the web profile's mandatory set (preview_starts,
        behavioural_acceptance, browser_flow). Until the architect decides what a game's mandatory set is, a played and
        passing game ends `release_policy_failed` in production, where the policy always enforces. See STATUS.md."""
        run = self.build([answer(sample())], env={'OMNI_RELEASE_POLICY': 'enforce'})
        self.assertEqual((run.status, run.error), ('failed', 'release_policy_failed'))
        self.assertTrue(run.rounds[-1][1].passed)

    def repo_file(self, run, path):
        return run.rounds[-1][0][path]


if __name__ == '__main__':
    unittest.main()

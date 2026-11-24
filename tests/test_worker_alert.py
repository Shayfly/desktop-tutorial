"""Warehouse 121 (the C18 finding, 2026-11-21): the dead-worker alert.

The decision and the issue handling run everywhere. RealRedis registers a real rq worker in a real Redis, the way the
build worker registers itself, and runs in intake-budget-pg (OMNI_TEST_REDIS_URL; no skip there).
Mutations: tests/negative_controls/worker_alert.json.
"""
import io
import json
import os
import sys
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import worker_alert as WA  # noqa: E402

NOW = datetime(2026, 11, 21, 18, 31, 0, tzinfo=timezone.utc)


def worker(name='w1', age=None, state='idle'):
    return {'name': name, 'state': state, 'last_heartbeat': None if age is None else NOW - timedelta(seconds=age)}


class Verdict(unittest.TestCase):
    def test_no_worker_registered_is_dead(self):
        self.assertEqual(WA.verdict([], NOW)[0], WA.DEAD)

    def test_a_fresh_heartbeat_is_alive(self):
        state, detail = WA.verdict([worker(age=40)], NOW)
        self.assertEqual(state, WA.ALIVE)
        self.assertIn('w1 (idle, heartbeat 40s ago)', detail)

    def test_a_worker_without_a_heartbeat_is_not_alive(self):
        state, detail = WA.verdict([worker(age=None)], NOW)
        self.assertEqual(state, WA.DEAD)
        self.assertIn('no heartbeat', detail)

    def test_a_stale_heartbeat_is_dead(self):
        self.assertEqual(WA.verdict([worker(age=600)], NOW)[0], WA.DEAD)

    def test_the_threshold_is_inclusive_at_180_seconds(self):
        self.assertEqual(WA.verdict([worker(age=180)], NOW)[0], WA.ALIVE)
        self.assertEqual(WA.verdict([worker(age=181)], NOW)[0], WA.DEAD)

    def test_one_live_worker_among_stale_ones_is_alive_and_the_stale_are_named(self):
        state, detail = WA.verdict([worker('old', age=900), worker('new', age=10, state='busy')], NOW)
        self.assertEqual(state, WA.ALIVE)
        self.assertIn('stale: old', detail)


class Check(unittest.TestCase):
    def test_no_redis_url_is_unverified(self):
        self.assertEqual(WA.check('', 'omni-builds', NOW)[0], WA.UNVERIFIED)

    def test_a_reader_error_is_unverified_not_alive(self):
        def broken(url, q):
            raise ConnectionError('refused')
        state, detail = WA.check('redis://x', 'omni-builds', NOW, reader=broken)
        self.assertEqual(state, WA.UNVERIFIED)
        self.assertIn('ConnectionError', detail)

    def test_a_real_refused_connection_is_unverified(self):
        # the real rq/redis reader against a port nothing listens on: the client raises, the verdict is not "alive"
        state, detail = WA.check('redis://127.0.0.1:1/0', 'omni-builds', NOW)
        self.assertEqual(state, WA.UNVERIFIED, detail)

    def test_the_redis_url_is_never_in_the_detail(self):
        def broken(url, q):
            raise ConnectionError(url)
        _, detail = WA.check('redis://user:secret@host:6379/0', 'omni-builds', NOW, reader=broken)
        self.assertNotIn('secret', detail)


class FakeGitHub:
    """The GitHub REST calls the alert makes, recorded; open issues per label kept in memory."""

    def __init__(self, open_issues=None):
        self.calls, self.issues, self.next = [], {i['number']: i for i in (open_issues or [])}, 900

    def urlopen(self, req, timeout=None):
        body = json.loads(req.data.decode()) if req.data else None
        path = req.full_url.split('/repos/o/r', 1)[1]
        self.calls.append((req.get_method(), path, body))
        out = None
        if req.get_method() == 'GET' and path.startswith('/issues?'):
            label = path.split('labels=')[1].split('&')[0]
            out = [i for i in self.issues.values() if i['state'] == 'open' and label in i['labels']]
        elif req.get_method() == 'POST' and path == '/issues':
            self.next += 1
            out = self.issues[self.next] = {'number': self.next, 'state': 'open', 'labels': body['labels'],
                                            'title': body['title']}
        elif req.get_method() == 'PATCH':
            self.issues[int(path.split('/')[2])]['state'] = body['state']
            out = {}
        else:
            out = {}
        return io.BytesIO(json.dumps(out).encode())

    def created(self):
        return [c for c in self.calls if c[0] == 'POST' and c[1] == '/issues']


class Issues(unittest.TestCase):
    def gh(self, fake):
        return WA.GitHub('o/r', 'token', fake.urlopen)

    def test_dead_with_nothing_open_opens_one_issue(self):
        fake = FakeGitHub()
        done = WA.act(self.gh(fake), WA.DEAD, 'no worker', 'omni-builds', drill=False, run_url='u')
        self.assertEqual(len(fake.created()), 1)
        self.assertEqual(fake.created()[0][2]['labels'], [WA.ALERT_LABEL])
        self.assertIn('ALERT: build worker down (omni-builds)', fake.created()[0][2]['title'])
        self.assertTrue(done.startswith('opened #'))

    def test_dead_again_comments_and_never_opens_a_second_issue(self):
        fake = FakeGitHub([{'number': 7, 'state': 'open', 'labels': [WA.ALERT_LABEL]}])
        for _ in range(3):
            WA.act(self.gh(fake), WA.DEAD, 'no worker', 'omni-builds', drill=False, run_url='u')
        self.assertEqual(fake.created(), [])
        self.assertEqual(sum(1 for c in fake.calls if c[1] == '/issues/7/comments'), 3)

    def test_alive_closes_the_open_alert_with_a_comment(self):
        fake = FakeGitHub([{'number': 7, 'state': 'open', 'labels': [WA.ALERT_LABEL]}])
        done = WA.act(self.gh(fake), WA.ALIVE, '1 live', 'omni-builds', drill=False, run_url='u')
        self.assertEqual(fake.issues[7]['state'], 'closed')
        self.assertIn(('POST', '/issues/7/comments', {'body': 'Recovered: 1 live\n\nu'}), fake.calls)
        self.assertEqual(done, 'closed #7')

    def test_alive_with_nothing_open_does_nothing(self):
        fake = FakeGitHub()
        self.assertEqual(WA.act(self.gh(fake), WA.ALIVE, '1 live', 'omni-builds', drill=False, run_url='u'), 'nothing open')
        self.assertEqual([c[0] for c in fake.calls], ['GET'])

    def test_unverified_alerts_under_its_own_title(self):
        fake = FakeGitHub()
        WA.act(self.gh(fake), WA.UNVERIFIED, 'cannot read', 'omni-builds', drill=False, run_url='u')
        self.assertIn('cannot be verified', fake.created()[0][2]['title'])

    def test_a_drill_raises_its_own_issue_and_closes_it(self):
        fake = FakeGitHub([{'number': 7, 'state': 'open', 'labels': [WA.ALERT_LABEL]}])   # a real alert stays untouched
        done = WA.act(self.gh(fake), WA.DEAD, 'no worker', 'omni-drill-no-consumer', drill=True, run_url='u')
        made = fake.created()[0][2]
        self.assertEqual(made['labels'], [WA.DRILL_LABEL])
        self.assertTrue(made['title'].startswith('ALERT (drill):'))
        self.assertEqual(fake.issues[901]['state'], 'closed')
        self.assertEqual(fake.issues[7]['state'], 'open')
        self.assertTrue(done.startswith('opened and closed drill issue #'))


class Cli(unittest.TestCase):
    def run_main(self, argv, env, reader=None, fake=None):
        old = dict(os.environ)
        os.environ.update(env)
        try:
            return WA.main(argv, urlopen=(fake or FakeGitHub()).urlopen,
                           reader=reader or (lambda url, q: [{'name': 'w1', 'state': 'idle',
                                                              'last_heartbeat': datetime.now(timezone.utc)}]))
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_drill_only_with_another_queue(self):
        env = {'OMNI_REDIS_URL': 'redis://x', 'GH_TOKEN': 't'}
        self.assertEqual(self.run_main(['--repo', 'o/r', '--drill'], env), 2)
        self.assertEqual(self.run_main(['--repo', 'o/r', '--queue', 'other'], env), 2)

    def test_exit_codes_follow_the_verdict(self):
        env = {'OMNI_REDIS_URL': 'redis://x', 'GH_TOKEN': 't'}
        self.assertEqual(self.run_main(['--repo', 'o/r'], env), 0)
        self.assertEqual(self.run_main(['--repo', 'o/r'], env, reader=lambda u, q: []), 1)
        self.assertEqual(self.run_main(['--repo', 'o/r'], {'OMNI_REDIS_URL': '', 'GH_TOKEN': 't'}), 2)

    def test_no_token_cannot_raise_the_alert_and_says_so(self):
        self.assertEqual(self.run_main(['--repo', 'o/r'], {'OMNI_REDIS_URL': 'redis://x', 'GH_TOKEN': ''},
                                       reader=lambda u, q: []), 2)


class RealRedis(unittest.TestCase):
    """A real rq worker registration in a real Redis, read back through the real reader."""

    def setUp(self):
        url = os.getenv('OMNI_TEST_REDIS_URL', '').strip()
        if not url:
            raise unittest.SkipTest('BLOCKED: OMNI_TEST_REDIS_URL (real Redis) not configured')
        from redis import Redis
        from rq import Queue, Worker
        self.url, self.conn = url, Redis.from_url(url)
        self.qname = f'omni-alert-test-{uuid.uuid4().hex[:8]}'
        self.worker = Worker([Queue(self.qname, connection=self.conn)], connection=self.conn,
                             name=f'alert-test-{uuid.uuid4().hex[:8]}')
        self.addCleanup(lambda: self.worker.register_death())

    def test_a_registered_worker_with_a_fresh_heartbeat_is_alive(self):
        self.worker.register_birth()
        self.worker.heartbeat()
        state, detail = WA.check(self.url, self.qname)
        self.assertEqual(state, WA.ALIVE, detail)
        self.assertIn(self.worker.name, detail)

    def test_a_heartbeat_older_than_the_threshold_is_dead(self):
        self.worker.register_birth()
        old = (datetime.now(timezone.utc) - timedelta(seconds=WA.MAX_AGE_SECONDS + 30))
        from rq.utils import utcformat
        self.conn.hset(self.worker.key, 'last_heartbeat', utcformat(old))
        self.assertEqual(WA.check(self.url, self.qname)[0], WA.DEAD)

    def test_a_worker_that_left_the_registry_is_dead(self):
        self.worker.register_birth()
        self.worker.heartbeat()
        self.worker.register_death()
        self.assertEqual(WA.check(self.url, self.qname)[0], WA.DEAD)

    def test_a_queue_nobody_listens_on_is_dead(self):
        self.worker.register_birth()
        self.worker.heartbeat()
        self.assertEqual(WA.check(self.url, self.qname + '-no-consumer')[0], WA.DEAD)


if __name__ == '__main__':
    unittest.main()

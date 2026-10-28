"""Production 2026-10-29: two builds (bld_c38ede3e..., bld_e15d00c1...) were taken by the build worker and ended in
~2.5 s as RQ "Job OK" -- no write, no log line -- because the worker read a different database than the web
(db-identity run 40786272189: worker d2eb0b8c775f, web 57afb09577d6). The builds stayed QUEUED for ever and the
customer saw the progress stop at "infrastructure".

A build the worker cannot find now fails LOUDLY: an error log line, FAILED with error_code build_not_found where its
job row exists (credits released), and the job raises -- RQ records a failed job, never "Job OK". A duplicate delivery
of a build that is no longer QUEUED stays an idempotent no-op, but logs a warning."""
from __future__ import annotations

import unittest
from unittest import mock

from omni_prod import worker_tasks as W
from omni_prod.models import BuildStatus


class Jobs:
    def __init__(self, *, request=None, row_status=None):
        self.request, self.row_status, self.transitions = request, row_status, []

    def get_request(self, build_id):
        if self.request is None:
            raise KeyError('Build request not found')
        return self.request

    def transition(self, *, build_id, expected, target, **kw):
        self.transitions.append({'expected': expected, 'target': target, **kw})
        if self.row_status != expected.value:
            return False
        self.row_status = target.value
        return True


def run(jobs, platform=None):
    return W._run_live_build_job('bld_x', jobs=jobs, platform=platform or mock.MagicMock(), workspace=None,
                                 components_factory=None, quality_fn=None, security_fn=None)


class ABuildTheWorkerCannotFind(unittest.TestCase):
    def test_an_unknown_build_id_raises_and_logs_never_a_silent_ok(self):
        jobs = Jobs()                                         # nothing here: not the request, not the job row
        with self.assertLogs('omni_prod.worker_tasks', level='ERROR') as logs, self.assertRaises(W.BuildNotFound):
            run(jobs)
        self.assertTrue(any('NOT FOUND' in line and 'bld_x' in line for line in logs.output), logs.output)

    def test_a_job_row_without_its_request_is_marked_failed_with_a_code_and_credits_released(self):
        jobs, platform = Jobs(row_status=BuildStatus.QUEUED.value), mock.MagicMock()
        with self.assertLogs('omni_prod.worker_tasks', level='ERROR'), self.assertRaises(W.BuildNotFound):
            run(jobs, platform)
        failed = [t for t in jobs.transitions if t['target'] == BuildStatus.FAILED]
        self.assertEqual(len(failed), 1, jobs.transitions)
        self.assertEqual(failed[0]['error_code'], 'build_not_found')
        self.assertIn('bld_x', failed[0]['error_message'])
        self.assertEqual(jobs.row_status, 'failed')
        platform.subscriptions.release.assert_called_once_with(build_id='bld_x')

    def test_the_customer_text_exists_in_both_languages(self):
        import pathlib
        js = (pathlib.Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js').read_text()
        self.assertEqual(js.count('build_not_found:'), 2)


class ADuplicateDelivery(unittest.TestCase):
    def test_a_build_no_longer_queued_is_not_failed_but_the_no_op_is_logged(self):
        jobs = Jobs(request={'user_id': 'u'}, row_status=BuildStatus.RUNNING.value)   # another delivery runs it
        with self.assertLogs('omni_prod.worker_tasks', level='WARNING') as logs:
            self.assertIsNone(run(jobs))
        self.assertEqual([t['target'] for t in jobs.transitions], [BuildStatus.RUNNING])   # the claim attempt only
        self.assertEqual(jobs.row_status, 'running')
        self.assertTrue(any('not claimed' in line for line in logs.output), logs.output)


def rq_job_for_an_unknown_build(build_id):
    """What RQ runs: the real _run_live_build_job over a database that has no such build."""
    return W._run_live_build_job(build_id, jobs=Jobs(), platform=mock.MagicMock(), workspace=None,
                                 components_factory=None, quality_fn=None, security_fn=None)


class OnARealQueue(unittest.TestCase):
    """The production symptom itself, on real Redis + RQ: the job must end FAILED, not "Job OK" (finished).
    Runs in intake-budget-pg (OMNI_TEST_REDIS_URL; no skip there)."""

    def test_an_unknown_build_is_a_failed_rq_job_not_job_ok(self):
        import os
        import uuid
        url = os.getenv('OMNI_TEST_REDIS_URL', '').strip()
        if not url:
            raise unittest.SkipTest('BLOCKED: OMNI_TEST_REDIS_URL (real Redis) not configured')
        from redis import Redis
        from rq import Queue, SimpleWorker
        conn = Redis.from_url(url)
        q = Queue(f'nf-{uuid.uuid4().hex[:8]}', connection=conn)
        job = q.enqueue(rq_job_for_an_unknown_build, 'bld_missing_0001')
        SimpleWorker([q], connection=conn).work(burst=True)
        job.refresh()
        self.assertEqual(job.get_status(refresh=True), 'failed')
        self.assertIn('BuildNotFound', job.latest_result().exc_string if hasattr(job, 'latest_result') else job.exc_info)
        from tests.evidence_notice import notice
        notice('worker build-not-found PASS', f'RQ job for an unknown build -> status={job.get_status()} (not finished / Job OK)')


if __name__ == '__main__':
    unittest.main()

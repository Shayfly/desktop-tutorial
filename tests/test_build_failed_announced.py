"""Warehouse 77c (owner 2026-11-16): a failed build is said in the conversation, with one action.

Found: a customer whose build failed saw nothing in the conversation; the failure lived only in the build tab.

Real path: the production worker job `_run_live_build_job` through the BuildHarness (fake engine and platform), its jobs
wrapped in `FailureWitness` exactly as `_run_live_build_job_with_components` wraps them, then `announce_if_failed` into
a MemoryConversationStore (it stands in for SQL only); the UI's own actionButtons() handles the action.
"""
from __future__ import annotations

import inspect
import unittest

from omni_prod import worker_tasks
from omni_prod.build_announcement import FailureWitness, announce_if_failed, message_for
from omni_prod.conversation.store import MemoryConversationStore
from tests.test_m3_preview_logic import BuildHarness

REQUEST = {'public_project_id': 'prj_shop', 'user_id': 'usr_customer'}


def run(h, store=None):
    witness = FailureWitness(h.jobs)
    h.jobs.request = {**(h.jobs.request or {}), **REQUEST}
    store = store if store is not None else MemoryConversationStore()
    real_jobs = h.jobs
    h.jobs = witness
    try:
        outcome = h.run()
    finally:
        h.jobs = real_jobs
        written = announce_if_failed(witness, conversation=store, request=real_jobs.get_request('bld_1'), build_id='bld_1')
    return outcome, written, store.messages_for('prj_shop', limit=10)


class AFailedBuildIsSaid(unittest.TestCase):
    def test_a_build_that_fails_its_checks_writes_one_message_with_one_action(self):
        outcome, written, msgs = run(BuildHarness(verified=False))
        self.assertEqual(outcome, 'failed')
        self.assertTrue(written)
        [m] = msgs
        self.assertEqual(m['role'], 'assistant')
        self.assertIn('הבנייה נכשלה.', m['content'])
        meta = m['interpretation']
        self.assertEqual((meta['intent'], meta['build_failed']), ('build_failed', 'bld_1'))
        self.assertEqual([a['type'] for a in meta['actions']], ['retry_build'])     # one action, not two
        self.assertEqual(meta['error_code'], 'verification_failed')

    def test_the_refund_is_said_only_when_the_credits_went_back(self):
        self.assertIn('לא חויבתם', message_for(build_id='b', error_code='verification_failed', billing='released')['content'])
        self.assertNotIn('לא חויבתם', message_for(build_id='b', error_code='verification_failed', billing=None)['content'])

    def test_a_missing_customer_detail_asks_for_it_instead_of_a_retry(self):
        msg = message_for(build_id='b', error_code='needs_customer_input', billing='released')
        self.assertEqual([a['type'] for a in msg['interpretation']['actions']], ['edit_requirements'])
        self.assertIn('חסר פרט', msg['content'])

    def test_a_ready_build_writes_nothing(self):
        outcome, written, msgs = run(BuildHarness())
        self.assertEqual(outcome, 'ready')
        self.assertFalse(written)
        self.assertEqual(msgs, [])

    def test_an_engine_crash_is_said_too(self):
        h, store = BuildHarness(engine_exc=RuntimeError('the engine died')), MemoryConversationStore()
        with self.assertRaises(RuntimeError):
            run(h, store)                                   # the job re-raises; the finally still announces
        [m] = store.messages_for('prj_shop')
        self.assertEqual(m['interpretation']['error_code'], 'worker_exception')
        self.assertEqual([a['type'] for a in m['interpretation']['actions']], ['retry_build'])

    def test_the_same_failure_is_said_once(self):
        witness = FailureWitness(BuildHarness().jobs)
        witness.failed = {'error_code': 'verification_failed', 'evidence_json': {}}
        store = MemoryConversationStore()
        for _ in range(2):
            announce_if_failed(witness, conversation=store, request=REQUEST, build_id='bld_3')
        self.assertEqual([m.get('request_key') for m in store.messages_for('prj_shop')], ['build-failed:bld_3'])

    def test_the_production_worker_wraps_its_jobs_and_announces(self):
        src = inspect.getsource(worker_tasks._run_live_build_job_with_components)
        self.assertIn('witness = FailureWitness(jobs)', src)
        self.assertIn('jobs=witness,', src)
        self.assertIn('announce_if_failed(witness', src)
        self.assertLess(src.index('try:'), src.index('jobs=witness,'))
        self.assertLess(src.index('jobs=witness,'), src.index('finally:'))


if __name__ == '__main__':
    unittest.main()

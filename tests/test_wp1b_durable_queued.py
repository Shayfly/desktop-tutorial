"""WP1b: the spec survives between messages on different machines, and the question's model phrasing goes through
the same reserved worker queue as interpretation (the six WP1 model conditions hold there too)."""
from __future__ import annotations

import json
import unittest
from decimal import Decimal

from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import budget as B
from omni_prod.intake.gaps import Questioner, Spec, fallback_text
from tests.test_conversation_os import MemoryBriefs
from tests.test_intake_worker_route import FakeService, interp, settled


class SpecSurvivesBetweenMachines(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()   # shared: the database

    def machine(self):
        return ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {})

    def test_turn_two_on_another_machine_continues_the_spec(self):
        t1 = self.machine().turn(project_id='p', account_id='a', message='אני רוצה אתר למספרה שלי')
        self.assertEqual(t1.gaps['question']['field'], 'content_only')
        t2 = self.machine().turn(project_id='p', account_id='a', message='תחליט אתה')     # a new process
        self.assertEqual(t2.gaps['kind'], 'website')                    # a follow-up does not reset the kind
        self.assertIn('content_only', t2.gaps['known'])
        self.assertNotEqual(t2.gaps['question']['field'], 'content_only')  # not asked again
        self.assertEqual(t2.gaps['metrics']['questions'], 2)           # the log came with the spec
        stored = [m for m in self.store.messages if m['role'] == 'assistant'][-1]
        self.assertEqual(stored['interpretation']['gap_spec']['schema'], 'gap-spec/1')
        self.assertNotIn('spec', t2.to_dict('he')['gaps'])              # the snapshot is stored, not sent to the UI

    def test_round_trip_keeps_the_spec_and_a_tampered_quote_comes_back_unsourced(self):
        s = Spec('website')
        s.hear('אתר לסטודנטים', [type('P', (), {'field': 'audience', 'value': 'public', 'evidence': 'לסטודנטים'})()])
        Questioner().next(s)
        again = Spec.from_dict(json.loads(json.dumps(s.to_dict())))
        self.assertEqual((again.detect(), again.fingerprint(), len(again.log)), (s.detect(), s.fingerprint(), 1))
        snap = s.to_dict()
        snap['items'][0]['span']['quote'] = 'לכולם'                      # edited in storage
        self.assertNotIn('audience', Spec.from_dict(snap).detect()['known'])
        with self.assertRaises(ValueError):
            Spec.from_dict({'schema': 'other'})


def queued(final=None, **kw):
    svc = FakeService(final=final, **kw)
    return svc, interp(svc)


def spec(lang_msg='אני רוצה אתר למספרה שלי'):
    s = Spec('website')
    s.hear(lang_msg)
    return s


class QuestionThroughTheQueue(unittest.TestCase):
    def ok(self, raw):
        return settled(B.SETTLED, B.ESTIMATED, Decimal('0.0003'), {'ok': True, 'raw': raw})

    def test_focused_question_one_reservation_only_what_is_missing(self):
        svc, w = queued(self.ok({'field': 'content_only', 'question': 'האתר יציג מידע בלבד או ישמור פרטים? אפשר גם "תחליט אתה".'}))
        q = Questioner(w.complete_json).next(spec())
        self.assertEqual((q.source, q.field), ('model', 'content_only'))
        self.assertEqual(len(svc.reserved), 1)                          # one call, no loop
        payload = svc.reserved[0]['payload']
        self.assertEqual(json.loads(payload['user'])['missing'], {'field': 'content_only', 'why_it_matters': 'saves_records'})
        self.assertEqual(payload['task'], 'conversation')               # the same priced task and budget
        self.assertTrue(svc.reserved[0]['idempotency_key'].startswith('intake-question:acct:p:rk:'))
        self.assertEqual(w.last_reservation['actual_usd'], '0.0003')

    def test_unfocused_or_ascii_only_from_the_queue_falls_back(self):
        for raw, why in (({'field': 'color', 'question': 'איזה צבע?'}, 'unfocused'),
                         ({'field': 'content_only', 'question': 'Will it store visitor data?'}, 'ascii_only')):
            _, w = queued(self.ok(raw))
            q = Questioner(w.complete_json).next(spec())
            self.assertEqual((q.source, q.text), ('fallback', fallback_text('saves_records', 'he')))
            self.assertTrue(q.rejected.startswith(why))

    def test_budget_exhausted_pending_or_released_never_blocks_the_question(self):
        cases = (dict(reserve_exc=B.BudgetExceeded('project:p', Decimal('0.5'), Decimal('0.5'), Decimal('0.01'))), dict(never_settles=True),
                 dict(final=settled(B.RELEASED, None, None, None)))
        for kw in cases:
            svc, w = queued(**kw)
            q = Questioner(w.complete_json).next(spec())
            self.assertEqual((q.source, q.field), ('fallback', 'content_only'), kw)
            self.assertTrue(q.rejected.startswith('error'), kw)
            self.assertLessEqual(len(svc.reserved), 1)


if __name__ == '__main__':
    unittest.main()

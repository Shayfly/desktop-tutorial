"""C6 (CEO 2026-10-27): the gap detector decides when the spec is complete; the catalog is only the fallback.

The experiment in docs/evidence/intake-2026-10-27 (main b97114c) showed the opposite: deleting the fixed question
catalog marked the brief complete from the first message and the detector's question was never shown."""
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

TOURISTS = 'אני רוצה אתר לתיירים שמגיעים לעיר'


def sup(briefs=None, store=None):
    return ConversationSupervisor(briefs=briefs or MemoryBriefs(), store=store or MemoryConversationStore())


class DeletingTheCatalogDoesNotStopTheQuestions(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.multiple(d, QUESTIONS=(), BY_ID={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_detectors_question_is_asked_and_the_brief_is_not_complete(self):
        s = sup()
        for said in (TOURISTS, 'תחליט אתה', 'תחליט אתה'):
            t = s.turn(project_id='p', account_id='a', message=said)
            asked = t.gaps['question']['field'] if t.gaps and t.gaps.get('question') else None
            if asked is None:
                break
            self.assertIn(t.gaps['question']['text'], t.reply)          # shown, not swallowed
            self.assertFalse(t.brief_row.complete)                       # open while the detector asks
            self.assertEqual(t.brief_row.brief.open_material, [asked])
            self.assertNotIn('לא זיהיתי פרטים חדשים', t.reply)

    def test_the_conversation_keeps_going_until_the_detector_is_satisfied(self):
        s, asked = sup(), []
        t = s.turn(project_id='p', account_id='a', message=TOURISTS)
        for _ in range(12):
            if not t.gaps or not t.gaps.get('question'):
                break
            asked.append(t.gaps['question']['field'])
            t = s.turn(project_id='p', account_id='a', message='תחליט אתה')
        self.assertGreaterEqual(len(asked), 2)                           # more than one question, no catalog at all
        self.assertEqual(len(asked), len(set(asked)))                    # never the same field twice
        self.assertTrue(t.brief_row.complete)                            # the detector, satisfied, closes the spec


class TheDetectorDecides(unittest.TestCase):
    def test_complete_by_the_catalog_is_not_complete_while_the_detector_asks(self):
        s = sup()
        s.turn(project_id='p', account_id='a', message='אני רוצה מערכת לניהול תורים למספרה שלי, בלי התחברות, הלקוחות ישאירו טלפון', lang='he')
        s.turn(project_id='p', account_id='a', answers={'personal_data': 'yes'}, lang='he')
        t = s.turn(project_id='p', account_id='a', answers={'access_scope': 'internal_link'}, lang='he')
        self.assertTrue(d.catalog_complete(t.brief_row.brief))
        self.assertFalse(t.brief_row.complete)
        self.assertEqual(d.missing(t.brief_row.brief)['pending'][0]['id'], t.brief_row.brief.open_material[0])

    def test_a_field_being_asked_is_not_also_announced_as_chosen(self):
        t = sup().turn(project_id='p', account_id='a', message=TOURISTS)
        self.assertEqual(t.gaps['question']['field'], 'languages')
        self.assertNotIn('שפה: עברית', t.reply)                          # was: "שפה: עברית" + "באיזו שפה?" together

    def test_the_open_field_is_not_part_of_the_approval_fingerprint(self):
        b = d.Brief('x', detector=True, open_material=['style'])
        self.assertEqual(b.fingerprint(), d.Brief('x', detector=True, open_material=[]).fingerprint())
        self.assertEqual(d.Brief.from_dict(b.to_dict()).open_material, ['style'])

    def test_a_brief_from_before_c6_keeps_the_catalog_rule_and_its_fingerprint(self):
        old = d.Brief('x')
        self.assertNotIn('detector', old.to_dict())
        self.assertEqual(d.complete(old), d.catalog_complete(old))


class TheCatalogIsTheFallback(unittest.TestCase):
    def test_a_security_choice_the_detector_did_not_ask_is_still_asked(self):
        b = d.Brief('x', detector=True, open_material=[])
        self.assertIn('login', [q.field for q in d.must_ask(b)])
        self.assertFalse(d.complete(b))


class AnotherServerDoesNotForget(unittest.TestCase):
    def test_a_fresh_supervisor_on_the_same_durable_store_does_not_reask(self):
        briefs, store = MemoryBriefs(), MemoryConversationStore()
        t1 = sup(briefs, store).turn(project_id='p', account_id='a', message=TOURISTS)
        first = t1.gaps['question']['field']
        t2 = sup(briefs, store).turn(project_id='p', account_id='a', message='תחליט אתה')   # a different server
        self.assertIsNotNone(t2.gaps)
        self.assertNotEqual((t2.gaps.get('question') or {}).get('field'), first)
        self.assertGreaterEqual(t2.gaps['metrics']['questions'], 2)                      # the replayed log counts


if __name__ == '__main__':
    unittest.main()

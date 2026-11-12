"""Shadow IntakeDecision (docs/design/persistence-migration.md, signed with C1-C3 by Michael 2026-11-11)."""
from __future__ import annotations

import json
import logging
import os
import unittest
from unittest import mock

from omni_prod import discovery as d
from omni_prod.intake import decision as D
from omni_prod.intake import decision_shadow as S

FLORIST = ('תבנה לי דף לחנות הפרחים שלי, "שושנת העמקים". שיהיה כפתור להתקשר וכפתור וואטסאפ, עם הודעה מוכנה '
           '"היי, אשמח להזמין זר". אנחנו פתוחים א\'–ה\' 8:00–19:00.')
AID = D.new_artifact_id(now_ms=1_762_860_000_000, randomness=bytes(range(10)))


def brief_with(**fields):
    b = d.start(FLORIST)
    for name, (value, source) in fields.items():
        b.fields[name] = {'value': value, 'source': source, 'question_id': name, 'confidence': 'confirmed'}
    return b


def persistence_of(brief):
    return S.decision_from_brief(brief, artifact_id=AID).artifacts[0].persistence


class ChannelIsDerived(unittest.TestCase):
    """§1 of the sketch: one test per row -- the channel comes from where the value was written."""

    def test_a_chip_answer_is_a_button(self):
        self.assertEqual(persistence_of(brief_with(content_only=('yes', 'answer'))), D.from_button('none'))

    def test_typed_text_is_text_not_a_stated_decision(self):
        f = persistence_of(brief_with(content_only=('yes', 'message')))
        self.assertEqual(f, D.from_text('none'))
        dec = S.decision_from_brief(brief_with(content_only=('yes', 'message')), artifact_id=AID)
        self.assertTrue(any(v.where.endswith('.persistence') and v.stop for v in D.validate(dec)))   # G2 holds

    def test_a_hint_is_inferred(self):
        b = d.start(FLORIST)
        b.hints['content_only'] = 'yes'
        self.assertEqual(persistence_of(b), D.inferred('none', by_model=True))

    def test_absent_is_missing_and_never_none(self):
        self.assertEqual(persistence_of(d.start(FLORIST)), D.MISSING)        # null is never read as "none"

    def test_kind_from_the_classifier_is_never_stated(self):
        k = S.decision_from_brief(d.start(FLORIST), artifact_id=AID).artifacts[0].kind
        self.assertEqual(k.conf, 'inferred')


class Shadow(unittest.TestCase):
    def test_a_valid_chip_decision_is_stored_and_clean(self):
        b = brief_with(content_only=('yes', 'answer'), login=('none', 'answer'), personal_data=('no', 'answer'))
        with self.assertNoLogs('omni_prod.intake.decision_shadow', level='WARNING'):
            payload = S.stored_payload(b, project_id='p1')
        dec = D.from_dict(payload['decision'])
        self.assertEqual(dec.artifacts[0].persistence, D.from_button('none'))
        self.assertEqual(D.validate(dec, revision_raw_brief=b.prompt), [])

    def test_a_violation_is_logged_never_raised(self):
        b = brief_with(content_only=('yes', 'message'))          # typed: would not count once enforced
        with self.assertLogs('omni_prod.intake.decision_shadow', level='WARNING') as logs:
            payload = S.stored_payload(b, project_id='p1')
        self.assertTrue(any('intake_decision_violation' in m and '.persistence' in m for m in logs.output))
        self.assertIn('decision', payload)

    def test_a_crash_inside_the_shadow_is_a_log_line(self):
        with mock.patch.object(S, 'decision_from_brief', side_effect=RuntimeError('boom')), \
                self.assertLogs('omni_prod.intake.decision_shadow', level='WARNING') as logs:
            payload = S.stored_payload(d.start(FLORIST), project_id='p1')
        self.assertNotIn('decision', payload)
        self.assertIn('SHADOW_ERROR', logs.output[0])

    def test_the_artifact_id_is_stable_across_revisions(self):
        first = S.stored_payload(d.start(FLORIST), project_id='p1')
        aid = S.previous_artifact_id(first)
        self.assertTrue(D.is_artifact_id(aid))
        second = S.stored_payload(brief_with(content_only=('yes', 'answer')), project_id='p1', previous_artifact_id=aid)
        self.assertEqual(S.previous_artifact_id(second), aid)

    def test_off_stores_nothing(self):
        with mock.patch.dict(os.environ, {S.MODE_ENV: 'off'}):
            self.assertNotIn('decision', S.stored_payload(d.start(FLORIST), project_id='p1'))


class ShadowChangesNothing(unittest.TestCase):
    """C3: the same conversation with the shadow on and off -> byte-identical contracts, questions, decision_asked."""

    def run_conversation(self, shadow: bool):
        from omni_prod.conversation.supervisor import ConversationSupervisor
        from omni_prod.product_architect import ProductArchitect
        from tests.test_conversation_os import MemoryBriefs, MemoryConversationStore

        class Store(MemoryBriefs):
            def save(self, *, project_id, account_id, brief, expected_revision, request_key=None):
                cur = self.latest(project_id)
                if (cur.revision if cur else 0) != expected_revision:
                    from omni_prod.brief_repository import StaleBrief
                    raise StaleBrief('stale')
                payload = (S.stored_payload(brief, project_id=project_id) if shadow else brief.to_dict())
                row = self.Row(expected_revision + 1, d.Brief.from_dict(json.loads(json.dumps(payload))))
                row.stored = payload
                self.rows.setdefault(project_id, []).append(row)
                return row

        briefs, store = Store(), MemoryConversationStore()
        sup = ConversationSupervisor(briefs=briefs, store=store, credits=10, context=lambda p: {})
        turns = [sup.turn(project_id='p1', account_id='a1', message=FLORIST)]
        for answers in ({'login': 'none', 'personal_data': 'no'}, {'content_only': 'yes'}):
            turns.append(sup.turn(project_id='p1', account_id='a1', answers=answers, lang='he'))
        rows = briefs.rows['p1']
        last = rows[-1].brief
        contract = ProductArchitect().compile(last.prompt + d.requirements_text(last), project_id='p1',
                                              contract_version=1, created_at='2026-11-11T00:00:00+00:00').to_dict()
        out = {
            'fingerprints': [r.fingerprint for r in rows],
            'requirements_text': d.requirements_text(last),
            'questions': [[q.id for q in t.questions] for t in turns],
            'messages': [(m['role'], m['content'], {k: v for k, v in (m.get('interpretation') or {}).items()
                                                    if k not in ('reservation_id',)})
                         for m in store.messages_for('p1')],
            'contract': contract,
        }
        return out, [getattr(r, 'stored', None) for r in rows]

    def test_shadow_on_and_off_are_identical(self):
        with mock.patch.dict(os.environ, {S.MODE_ENV: 'off'}):
            off, _ = self.run_conversation(shadow=True)
        on, stored = self.run_conversation(shadow=True)
        self.assertTrue(any(p and 'decision' in p for p in stored), 'the shadow did not run')
        self.assertEqual(json.dumps(on, sort_keys=True, ensure_ascii=False, default=str),
                         json.dumps(off, sort_keys=True, ensure_ascii=False, default=str))

    def test_no_v2_line_is_written_in_shadow(self):
        on, _ = self.run_conversation(shadow=True)
        self.assertNotIn('Product decisions v2', on['requirements_text'])
        self.assertNotIn('Product decisions v2', on['contract']['prompt'])


if __name__ == '__main__':
    unittest.main()

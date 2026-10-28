"""The question loop (reproduced 2026-10-28 on main 482a271 and on d2a658b, before #154/#162).

"אתר לחנות פרחים עם טופס הזמנה", then the quick-reply buttons personal_data=yes, access_scope=internal_link,
content_only=yes, audience=internal: the fifth turn asked personal_data AGAIN although the brief held
('yes', 'answer'). Three causes, each pinned here:
  1. the label of content_only=yes ("...בלי שמירת נתונים") was read as another product family and wiped the spec;
  2. the detector's question was not checked against the brief (it asked decided / inapplicable fields);
  3. the spec lived in the process (`_gap_specs`), so another server asked from scratch.
The repeat rule (Matt 2026-10-28) is state-dependent: the previous field comes back only after "what?" or when the
answer contradicts a confirmed value.
"""
import os
import pathlib
import unittest
import uuid

from omni_prod import discovery as d
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs

ROOT = pathlib.Path(__file__).resolve().parents[1]
FLOWERS = 'אתר לחנות פרחים עם טופס הזמנה'
LOOP = ({'personal_data': 'yes'}, {'access_scope': 'internal_link'}, {'content_only': 'yes'}, {'audience': 'internal'})


def asked(t):
    return ((t.gaps or {}).get('question') or {}).get('field') or (t.questions[0].id if t.questions else None)


class Conversation:
    """One project; `fresh=True` builds a NEW supervisor for every turn (another server / a new instance)."""

    def __init__(self, briefs=None, store=None, fresh=False):
        self.briefs, self.store, self.fresh = briefs or MemoryBriefs(), store or MemoryConversationStore(), fresh
        self.pid, self._sup = f'p{uuid.uuid4().hex[:8]}', None
        self.account = 'a'

    def sup(self):
        if self.fresh or self._sup is None:
            self._sup = ConversationSupervisor(briefs=self.briefs, store=self.store)
        return self._sup

    def say(self, message):
        return self.sup().turn(project_id=self.pid, account_id=self.account, message=message, lang='he')

    def click(self, answers):
        return self.sup().turn(project_id=self.pid, account_id=self.account, answers=answers, lang='he')

    def decided(self):
        b = self.briefs.latest(self.pid).brief
        return {k for k, f in b.fields.items() if f.get('source') in ('answer', 'message')}


def the_loop(c):
    """The reproduced sequence; returns the field asked after each click."""
    c.say(FLOWERS)
    return [asked(c.click(a)) for a in LOOP]


class TheLoopIsGone(unittest.TestCase):
    def test_the_reproduced_sequence_never_reasks_an_answered_field(self):
        c = Conversation()
        out = the_loop(c)
        self.assertNotEqual(out[-1], 'personal_data', out)               # the loop: personal_data asked again
        for i, f in enumerate(out):
            self.assertNotIn(f, {k for a in LOOP[:i + 1] for k in a}, (i, out))

    def test_two_buttons_in_a_row_the_previous_field_is_not_asked_again(self):
        c = Conversation()
        first = asked(c.say(FLOWERS))
        t1 = c.click({first: d.BY_ID[first].options[0].value})
        second = asked(t1)
        self.assertNotEqual(second, first)
        t2 = c.click({second: d.BY_ID[second].options[0].value})
        self.assertNotIn(asked(t2), {first, second})

    def test_words_that_fill_nothing_do_not_bring_the_same_question_back(self):
        c = Conversation()
        first = asked(c.say(FLOWERS))
        self.assertIsNotNone(first)
        t = c.say('לא יודע, משהו יפה')                                  # not "what?": an answer that maps to nothing
        self.assertNotEqual(asked(t), first)

    def test_a_label_that_reads_as_another_family_does_not_reset_the_spec(self):
        c = Conversation()
        c.say(FLOWERS)
        c.click({'personal_data': 'yes'})
        t = c.click({'content_only': 'yes'})                             # label "...בלי שמירת נתונים" -> web_app
        self.assertEqual(t.gaps['kind'], 'website')
        spec, _, _ = c.sup()._replayed_spec(c.pid)                       # what was said is still known
        self.assertEqual((spec.kind, spec.value('personal_data')), ('website', 'yes'))
        self.assertNotEqual(asked(t), 'personal_data')

    def test_a_decided_or_inapplicable_field_is_never_offered(self):
        c = Conversation()
        c.say(FLOWERS)
        for answers in LOOP:
            t = c.click(answers)
            closed = ConversationSupervisor._closed_in_brief(c.briefs.latest(c.pid).brief)
            self.assertTrue(c.decided() <= closed)
            self.assertNotIn(asked(t), closed, (answers, asked(t)))
        # the reproduced trace asked content_only after access_scope although it no longer applied (pending=[]),
        # and the answer was swallowed without a revision
        c2 = Conversation()
        self.assertNotEqual(the_loop(c2)[1], 'content_only')


class TheRepeatRule(unittest.TestCase):
    def test_what_brings_the_same_question_back_explained(self):
        c = Conversation()
        first = asked(c.say(FLOWERS))
        t = c.say('מה?')                                                 # did not understand: repeat allowed
        self.assertEqual(asked(t), first)
        self.assertTrue(t.explained)

    def test_the_rule_itself(self):
        rule = ConversationSupervisor._askable
        missing = ['a', 'b', 'c']
        self.assertEqual(rule(missing, set(), 'a'), ['b', 'c'])                         # settled: not again
        self.assertEqual(rule(missing, set(), 'b', unsure=True), ['b', 'a', 'c'])       # "what?": again, first
        self.assertEqual(rule(missing, set(), 'a', contested={'a'}), ['a', 'b', 'c'])   # contradicted: may return
        self.assertEqual(rule(missing, {'a'}, 'a', unsure=True), ['b', 'c'])            # closed by the brief: never


class Clarifications(unittest.TestCase):
    """Owner + Matt 2026-10-28: "לא הבנתי" repeats once, explained, then moves on; "לא יודע" never repeats (the
    default, shown as an assumption); a field with no valid default gets one explained repeat, then is held OPEN."""

    def first_question(self, c, want):
        t = c.say(FLOWERS)
        for _ in range(6):                                              # click through to the field under test
            if asked(t) == want:
                return t
            f = asked(t)
            t = c.click({f: d.BY_ID[f].options[0].value})
        self.fail(f'{want} was never asked')

    def test_not_understood_repeats_once_explained_then_moves_on(self):
        c = Conversation()
        t0 = self.first_question(c, 'style')                           # style has a valid default ('clean')
        t1 = c.say('לא הבנתי')
        self.assertEqual(asked(t1), 'style')                            # once more ...
        self.assertTrue(t1.explained)                                   # ... explained
        t2 = c.say('לא הבנתי')
        self.assertNotEqual(asked(t2), 'style')                         # then the conversation moves on
        self.assertEqual(c.briefs.latest(c.pid).brief.fields['style']['value'], 'clean')

    def test_dont_know_does_not_repeat_and_the_default_is_shown(self):
        c = Conversation()
        self.first_question(c, 'style')
        t = c.say('לא יודע')
        self.assertNotEqual(asked(t), 'style')                          # not asked again
        f = c.briefs.latest(c.pid).brief.fields['style']
        self.assertEqual((f['value'], f['source']), ('clean', 'default'))   # the default, visible in the brief
        from omni_prod.conversation.supervisor import _label
        self.assertIn(_label('style', 'clean', 'he'), t.reply)        # ... and said to the customer

    def test_no_valid_default_one_repeat_then_held_open_not_a_loop(self):
        c = Conversation()
        t0 = c.say(FLOWERS)
        self.assertEqual(asked(t0), 'personal_data')                    # sensitive: no valid default to assume
        t1 = c.say('לא יודע')
        self.assertEqual(asked(t1), 'personal_data')                    # one repeat, explained
        self.assertTrue(t1.explained)
        t2 = c.say('לא יודע')
        self.assertNotEqual(asked(t2), 'personal_data')                 # not a loop ...
        b = c.briefs.latest(c.pid).brief
        self.assertIn('personal_data', b.open_material)                 # ... held as an OPEN field
        self.assertFalse(c.briefs.latest(c.pid).complete)
        self.assertNotIn('personal_data', b.fields if b.fields.get('personal_data', {}).get('source') == 'default'
                         else {})                                       # never silently assumed
        t3 = c.say('משהו')
        self.assertNotEqual(asked(t3), 'personal_data')                 # still not asked again by itself


class TheModelLeads(unittest.TestCase):
    class Gateway:
        def __init__(self, pick):
            self.pick, self.calls = pick, []

        def complete_json(self, *, system, user, **_):
            import json
            payload = json.loads(user)
            self.calls.append(payload)
            field = self.pick([m['field'] for m in payload['missing']])
            return {'field': field, 'question': 'שאלה קצרה שהמודל ניסח? אפשר גם "תחליט אתה".'}

    def ask(self, pick):
        from omni_prod.intake.gaps import Questioner, Spec
        spec = Spec('website', [])
        spec.hear(FLOWERS, ())
        gw = self.Gateway(pick)
        allowed = spec.detect()['missing_material']
        return Questioner(gw.complete_json).next(spec, allowed=allowed), gw, allowed

    def test_the_model_chooses_one_field_from_the_list(self):
        q, gw, allowed = self.ask(lambda fields: fields[-1])
        self.assertEqual(len(gw.calls), 1)
        self.assertGreater(len(gw.calls[0]['missing']), 1)               # a list, not one forced question
        self.assertEqual((q.source, q.field), ('model', gw.calls[0]['missing'][-1]['field']))

    def test_a_field_outside_the_list_is_refused(self):
        q, gw, allowed = self.ask(lambda fields: 'personal_data_already_answered')
        self.assertEqual(q.source, 'fallback')
        self.assertTrue(q.rejected.startswith('unfocused'))
        self.assertEqual(q.field, allowed[0])


class ANewInstanceDoesNotReask(unittest.TestCase):
    """Every turn on a NEW supervisor over the same store: nothing is kept in a process."""

    def test_new_instance_each_turn_memory_store(self):
        out = the_loop(Conversation(fresh=True))
        self.assertNotIn('personal_data', out[1:], out)
        shown = [f for f in out if f]
        self.assertEqual(len(shown), len(set(shown)), out)              # no field asked twice


DATABASE_URL = os.getenv('M4D2_DATABASE_URL', '').strip()


class ANewInstanceDoesNotReaskOnPostgres(unittest.TestCase):
    """The same, against the REAL stores: PostgresConversationStore + PostgresBriefRepository on a fresh database
    with every repository migration applied. Runs in intake-budget-pg, where a skip is an error."""

    @classmethod
    def setUpClass(cls):
        if not DATABASE_URL:
            raise unittest.SkipTest('BLOCKED: M4D2_DATABASE_URL (real PostgreSQL) not configured')
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'nrq_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(ROOT / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def conversation(self):
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.conversation.store import PostgresConversationStore
        account, project = f'acc_{uuid.uuid4().hex[:10]}', f'prj_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                         (account, f'{account}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (project, account))
            conn.commit()

        class Fresh(Conversation):
            def sup(inner):                                    # new repositories AND a new supervisor every turn
                return ConversationSupervisor(briefs=PostgresBriefRepository(self.pool),
                                              store=PostgresConversationStore(self.pool))
        c = Fresh(PostgresBriefRepository(self.pool), PostgresConversationStore(self.pool), fresh=True)
        c.pid, c.account = project, account
        return c

    def test_new_instance_each_turn_real_store(self):
        c = self.conversation()
        out = the_loop(c)
        self.assertNotIn('personal_data', out[1:], out)
        shown = [f for f in out if f]
        self.assertEqual(len(shown), len(set(shown)), out)              # no field asked twice
        stored = [m for m in c.store.messages_for(c.pid) if m['role'] == 'customer']
        self.assertEqual(stored[1]['interpretation'].get('answers'), {'personal_data': 'yes'})   # replayable from the DB
        self.assertTrue(c.decided() >= {'personal_data'})


if __name__ == '__main__':
    unittest.main()

"""The customer's words are not cut silently (the owner, 2026-11-26, WAREHOUSE 136 option a: a limit that is not money
is cancelled; a bound that remains is stated, logged and said to the customer when it applies).

  the model reads the whole message, up to the conversation's message limit (it read only the first 4,000 characters)
  the build prompt keeps every approved decision (the 12,000-character cut removed the decisions, appended last);
  past its bound the request's oldest words go, said in the prompt, the build evidence and the plan, in words
  a new brief carries the customer's earlier messages (5 and 12,000 characters before, the oldest dropped silently);
  a drop is said in the reply and stored with it
  the model's reply, requirements and proposals have raised bounds; a bound that applies is said, never only noted
  the customer's own page outline: 60 sections and 4,000 characters a section (20 and 400 before); past them, said
  in the spec the customer approves

The real interpreter, discovery, supervisor (memory stores, as tests/test_a_refused_message_is_still_the_request.py),
rehearsal prompt, worker evidence function and page outline; only the model is a double that never contacts a
provider."""
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod import page_outline as PO
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import interpreter as I

sys.path.insert(0, os.path.dirname(__file__))
from test_conversation_os import MemoryBriefs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REQUEST = ('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234. כתובת: רחוב הרצל 12, חולון. '
           'אתר תוכן בלבד, לא שומרים כלום.')


class Gateway:
    """A model double that never contacts a provider (an empty attempt ledger); records what it was sent."""
    accepts_call_id = True

    def __init__(self, raw=None):
        self.seen, self.raw = None, raw
        self.recorder = type('R', (), {'records': []})()

    def complete_json(self, **kw):
        self.seen = kw
        return self.raw or {'language': 'he', 'product_family': 'website', 'proposals': []}


class TheModelReadsTheWholeMessage(unittest.TestCase):
    def test_the_bound_is_the_conversations_message_limit(self):
        source = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        limit = re.search(r"class V28ConversationMessage\(BaseModel\):\s*\n\s*message: str = Field\(default='', "
                          r"max_length=(\d+)\)", source)
        self.assertIsNotNone(limit)
        self.assertEqual(I.MAX_MESSAGE_CHARS, int(limit.group(1)))
        self.assertEqual(I.MAX_MESSAGE_CHARS, 8000)

    def test_a_message_at_the_limit_reaches_the_model_whole(self):
        message = ('אני רוצה אתר לסטודיו. ' * 400)[:I.MAX_MESSAGE_CHARS - 1] + 'ס'    # 8,000 characters, the last one ס
        g = Gateway()
        I.ModelInterpreter(g).interpret(message)
        self.assertTrue(g.seen['user'].endswith(message), g.seen['user'][-80:])
        self.assertGreater(len(message), 4000)                    # the old bound would have cut it here

    def test_a_longer_message_from_an_internal_caller_is_noted_and_logged(self):
        with self.assertLogs('omni_prod.intake.interpreter', 'WARNING') as logs:
            out = I.ModelInterpreter(Gateway()).interpret('א' * (I.MAX_MESSAGE_CHARS + 50))
        self.assertTrue(any('INTAKE_MESSAGE_CUT' in line for line in logs.output))
        self.assertTrue(any('message cut to its first 8000 of 8050 characters' in n for n in out.dropped), out.dropped)


class TheModelsOutput(unittest.TestCase):
    def valid(self, raw, message='אתר למספרה'):
        model, dropped = I.validate_model_output({'language': 'he', 'product_family': 'website', **raw}, message)
        self.assertIsNotNone(model)
        return model

    def test_a_reply_of_3000_characters_is_kept_whole(self):
        reply = ('הבנתי שאתם צריכים אתר למספרה. ' * 120)[:3000]
        model = self.valid({'reply': reply})
        self.assertEqual(model.reply, reply.strip())
        self.assertEqual(model.notices, [])

    def test_a_reply_past_the_bound_is_cut_at_a_sentence_and_says_so(self):
        reply = 'הבנתי שאתם צריכים אתר למספרה. ' * 200                # 6,000 characters
        with self.assertLogs('omni_prod.intake.interpreter', 'WARNING') as logs:
            model = self.valid({'reply': reply})
        self.assertLessEqual(len(model.reply), I.MAX_REPLY_CHARS + 200)
        self.assertTrue(model.reply.endswith(I._NOTICE['reply_cut']['he']))
        self.assertEqual([n['kind'] for n in model.notices], ['reply_cut'])
        self.assertTrue(any('INTAKE_OUTPUT_BOUND kind=reply_cut' in line for line in logs.output))
        self.assertTrue(any('reply of 6000 characters cut' in n for n in model.dropped))
        self.assertIn('notices', model.to_dict())

    def test_forty_requirements_and_a_long_one_are_kept(self):
        reqs = [f'דרישה מספר {i} של הלקוח' for i in range(40)] + ['א' * 500]
        model = self.valid({'requirements': reqs})
        self.assertEqual(len(model.requirements), 41)               # 12 before; the 500-character one was dropped
        self.assertEqual(model.notices, [])

    def test_requirements_past_their_bounds_are_said(self):
        reqs = [f'דרישה {i}' for i in range(I.MAX_REQUIREMENTS + 5)]
        reqs[0] = 'ב' * (I.MAX_REQUIREMENT_CHARS + 10)
        model = self.valid({'requirements': reqs})
        self.assertEqual(len(model.requirements), I.MAX_REQUIREMENTS)
        self.assertEqual(len(model.requirements[0]), I.MAX_REQUIREMENT_CHARS)
        self.assertEqual([n['kind'] for n in model.notices], ['model_output_cut'])          # one notice, two notes
        self.assertEqual(len([n for n in model.dropped if 'requirement' in n]), 2)

    def test_a_valid_proposal_after_thirty_invalid_ones_is_read(self):
        junk = [{'field': 'nope', 'value': 'x', 'confidence': 'high', 'evidence': 'x'}] * 30
        good = {'field': 'login', 'value': 'none', 'confidence': 'high', 'evidence': 'בלי התחברות'}
        model = self.valid({'proposals': junk + [good]}, message='אתר בלי התחברות')
        self.assertIn('login', [p.field for p in model.proposals])  # the 30 cut dropped it before
        self.assertEqual(model.notices, [])

    def test_the_notices_survive_the_merge_and_reach_the_stored_turn(self):
        reply = 'הבנתי שאתם צריכים אתר למספרה. ' * 200
        out = I.ModelInterpreter(Gateway({'language': 'he', 'product_family': 'website', 'proposals': [],
                                          'reply': reply})).interpret('אתר למספרה')
        self.assertEqual([n['kind'] for n in out.notices], ['reply_cut'])
        self.assertEqual(out.to_dict()['notices'][0]['kind'], 'reply_cut')


def long_request(chars: int) -> str:
    text = REQUEST + '\n' + 'פרטים נוספים על הסטודיו והשירותים שלו. ' * (chars // 38 + 1)
    return text[:chars]


class TheBuildPrompt(unittest.TestCase):
    def test_a_request_past_the_old_cut_keeps_every_decision(self):
        brief = d.start(long_request(20_000))
        decisions = d.requirements_text(brief)
        prompt, cut = d.build_prompt(brief)
        self.assertIsNone(cut)
        self.assertTrue(prompt.endswith(decisions))
        self.assertIn(brief.prompt, prompt)
        old = (brief.prompt + '\n' + decisions)[:12000]             # the old cut: the decisions were what it removed
        self.assertNotIn(d.BRIEF_MARKER, old)
        self.assertIn(d.BRIEF_MARKER, prompt)

    def test_past_the_bound_the_oldest_words_go_and_it_is_said(self):
        brief = d.start(long_request(d.BUILD_PROMPT_MAX + 5_000))
        decisions = d.requirements_text(brief)
        with self.assertLogs('omni_prod.discovery', 'WARNING') as logs:
            prompt, cut = d.build_prompt(brief)
        self.assertLessEqual(len(prompt), d.BUILD_PROMPT_MAX)
        self.assertIn(decisions, prompt)                            # every decision, whole
        self.assertTrue(brief.prompt.endswith(prompt.split('\n' + decisions)[0]))      # the newest words kept
        self.assertEqual(cut['dropped_chars'] + cut['kept_chars'], len(brief.prompt))
        self.assertEqual(d.request_cut_of(prompt), cut)             # the line in the prompt says the same
        self.assertTrue(any('BUILD_PROMPT_CUT' in line for line in logs.output))
        said = d.request_cut_message(cut, 'he')
        self.assertIn(f"{cut['dropped_chars']:,}", said)
        self.assertIn('ההחלטות שאישרתם נכנסות במלואן', said)
        self.assertIn('Every decision you approved goes in whole', d.request_cut_message(cut, 'en'))

    def test_decisions_that_alone_fill_the_bound_refuse_out_loud(self):
        brief = d.start(REQUEST)
        with mock.patch.object(d, 'requirements_text', return_value='x' * d.BUILD_PROMPT_MAX):
            with self.assertRaises(ValueError):
                d.build_prompt(brief)

    def test_every_place_that_built_the_prompt_uses_the_one_function(self):
        for path in ('omni_prod/investor_app.py', 'omni_prod/conversation/supervisor.py', 'omni_prod/rehearsal.py'):
            source = (ROOT / path).read_text(encoding='utf-8')
            self.assertNotIn("requirements_text(row.brief))[:12000]", source, path)
            self.assertNotIn("requirements_text(brief))[:12000]", source, path)
            self.assertIn('build_prompt(', source, path)

    def test_the_rehearsal_prompt_is_the_customers_and_keeps_the_decisions(self):
        from omni_prod.rehearsal import approved_prompt
        prompt = approved_prompt(long_request(20_000), {'login': 'none', 'personal_data': 'no', 'content_only': 'yes'})
        self.assertIn(d.BRIEF_MARKER, prompt)
        self.assertGreater(len(prompt), 20_000)

    def test_the_build_evidence_records_the_cut(self):
        from omni_prod import worker_tasks as W
        brief = d.start(long_request(d.BUILD_PROMPT_MAX + 5_000))
        prompt, cut = d.build_prompt(brief)
        self.assertEqual(W._request_cut_evidence(prompt), cut)
        self.assertIsNone(W._request_cut_evidence(d.build_prompt(d.start(REQUEST))[0]))
        source = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        self.assertEqual(source.count("'request_cut': _request_cut_evidence(prompt)"), 2)       # success and failure


class ANewBriefCarriesTheEarlierMessages(unittest.TestCase):
    def setUp(self):
        self.briefs, self.store = MemoryBriefs(), MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store, credits=10, context=lambda p: {})

    def say(self, msg):
        return self.sup.turn(project_id='p1', account_id='a1', message=msg, lang='he')

    def test_eight_long_messages_are_all_carried_now(self):
        for i in range(8):                                          # the old bound kept the last five
            self.say(f'סרטון מספר {i} ' + 'א' * 3000)
        turn = self.say('אתר')
        prompt = self.briefs.latest('p1').brief.prompt
        for i in range(8):
            self.assertIn(f'סרטון מספר {i}', prompt)
        self.assertNotIn('request_cut', turn.interpretation or {})

    def test_past_the_bounds_the_oldest_are_left_out_and_it_is_said(self):
        n = ConversationSupervisor.MAX_CARRIED_MESSAGES + 3
        for i in range(n):
            self.say(f'סרטון מספר {i} ' + 'א' * 3000)
        with self.assertLogs('omni_prod.conversation.supervisor', 'WARNING') as logs:
            turn = self.say('אתר')
        prompt = self.briefs.latest('p1').brief.prompt
        self.assertLessEqual(len(prompt), ConversationSupervisor.MAX_REQUEST_CHARS)
        self.assertNotIn('סרטון מספר 0 ', prompt)
        self.assertIn(f'סרטון מספר {n - 1} ', prompt)
        self.assertTrue(prompt.rstrip().endswith('אתר'))                     # the newest words are never cut
        cut = turn.interpretation['request_cut']
        self.assertGreaterEqual(cut['messages_left_out'], 3)
        self.assertEqual(cut['bound_messages'], ConversationSupervisor.MAX_CARRIED_MESSAGES)
        self.assertIn('REQUEST_CUT', '\n'.join(logs.output))
        said = turn.interpretation['notices'][0]['message']
        self.assertIn(said, turn.reply)                                       # said in the reply
        self.assertIn(f"{cut['chars_left_out']:,}", said)
        stored = [m for m in self.store.messages if m['role'] == 'assistant'][-1]
        self.assertEqual(stored['interpretation']['request_cut'], cut)       # and stored with the message


OUTLINE_HEAD = 'שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234.\nמבנה הדף:\n'


class TheCustomersOwnOutline(unittest.TestCase):
    def test_thirty_sections_and_a_long_section_are_read_whole(self):
        body = 'מה שהלקוח כתב לחלק הזה. ' * 80                       # ~1,900 characters
        text = OUTLINE_HEAD + '\n'.join(f'חלק {i} — {body}' for i in range(30))
        sections = PO.outline(text)
        self.assertEqual(len(sections), 30)                          # 20 before
        self.assertEqual(sections[0][1], body.strip())                # cut at 400 before
        self.assertEqual(PO.outline_notes(text), [])

    def test_past_the_bounds_it_is_logged_and_said(self):
        text = OUTLINE_HEAD + '\n'.join(f'חלק {i} — תיאור' for i in range(PO.MAX_SECTIONS + 5))
        text = text.replace('חלק 0 — תיאור', 'חלק 0 — ' + 'ת' * (PO.MAX_BODY + 7), 1)
        with self.assertLogs('omni_prod.page_outline', 'WARNING') as logs:
            sections = PO.outline(text)
        self.assertEqual(len(sections), PO.MAX_SECTIONS)
        self.assertEqual(len(sections[0][1]), PO.MAX_BODY)
        self.assertEqual(len([line for line in logs.output if 'PAGE_OUTLINE_CUT' in line]), 2)
        notes = PO.outline_notes(text)
        self.assertEqual(sorted(n['kind'] for n in notes), ['body_cut', 'sections_cut'])
        self.assertEqual(next(n for n in notes if n['kind'] == 'sections_cut')['left_out'], 5)
        said = PO.notes_message(notes, 'he')
        self.assertTrue(any('5 האחרונים לא ייכנסו' in s for s in said), said)
        self.assertTrue(any('"חלק 0"' in s for s in PO.notes_message(notes, 'en')))

    def test_the_spec_the_customer_approves_says_it(self):
        from omni_prod import conversation_rehearsal as R
        from test_conversation_rehearsal import Scripted
        request = (OUTLINE_HEAD + '\n'.join(f'חלק {i} — תיאור של חלק {i}' for i in range(PO.MAX_SECTIONS + 4))
                   + '\n\nכתובת: רחוב הרצל 12, חולון. שעות פעילות א׳–ה׳ 09:00–19:00. אתר תוכן בלבד, לא שומרים כלום.')
        answers = {'personal_data': 'לא', 'content_only': 'כן, אתר תוכן בלבד, לא שומרים כלום'}
        with mock.patch.dict(os.environ, {'OMNI_INTAKE_AGENT': '1'}):
            sup = R._Supervisor(Scripted())
            t = sup.turn(project_id='p', account_id='a', message=request, lang='he')
            for _ in range(12):
                if any(a['type'] == 'approve_spec' for a in t.actions):
                    break
                asked = list(getattr(t, 'asked_in_words', None) or [q.id for q in t.questions])
                t = sup.turn(project_id='p', account_id='a', lang='he',
                             message=answers.get(asked[0] if asked else None, 'תחליטו אתם על השאר'))
            else:
                self.fail('the conversation never reached gate 1')
        said = PO.notes_message(PO.outline_notes(request), 'he')
        self.assertTrue(said)
        for s in said:
            self.assertIn(s, t.reply)
        self.assertEqual([n['kind'] for n in t.interpretation['notices']], ['outline_cut'])


if __name__ == '__main__':
    unittest.main()

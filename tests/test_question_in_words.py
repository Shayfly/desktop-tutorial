"""The empty question (the owner, 2026-11-16).

Production, 2026-11-16 11:05-11:09, one conversation: five assistant messages were exactly "שאלה אחת לפני שממשיכים:".
The question lived only in the card of the live turn; the stored message asked nothing. Now every message that
announces a question carries it in words, and the card does not repeat it. The real supervisor runs."""
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import discovery as d
from omni_prod.conversation import supervisor as S
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from tests.test_conversation_os import MemoryBriefs
from tests.test_venice_live_wiring import REQUEST

LABELS = {t['ask_one'] for t in S._TXT.values()}
APP_JS = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')


class QuestionInWords(unittest.TestCase):
    def setUp(self):
        self.store = MemoryConversationStore()
        self.sup = ConversationSupervisor(briefs=MemoryBriefs(), store=self.store)

    def say(self, msg='', answers=None, lang='he'):
        return self.sup.turn(project_id='p', account_id='a', message=msg, answers=answers, lang=lang)

    def assistant(self):
        return [m['content'] for m in self.store.messages_for('p') if m['role'] == 'assistant'
                and not (m.get('interpretation') or {}).get('system')]

    def test_the_message_that_announces_a_question_asks_it(self):
        t = self.say('אני רוצה אתר לתיירים שמגיעים לעיר')
        self.assertTrue(t.questions)
        self.assertIn(S._TXT['he']['ask_one'] + ' ' + t.questions[0].he, t.reply)
        self.assertEqual(self.assistant()[-1], t.reply)                     # what is stored is what was said

    def test_english_carries_the_english_question(self):
        t = self.say('I want a site for tourists visiting the city', lang='en')
        self.assertTrue(t.questions)
        self.assertTrue(t.reply.endswith(S._TXT['en']['ask_one'] + ' ' + t.questions[0].en), t.reply)

    def test_no_stored_message_is_a_label_alone_all_the_way_to_the_summary(self):
        t = self.say(REQUEST, lang='en')
        for _ in range(10):                                                 # bounded, as in test_venice_live_wiring
            if any(a['type'] == 'approve_spec' for a in t.actions):
                break
            q = t.questions[0] if t.questions else None
            t = self.say(answers={q.id: q.options[0].value if q.kind == 'choice' else d.DELEGATE}, lang='en') if q \
                else self.say('you decide', lang='en')
        else:
            self.fail('never reached the summary')
        said = self.assistant()
        self.assertGreater(len(said), 1)
        self.assertTrue(any(label in content for content in said for label in LABELS), said)   # a card WAS asked
        for content in said:
            self.assertTrue(content.strip())
            self.assertNotIn(content.strip(), LABELS)
            self.assertFalse(any(content.rstrip().endswith(label) for label in LABELS), content)

    def test_a_label_with_no_question_is_logged_and_not_shown(self):
        for lang in ('he', 'en'):
            label = S._TXT[lang]['ask_one']
            turn = SimpleNamespace(reply='context. ' + label, questions=[])
            with self.assertLogs(S.__name__, level='ERROR') as logs:
                ConversationSupervisor._label_carries_its_question(turn, lang)
            self.assertEqual(turn.reply, 'context.')
            self.assertIn('ASK_LABEL_WITHOUT_QUESTION', logs.output[0])
            alone = SimpleNamespace(reply=label, questions=[])
            with self.assertLogs(S.__name__, level='ERROR'):
                ConversationSupervisor._label_carries_its_question(alone, lang)
            self.assertEqual(alone.reply, S._TXT[lang]['nothing'])

    def test_a_reply_that_does_not_end_with_the_label_is_untouched(self):
        q = d.BY_ID['personal_data']
        turn = SimpleNamespace(reply='שלום. ' + q.he, questions=[q])
        ConversationSupervisor._label_carries_its_question(turn, 'he')
        self.assertEqual(turn.reply, 'שלום. ' + q.he)

    def test_the_finish_path_carries_the_question_too(self):
        src = Path(S.__file__).read_text(encoding='utf-8')
        finish = src[src.index('    def _finish(self'):]
        self.assertLess(finish.index('self._label_carries_its_question(turn)'), finish.index('self.store.add_message('))

    def test_the_card_does_not_repeat_a_question_the_message_already_asks(self):
        self.assertIn("q.text && !String(said || '').includes(q.text) ? h('div', { class: 'qq' }, q.text) : null", APP_JS)
        self.assertIn('bubble.append(quickReplies(qs, m.content))', APP_JS)
        self.assertEqual(len(re.findall(r'quickReplies\(', APP_JS)), 2)     # the definition and this one caller


if __name__ == '__main__':
    unittest.main()

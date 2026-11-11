import unittest
from tests.test_no_repeat_questions import Conversation, FLOWERS
from omni_prod.conversation.supervisor import _label


class VisibleDelegationTests(unittest.TestCase):
    def test_negated_or_quoted_delegation_does_not_waive_sensitive_field(self):
        for message in ('אל תחליט במקומי, אני לא יודע',
                        'I did not say you decide. I am still unsure.',
                        'מה הכוונה כשאתה אומר תחליט אתה?'):
            with self.subTest(message=message):
                c = Conversation(fresh=True)
                c.say(FLOWERS)
                c.say('לא יודע')
                c.say('לא יודע')
                c.say(message)
                b = c.briefs.latest(c.pid).brief
                self.assertIn('personal_data', b.open_material)
                self.assertNotEqual((b.fields.get('personal_data') or {}).get('source'), 'delegated')

    def test_explicit_delegation_clears_held_field_and_shows_default(self):
        c = Conversation(fresh=True)
        c.say(FLOWERS)
        c.say('לא יודע')
        c.say('לא יודע')
        self.assertIn('personal_data', c.briefs.latest(c.pid).brief.open_material)
        t = c.say('תחליט אתה')
        b = c.briefs.latest(c.pid).brief
        self.assertNotIn('personal_data', b.open_material)
        self.assertEqual(b.fields['personal_data']['value'], 'no')
        self.assertEqual(b.fields['personal_data']['source'], 'delegated')
        self.assertIn(_label('personal_data', 'no', 'he'), t.reply)
        for _ in range(8):
            if c.briefs.latest(c.pid).complete:
                break
            t = c.say('תחליט אתה')
        self.assertTrue(c.briefs.latest(c.pid).complete)
        self.assertIn('approve_spec', [a['type'] for a in t.actions])
        self.assertFalse(any((m.get('interpretation') or {}).get('spec_approved')
                             for m in c.store.messages_for(c.pid)))
        c.say('מה המצב?')  # another supervisor replays the durable history
        self.assertNotIn('personal_data', c.briefs.latest(c.pid).brief.open_material)

    def test_delegation_does_not_replace_a_confirmed_value(self):
        c = Conversation(fresh=True)
        c.say(FLOWERS)
        c.click({'personal_data': 'yes'})
        c.say('תחליט אתה')
        f = c.briefs.latest(c.pid).brief.fields['personal_data']
        self.assertEqual((f['value'], f['source']), ('yes', 'answer'))

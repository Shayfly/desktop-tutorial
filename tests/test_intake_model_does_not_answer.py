"""Audit 2026-11-02 findings 4 + 5 (one bug: the model answers for the customer).

  finding 4  intake/gaps.py:123 passes a 'high' confidence proposal as STATED even with span=None. RE-CHECKED: the
             audit overstated it -- Ledger.add (intake/sources.py) already records a STATED claim whose words are not
             in the conversation as UNSOURCED, and Spec.value() does not return it. No code change; these tests pin
             that guard (negative control: remove it and they fail).
  finding 5  intake/gaps.py: a reply that filled nothing on the pending question took the field's default, also on
             sensitive confirm=True fields (personal_data='no', access_scope). Now: a confirm field never takes a
             silent default; it stays empty and the conversation holds it OPEN for the approval gate. An explicit
             "you decide" still delegates. Non-sensitive fields keep the old rule (control).
"""
import unittest

from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.gaps import STATED, Questioner, Spec
from omni_prod.intake.sources import UNSOURCED
from omni_prod.intake.interpreter import Proposal

REQUEST = 'אני רוצה אפליקציה לניהול תורים במספרה'          # a booking app: personal_data is material and sensitive


def asked(spec, field):
    """Ask `field` now (the detector's next question restricted to it)."""
    q = Questioner(None).next(spec, allowed=[field])
    assert q is not None and q.field == field, q
    return q


class NoSpanNoStated(unittest.TestCase):
    def test_a_high_confidence_proposal_without_a_quote_is_not_stated(self):
        spec = Spec('web_app', [])
        spec.hear(REQUEST, [Proposal('personal_data', 'no', 'high', 'we store nothing personal', origin='model')],
                  settle=False)
        cur = spec.ledger.current('personal_data')
        print('\n[no quote]', cur)
        self.assertEqual(cur.status, UNSOURCED)                  # kept and flagged, never STATED
        self.assertIsNone(spec.value('personal_data'))
        self.assertIn('personal_data', spec.detect()['missing_material'])

    def test_control_the_same_proposal_with_its_quote_in_the_words_is_stated(self):
        spec = Spec('web_app', [])
        spec.hear(REQUEST + ', לא שומרים פרטים אישיים',
                  [Proposal('personal_data', 'no', 'high', 'לא שומרים פרטים אישיים', origin='model')], settle=False)
        cur = spec.ledger.current('personal_data')
        self.assertEqual((cur.status, cur.value, cur.span.quote), (STATED, 'no', 'לא שומרים פרטים אישיים'))
        self.assertEqual(spec.value('personal_data'), 'no')


class ConfirmFieldsNeverTakeASilentDefault(unittest.TestCase):
    def spec_asking(self, field):
        spec = Spec('web_app', [])
        spec.hear(REQUEST, (), settle=False)
        asked(spec, field)
        return spec

    def test_an_unparsed_answer_leaves_personal_data_empty_and_missing(self):
        spec = self.spec_asking('personal_data')
        spec.hear('לא, אבל רק את מה שצריך בשביל התור')            # "no, but..." -- maps to nothing
        print('[unparsed on personal_data]', spec.ledger.current('personal_data'), spec.log[-1].filled)
        self.assertIsNone(spec.value('personal_data'))           # NOT the default 'no'
        self.assertIsNone(spec.ledger.current('personal_data'))
        self.assertFalse(spec.log[-1].filled)
        self.assertIn('personal_data', spec.detect()['missing_material'])

    def test_the_conversation_holds_it_open_for_the_approval_gate(self):
        spec = self.spec_asking('personal_data')
        spec.hear('לא, אבל רק את מה שצריך בשביל התור')
        self.assertTrue(ConversationSupervisor._unsettled_sensitive(spec, 'personal_data', True))
        self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, 'personal_data', False))  # "what?" path

    def test_an_explicit_you_decide_still_delegates(self):
        spec = self.spec_asking('personal_data')
        spec.hear('תחליט אתה')
        cur = spec.ledger.current('personal_data')
        self.assertEqual((cur.value, cur.why), ('no', 'delegated'))
        self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, 'personal_data', True))

    def test_control_a_non_sensitive_field_keeps_the_default_rule(self):
        spec = self.spec_asking('login')
        spec.hear('לא, אבל אולי בהמשך')
        cur = spec.ledger.current('login')
        self.assertEqual((cur.value, cur.why), ('none', 'not answered'))
        self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, 'login', True))


if __name__ == '__main__':
    unittest.main()

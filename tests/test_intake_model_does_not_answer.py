"""Audit 2026-11-02 findings 4 + 5 (one bug: the model answers for the customer).

  finding 4  intake/gaps.py:123 passes a 'high' confidence proposal as STATED even with span=None. RE-CHECKED: the
             audit overstated it -- Ledger.add (intake/sources.py) already records a STATED claim whose words are not
             in the conversation as UNSOURCED, and Spec.value() does not return it. No code change. The no-quote test
             pins that guard (negative control: remove it -> that test fails); the with-quote test is the positive
             control and stays green either way.
  finding 5  intake/gaps.py: a reply that filled nothing on the pending question took the field's default, also on
             sensitive confirm=True fields (personal_data, access_scope, content_only). Now: a confirm field never takes a
             silent default; it stays empty and the conversation holds it OPEN for the approval gate. An explicit
             "you decide" still delegates. Non-sensitive fields keep the old rule (control).
"""
import unittest

from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake.gaps import STATED, Questioner, Spec
from omni_prod.intake.sources import UNSOURCED
from omni_prod.intake.interpreter import Proposal

REQUEST = 'אני רוצה אפליקציה לניהול תורים במספרה'          # a booking app: personal_data is material and sensitive


def asked(spec, field, pending=()):
    """Ask `field` now (the detector's next question restricted to it)."""
    q = Questioner(None).next(spec, pending, allowed=[field])
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
    """Each sensitive (confirm=True) field, one by one: an unclear reply leaves it EMPTY, MISSING and held OPEN."""
    CASES = {   # field -> (artifact kind, request, discovery questions still open)
        'personal_data': ('web_app', REQUEST, ()),
        'access_scope': ('web_app', REQUEST, ('access_scope',)),                 # conditional: asked when open
        'content_only': ('website', 'אתר תדמית למספרה שלי עם טופס הרשמה', ()),   # implied 'no': proposed, confirmed
    }
    UNCLEAR = 'לא, אבל רק את מה שצריך בשביל התור'                                 # "no, but..." -- maps to nothing

    def spec_asking(self, field):
        kind, request, pending = self.CASES[field]
        spec = Spec(kind, [])
        spec.hear(request, (), settle=False)
        asked(spec, field, pending)
        return spec, pending

    def assert_stays_open(self, field):
        spec, pending = self.spec_asking(field)
        spec.hear(self.UNCLEAR)
        print(f'[unclear on {field}]', spec.ledger.current(field), 'filled:', spec.log[-1].filled)
        self.assertIsNone(spec.value(field))                          # NOT the field's default
        self.assertIsNone(spec.ledger.current(field))
        self.assertFalse(spec.log[-1].filled)
        self.assertIn(field, spec.detect(pending)['missing_material'])
        self.assertTrue(ConversationSupervisor._unsettled_sensitive(spec, field, True))    # held OPEN
        self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, field, False))  # "what?" path: re-asked

    def test_unclear_answer_on_personal_data_stays_open(self):
        self.assert_stays_open('personal_data')

    def test_unclear_answer_on_access_scope_stays_open(self):
        self.assert_stays_open('access_scope')

    def test_unclear_answer_on_content_only_stays_open(self):
        self.assert_stays_open('content_only')

    def test_an_explicit_you_decide_still_delegates(self):
        for field in self.CASES:
            with self.subTest(field=field):
                spec, pending = self.spec_asking(field)
                spec.hear('תחליט אתה')
                cur = spec.ledger.current(field)
                self.assertIsNotNone(cur, f'{field}: "you decide" recorded nothing')
                self.assertEqual(cur.why, 'delegated')
                self.assertIsNotNone(spec.value(field))
                self.assertNotIn(field, spec.detect(pending)['missing_material'])          # not left open
                self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, field, True))

    def test_control_a_non_sensitive_field_keeps_the_default_rule(self):
        spec = Spec('web_app', [])
        spec.hear(REQUEST, (), settle=False)
        asked(spec, 'login')
        spec.hear('לא, אבל אולי בהמשך')
        cur = spec.ledger.current('login')
        self.assertIsNotNone(cur, 'login: the default was not recorded')
        self.assertEqual((cur.value, cur.why), ('none', 'not answered'))
        self.assertFalse(ConversationSupervisor._unsettled_sensitive(spec, 'login', True))


if __name__ == '__main__':
    unittest.main()

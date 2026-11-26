"""An approval is valid a day, not 30 minutes (the owner, 2026-11-26, WAREHOUSE 136 option a), as long as nothing it
covers changed. The real PostgresBriefRepository.create_approval and consume, on a scripted cursor (no database here):
a day-old approval of an unchanged request starts the build; a changed request, contract or price refuses it as
approval_stale at any age; past the day it is approval_expired."""
import json
import unittest
from datetime import datetime, timedelta, timezone

from omni_prod import discovery as d
from omni_prod.brief_repository import APPROVAL_TTL, ApprovalError, PostgresBriefRepository

BRIEF = d.start('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234.')
CHANGED = d.start('שם העסק: סטודיו נועה. אתר תדמית למספרה. טלפון 03-5551234. ועוד גלריה.')


class Cursor:
    """Answers each SELECT from a queue and records every statement."""

    def __init__(self, answers):
        self.answers, self.sql = list(answers), []

    def execute(self, sql, params=()):
        self.sql.append(' '.join(sql.split()))

    def fetchone(self):
        return self.answers.pop(0)


def brief_row(brief, revision=3):
    return ('brf_1', 'p1', revision, json.dumps(brief.to_dict()), True, brief.fingerprint())


def approval_row(age: timedelta, brief=BRIEF, revision=3):
    created = datetime.now(timezone.utc) - age
    return ('p1', 'a1', revision, brief.fingerprint(), 'bc_1', 'cfp', 'bfp', 'ACTIVE', created + APPROVAL_TTL, None)


def consume(cur, **over):
    kw = dict(approval_id='apr_1', project_id='p1', account_id='a1', build_contract_id='bc_1',
              contract_fingerprint='cfp', budget_fingerprint='bfp', build_id='bld_1')
    return PostgresBriefRepository(pool=None).consume(cur, **{**kw, **over})


class AnApprovalLivesADay(unittest.TestCase):
    def test_the_bound_is_a_day(self):
        self.assertEqual(APPROVAL_TTL, timedelta(hours=24))

    def test_an_approval_of_an_unchanged_request_starts_the_build_after_23_hours(self):
        cur = Cursor([approval_row(timedelta(hours=23)), brief_row(BRIEF)])
        out = consume(cur)
        self.assertEqual(out['brief_fingerprint'], BRIEF.fingerprint())
        self.assertTrue(any("SET status = 'USED'" in s for s in cur.sql))

    def test_a_changed_request_is_refused_at_any_age(self):
        for age in (timedelta(minutes=1), timedelta(hours=23)):
            with self.subTest(age=age):
                cur = Cursor([approval_row(age), brief_row(CHANGED, revision=4)])
                with self.assertRaises(ApprovalError) as caught:
                    consume(cur)
                self.assertEqual((caught.exception.code, str(caught.exception)),
                                 ('approval_stale', 'the request changed after approval'))

    def test_a_changed_plan_or_price_is_refused_too(self):
        for over, why in (({'contract_fingerprint': 'other'}, 'the plan changed after approval'),
                          ({'budget_fingerprint': 'other'}, 'the price or budget changed after approval')):
            with self.subTest(why):
                cur = Cursor([approval_row(timedelta(hours=20)), brief_row(BRIEF)])
                with self.assertRaises(ApprovalError) as caught:
                    consume(cur, **over)
                self.assertEqual((caught.exception.code, str(caught.exception)), ('approval_stale', why))

    def test_past_the_day_it_expires(self):
        cur = Cursor([approval_row(timedelta(hours=24, minutes=1))])
        with self.assertRaises(ApprovalError) as caught:
            consume(cur)
        self.assertEqual(caught.exception.code, 'approval_expired')


if __name__ == '__main__':
    unittest.main()

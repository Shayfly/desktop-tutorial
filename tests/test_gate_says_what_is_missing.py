"""O10 (founder 2026-10-21): the build gate says WHAT is missing, not only that something is.

The gate (investor_app._brief_prompt, brief_repository.create_approval) refused with
409 brief_incomplete "Some questions are still open." and named neither the pending questions nor the contradiction.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from omni_prod import discovery as d
from omni_prod.brief_repository import ApprovalError, BriefRow, PostgresBriefRepository

try:
    from omni_prod import investor_app
except ModuleNotFoundError:  # fastapi missing outside CI
    investor_app = None


def row(brief, revision=1):
    return BriefRow(f'brf_{revision}', 'prj_1', revision, brief, d.complete(brief), brief.fingerprint())


OPEN = d.start('מערכת לניהול משימות לצוות')                                   # most questions still open
CONTRADICTION = d.answer(d.start('אתר לקוחות בלי התחברות'), {'audience': 'public', 'personal_data': 'yes'})


@unittest.skipIf(investor_app is None, 'needs fastapi')
class TheBuildGateNamesWhatIsMissing(unittest.TestCase):
    def refuse(self, brief):
        repo = SimpleNamespace(latest=lambda project_id, cur=None: row(brief))
        with patch.object(investor_app, '_brief_repo', return_value=repo):
            with self.assertRaises(investor_app.HTTPException) as ctx:
                investor_app._brief_prompt('prj_1', 1)
        self.assertEqual((ctx.exception.status_code, ctx.exception.detail['error']), (409, 'brief_incomplete'))
        return ctx.exception.detail

    def test_the_409_lists_every_pending_question(self):
        detail = self.refuse(OPEN)
        self.assertEqual([q['id'] for q in detail['pending']], [q.id for q in d.pending(OPEN)])
        self.assertTrue(detail['pending'])
        self.assertTrue(all(q['he'] and q['en'] for q in detail['pending']))   # a person can read it, not just an id

    def test_the_409_names_the_contradiction(self):
        self.assertTrue(d.contradictions(CONTRADICTION))
        detail = self.refuse(CONTRADICTION)
        self.assertEqual(detail['contradictions'], d.contradictions(CONTRADICTION))
        self.assertIn('access_scope', [q['id'] for q in detail['pending']])     # and the question that resolves it


class TheApprovalGateNamesWhatIsMissing(unittest.TestCase):
    def test_create_approval_carries_the_pending_questions(self):
        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        pool = MagicMock()
        pool.connection.return_value.__enter__.return_value = conn
        repo = PostgresBriefRepository(pool)
        current = row(OPEN)
        with patch.object(repo, 'latest', return_value=current):
            with self.assertRaises(ApprovalError) as ctx:
                repo.create_approval(project_id='prj_1', account_id='usr_1', brief_row=current, build_contract_id='bc',
                                     contract_fingerprint='c', budget_fingerprint='b')
        self.assertEqual(ctx.exception.code, 'brief_incomplete')
        self.assertEqual([q['id'] for q in ctx.exception.details['pending']], [q.id for q in d.pending(OPEN)])
        self.assertEqual(ctx.exception.details['contradictions'], [])
        cur.execute.assert_not_called()                                          # still refused before any write


if __name__ == '__main__':
    unittest.main()

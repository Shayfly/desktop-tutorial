"""Discovery conversation, ProjectBrief and server-bound approval
(master directive 2026-10-09 §4-5, G2). Engine tests are pure; repository
tests run against a real Postgres with migrations applied (skipped, not faked,
without one -- same convention as test_golden_mod_path_live_postgres)."""
from __future__ import annotations

import os
import threading
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from omni_prod import discovery as d


class EngineTests(unittest.TestCase):
    def test_known_facts_are_not_asked_and_hints_are_preselected(self):
        b = d.start('מערכת תורים למספרה בעברית, לקוחות קובעים תור עם שם וטלפון, בלי התחברות, צבע סגול')
        self.assertEqual({k: b.fields[k]['source'] for k in ('login', 'languages', 'color')},
                         {'login': 'message', 'languages': 'message', 'color': 'message'})
        asked = {q.id for q in d.pending(b)}
        self.assertNotIn('login', asked)
        self.assertNotIn('color', asked)
        self.assertIn('audience', asked)  # a hint is not a fact: still asked
        self.assertEqual(b.hints['audience'], 'public')

    def test_simple_design_questions_are_asked_too(self):
        b = d.start('מערכת לניהול משימות לצוות')
        self.assertTrue({'style', 'color', 'font', 'logo', 'references', 'audience', 'content'} <= {q.id for q in d.pending(b)})

    def test_small_groups_in_order(self):
        b = d.start('מערכת לניהול משימות לצוות')
        group, qs = d.next_group(b)
        self.assertEqual(group, 'purpose')
        self.assertLessEqual(len(qs), 4)

    def test_contradiction_is_asked_and_never_invented(self):
        b = d.start('אתר תורים ללקוחות עם טלפון, בלי התחברות')
        b = d.answer(b, {'audience': 'public', 'goal': 'קביעת תור', 'personal_data': 'yes'})
        self.assertEqual(d.next_group(b)[1][0].id, 'access_scope')
        self.assertFalse(d.complete(b))
        with self.assertRaises(ValueError):  # cannot be delegated: it is the user's decision
            d.answer(b, {'access_scope': d.DELEGATE})
        b2 = d.answer(b, {'access_scope': 'internal_link'})
        self.assertNotIn('access_scope', {q.id for q in d.pending(b2)})

    def test_changing_an_answer_drops_answers_that_no_longer_apply(self):
        b = d.start('אתר תורים ללקוחות עם טלפון, בלי התחברות')
        b = d.answer(b, {'audience': 'public', 'personal_data': 'yes', 'access_scope': 'internal_link'})
        self.assertIn('access_scope', b.fields)
        b = d.answer(b, {'audience': 'internal'})
        self.assertNotIn('access_scope', b.fields)

    def test_delegation_is_marked_and_recommend_mode_completes(self):
        b = d.answer(d.start('מערכת לניהול משימות לצוות'), {'color': d.DELEGATE})
        self.assertEqual(b.fields['color'], {'value': 'blue', 'source': 'delegated', 'question_id': 'color',
                                             'confidence': 'recommended'})
        r = d.start('אתר לניהול ספרייה עם מנויים', d.RECOMMEND)
        self.assertTrue(d.complete(r))
        self.assertTrue(all(f['source'] in ('delegated', 'message') for f in r.fields.values()))
        self.assertTrue(d.summary(r)['assumptions'])

    def test_requirements_honour_no_login_and_bind_the_fingerprint(self):
        r = d.start('מערכת משימות בעברית בלי התחברות', d.RECOMMEND)
        text = d.requirements_text(r)
        self.assertIn('Sign-in: NONE', text)
        self.assertIn(r.fingerprint()[:16], text)
        self.assertNotIn('email', text.lower())  # would add outbound e-mail infrastructure
        from omni_prod.product_architect import ProductArchitect
        c = ProductArchitect().compile(r.prompt + '\n' + text, project_id='prj_t', contract_version=1)
        self.assertEqual(c.user_roles, ('user',))
        self.assertNotIn('auth_session', {i.kind for i in c.infrastructure})

    def test_fingerprint_changes_with_any_answer(self):
        b = d.start('מערכת לניהול משימות לצוות')
        self.assertNotEqual(b.fingerprint(), d.answer(b, {'color': 'green'}).fingerprint())

    def test_invalid_option_is_rejected(self):
        with self.assertRaises(ValueError):
            d.answer(d.start('מערכת לניהול משימות לצוות'), {'style': 'unknown-style'})


DATABASE_URL = os.environ.get('M4D2_DATABASE_URL', 'postgresql://postgres:m4d2pass@127.0.0.1:5432/m4d2_test')


def _skip_reason():
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
            if conn.execute("SELECT to_regclass('public.build_approvals')").fetchone()[0] is None:
                return 'schema (through migration 030) not applied'
    except Exception as exc:
        return f'no live Postgres: {exc}'
    return None


_SKIP = _skip_reason()


@unittest.skipIf(_SKIP, _SKIP)
class LiveBriefAndApprovalTests(unittest.TestCase):
    def setUp(self):
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.creator_accounts import PostgresAccountService
        from omni_prod.db import DatabasePool
        self.pool = DatabasePool(DATABASE_URL)
        accounts = PostgresAccountService(token_secret='t' * 48, pool=self.pool)
        self.account, _ = accounts.register(email=f'b-{uuid.uuid4().hex[:8]}@example.com', password='a-long-password-123')
        self.other, _ = accounts.register(email=f'o-{uuid.uuid4().hex[:8]}@example.com', password='a-long-password-123')
        self.project = f'prj_{uuid.uuid4().hex[:10]}'
        self.contract = f'bc_{uuid.uuid4().hex[:10]}'
        with self.pool.connection() as conn:
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (self.project, self.account.id))
            conn.execute("INSERT INTO m5_build_contracts (id, project_id, contract_version, status, capability_plan_fingerprint,"
                         " contract_fingerprint, contract_json, created_at) VALUES (%s, %s, 1, 'READY', 'c', 'cfp', '{}'::jsonb, now())",
                         (self.contract, self.project))
            conn.commit()
        self.repo = PostgresBriefRepository(self.pool)

    def tearDown(self):
        getattr(self.pool, 'close', lambda: None)()

    def _complete_brief(self):
        row = self.repo.save(project_id=self.project, account_id=self.account.id,
                             brief=d.start('מערכת משימות בעברית בלי התחברות', d.RECOMMEND), expected_revision=0)
        self.assertTrue(row.complete)
        return row

    def _approve(self, row):
        return self.repo.create_approval(project_id=self.project, account_id=self.account.id, brief_row=row,
                                         build_contract_id=self.contract, contract_fingerprint='cfp', budget_fingerprint='bfp')

    def _consume(self, approval_id, account=None, contract_fp='cfp', budget_fp='bfp', build_id=None):
        with self.pool.connection() as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    return self.repo.consume(cur, approval_id=approval_id, project_id=self.project,
                                             account_id=(account or self.account).id, build_contract_id=self.contract,
                                             contract_fingerprint=contract_fp, budget_fingerprint=budget_fp,
                                             build_id=build_id or f'bld_{uuid.uuid4().hex}')

    def test_revisions_are_compare_and_set_and_survive_refresh(self):
        from omni_prod.brief_repository import StaleBrief
        r1 = self.repo.save(project_id=self.project, account_id=self.account.id, brief=d.start('מערכת לניהול משימות לצוות'),
                            expected_revision=0)
        r2 = self.repo.save(project_id=self.project, account_id=self.account.id, brief=d.answer(r1.brief, {'color': 'green'}),
                            expected_revision=1, request_key='k1')
        self.assertEqual(r2.revision, 2)
        # A retried submission returns the same revision; a stale tab is refused.
        again = self.repo.save(project_id=self.project, account_id=self.account.id, brief=r1.brief, expected_revision=1,
                               request_key='k1')
        self.assertEqual(again.id, r2.id)
        with self.assertRaises(StaleBrief):
            self.repo.save(project_id=self.project, account_id=self.account.id, brief=r1.brief, expected_revision=1)
        latest = self.repo.latest(self.project)  # "refresh": everything comes back from the database
        self.assertEqual((latest.revision, latest.brief.fields['color']['value']), (2, 'green'))

    def test_two_parallel_writers_of_one_revision_one_wins(self):
        from omni_prod.brief_repository import StaleBrief
        base = self.repo.save(project_id=self.project, account_id=self.account.id, brief=d.start('מערכת לניהול משימות לצוות'),
                              expected_revision=0)
        results, barrier = [], threading.Barrier(2)

        def write(color):
            barrier.wait()
            try:
                results.append(self.repo.save(project_id=self.project, account_id=self.account.id,
                                              brief=d.answer(base.brief, {'color': color}), expected_revision=1).revision)
            except StaleBrief:
                results.append('stale')
        ts = [threading.Thread(target=write, args=(c,)) for c in ('green', 'purple')]
        [t.start() for t in ts]
        [t.join(10) for t in ts]
        self.assertEqual(sorted(map(str, results)), ['2', 'stale'])

    def test_approval_is_consumed_once(self):
        from omni_prod.brief_repository import ApprovalError
        approval = self._approve(self._complete_brief())
        self.assertEqual(self._consume(approval['approval_id'])['brief_revision'], 1)
        with self.assertRaises(ApprovalError) as ctx:
            self._consume(approval['approval_id'])
        self.assertEqual(ctx.exception.code, 'approval_used')

    def test_one_approval_never_starts_two_builds(self):
        """Two builds racing on ONE approval (a double click that reached POST .../builds twice with different build
        ids): consume() runs inside each build's transaction under SELECT ... FOR UPDATE, so exactly one build gets
        the approval and the other is refused before it is created."""
        from omni_prod.brief_repository import ApprovalError
        approval = self._approve(self._complete_brief())
        builds, outcome, barrier = ['bld_' + uuid.uuid4().hex for _ in range(2)], {}, threading.Barrier(2)

        def start(build_id):
            barrier.wait()
            try:
                self._consume(approval['approval_id'], build_id=build_id)
                outcome[build_id] = 'started'
            except ApprovalError as exc:
                outcome[build_id] = exc.code
        ts = [threading.Thread(target=start, args=(b,)) for b in builds]
        [t.start() for t in ts]
        [t.join(10) for t in ts]
        self.assertEqual(sorted(outcome.values()), ['approval_used', 'started'])
        winner = next(b for b, o in outcome.items() if o == 'started')
        with self.pool.connection() as conn:
            used_by = conn.execute('SELECT used_by_build_id FROM build_approvals WHERE id = %s',
                                   (approval['approval_id'],)).fetchone()[0]
        self.assertEqual(used_by, winner)                     # one approval -> one build, recorded

    def test_a_meaningful_change_invalidates_the_approval(self):
        from omni_prod.brief_repository import ApprovalError
        row = self._complete_brief()
        approval = self._approve(row)
        self.repo.save(project_id=self.project, account_id=self.account.id, brief=d.answer(row.brief, {'color': 'green'}),
                       expected_revision=1)
        with self.assertRaises(ApprovalError) as ctx:
            self._consume(approval['approval_id'])
        self.assertEqual(ctx.exception.code, 'approval_stale')

    def test_approval_is_bound_to_plan_budget_and_user(self):
        from omni_prod.brief_repository import ApprovalError
        approval = self._approve(self._complete_brief())
        for kwargs, code in (({'contract_fp': 'other'}, 'approval_stale'), ({'account': self.other}, 'approval_not_found')):
            with self.assertRaises(ApprovalError) as ctx:
                self._consume(approval['approval_id'], **kwargs)
            self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(ApprovalError) as ctx:
            self._consume(approval['approval_id'], budget_fp='more expensive')
        self.assertEqual(ctx.exception.code, 'approval_stale')

    def test_expired_approval_is_refused(self):
        from omni_prod.brief_repository import ApprovalError
        row = self._complete_brief()
        approval = self.repo.create_approval(project_id=self.project, account_id=self.account.id, brief_row=row,
                                             build_contract_id=self.contract, contract_fingerprint='cfp', budget_fingerprint='bfp',
                                             now=datetime.now(timezone.utc) - timedelta(hours=2))
        with self.assertRaises(ApprovalError) as ctx:
            self._consume(approval['approval_id'])
        self.assertEqual(ctx.exception.code, 'approval_expired')

    def test_incomplete_brief_cannot_be_approved(self):
        from omni_prod.brief_repository import ApprovalError
        row = self.repo.save(project_id=self.project, account_id=self.account.id, brief=d.start('מערכת לניהול משימות לצוות'),
                             expected_revision=0)
        with self.assertRaises(ApprovalError) as ctx:
            self._approve(row)
        self.assertEqual(ctx.exception.code, 'brief_incomplete')


if __name__ == '__main__':
    unittest.main()

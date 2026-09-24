"""Real unit tests for omni_prod/modification_repository.py (M4A/M4D).

What is real here: resolve_accept()'s four decision branches (the pure
function implementing M4's concurrency requirement), every SQL statement
PostgresModificationRepository emits (shape, WHERE clauses, params, JSONB
round-tripping), the outbox relay's one-row-per-transaction/duplicate-safe
behaviour (mirrors tests/test_m3_preview_logic.py's TestOutboxRelay for
job_repository.py), and accept()/rollback()'s actual version-history
mechanics -- these run against the real omni_prod.workspace.
MemoryProjectWorkspace, so `new_version.parent_id`, `.repository()` and
`current()` are genuine, not asserted-by-fiat.

What is faked, and why: the Postgres pool (no psycopg here -- the fake
mirrors DatabasePool's context-manager contract, same ScriptedCursor/
FakeConn/FakePool/_Ctx pattern as test_spec_repository.py and
test_m3_preview_logic.py), and the spec repository (FakeSpecRepo, an
in-memory stand-in for PostgresSpecRepository's get/save contract -- the
real PostgresSpecRepository already has its own dedicated SQL-shape tests
in test_spec_repository.py, so re-faking Postgres for it here would only
duplicate that coverage without adding anything).

Run with: python3 -m unittest tests.test_modification_repository -v
"""
import json
import unittest

from omni_prod.modification_repository import (
    ModificationDetails, PostgresModificationRepository, resolve_accept,
)
from omni_prod.product_spec import ProductSpec
from omni_prod.spec_repository import SpecNotFound
from omni_prod.workspace import MemoryProjectWorkspace, SKIP_VERSION_CHECK, VersionConflict

SPEC = {
    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
}
SPEC_V2 = {**SPEC, 'title': 'Todo v2'}


# ===========================================================================
# Fakes -- shared fake-pool convention (test_spec_repository.py /
# test_m3_preview_logic.py) plus a FakeSpecRepo for the accept()/rollback()
# tests below.
# ===========================================================================

class ScriptedCursor:
    def __init__(self, fetch=(), rowcounts=()):
        self.executed: list[tuple[str, object]] = []
        self._fetch = list(fetch)
        self._rowcounts = list(rowcounts)
        self.rowcount = 0

    def execute(self, sql, params=None):
        self.executed.append((' '.join(sql.split()), params))
        self.rowcount = self._rowcounts.pop(0) if self._rowcounts else 1

    def fetchone(self):
        return self._fetch.pop(0) if self._fetch else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Ctx:
    def __init__(self, value=None):
        self.value = value

    def __enter__(self):
        return self.value if self.value is not None else self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, cur):
        self.cur = cur
        self.transactions = 0

    def cursor(self):
        return self.cur

    def transaction(self):
        self.transactions += 1
        return _Ctx()


class FakePool:
    def __init__(self, cur):
        self.conn = FakeConn(cur)

    def connection(self):
        return _Ctx(self.conn)


class ExplodingPool:
    def connection(self):
        raise AssertionError('validation must reject before touching the pool')


class FakeSpecRepo:
    """In-memory stand-in for PostgresSpecRepository's get/save contract --
    see the module docstring for why this isn't a second fake-Postgres."""
    def __init__(self):
        self._store: dict[str, ProductSpec] = {}
        self.save_calls: list[tuple[str, str]] = []

    def save(self, *, version_id, project_id, spec, cur=None):
        # `cur` is accepted for interface parity with PostgresSpecRepository
        # (M4D.1: accept()/rollback() now pass the same cursor they gave
        # workspace.commit(), to merge everything into one transaction) but
        # is unused here -- this is a pure in-memory double, no SQL to share.
        self.save_calls.append((version_id, project_id))
        self._store.setdefault(version_id, spec)  # ON CONFLICT DO NOTHING, like the real one

    def get(self, version_id, project_id):
        try:
            return self._store[version_id]
        except KeyError:
            raise SpecNotFound(f'no spec stored for version {version_id!r}')


class RacyWorkspace:
    """Wraps a real MemoryProjectWorkspace. Its first commit() call injects
    a *different*, unconditional commit -- simulating a second
    modification's accept() landing -- immediately before delegating to the
    inner workspace's real (M4D.1) commit(), simulating a second
    modification's accept() winning the race in the narrow window between
    this call's own read-of-current and its own write. Because the inner
    MemoryProjectWorkspace.commit() now does its expected-version compare
    INSIDE the same lock as the read+write (not after), the delegated call
    below -- called with whatever `expected_current_version_id`/`cur`
    accept() actually passed -- will correctly raise VersionConflict itself
    when the interloper has moved current out from under it (force=False),
    or correctly succeed on top of the interloper (force=True). This class
    no longer needs to special-case the race outcome; it only needs to make
    the race happen, and let the real atomic check do its job."""
    def __init__(self, inner):
        self.inner = inner
        self.commit_calls = 0

    def current(self, project_id):
        return self.inner.current(project_id)

    def restore(self, *, project_id, version_id, message='restore', cur=None):
        return self.inner.restore(project_id=project_id, version_id=version_id, message=message, cur=cur)

    def commit(self, *, project_id, repository, message,
               expected_current_version_id=SKIP_VERSION_CHECK, cur=None):
        self.commit_calls += 1
        if self.commit_calls == 1:
            self.inner.commit(project_id=project_id, repository={'interloper.py': '1'},
                              message='a different accept() wins the race')
        # Delegate with exactly what was passed in (or workspace.py's own
        # "no check" sentinel, matching its default, if nothing was passed).
        return self.inner.commit(project_id=project_id, repository=repository, message=message,
                                 expected_current_version_id=expected_current_version_id, cur=cur)


def repo_of(**kw):
    cur = ScriptedCursor(**kw)
    return PostgresModificationRepository(FakePool(cur)), cur


# ===========================================================================
# resolve_accept() -- the pure concurrency decision, M4's Version 10/11 case
# ===========================================================================

class ResolveAcceptTests(unittest.TestCase):
    def test_not_ready_for_review_is_invalid_status_regardless_of_versions(self):
        self.assertEqual(resolve_accept(status='RUNNING', expected_source_version_id='v10',
                                        current_version_id='v10', force=False), 'invalid_status')
        self.assertEqual(resolve_accept(status='FAILED', expected_source_version_id='v10',
                                        current_version_id='v11', force=True), 'invalid_status')

    def test_current_still_matches_source_is_a_plain_accept(self):
        self.assertEqual(resolve_accept(status='READY_FOR_REVIEW', expected_source_version_id='v10',
                                        current_version_id='v10', force=False), 'accept')

    def test_force_does_not_change_the_outcome_when_there_is_no_conflict(self):
        self.assertEqual(resolve_accept(status='READY_FOR_REVIEW', expected_source_version_id='v10',
                                        current_version_id='v10', force=True), 'accept')

    def test_the_version_10_11_scenario_is_a_conflict_without_force(self):
        # Modification A accepted first: current is now v11, not the v10 that
        # Modification B was proposed and built against.
        self.assertEqual(resolve_accept(status='READY_FOR_REVIEW', expected_source_version_id='v10',
                                        current_version_id='v11', force=False), 'conflict')

    def test_the_version_10_11_scenario_with_force_is_accept_forced(self):
        self.assertEqual(resolve_accept(status='READY_FOR_REVIEW', expected_source_version_id='v10',
                                        current_version_id='v11', force=True), 'accept_forced')

    def test_no_current_version_at_all_is_treated_as_a_mismatch(self):
        self.assertEqual(resolve_accept(status='READY_FOR_REVIEW', expected_source_version_id='v10',
                                        current_version_id=None, force=False), 'conflict')


# ===========================================================================
# create / create_outbox / mark_outbox_enqueued / dispatch_pending_outbox
# ===========================================================================

class CreateAndOutboxTests(unittest.TestCase):
    def test_create_inserts_queued_with_source_spec_version_equal_to_source(self):
        cur = ScriptedCursor()
        PostgresModificationRepository(FakePool(cur)).create(
            cur, modification_id='mod_1', project_id='proj_1', user_id='user_1',
            source_version_id='v10', followup='fix the login bug',
        )
        sql, params = cur.executed[0]
        self.assertIn('INSERT INTO modification_requests', sql)
        self.assertIn("'QUEUED'", sql)
        self.assertEqual(params[:6], ('mod_1', 'proj_1', 'user_1', 'v10', 'v10', 'fix the login bug'))
        self.assertEqual(json.loads(params[6]), ['US', 'EU', 'IL'])  # default target markets
        self.assertEqual(json.loads(params[7]), [])  # default rights evidence

    def test_create_stores_explicit_target_markets_and_rights_evidence(self):
        cur = ScriptedCursor()
        PostgresModificationRepository(FakePool(cur)).create(
            cur, modification_id='mod_1', project_id='proj_1', user_id='user_1',
            source_version_id='v10', followup='fix the login bug',
            target_markets=('DE', 'FR'), rights_evidence=[{'id': 'ev_1'}],
        )
        _, params = cur.executed[0]
        self.assertEqual(json.loads(params[6]), ['DE', 'FR'])
        self.assertEqual(json.loads(params[7]), [{'id': 'ev_1'}])

    def test_create_outbox_inserts_one_row(self):
        cur = ScriptedCursor()
        PostgresModificationRepository(FakePool(cur)).create_outbox(cur, modification_id='mod_1')
        sql, params = cur.executed[0]
        self.assertIn('INSERT INTO modification_outbox', sql)
        self.assertEqual(params, ('mod_1',))

    def test_mark_outbox_enqueued_sets_timestamp(self):
        r, cur = repo_of()
        r.mark_outbox_enqueued('mod_1')
        sql, params = cur.executed[0]
        self.assertIn('SET enqueued_at = now()', sql)
        self.assertEqual(params, ('mod_1',))


class OutboxDispatchTests(unittest.TestCase):
    def test_dispatches_pending_rows_one_transaction_each(self):
        cur = ScriptedCursor(fetch=[('mod_1',), ('mod_2',), None])
        pool = FakePool(cur)
        sent = []
        out = PostgresModificationRepository(pool).dispatch_pending_outbox(sent.append, older_than_seconds=30)
        self.assertEqual((out, sent), (['mod_1', 'mod_2'], ['mod_1', 'mod_2']))
        selects = [s for s, _ in cur.executed if s.startswith('SELECT')]
        updates = [p for s, p in cur.executed if s.startswith('UPDATE modification_outbox')]
        self.assertTrue(all('FOR UPDATE SKIP LOCKED' in s and 'enqueued_at IS NULL' in s for s in selects))
        self.assertEqual(updates, [('mod_1',), ('mod_2',)])
        self.assertEqual(pool.conn.transactions, 3)

    def test_enqueue_failure_leaves_row_pending(self):
        cur = ScriptedCursor(fetch=[('mod_1',)])

        def down(modification_id):
            raise ConnectionError('redis down')

        with self.assertRaises(ConnectionError):
            PostgresModificationRepository(FakePool(cur)).dispatch_pending_outbox(down)
        self.assertFalse(any(s.startswith('UPDATE') for s, _ in cur.executed))

    def test_limit_is_respected(self):
        cur = ScriptedCursor(fetch=[('a',), ('b',), ('c',)])
        out = PostgresModificationRepository(FakePool(cur)).dispatch_pending_outbox(lambda m: None, limit=2)
        self.assertEqual(out, ['a', 'b'])


# ===========================================================================
# get_request / transition_running
# ===========================================================================

class GetRequestAndTransitionTests(unittest.TestCase):
    def test_get_request_returns_worker_fields(self):
        r, cur = repo_of(fetch=[('proj_1', 'user_1', 'v10', 'add dark mode',
                                 json.dumps(['US', 'EU']), json.dumps([{'id': 'ev_1'}]))])
        out = r.get_request('mod_1')
        self.assertEqual(out, {'project_id': 'proj_1', 'user_id': 'user_1',
                                'source_version_id': 'v10', 'followup': 'add dark mode',
                                'target_markets': ('US', 'EU'), 'rights_evidence': [{'id': 'ev_1'}]})

    def test_get_request_defaults_target_markets_and_rights_evidence_when_null(self):
        r, cur = repo_of(fetch=[('proj_1', 'user_1', 'v10', 'add dark mode', None, None)])
        out = r.get_request('mod_1')
        self.assertEqual(out['target_markets'], ('US', 'EU', 'IL'))
        self.assertEqual(out['rights_evidence'], [])

    def test_get_request_missing_raises(self):
        r, cur = repo_of(fetch=[None])
        with self.assertRaises(KeyError):
            r.get_request('mod_missing')

    def test_transition_running_succeeds_from_queued(self):
        r, cur = repo_of(rowcounts=[1])
        self.assertTrue(r.transition_running('mod_1'))
        sql, params = cur.executed[0]
        self.assertIn("status='RUNNING'", sql)
        self.assertIn("AND status='QUEUED'", sql)
        self.assertEqual(params, ('mod_1',))

    def test_transition_running_is_a_noop_on_duplicate_delivery(self):
        r, cur = repo_of(rowcounts=[0])
        self.assertFalse(r.transition_running('mod_1'))


# ===========================================================================
# complete()
# ===========================================================================

class CompleteTests(unittest.TestCase):
    def test_invalid_completion_status_is_rejected_before_touching_the_pool(self):
        r = PostgresModificationRepository(ExplodingPool())
        with self.assertRaises(ValueError):
            r.complete('mod_1', project_id='proj_1', status='ACCEPTED')

    def test_ready_for_review_without_a_candidate_is_rejected_before_touching_the_pool(self):
        r = PostgresModificationRepository(ExplodingPool())
        with self.assertRaises(ValueError):
            r.complete('mod_1', project_id='proj_1', status='READY_FOR_REVIEW')

    def test_failed_completion_writes_no_candidate_row(self):
        r, cur = repo_of(rowcounts=[1])
        applied = r.complete('mod_1', project_id='proj_1', status='FAILED',
                             error_code='verification_failed', error_message='2 tests failed')
        self.assertTrue(applied)
        self.assertEqual(len(cur.executed), 1)
        sql, params = cur.executed[0]
        self.assertIn("SET status = %s, completed_at = now()", sql)
        self.assertIn("WHERE id = %s AND status = 'RUNNING'", sql)
        self.assertNotIn('modification_candidates', sql)

    def test_ready_for_review_writes_status_and_candidate_atomically(self):
        r, cur = repo_of(rowcounts=[1])
        spec = ProductSpec.from_dict(SPEC)
        applied = r.complete(
            'mod_1', project_id='proj_1', status='READY_FOR_REVIEW',
            classification='missing_requirement', billable=False,
            candidate_repository={'app.py': 'v2'}, candidate_spec=spec, repair_rounds=1,
        )
        self.assertTrue(applied)
        self.assertEqual(len(cur.executed), 2)
        update_sql, update_params = cur.executed[0]
        self.assertIn("SET status = %s, completed_at = now()", update_sql)
        insert_sql, insert_params = cur.executed[1]
        self.assertIn('INSERT INTO modification_candidates', insert_sql)
        self.assertIn('ON CONFLICT (modification_id) DO NOTHING', insert_sql)
        self.assertEqual(insert_params[0], 'mod_1')
        self.assertEqual(insert_params[1], 'proj_1')
        self.assertEqual(json.loads(insert_params[2]), {'app.py': 'v2'})
        self.assertEqual(json.loads(insert_params[3])['title'], 'Todo')

    def test_duplicate_completion_is_a_noop_and_never_double_writes_the_candidate(self):
        r, cur = repo_of(rowcounts=[0])
        applied = r.complete('mod_1', project_id='proj_1', status='READY_FOR_REVIEW',
                             candidate_repository={'app.py': 'v2'}, candidate_spec=ProductSpec.from_dict(SPEC))
        self.assertFalse(applied)
        self.assertEqual(len(cur.executed), 1)  # UPDATE only -- candidate insert skipped


# ===========================================================================
# get_details / get_candidate
# ===========================================================================

class GetDetailsAndCandidateTests(unittest.TestCase):
    ROW = ('READY_FOR_REVIEW', 'change_request', 'user wants dark mode', True,
           'v10', None, 2, {'k': 'v'}, None, None,
           '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:01+00:00', '2026-01-01T00:00:02+00:00', None, None)

    def test_get_details_maps_every_field(self):
        r, cur = repo_of(fetch=[self.ROW])
        out = r.get_details('mod_1', 'proj_1')
        self.assertEqual(out, ModificationDetails(
            id='mod_1', status='READY_FOR_REVIEW', classification='change_request',
            classification_reason='user wants dark mode', billable=True, source_version_id='v10',
            promoted_version_id=None, repair_rounds=2, evidence={'k': 'v'}, error_code=None, error_message=None,
            created_at='2026-01-01T00:00:00+00:00', started_at='2026-01-01T00:00:01+00:00',
            completed_at='2026-01-01T00:00:02+00:00', accepted_at=None, rejected_at=None,
        ))

    def test_get_details_missing_raises(self):
        r, cur = repo_of(fetch=[None])
        with self.assertRaises(KeyError):
            r.get_details('mod_missing', 'proj_1')

    def test_get_candidate_returns_parsed_repository_and_spec(self):
        r, cur = repo_of(fetch=[(json.dumps({'a.py': '1'}), json.dumps(SPEC))])
        out = r.get_candidate('mod_1', 'proj_1')
        self.assertEqual(out['repository'], {'a.py': '1'})
        self.assertEqual(out['spec'].title, 'Todo')

    def test_get_candidate_handles_already_decoded_jsonb(self):
        r, cur = repo_of(fetch=[({'a.py': '1'}, SPEC)])
        out = r.get_candidate('mod_1', 'proj_1')
        self.assertEqual(out['repository'], {'a.py': '1'})

    def test_get_candidate_missing_raises(self):
        r, cur = repo_of(fetch=[None])
        with self.assertRaises(KeyError):
            r.get_candidate('mod_missing', 'proj_1')


# ===========================================================================
# accept() -- real MemoryProjectWorkspace, FakeSpecRepo. This is the
# concurrency-critical path (M4's Version 10/11 scenario).
# ===========================================================================

class AcceptTests(unittest.TestCase):
    def test_invalid_status_returns_without_ever_touching_the_workspace(self):
        r, cur = repo_of(fetch=[('v10', 'FAILED')])

        class PoisonWorkspace:
            def current(self, project_id):
                raise AssertionError('must not consult the workspace for a non-READY_FOR_REVIEW modification')

        out = r.accept('mod_1', 'proj_1', workspace=PoisonWorkspace(), spec_repo=FakeSpecRepo())
        self.assertEqual(out, {'accepted': False, 'reason': 'invalid_status', 'status': 'FAILED'})
        self.assertEqual(len(cur.executed), 1)  # only the pre-check SELECT; no candidate lookup either

    def test_not_found_raises(self):
        r, cur = repo_of(fetch=[None])
        with self.assertRaises(KeyError):
            r.accept('mod_missing', 'proj_1', workspace=MemoryProjectWorkspace(), spec_repo=FakeSpecRepo())

    def test_ready_for_review_with_no_stored_candidate_is_a_defensive_error(self):
        r, cur = repo_of(fetch=[('v10', 'READY_FOR_REVIEW'), None])
        with self.assertRaises(RuntimeError):
            r.accept('mod_1', 'proj_1', workspace=MemoryProjectWorkspace(), spec_repo=FakeSpecRepo())

    def test_happy_path_promotes_the_candidate_and_saves_its_spec(self):
        workspace = MemoryProjectWorkspace()
        v10 = workspace.commit(project_id='proj_1', repository={'a.py': '1'}, message='init')
        r, cur = repo_of(fetch=[(v10.id, 'READY_FOR_REVIEW'), (json.dumps({'a.py': '2'}), json.dumps(SPEC))])
        spec_repo = FakeSpecRepo()

        out = r.accept('mod_1', 'proj_1', workspace=workspace, spec_repo=spec_repo)
        # M4D.1: the whole promotion -- status/candidate read, the version
        # commit (via the shared cur), the spec save (via the shared cur),
        # and the final ACCEPTED update -- now happens inside exactly ONE
        # `conn.transaction()`, not the pre-M4D.1 two (pre-check + a later,
        # separate final-update transaction).
        self.assertEqual(r.pool.conn.transactions, 1)

        self.assertTrue(out['accepted'])
        self.assertFalse(out['forced'])
        new_id = out['new_version_id']
        self.assertNotEqual(new_id, v10.id)  # a brand new version, never an in-place edit
        # The workspace itself now really serves the promoted content.
        current = workspace.current('proj_1')
        self.assertEqual(current.id, new_id)
        self.assertEqual(current.repository(), {'a.py': '2'})
        self.assertEqual(current.parent_id, v10.id)
        # The spec was carried over under the new version's id (M4B pairing).
        self.assertEqual(spec_repo._store[new_id].title, 'Todo')
        # Final bookkeeping UPDATE landed.
        update_sql, update_params = cur.executed[-1]
        self.assertIn("SET status='ACCEPTED'", update_sql)
        self.assertEqual(update_params, (new_id, 'mod_1'))

    def test_pre_check_conflict_when_current_has_moved_marks_conflict_and_never_commits(self):
        workspace = MemoryProjectWorkspace()
        v10 = workspace.commit(project_id='proj_1', repository={'a.py': '1'}, message='init')
        v11 = workspace.commit(project_id='proj_1', repository={'a.py': '1', 'b.py': '2'}, message='someone else')
        # This modification was proposed against v10, but v11 is current now
        # -- the exact Version 10/11 scenario the directive requires.
        r, cur = repo_of(fetch=[(v10.id, 'READY_FOR_REVIEW'), (json.dumps({'a.py': 'from-mod'}), json.dumps(SPEC))])
        spec_repo = FakeSpecRepo()

        out = r.accept('mod_1', 'proj_1', workspace=workspace, spec_repo=spec_repo)

        self.assertEqual(out, {'accepted': False, 'reason': 'conflict',
                               'current_version_id': v11.id, 'source_version_id': v10.id})
        self.assertEqual(workspace.current('proj_1').id, v11.id)  # untouched
        self.assertEqual(len(workspace.history('proj_1')), 2)  # v10, v11 only -- nothing extra
        self.assertEqual(spec_repo.save_calls, [])
        conflict_sql, conflict_params = cur.executed[-1]
        self.assertIn("SET status='CONFLICT'", conflict_sql)
        self.assertEqual(conflict_params, ('mod_1',))
        # The aborted promotion attempt (rolled back on VersionConflict) plus
        # _mark_conflict()'s own follow-up update: two transactions, never
        # one that somehow both wrote a version AND reported conflict.
        self.assertEqual(r.pool.conn.transactions, 2)

    def test_pre_check_conflict_with_force_promotes_onto_whatever_is_current(self):
        workspace = MemoryProjectWorkspace()
        v10 = workspace.commit(project_id='proj_1', repository={'a.py': '1'}, message='init')
        v11 = workspace.commit(project_id='proj_1', repository={'a.py': '1', 'b.py': '2'}, message='someone else')
        r, cur = repo_of(fetch=[(v10.id, 'READY_FOR_REVIEW'), (json.dumps({'a.py': 'from-mod'}), json.dumps(SPEC))])
        spec_repo = FakeSpecRepo()

        out = r.accept('mod_1', 'proj_1', workspace=workspace, spec_repo=spec_repo, force=True)

        self.assertTrue(out['accepted'])
        self.assertTrue(out['forced'])
        new = workspace.current('proj_1')
        self.assertEqual(new.id, out['new_version_id'])
        self.assertEqual(new.parent_id, v11.id)  # committed on top of whatever was actually current
        self.assertEqual(new.repository(), {'a.py': 'from-mod'})

    def test_race_at_commit_time_is_caught_even_though_the_pre_check_passed(self):
        """M4D.1: this is the 'late race between pre-check and commit'
        required test. Before the fix, RacyWorkspace's injected interloper
        commit would already have landed in project_versions (and become
        `current()`) by the time accept() noticed the mismatch -- the exact
        production-blocking bug the M4D.1 directive named: a caller told
        'conflict, not accepted' while the project had already silently
        mutated to unintended content. After the fix, the interloper commit
        happens, but THIS modification's own attempt to commit on top of a
        now-stale expectation raises VersionConflict from inside
        workspace.commit() itself, before any row for THIS modification is
        ever written -- no orphaned version, no extra history entry, current
        stays exactly the interloper's version and nothing more."""
        inner = MemoryProjectWorkspace()
        v10 = inner.commit(project_id='proj_1', repository={'a.py': '1'}, message='init')
        workspace = RacyWorkspace(inner)
        r, cur = repo_of(fetch=[(v10.id, 'READY_FOR_REVIEW'), (json.dumps({'a.py': 'from-mod'}), json.dumps(SPEC))])
        spec_repo = FakeSpecRepo()

        out = r.accept('mod_1', 'proj_1', workspace=workspace, spec_repo=spec_repo)

        self.assertFalse(out['accepted'])
        self.assertEqual(out['reason'], 'conflict')
        self.assertEqual(out['source_version_id'], v10.id)
        self.assertNotIn('orphaned_version_id', out)  # M4D.1: there is no such thing anymore
        # Exactly v10 + the interloper's version exist -- nothing from this
        # modification's failed attempt was ever written.
        self.assertEqual(len(inner.history('proj_1')), 2)
        current = inner.current('proj_1')
        self.assertNotEqual(current.id, v10.id)  # the interloper's version is current
        self.assertEqual(current.repository(), {'interloper.py': '1'})
        self.assertEqual(spec_repo.save_calls, [])  # never promoted as this modification's success
        conflict_sql, conflict_params = cur.executed[-1]
        self.assertIn("SET status='CONFLICT'", conflict_sql)
        self.assertEqual(conflict_params, ('mod_1',))

    def test_race_at_commit_time_with_force_is_accepted_and_reported_as_forced(self):
        inner = MemoryProjectWorkspace()
        v10 = inner.commit(project_id='proj_1', repository={'a.py': '1'}, message='init')
        workspace = RacyWorkspace(inner)
        r, cur = repo_of(fetch=[(v10.id, 'READY_FOR_REVIEW'), (json.dumps({'a.py': 'from-mod'}), json.dumps(SPEC))])
        spec_repo = FakeSpecRepo()

        out = r.accept('mod_1', 'proj_1', workspace=workspace, spec_repo=spec_repo, force=True)

        self.assertTrue(out['accepted'])
        self.assertTrue(out['forced'])
        self.assertEqual(inner.current('proj_1').id, out['new_version_id'])
        self.assertEqual(spec_repo.save_calls, [(out['new_version_id'], 'proj_1')])


# ===========================================================================
# reject()
# ===========================================================================

class RejectTests(unittest.TestCase):
    def test_ready_for_review_can_be_rejected(self):
        r, cur = repo_of(fetch=[('READY_FOR_REVIEW',)])
        out = r.reject('mod_1', 'proj_1', reason='not what I wanted')
        self.assertEqual(out, {'rejected': True})
        self.assertEqual(len(cur.executed), 2)
        update_sql, update_params = cur.executed[1]
        self.assertIn("SET status='REJECTED'", update_sql)
        self.assertEqual(update_params, ('not what I wanted', 'mod_1'))
        self.assertTrue(all('project_versions' not in s for s, _ in cur.executed))

    def test_failed_needs_clarification_and_conflict_are_all_rejectable(self):
        for status in ('FAILED', 'NEEDS_CLARIFICATION', 'CONFLICT'):
            r, cur = repo_of(fetch=[(status,)])
            self.assertEqual(r.reject('mod_1', 'proj_1'), {'rejected': True})

    def test_non_rejectable_statuses_are_left_alone(self):
        for status in ('QUEUED', 'RUNNING', 'ACCEPTED', 'REJECTED'):
            r, cur = repo_of(fetch=[(status,)])
            out = r.reject('mod_1', 'proj_1')
            self.assertEqual(out, {'rejected': False, 'status': status})
            self.assertEqual(len(cur.executed), 1)  # SELECT only, no UPDATE

    def test_not_found_raises(self):
        r, cur = repo_of(fetch=[None])
        with self.assertRaises(KeyError):
            r.reject('mod_missing', 'proj_1')


# ===========================================================================
# rollback() -- real MemoryProjectWorkspace.restore(), FakeSpecRepo
# ===========================================================================

class RollbackTests(unittest.TestCase):
    def test_rollback_restores_historical_content_and_carries_the_spec_forward(self):
        workspace = MemoryProjectWorkspace()
        v1 = workspace.commit(project_id='proj_1', repository={'a.py': '1'}, message='v1')
        workspace.commit(project_id='proj_1', repository={'a.py': '2'}, message='v2')
        spec_repo = FakeSpecRepo()
        spec_repo.save(version_id=v1.id, project_id='proj_1', spec=ProductSpec.from_dict(SPEC))

        out = spec_repo, workspace  # noqa: for readability of the next line
        result = PostgresModificationRepository(FakePool(ScriptedCursor())).rollback(
            'proj_1', target_version_id=v1.id, workspace=workspace, spec_repo=spec_repo,
        )

        self.assertNotEqual(result['version_id'], v1.id)  # a new version, not a pointer move
        self.assertEqual(result['restored_from'], v1.id)
        self.assertTrue(result['spec_restored'])
        restored = workspace.get(project_id='proj_1', version_id=result['version_id'])
        self.assertEqual(restored.repository(), {'a.py': '1'})
        self.assertEqual(spec_repo._store[result['version_id']].title, 'Todo')

    def test_rollback_to_a_version_with_no_spec_row_still_restores_the_repository(self):
        workspace = MemoryProjectWorkspace()
        v1 = workspace.commit(project_id='proj_1', repository={'a.py': 'pre-m4b'}, message='v1')
        spec_repo = FakeSpecRepo()  # nothing stored for v1

        result = PostgresModificationRepository(FakePool(ScriptedCursor())).rollback(
            'proj_1', target_version_id=v1.id, workspace=workspace, spec_repo=spec_repo,
        )

        self.assertFalse(result['spec_restored'])
        restored = workspace.get(project_id='proj_1', version_id=result['version_id'])
        self.assertEqual(restored.repository(), {'a.py': 'pre-m4b'})
        self.assertNotIn(result['version_id'], spec_repo._store)

    def test_rollback_to_a_nonexistent_version_raises(self):
        workspace = MemoryProjectWorkspace()
        workspace.commit(project_id='proj_1', repository={'a.py': '1'}, message='v1')
        with self.assertRaises(KeyError):
            PostgresModificationRepository(FakePool(ScriptedCursor())).rollback(
                'proj_1', target_version_id='v_nope', workspace=workspace, spec_repo=FakeSpecRepo(),
            )


if __name__ == '__main__':
    unittest.main()

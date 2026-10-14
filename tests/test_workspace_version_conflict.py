"""M4D.1: direct tests of workspace.py's atomic expected-version check --
the actual mechanism that closes the production-blocking bug an independent
architecture review found in the original M4D design (a post-commit
`new_version.parent_id != source_version_id` check, which could only ever
run AFTER the new ProjectVersion already existed and `current()` had
already silently advanced).

What's proven here, at the workspace level (modification_repository.py's
own tests, and tests/test_m4d1_atomic_accept.py, prove the same property one
layer up, through accept()):

  - `commit(..., expected_current_version_id=X)` compares X against the
    REAL current version under the same lock (MemoryProjectWorkspace's
    `self._lock`) or the same advisory-locked transaction
    (PostgresProjectWorkspace's `pg_advisory_xact_lock`, held on the same
    cursor from the read through the insert) that would perform the write.
  - A mismatch raises VersionConflict BEFORE any row is written / any
    version is appended -- never after.
  - The default (no `expected_current_version_id` passed at all) is
    byte-for-byte the pre-M4D.1 behavior: unconditional commit. Every other
    call site in this codebase (ordinary builds, v26/27/28 platform routes,
    unified_engine.py, worker_tasks.py) calls `commit()` this way and none
    of them needed to change for M4D.1.
  - `cur`, when given, lets PostgresProjectWorkspace.commit() participate in
    a caller's already-open transaction instead of opening its own --
    proven here by handing it a pool that raises if `.connection()` is ever
    called, so a passing test is itself proof the pool was never touched.

Run with: python3 -m unittest tests.test_workspace_version_conflict -v
"""
import unittest

from omni_prod.workspace import (
    MemoryProjectWorkspace, PostgresProjectWorkspace, SKIP_VERSION_CHECK, VersionConflict,
)


# ===========================================================================
# Fakes
# ===========================================================================

class ScriptedCursor:
    def __init__(self, fetch=()):
        self.executed: list[tuple[str, object]] = []
        self._fetch = list(fetch)

    def execute(self, sql, params=None):
        self.executed.append((' '.join(sql.split()), params))

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
    """A pool that fails the test the moment anything asks it for a
    connection -- used to prove the shared-`cur` path never does."""
    def connection(self):
        raise AssertionError('commit() must not open its own connection when a cur is given')


class FakeStorage:
    """Content-addressed blob store double for PostgresProjectWorkspace --
    irrelevant to the version-conflict logic under test, just needs to not
    explode."""
    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    def get_bytes(self, key, verify=False):
        if key not in self.blobs:
            raise KeyError(key)
        return self.blobs[key]

    def put_bytes(self, key, data):
        self.blobs[key] = data


# ===========================================================================
# MemoryProjectWorkspace
# ===========================================================================

class MemoryWorkspaceTests(unittest.TestCase):
    def test_default_commit_is_unconditional_matching_every_pre_m4d1_call_site(self):
        """No `expected_current_version_id` at all -- the call shape every
        existing caller (builds, v26/27/28 platforms, unified_engine,
        worker_tasks) uses -- must behave exactly as before M4D.1: commit
        unconditionally on top of whatever is current."""
        ws = MemoryProjectWorkspace()
        v1 = ws.commit(project_id='p1', repository={'a': '1'}, message='v1')
        v2 = ws.commit(project_id='p1', repository={'a': '2'}, message='v2')
        self.assertEqual(v2.parent_id, v1.id)
        self.assertEqual(ws.current('p1').id, v2.id)

    def test_matching_expectation_succeeds(self):
        ws = MemoryProjectWorkspace()
        v1 = ws.commit(project_id='p1', repository={'a': '1'}, message='v1')
        v2 = ws.commit(project_id='p1', repository={'a': '2'}, message='v2',
                       expected_current_version_id=v1.id)
        self.assertEqual(v2.parent_id, v1.id)
        self.assertEqual(ws.current('p1').id, v2.id)

    def test_mismatched_expectation_raises_before_any_write(self):
        ws = MemoryProjectWorkspace()
        v1 = ws.commit(project_id='p1', repository={'a': '1'}, message='v1')
        v2 = ws.commit(project_id='p1', repository={'a': '2'}, message='v2')  # current moves to v2

        with self.assertRaises(VersionConflict) as ctx:
            ws.commit(project_id='p1', repository={'a': 'unwanted'}, message='stale',
                      expected_current_version_id=v1.id)  # stale expectation

        exc = ctx.exception
        self.assertEqual(exc.project_id, 'p1')
        self.assertEqual(exc.expected_current_version_id, v1.id)
        self.assertEqual(exc.actual_current_version_id, v2.id)
        # The whole point: current() and history() are provably unaffected
        # by the rejected attempt -- not "rolled back," never written.
        self.assertEqual(ws.current('p1').id, v2.id)
        self.assertEqual(len(ws.history('p1')), 2)

    def test_expected_none_matches_the_empty_project(self):
        ws = MemoryProjectWorkspace()
        v1 = ws.commit(project_id='p1', repository={'a': '1'}, message='first ever',
                       expected_current_version_id=None)
        self.assertIsNone(v1.parent_id)
        self.assertEqual(ws.current('p1').id, v1.id)

    def test_expected_none_mismatches_once_a_version_already_exists(self):
        ws = MemoryProjectWorkspace()
        ws.commit(project_id='p1', repository={'a': '1'}, message='v1')
        with self.assertRaises(VersionConflict):
            ws.commit(project_id='p1', repository={'a': '2'}, message='v2',
                      expected_current_version_id=None)  # no longer true -- v1 exists

    def test_cur_kwarg_is_accepted_and_ignored(self):
        """MemoryProjectWorkspace has no SQL connection to share -- `cur` is
        accepted only so callers (modification_repository.accept()) can
        pass the same keyword to either workspace implementation without
        branching on type."""
        ws = MemoryProjectWorkspace()
        v = ws.commit(project_id='p1', repository={'a': '1'}, message='v1', cur=object())
        self.assertEqual(ws.current('p1').id, v.id)

    def test_restore_forwards_cur_and_still_recommits_exact_historical_content(self):
        ws = MemoryProjectWorkspace()
        v1 = ws.commit(project_id='p1', repository={'a': 'original'}, message='v1')
        ws.commit(project_id='p1', repository={'a': 'changed'}, message='v2')
        restored = ws.restore(project_id='p1', version_id=v1.id, cur=object())
        self.assertEqual(restored.repository(), {'a': 'original'})
        self.assertNotEqual(restored.id, v1.id)


# ===========================================================================
# PostgresProjectWorkspace (fake pool/cursor -- no live Postgres here)
# ===========================================================================

class PostgresWorkspaceTests(unittest.TestCase):
    def test_default_commit_opens_its_own_transaction_and_is_unconditional(self):
        cur = ScriptedCursor(fetch=[('whatever_is_current',)])
        pool = FakePool(cur)
        ws = PostgresProjectWorkspace(pool, FakeStorage())
        v = ws.commit(project_id='p1', repository={'a': '1'}, message='m')
        self.assertEqual(v.parent_id, 'whatever_is_current')
        self.assertTrue(any('INSERT INTO project_versions' in s for s, _ in cur.executed))
        self.assertEqual(pool.conn.transactions, 1)

    def test_matching_expectation_inserts(self):
        cur = ScriptedCursor(fetch=[('v10',)])
        ws = PostgresProjectWorkspace(FakePool(cur), FakeStorage())
        v = ws.commit(project_id='p1', repository={'a': '1'}, message='m',
                      expected_current_version_id='v10')
        self.assertEqual(v.parent_id, 'v10')
        self.assertTrue(any('INSERT INTO project_versions' in s for s, _ in cur.executed))

    def test_mismatched_expectation_raises_and_never_inserts(self):
        cur = ScriptedCursor(fetch=[('v11',)])  # real current has moved to v11
        ws = PostgresProjectWorkspace(FakePool(cur), FakeStorage())
        with self.assertRaises(VersionConflict) as ctx:
            ws.commit(project_id='p1', repository={'a': '1'}, message='m',
                      expected_current_version_id='v10')
        self.assertEqual(ctx.exception.expected_current_version_id, 'v10')
        self.assertEqual(ctx.exception.actual_current_version_id, 'v11')
        self.assertFalse(any('INSERT INTO project_versions' in s for s, _ in cur.executed))

    def test_lock_is_taken_and_current_is_read_before_any_insert_decision(self):
        """Statement ordering matters for the atomicity claim: the advisory
        lock must be acquired, and the current version read, strictly
        before the INSERT (or the raise) -- proving the read that decides
        the outcome and the write that would apply it are both inside the
        same locked window, not two separate round trips."""
        cur = ScriptedCursor(fetch=[('v10',)])
        ws = PostgresProjectWorkspace(FakePool(cur), FakeStorage())
        ws.commit(project_id='p1', repository={'a': '1'}, message='m',
                  expected_current_version_id='v10')
        kinds = [sql.split()[0:2] for sql, _ in cur.executed]
        self.assertIn('pg_advisory_xact_lock', cur.executed[0][0])
        self.assertTrue(cur.executed[1][0].startswith('SELECT id FROM project_versions'))
        self.assertTrue(cur.executed[2][0].startswith('INSERT INTO project_versions'))

    def test_shared_cur_never_opens_a_connection_from_the_pool(self):
        """The strongest proof that commit(cur=...) truly participates in
        the caller's transaction rather than opening a second one: give it
        a pool that raises if `.connection()` is ever called at all."""
        cur = ScriptedCursor(fetch=[('v10',)])
        ws = PostgresProjectWorkspace(ExplodingPool(), FakeStorage())
        v = ws.commit(project_id='p1', repository={'a': '1'}, message='m',
                      expected_current_version_id='v10', cur=cur)
        self.assertEqual(v.parent_id, 'v10')

    def test_shared_cur_mismatch_raises_without_insert_and_without_touching_the_pool(self):
        cur = ScriptedCursor(fetch=[('v11',)])
        ws = PostgresProjectWorkspace(ExplodingPool(), FakeStorage())
        with self.assertRaises(VersionConflict):
            ws.commit(project_id='p1', repository={'a': '1'}, message='m',
                      expected_current_version_id='v10', cur=cur)
        self.assertFalse(any('INSERT INTO project_versions' in s for s, _ in cur.executed))

    def test_restore_forwards_cur_to_commit(self):
        """PostgresProjectWorkspace.restore() must not silently open its own
        connection for the write half once a caller (rollback()) is trying
        to merge everything into one transaction."""
        get_cur = ScriptedCursor(fetch=[(None, '2026-01-01T00:00:00+00:00', 'v1', 'abc123',
                                         'repositories/abc123.zip', 1)])
        storage = FakeStorage()
        storage.blobs['repositories/abc123.zip'] = _zip_of({'a': 'original'})
        get_pool = FakePool(get_cur)
        ws = PostgresProjectWorkspace(get_pool, storage)

        commit_cur = ScriptedCursor(fetch=[('current_elsewhere',)])
        restored = ws.restore(project_id='p1', version_id='v1', cur=commit_cur)
        self.assertEqual(restored.repository(), {'a': 'original'})
        # The write went through the SHARED cur, not a fresh connection --
        # get_pool.conn is untouched beyond the one read `get()` needed.
        self.assertTrue(any('INSERT INTO project_versions' in s for s, _ in commit_cur.executed))


def _zip_of(repo: dict[str, str]) -> bytes:
    import io, zipfile
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in repo.items():
            zf.writestr(path, content)
    return out.getvalue()


if __name__ == '__main__':
    unittest.main()

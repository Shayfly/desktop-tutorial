import unittest

from omni_prod.product_spec import ProductSpec
from omni_prod.spec_repository import PostgresSpecRepository, SpecNotFound

SPEC = {
    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
}


class ScriptedCursor:
    """Mirrors omni_prod/db.py's DatabasePool cursor contract, same pattern
    tests/test_m3_preview_logic.py uses for PostgresPreviewRepository."""
    def __init__(self, fetch=()):
        self.executed = []
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

    def cursor(self):
        return self.cur

    def transaction(self):
        return _Ctx()


class FakePool:
    def __init__(self, cur):
        self.conn = FakeConn(cur)

    def connection(self):
        return _Ctx(self.conn)


class SaveTests(unittest.TestCase):
    def test_save_writes_jsonb_and_is_idempotent_on_conflict(self):
        cur = ScriptedCursor()
        repo = PostgresSpecRepository(FakePool(cur))
        repo.save(version_id='v_1', project_id='proj_1', spec=ProductSpec.from_dict(SPEC))
        sql, params = cur.executed[0]
        self.assertIn('INSERT INTO project_version_specs', sql)
        self.assertIn('ON CONFLICT (version_id) DO NOTHING', sql)
        self.assertEqual(params[0], 'v_1')
        self.assertEqual(params[1], 'proj_1')
        # params[2] is json.dumps(spec.to_dict()); confirm it round-trips.
        import json
        self.assertEqual(json.loads(params[2])['title'], 'Todo')

    def test_save_with_caller_managed_cursor_does_not_open_its_own_connection(self):
        outer_cur = ScriptedCursor()

        class ExplodingPool:
            def connection(self):
                raise AssertionError('save(cur=...) must not open its own connection')

        repo = PostgresSpecRepository(ExplodingPool())
        repo.save(version_id='v_1', project_id='proj_1', spec=ProductSpec.from_dict(SPEC), cur=outer_cur)
        self.assertEqual(len(outer_cur.executed), 1)


class GetTests(unittest.TestCase):
    def test_get_returns_the_exact_spec_for_that_version(self):
        import json
        cur = ScriptedCursor(fetch=[(json.dumps(SPEC),)])
        repo = PostgresSpecRepository(FakePool(cur))
        spec = repo.get('v_1', 'proj_1')
        self.assertEqual(spec.title, 'Todo')
        self.assertEqual(cur.executed[0][1], ('v_1', 'proj_1'))

    def test_get_accepts_a_driver_that_already_decodes_jsonb_to_dict(self):
        # Some psycopg configurations return JSONB columns already decoded;
        # get() must handle both a raw string and an already-parsed dict.
        cur = ScriptedCursor(fetch=[(SPEC,)])
        repo = PostgresSpecRepository(FakePool(cur))
        spec = repo.get('v_1', 'proj_1')
        self.assertEqual(spec.title, 'Todo')

    def test_get_is_project_scoped_and_raises_when_missing(self):
        cur = ScriptedCursor(fetch=[None])
        repo = PostgresSpecRepository(FakePool(cur))
        with self.assertRaises(SpecNotFound):
            repo.get('v_missing', 'proj_1')


if __name__ == '__main__':
    unittest.main()

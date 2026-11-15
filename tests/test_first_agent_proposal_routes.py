"""The proposal API routes exist and validate their input (runs where fastapi is installed: CI)."""
import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec('fastapi'), 'fastapi is required to import the app')
class ProposalRoutes(unittest.TestCase):
    def test_routes_and_edit_validation(self):
        from pydantic import ValidationError
        from omni_prod import investor_app as A
        paths = {(r.path, tuple(sorted(r.methods))) for r in A.app.routes if hasattr(r, 'methods')}
        self.assertIn(('/api/v28/projects/{project_id}/proposal', ('GET',)), paths)
        self.assertIn(('/api/v28/projects/{project_id}/proposal/edit', ('POST',)), paths)
        self.assertIn(('/api/v28/projects/{project_id}/proposal/undo', ('POST',)), paths)
        A.V28ProposalEdit(revision=3, op='move_up', key='hours')
        for bad in ({'revision': 0, 'op': 'move_up', 'key': 'hours'}, {'revision': 1, 'op': 'rewrite_brief', 'key': 'x'}):
            with self.assertRaises(ValidationError):
                A.V28ProposalEdit(**bad)


if __name__ == '__main__':
    unittest.main()

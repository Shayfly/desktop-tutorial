import unittest

from omni_prod.modification_diff import diff_modification, diff_repositories, diff_specs
from omni_prod.product_spec import ProductSpec

SPEC = {
    'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
    'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
    'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'}],
}


class RepositoryDiffTests(unittest.TestCase):
    def test_added_modified_deleted_are_detected(self):
        old = {'a.py': '1', 'b.py': '2', 'c.py': '3'}
        new = {'a.py': '1', 'b.py': 'CHANGED', 'd.py': '4'}
        d = diff_repositories(old, new)
        self.assertEqual(d.added, ('d.py',))
        self.assertEqual(d.modified, ('b.py',))
        self.assertEqual(d.deleted, ('c.py',))
        self.assertFalse(d.is_empty)

    def test_identical_repositories_produce_empty_diff(self):
        repo = {'a.py': '1'}
        d = diff_repositories(repo, dict(repo))
        self.assertTrue(d.is_empty)
        self.assertEqual(d.added, ())
        self.assertEqual(d.modified, ())
        self.assertEqual(d.deleted, ())

    def test_dependency_manifest_change_is_flagged(self):
        old = {'requirements.txt': 'flask'}
        new = {'requirements.txt': 'flask\ndjango'}
        d = diff_repositories(old, new)
        self.assertEqual(d.dependency_manifests_changed, ('requirements.txt',))

    def test_nested_dependency_manifest_matched_by_basename(self):
        old = {'backend/package.json': '{}'}
        new = {'backend/package.json': '{"x":1}'}
        d = diff_repositories(old, new)
        self.assertEqual(d.dependency_manifests_changed, ('backend/package.json',))

    def test_schema_file_change_is_flagged(self):
        old = {}
        new = {'migrations/0001_init.sql': 'CREATE TABLE x();'}
        d = diff_repositories(old, new)
        self.assertEqual(d.schema_files_changed, ('migrations/0001_init.sql',))

    def test_security_sensitive_file_change_is_flagged(self):
        old = {'app/auth.py': 'old'}
        new = {'app/auth.py': 'new'}
        d = diff_repositories(old, new)
        self.assertEqual(d.security_sensitive_files_changed, ('app/auth.py',))

    def test_unrelated_file_is_not_flagged_in_any_special_category(self):
        old = {'app.py': '1'}
        new = {'app.py': '2'}
        d = diff_repositories(old, new)
        self.assertEqual(d.dependency_manifests_changed, ())
        self.assertEqual(d.schema_files_changed, ())
        self.assertEqual(d.security_sensitive_files_changed, ())

    def test_diff_is_deterministic_regardless_of_dict_insertion_order(self):
        old1 = {'a.py': '1', 'b.py': '2'}
        old2 = {'b.py': '2', 'a.py': '1'}
        new = {'a.py': '1', 'b.py': 'X', 'c.py': '3'}
        self.assertEqual(diff_repositories(old1, new), diff_repositories(old2, new))


class SpecDiffTests(unittest.TestCase):
    def test_identical_specs_produce_empty_diff(self):
        spec = ProductSpec.from_dict(SPEC)
        d = diff_specs(spec, ProductSpec.from_dict(SPEC))
        self.assertTrue(d.is_empty)

    def test_added_requirement_and_acceptance_are_detected(self):
        old = ProductSpec.from_dict(SPEC)
        new_dict = {
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [
                {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
                {'id': 'R2', 'text': 'calendar', 'kind': 'functional', 'mandatory': True},
            ],
            'acceptance': [
                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
                {'id': 'A2', 'requirement_id': 'R2', 'text': 'calendar renders'},
            ],
        }
        new = ProductSpec.from_dict(new_dict)
        d = diff_specs(old, new)
        self.assertEqual(d.requirements_added, ('R2',))
        self.assertEqual(d.acceptance_added, ('A2',))
        self.assertEqual(d.requirements_removed, ())
        self.assertEqual(d.acceptance_removed, ())
        self.assertFalse(d.is_empty)

    def test_changed_requirement_text_is_detected_as_changed_not_added_or_removed(self):
        old = ProductSpec.from_dict(SPEC)
        new_dict = dict(SPEC)
        new_dict['requirements'] = [{'id': 'R1', 'text': 'show todos SORTED BY DUE DATE', 'kind': 'functional', 'mandatory': True}]
        new = ProductSpec.from_dict(new_dict)
        d = diff_specs(old, new)
        self.assertEqual(d.requirements_changed, ('R1',))
        self.assertEqual(d.requirements_added, ())
        self.assertEqual(d.requirements_removed, ())

    def test_title_and_stack_changes_are_detected(self):
        old = ProductSpec.from_dict(SPEC)
        new_dict = dict(SPEC)
        new_dict['title'] = 'Super Todo'
        new_dict['stack'] = ['python', 'redis']
        new = ProductSpec.from_dict(new_dict)
        d = diff_specs(old, new)
        self.assertTrue(d.title_changed)
        self.assertEqual(d.stack_added, ('redis',))
        self.assertFalse(d.summary_changed)


class ModificationDiffTests(unittest.TestCase):
    def test_combines_repository_and_spec_diffs(self):
        spec = ProductSpec.from_dict(SPEC)
        d = diff_modification(
            old_repository={'app.py': '1'}, new_repository={'app.py': '2', 'new.py': 'x'},
            old_spec=spec, new_spec=spec,
        )
        self.assertEqual(d.repository.added, ('new.py',))
        self.assertTrue(d.spec.is_empty)
        as_dict = d.to_dict()
        self.assertIn('repository', as_dict)
        self.assertIn('spec', as_dict)


if __name__ == '__main__':
    unittest.main()

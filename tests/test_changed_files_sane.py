"""scripts/changed_files_sane.py (the `light` CI job): the same marker rule as commit_resolved.sh, and JSON parses."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from changed_files_sane import problems  # noqa: E402


class ChangedFilesSane(unittest.TestCase):
    def check(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as d:
            for name, text in files.items():
                (Path(d) / name).write_text(text, encoding='utf-8')
            return problems(list(files) + ['deleted.json'], Path(d))

    def test_a_conflict_left_in_a_file_is_named(self):
        found = self.check({'a.json': '{\n<<<<<<< HEAD\n"a": 1\n=======\n"a": 2\n>>>>>>> main\n}\n'})
        self.assertEqual([f.split(':')[0] for f in found], ['a.json', 'a.json'])   # markers, and invalid json
        self.assertIn('3 conflict marker line(s)', found[0])

    def test_a_markdown_rule_alone_is_not_a_marker(self):
        self.assertEqual(self.check({'r.md': 'Title\n=======\nbody\n'}), [])

    def test_broken_json_is_named_and_a_deleted_file_is_not(self):
        found = self.check({'x.json': '{"a": \n', 'ok.json': '{"a": 1}'})
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].startswith('x.json: invalid json'))


if __name__ == '__main__':
    unittest.main()

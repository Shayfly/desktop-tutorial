import importlib.util
from pathlib import Path
import unittest
import yaml

class CIYamlValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'scripts/validate_workflows.py'
        spec = importlib.util.spec_from_file_location('validate_workflows', path)
        cls.validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.validator)

    def test_duplicate_keys_are_rejected_at_any_depth(self):
        for text in ('on: push\non: pull_request', 'jobs:\n  test:\n    timeout-minutes: 10\n    timeout-minutes: 20'):
            with self.assertRaisesRegex(ValueError, 'duplicate YAML key'):
                yaml.load(text, Loader=self.validator.UniqueLoader)

    def test_on_is_not_misread_as_boolean(self):
        data = yaml.load('on:\n  push:\npermissions:\n  contents: read', Loader=self.validator.UniqueLoader)
        self.assertIn('on', data)
        self.assertNotIn(True, data)

    def test_invalid_yaml_is_rejected(self):
        with self.assertRaises(yaml.YAMLError):
            yaml.load('jobs: [unterminated', Loader=self.validator.UniqueLoader)

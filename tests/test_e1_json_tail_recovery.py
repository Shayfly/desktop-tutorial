"""E1: the first complete JSON object survives the exact 7807/7825 extra-data shape."""
import json
import unittest

from omni_prod.model_gateway import parse_model_json


class E1TailRecovery(unittest.TestCase):
    @staticmethod
    def failed_shape():
        # First JSON object ends at byte/character 7807; the 18-char unknown tail
        # deliberately stays UNKNOWN rather than being mislabelled Markdown.
        prefix = '{"files":[{"path":".omni/project.json","content":"'
        suffix = '"}]}'
        body = prefix + ('x' * (7807 - len(prefix) - len(suffix))) + suffix
        assert len(body) == 7807
        return body + 'UNEXPLAINED_TAIL_18'

    def test_real_error_shape_recovers_without_silent_tail_discard(self):
        raw = self.failed_shape()
        self.assertEqual(len(raw), 7825)
        with self.assertRaises(json.JSONDecodeError) as previous_failure:
            json.loads(raw)
        self.assertEqual(previous_failure.exception.pos, 7807)
        obj, diagnostic = parse_model_json(raw)
        self.assertIsInstance(obj, dict)
        self.assertEqual(obj['files'][0]['path'], '.omni/project.json')
        self.assertEqual(diagnostic['verdict'], 'accepted_with_unexplained_tail')
        self.assertEqual(diagnostic['trailing_chars'], 18)
        self.assertEqual(diagnostic['tail_status'], 'unexplained')
        self.assertEqual(diagnostic['tail'], raw[7807:])

    def test_second_object_is_recorded_not_mislabelled_as_clean(self):
        obj, diagnostic = parse_model_json('{"files":[]}{"other":true}')
        self.assertEqual(obj, {'files': []})
        self.assertEqual(diagnostic['tail_status'], 'unexplained')
        self.assertEqual(diagnostic['tail'], '{"other":true}')

    def test_bad_first_object_is_not_recovered(self):
        obj, diagnostic = parse_model_json('{"files": invalid}tail')
        self.assertIsNone(obj)
        self.assertEqual(diagnostic['verdict'], 'rejected')


if __name__ == '__main__':
    unittest.main()

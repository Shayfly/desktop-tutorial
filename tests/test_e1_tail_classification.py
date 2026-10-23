"""H1 deterministic tail classes. No external model calls."""
import unittest
from omni_prod.model_gateway import parse_model_json

class TailClassification(unittest.TestCase):
    def verify(self, raw, status, verdict):
        obj, diag = parse_model_json(raw)
        self.assertEqual(obj, {'files': []})
        self.assertEqual(diag['tail_status'], status)
        self.assertEqual(diag['verdict'], verdict)
        self.assertEqual(diag['tail'], raw.strip()[len('{"files": []}'):])
        self.assertEqual(diag['trailing_chars'], len(diag['tail'].strip()))
        self.assertEqual(diag['trailing_starts'], diag['tail'].strip()[:80])
        return diag

    def test_benign_empty(self):
        self.verify('{"files": []}  ', 'benign_empty', 'accepted')
        self.verify('{"files": []}   \\n', 'benign_empty', 'accepted')

    def test_empty_tail_forms_are_classified_by_shape(self):
        root = '{"files": []}'
        for suffix in ('  ', '\n', '\\n', '\\t', '\\n\\t', '  \\n  '):
            with self.subTest(suffix=repr(suffix)):
                obj, diag = parse_model_json(root + suffix)
                self.assertEqual(obj, {'files': []})
                self.assertEqual(diag['tail_status'], 'benign_empty')
                self.assertEqual(diag['verdict'], 'accepted')
                self.assertFalse(diag['tail_conflict'])

    def test_benign_prose(self):
        self.verify('{"files": []} AND ALSO', 'benign_prose', 'accepted_with_unexplained_tail')

    def test_benign_second_object_match(self):
        self.verify('{"files": []} {"files": []}', 'benign_second_object_match', 'accepted_with_unexplained_tail')

    def test_conflict_second_object_is_flagged(self):
        d = self.verify('{"files": []} {"files": [1]}', 'conflict_second_object', 'accepted_with_conflict')
        self.assertTrue(d['tail_conflict'])

    def test_malformed_tail_is_flagged(self):
        d = self.verify('{"files": []} {"files":', 'malformed_tail', 'accepted_with_conflict')
        self.assertTrue(d['tail_conflict'])

    def test_negative_tail_not_silently_eaten(self):
        d = self.verify('{"files": []} SUSPICIOUS', 'benign_prose', 'accepted_with_unexplained_tail')
        self.assertEqual(d['tail'], ' SUSPICIOUS')


    def test_required_whitespace_and_18_character_examples(self):
        self.verify('{"files": []}\\n\\nNote: I also changed b.py', 'benign_prose', 'accepted_with_unexplained_tail')
        self.verify('{"files": []}UNEXPLAINED_TAIL18', 'benign_prose', 'accepted_with_unexplained_tail')
        self.verify('{"files": []}{"files": []}', 'benign_second_object_match', 'accepted_with_unexplained_tail')
        self.verify('{"files": []}{"other":true}', 'conflict_second_object', 'accepted_with_conflict')
        self.verify('{"files": []}  {"broken":}  ', 'malformed_tail', 'accepted_with_conflict')

    def test_invalid_first_object_still_rejected(self):
        obj, diag = parse_model_json('{"files": invalid}tail')
        self.assertIsNone(obj)
        self.assertEqual(diag['verdict'], 'rejected')

    def test_existing_consistency_verification_reports_conflict(self):
        from omni_prod.consistency_gate import ConsistencyGateExecutor
        from types import SimpleNamespace
        executor = ConsistencyGateExecutor(SimpleNamespace(), enabled=True)
        executor.record_model_json_conflicts([{'task': 'codegen', 'attempt_seq': 3,
                                               'tail_status': 'conflict_second_object'}])
        report = executor.last_consistency
        self.assertTrue(report['passed'])
        self.assertIn('model_json_tail', report['checks_run'])
        self.assertTrue(any(f['check'] == 'model_json_tail' and
                            'conflict_second_object' in f['message']
                            for f in report['advisories']))


    def test_worker_build_evidence_contains_consistency_conflict(self):
        from types import SimpleNamespace
        from omni_prod.consistency_gate import ConsistencyGateExecutor
        from omni_prod.worker_tasks import consistency_evidence, rejected_json_evidence
        wrapper = ConsistencyGateExecutor(SimpleNamespace(), enabled=True)
        engine = SimpleNamespace(executor=wrapper)
        gateway = SimpleNamespace(accepted_json_manifest=[{
            'task': 'codegen', 'attempt_seq': 11, 'diagnostic': {
                'tail_status': 'conflict_second_object', 'tail_conflict': True,
                'tail': '{"other":true}'}}])
        manifest = {
            'consistency_gate': consistency_evidence(engine, gateway),
            **rejected_json_evidence(gateway),
        }
        self.assertIn('model_json_tail', manifest['consistency_gate']['last']['checks_run'])
        self.assertTrue(any(
            item['check'] == 'model_json_tail' and 'conflict_second_object' in item['message']
            for item in manifest['consistency_gate']['last']['advisories']))
        self.assertEqual(manifest['model_json_tail_conflicts'][0]['tail_status'],
                         'conflict_second_object')

    def test_non_conflicting_build_evidence_unchanged_on_both_paths(self):
        from types import SimpleNamespace
        from omni_prod.consistency_gate import ConsistencyGateExecutor
        from omni_prod.worker_tasks import consistency_evidence, rejected_json_evidence
        for manifest_rows in ([], [{'task': 'codegen', 'attempt_seq': 11,
                                      'diagnostic': {'tail_conflict': False,
                                                     'tail_status': 'benign_prose'}}]):
            with self.subTest(rows=manifest_rows):
                gate = ConsistencyGateExecutor(SimpleNamespace(), enabled=True)
                # Reproduce the pre-existing report shape, before evidence serialization.
                gate.last_consistency = {'passed': True, 'checks_run': ['syntax'],
                                         'skipped': {}, 'blocking': [], 'advisories': []}
                gate.consistency_rounds = [{'passed': True, 'blocking': 0, 'advisories': 0}]
                engine = SimpleNamespace(executor=gate)
                gateway = SimpleNamespace(accepted_json_manifest=manifest_rows)
                original = {'last': dict(gate.last_consistency),
                            'rounds': list(gate.consistency_rounds)}
                quality_path = consistency_evidence(engine, gateway)
                build_path = {'consistency_gate': consistency_evidence(engine, gateway),
                              **rejected_json_evidence(gateway)}
                self.assertEqual(quality_path, original)
                self.assertEqual(build_path['consistency_gate'], original)
                self.assertNotIn('model_json_tail', quality_path['last']['checks_run'])
                self.assertEqual(quality_path['last']['advisories'], [])
                self.assertEqual(build_path['model_json_tail_conflicts'], [])

if __name__ == '__main__':
    unittest.main()

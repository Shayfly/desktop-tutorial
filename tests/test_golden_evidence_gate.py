"""Synthetic evidence tests; their PASS is never a live Golden E2E claim."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'verify_golden_evidence.py'
IDENTITY = {'run_id': '123', 'build_id': 'bld_test', 'commit': 'a' * 40}


class GoldenEvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('app.py', 'print("hello")\n')
            z.writestr('index.html', '<html lang="he">שלום</html>')
        self.artifact = self.blob('source.zip', data.getvalue())
        self.shot = self.blob('preview.png', bytes.fromhex(
            '89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02'
            '0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082'))
        self.receipts = {
            'input': {**IDENTITY, 'prompt': 'בנה אתר בעברית', 'channel': 'customer_ui',
                      'submitted_at': '2026-10-19T20:00:00.000Z',
                      'accepted_at': '2026-10-19T20:00:00.010Z',
                      'requirements': [{'id': 'A1', 'text': 'הדף נפתח בעברית'}],
                      'provider_request_ids': ['req-1']},
            'r2': {**IDENTITY, 'provider': 'cloudflare_r2', 'bucket': 'test-bucket',
                   'key': 'bld_test/source.zip', 'version_id': 'v_test',
                   'put_status': 200, 'get_status': 200,
                   'written_at': '2026-10-19T20:00:01.000Z',
                   'readback_at': '2026-10-19T20:00:01.100Z',
                   'bytes_written': len(data.getvalue()), 'file_count': 2,
                   'sha256': self.artifact['sha256'], 'readback_sha256': self.artifact['sha256'],
                   'artifact': self.artifact},
            'preview': {**IDENTITY, 'url': 'https://preview.example.test/p/bld_test',
                        'http_status': 200, 'browser': 'playwright', 'status': 'PASS',
                        'version_id': 'v_test', 'artifact_sha256': self.artifact['sha256'],
                        'opened_at': '2026-10-19T20:00:01.200Z',
                        'verified_at': '2026-10-19T20:00:02.000Z',
                        'checks': [{'acceptance_id': 'A1', 'passed': True, 'detail': 'Hebrew content rendered'}],
                        'screenshot': self.shot},
            'accounting': {**IDENTITY, 'currency': 'USD', 'cost_status': 'KNOWN',
                           'actual_cost_usd': '0.010000', 'elapsed_ms': 2000,
                           'queue_ms': 10, 'started_monotonic_ns': 1000000000,
                           'finished_monotonic_ns': 3000000000,
                           'includes_retries': True, 'includes_repairs': True},
        }
        self.ledger = {**IDENTITY, 'complete': True, 'entries': [
            {'id': 'e1', 'kind': 'model', 'actual_cost_usd': '0.01', 'basis': 'measured', 'source_id': 'req-1'},
            {'id': 'e2', 'kind': 'compute', 'actual_cost_usd': '0', 'basis': 'reconciled', 'source_id': 'compute-1'},
            {'id': 'e3', 'kind': 'storage', 'actual_cost_usd': '0', 'basis': 'reconciled', 'source_id': 'storage-1'},
            {'id': 'e4', 'kind': 'egress', 'actual_cost_usd': '0', 'basis': 'reconciled', 'source_id': 'egress-1'}]}
        self.manifest = {**IDENTITY, 'schema_version': 1, 'manual_steps': 0}

    def blob(self, name, value):
        (self.root / name).write_bytes(value)
        return {'path': name, 'sha256': hashlib.sha256(value).hexdigest()}

    def flush(self):
        self.receipts['accounting']['ledger'] = self.blob('ledger.json', json.dumps(self.ledger).encode())
        for name, value in self.receipts.items():
            self.manifest[name] = self.blob(name + '.json', json.dumps(value, ensure_ascii=False).encode())
        (self.root / 'manifest.json').write_text(json.dumps(self.manifest))

    def run_gate(self, flush=True, extra=()):
        if flush:
            self.flush()
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.root / 'manifest.json'),
                            '--run-id', IDENTITY['run_id'], '--build-id', IDENTITY['build_id'],
                            '--commit', IDENTITY['commit'], '--max-cost-usd', '0.50',
                            '--max-elapsed-ms', '30000', *extra], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout)

    def assert_rejected(self, **kwargs):
        rc, report = self.run_gate(**kwargs)
        self.assertNotEqual(rc, 0)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(set(report['checks']), {'input', 'r2', 'preview', 'accounting'})
        return report

    def test_complete_synthetic_bundle_passes(self):
        rc, report = self.run_gate()
        self.assertEqual(rc, 0, report)
        self.assertEqual(report['cost_status'], 'KNOWN')

    def test_missing_cost_is_unknown_and_fails(self):
        del self.receipts['accounting']['actual_cost_usd']
        self.assertEqual(self.assert_rejected()['cost_status'], 'UNKNOWN')

    def test_unknown_ledger_entry_is_not_free(self):
        self.ledger['entries'][0]['actual_cost_usd'] = None
        self.assertEqual(self.assert_rejected()['cost_status'], 'UNKNOWN')

    def test_all_required_receipt_fields_fail_when_removed(self):
        self.flush()
        original = copy.deepcopy(self.receipts)
        for section, record in original.items():
            for key in record:
                with self.subTest(section=section, missing=key):
                    self.receipts = copy.deepcopy(original)
                    self.flush()
                    del self.receipts[section][key]
                    self.manifest[section] = self.blob(section + '.json', json.dumps(self.receipts[section]).encode())
                    (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
                    self.assert_rejected(flush=False)

    def test_all_required_manifest_fields_fail_when_removed(self):
        self.flush()
        original = copy.deepcopy(self.manifest)
        for key in original:
            with self.subTest(missing=key):
                self.manifest = copy.deepcopy(original)
                del self.manifest[key]
                (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
                self.assert_rejected(flush=False)

    def test_bad_amounts_and_types_fail(self):
        for value in [None, '', 'UNKNOWN', 'NaN', 'Infinity', '-1', True, 0.01, '1e999999']:
            with self.subTest(value=value):
                self.receipts['accounting']['actual_cost_usd'] = value
                self.assert_rejected()

    def test_budget_and_time_ceilings_are_enforced(self):
        self.assert_rejected(extra=['--max-cost-usd', '0.001'])
        self.assert_rejected(extra=['--max-elapsed-ms', '1000'])

    def test_identity_cannot_be_replayed_from_another_build_or_run(self):
        for section in self.receipts:
            for key in IDENTITY:
                with self.subTest(section=section, key=key):
                    old = self.receipts[section][key]
                    self.receipts[section][key] = 'wrong'
                    self.assert_rejected()
                    self.receipts[section][key] = old

    def test_corrupted_or_missing_artifact_fails(self):
        self.flush()
        (self.root / 'source.zip').write_bytes(b'corrupt')
        self.assert_rejected(flush=False)
        (self.root / 'source.zip').unlink()
        self.assert_rejected(flush=False)

    def test_traversal_and_symlinks_fail(self):
        self.receipts['preview']['screenshot']['path'] = '../outside.png'
        self.assert_rejected()
        self.receipts['preview']['screenshot']['path'] = 'link.png'
        (self.root / 'link.png').symlink_to(self.root / 'preview.png')
        self.assert_rejected()

    def test_wrong_preview_version_and_incomplete_acceptance_fail(self):
        self.receipts['preview']['version_id'] = 'v_other'
        self.assert_rejected()
        self.receipts['preview']['version_id'] = 'v_test'
        self.receipts['preview']['checks'] = []
        self.assert_rejected()

    def test_manual_steps_and_string_pass_are_rejected(self):
        self.manifest['manual_steps'] = 1
        self.assert_rejected()
        self.manifest['manual_steps'] = 0
        self.receipts['preview']['checks'][0]['passed'] = 'true'
        self.assert_rejected()

    def test_ledger_mismatch_duplicate_and_partial_coverage_fail(self):
        original = copy.deepcopy(self.ledger)
        self.ledger['entries'][0]['actual_cost_usd'] = '0.02'
        self.assert_rejected()
        self.ledger = copy.deepcopy(original)
        self.ledger['entries'].append(copy.deepcopy(self.ledger['entries'][0]))
        self.assert_rejected()
        self.ledger = copy.deepcopy(original)
        self.ledger['entries'].pop()
        self.assert_rejected()

    def test_missing_or_malformed_manifest_fails_without_traceback(self):
        for raw in ['null', '[]', '{}', '{', '{"schema_version":1,"schema_version":1}']:
            (self.root / 'manifest.json').write_text(raw)
            self.assert_rejected(flush=False)
        (self.root / 'manifest.json').unlink()
        self.assert_rejected(flush=False)

    def test_report_remains_unknown_if_accounting_passes_but_other_section_fails(self):
        self.receipts['input']['prompt'] = ''
        self.assertEqual(self.assert_rejected()['cost_status'], 'UNKNOWN')

    def test_missing_nested_fields_are_rejected(self):
        self.flush()
        original = copy.deepcopy(self.receipts)
        for section, path in [('input', ('requirements', 0, 'id')),
                              ('input', ('requirements', 0, 'text')),
                              ('r2', ('artifact', 'path')), ('r2', ('artifact', 'sha256')),
                              ('preview', ('checks', 0, 'acceptance_id')),
                              ('preview', ('checks', 0, 'passed')), ('preview', ('checks', 0, 'detail')),
                              ('preview', ('screenshot', 'path')), ('preview', ('screenshot', 'sha256')),
                              ('accounting', ('ledger', 'path')), ('accounting', ('ledger', 'sha256'))]:
            with self.subTest(section=section, path=path):
                self.receipts = copy.deepcopy(original)
                node = self.receipts[section]
                for part in path[:-1]:
                    node = node[part]
                del node[path[-1]]
                # Write receipts directly: flush() intentionally builds a fresh ledger reference.
                for name, value in self.receipts.items():
                    self.manifest[name] = self.blob(name + '.json', json.dumps(value).encode())
                (self.root / 'manifest.json').write_text(json.dumps(self.manifest))
                self.assert_rejected(flush=False)

    def test_missing_ledger_fields_and_wrong_shape_fail(self):
        original = copy.deepcopy(self.ledger)
        for key in original:
            with self.subTest(missing=key):
                self.ledger = copy.deepcopy(original)
                del self.ledger[key]
                self.assert_rejected()
        for key in original['entries'][0]:
            with self.subTest(missing_entry_field=key):
                self.ledger = copy.deepcopy(original)
                del self.ledger['entries'][0][key]
                self.assert_rejected()
        self.ledger = copy.deepcopy(original)
        self.ledger['complete'] = 'true'
        self.assert_rejected()

    def test_bad_timing_provider_coverage_and_screenshot_fail(self):
        for key, value in [('elapsed_ms', True), ('queue_ms', 0),
                           ('finished_monotonic_ns', 999), ('includes_repairs', 'true')]:
            with self.subTest(key=key):
                old = self.receipts['accounting'][key]
                self.receipts['accounting'][key] = value
                self.assert_rejected()
                self.receipts['accounting'][key] = old
        self.receipts['input']['provider_request_ids'].append('missing-ledger-request')
        self.assert_rejected()
        self.receipts['input']['provider_request_ids'].pop()
        self.receipts['preview']['screenshot'] = self.blob('not-image.bin', b'x' * 64)
        self.assert_rejected()


if __name__ == '__main__':
    unittest.main()

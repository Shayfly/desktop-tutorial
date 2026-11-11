"""T7b (Matt on #83): a "ready" build without result_version_id must fail paid-verify, not skip R2 and the preview.

The real paid-verify stage and the real CLI aggregate (main -> exit code); API/DB/state collaborators stubbed exactly as
in Matt's probe (sha256 93c90835...). No live R2 or E2E claim.
"""
import unittest
from unittest.mock import patch

from omni_prod import postdeploy_checks as p

STATE = {'token': 'synthetic-token', 'paid_project': 'p', 'paid_build': 'b'}


def run(version):
    build = {'status': 'ready', 'result_version_id': version,
             'evidence': {'browser_check': {'status': 'passed'}, 'product_review': [{'round': 1}]}}

    def api(method, path, *args):
        if '/events?' in path:
            return 200, {'events': [{'kind': 'info', 'message': 'synthetic'}] * 3}
        return 200, build
    with patch.object(p, 'load_state', return_value=STATE), patch.object(p, 'start_api'), \
            patch.object(p, 'save_state'), patch.object(p, 'store_results'), \
            patch.object(p, 'api', side_effect=api), \
            patch.object(p, 'reservation', return_value={'status': 'SETTLED'}), \
            patch.object(p, 'record_agent_graph'), patch.object(p, 'record_r2_artifact') as r2, \
            patch.object(p, 'preview_launch', return_value=(None, 'synthetic: preview not started')):
        p.RESULTS.clear()
        rc = p.main(['paid-verify'])
        return rc, r2.called, [r for r in p.RESULTS if not r['ok']]


class PaidVerifyWithoutAVersion(unittest.TestCase):
    def test_ready_without_a_version_exits_nonzero_and_names_why(self):
        rc, r2_called, failed = run(None)
        self.assertEqual(rc, 1)
        self.assertFalse(r2_called)
        self.assertEqual([f['check'] for f in failed], ['built version for R2 + preview'])
        self.assertIn('NOT verified', failed[0]['detail'])

    def test_control_with_a_version_reaches_r2_and_the_preview(self):
        rc, r2_called, failed = run('ver_1')
        self.assertTrue(r2_called)                                         # the R2 check is reached
        self.assertEqual([f['check'] for f in failed], ['preview of the built version'])   # stubbed preview -> fail
        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()

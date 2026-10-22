"""T7d (founder 2026-10-22): a preview that started but served a non-interface page is not reported as "did not start".

Same real smoke script and runner as tests/test_preview_verdict_names_condition.py (#89's frozen file, unchanged).
"""
import sys
import unittest

from tests.test_preview_verdict_names_condition import HEAD, repo, verdict
from omni_prod.preview_smoke import PreviewReadyExecutor
from tests.test_sandbox_callers_real_policy import Inner, StubRunner
from types import SimpleNamespace


class ThePreviewMessageSaysWhatHappened(unittest.TestCase):
    def test_a_started_app_with_a_non_interface_page_is_not_did_not_start(self):
        for page in (HEAD + '<button>הוסף</button></body></html>', HEAD + '<h1>OK</h1></body></html>'):
            report, text = verdict(page)
            self.assertFalse(report.passed)
            self.assertIn('the app started for preview, but its page is not the product', text)
            self.assertNotIn('did not start', text)

    def test_an_app_that_really_does_not_start_still_says_so(self):
        broken = dict(repo('<html></html>'))
        broken['app.py'] = 'raise SystemExit("boom")\n'
        ex = PreviewReadyExecutor(Inner(StubRunner()))
        report = ex.execute(repository=broken, spec=SimpleNamespace(acceptance=[], requirements=[]))
        self.assertFalse(report.passed)
        self.assertIn('the app did not start for preview', ' '.join(f.message for f in report.failures))


if __name__ == '__main__':
    unittest.main()

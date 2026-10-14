import pathlib
import unittest

from omni_prod.secret_scan import scan_text, scan_tree

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ".github/workflows/x.yml"
CI_URL = "      FAULT_DATABASE: postgresql://fault_test:ci-fixture-abcdef123@127.0.0.1:5432/db"
REAL_KEY = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2"


class CiServiceCredentialExemptionTests(unittest.TestCase):
    def test_loopback_ci_fixture_password_in_workflow_env_is_allowed(self):
        self.assertEqual(scan_text(CI_URL, path=WF), [])

    def test_same_line_outside_a_workflow_is_still_caught(self):
        for path in ("omni_prod/config.py", "docs/x.yml", ".github/other/x.yml", "x.yml"):
            kinds = [f.kind for f in scan_text(CI_URL, path=path)]
            self.assertEqual(kinds, ["url_password"], path)

    def test_non_loopback_host_or_non_ci_password_is_still_caught(self):
        remote = CI_URL.replace("127.0.0.1", "db.example.com")
        real = CI_URL.replace("ci-fixture-abcdef123", "Xk29sd81hf3Qpl")
        for line in (remote, real):
            self.assertEqual([f.kind for f in scan_text(line, path=WF)], ["url_password"], line)

    def test_url_inside_a_run_script_is_still_caught(self):
        line = "        psql postgresql://u:ci-fixture-abcdef123@127.0.0.1:5432/db -c 'select 1'"
        self.assertEqual([f.kind for f in scan_text(line, path=WF)], ["url_password"])

    def test_real_api_key_inside_a_workflow_is_still_caught(self):
        for line in (f"      OPENAI: {REAL_KEY}", f"      run: curl -H 'x: {REAL_KEY}'"):
            kinds = {f.kind for f in scan_text(line, path=WF)}
            self.assertIn("openai_style_key", kinds, line)

    def test_real_key_on_the_same_line_as_a_ci_url_is_still_caught(self):
        line = CI_URL + f"  # {REAL_KEY}"
        self.assertIn("openai_style_key", {f.kind for f in scan_text(line, path=WF)})

    def test_repository_tree_is_clean(self):
        self.assertEqual(scan_tree(ROOT), [])


if __name__ == "__main__":
    unittest.main()

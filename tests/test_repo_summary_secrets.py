"""Contract tests: secret filtering in _repo_summary.

Contract under test (omni_prod.investor_app):
  is_sensitive_path(path) -> bool
  _repo_summary(repo) -> sensitive files listed WITHOUT 'preview'; others WITH 'preview'.

These tests are written against the contract before the implementation exists.
They are expected to fail (red) until omni_prod implements it.
"""
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from omni_prod import investor_app


# Resolved per call, not at import: a missing contract symbol must fail only these
# tests, never abort pytest collection for the whole suite.
def is_sensitive_path(path):
    return investor_app.is_sensitive_path(path)


def _repo_summary(repo):
    return investor_app._repo_summary(repo)

ENV_SECRET = "OMNI_SECRET_KEY=sk-live-DO-NOT-LEAK-1234567890"
ENV_PROD_SECRET = "DATABASE_URL=postgres://admin:hunter2@prod-db.internal:5432/omni"
CONFIG_WITH_KEY = '{"name": "app", "api_key": "AKIA-FAKE-SECRET-ABCDEF"}'
CLEAN_SETTINGS = '{"theme": "dark", "locale": "he"}'
APP_PY = "from fastapi import FastAPI\napp = FastAPI()\n"

MOCK_REPO = {
    ".env": ENV_SECRET,
    ".env.production": ENV_PROD_SECRET,
    "config.json": CONFIG_WITH_KEY,
    "settings.json": CLEAN_SETTINGS,
    "app.py": APP_PY,
}
SENSITIVE = {".env", ".env.production", "config.json"}
REGULAR = {"settings.json", "app.py"}
SECRET_VALUES = (ENV_SECRET, ENV_PROD_SECRET, "sk-live-DO-NOT-LEAK", "hunter2", "AKIA-FAKE-SECRET")


class IsSensitivePathTests(unittest.TestCase):
    def test_env_files_are_sensitive(self):
        self.assertTrue(is_sensitive_path(".env"))
        self.assertTrue(is_sensitive_path(".env.production"))

    def test_nested_env_file_is_sensitive(self):
        self.assertTrue(is_sensitive_path("backend/.env"))

    def test_regular_files_are_not_sensitive(self):
        self.assertFalse(is_sensitive_path("app.py"))
        self.assertFalse(is_sensitive_path("settings.json"))


class RepoSummaryContractTests(unittest.TestCase):
    def setUp(self):
        self.summary = _repo_summary(dict(MOCK_REPO))
        self.by_path = {f["path"]: f for f in self.summary["files"]}

    def test_all_files_are_listed(self):
        self.assertEqual(set(self.by_path), set(MOCK_REPO))
        self.assertEqual(self.summary["file_count"], len(MOCK_REPO))

    def test_sensitive_files_have_no_preview(self):
        for path in SENSITIVE:
            self.assertNotIn("preview", self.by_path[path], path)

    def test_regular_files_keep_preview(self):
        for path in REGULAR:
            self.assertEqual(self.by_path[path].get("preview"), MOCK_REPO[path][:400], path)

    def test_no_secret_value_anywhere_in_summary(self):
        blob = repr(self.summary)
        for secret in SECRET_VALUES:
            self.assertNotIn(secret, blob)


class RepoSummaryRouteTests(unittest.TestCase):
    """Same contract through a real public route (/api/source/mobile/android)."""

    def test_route_returns_200_and_filters_secrets(self):
        client = TestClient(investor_app.app)
        with patch.dict(os.environ, {"OMNI_ENV": "development"}), \
                patch.object(investor_app, "android_project", return_value=dict(MOCK_REPO)):
            r = client.get("/api/source/mobile/android")
        self.assertEqual(r.status_code, 200, r.text[:300])
        files = {f["path"]: f for f in r.json()["repository"]["files"]}
        for path in SENSITIVE:
            self.assertNotIn("preview", files[path], path)
        for path in REGULAR:
            self.assertEqual(files[path].get("preview"), MOCK_REPO[path][:400], path)
        for secret in SECRET_VALUES:
            self.assertNotIn(secret, r.text)


if __name__ == "__main__":
    unittest.main()

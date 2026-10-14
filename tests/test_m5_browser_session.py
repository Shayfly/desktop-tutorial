"""M5 remediation: browser sessions use an HttpOnly cookie; Bearer stays for API clients."""
from __future__ import annotations

import unittest
from pathlib import Path

from omni_prod.browser_session import (
    COOKIE_NAME, SessionTokenError, cookie_settings, extract_session_token, browser_session_readiness)

ASSETS = Path(__file__).resolve().parents[1] / "omni_prod" / "assets"


class _Req:
    def __init__(self, method="GET", headers=None, cookies=None, host="app.148ai.example", scheme="https"):
        self.method = method
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.cookies = cookies or {}
        self.url = type("U", (), {"hostname": host, "scheme": scheme, "netloc": host})()


class ExtractionTests(unittest.TestCase):
    def test_bearer_header_still_works_and_wins(self):
        req = _Req("POST", headers={"Authorization": "Bearer api-token"}, cookies={COOKIE_NAME: "cookie-token"})
        self.assertEqual(extract_session_token(req, allowed_origins=()), ("api-token", "bearer"))

    def test_cookie_authenticates_safe_requests(self):
        self.assertEqual(extract_session_token(_Req("GET", cookies={COOKIE_NAME: "c"}), allowed_origins=()),
                         ("c", "cookie"))

    def test_cookie_write_requires_same_origin(self):
        ok = _Req("POST", headers={"Origin": "https://app.148ai.example"}, cookies={COOKIE_NAME: "c"})
        self.assertEqual(extract_session_token(ok, allowed_origins=())[0], "c")
        fetch_site = _Req("DELETE", headers={"Sec-Fetch-Site": "same-origin"}, cookies={COOKIE_NAME: "c"})
        self.assertEqual(extract_session_token(fetch_site, allowed_origins=())[0], "c")
        allowed = _Req("PATCH", headers={"Origin": "https://studio.148ai.example"}, cookies={COOKIE_NAME: "c"})
        self.assertEqual(extract_session_token(allowed, allowed_origins=("https://studio.148ai.example",))[0], "c")
        for headers in ({"Origin": "https://evil.example"}, {}, {"Sec-Fetch-Site": "cross-site"},
                        {"Origin": "null"}):
            with self.subTest(headers=headers), self.assertRaises(SessionTokenError) as ctx:
                extract_session_token(_Req("POST", headers=headers, cookies={COOKIE_NAME: "c"}), allowed_origins=())
            self.assertEqual(ctx.exception.status_code, 403)

    def test_missing_credentials_is_401(self):
        with self.assertRaises(SessionTokenError) as ctx:
            extract_session_token(_Req("GET"), allowed_origins=())
        self.assertEqual(ctx.exception.status_code, 401)
        with self.assertRaises(SessionTokenError):
            extract_session_token(_Req("GET", headers={"Authorization": "Basic abc"}), allowed_origins=())


class CookieSettingsTests(unittest.TestCase):
    def test_production_cookie_is_httponly_secure_strict(self):
        s = cookie_settings(production=True, env={})
        self.assertEqual((s["httponly"], s["secure"], s["samesite"], s["path"]), (True, True, "strict", "/"))
        self.assertEqual(s["key"], COOKIE_NAME)
        self.assertNotIn("max_age", s)  # browser-session cookie; token expiry stays server-side

    def test_secure_can_only_be_disabled_outside_production(self):
        self.assertFalse(cookie_settings(production=False, env={"OMNI_SESSION_COOKIE_SECURE": "0"})["secure"])
        self.assertTrue(cookie_settings(production=True, env={"OMNI_SESSION_COOKIE_SECURE": "0"})["secure"])
        self.assertTrue(cookie_settings(production=False, env={})["secure"])

    def test_readiness_never_calls_insecure_cookie_hardened(self):
        self.assertEqual(browser_session_readiness(production=True, env={})["status"], "PARTIAL")
        dev = browser_session_readiness(production=False, env={"OMNI_SESSION_COOKIE_SECURE": "0"})
        self.assertEqual(dev["status"], "BLOCKED")
        self.assertIn("Secure", dev["reason"])


class WorkspaceStorageTests(unittest.TestCase):
    def test_workspace_no_longer_persists_the_token(self):
        js = (ASSETS / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("localStorage.setItem('148ai_token'", js)
        self.assertIn("localStorage.removeItem('148ai_token')", js)  # migrates old sessions away
        self.assertIn("credentials: 'same-origin'", js)
        self.assertNotIn("Authorization", js)


if __name__ == "__main__":
    unittest.main()

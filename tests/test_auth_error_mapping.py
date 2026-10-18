import json
import re
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from omni_prod import investor_app

APP_JS = Path(__file__).resolve().parents[1] / "omni_prod" / "assets" / "app.js"
PASSWORD = "correct-horse-battery"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:10]}@example.com"


def _has_session_cookie(resp) -> bool:
    return "148ai_session" in resp.headers.get("set-cookie", "")


class AuthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(investor_app.app)

    def _register(self, email, password=PASSWORD):
        return self.client.post("/api/v28/auth/register", json={"email": email, "password": password})

    def test_register_existing_email_with_correct_password_returns_session(self):
        email = _email()
        self.assertEqual(self._register(email).status_code, 200)
        self.client.cookies.clear()
        r = self._register(email)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIs(r.json().get("existing_account"), True)
        self.assertTrue(_has_session_cookie(r))

    def test_register_existing_email_with_different_password_is_409(self):
        email = _email()
        self.assertEqual(self._register(email).status_code, 200)
        r = self._register(email, "another-password-1")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["detail"], "account already exists")

    def test_login_wrong_password_is_401_invalid_credentials(self):
        email = _email()
        self._register(email)
        r = self.client.post("/api/v28/auth/login", json={"email": email, "password": "wrong-password-1"})
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "invalid credentials")

    def test_login_ok_sets_session_cookie(self):
        email = _email()
        self._register(email)
        self.client.cookies.clear()
        r = self.client.post("/api/v28/auth/login", json={"email": email, "password": PASSWORD})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(_has_session_cookie(r))


@unittest.skipUnless(shutil.which("node"), "node is required to execute app.js explain()")
class ExplainTests(unittest.TestCase):
    def _explain(self, signed_in, status, message):
        src = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"^function explain\(err\) \{.*?^\}", src, re.S | re.M)
        self.assertIsNotNone(m)
        harness = f"""
class ApiError extends Error {{ constructor(status, detail) {{ super(detail); this.status = status; this.detail = detail; }} }}
const S = {{ signedIn: {json.dumps(signed_in)}, lang: 'he' }};
const T = {{ err401: 'SESSION_EXPIRED', errBadCreds: 'BAD_CREDS', errAccountExists: 'EXISTS', err409: 'CONFLICT' }};
const t = k => T[k];
{m.group(0)}
process.stdout.write(explain(new ApiError({status}, {json.dumps(message)})));
"""
        out = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def test_401_when_signed_in_still_says_session_expired(self):
        self.assertEqual(self._explain(True, 401, "authentication required"), "SESSION_EXPIRED")

    def test_401_on_sign_in_screen_says_bad_credentials(self):
        self.assertEqual(self._explain(False, 401, "invalid credentials"), "BAD_CREDS")

    def test_account_exists_is_translated(self):
        self.assertEqual(self._explain(False, 409, "account already exists"), "EXISTS")
        self.assertEqual(self._explain(False, 400, "account already exists"), "EXISTS")


if __name__ == "__main__":
    unittest.main()

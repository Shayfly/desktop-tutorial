"""Real loopback HTTP contract, safety and failure-injection tests (no live 148AI)."""
from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tools.qa_postdeploy import CheckStatus, ErrorClass, ExecutionMode, RunConfig, Verdict, run_postdeploy_checks
from tools.qa_postdeploy.cli import main
from tools.qa_postdeploy.http_client import SafeHttpClient, validated_origin


class Server(BaseHTTPRequestHandler):
    token_seen = None

    def log_message(self, *_):
        pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/v28/pricing":
            return self.send_json(200, {"plans": []})
        if path == "/api/v28/me":
            if self.headers.get("Authorization") != "Bearer valid":
                return self.send_json(401, {"detail": "Invalid session"})
            return self.send_json(200, {"id": "secret-account-id", "email": "private@test.example", "created_at": "today", "subscription": {"plan": "free"}})
        if path == "/api/v28/projects":
            return self.send_json(200, {"projects": [{"id": "good"}]})
        if path.endswith("/conversation"):
            key = path.split("/")[-2]
            if key == "migration":
                return self.send_json(503, {"detail": {"error": "conversation_not_ready", "missing_migration": "036_intelligence_plane"}})
            if key == "legacy_migration":
                return self.send_json(503, {"error_code": "conversation_not_ready", "missing_migration": "036_intelligence_plane"})
            if key == "database":
                return self.send_json(503, {"detail": {"error": "durable_backend_required"}})
            if key == "broken":
                return self.send_json(500, {"detail": "server fault"})
            if key == "unavailable":
                return self.send_json(503, {"detail": "service unavailable"})
            if key == "invalid":
                return self.send_json(200, {"messages": {}})
            if key == "not_json":
                return self.send_raw(200, b"definitely not json")
            if key == "denied":
                return self.send_json(403, {"detail": "no access"})
            if key == "redirect":
                self.send_response(302)
                self.send_header("Location", "https://not-allowed.example/")
                self.end_headers()
                return
            if key == "redirect_same":
                self.send_response(302)
                self.send_header("Location", "/api/v28/pricing")
                self.end_headers()
                return
            if key == "large":
                return self.send_raw(200, b"{" + b" " * 2048 + b"}")
            if key == "slow":
                time.sleep(0.15)
                return self.send_json(200, {"messages": [], "discovery": None, "plan": None, "plan_id": None, "interpreter": "deterministic"})
            return self.send_json(200, {"messages": [], "discovery": None, "plan": None, "plan_id": None, "interpreter": "deterministic"})
        if path.endswith("/memory"):
            return self.send_json(200, {"summary": {}})
        if path.endswith("/discovery"):
            if "/optional_fail/" in path:
                return self.send_json(500, {"detail": "temporary"})
            return self.send_json(200, {"revision": 1})
        return self.send_json(404, {"detail": "unknown"})

    def send_raw(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, code, data):
        return self.send_raw(code, json.dumps(data).encode())


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Server)
        cls.port = cls.server.server_address[1]
        cls.url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=2)
        cls.server.server_close()

    def config(self, project="good", token="valid", **kwargs):
        params = {"base_url": self.url, "target_environment": "test", "project_id": project,
                  "bearer_token": token}
        params.update(kwargs)
        return RunConfig(**params)

    @staticmethod
    def check(result, name="proj_conversation"):
        return next(c for c in result.checks if c.check_id == name)

    def test_01_happy_path(self):
        r = run_postdeploy_checks(self.config())
        self.assertEqual(r.verdict, Verdict.VERIFIED)
        self.assertEqual([c.status for c in r.checks], [CheckStatus.PASS] * 6)

    def test_02_uses_real_loopback_requests(self):
        c = SafeHttpClient(self.url, token="valid", allowed_hosts=(), timeout=1, max_bytes=3000)
        r = c.get("/api/v28/me", require_auth=True)
        self.assertEqual((r.code, r.error), (200, ErrorClass.NONE))

    def test_03_no_token_blocks(self):
        r = run_postdeploy_checks(self.config(token=None))
        self.assertEqual(r.verdict, Verdict.BLOCKED)
        self.assertEqual(self.check(r, "auth_me").status, CheckStatus.NOT_RUN)

    def test_04_invalid_token_is_rejected(self):
        r = run_postdeploy_checks(self.config(token="wrong"))
        self.assertEqual(self.check(r, "auth_me").classification, ErrorClass.AUTHENTICATION_INVALID)
        self.assertEqual(r.verdict, Verdict.FAILED)

    def test_05_missing_project_blocks(self):
        r = run_postdeploy_checks(self.config(project=None))
        self.assertEqual(self.check(r).status, CheckStatus.NOT_RUN)
        self.assertEqual(r.verdict, Verdict.BLOCKED)

    def test_06_invalid_project_rejected(self):
        with self.assertRaises(ValueError):
            run_postdeploy_checks(self.config(project="../admin?token=a"))

    def test_07_migration_036_nested_fastapi_error(self):
        r = run_postdeploy_checks(self.config(project="migration"))
        self.assertEqual(self.check(r).classification, ErrorClass.MIGRATION_NOT_APPLIED)
        self.assertEqual(self.check(r).status, CheckStatus.BLOCKED)
        self.assertEqual(r.verdict, Verdict.BLOCKED)

    def test_08_old_style_migration_error(self):
        r = run_postdeploy_checks(self.config(project="legacy_migration"))
        self.assertEqual(self.check(r).classification, ErrorClass.MIGRATION_NOT_APPLIED)

    def test_09_database_unavailable(self):
        r = run_postdeploy_checks(self.config(project="database"))
        self.assertEqual(self.check(r).classification, ErrorClass.DATABASE_NOT_READY)
        self.assertEqual(r.verdict, Verdict.BLOCKED)

    def test_10_http_500_blocks_release(self):
        r = run_postdeploy_checks(self.config(project="broken"))
        self.assertEqual(self.check(r).classification, ErrorClass.HTTP_500)
        self.assertEqual(r.verdict, Verdict.FAILED)

    def test_11_http_503_unknown_fails(self):
        r = run_postdeploy_checks(self.config(project="unavailable"))
        self.assertEqual(self.check(r).classification, ErrorClass.HTTP_503)
        self.assertEqual(r.verdict, Verdict.FAILED)

    def test_12_app_or_vercel_403_is_ambiguous(self):
        r = run_postdeploy_checks(self.config(project="denied"))
        self.assertEqual(self.check(r).classification, ErrorClass.HTTP_403)
        self.assertEqual(r.verdict, Verdict.BLOCKED)

    def test_13_invalid_contract(self):
        r = run_postdeploy_checks(self.config(project="invalid"))
        self.assertEqual(self.check(r).classification, ErrorClass.INVALID_RESPONSE_CONTRACT)

    def test_14_non_json(self):
        r = run_postdeploy_checks(self.config(project="not_json"))
        self.assertEqual(self.check(r).classification, ErrorClass.INVALID_JSON)

    def test_15_large_response_limit(self):
        r = run_postdeploy_checks(self.config(project="large", max_response_bytes=1000))
        self.assertEqual(self.check(r).classification, ErrorClass.RESPONSE_TOO_LARGE)

    def test_16_timeout(self):
        r = run_postdeploy_checks(self.config(project="slow", timeout_seconds=0.03))
        self.assertEqual(self.check(r).classification, ErrorClass.TIMEOUT)

    def test_17_connection_failure(self):
        r = run_postdeploy_checks(self.config(base_url="http://127.0.0.1:1"))
        self.assertEqual(self.check(r).classification, ErrorClass.HTTP_CONNECTION_FAILURE)

    def test_18_cross_origin_redirect_blocked(self):
        r = run_postdeploy_checks(self.config(project="redirect"))
        self.assertEqual(self.check(r).classification, ErrorClass.UNEXPECTED_REDIRECT)

    def test_19_same_origin_redirect_blocked(self):
        r = run_postdeploy_checks(self.config(project="redirect_same"))
        self.assertEqual(self.check(r).classification, ErrorClass.UNEXPECTED_REDIRECT)

    def test_20_http_remote_forbidden(self):
        with self.assertRaises(ValueError):
            validated_origin("http://public.example.com", ("public.example.com",))

    def test_21_remote_https_allowlist_required(self):
        with self.assertRaises(ValueError):
            validated_origin("https://preview.example.com")
        self.assertEqual(validated_origin("https://preview.example.com", ("preview.example.com",)), "https://preview.example.com")

    def test_22_embedded_credentials_forbidden(self):
        with self.assertRaises(ValueError):
            validated_origin("https://user:password@preview.example.com", ("preview.example.com",))

    def test_23_url_path_query_fragment_forbidden(self):
        for url in (f"{self.url}/hidden", f"{self.url}?token=x", f"{self.url}#fragment"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validated_origin(url)

    def test_24_private_ip_forbidden_even_https(self):
        with self.assertRaises(ValueError):
            validated_origin("https://192.168.0.1", ("192.168.0.1",))

    def test_25_excessive_resource_limits_rejected(self):
        for kw in ({"timeout_seconds": 61}, {"max_response_bytes": 10**9}, {"timeout_seconds": -1}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                run_postdeploy_checks(self.config(**kw))

    def test_26_canary_is_not_faked(self):
        with self.assertRaisesRegex(ValueError, "CANARY"):
            run_postdeploy_checks(self.config(execution_mode=ExecutionMode.CANARY))

    def test_27_commit_expected_without_attestation_blocks(self):
        r = run_postdeploy_checks(self.config(expected_commit_sha="a" * 40))
        self.assertEqual(r.verdict, Verdict.BLOCKED)
        self.assertIsNone(r.observed_commit_sha)
        self.assertEqual(self.check(r, "deployment_commit").classification, ErrorClass.DEPLOYMENT_SHA_UNVERIFIED)

    def test_28_commit_matches_attestation(self):
        r = run_postdeploy_checks(self.config(expected_commit_sha="a" * 40, trusted_observed_commit_sha="a" * 40))
        self.assertEqual(r.verdict, Verdict.VERIFIED)
        self.assertEqual(self.check(r, "deployment_commit").status, CheckStatus.PASS)

    def test_29_commit_mismatch_blocks(self):
        r = run_postdeploy_checks(self.config(expected_commit_sha="a" * 40, trusted_observed_commit_sha="b" * 40))
        self.assertEqual(r.verdict, Verdict.BLOCKED)

    def test_30_invalid_commit_rejected(self):
        with self.assertRaises(ValueError):
            run_postdeploy_checks(self.config(expected_commit_sha="short"))

    def test_31_optional_failure_does_not_override_mandatory_pass(self):
        r = run_postdeploy_checks(self.config(project="optional_fail"))
        self.assertEqual(self.check(r, "proj_discovery").status, CheckStatus.FAIL)
        self.assertEqual(r.verdict, Verdict.VERIFIED)

    def test_32_required_fail_overrides_blocked(self):
        r = run_postdeploy_checks(self.config(project="broken", expected_commit_sha="a" * 40))
        self.assertEqual(r.verdict, Verdict.FAILED)

    def test_33_result_contains_no_user_data_or_token(self):
        r = run_postdeploy_checks(self.config())
        serialized = json.dumps(r.to_dict())
        for secret in ("valid", "private@test.example", "secret-account-id"):
            self.assertNotIn(secret, serialized)

    def test_34_cli_good_and_json_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "evidence.json")
            with patch.dict(os.environ, {"QA_BEARER_TOKEN": "valid"}):
                out = io.StringIO()
                with redirect_stdout(out):
                    code = main(["--base-url", self.url, "--environment", "test", "--project-id", "good", "--json-output", path])
            self.assertEqual(code, 0)
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["verdict"], "VERIFIED")
            self.assertNotIn("valid", out.getvalue())

    def test_35_cli_missing_auth_returns_blocked(self):
        with patch.dict(os.environ, {"QA_BEARER_TOKEN": ""}):
            with redirect_stdout(io.StringIO()):
                code = main(["--base-url", self.url, "--environment", "test", "--project-id", "good"])
        self.assertEqual(code, 2)

    def test_36_cli_invalid_config_returns_3(self):
        with redirect_stderr(io.StringIO()):
            code = main(["--base-url", "http://not-safe.example", "--environment", "test"])
        self.assertEqual(code, 3)

    def test_37_cli_canary_refused(self):
        with redirect_stderr(io.StringIO()):
            code = main(["--base-url", self.url, "--environment", "test", "--mode", "CANARY"])
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)

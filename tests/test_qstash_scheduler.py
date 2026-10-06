"""QStash protocol tests; fake transport, no billable provider requests."""
import base64
from dataclasses import replace
import hashlib
import hmac
import io
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

from omni_prod.infrastructure_contracts import BindingStatus, InfrastructureKind
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import ManagedWebSaaSConfig, ManagedWebSaaSProvisioner
from omni_prod.providers.qstash_scheduler import QStashClient, QStashError, QStashReceiver

try:
    from tests.test_m5_managed_web_saas_profile import FULL_ENV, FakeSecretStore, _resolver
except ModuleNotFoundError:
    from test_m5_managed_web_saas_profile import FULL_ENV, FakeSecretStore, _resolver

URL = "https://qstash-eu-central-1.upstash.io"
TARGET = "https://preview.example.com/api/scheduler"
TOKEN = "test-parent-token"


class Response:
    def __init__(self, value=None, raw=None, status=200):
        self.raw = json.dumps(value).encode() if raw is None else raw
        self.status = status
    def read(self, size=-1):
        return self.raw[:size] if size >= 0 else self.raw
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Transport:
    def __init__(self, response=None):
        self.response = response or Response([])
        self.requests = []
    def __call__(self, req, *, timeout):
        self.requests.append(req)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def signed(*, key="current-key", claims=None, body=b'{"probe":true}', header=None):
    values = {"iss": "Upstash", "sub": TARGET, "exp": 1300, "nbf": 900, "iat": 900,
              "jti": "delivery-a", "body": base64.urlsafe_b64encode(hashlib.sha256(body).digest()).decode()}
    if claims:
        values.update(claims)
    def enc(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()
    message = enc(header or {"alg": "HS256", "typ": "JWT"}) + "." + enc(values)
    sig = base64.urlsafe_b64encode(hmac.new(key.encode(), message.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
    return message + "." + sig


class ClientTests(unittest.TestCase):
    def client(self, transport):
        return QStashClient(base_url=URL, token=TOKEN, allowed_destinations=[TARGET], opener=transport)

    def test_create_uses_deterministic_id_bounded_retries_and_redaction(self):
        t = Transport(Response({"scheduleId": "app-preview-job"}))
        self.assertEqual(self.client(t).create(destination=TARGET, cron="*/5 * * * *",
                         schedule_id="app-preview-job", payload={"job": "probe"}), "app-preview-job")
        req = t.requests[0]
        headers = {k.lower(): v for k,v in req.headers.items()}
        self.assertEqual(req.method, "POST")
        self.assertEqual(headers["authorization"], "Bearer " + TOKEN)
        self.assertEqual(headers["upstash-schedule-id"], "app-preview-job")
        self.assertEqual(headers["upstash-retries"], "2")
        self.assertEqual(headers["upstash-redact-fields"], "body,headers")
        self.assertTrue(req.full_url.startswith(URL + "/v2/schedules/https%3A%2F%2F"))
        self.assertEqual(json.loads(req.data), {"job": "probe"})

    def test_publish_uses_deduplication_and_returns_only_message_id(self):
        t = Transport(Response({"messageId": "m-1"}))
        self.assertEqual(self.client(t).publish(destination=TARGET, payload={"probe": True},
                                               deduplication_id="probe-1"), "m-1")
        self.assertEqual({k.lower():v for k,v in t.requests[0].headers.items()}["upstash-deduplication-id"], "probe-1")

    def test_api_access_requires_a_list_not_just_http_200(self):
        self.assertTrue(self.client(Transport(Response([]))).check_access())
        self.assertFalse(self.client(Transport(Response({"error": "unexpected"}))).check_access())

    def test_get_and_cancel_do_not_accept_path_injection(self):
        t = Transport(Response({"scheduleId": "safe"}))
        client = self.client(t)
        self.assertEqual(client.get("safe")["scheduleId"], "safe")
        client.cancel("safe")
        self.assertEqual([r.method for r in t.requests], ["GET", "DELETE"])
        for sid in ("../all", "x?other=y", "", "a/b"):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                client.cancel(sid)

    def test_404_get_and_cancel_are_idempotent(self):
        for method in ("get", "cancel"):
            t = Transport(HTTPError(URL, 404, "not found " + TOKEN, {}, io.BytesIO(b"secret")))
            self.assertIsNone(getattr(self.client(t), method)("missing"))

    def test_external_unallowlisted_destinations_fail_before_transport(self):
        t = Transport()
        client = self.client(t)
        for destination in ("https://attacker.example/", "http://preview.example.com/api/scheduler", TARGET + "?x=1"):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                client.publish(destination=destination, payload={}, deduplication_id="p")
        self.assertEqual(t.requests, [])

    def test_credentials_cannot_be_redirected_to_another_origin(self):
        for origin in ("http://qstash.upstash.io", URL + "/api", URL + "?x=1", "https://qstash.upstash.io.evil.example"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                QStashClient(base_url=origin, token=TOKEN)
        from omni_prod.providers.qstash_scheduler import _NoRedirect
        self.assertIsNone(_NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))

    def test_errors_reject_redirects_and_do_not_expose_provider_text(self):
        for status in (302, 401, 429, 500):
            t = Transport(HTTPError(URL, status, "token=" + TOKEN, {}, io.BytesIO(TOKEN.encode())))
            with self.subTest(status=status), self.assertRaises(QStashError) as exc:
                self.client(t).check_access()
            self.assertNotIn(TOKEN, str(exc.exception))
            self.assertNotIn(TARGET, str(exc.exception))

    def test_response_schema_size_and_payload_limits(self):
        for response in (Response(raw=b"invalid"), Response(raw=b"x" * 262145), Response({"scheduleId": "wrong"})):
            with self.subTest(response=response), self.assertRaises(QStashError):
                self.client(Transport(response)).create(destination=TARGET, cron="* * * * *", schedule_id="wanted", payload={})
        t = Transport()
        with self.assertRaises(ValueError):
            self.client(t).publish(destination=TARGET, payload={"large": "x"*65536}, deduplication_id="p")
        self.assertEqual(t.requests, [])

    def test_invalid_cron_and_repr_do_not_send_or_expose_secrets(self):
        t = Transport()
        for cron in ("* * *", "* * * * *\r\nAuthorization: x", "CRON_TZ=UTC * * * * *"):
            with self.subTest(cron=cron), self.assertRaises(ValueError):
                self.client(t).create(destination=TARGET, cron=cron, schedule_id="s", payload={})
        self.assertNotIn(TOKEN, repr(self.client(t)))


class ReceiverTests(unittest.TestCase):
    def receiver(self):
        return QStashReceiver(current_key="current-key", next_key="next-key", clock=lambda:1000)

    def test_current_and_next_signatures_and_unpadded_body_hash(self):
        for key in ("current-key", "next-key"):
            with self.subTest(key=key):
                result = self.receiver().verify(signature=signed(key=key), body=b'{"probe":true}',
                                                destination=TARGET, claim_once=lambda jti, exp: True)
                self.assertEqual(result, {"delivery_id":"delivery-a", "expires_at":1300})

    def test_body_destination_and_signing_key_are_bound(self):
        for changes in ({"body": b"tampered"}, {"destination": "https://other.example"},
                        {"signature": signed(key="wrong")}):
            kwargs = dict(signature=signed(), body=b'{"probe":true}', destination=TARGET,
                          claim_once=lambda jti, exp: self.fail("invalid signature must not claim"))
            kwargs.update(changes)
            with self.subTest(changes=changes), self.assertRaises(QStashError):
                self.receiver().verify(**kwargs)

    def test_algorithm_and_time_claims_fail_closed(self):
        tokens = [signed(header={"alg":"none","typ":"JWT"})]
        tokens += [signed(claims=claims) for claims in (
            {"exp":1000}, {"exp":True}, {"exp":"1300"}, {"nbf":1001},
            {"iat":1001}, {"iss":"Other"}, {"jti":""}, {"body":"bad"})]
        for token in tokens:
            with self.subTest(token=token), self.assertRaises(QStashError):
                self.receiver().verify(signature=token, body=b'{"probe":true}', destination=TARGET,
                                       claim_once=lambda *args:self.fail("must not claim"))

    def test_replay_is_atomic_and_storage_failure_is_closed(self):
        seen = set()
        def claim(jti, expiry):
            if jti in seen:
                return False
            seen.add(jti)
            return True
        kwargs = dict(signature=signed(), body=b'{"probe":true}', destination=TARGET, claim_once=claim)
        self.receiver().verify(**kwargs)
        with self.assertRaisesRegex(QStashError, "duplicate"):
            self.receiver().verify(**kwargs)
        def unavailable(*args):
            raise RuntimeError("secret-dsn")
        kwargs["claim_once"] = unavailable
        with self.assertRaisesRegex(QStashError, "protection unavailable") as exc:
            self.receiver().verify(**kwargs)
        self.assertNotIn("secret-dsn", str(exc.exception))

    def test_malformed_token_and_missing_replay_store_rejected(self):
        for signature in ("bad", "a.b.c", "", "."*4):
            with self.subTest(signature=signature), self.assertRaises(QStashError):
                self.receiver().verify(signature=signature, body=b"", destination=TARGET, claim_once=None)
        self.assertNotIn("current-key", repr(self.receiver()))


class WiringTests(unittest.TestCase):
    def env(self):
        return dict(FULL_ENV, QSTASH_URL=URL, QSTASH_TOKEN=TOKEN,
                    QSTASH_CURRENT_SIGNING_KEY="current-key", QSTASH_NEXT_SIGNING_KEY="next-key",
                    OMNI_GENAPP_SCHEDULER_URL="",
                    OMNI_GENAPP_SCHEDULER_TOKEN_REF="")

    def test_standard_saved_variables_select_qstash_with_partial_readiness(self):
        env = self.env()
        cfg = ManagedWebSaaSConfig.from_env(env)
        self.assertEqual((cfg.scheduler_provider, cfg.scheduler_url, cfg.scheduler_token_ref),
                         ("qstash", URL, "env:QSTASH_TOKEN"))
        self.assertEqual(cfg.config_status(InfrastructureKind.SCHEDULED_HTTP,env)[0], "PARTIAL")
        self.assertEqual(replace(cfg, qstash_signing_keys_present=False).config_status(
            InfrastructureKind.SCHEDULED_HTTP,env)[0], "NOT_CONFIGURED")
        missing_token = dict(env, QSTASH_TOKEN="")
        self.assertEqual(ManagedWebSaaSConfig.from_env(missing_token).config_status(
            InfrastructureKind.SCHEDULED_HTTP, missing_token)[0], "NOT_CONFIGURED")

    def test_api_success_cannot_create_a_live_binding_or_expose_parent_keys(self):
        env = self.env()
        p = ManagedWebSaaSProvisioner(config=ManagedWebSaaSConfig.from_env(env),
                                     secret_store=FakeSecretStore(), resolve_reference=_resolver(env), control_plane_env=env)
        contract = ProductArchitect().compile("Web app with scheduled reminders.", project_id="p",contract_version=1)
        req = next(r for r in contract.infrastructure if r.kind=="scheduled_http")
        with patch("omni_prod.providers.qstash_scheduler.QStashClient.check_access", return_value=True):
            binding = p.provision(req, tenant_id="u", project_id="p", environment="preview", idempotency_key="k"*64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)
        self.assertTrue(binding.evidence["api_access_verified"])
        self.assertFalse(binding.evidence["delivery_verified"])
        self.assertNotIn(TOKEN, json.dumps(binding.to_record()))
        self.assertEqual(binding.secret_references, {})

    def test_legacy_scheduler_configuration_preserved(self):
        cfg = ManagedWebSaaSConfig.from_env(FULL_ENV)
        self.assertEqual(cfg.scheduler_provider,"generic_http")
        self.assertEqual(cfg.scheduler_url,FULL_ENV["OMNI_GENAPP_SCHEDULER_URL"])


if __name__ == "__main__":
    unittest.main()

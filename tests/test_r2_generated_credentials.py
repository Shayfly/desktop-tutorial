"""Protocol and wiring tests; these do not claim live Cloudflare verification."""
import base64
from dataclasses import replace
import hashlib
import hmac
import json
import unittest
from unittest.mock import patch

from omni_prod.infrastructure_contracts import BindingStatus, InfrastructureKind
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import (
    ManagedWebSaaSConfig, ManagedWebSaaSProvisioner, scoped_object_policy)
from omni_prod.providers.r2_credentials import R2CredentialIssuer, r2_account_id

try:
    from tests.test_m5_managed_web_saas_profile import FULL_ENV, FakeSecretStore, _resolver
except ModuleNotFoundError:
    from test_m5_managed_web_saas_profile import FULL_ENV, FakeSecretStore, _resolver

ACCOUNT = "a" * 32
ENDPOINT = f"https://{ACCOUNT}.r2.cloudflarestorage.com"
POLICY = scoped_object_policy("genapp-objects", "generated-apps/abc/preview/")


def decode(creds):
    raw = base64.b64decode(creds["session_token"]).decode()
    assert raw.startswith("jwt/")
    jwt = raw[4:]
    header, payload, sig = jwt.split(".")
    return jwt, json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))), sig


class R2CredentialsTests(unittest.TestCase):
    def issue(self, **changes):
        kwargs = dict(operator_access_key="parent-access", operator_secret_key="parent-secret",
                      role_arn="", policy=POLICY, session_name="app", ttl_seconds=900)
        kwargs.update(changes)
        return R2CredentialIssuer(endpoint=ENDPOINT, clock=lambda: 1800000000).issue(**kwargs)

    def test_cloudflare_protocol_signature_derivation_and_expiry(self):
        creds = self.issue()
        jwt, claims, sig = decode(creds)
        expected = hmac.new(b"parent-secret", jwt.rsplit(".", 1)[0].encode(), hashlib.sha256).digest()
        self.assertEqual(base64.urlsafe_b64decode(sig + "=" * (-len(sig) % 4)), expected)
        self.assertEqual(creds["secret_access_key"], hashlib.sha256(jwt.encode()).hexdigest())
        self.assertEqual(creds["access_key_id"], "parent-access")
        self.assertEqual((claims["sub"], claims["iss"], claims["aud"]),
                         (ACCOUNT, "parent-access", ENDPOINT[8:]))
        self.assertEqual((claims["iat"], claims["exp"]), (1800000000, 1800000900))
        self.assertNotEqual(creds["secret_access_key"], "parent-secret")
        self.assertNotIn("parent-secret", json.dumps(creds))
        self.assertTrue(creds["expires_at"].endswith("Z"))

    def test_scope_is_one_app_environment_and_only_crud_list(self):
        _, claims, _ = decode(self.issue())
        self.assertEqual(claims["bucket"], "genapp-objects")
        self.assertEqual(claims["paths"], {"prefixPaths": ["generated-apps/abc/preview/"], "objectPaths": []})
        self.assertEqual(set(claims["actions"]),
                         {"GetObject", "PutObject", "DeleteObject", "ListObjectsV1", "ListObjectsV2"})
        self.assertNotIn("admin", claims["scope"])

    def test_reissued_credentials_differ_even_in_same_second(self):
        self.assertNotEqual(self.issue()["session_token"], self.issue()["session_token"])

    def test_invalid_ttls_fail_closed(self):
        for ttl in (0, -1, 3601, True, "900", 1.5):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                self.issue(ttl_seconds=ttl)

    def test_unknown_or_broader_iam_policies_are_rejected(self):
        variants = []
        for mutate in (
            lambda d: d["Statement"][0]["Action"].append("s3:DeleteBucket"),
            lambda d: d["Statement"][0]["Resource"].append("arn:aws:s3:::other/*"),
            lambda d: d["Statement"].append({"Effect": "Allow", "Action": "*", "Resource": "*"}),
            lambda d: d["Statement"][1].pop("Condition"),
            lambda d: d.update(Extra=True),
        ):
            d = json.loads(POLICY)
            mutate(d)
            variants.append(json.dumps(d))
        variants.extend(["[]", "null", "bad", scoped_object_policy("genapp-objects", ""),
                         scoped_object_policy("genapp-objects", "generated-apps/*/preview/")])
        for policy in variants:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                self.issue(policy=policy)

    def test_endpoint_rejects_credentials_redirect_origins_and_paths(self):
        for url in ("http://" + ENDPOINT[8:], ENDPOINT + "/bucket", ENDPOINT + "?q=x",
                    ENDPOINT + "#x", ENDPOINT + ":443", "https://user@" + ENDPOINT[8:],
                    "https://evil.example", "https://" + ENDPOINT[8:] + ".evil.example"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                r2_account_id(url)
        self.assertEqual(r2_account_id(ENDPOINT + "/"), ACCOUNT)

    def test_r2_configuration_requires_no_aws_role_and_remains_partial(self):
        env = dict(FULL_ENV, OMNI_GENAPP_S3_PROVIDER="cloudflare_r2", OMNI_GENAPP_S3_ENDPOINT=ENDPOINT)
        env.pop("OMNI_GENAPP_S3_ROLE_ARN")
        config = ManagedWebSaaSConfig.from_env(env)
        self.assertEqual(config.config_status(InfrastructureKind.OBJECT_STORAGE, env)[0], "PARTIAL")
        self.assertEqual(replace(config, s3_provider="unknown").config_status(
            InfrastructureKind.OBJECT_STORAGE, env)[0], "BLOCKED")
        self.assertEqual(replace(config, s3_endpoint="https://evil.example").config_status(
            InfrastructureKind.OBJECT_STORAGE, env)[0], "BLOCKED")
        self.assertEqual(replace(config, s3_credential_ttl_seconds=0).config_status(
            InfrastructureKind.OBJECT_STORAGE, env)[0], "BLOCKED")
        self.assertEqual(replace(config, s3_provider="aws_sts").config_status(
            InfrastructureKind.OBJECT_STORAGE, env)[0], "NOT_CONFIGURED")

    def test_real_issuer_is_wired_and_only_generated_secrets_are_saved(self):
        env = dict(FULL_ENV, OMNI_GENAPP_S3_PROVIDER="cloudflare_r2", OMNI_GENAPP_S3_ENDPOINT=ENDPOINT)
        env.pop("OMNI_GENAPP_S3_ROLE_ARN")
        class Probe:
            def verify(self, **kw):
                self.creds = kw
                return {"ok": True, "probe_object": kw["prefix"] + ".probe"}
            def verify_denied(self, **kw):
                return True
        probe, store = Probe(), FakeSecretStore()
        p = ManagedWebSaaSProvisioner(config=ManagedWebSaaSConfig.from_env(env), secret_store=store,
                                      resolve_reference=_resolver(env), storage_backend=probe, control_plane_env=env)
        contract = ProductArchitect().compile("Web app with file uploads.", project_id="prj_r2", contract_version=1)
        req = next(r for r in contract.infrastructure if r.kind == "object_storage")
        binding = p.provision(req, tenant_id="u", project_id="prj_r2", environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.LIVE)
        self.assertNotEqual(probe.creds["secret_key"], env["GENAPP_S3_SECRET"])
        self.assertEqual(set(binding.secret_references), {"access_key_id", "secret_access_key", "session_token"})
        self.assertNotIn(env["GENAPP_S3_SECRET"], json.dumps(binding.to_record()))
        self.assertEqual(len(store.values), 3)

    def test_default_sts_configuration_is_preserved(self):
        self.assertEqual(ManagedWebSaaSConfig.from_env(FULL_ENV).s3_provider, "aws_sts")


if __name__ == "__main__":
    unittest.main()

"""M5 remediation: generated-app object storage is isolated per app/environment
by scoped credentials, not just by key prefix.

The fake object store below ENFORCES the session policy attached to issued
credentials, so these tests check the policy really denies cross-environment
and cross-app access. Provider-level IAM proof is the gated integration test.
"""
from __future__ import annotations

import json
import unittest

from omni_prod.infrastructure_contracts import BindingStatus, InfrastructureKind
from omni_prod.infrastructure_provisioner import InfrastructureProvisioningService, MemoryInfrastructureBindingRepository
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import (
    ManagedWebSaaSConfig, ManagedWebSaaSProvisioner, managed_web_saas_readiness, scoped_object_policy,
    scoped_policy_allows)

try:
    from tests.test_m5_managed_web_saas_profile import FULL_ENV, FakeDatabaseBackend, FakeHttpProbe, FakeSecretStore, _resolver
except ModuleNotFoundError:
    from test_m5_managed_web_saas_profile import FULL_ENV, FakeDatabaseBackend, FakeHttpProbe, FakeSecretStore, _resolver

PROMPT = ("Build a booking SaaS for admins and customers with Postgres, login, uploads, scheduled reminders "
          "and outbound email.")


class PolicyEnforcingStore:
    """Fake S3: every request is evaluated against the credential's session policy."""

    def __init__(self, *, ignore_policy=False):
        self.credentials = {}       # access key -> policy
        self.ignore_policy = ignore_policy
        self.denied = []

    def issue(self, *, operator_access_key, operator_secret_key, role_arn, policy, session_name, ttl_seconds):
        assert operator_access_key == "genapp-access" and role_arn.startswith("arn:")
        key = f"ASIA{len(self.credentials):04d}{session_name[-8:]}"
        self.credentials[key] = json.loads(policy)
        return {"access_key_id": key, "secret_access_key": "scoped-secret-" + key,
                "session_token": "scoped-token-" + key, "expires_at": "2026-10-04T23:00:00Z"}

    def _allowed(self, access_key, action, bucket, key):
        if self.ignore_policy:
            return True
        return scoped_policy_allows(self.credentials[access_key], action=action, bucket=bucket, key=key)

    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key, session_token=None):
        ok = self._allowed(access_key, "s3:PutObject", bucket, prefix + ".148ai-probe")
        return {"probe_object": prefix + ".148ai-probe", "ok": ok}

    def verify_denied(self, *, endpoint, bucket, key, region, access_key, secret_key, session_token=None):
        allowed = self._allowed(access_key, "s3:GetObject", bucket, key)
        if not allowed:
            self.denied.append(key)
        return not allowed

    def get(self, access_key, bucket, key):
        if not self._allowed(access_key, "s3:GetObject", bucket, key):
            raise PermissionError("AccessDenied")
        return b"object"


def _provisioner(store, env=None, secret_store=None):
    env = dict(FULL_ENV if env is None else env)
    secret_store = secret_store or FakeSecretStore()
    return ManagedWebSaaSProvisioner(
        config=ManagedWebSaaSConfig.from_env(env), secret_store=secret_store, resolve_reference=_resolver(env),
        database_backend=FakeDatabaseBackend(), storage_backend=store, credential_issuer=store,
        http_probe=FakeHttpProbe(), control_plane_env=env), secret_store


class StorageIsolationTests(unittest.TestCase):
    def setUp(self):
        self.contract = ProductArchitect().compile(PROMPT, project_id="prj_iso", contract_version=1)
        self.storage_req = next(r for r in self.contract.infrastructure if r.kind == "object_storage")

    def _bind(self, store, project_id, environment, secrets=None):
        prov, secrets = _provisioner(store, secret_store=secrets)
        binding = prov.provision(self.storage_req, tenant_id="usr_1", project_id=project_id,
                                 environment=environment, idempotency_key=f"k_{project_id}_{environment}".ljust(64, "x"))
        return binding, secrets

    def _creds(self, binding, secrets):
        return secrets.values[binding.secret_references["access_key_id"]]

    def test_each_environment_gets_distinct_scoped_credentials(self):
        store = PolicyEnforcingStore()
        secrets = FakeSecretStore()
        preview, _ = self._bind(store, "prj_iso", "preview", secrets)
        prod, _ = self._bind(store, "prj_iso", "production", secrets)
        self.assertEqual((preview.status, prod.status), (BindingStatus.LIVE, BindingStatus.LIVE))
        self.assertEqual(preview.public_config["environment_isolation"], "SCOPED_CREDENTIALS")
        self.assertNotEqual(self._creds(preview, secrets), self._creds(prod, secrets))
        for b in (preview, prod):
            self.assertEqual(set(b.secret_references), {"access_key_id", "secret_access_key", "session_token"})
            self.assertTrue(all(r.startswith("vault:secret/data/148ai/generated-apps/") for r in b.secret_references.values()))
            self.assertNotIn("env:GENAPP_S3_ACCESS", json.dumps(b.to_record()))  # operator creds never reach the app

    def test_preview_cannot_read_production_objects_even_with_a_guessed_key(self):
        store = PolicyEnforcingStore()
        secrets = FakeSecretStore()
        preview, _ = self._bind(store, "prj_iso", "preview", secrets)
        prod, _ = self._bind(store, "prj_iso", "production", secrets)
        preview_key = self._creds(preview, secrets)
        bucket = prod.public_config["bucket"]
        guessed = prod.public_config["prefix"] + "uploads/invoice-001.pdf"
        with self.assertRaises(PermissionError):
            store.get(preview_key, bucket, guessed)
        self.assertEqual(store.get(preview_key, bucket, preview.public_config["prefix"] + "uploads/a.png"), b"object")

    def test_one_app_cannot_read_another_apps_objects(self):
        store = PolicyEnforcingStore()
        secrets = FakeSecretStore()
        a, _ = self._bind(store, "prj_a", "preview", secrets)
        b, _ = self._bind(store, "prj_b", "preview", secrets)
        with self.assertRaises(PermissionError):
            store.get(self._creds(a, secrets), b.public_config["bucket"], b.public_config["prefix"] + "x")

    def test_provisioning_proves_cross_environment_denial_before_live(self):
        store = PolicyEnforcingStore()
        binding, _ = self._bind(store, "prj_iso", "preview")
        self.assertEqual(binding.status, BindingStatus.LIVE)
        self.assertTrue(binding.evidence["cross_environment_denied"])
        self.assertTrue(any("/production/" in k for k in store.denied))

    def test_storage_that_ignores_policy_is_blocked_not_live(self):
        binding, _ = self._bind(PolicyEnforcingStore(ignore_policy=True), "prj_iso", "preview")
        self.assertEqual(binding.status, BindingStatus.BLOCKED)
        self.assertIn("isolation", binding.status_reason)

    def test_without_role_arn_storage_is_not_configured_never_prefix_only_live(self):
        env = {k: v for k, v in FULL_ENV.items() if k != "OMNI_GENAPP_S3_ROLE_ARN"}
        prov, _ = _provisioner(PolicyEnforcingStore(), env=env)
        binding = prov.provision(self.storage_req, tenant_id="usr_1", project_id="prj_iso", environment="preview",
                                 idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.NOT_CONFIGURED)
        self.assertIn("scoped", binding.status_reason)
        self.assertEqual(managed_web_saas_readiness(env)["kinds"]["object_storage"]["status"], "NOT_CONFIGURED")

    def test_policy_document_is_least_privilege(self):
        policy = json.loads(scoped_object_policy("genapp-objects", "generated-apps/abc/preview/"))
        actions = {a for s in policy["Statement"] for a in (s["Action"] if isinstance(s["Action"], list) else [s["Action"]])}
        self.assertEqual(actions, {"s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"})
        self.assertFalse(scoped_policy_allows(policy, action="s3:GetObject", bucket="genapp-objects",
                                              key="generated-apps/abc/production/x"))
        self.assertFalse(scoped_policy_allows(policy, action="s3:GetObject", bucket="other-bucket",
                                              key="generated-apps/abc/preview/x"))
        self.assertFalse(scoped_policy_allows(policy, action="s3:DeleteBucket", bucket="genapp-objects",
                                              key="generated-apps/abc/preview/x"))
        self.assertTrue(scoped_policy_allows(policy, action="s3:PutObject", bucket="genapp-objects",
                                             key="generated-apps/abc/preview/uploads/a.png"))

    def test_expired_scoped_credentials_are_not_live(self):
        store = PolicyEnforcingStore()
        prov, _ = _provisioner(store)
        binding = prov.provision(self.storage_req, tenant_id="usr_1", project_id="prj_iso", environment="preview",
                                 idempotency_key="k" * 64)
        checked = prov.status(binding, now="2026-10-05T00:00:00Z")
        self.assertEqual(checked.status, BindingStatus.BLOCKED)
        self.assertIn("expired", checked.status_reason)


if __name__ == "__main__":
    unittest.main()

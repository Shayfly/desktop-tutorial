"""M5 Task 7: concrete managed_web_saas_v1 provisioner (unit level).

All backends here are in-test doubles. They let us prove naming, idempotency,
secret handling, environment separation and revoke behaviour without real
infrastructure. Real-infrastructure proof lives in the gated integration test
tests/integration/test_m5_managed_web_saas_live.py.
"""
from __future__ import annotations

import json
import logging
import unittest
from pathlib import Path

from omni_prod.infrastructure_contracts import (
    BindingStatus,
    InfrastructureBinding,
    InfrastructureEnvironment,
    InfrastructureKind,
)
from omni_prod.infrastructure_provisioner import (
    InfrastructureProvisioningService,
    MemoryInfrastructureBindingRepository,
    PostgresInfrastructureBindingRepository,
)
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.managed_web_saas import (
    ManagedWebSaaSConfig,
    ManagedWebSaaSProvisioner,
    managed_web_saas_readiness,
)
from omni_prod.secrets_manager import VaultHttpSecretWriter

PROMPT = (
    "Build a travel agency CRM SaaS for admin and travel-agent users. "
    "Manage customers and bookings in Postgres, require login, file uploads, "
    "scheduled follow-ups and outbound email notifications."
)

FULL_ENV = {
    "OMNI_GENAPP_SECRET_STORE_URL": "https://vault.internal.example",
    "OMNI_GENAPP_VAULT_TOKEN": "vault-token-value",
    "OMNI_GENAPP_DATABASE_ADMIN_DSN_REF": "env:GENAPP_ADMIN_DSN",
    "GENAPP_ADMIN_DSN": "postgresql://genapp_admin:adminpw@db.genapp.example:5432/apps",
    "OMNI_DATABASE_URL": "postgresql://control:controlpw@db.control.example:5432/control",
    "OMNI_GENAPP_S3_ENDPOINT": "https://objects.genapp.example",
    "OMNI_GENAPP_S3_BUCKET": "genapp-objects",
    "OMNI_GENAPP_S3_ACCESS_KEY_REF": "env:GENAPP_S3_ACCESS",
    "OMNI_GENAPP_S3_SECRET_KEY_REF": "env:GENAPP_S3_SECRET",
    "GENAPP_S3_ACCESS": "genapp-access",
    "GENAPP_S3_SECRET": "genapp-secret",
    "OMNI_S3_BUCKET": "control-artifacts",
    "OMNI_S3_ACCESS_KEY": "control-access",
    "OMNI_GENAPP_SCHEDULER_URL": "https://scheduler.genapp.example",
    "OMNI_GENAPP_SCHEDULER_TOKEN_REF": "env:GENAPP_SCHEDULER_TOKEN",
    "GENAPP_SCHEDULER_TOKEN": "sched-token",
    "OMNI_GENAPP_EMAIL_API_KEY_REF": "env:GENAPP_EMAIL_KEY",
    "GENAPP_EMAIL_KEY": "genapp-email-key",
    "RESEND_API_KEY": "control-email-key",
}


class FakeSecretStore:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []

    def write(self, reference: str, value: str) -> None:
        self.values[reference] = value

    def resolve(self, reference: str) -> str:
        return self.values[reference]

    def delete(self, reference: str) -> None:
        self.deleted.append(reference)
        self.values.pop(reference, None)


class FakeDatabaseBackend:
    def __init__(self, *, login_ok=True):
        self.roles: dict[str, str] = {}
        self.disabled: list[str] = []
        self.ensure_calls = 0
        self.login_ok = login_ok

    def ensure_role_and_schema(self, *, admin_dsn, role, schema, password):
        assert "adminpw" in admin_dsn
        self.ensure_calls += 1
        self.roles[role] = password
        return {"role": role, "schema": schema, "created": True}

    def verify_login(self, app_dsn, *, schema):
        return self.login_ok and any(pw in app_dsn for pw in self.roles.values())

    def disable_role(self, *, admin_dsn, role):
        self.disabled.append(role)


class FakeStorageBackend:
    def __init__(self, ok=True):
        self.ok = ok
        self.probes = []

    def verify(self, *, endpoint, bucket, prefix, region, access_key, secret_key):
        self.probes.append((bucket, prefix, access_key))
        assert access_key == "genapp-access" and secret_key == "genapp-secret"
        return {"probe_object": prefix + ".148ai-probe", "ok": self.ok}


class FakeHttpProbe:
    def __init__(self, status=200):
        self.status = status
        self.calls = []

    def __call__(self, url, *, token):
        self.calls.append(url)
        return self.status


def _resolver(env):
    def resolve(reference):
        scheme, _, name = reference.partition(":")
        if scheme != "env" or name not in env:
            raise RuntimeError("secret not configured")
        return env[name]
    return resolve


def _provisioner(env=None, **backends):
    env = dict(FULL_ENV if env is None else env)
    secret_store = backends.pop("secret_store", FakeSecretStore())
    return ManagedWebSaaSProvisioner(
        config=ManagedWebSaaSConfig.from_env(env),
        secret_store=secret_store,
        resolve_reference=_resolver(env),
        database_backend=backends.pop("database_backend", FakeDatabaseBackend()),
        storage_backend=backends.pop("storage_backend", FakeStorageBackend()),
        http_probe=backends.pop("http_probe", FakeHttpProbe()),
        control_plane_env=env,
    ), secret_store


class ManagedWebSaaSProvisionerTests(unittest.TestCase):
    def setUp(self):
        self.contract = ProductArchitect().compile(PROMPT, project_id="prj_crm", contract_version=1)

    def _ensure(self, prov, environment="preview", repo=None):
        repo = repo or MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=prov, repository=repo)
        return service, repo, service.ensure(self.contract, tenant_id="usr_1", project_id="prj_crm",
                                             environment=environment)

    def test_fully_configured_profile_provisions_all_kinds_live(self):
        prov, store = _provisioner()
        _, repo, result = self._ensure(prov)
        self.assertTrue(result.ready, result.to_dict())
        bindings = {b.kind: b for b in repo.list_for(project_id="prj_crm", environment="preview")}
        self.assertEqual(set(bindings), set(InfrastructureKind))
        self.assertTrue(all(b.status == BindingStatus.LIVE for b in bindings.values()))
        self.assertEqual(bindings[InfrastructureKind.DATABASE].provisioner, "managed_web_saas")

    def test_resource_names_are_deterministic(self):
        prov_a, _ = _provisioner()
        prov_b, _ = _provisioner()
        _, repo_a, _ = self._ensure(prov_a)
        _, repo_b, _ = self._ensure(prov_b)
        names_a = {b.kind: b.resource_name for b in repo_a.list_for(project_id="prj_crm", environment="preview")}
        names_b = {b.kind: b.resource_name for b in repo_b.list_for(project_id="prj_crm", environment="preview")}
        self.assertEqual(names_a, names_b)
        db = names_a[InfrastructureKind.DATABASE]
        self.assertRegex(db, r"^ga_[0-9a-f]{16}_prev_database$")

    def test_idempotent_second_ensure_does_not_reprovision(self):
        db = FakeDatabaseBackend()
        prov, store = _provisioner(database_backend=db)
        service, repo, _ = self._ensure(prov)
        writes_before = dict(store.values)
        service.ensure(self.contract, tenant_id="usr_1", project_id="prj_crm", environment="preview")
        self.assertEqual(db.ensure_calls, 1)
        self.assertEqual(store.values, writes_before)

    def test_secrets_are_app_scoped_references_never_values(self):
        prov, store = _provisioner()
        _, repo, result = self._ensure(prov)
        serialized = json.dumps([b.to_record() for b in repo.list_for(project_id="prj_crm", environment="preview")])
        serialized += json.dumps(result.to_dict())
        for value in store.values.values():
            self.assertNotIn(value, serialized)
        for forbidden in ("adminpw", "genapp-secret", "genapp-access", "sched-token", "genapp-email-key",
                          "vault-token-value", "controlpw"):
            self.assertNotIn(forbidden, serialized)
        db = [b for b in repo.list_for(project_id="prj_crm", environment="preview")
              if b.kind == InfrastructureKind.DATABASE][0]
        self.assertTrue(db.secret_references["database_url"].startswith("vault:secret/data/148ai/generated-apps/"))
        # the generated app's database URL is a new role, not the admin or control-plane login
        app_dsn = store.values[db.secret_references["database_url"]]
        self.assertNotIn("genapp_admin", app_dsn)
        self.assertNotIn("control", app_dsn)

    def test_no_secret_material_reaches_logs(self):
        prov, store = _provisioner()
        with self.assertLogs("omni_prod.providers.managed_web_saas", level="DEBUG") as logs:
            logging.getLogger("omni_prod.providers.managed_web_saas").debug("probe")
            self._ensure(prov)
        text = "\n".join(logs.output)
        for value in store.values.values():
            self.assertNotIn(value, text)

    def test_preview_and_production_are_separate_resources_and_secrets(self):
        prov, store = _provisioner()
        repo = MemoryInfrastructureBindingRepository()
        self._ensure(prov, "preview", repo)
        self._ensure(prov, "production", repo)
        preview = {b.kind: b for b in repo.list_for(project_id="prj_crm", environment="preview")}
        prod = {b.kind: b for b in repo.list_for(project_id="prj_crm", environment="production")}
        generated = "vault:secret/data/148ai/generated-apps/"
        for kind in InfrastructureKind:
            self.assertNotEqual(preview[kind].resource_name, prod[kind].resource_name)
            for name, ref in preview[kind].secret_references.items():
                other = prod[kind].secret_references.get(name)
                if ref.startswith(generated):
                    self.assertNotEqual(ref, other)  # generated secrets are never shared
                elif ref == other:
                    # an operator-configured reference shared across environments
                    # must be declared by an explicit isolation policy
                    self.assertIn("isolation_policy", preview[kind].public_config, (kind, name))
        p_store = preview[InfrastructureKind.OBJECT_STORAGE].public_config["prefix"]
        r_store = prod[InfrastructureKind.OBJECT_STORAGE].public_config["prefix"]
        self.assertNotEqual(p_store, r_store)
        self.assertTrue(p_store.endswith("/preview/") and r_store.endswith("/production/"))

    def test_shared_object_storage_credentials_require_explicit_policy(self):
        prov, _ = _provisioner()
        binding = prov.provision(
            self.contract.infrastructure[2], tenant_id="usr_1", project_id="prj_crm",
            environment="production", idempotency_key="k" * 64)
        self.assertEqual(binding.public_config["environment_isolation"], "prefix")
        self.assertEqual(binding.public_config["isolation_policy"],
                         "generated-app object credentials are shared across environments; isolation is by prefix")

    def test_missing_secret_store_is_not_configured_everywhere(self):
        env = {k: v for k, v in FULL_ENV.items() if k != "OMNI_GENAPP_SECRET_STORE_URL"}
        prov, _ = _provisioner(env)
        _, repo, result = self._ensure(prov)
        self.assertFalse(result.ready)
        statuses = {b.kind: b.status for b in repo.list_for(project_id="prj_crm", environment="preview")}
        self.assertEqual(statuses[InfrastructureKind.DATABASE], BindingStatus.NOT_CONFIGURED)
        self.assertEqual(statuses[InfrastructureKind.AUTH_SESSION], BindingStatus.NOT_CONFIGURED)

    def test_partial_configuration_reports_each_kind_honestly(self):
        env = {k: v for k, v in FULL_ENV.items() if not k.startswith("OMNI_GENAPP_SCHEDULER")}
        prov, _ = _provisioner(env)
        _, repo, result = self._ensure(prov)
        statuses = {b.kind: b.status for b in repo.list_for(project_id="prj_crm", environment="preview")}
        self.assertEqual(statuses[InfrastructureKind.SCHEDULED_HTTP], BindingStatus.NOT_CONFIGURED)
        self.assertEqual(statuses[InfrastructureKind.DATABASE], BindingStatus.LIVE)
        self.assertFalse(result.ready)
        self.assertIn(InfrastructureKind.SCHEDULED_HTTP, result.not_live)

    def test_reusing_control_plane_credentials_is_blocked(self):
        env = dict(FULL_ENV, GENAPP_S3_ACCESS="control-access")
        prov, _ = _provisioner(env, storage_backend=FakeStorageBackend())
        binding = prov.provision(self.contract.infrastructure[2], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)
        self.assertIn("control-plane", binding.status_reason)

        env = dict(FULL_ENV, OMNI_GENAPP_S3_BUCKET="control-artifacts")
        prov, _ = _provisioner(env)
        binding = prov.provision(self.contract.infrastructure[2], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)

        env = dict(FULL_ENV, GENAPP_ADMIN_DSN=FULL_ENV["OMNI_DATABASE_URL"])
        prov, _ = _provisioner(env)
        binding = prov.provision(self.contract.infrastructure[0], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)

        env = dict(FULL_ENV, GENAPP_EMAIL_KEY="control-email-key")
        prov, _ = _provisioner(env)
        binding = prov.provision(self.contract.infrastructure[4], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)

    def test_failed_verification_is_blocked_not_live(self):
        prov, _ = _provisioner(database_backend=FakeDatabaseBackend(login_ok=False))
        binding = prov.provision(self.contract.infrastructure[0], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)
        prov, _ = _provisioner(storage_backend=FakeStorageBackend(ok=False))
        binding = prov.provision(self.contract.infrastructure[2], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)
        prov, _ = _provisioner(http_probe=FakeHttpProbe(status=503))
        binding = prov.provision(self.contract.infrastructure[3], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.BLOCKED)

    def test_outbound_email_is_not_claimed_live_verified(self):
        prov, _ = _provisioner()
        binding = prov.provision(self.contract.infrastructure[4], tenant_id="usr_1", project_id="prj_crm",
                                 environment="preview", idempotency_key="k" * 64)
        self.assertEqual(binding.status, BindingStatus.LIVE)
        self.assertIn("webhook_signing_secret", binding.secret_references)
        self.assertTrue(binding.evidence["email_configured"])
        self.assertFalse(binding.evidence["email_live_verified"])

    def test_revoke_disables_role_and_deletes_generated_secrets(self):
        db = FakeDatabaseBackend()
        prov, store = _provisioner(database_backend=db)
        service, repo, _ = self._ensure(prov)
        generated = set(store.values)
        revoked = service.revoke_all(project_id="prj_crm", environment="preview")
        self.assertEqual({b.status for b in revoked}, {BindingStatus.REVOKED})
        self.assertEqual(len(db.disabled), 1)
        self.assertEqual(set(store.deleted), generated)

    def test_readiness_surface_never_claims_live_from_config(self):
        surface = managed_web_saas_readiness(FULL_ENV)
        self.assertEqual(set(surface["kinds"]), {k.value for k in InfrastructureKind})
        self.assertTrue(all(v["status"] in {"PARTIAL", "NOT_CONFIGURED", "BLOCKED"} for v in surface["kinds"].values()))
        self.assertNotIn("LIVE", {v["status"] for v in surface["kinds"].values()})
        empty = managed_web_saas_readiness({})
        self.assertEqual({v["status"] for v in empty["kinds"].values()}, {"NOT_CONFIGURED"})
        blocked = managed_web_saas_readiness(dict(FULL_ENV, OMNI_GENAPP_S3_BUCKET="control-artifacts"))
        self.assertEqual(blocked["kinds"]["object_storage"]["status"], "BLOCKED")
        self.assertNotIn("genapp-secret", json.dumps(surface))


class VaultWriterTests(unittest.TestCase):
    def test_writer_posts_kv_v2_payload_and_never_puts_value_in_url(self):
        seen = {}

        class _Resp:
            status = 200
            def read(self): return b"{}"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def urlopen(req, timeout):
            seen["url"] = req.full_url
            seen["method"] = req.get_method()
            seen["body"] = json.loads(req.data.decode())
            seen["token"] = req.headers.get("X-vault-token")
            return _Resp()

        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"OMNI_GENAPP_VAULT_TOKEN": "tkn"}):
            writer = VaultHttpSecretWriter(base_url="https://vault.example", token_env="OMNI_GENAPP_VAULT_TOKEN",
                                           urlopen=urlopen)
            writer.write("vault:secret/data/148ai/generated-apps/x/preview/database/database_url", "s3cr3t")
        self.assertEqual(seen["url"], "https://vault.example/v1/secret/data/148ai/generated-apps/x/preview/database/database_url")
        self.assertEqual(seen["method"], "POST")
        self.assertEqual(seen["body"], {"data": {"value": "s3cr3t"}})
        self.assertNotIn("s3cr3t", seen["url"])
        self.assertEqual(seen["token"], "tkn")

    def test_writer_rejects_non_vault_reference(self):
        writer = VaultHttpSecretWriter(base_url="https://vault.example", token_env="X", urlopen=lambda *a, **k: None)
        with self.assertRaises(Exception):
            writer.write("env:SOMETHING", "v")


class PostgresBindingRepositoryTests(unittest.TestCase):
    def test_migration_021_enforces_reference_only_and_ownership(self):
        sql = (Path(__file__).resolve().parents[1] / "infra/postgres/021_generated_app_bindings.sql").read_text().lower()
        self.assertIn("create table if not exists generated_app_bindings", sql)
        self.assertIn("unique (idempotency_key)", sql)
        self.assertIn("unique (profile_key, project_id, environment, kind)", sql)
        self.assertIn("jsonb_path_exists", sql)  # secret_references must be env:/vault: refs
        self.assertIn("environment in ('preview','production')", sql)
        self.assertIn("cannot change binding ownership", sql)

    def test_repository_upsert_is_idempotency_keyed_and_tenant_guarded(self):
        calls = []

        class _Cur:
            def __init__(self): self.rows = [("usr_1",)]
            def execute(self, sql, params=None): calls.append((" ".join(sql.split()), params))
            def fetchone(self): return self.rows.pop(0) if self.rows else None
            def fetchall(self): return []
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _Conn:
            def cursor(self): return _Cur()
            def transaction(self): return self
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _Pool:
            def connection(self): return _Conn()

        repo = PostgresInfrastructureBindingRepository(_Pool())
        binding = InfrastructureBinding(
            binding_id="ib_1", profile_key="managed_web_saas_v1", tenant_id="usr_2", project_id="prj_crm",
            environment=InfrastructureEnvironment.PREVIEW, kind=InfrastructureKind.DATABASE,
            status=BindingStatus.LIVE, resource_name="ga_x", idempotency_key="k" * 64, provisioner="p",
            secret_references={"database_url": "vault:secret/data/x"})
        with self.assertRaises(PermissionError):
            repo.save(binding)
        self.assertIn("FOR UPDATE", calls[0][0])

        calls.clear()
        ok = binding.__class__(**{**binding.__dict__, "tenant_id": "usr_1"})
        repo.save(ok)
        insert = [c for c in calls if c[0].startswith("INSERT INTO generated_app_bindings")]
        self.assertTrue(insert)
        self.assertIn("ON CONFLICT (idempotency_key) DO UPDATE", insert[0][0])


if __name__ == "__main__":
    unittest.main()

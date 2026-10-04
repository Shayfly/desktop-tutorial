"""M5 Task 7 gated integration: real generated-app infrastructure.

Runs only when real staging infrastructure is supplied. Without it every test
SKIPs with the precise missing prerequisite; nothing here may be reported as
LIVE unless it actually ran.

Required for the provisioning test (M5_GENAPP_LIVE=1 plus):
  OMNI_GENAPP_SECRET_STORE_URL, the Vault token env (default OMNI_GENAPP_VAULT_TOKEN),
  OMNI_GENAPP_DATABASE_ADMIN_DSN_REF, OMNI_GENAPP_S3_ENDPOINT, OMNI_GENAPP_S3_BUCKET,
  OMNI_GENAPP_S3_ACCESS_KEY_REF, OMNI_GENAPP_S3_SECRET_KEY_REF,
  OMNI_GENAPP_SCHEDULER_URL, OMNI_GENAPP_SCHEDULER_TOKEN_REF
Required for the migration test: M5_DATABASE_URL pointing at a disposable database.
"""
from __future__ import annotations

import os
import unittest
import uuid
from pathlib import Path

REQUIRED = (
    "OMNI_GENAPP_SECRET_STORE_URL", "OMNI_GENAPP_DATABASE_ADMIN_DSN_REF", "OMNI_GENAPP_S3_ENDPOINT",
    "OMNI_GENAPP_S3_BUCKET", "OMNI_GENAPP_S3_ACCESS_KEY_REF", "OMNI_GENAPP_S3_SECRET_KEY_REF",
    "OMNI_GENAPP_SCHEDULER_URL", "OMNI_GENAPP_SCHEDULER_TOKEN_REF",
)


def _live_skip_reason() -> str | None:
    if os.environ.get("M5_GENAPP_LIVE") != "1":
        return "M5_GENAPP_LIVE=1 not set (real generated-app staging infrastructure not supplied)"
    missing = [name for name in REQUIRED if not os.environ.get(name)]
    token_env = os.environ.get("OMNI_GENAPP_SECRET_STORE_TOKEN_ENV", "OMNI_GENAPP_VAULT_TOKEN")
    if not os.environ.get(token_env):
        missing.append(token_env)
    if missing:
        return "missing generated-app staging configuration: " + ", ".join(missing)
    try:
        import psycopg  # noqa: F401
        import boto3  # noqa: F401
    except ImportError as exc:
        return f"live dependency not importable: {exc}"
    return None


def _db_skip_reason() -> str | None:
    if not os.environ.get("M5_DATABASE_URL"):
        return "M5_DATABASE_URL not set (no disposable Postgres supplied)"
    try:
        import psycopg  # noqa: F401
    except ImportError as exc:
        return f"psycopg not importable ({exc})"
    return None


_LIVE_SKIP = _live_skip_reason()
_DB_SKIP = _db_skip_reason()


@unittest.skipIf(_LIVE_SKIP is not None, _LIVE_SKIP or "")
class ManagedWebSaaSLiveProvisioningTests(unittest.TestCase):
    def test_provision_verify_idempotent_revoke_against_real_infrastructure(self):
        from omni_prod.infrastructure_contracts import BindingStatus, InfrastructureKind
        from omni_prod.infrastructure_provisioner import (
            InfrastructureProvisioningService, MemoryInfrastructureBindingRepository)
        from omni_prod.product_architect import ProductArchitect
        from omni_prod.providers.managed_web_saas import build_managed_web_saas_provisioner

        project_id = "prj_m5live_" + uuid.uuid4().hex[:10]
        contract = ProductArchitect().compile(
            "Build a booking SaaS for admins and customers with Postgres, login, uploads, "
            "scheduled reminders and outbound email.", project_id=project_id, contract_version=1)
        provisioner = build_managed_web_saas_provisioner()
        repo = MemoryInfrastructureBindingRepository()
        service = InfrastructureProvisioningService(provisioner=provisioner, repository=repo)

        result = service.ensure(contract, tenant_id="usr_m5live", project_id=project_id, environment="preview")
        self.assertTrue(result.ready, result.to_dict())
        first = {b.kind: b for b in repo.list_for(project_id=project_id, environment="preview")}
        self.assertEqual(set(first), set(InfrastructureKind))

        again = service.ensure(contract, tenant_id="usr_m5live", project_id=project_id, environment="preview")
        self.assertEqual(result.to_dict()["bindings"], again.to_dict()["bindings"])

        for binding in first.values():
            self.assertEqual(provisioner.status(binding).status, BindingStatus.LIVE, binding.kind)

        revoked = service.revoke_all(project_id=project_id, environment="preview")
        self.assertEqual({b.status for b in revoked}, {BindingStatus.REVOKED})


@unittest.skipIf(_DB_SKIP is not None, _DB_SKIP or "")
class GeneratedAppBindingMigrationLiveTests(unittest.TestCase):
    def setUp(self):
        import psycopg
        self.conn = psycopg.connect(os.environ["M5_DATABASE_URL"], autocommit=True)
        sql = (Path(__file__).resolve().parents[2] / "infra/postgres/021_generated_app_bindings.sql").read_text()
        with self.conn.cursor() as cur:
            cur.execute(sql)

    def tearDown(self):
        self.conn.close()

    def test_database_rejects_plaintext_secrets_and_ownership_changes(self):
        import psycopg
        bid = "ib_live_" + uuid.uuid4().hex[:12]
        with self.conn.cursor() as cur:
            with self.assertRaises(psycopg.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO generated_app_bindings(binding_id,idempotency_key,profile_key,tenant_id,project_id,"
                    "environment,kind,status,resource_name,provisioner,secret_references) "
                    "VALUES(%s,%s,'managed_web_saas_v1','t','p','preview','database','LIVE','r','x',%s::jsonb)",
                    (bid, bid, '{"database_url": "postgresql://u:pw@h/db"}'))
            cur.execute(
                "INSERT INTO generated_app_bindings(binding_id,idempotency_key,profile_key,tenant_id,project_id,"
                "environment,kind,status,resource_name,provisioner,secret_references) "
                "VALUES(%s,%s,'managed_web_saas_v1','t','p','preview','database','LIVE','r','x',%s::jsonb)",
                (bid, bid, '{"database_url": "vault:secret/data/148ai/x"}'))
            with self.assertRaises(psycopg.errors.RaiseException):
                cur.execute("UPDATE generated_app_bindings SET tenant_id='intruder' WHERE binding_id=%s", (bid,))
            cur.execute("DELETE FROM generated_app_bindings WHERE binding_id=%s", (bid,))


if __name__ == "__main__":
    unittest.main()

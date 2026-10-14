from __future__ import annotations

import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import investor_app, worker_tasks
from omni_prod.build_contract import BuildContractStatus
from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.job_repository import PostgresBuildRepository
from omni_prod.models import BuildStatus
from omni_prod.product_architect import ProductArchitect
from tests.policy_fixtures import ACCEPTED_SPEC, verified_chain


class _Cursor:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.rowcount = 1
    def execute(self, sql, params=None):
        self.calls.append((" ".join(sql.split()), params))
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None
    def __enter__(self): return self
    def __exit__(self, *args): return False


class _Ctx:
    def __init__(self, value): self.value = value
    def __enter__(self): return self.value
    def __exit__(self, *args): return False


class _Conn:
    def __init__(self, cur): self.cur = cur
    def cursor(self): return self.cur


class _Pool:
    def __init__(self, cur): self.cur = cur
    def connection(self): return _Ctx(_Conn(self.cur))


class BuildRequestContractRepositoryTests(unittest.TestCase):
    def test_create_request_persists_build_contract_id(self):
        cur = _Cursor()
        repo = PostgresBuildRepository(None)
        repo.create_request(
            cur,
            build_id="b1",
            user_id="u1",
            internal_project_id="tenant-key",
            prompt="immutable prompt",
            target_markets=("US",),
            branding_visible=None,
            white_label_name=None,
            rights_evidence=[],
            public_project_id="proj-1",
            build_contract_id="bc-1",
        )
        sql, params = cur.calls[-1]
        self.assertIn("build_contract_id", sql)
        self.assertEqual(params[-1], "bc-1")

    def test_get_request_returns_bound_contract_and_fingerprint(self):
        contract = ProductArchitect().compile(
            "Build a SaaS CRM for customers and bookings",
            project_id="proj-1",
            contract_version=1,
        )
        row = (
            "u1", "tenant-key", "mutable legacy prompt", ["US"], None, None, [], "proj-1",
            contract.id, contract.to_dict(), contract.contract_fingerprint,
            Decimal("0.30"), {"economics_quote": {"provider_maximum_usd": "0.30"}},
        )
        cur = _Cursor([row])
        out = PostgresBuildRepository(_Pool(cur)).get_request("b1")
        self.assertEqual(out["build_contract_id"], contract.id)
        self.assertEqual(out["build_contract"]["prompt"], contract.prompt)
        self.assertEqual(out["build_contract_fingerprint"], contract.contract_fingerprint)
        self.assertEqual(out["build_contract_binding"], "BOUND")
        self.assertIn("LEFT JOIN m5_build_contracts", cur.calls[0][0])

    def test_legacy_request_remains_readable_with_explicit_status(self):
        row = (
            "u1", "tenant-key", "legacy prompt", ["US"], None, None, [], "proj-1",
            None, None, None, Decimal("0.30"), {},
        )
        out = PostgresBuildRepository(_Pool(_Cursor([row]))).get_request("legacy")
        self.assertIsNone(out["build_contract_id"])
        self.assertIsNone(out["build_contract"])
        self.assertEqual(out["build_contract_binding"], "LEGACY_UNBOUND")


class ContractSelectionTests(unittest.TestCase):
    def test_unresolved_material_questions_block_before_reservation(self):
        repo = MemoryBuildContractRepository()
        with self.assertRaises(investor_app.M5BuildContractBlocked) as ctx:
            investor_app._m5_resolve_build_contract(
                repository=repo,
                architect=ProductArchitect(),
                project_id="proj-vague",
                prompt="Build me an app",
                requested_contract_id=None,
            )
        self.assertEqual(ctx.exception.contract.status, BuildContractStatus.NEEDS_CLARIFICATION)
        self.assertIsNotNone(repo.latest("proj-vague"))

    def test_cross_project_contract_id_is_rejected(self):
        repo = MemoryBuildContractRepository()
        contract = ProductArchitect().compile(
            "Build a SaaS CRM for customers",
            project_id="proj-owner",
            contract_version=1,
        )
        repo.save(contract)
        with self.assertRaises(PermissionError):
            investor_app._m5_resolve_build_contract(
                repository=repo,
                architect=ProductArchitect(),
                project_id="proj-other",
                prompt="changed prompt must not matter",
                requested_contract_id=contract.id,
            )

    def test_existing_contract_id_wins_over_changed_prompt(self):
        repo = MemoryBuildContractRepository()
        contract = ProductArchitect().compile(
            "Build a SaaS CRM for customers and bookings",
            project_id="proj-1",
            contract_version=1,
        )
        repo.save(contract)
        resolved = investor_app._m5_resolve_build_contract(
            repository=repo,
            architect=ProductArchitect(),
            project_id="proj-1",
            prompt="MUTATED PROMPT AFTER CONTRACT",
            requested_contract_id=contract.id,
        )
        self.assertEqual(resolved.id, contract.id)
        self.assertEqual(resolved.prompt, contract.prompt)


class _Jobs:
    def __init__(self, request):
        self.request = request
        self.transitions = []
    def get_request(self, build_id): return self.request
    def transition(self, **kw):
        self.transitions.append(kw)
        return True


class _PassingStage:
    def __init__(self): self.prepare_calls = []
    def prepare(self, **kw):
        self.prepare_calls.append(kw)
        return {"required_ready": True, "status": "VERIFIED", "requirements": []}
    def finalize_native(self, **kw):
        return {"required_ready": True, "status": "VERIFIED", "requirements": []}


class WorkerContractBindingTests(unittest.TestCase):
    def test_worker_uses_immutable_contract_prompt_plan_and_records_evidence(self):
        contract = ProductArchitect().compile(
            "Build a SaaS CRM for customers and bookings",
            project_id="proj-1",
            contract_version=1,
        )
        request = {
            "user_id": "u1",
            "internal_project_id": "tenant-key",
            "prompt": "MUTATED REQUEST PROMPT",
            "target_markets": ("US",),
            "branding_visible": None,
            "white_label_name": None,
            "rights_evidence": [],
            "public_project_id": "proj-1",
            "authorized_provider_cost_usd": Decimal("1.00"),
            "build_contract_id": contract.id,
            "build_contract": contract.to_dict(),
            "build_contract_fingerprint": contract.contract_fingerprint,
            "build_contract_binding": "BOUND",
            "economics_quote": {},
        }
        jobs = _Jobs(request)
        stage = _PassingStage()
        platform = MagicMock()
        platform.subscriptions = MagicMock()
        platform.subscriptions.plan_for.return_value = SimpleNamespace(code="pro")
        # Deliberately different mutable brain capability plan; Task 5 must not use it.
        platform.brain.decide.return_value = SimpleNamespace(
            capabilities=SimpleNamespace(requirements=()),
            rights=SimpleNamespace(required_disclosures=()),
            creative="creative",
        )
        platform.brain.creative.repository_files.return_value = {}
        platform.rights.assess.return_value = SimpleNamespace(
            publish_allowed=True,
            status=SimpleNamespace(value="CLEAR"),
            to_dict=lambda: {"status": "CLEAR"},
        )
        platform.rights.repository_files.return_value = {}
        platform.branding.decorate_repository.side_effect = lambda repo, **kw: dict(repo)

        report = SimpleNamespace(passed=True, failures=(), build_log="ok")
        engine = MagicMock()
        engine.executor = verified_chain()  # release policy: the chain's checks ran and passed
        engine.build.return_value = SimpleNamespace(
            status="ready", report=report, spec=ACCEPTED_SPEC, repository={"app.py": "x"}, repair_rounds=0,
        )
        workspace = MagicMock()
        workspace.commit.return_value = SimpleNamespace(id="v1", artifact_key="a.zip")

        out = worker_tasks._run_live_build_job(
            "b1",
            jobs=jobs,
            platform=platform,
            workspace=workspace,
            components_factory=lambda: (engine, None),
            quality_fn=lambda **kw: SimpleNamespace(passed=True, score=100, minimum_score=80, blockers=(), to_dict=lambda: {"passed": True}),
            security_fn=lambda repo: SimpleNamespace(passed=True, findings=(), to_dict=lambda: {"passed": True}),
            capability_stage=stage,
        )
        self.assertEqual(out, BuildStatus.READY.value)
        engine.build.assert_called_once_with(contract.prompt)
        self.assertEqual(stage.prepare_calls[0]["plan"], contract.capability_plan)
        evidence = jobs.transitions[-1]["evidence_json"]["build_contract"]
        self.assertEqual(evidence["id"], contract.id)
        self.assertEqual(evidence["fingerprint"], contract.contract_fingerprint)
        self.assertEqual(evidence["binding"], "BOUND")


class MigrationContractTests(unittest.TestCase):
    def test_migration_adds_restricted_contract_fk_and_project_guard(self):
        text = (Path(__file__).resolve().parents[1] / "infra/postgres/020_m5_build_contracts.sql").read_text().lower()
        self.assertIn("build_contract_id", text)
        self.assertIn("references m5_build_contracts(id)", text)
        self.assertIn("on delete restrict", text)
        self.assertIn("public_project_id", text)
        self.assertIn("m5_build_request_contract_project", text)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

from omni_prod.product_spec import ProductSpec
from omni_prod.build_contract import BuildContract, BuildContractStatus
from omni_prod.build_contract_repository import MemoryBuildContractRepository
from omni_prod.product_architect import ProductArchitect


class _SparseArchitectAgent:
    """Deliberately omits platform minimums; deterministic floor must survive."""

    def __init__(self):
        self.floor = None

    def create_spec(self, prompt: str, *, deterministic_floor=None) -> ProductSpec:
        self.floor = deterministic_floor
        return ProductSpec.from_dict(
            {
                "title": "Travel CRM",
                "summary": "A narrow model-authored enrichment.",
                "stack": ["Python", "FastAPI"],
                "requirements": [
                    {"id": "model-reporting", "text": "Managers can view a bookings report", "kind": "functional"}
                ],
                "acceptance": [
                    {"id": "model-reporting-accept", "requirement_id": "model-reporting", "text": "Report endpoint returns booking totals"}
                ],
            }
        )


class ProductArchitectTests(unittest.TestCase):
    def test_high_confidence_web_saas_contract_is_complete_and_ready(self):
        architect = ProductArchitect()
        contract = architect.compile(
            "Build a travel agency CRM SaaS for admin and travel-agent users. "
            "Manage customers and bookings in Postgres, require login, file uploads, "
            "scheduled follow-ups and outbound email notifications.",
            project_id="prj_travel",
            contract_version=1,
            pricing_catalog_version="catalog-2026-10-04",
        )

        self.assertEqual(contract.status, BuildContractStatus.READY)
        self.assertEqual(contract.product_family, "managed_web_saas_v1")
        self.assertEqual(contract.target, "web")
        self.assertEqual(contract.release_target, "vercel")
        self.assertIn("admin", contract.user_roles)
        self.assertIn("travel_agent", contract.user_roles)
        self.assertIn("customers", contract.data_requirements)
        self.assertIn("bookings", contract.data_requirements)
        self.assertIn("email", contract.required_integrations)
        self.assertEqual(contract.unresolved_questions, ())

        infra = {item.kind for item in contract.infrastructure if item.required}
        self.assertTrue({"database", "auth_session", "object_storage", "scheduled_http", "outbound"}.issubset(infra))
        self.assertTrue(contract.acceptance)
        self.assertTrue(contract.security)
        self.assertTrue(contract.capability_plan_fingerprint.startswith("sha256:"))
        self.assertEqual(contract.cost_envelope.pricing_catalog_version, "catalog-2026-10-04")
        self.assertTrue(contract.cost_envelope.reservation_required)
        self.assertEqual(contract.cost_envelope.quote_basis, "CONSERVATIVE_MAXIMUM")
        self.assertTrue(contract.required_skill_keys)
        self.assertIn("agent.venice", contract.required_agent_keys)
        self.assertIn("agent.chief_orchestrator", contract.required_agent_keys)

    def test_low_confidence_material_ambiguity_creates_concise_question(self):
        contract = ProductArchitect().compile(
            "Build me an app",
            project_id="prj_vague",
            contract_version=1,
        )
        self.assertEqual(contract.status, BuildContractStatus.NEEDS_CLARIFICATION)
        self.assertGreaterEqual(len(contract.unresolved_questions), 1)
        self.assertLessEqual(len(contract.unresolved_questions), 2)
        self.assertTrue(all(q.material for q in contract.unresolved_questions))
        self.assertTrue(all(q.question.strip() for q in contract.unresolved_questions))

    def test_model_output_cannot_remove_deterministic_capability_floor(self):
        model = _SparseArchitectAgent()
        contract = ProductArchitect(architect_agent=model).compile(
            "Build a SaaS CRM for customers and bookings with payment checkout",
            project_id="prj_floor",
            contract_version=1,
        )
        keys = {r.key for r in contract.capability_plan.requirements}
        for required in (
            "software.plan",
            "software.architecture",
            "software.code.generate",
            "software.dependencies.install",
            "software.build",
            "software.test",
            "software.repair",
            "software.preview",
            "software.export",
            "target.web",
            "target.saas",
            "integration.payment",
        ):
            self.assertIn(required, keys)
        self.assertIsNotNone(model.floor)
        self.assertIn("capability_plan", model.floor)
        self.assertIn("model-reporting", {r.id for r in contract.product_spec.requirements})
        self.assertIn("platform-auth", {r.id for r in contract.product_spec.requirements})

    def test_capability_plan_fingerprint_is_stable_for_same_intent(self):
        architect = ProductArchitect()
        a = architect.compile("Build a SaaS CRM for customers and bookings", project_id="p", contract_version=1)
        b = architect.compile("Build a SaaS CRM for customers and bookings", project_id="p", contract_version=2)
        self.assertEqual(a.capability_plan_fingerprint, b.capability_plan_fingerprint)
        self.assertNotEqual(a.contract_fingerprint, b.contract_fingerprint)

    def test_build_contract_round_trip_preserves_canonical_fingerprints(self):
        original = ProductArchitect().compile(
            "Build a SaaS CRM for customers and bookings",
            project_id="prj_roundtrip",
            contract_version=1,
        )
        restored = BuildContract.from_dict(original.to_dict())
        self.assertEqual(restored, original)
        self.assertEqual(restored.contract_fingerprint, original.contract_fingerprint)

    def test_repository_revisions_are_immutable_and_monotonic(self):
        architect = ProductArchitect()
        repo = MemoryBuildContractRepository()
        v1 = architect.compile("Build a SaaS CRM for customers", project_id="p1", contract_version=1)
        repo.save(v1)
        self.assertEqual(repo.get(v1.id, project_id="p1"), v1)

        with self.assertRaisesRegex(ValueError, "already exists"):
            repo.save(architect.compile("Build a SaaS CRM for bookings", project_id="p1", contract_version=1))

        v2 = architect.compile("Build a SaaS CRM for customers and bookings", project_id="p1", contract_version=2)
        repo.save(v2)
        self.assertEqual(repo.latest("p1"), v2)
        self.assertEqual([c.contract_version for c in repo.list_revisions("p1")], [1, 2])

    def test_repository_enforces_project_scope(self):
        contract = ProductArchitect().compile("Build a SaaS CRM for customers", project_id="owner-project", contract_version=1)
        repo = MemoryBuildContractRepository()
        repo.save(contract)
        with self.assertRaises(PermissionError):
            repo.get(contract.id, project_id="different-project")


class BuildContractSchemaContractTests(unittest.TestCase):
    def test_migration_has_immutable_revision_identity_and_no_cascade_delete(self):
        migration = (Path(__file__).resolve().parents[1] / "infra/postgres/020_m5_build_contracts.sql").read_text().lower()
        self.assertIn("m5_build_contracts", migration)
        self.assertIn("unique(project_id,contract_version)", migration.replace(" ", "").replace("\n", ""))
        self.assertIn("contract_fingerprint", migration)
        self.assertIn("capability_plan_fingerprint", migration)
        self.assertIn("jsonb", migration)
        self.assertNotIn("on delete cascade", migration)
        self.assertIn("reject_m5_build_contract_mutation", migration)


if __name__ == "__main__":
    unittest.main()

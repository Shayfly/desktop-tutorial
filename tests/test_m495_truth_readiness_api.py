from __future__ import annotations

import json
import os
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from omni_prod.capability_repository import CapabilityRequirementRecord
from omni_prod.capabilities import CapabilityStatus
from omni_prod.investor_app import app, _v28


class _FakeBuildRepository:
    expected_project_key: str | None = None

    def __init__(self, pool) -> None:
        self.pool = pool

    def get_details(self, build_id: str, *, internal_project_id: str):
        if build_id != "bld_truth_1" or internal_project_id != self.expected_project_key:
            raise KeyError("not found")
        return object()


class _FakeCapabilityRepository:
    def __init__(self, pool) -> None:
        self.pool = pool

    def list_requirements(self, build_id: str):
        if build_id != "bld_truth_1":
            return []
        return [
            CapabilityRequirementRecord(
                build_id=build_id,
                requirement_id="req_3d",
                capability_key="media.3d.mesh.generate",
                purpose="Generate verified mesh",
                required=True,
                quantity=1,
                constraints={"format": "glb", "api_key": "must-never-leak"},
                dependency_ids=(),
                status="VERIFIED",
                selected_provider="fake-3d",
                artifact_key="projects/internal/builds/bld_truth_1/mesh.glb",
                verification={"passed": True, "sha256": "a" * 64, "authorization": "must-never-leak"},
            )
        ]


class M495TruthReadinessAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def _register(self, prefix: str) -> tuple[str, str, str]:
        email = f"{prefix}-{uuid.uuid4().hex[:10]}@example.com"
        response = self.client.post(
            "/api/v28/auth/register",
            json={"email": email, "password": "StrongPass123!"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        token = response.json()["token"]
        project = self.client.post(
            "/api/v28/projects",
            headers={"Authorization": f"Bearer {token}"},
            json={"title": f"{prefix} project"},
        )
        self.assertEqual(project.status_code, 200, project.text)
        return token, project.json()["id"], response.json()["user"]["id"]

    def test_capability_catalog_requires_auth_and_uses_truth_status_vocabulary(self):
        denied = self.client.get("/api/v28/capabilities")
        self.assertEqual(denied.status_code, 401)

        token, _, _ = self._register("capability-truth")
        response = self.client.get(
            "/api/v28/capabilities",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertGreater(len(payload["capabilities"]), 20)
        by_key = {row["key"]: row for row in payload["capabilities"]}
        self.assertIn("media.3d.mesh.generate", by_key)
        allowed = {status.value for status in CapabilityStatus}
        self.assertTrue(all(row["status"] in allowed for row in payload["capabilities"]))
        # M4.95 has contracts but no live commercial 3D provider wired yet.
        self.assertNotEqual(by_key["media.3d.mesh.generate"]["status"], "LIVE")

    def test_provider_status_never_returns_secret_values(self):
        token, _, _ = self._register("provider-truth")
        with patch.dict(os.environ, {"RUNPOD_API_KEY": "provider-secret-value-xyz"}, clear=False):
            response = self.client.get(
                "/api/v28/providers/status",
                headers={"Authorization": f"Bearer {token}"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        serialized = json.dumps(response.json(), sort_keys=True)
        self.assertNotIn("provider-secret-value-xyz", serialized)
        self.assertIn("providers", response.json())

    def test_build_capability_truth_is_tenant_scoped_and_secret_redacted(self):
        owner_token, owner_project, _ = self._register("truth-owner")
        other_token, _, _ = self._register("truth-other")
        _, internal_key = _v28.resolve_project_key(token=owner_token, project_id=owner_project)
        _FakeBuildRepository.expected_project_key = internal_key

        patches = (
            patch("omni_prod.investor_app._v28_pool", object()),
            patch("omni_prod.investor_app.PostgresBuildRepository", _FakeBuildRepository),
            patch("omni_prod.investor_app.PostgresCapabilityRepository", _FakeCapabilityRepository),
        )
        with patches[0], patches[1], patches[2]:
            owner = self.client.get(
                f"/api/v28/projects/{owner_project}/builds/bld_truth_1/capabilities",
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            self.assertEqual(owner.status_code, 200, owner.text)
            serialized = json.dumps(owner.json(), sort_keys=True)
            self.assertNotIn("must-never-leak", serialized)
            row = owner.json()["requirements"][0]
            self.assertEqual(row["capability_key"], "media.3d.mesh.generate")
            self.assertEqual(row["status"], "VERIFIED")
            self.assertEqual(row["constraints"]["format"], "glb")
            self.assertEqual(row["constraints"]["api_key"], "[REDACTED]")
            self.assertEqual(row["verification"]["authorization"], "[REDACTED]")

            denied = self.client.get(
                f"/api/v28/projects/{owner_project}/builds/bld_truth_1/capabilities",
                headers={"Authorization": f"Bearer {other_token}"},
            )
            self.assertIn(denied.status_code, {403, 404})


if __name__ == "__main__":
    unittest.main()

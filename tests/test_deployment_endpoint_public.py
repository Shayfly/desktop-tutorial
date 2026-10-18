import unittest

from fastapi.testclient import TestClient
from unittest.mock import patch

from omni_prod import investor_app


class DeploymentEndpointPublicTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(investor_app.app)

    def test_deployment_is_public_in_production(self):
        with patch.dict("os.environ", {"OMNI_ENV": "production"}):
            self.assertNotEqual(self.client.get("/api/v28/deployment").status_code, 401)

    def test_project_conversation_stays_protected_in_production(self):
        # deployment_verify.py's unauthenticated_denied check targets this endpoint.
        with patch.dict("os.environ", {"OMNI_ENV": "production"}):
            r = self.client.get("/api/v28/projects/p1/conversation")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.json()["detail"], "authentication required")


if __name__ == "__main__":
    unittest.main()

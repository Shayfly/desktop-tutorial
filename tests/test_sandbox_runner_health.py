"""The sandbox runner is healthy only when a run can work.

Golden E2E #1 on Preview (2026-10-07): the runner answered /health 200 while
its image had no docker client, and every build's first sandbox command got
HTTP 500 ("No such file or directory: 'docker'"). Health now checks the client
and the daemon socket; the image build fails without the client; the worker
deploy runs a real snippet through the sandbox.
"""
import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class ImageAndDeployTests(unittest.TestCase):
    def test_runner_image_build_fails_without_the_docker_client(self):
        dockerfile = (ROOT / "infra/sandbox-runner/Dockerfile").read_text()
        self.assertIn("docker-cli", dockerfile)
        self.assertIn("&& docker --version", dockerfile)

    def test_deploy_runs_code_in_the_sandbox_and_checks_network_isolation(self):
        # Plain text (PyYAML is not a CI dependency).
        text = (ROOT / ".github/workflows/deploy-worker.yml").read_text()
        probe = text.index("- name: Prove the sandbox runs code without network access")
        queue = text.index("- name: Prove the worker executes a job from the build queue")
        self.assertLess(probe, queue)
        run = text[probe:queue]
        for needle in ("RemoteSandboxRepositoryExecutor", "network-blocked", "sys.exit(1)"):
            self.assertIn(needle, run)

    def test_mount_roots_are_usable_by_the_unprivileged_sandbox_user(self):
        # First deploy probe after the client fix: python exited 2 inside the
        # sandbox because the 0700 temp directory was not traversable by uid
        # 10001. The runner now opens the source (0755) and output (0777) roots.
        source = (ROOT / "omni_prod/sandbox_service.py").read_text()
        self.assertIn("os.chmod(root,0o755); os.chmod(out,0o777)", source)
        self.assertLess(source.index("os.chmod(root,0o755)"), source.index("r=run_sandbox("))


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "FastAPI not installed")
class HealthEndpointTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from omni_prod import sandbox_service
        self.module = sandbox_service
        self.client = TestClient(sandbox_service.app)

    def test_missing_docker_client_is_unhealthy(self):
        with mock.patch("shutil.which", return_value=None):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 503)
        self.assertIn("docker client not installed", r.text)

    def test_missing_socket_is_unhealthy(self):
        with mock.patch("shutil.which", return_value="/usr/bin/docker"), \
                mock.patch.dict("os.environ", {"DOCKER_HOST": ""}), \
                mock.patch.object(self.module.Path, "exists", return_value=False):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 503)
        self.assertIn("socket not mounted", r.text)

    def test_ready_runner_is_healthy(self):
        with mock.patch("shutil.which", return_value="/usr/bin/docker"), \
                mock.patch.object(self.module.Path, "exists", return_value=True):
            r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"ok": True, "runner": "docker-isolated"})


if __name__ == "__main__":
    unittest.main()

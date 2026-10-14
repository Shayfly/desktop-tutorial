import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_prod.config import Settings
from omni_prod.sandbox import SandboxLimits, build_docker_command

class ConfigTests(unittest.TestCase):
    def test_production_secret_minimum(self):
        env = {
            "OMNI_ENV": "production",
            "OMNI_SECRET_KEY": "x" * 64,
            "OMNI_DATABASE_URL": "postgresql://x",
            "OMNI_REDIS_URL": "redis://x",
            "OMNI_S3_ENDPOINT": "http://s3",
            "OMNI_S3_BUCKET": "b",
            "OMNI_S3_ACCESS_KEY": "a",
            "OMNI_S3_SECRET_KEY": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            s = Settings.from_env()
            self.assertEqual(s.environment, "production")
            self.assertEqual(s.sandbox_timeout_seconds, 180)

    def test_short_production_secret_rejected(self):
        env = {
            "OMNI_ENV": "production",
            "OMNI_SECRET_KEY": "short",
            "OMNI_DATABASE_URL": "postgresql://x",
            "OMNI_REDIS_URL": "redis://x",
            "OMNI_S3_ENDPOINT": "http://s3",
            "OMNI_S3_BUCKET": "b",
            "OMNI_S3_ACCESS_KEY": "a",
            "OMNI_S3_SECRET_KEY": "s",
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(RuntimeError):
                Settings.from_env()

class SandboxTests(unittest.TestCase):
    def test_docker_command_is_locked_down(self):
        with tempfile.TemporaryDirectory() as td:
            cmd = build_docker_command(
                source_dir=td,
                build_id="abc-123",
                limits=SandboxLimits(),
                command=["python", "-m", "pytest", "-q"],
            )
            joined = " ".join(cmd)
            self.assertIn("--network none", joined)
            self.assertIn("--read-only", joined)
            self.assertIn("--cap-drop ALL", joined)
            self.assertIn("--pids-limit 256", joined)
            self.assertIn("readonly", joined)

    def test_unsafe_build_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                build_docker_command(
                    source_dir=td,
                    build_id="../bad",
                    limits=SandboxLimits(),
                    command=["python", "-V"],
                )

if __name__ == "__main__":
    unittest.main()

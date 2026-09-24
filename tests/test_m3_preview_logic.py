from __future__ import annotations

"""Real unit tests for M3 (Real Running Preview) logic.

Scope, matching the M3 directive's Step 6 exactly:
  - DockerPreviewProvider: subprocess.run is mocked (no real Docker registry/
    daemon access in this sandbox -- see PATCH_APPLICATION_REPORT.md), and
    every test asserts against the REAL argv/parsing/port/file-materialization
    logic that runs around that mocked call, not against a canned response.
  - PostgresPreviewRepository: no real Postgres connection is available in
    this sandbox (psycopg/psycopg_pool are not installed here, matching every
    prior phase's documented blocker). Nothing in this repository currently
    unit-tests a Postgres*Repository class against a real *or* fake pool, so
    this file adds a small, self-contained fake pool/connection/cursor that
    mirrors DatabasePool's real contract (omni_prod/db.py: pool.connection()
    is a context manager yielding a conn; conn.transaction() and
    conn.cursor() are both context managers) closely enough to exercise the
    real SQL/parameter-building and state-transition logic in
    preview_repository.py -- it is not a substitute for an integration test
    against real Postgres, and is not claimed to be one.

execute_preview_launch() (worker_tasks.py) and the two new FastAPI routes in
investor_app.py are NOT tested here, for the same reason execute_live_build_job
was not unit-tested in tests/test_m2_native_logic.py: importing investor_app
(even indirectly, via worker_tasks.py's lazy `from .investor_app import ...`)
requires `fastapi`, which is not installable in this sandbox (see
PATCH_APPLICATION_REPORT.md). This is stated plainly rather than worked
around with a fabricated fastapi stub.

Run with: python3 -m unittest tests.test_m3_preview_logic -v
"""

import json
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from omni_prod.preview_runtime import (
    DockerPreviewProvider,
    _free_host_port,
    _materialize_repository,
    _parse_start_command,
)
from omni_prod.preview_repository import PostgresPreviewRepository
from omni_prod.repository_patch import PatchValidationError


def _repo_with_start(start=None, port=None, extra_files=None):
    manifest = {}
    if start is not None:
        manifest["start"] = start
    if port is not None:
        manifest["port"] = port
    repo = {".omni/project.json": json.dumps(manifest), "app.py": 'print("hi")'}
    if extra_files:
        repo.update(extra_files)
    return repo


# ---------------------------------------------------------------------------
# _parse_start_command
# ---------------------------------------------------------------------------


class TestParseStartCommand(unittest.TestCase):
    def test_valid_start_and_port(self):
        cmd, port = _parse_start_command(_repo_with_start(start=["python", "app.py"], port=9000))
        self.assertEqual(cmd, ["python", "app.py"])
        self.assertEqual(port, 9000)

    def test_defaults_to_port_8000_when_omitted(self):
        _, port = _parse_start_command(_repo_with_start(start=["node", "index.js"]))
        self.assertEqual(port, 8000)

    def test_missing_manifest_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({"app.py": "x"})

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": "{not valid json"})

    def test_manifest_root_not_object_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps(["a", "list"])})

    def test_missing_start_key_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({})})

    def test_start_not_a_list_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({"start": "python app.py"})})

    def test_start_with_non_string_element_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({"start": ["python", 1]})})

    def test_empty_start_list_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({"start": []})})

    def test_port_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({"start": ["a"], "port": 99999})})

    def test_port_not_int_raises(self):
        with self.assertRaises(ValueError):
            _parse_start_command({".omni/project.json": json.dumps({"start": ["a"], "port": "8000"})})


# ---------------------------------------------------------------------------
# _materialize_repository
# ---------------------------------------------------------------------------


class TestMaterializeRepository(unittest.TestCase):
    def test_writes_files_with_real_content(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _materialize_repository(root, {"a/b.txt": "hello", "c.txt": "world"})
            self.assertEqual((root / "a" / "b.txt").read_text(), "hello")
            self.assertEqual((root / "c.txt").read_text(), "world")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(PatchValidationError):
                _materialize_repository(root, {"../evil.txt": "x"})


# ---------------------------------------------------------------------------
# _free_host_port
# ---------------------------------------------------------------------------


class TestFreeHostPort(unittest.TestCase):
    def test_returns_a_bindable_port(self):
        port = _free_host_port()
        self.assertIsInstance(port, int)
        self.assertTrue(0 < port <= 65535)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))  # re-bindable immediately after release


# ---------------------------------------------------------------------------
# DockerPreviewProvider.start() -- subprocess.run mocked, everything else real
# ---------------------------------------------------------------------------


class TestDockerPreviewProviderStart(unittest.TestCase):
    def _repo(self):
        return _repo_with_start(start=["python", "app.py"], port=9000)

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_success_builds_correct_argv_and_materializes_files_to_disk(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc123containerid\n", stderr="",
        )
        provider = DockerPreviewProvider(workspace=None)
        container_id, url = provider.start(
            preview_id="prv_test1", project_id="proj_1", version_id="ver_1", repository=self._repo(),
        )

        self.assertEqual(container_id, "abc123containerid")
        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]

        self.assertEqual(argv[0:3], ["docker", "run", "-d"])
        self.assertIn("--name", argv)
        self.assertIn("omni-preview-prv_test1", argv)
        self.assertNotIn("--rm", argv)  # deliberate: see preview_runtime.py comment

        self.assertIn("--mount", argv)
        mount_arg = argv[argv.index("--mount") + 1]
        self.assertTrue(mount_arg.startswith("type=bind,src="))
        self.assertIn("dst=/workspace,readonly", mount_arg)

        # The mounted source directory is real and really holds the repo.
        src_path = mount_arg.split("src=")[1].split(",dst=")[0]
        self.assertTrue((Path(src_path) / "app.py").exists())
        self.assertEqual(
            (Path(src_path) / ".omni" / "project.json").read_text(),
            self._repo()[".omni/project.json"],
        )

        # start command is appended verbatim at the end of argv
        self.assertEqual(argv[-2:], ["python", "app.py"])

        # -p host:container maps to the manifest port, and the returned url
        # matches whichever host port was actually chosen (not a hardcoded one)
        p_index = argv.index("-p")
        host_port_str, container_port_str = argv[p_index + 1].split(":")
        self.assertEqual(container_port_str, "9000")
        self.assertEqual(url, f"http://localhost:{host_port_str}")

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_docker_run_nonzero_exit_raises_runtime_error_with_stderr(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="no such image: bogus:latest",
        )
        provider = DockerPreviewProvider(workspace=None)
        with self.assertRaises(RuntimeError) as ctx:
            provider.start(preview_id="prv_test2", project_id="proj_1", version_id="ver_1", repository=self._repo())
        self.assertIn("no such image", str(ctx.exception))

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_empty_stdout_on_success_raises_runtime_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        provider = DockerPreviewProvider(workspace=None)
        with self.assertRaises(RuntimeError):
            provider.start(preview_id="prv_test3", project_id="proj_1", version_id="ver_1", repository=self._repo())

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_missing_start_command_never_calls_docker(self, mock_run):
        provider = DockerPreviewProvider(workspace=None)
        repo = {".omni/project.json": json.dumps({})}
        with self.assertRaises(ValueError):
            provider.start(preview_id="prv_test4", project_id="proj_1", version_id="ver_1", repository=repo)
        mock_run.assert_not_called()

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_unsafe_preview_id_never_calls_docker(self, mock_run):
        provider = DockerPreviewProvider(workspace=None)
        with self.assertRaises(ValueError):
            provider.start(
                preview_id="prv_1/../evil", project_id="proj_1", version_id="ver_1", repository=self._repo(),
            )
        mock_run.assert_not_called()

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_falls_back_to_workspace_when_repository_not_given(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="cid\n", stderr="")
        fake_version = MagicMock()
        fake_version.repository.return_value = self._repo()
        fake_workspace = MagicMock()
        fake_workspace.get.return_value = fake_version

        provider = DockerPreviewProvider(workspace=fake_workspace)
        container_id, _url = provider.start(preview_id="prv_test5", project_id="proj_1", version_id="ver_1")

        fake_workspace.get.assert_called_once_with(project_id="proj_1", version_id="ver_1")
        fake_version.repository.assert_called_once()
        self.assertEqual(container_id, "cid")


class TestDockerPreviewProviderStopAndLogs(unittest.TestCase):
    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_stop_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        DockerPreviewProvider(workspace=None).stop("cid123")
        mock_run.assert_called_once_with(
            ["docker", "rm", "-f", "cid123"], text=True, capture_output=True, timeout=30,
        )

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_stop_failure_raises_runtime_error_with_stderr(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="no such container",
        )
        with self.assertRaises(RuntimeError) as ctx:
            DockerPreviewProvider(workspace=None).stop("cid123")
        self.assertIn("no such container", str(ctx.exception))

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_logs_success_concatenates_stdout_and_stderr(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="out-line\n", stderr="err-line\n",
        )
        result = DockerPreviewProvider(workspace=None).logs("cid123", tail=20)
        self.assertIn("out-line", result)
        self.assertIn("err-line", result)
        mock_run.assert_called_once_with(
            ["docker", "logs", "--tail", "20", "cid123"], text=True, capture_output=True, timeout=30,
        )

    @patch("omni_prod.preview_runtime.subprocess.run")
    def test_logs_failure_raises_runtime_error(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="no such container",
        )
        with self.assertRaises(RuntimeError):
            DockerPreviewProvider(workspace=None).logs("cid123")


# ---------------------------------------------------------------------------
# PostgresPreviewRepository -- fake pool/connection/cursor mirroring
# omni_prod/db.py's DatabasePool contract (see module docstring above).
# ---------------------------------------------------------------------------


class _FakeCursor:
    def __init__(self, fetchone_result=None, rowcount=0):
        self.executed = []
        self._fetchone_result = fetchone_result
        self.rowcount = rowcount

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self._fetchone_result

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def transaction(self):
        return _FakeTransaction()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class _FakePool:
    """Mirrors DatabasePool.connection()'s contract: a context manager
    yielding a connection. Not psycopg_pool -- just enough surface for
    PostgresPreviewRepository to run its real SQL-building/parsing logic."""

    def __init__(self, cursor: _FakeCursor):
        self._conn = _FakeConnection(cursor)

    def connection(self):
        return self._conn


class TestPostgresPreviewRepositoryCreate(unittest.TestCase):
    def test_uses_make_interval_not_the_invalid_string_concat_form(self):
        cur = _FakeCursor()
        repo = PostgresPreviewRepository(_FakePool(cur))
        repo.create("prv_1", "proj_1", "ver_1", ttl_seconds=3600)

        self.assertEqual(len(cur.executed), 1)
        sql, params = cur.executed[0]
        # This is the exact bug caught and fixed while writing this file:
        # `now() + (%s || ' seconds')::interval` is invalid Postgres
        # (integer || text). make_interval(secs => %s) is the fix.
        self.assertIn("make_interval", sql)
        self.assertNotIn("||", sql)
        self.assertEqual(params, ("prv_1", "proj_1", "ver_1", 3600))

    def test_rejects_non_positive_ttl_without_touching_the_pool(self):
        cur = _FakeCursor()
        repo = PostgresPreviewRepository(_FakePool(cur))
        with self.assertRaises(ValueError):
            repo.create("prv_1", "proj_1", "ver_1", ttl_seconds=0)
        with self.assertRaises(ValueError):
            repo.create("prv_1", "proj_1", "ver_1", ttl_seconds=-5)
        self.assertEqual(cur.executed, [])


class TestPostgresPreviewRepositoryUpdateStatus(unittest.TestCase):
    def test_valid_status_transition_executes_update(self):
        cur = _FakeCursor()
        repo = PostgresPreviewRepository(_FakePool(cur))
        repo.update_status("prv_1", "RUNNING", url="http://localhost:5555", container_id="cid1")

        self.assertEqual(len(cur.executed), 1)
        sql, params = cur.executed[0]
        self.assertIn("UPDATE project_previews", sql)
        self.assertEqual(params, ("RUNNING", "http://localhost:5555", "cid1", None, "prv_1"))

    def test_invalid_status_rejected_without_touching_the_pool(self):
        cur = _FakeCursor()
        repo = PostgresPreviewRepository(_FakePool(cur))
        with self.assertRaises(ValueError):
            repo.update_status("prv_1", "NOT_A_REAL_STATUS")
        self.assertEqual(cur.executed, [])

    def test_failure_transition_carries_error_message(self):
        cur = _FakeCursor()
        repo = PostgresPreviewRepository(_FakePool(cur))
        repo.update_status("prv_1", "FAILED", error="docker run failed (exit 1): boom")
        _sql, params = cur.executed[0]
        self.assertEqual(params, ("FAILED", None, None, "docker run failed (exit 1): boom", "prv_1"))


class TestPostgresPreviewRepositoryGet(unittest.TestCase):
    def test_parses_row_into_dict_and_scopes_by_project_id(self):
        from datetime import datetime, timezone

        row = (
            "prv_1", "proj_1", "ver_1", "RUNNING", "http://localhost:5555",
            "cid1", None,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        )
        cur = _FakeCursor(fetchone_result=row)
        repo = PostgresPreviewRepository(_FakePool(cur))

        result = repo.get("prv_1", "proj_1")

        self.assertEqual(result["id"], "prv_1")
        self.assertEqual(result["project_id"], "proj_1")
        self.assertEqual(result["status"], "RUNNING")
        self.assertEqual(result["preview_url"], "http://localhost:5555")
        self.assertEqual(result["internal_container_id"], "cid1")
        self.assertIsNone(result["error_message"])
        self.assertEqual(result["created_at"], "2026-01-01T00:00:00+00:00")

        # access-control: project_id must be part of the WHERE filter, not
        # applied after the fact in Python
        _sql, params = cur.executed[0]
        self.assertEqual(params, ("prv_1", "proj_1"))

    def test_not_found_or_wrong_project_raises_keyerror(self):
        cur = _FakeCursor(fetchone_result=None)
        repo = PostgresPreviewRepository(_FakePool(cur))
        with self.assertRaises(KeyError):
            repo.get("prv_missing", "proj_1")


class TestPostgresPreviewRepositoryMarkExpired(unittest.TestCase):
    def test_returns_rowcount_and_targets_only_running_past_ttl(self):
        cur = _FakeCursor(rowcount=3)
        repo = PostgresPreviewRepository(_FakePool(cur))
        self.assertEqual(repo.mark_expired(), 3)

        sql, _params = cur.executed[0]
        self.assertIn("status = 'EXPIRED'", sql)
        self.assertIn("status = 'RUNNING'", sql)
        self.assertIn("expires_at < now()", sql)

    def test_returns_zero_when_nothing_expired(self):
        cur = _FakeCursor(rowcount=0)
        repo = PostgresPreviewRepository(_FakePool(cur))
        self.assertEqual(repo.mark_expired(), 0)


if __name__ == "__main__":
    unittest.main()

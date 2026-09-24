from __future__ import annotations
import json
import re
import socket
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Protocol

from .repository_patch import normalize_repo_path

DEFAULT_PORT = 8000
_CONTAINER_NAME_SAFE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')


class PreviewProvider(Protocol):
    def start(self, *, preview_id: str, project_id: str, version_id: str, repository: dict[str, str]) -> tuple[str, str]:
        """Returns (container_id, url)."""
        ...

    def stop(self, container_id: str) -> None: ...

    def logs(self, container_id: str, tail: int = 50) -> str: ...


def _parse_start_command(repository: dict[str, str]) -> tuple[list[str], int]:
    """Reads `start`/`port` from .omni/project.json.

    Deliberately separate from ProjectManifest (build/verify only, used by
    the build sandbox) rather than extending it -- previews are a distinct
    lifecycle from the build/verify gate, and this keeps ProjectManifest's
    existing contract and every one of its current callers untouched.
    """
    raw = repository.get('.omni/project.json')
    if raw is None:
        raise ValueError('generated repository missing .omni/project.json')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError('invalid .omni/project.json') from exc
    if not isinstance(data, dict):
        raise ValueError('project manifest root must be object')

    start = data.get('start')
    if not start or not isinstance(start, list) or not all(isinstance(x, str) for x in start):
        raise ValueError('no start command in .omni/project.json -- cannot preview a repository with nothing to run')

    port = data.get('port', DEFAULT_PORT)
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValueError(f'invalid port in .omni/project.json: {port!r}')

    return list(start), port


def _materialize_repository(root: Path, repository: dict[str, str]) -> None:
    for rel, content in repository.items():
        safe = normalize_repo_path(rel)
        path = root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def _free_host_port() -> int:
    # Bind to port 0 and let the OS assign a free ephemeral port, then
    # release it immediately so `docker run -p {port}:...` can bind it.
    # Same well-known approach used by most local dev tooling; there is an
    # inherent (small) TOCTOU race between release and docker's bind, which
    # is unavoidable without asking Docker to pick the port itself -- and
    # letting Docker pick (`-p 0:{port}`) then requires a second `docker
    # port` call to discover what it chose, which is no more race-free and
    # strictly more moving parts, and directly deviates from the paste-only
    # instruction. Documented here rather than left implicit.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class DockerPreviewProvider:
    """M3 real running-preview provider. Build sandbox and preview runtime
    are intentionally separate: this never touches omni_prod/sandbox.py's
    lockdown flags (network none, read-only root, etc.) because a preview
    has to actually serve HTTP -- weakening the build sandbox to make
    previews work is explicitly what the master directive prohibits."""

    def __init__(self, *, workspace, image_env_default: str = 'omni-preview:latest'):
        self.workspace = workspace

    def start(self, *, preview_id: str, project_id: str, version_id: str, repository: dict[str, str] | None = None) -> tuple[str, str]:
        if repository is None:
            version = self.workspace.get(project_id=project_id, version_id=version_id)
            repository = version.repository()

        start_cmd, port = _parse_start_command(repository)
        host_port = _free_host_port()

        container_name = f"omni-preview-{preview_id}"
        if not _CONTAINER_NAME_SAFE.match(container_name):
            raise ValueError('unsafe preview id for container name')

        # NOT `with tempfile.TemporaryDirectory() as td:` -- `docker run -d`
        # returns as soon as the container is created, while the container
        # keeps running afterward with this directory bind-mounted into it.
        # A TemporaryDirectory context manager deletes the host directory the
        # moment this function returns, out from under the still-running
        # container -- every preview would start, then fail the instant the
        # app inside tried to read a source file. mkdtemp() persists past
        # this call; it is intentionally not cleaned up here. stop() removes
        # the container but currently leaves this directory on disk -- see
        # PATCH_APPLICATION_REPORT.md; cleaning it up needs the temp dir
        # path threaded through to stop(), which is a repository/DB-layer
        # change (storing it alongside container_id) not asked for here.
        root = Path(tempfile.mkdtemp(prefix=f'omni-preview-{preview_id}-'))
        _materialize_repository(root, repository)

        argv = [
            'docker', 'run', '-d',
            '--name', container_name,
            '-p', f'{host_port}:{port}',
            '--mount', f'type=bind,src={root},dst=/workspace,readonly',
            '--workdir', '/workspace',
            *start_cmd,
        ]
        result = subprocess.run(argv, text=True, capture_output=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f'docker run failed (exit {result.returncode}): {result.stderr.strip()}')

        container_id = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ''
        if not container_id:
            raise RuntimeError('docker run succeeded but produced no container id on stdout')

        url = f'http://localhost:{host_port}'
        return container_id, url

    def stop(self, container_id: str) -> None:
        result = subprocess.run(['docker', 'rm', '-f', container_id], text=True, capture_output=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f'docker rm failed (exit {result.returncode}): {result.stderr.strip()}')

    def logs(self, container_id: str, tail: int = 50) -> str:
        result = subprocess.run(
            ['docker', 'logs', '--tail', str(tail), container_id],
            text=True, capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f'docker logs failed (exit {result.returncode}): {result.stderr.strip()}')
        return (result.stdout or '') + (result.stderr or '')

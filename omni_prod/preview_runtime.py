from __future__ import annotations

"""M3 Revision 2: real running-preview runtime.

Separate lifecycle from the build sandbox (omni_prod/sandbox.py /
sandbox_executor.py): a preview has to actually serve HTTP, so it cannot reuse
the build sandbox's `--network none` lockdown -- and weakening the build
sandbox to make previews work is exactly what the master directive prohibits.
What a preview container gets instead is its own fixed resource/privilege
envelope (see `SECURITY_FLAGS`), a read-only root filesystem, a read-only
source mount, a small `/tmp` tmpfs, a non-root user, and a host port that
Docker allocates itself, bound to a configurable interface (loopback by
default) rather than every interface on the host.

Everything that decides *what* runs lives in pure functions
(`parse_preview_contract`, `build_run_argv`, `external_preview_url`,
`wait_until_healthy`) so it is unit-testable without a Docker daemon; the
`DockerPreviewProvider` class is the thin subprocess layer around them.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import urlsplit

from .repository_patch import normalize_repo_path

PREVIEW_SCHEMA_VERSION = 2

# Explicit image allowlist. `runtime` comes from an AI-generated manifest, so
# it is untrusted input: without an allowlist a generated repository could
# name any image on any registry and the worker host would pull and run it.
# Overridable (comma-separated) via OMNI_PREVIEW_ALLOWED_RUNTIMES for
# operators who pre-build hardened images of their own.
DEFAULT_ALLOWED_RUNTIMES: tuple[str, ...] = ('python:3.11-slim', 'node:20-slim')

# Exactly the flags the M3 Rev2 directive requires, in a fixed order, plus a
# non-root user. `--tmpfs /tmp` gives the app writable scratch space while the
# root filesystem stays read-only.
SECURITY_FLAGS: tuple[str, ...] = (
    '--cpus=0.5',
    '--memory=512m',
    '--pids-limit=64',
    '--read-only',
    '--cap-drop=ALL',
    '--security-opt=no-new-privileges',
    # mode=1777 is required, not cosmetic: without it Docker's tmpfs is not
    # writable by the non-root user below (verified against a live daemon --
    # PermissionError on the first write to /tmp).
    '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
    # Not in the directive's list; added because every other flag above
    # constrains a *root* process. The build sandbox already runs non-root
    # (tests/test_v21_gemini_remediation.py asserts it); the preview runtime
    # should not be the weaker of the two. 65534 = nobody.
    '--user', '65534:65534',
)

PREVIEW_WORKDIR_PREFIX = 'omni-preview-'
_CONTAINER_NAME_SAFE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')
_HEALTH_PATH_SAFE = re.compile(r'^/[A-Za-z0-9._~!$&\'()*+,;=:@%/?-]{0,255}$')
_LOCAL_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1', '[::1]', ''}


class NotPreviewable(ValueError):
    """The repository cannot satisfy the preview runtime contract.

    A deterministic property of the artifact, not a runtime failure -- the
    API returns it as 422 NOT_PREVIEWABLE and the worker persists it as the
    NOT_PREVIEWABLE terminal status, never as FAILED and never as RUNNING."""


class PreviewBackendUnavailable(RuntimeError):
    """The deployment cannot run previews correctly (API -> 503)."""


@dataclass(frozen=True)
class PreviewContract:
    runtime: str
    start: tuple[str, ...]
    port: int
    health_path: str


@dataclass(frozen=True)
class StartedPreview:
    container_id: str
    host_port: int | None  # None: the container exited before its port was published
    workdir: str
    contract: PreviewContract


@dataclass(frozen=True)
class HealthResult:
    ok: bool
    detail: str
    attempts: int


@dataclass(frozen=True)
class WebSaaSAcceptancePlan:
    product_family: str
    required_kinds: tuple[str, ...]
    personas: tuple[dict, ...]


def allowed_runtimes() -> tuple[str, ...]:
    raw = os.getenv('OMNI_PREVIEW_ALLOWED_RUNTIMES', '').strip()
    if not raw:
        return DEFAULT_ALLOWED_RUNTIMES
    return tuple(x.strip() for x in raw.split(',') if x.strip())


def parse_preview_contract(repository: dict[str, str], *,
                           allowed: tuple[str, ...] | None = None) -> PreviewContract:
    """Reads the schema_version 2 preview contract from .omni/project.json.

    Deliberately separate from ProjectManifest (build/verify only, shared by
    the build sandbox, quality gate and security scan) so that contract --
    and every one of its callers -- stays untouched. ProjectManifest ignores
    unknown keys, so the extra preview keys coexist in the same file."""
    allowed = allowed if allowed is not None else allowed_runtimes()
    raw = repository.get('.omni/project.json')
    if raw is None:
        raise NotPreviewable('repository has no .omni/project.json')
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NotPreviewable('invalid .omni/project.json') from exc
    if not isinstance(data, dict):
        raise NotPreviewable('.omni/project.json root must be an object')

    version = data.get('schema_version')
    if type(version) is not int or version != PREVIEW_SCHEMA_VERSION:
        raise NotPreviewable(
            f'preview contract requires schema_version {PREVIEW_SCHEMA_VERSION}, got {version!r}')

    runtime = data.get('runtime')
    if not isinstance(runtime, str) or runtime not in allowed:
        raise NotPreviewable(f'runtime {runtime!r} is not an allowed preview runtime {list(allowed)}')

    start = data.get('start')
    if (not isinstance(start, list) or not start or len(start) > 64
            or not all(isinstance(x, str) and x and '\x00' not in x for x in start)):
        raise NotPreviewable('start must be a non-empty argv array of strings')

    port = data.get('port')
    if type(port) is not int or not (1 <= port <= 65535):
        raise NotPreviewable(f'port must be an integer 1-65535, got {port!r}')

    health_path = data.get('health_path', '/')
    if (not isinstance(health_path, str) or not _HEALTH_PATH_SAFE.match(health_path)
            or health_path.startswith('//') or '..' in health_path):
        raise NotPreviewable(f'health_path must be an absolute URL path, got {health_path!r}')

    return PreviewContract(runtime=runtime, start=tuple(start), port=port, health_path=health_path)


def parse_web_saas_acceptance_plan(repository: dict[str, str]) -> WebSaaSAcceptancePlan | None:
    """Read the generated, domain-neutral behavioral test plan.

    Absence is allowed for legacy/non-SaaS artifacts, but such a preview can
    never become release-eligible through M5 Task 11.  Malformed plans fail
    closed because they would otherwise create false behavioral evidence.
    """
    raw = repository.get('.omni/project.json')
    if raw is None:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NotPreviewable('invalid .omni/project.json') from exc
    block = data.get('web_saas_acceptance') if isinstance(data, dict) else None
    if block is None:
        return None
    if not isinstance(block, dict):
        raise NotPreviewable('web_saas_acceptance must be an object')
    family = str(block.get('product_family') or '').strip()
    if not family:
        raise NotPreviewable('web_saas_acceptance.product_family is required')
    if family != 'managed_web_saas_v1':
        raise NotPreviewable(f'unsupported web_saas_acceptance.product_family {family!r}')
    kinds = block.get('required_kinds')
    if not isinstance(kinds, list) or not kinds or not all(isinstance(x, str) and x.strip() for x in kinds):
        raise NotPreviewable('web_saas_acceptance.required_kinds must be a non-empty string array')
    personas = block.get('personas')
    if not isinstance(personas, list) or not personas or not all(isinstance(x, dict) for x in personas):
        raise NotPreviewable('web_saas_acceptance.personas must be a non-empty object array')
    return WebSaaSAcceptancePlan(
        product_family=family,
        required_kinds=tuple(dict.fromkeys(x.strip() for x in kinds)),
        personas=tuple(dict(x) for x in personas),
    )


def container_name(preview_id: str) -> str:
    name = f'omni-preview-{preview_id}'
    if not _CONTAINER_NAME_SAFE.match(name):
        raise ValueError('unsafe preview id for container name')
    return name


def build_run_argv(*, preview_id: str, contract: PreviewContract, workdir: str,
                   bind_address: str = '127.0.0.1') -> list[str]:
    """`docker run [SECURITY_FLAGS] -d -p ... --mount ... IMAGE START_CMD`.

    DEVIATION FROM THE LITERAL `-P`: `-P` publishes only ports the *image*
    declares with EXPOSE. python:3.11-slim and node:20-slim declare none, so
    `-P` alone would publish nothing and the follow-up `docker port` would
    fail for every preview. It also binds 0.0.0.0, putting untrusted
    generated code directly on every interface of the worker host, around
    the external routing layer. `-p ADDR::PORT` keeps the property the
    directive actually wants -- Docker allocates the host port itself (no
    bind-then-release TOCTOU), read back with `docker port` -- while
    publishing exactly the contract's port on exactly one interface."""
    return [
        'docker', 'run',
        *SECURITY_FLAGS,
        '-e', 'HOME=/tmp',
        '-e', f'PORT={contract.port}',
        '-e', 'PYTHONDONTWRITEBYTECODE=1', '-e', 'DATA_DIR=/tmp',
        '-d',
        '-p', f'{bind_address}::{contract.port}',
        '--name', container_name(preview_id),
        '--label', f'omni.preview_id={preview_id}',
        '--mount', f'type=bind,src={workdir},dst=/workspace,readonly',
        '--workdir', '/workspace',
        contract.runtime,
        *contract.start,
    ]


def parse_docker_port_output(output: str) -> int:
    """`docker port CID 3000/tcp` -> '127.0.0.1:49153' (one line per binding;
    IPv6 bindings look like '[::]:49153'). Returns the first host port."""
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        _, _, port = line.rpartition(':')
        if port.isdigit() and 0 < int(port) <= 65535:
            return int(port)
    raise RuntimeError(f'could not parse host port from docker port output: {output!r}')


def preview_host_label(preview_id: str) -> str:
    """DNS label for a preview id. Ids are 'prv_<hex>'; '_' is not valid in
    a hostname a public CA will certify, so the URL uses 'prv-<hex>'."""
    return preview_id.replace('_', '-').lower()


def preview_id_from_host_label(label: str) -> str | None:
    """Inverse of preview_host_label for the router; None if not a preview."""
    label = label.strip().lower()
    if not label.startswith('prv-') or not all(c in '0123456789abcdef' for c in label[4:]) or len(label) < 12:
        return None
    return 'prv_' + label[4:]


def external_preview_url(preview_id: str, template: str | None) -> str:
    """Builds the externally routable preview URL from PREVIEW_DOMAIN_TEMPLATE
    (e.g. 'https://{preview_id}.preview.148ai.com'). Never returns a
    localhost/loopback URL: the host port a worker allocates is not
    reachable from a user's browser, and persisting it would be a URL that
    only ever worked on the worker itself."""
    if not template or '{preview_id}' not in template:
        raise PreviewBackendUnavailable(
            'PREVIEW_DOMAIN_TEMPLATE must be set and contain {preview_id}')
    url = template.replace('{preview_id}', preview_host_label(preview_id))
    parts = urlsplit(url)
    if parts.scheme not in {'https', 'http'} or not parts.hostname:
        raise PreviewBackendUnavailable(f'PREVIEW_DOMAIN_TEMPLATE is not an http(s) URL: {template!r}')
    host = parts.hostname.lower()
    if host in _LOCAL_HOSTS or host.startswith('127.') or host.endswith('.localhost'):
        raise PreviewBackendUnavailable('PREVIEW_DOMAIN_TEMPLATE must not point at localhost')
    return url


def preview_frame_source(template: str | None) -> str | None:
    """CSP frame-src value for embedding previews: only the wildcard preview
    host derived from PREVIEW_DOMAIN_TEMPLATE (https://{preview_id}.<domain>)."""
    if not template or not template.startswith('https://{preview_id}.'):
        return None
    rest = template[len('https://{preview_id}.'):]
    host = rest.split('/', 1)[0].split(':', 1)[0].lower()
    if not host or '{' in host or host in _LOCAL_HOSTS or host.endswith('localhost') or '.' not in host:
        return None
    return f'https://*.{host}'


def ensure_durable_workspace(workspace, *, purpose: str = 'Real running preview') -> None:
    """Previews and async builds run in a worker process, possibly on a
    different host from the API. With MemoryProjectWorkspace, a version
    committed in one process does not exist in the other -- the preview
    worker would 404 on every version the API just validated, and an async
    build's result_version_id would name a version the API can never serve.
    Only the S3-backed PostgresProjectWorkspace is shared across
    processes/hosts."""
    from .workspace import PostgresProjectWorkspace
    if not isinstance(workspace, PostgresProjectWorkspace):
        raise PreviewBackendUnavailable(
            f'{purpose} requires OMNI_CREATOR_PERSISTENCE=postgres with durable '
            f'(S3-backed) project storage; this deployment uses {type(workspace).__name__}')


def wait_until_healthy(*, url: str, is_alive: Callable[[], tuple[bool, int | None]],
                       timeout_seconds: float = 30.0, interval_seconds: float = 1.0,
                       http_get: Callable[[str, float], int] | None = None,
                       sleep: Callable[[float], None] = time.sleep,
                       clock: Callable[[], float] = time.monotonic) -> HealthResult:
    """Polls `url` until it answers 2xx/3xx, the container dies, or the
    deadline passes. A container that has exited fails immediately -- no
    point probing a port nothing is listening on for the remaining budget."""
    http_get = http_get or _http_status
    deadline = clock() + timeout_seconds
    attempts = 0
    last = 'no probe attempted'
    while True:
        alive, exit_code = is_alive()
        if not alive:
            return HealthResult(False, f'container exited before becoming healthy (exit code {exit_code})', attempts)
        attempts += 1
        try:
            status = http_get(url, max(0.5, min(5.0, interval_seconds * 2)))
            if 200 <= status < 400:
                return HealthResult(True, f'HTTP {status} from {url}', attempts)
            last = f'HTTP {status} from {url}'
        except Exception as exc:  # connection refused/reset/timeouts while booting
            last = f'{type(exc).__name__}: {exc}'
        if clock() + interval_seconds > deadline:
            return HealthResult(False, f'health probe timed out after {timeout_seconds:g}s; last result: {last}', attempts)
        sleep(interval_seconds)


def _http_status(url: str, timeout: float) -> int:
    req = urlrequest.Request(url, method='GET', headers={'User-Agent': '148ai-preview-probe'})
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return int(resp.status)
    except urlerror.HTTPError as exc:  # 4xx/5xx still means "something answered"
        return int(exc.code)


def _materialize_repository(root: Path, repository: dict[str, str]) -> None:
    for rel, content in repository.items():
        safe = normalize_repo_path(rel)
        path = root / safe
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')


def _make_world_readable(root: Path) -> None:
    # mkdtemp() creates the directory 0700 owned by the worker's uid. The
    # container runs as uid 65534 with every capability dropped (no
    # CAP_DAC_OVERRIDE), so a 0700 directory owned by anyone else is
    # unreadable inside it and every app would fail on its first file read.
    # Source files are not secret (the user can export them anyway), and the
    # mount is read-only, so read+traverse for others is the minimum needed.
    for dirpath, dirnames, filenames in os.walk(root):
        os.chmod(dirpath, 0o755)
        for name in filenames:
            os.chmod(os.path.join(dirpath, name), 0o644)


def is_managed_workdir(path: str | None) -> bool:
    """True only for directories this module created. remove_workdir() takes
    its path from the database; this check guarantees a corrupted or
    tampered row can never make the worker rmtree an arbitrary path."""
    if not path:
        return False
    p = Path(path).resolve()
    tmp = Path(tempfile.gettempdir()).resolve()
    return p.parent == tmp and p.name.startswith(PREVIEW_WORKDIR_PREFIX)


class PreviewProvider(Protocol):
    def start(self, *, preview_id: str, project_id: str, version_id: str,
              repository: dict[str, str] | None = None) -> StartedPreview: ...
    def is_running(self, container_id: str) -> tuple[bool, int | None]: ...
    def stop(self, container_id: str) -> None: ...
    def logs(self, container_id: str, tail: int = 50) -> str: ...
    def remove_workdir(self, path: str | None) -> bool: ...


class DockerPreviewProvider:
    def __init__(self, *, workspace, bind_address: str | None = None,
                 runner: Callable[..., subprocess.CompletedProcess] | None = None):
        self.workspace = workspace
        self.bind_address = bind_address or os.getenv('OMNI_PREVIEW_BIND_ADDRESS', '127.0.0.1')
        self._runner = runner

    def _run(self, argv: list[str], timeout: int) -> subprocess.CompletedProcess:
        runner = self._runner or subprocess.run
        return runner(argv, text=True, capture_output=True, timeout=timeout)

    def start(self, *, preview_id: str, project_id: str, version_id: str,
              repository: dict[str, str] | None = None) -> StartedPreview:
        if repository is None:
            repository = self.workspace.get(project_id=project_id, version_id=version_id).repository()
        contract = parse_preview_contract(repository)  # NotPreviewable before any side effect
        container_name(preview_id)  # validate before creating anything on disk

        # mkdtemp, not TemporaryDirectory: the detached container keeps using
        # this bind mount after start() returns (see PATCH_APPLICATION_REPORT.md,
        # M3). Its path is persisted (project_previews.workdir_path) and
        # removed by the stop task or by any failure path below.
        root = Path(tempfile.mkdtemp(prefix=f'{PREVIEW_WORKDIR_PREFIX}{preview_id}-'))
        try:
            _materialize_repository(root, repository)
            _make_world_readable(root)
            argv = build_run_argv(preview_id=preview_id, contract=contract, workdir=str(root),
                                  bind_address=self.bind_address)
            result = self._run(argv, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f'docker run failed (exit {result.returncode}): {(result.stderr or "").strip()[:1000]}')
            out = (result.stdout or '').strip()
            container_id = out.splitlines()[-1].strip() if out else ''
            if not container_id:
                raise RuntimeError('docker run succeeded but produced no container id on stdout')
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

        try:
            port_result = self._run(['docker', 'port', container_id, f'{contract.port}/tcp'], timeout=30)
            if port_result.returncode != 0:
                # A container that exits immediately (crash on boot) has its
                # port bindings released, so `docker port` fails with "no
                # public port published". That is the app's failure, not the
                # runtime's: hand the container back with host_port=None so
                # the caller can collect its exit code and logs before
                # teardown (found by the live Docker test -- the first version
                # removed the container here and lost both).
                running, _ = self.is_running(container_id)
                if not running:
                    return StartedPreview(container_id=container_id, host_port=None,
                                          workdir=str(root), contract=contract)
                raise RuntimeError(f'docker port failed (exit {port_result.returncode}): {(port_result.stderr or "").strip()[:500]}')
            host_port = parse_docker_port_output(port_result.stdout or '')
        except Exception:
            self.stop(container_id)
            shutil.rmtree(root, ignore_errors=True)
            raise

        return StartedPreview(container_id=container_id, host_port=host_port, workdir=str(root), contract=contract)

    def is_running(self, container_id: str) -> tuple[bool, int | None]:
        r = self._run(['docker', 'inspect', '-f', '{{.State.Running}} {{.State.ExitCode}}', container_id], timeout=30)
        if r.returncode != 0:
            return False, None
        parts = (r.stdout or '').split()
        running = bool(parts) and parts[0] == 'true'
        code = int(parts[1]) if len(parts) > 1 and parts[1].lstrip('-').isdigit() else None
        return running, code

    def stop(self, container_id: str) -> None:
        r = self._run(['docker', 'rm', '-f', container_id], timeout=30)
        if r.returncode != 0:
            stderr = (r.stderr or '').strip()
            if 'no such container' in stderr.lower():
                return  # already gone: stopping is idempotent
            raise RuntimeError(f'docker rm failed (exit {r.returncode}): {stderr[:500]}')

    def logs(self, container_id: str, tail: int = 50) -> str:
        r = self._run(['docker', 'logs', '--tail', str(int(tail)), container_id], timeout=30)
        if r.returncode != 0:
            raise RuntimeError(f'docker logs failed (exit {r.returncode}): {(r.stderr or "").strip()[:500]}')
        return (r.stdout or '') + (r.stderr or '')

    def remove_workdir(self, path: str | None) -> bool:
        if not is_managed_workdir(path):
            return False
        shutil.rmtree(path, ignore_errors=True)
        return not Path(path).exists()

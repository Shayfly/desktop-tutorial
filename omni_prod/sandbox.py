from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,120}$")

@dataclass(frozen=True)
class SandboxLimits:
    image: str = "omni-sandbox:latest"
    timeout_seconds: int = 180
    memory: str = "1024m"
    cpus: str = "1.5"
    pids: int = 256
    user: str = "10001:10001"
    nofile: int = 1024

@dataclass(frozen=True)
class SandboxResult:
    returncode: int
    stdout: str
    stderr: str

def build_docker_command(
    *,
    source_dir: str | Path,
    build_id: str,
    limits: SandboxLimits,
    command: list[str],
    output_dir: str | Path | None = None,
) -> list[str]:
    if not _SAFE_ID.fullmatch(build_id):
        raise ValueError("unsafe build_id")
    source = Path(source_dir).resolve()
    if not source.is_dir():
        raise ValueError("source_dir must exist and be a directory")
    if not command or any(
        not isinstance(x, str) or "\x00" in x for x in command
    ):
        raise ValueError("invalid command")

    argv = [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--security-opt", "no-new-privileges:true",
        "--cap-drop", "ALL",
        "--user", limits.user,
        "--memory", limits.memory,
        "--memory-swap", limits.memory,
        "--cpus", limits.cpus,
        "--pids-limit", str(limits.pids),
        "--ulimit", f"nofile={limits.nofile}:{limits.nofile}",
        "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=256m",
        "--tmpfs", "/run:rw,noexec,nosuid,nodev,size=32m",
        "--mount", f"type=bind,src={source},dst=/workspace,readonly",
        "--workdir", "/workspace",
        "--hostname", "omni-sandbox",
        "--env", "HOME=/tmp",
        "--name", f"omni-build-{build_id}",
    ]

    if output_dir is not None:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        argv.extend([
            "--mount",
            f"type=bind,src={output},dst=/output,rw",
            "--env",
            "OMNI_OUTPUT_DIR=/output",
        ])

    argv.extend([limits.image, *command])
    return argv

def run_sandbox(
    *,
    source_dir: str | Path,
    build_id: str,
    limits: SandboxLimits,
    command: list[str],
    output_dir: str | Path | None = None,
) -> SandboxResult:
    argv = build_docker_command(
        source_dir=source_dir,
        build_id=build_id,
        limits=limits,
        command=command,
        output_dir=output_dir,
    )
    proc = subprocess.run(
        argv,
        text=True,
        capture_output=True,
        timeout=limits.timeout_seconds,
        check=False,
        env={k:v for k,v in {"PATH": "/usr/bin:/bin", "DOCKER_HOST": __import__("os").environ.get("DOCKER_HOST", ""), "DOCKER_TLS_VERIFY": __import__("os").environ.get("DOCKER_TLS_VERIFY", ""), "DOCKER_CERT_PATH": __import__("os").environ.get("DOCKER_CERT_PATH", "")}.items() if v},
    )
    return SandboxResult(proc.returncode, proc.stdout, proc.stderr)

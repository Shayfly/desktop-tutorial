from __future__ import annotations

import base64
import hashlib
import io
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from uuid import UUID
import zipfile

from .executor import ExecutionResult, UnsafeArtifact, execute_web_artifact, repair_web_artifact, validate_zip
from .runtime_bridge import generate_export
from .store import BuildRecord, ProjectRecord, Store, VersionRecord


def _project_title(prompt: str) -> str:
    compact = re.sub(r"\s+", " ", prompt).strip()
    return (compact[:56] or "My 148AI Product").strip()


Generator = Callable[[str, str, list[str]], bytes]
Executor = Callable[[bytes, int], ExecutionResult]
Repairer = Callable[[bytes, int], bytes | None]


class CustomerService:
    def __init__(
        self,
        store: Store,
        *,
        generator: Generator = generate_export,
        executor: Executor = execute_web_artifact,
        repairer: Repairer = repair_web_artifact,
        artifact_limit_bytes: int = 5 * 1024 * 1024,
        execution_timeout_seconds: int = 15,
    ) -> None:
        self.store = store
        self.generator = generator
        self.executor = executor
        self.repairer = repairer
        self.artifact_limit_bytes = artifact_limit_bytes
        self.execution_timeout_seconds = execution_timeout_seconds

    def ensure_project(self, owner_id: str, prompt: str, project_id: str | None = None) -> ProjectRecord:
        if project_id:
            project = self.store.get_project(project_id, owner_id)
            if not project:
                raise KeyError("project not found")
            return project
        return self.store.create_project(owner_id, _project_title(prompt))

    def start_build(self, owner_id: str, prompt: str, project_id: str | None = None) -> BuildRecord:
        prompt = prompt.strip()
        if len(prompt) < 3:
            raise ValueError("prompt must contain at least 3 characters")
        project = self.ensure_project(owner_id, prompt, project_id)
        build = self.store.create_build(owner_id, project.id, prompt)
        self.store.append_build_event(build.id, "planning", "Preparing product specification")
        return build

    def _stage(self, build_id: str, stage: str, message: str) -> BuildRecord:
        build = self.store.update_build(build_id, stage=stage, status="running", error=None)
        self.store.append_build_event(build_id, stage, message)
        return build

    def _fail(self, build_id: str, error: str) -> BuildRecord:
        safe_error = (error or "Build failed").strip()[:600]
        build = self.store.update_build(build_id, stage="failed", status="failed", error=safe_error)
        self.store.append_build_event(build_id, "failed", safe_error)
        return build

    def build(
        self,
        owner_id: str,
        prompt: str,
        project_id: str | None = None,
        target_markets: list[str] | None = None,
    ) -> BuildRecord:
        build = self.start_build(owner_id, prompt, project_id)
        project = self.store.get_project(build.project_id, owner_id)
        if not project:
            return self._fail(build.id, "Project disappeared during build")
        markets = list(target_markets or [])

        try:
            self._stage(build.id, "generating", "Generating product files")
            blob = self.generator(build.prompt, project.title, markets)
            if not isinstance(blob, (bytes, bytearray)):
                return self._fail(build.id, "Generator returned an invalid artifact")
            blob = bytes(blob)

            self._stage(build.id, "running", "Validating generated artifact")
            try:
                validate_zip(blob, self.artifact_limit_bytes)
            except UnsafeArtifact as exc:
                if "index.html" not in str(exc):
                    return self._fail(build.id, str(exc))
                self._stage(build.id, "repairing", "Repairing generated web entry point")
                repaired = self.repairer(blob, self.artifact_limit_bytes)
                if repaired is None:
                    return self._fail(build.id, str(exc))
                blob = repaired
                self._stage(build.id, "running", "Re-validating repaired artifact")
                validate_zip(blob, self.artifact_limit_bytes)

            self._stage(build.id, "testing", "Running executable validation")
            result = self.executor(blob, self.execution_timeout_seconds)
            if not result.ok:
                return self._fail(build.id, result.error or "Generated artifact did not pass execution checks")

            digest = hashlib.sha256(blob).hexdigest()
            artifact = self.store.create_artifact(owner_id, project.id, digest, blob)
            current = self.store.get_project(project.id, owner_id)
            parent_version_id = current.active_version_id if current else None
            version = self.store.create_version(
                owner_id,
                project.id,
                artifact.id,
                build.prompt,
                parent_version_id=parent_version_id,
            )
            self.store.set_active_version(project.id, owner_id, version.id)
            ready = self.store.update_build(
                build.id,
                stage="ready",
                status="ready",
                error=None,
                version_id=version.id,
            )
            self.store.append_build_event(build.id, "ready", "Build passed validation and is ready to preview")
            return ready
        except Exception as exc:
            return self._fail(build.id, f"{type(exc).__name__}: {exc}")

    def list_projects(self, owner_id: str) -> list[ProjectRecord]:
        return self.store.list_projects(owner_id)

    def list_versions(self, owner_id: str, project_id: str) -> list[VersionRecord]:
        if not self.store.get_project(project_id, owner_id):
            raise KeyError("project not found")
        return self.store.list_versions(project_id, owner_id)

    def get_build(self, owner_id: str, build_id: str) -> tuple[BuildRecord, list]:
        build = self.store.get_build(build_id, owner_id)
        if not build:
            raise KeyError("build not found")
        return build, self.store.get_build_event_records(build.id)

    def _owned_version(self, owner_id: str, project_id: str, version_id: str) -> VersionRecord:
        project = self.store.get_project(project_id, owner_id)
        if not project:
            raise KeyError("project not found")
        version = self.store.get_version(version_id, owner_id)
        if not version or version.project_id != project.id:
            raise KeyError("version not found")
        return version

    def restore_version(self, owner_id: str, project_id: str, version_id: str) -> ProjectRecord:
        self._owned_version(owner_id, project_id, version_id)
        return self.store.set_active_version(project_id, owner_id, version_id)

    def export_version(self, owner_id: str, project_id: str, version_id: str) -> bytes:
        version = self._owned_version(owner_id, project_id, version_id)
        artifact = self.store.get_artifact(version.artifact_id, owner_id)
        if not artifact or artifact.project_id != project_id:
            raise KeyError("artifact not found")
        validate_zip(artifact.data, self.artifact_limit_bytes)
        return artifact.data

    def create_preview_handle(self, owner_id: str, project_id: str, version_id: str) -> str:
        version = self._owned_version(owner_id, project_id, version_id)
        artifact = self.store.get_artifact(version.artifact_id, owner_id)
        if not artifact or artifact.project_id != project_id:
            raise KeyError("artifact not found")
        validate_zip(artifact.data, self.artifact_limit_bytes)
        raw = UUID(version.id).bytes + UUID(artifact.id).bytes
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def preview_asset(self, preview_id: str, path: str | None = None) -> tuple[bytes, str]:
        try:
            raw = base64.urlsafe_b64decode(preview_id + "=" * (-len(preview_id) % 4))
            if len(raw) != 32:
                raise ValueError("invalid preview handle length")
            version_id = str(UUID(bytes=raw[:16]))
            artifact_id = str(UUID(bytes=raw[16:]))
        except Exception as exc:
            raise KeyError("preview not found") from exc

        version = self.store.get_version(version_id)
        if not version or version.artifact_id != artifact_id:
            raise KeyError("preview not found")
        artifact = self.store.get_artifact(artifact_id)
        if not artifact or artifact.project_id != version.project_id:
            raise KeyError("preview not found")
        validate_zip(artifact.data, self.artifact_limit_bytes)

        requested = (path or "index.html").replace("\\", "/").lstrip("/") or "index.html"
        posix = PurePosixPath(requested)
        if posix.is_absolute() or ".." in posix.parts:
            raise KeyError("preview asset not found")
        requested = str(posix)
        try:
            with zipfile.ZipFile(io.BytesIO(artifact.data), "r") as archive:
                data = archive.read(requested)
        except (KeyError, zipfile.BadZipFile) as exc:
            raise KeyError("preview asset not found") from exc
        return data, requested

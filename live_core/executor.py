from __future__ import annotations

from dataclasses import dataclass
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import zipfile


class UnsafeArtifact(RuntimeError):
    pass


@dataclass(frozen=True)
class ArtifactManifest:
    entrypoint: str
    files: tuple[str, ...]
    total_uncompressed_bytes: int


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    entrypoint: str | None
    checked_js: int
    error: str | None


def _safe_member_name(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or normalized.startswith("/") or path.is_absolute() or ".." in path.parts:
        raise UnsafeArtifact(f"unsafe archive path: {name!r}")
    return str(path)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _inspect_zip(blob: bytes, max_bytes: int, *, require_index: bool) -> tuple[list[zipfile.ZipInfo], int]:
    if not isinstance(blob, (bytes, bytearray)) or not blob:
        raise UnsafeArtifact("artifact is empty")
    if len(blob) > max_bytes:
        raise UnsafeArtifact(f"artifact exceeds {max_bytes} byte limit")
    try:
        archive = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as exc:
        raise UnsafeArtifact("artifact is not a valid ZIP") from exc

    infos: list[zipfile.ZipInfo] = []
    total = 0
    names: set[str] = set()
    try:
        bad = archive.testzip()
        if bad:
            raise UnsafeArtifact(f"artifact ZIP CRC failure: {bad}")
        for info in archive.infolist():
            safe_name = _safe_member_name(info.filename)
            if _is_symlink(info):
                raise UnsafeArtifact(f"symlinks are not allowed: {safe_name}")
            total += int(info.file_size)
            if total > max_bytes:
                raise UnsafeArtifact(f"expanded artifact exceeds {max_bytes} byte limit")
            infos.append(info)
            if not info.is_dir():
                names.add(safe_name)
    finally:
        archive.close()
    if require_index and "index.html" not in names:
        raise UnsafeArtifact("generated web artifact requires index.html")
    return infos, total


def validate_zip(blob: bytes, max_bytes: int) -> ArtifactManifest:
    infos, total = _inspect_zip(blob, max_bytes, require_index=True)
    files = tuple(sorted(_safe_member_name(i.filename) for i in infos if not i.is_dir()))
    return ArtifactManifest(entrypoint="index.html", files=files, total_uncompressed_bytes=total)


def repair_web_artifact(blob: bytes, max_bytes: int) -> bytes | None:
    """Apply only narrow deterministic repairs; never repair unsafe archives."""
    infos, _ = _inspect_zip(blob, max_bytes, require_index=False)
    safe_files = [_safe_member_name(i.filename) for i in infos if not i.is_dir()]
    if "index.html" in safe_files:
        return bytes(blob)
    html_files = [name for name in safe_files if name.lower().endswith((".html", ".htm"))]
    if len(html_files) != 1:
        return None

    source_name = html_files[0]
    source = io.BytesIO(blob)
    output = io.BytesIO()
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.is_dir():
                continue
            safe_name = _safe_member_name(info.filename)
            data = src.read(info)
            dst.writestr(safe_name, data)
        dst.writestr("index.html", src.read(source_name))
    repaired = output.getvalue()
    validate_zip(repaired, max_bytes)
    return repaired


def _extract_verified(blob: bytes, root: Path, max_bytes: int) -> ArtifactManifest:
    manifest = validate_zip(blob, max_bytes)
    with zipfile.ZipFile(io.BytesIO(blob), "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            safe_name = _safe_member_name(info.filename)
            target = (root / safe_name).resolve()
            if root.resolve() not in target.parents and target != root.resolve():
                raise UnsafeArtifact(f"archive escaped extraction root: {safe_name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    return manifest


def execute_web_artifact(blob: bytes, timeout_seconds: int) -> ExecutionResult:
    max_bytes = 5 * 1024 * 1024
    try:
        with tempfile.TemporaryDirectory(prefix="148ai-build-") as tmp:
            root = Path(tmp)
            manifest = _extract_verified(blob, root, max_bytes)
            index = root / manifest.entrypoint
            try:
                html = index.read_text("utf-8")
            except UnicodeDecodeError:
                return ExecutionResult(False, manifest.entrypoint, 0, "index.html is not valid UTF-8")
            if not html.strip():
                return ExecutionResult(False, manifest.entrypoint, 0, "index.html is empty")

            js_files = [root / name for name in manifest.files if name.lower().endswith((".js", ".mjs", ".cjs"))]
            node = shutil.which("node")
            if js_files and not node:
                return ExecutionResult(False, manifest.entrypoint, 0, "JavaScript validation unavailable: node is not installed")

            checked = 0
            for js_file in js_files:
                try:
                    proc = subprocess.run(
                        [node, "--check", str(js_file)],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        timeout=max(1, int(timeout_seconds)),
                        env={"PATH": os.environ.get("PATH", "")},
                        check=False,
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(False, manifest.entrypoint, checked, "JavaScript syntax validation timed out")
                checked += 1
                if proc.returncode != 0:
                    detail = (proc.stderr or proc.stdout or "syntax error").strip()
                    return ExecutionResult(False, manifest.entrypoint, checked, f"JavaScript syntax check failed: {detail[:500]}")

            return ExecutionResult(True, manifest.entrypoint, checked, None)
    except UnsafeArtifact as exc:
        return ExecutionResult(False, None, 0, str(exc))
    except Exception as exc:
        return ExecutionResult(False, None, 0, f"artifact execution failed: {type(exc).__name__}: {exc}")

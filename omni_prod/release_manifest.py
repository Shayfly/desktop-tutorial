from __future__ import annotations
from pathlib import Path
import hashlib
import json

DEFAULT_EXCLUDES = {"__pycache__", ".git", ".pytest_cache"}

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_release_manifest(
    root: str | Path,
    *,
    version: str,
    test_count: int,
    excluded_parts: set[str] | None = None,
) -> dict:
    base = Path(root)
    excludes = excluded_parts or DEFAULT_EXCLUDES
    files = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        if any(part in excludes for part in path.parts):
            continue
        rel = path.relative_to(base).as_posix()
        if rel == "RELEASE-MANIFEST.json":
            continue
        files[rel] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return {
        "schema": 1,
        "version": version,
        "test_count": test_count,
        "files": files,
    }

def write_release_manifest(root: str | Path, *, version: str, test_count: int) -> Path:
    base = Path(root)
    manifest = build_release_manifest(base, version=version, test_count=test_count)
    path = base / "RELEASE-MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return path

def verify_release_manifest(root: str | Path) -> tuple[bool, list[str]]:
    base = Path(root)
    manifest_path = base / "RELEASE-MANIFEST.json"
    if not manifest_path.exists():
        return False, ["RELEASE-MANIFEST.json missing"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    recorded = manifest.get("files", {})
    for rel, meta in recorded.items():
        path = base / rel
        if not path.exists():
            errors.append(f"missing file: {rel}")
            continue
        if path.stat().st_size != meta["size"]:
            errors.append(f"size mismatch: {rel}")
        if sha256_file(path) != meta["sha256"]:
            errors.append(f"checksum mismatch: {rel}")
    # Detect unrecorded files, except the manifest itself and excluded runtime caches.
    current = build_release_manifest(
        base,
        version=str(manifest.get("version", "")),
        test_count=int(manifest.get("test_count", 0)),
    )["files"]
    extra = sorted(set(current) - set(recorded))
    for rel in extra:
        errors.append(f"unrecorded file: {rel}")
    return not errors, errors

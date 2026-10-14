from __future__ import annotations
from pathlib import Path
import hashlib
import json

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_backup_manifest(root: str | Path) -> dict:
    base = Path(root)
    files = {}
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.name == "BACKUP-MANIFEST.json":
            continue
        rel = path.relative_to(base).as_posix()
        files[rel] = {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    return {"schema": 1, "files": files}

def write_backup_manifest(root: str | Path) -> Path:
    base = Path(root)
    out = base / "BACKUP-MANIFEST.json"
    out.write_text(
        json.dumps(build_backup_manifest(base), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return out

def verify_backup_manifest(root: str | Path) -> tuple[bool, list[str]]:
    base = Path(root)
    manifest_path = base / "BACKUP-MANIFEST.json"
    if not manifest_path.exists():
        return False, ["BACKUP-MANIFEST.json missing"]
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    recorded = data.get("files", {})
    for rel, meta in recorded.items():
        path = base / rel
        if not path.exists():
            errors.append(f"missing: {rel}")
            continue
        if path.stat().st_size != meta["size"]:
            errors.append(f"size mismatch: {rel}")
        if sha256_file(path) != meta["sha256"]:
            errors.append(f"checksum mismatch: {rel}")
    current = build_backup_manifest(base)["files"]
    for rel in sorted(set(current) - set(recorded)):
        errors.append(f"unrecorded: {rel}")
    return not errors, errors

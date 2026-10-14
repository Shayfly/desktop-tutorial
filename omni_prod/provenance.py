from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

@dataclass(frozen=True)
class ArtifactProvenance:
    sha256: str
    size: int
    project_id: str
    version_id: str
    build_id: str

def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_manifest(path: str | Path, *, project_id: str, version_id: str,
                   build_id: str) -> dict:
    p = Path(path)
    return {
        "schema": 1,
        "artifact": {
            "filename": p.name,
            "sha256": file_sha256(p),
            "size": p.stat().st_size,
        },
        "project_id": project_id,
        "version_id": version_id,
        "build_id": build_id,
    }

def write_manifest(path: str | Path, destination: str | Path, **ids) -> Path:
    manifest = build_manifest(path, **ids)
    out = Path(destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return out

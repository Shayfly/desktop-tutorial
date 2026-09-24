from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

_NAME = re.compile(r"^(?P<version>\d{3,})_(?P<name>[a-z0-9_]+)\.sql$")

@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    sha256: str
    sql: str

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def discover_migrations(directory: str | Path) -> list[Migration]:
    root = Path(directory)
    found: list[Migration] = []
    for path in sorted(root.glob("*.sql")):
        m = _NAME.fullmatch(path.name)
        if not m:
            raise ValueError(f"invalid migration filename: {path.name}")
        raw = path.read_bytes()
        sql = raw.decode("utf-8")
        if not sql.strip():
            raise ValueError(f"empty migration: {path.name}")
        found.append(Migration(
            version=int(m.group("version")),
            name=m.group("name"),
            path=path,
            sha256=_sha256_bytes(raw),
            sql=sql,
        ))
    versions = [m.version for m in found]
    if len(versions) != len(set(versions)):
        raise ValueError("duplicate migration version")
    if versions != sorted(versions):
        raise ValueError("migrations are not ordered")
    return found

def verify_applied(
    migrations: list[Migration],
    applied: dict[int, str],
) -> None:
    by_version = {m.version: m for m in migrations}
    for version, recorded_sha in applied.items():
        current = by_version.get(version)
        if current is None:
            raise RuntimeError(f"applied migration missing from package: {version}")
        if current.sha256 != recorded_sha:
            raise RuntimeError(f"migration checksum drift detected: {version}")

def pending_migrations(
    migrations: list[Migration],
    applied: dict[int, str],
) -> list[Migration]:
    verify_applied(migrations, applied)
    return [m for m in migrations if m.version not in applied]

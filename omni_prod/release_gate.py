from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .migrations import discover_migrations
from .release_manifest import verify_release_manifest
from .secret_scan import scan_tree

@dataclass(frozen=True)
class GateResult:
    ok: bool
    checks: dict[str, bool]
    errors: tuple[str, ...]

def evaluate_release_gate(root: str | Path) -> GateResult:
    base = Path(root)
    checks: dict[str, bool] = {}
    errors: list[str] = []

    # Migration package validity
    try:
        migrations = discover_migrations(base / "infra/postgres")
        checks["migrations_valid"] = len(migrations) > 0
        if not migrations:
            errors.append("no migrations found")
    except Exception as exc:
        checks["migrations_valid"] = False
        errors.append(f"migration validation failed: {exc}")

    # Secret scanning on deployable content only
    findings = scan_tree(base)
    checks["no_embedded_secrets"] = len(findings) == 0
    for f in findings:
        errors.append(f"secret finding {f.kind} at {f.path}:{f.line}")

    # Release manifest
    manifest_ok, manifest_errors = verify_release_manifest(base)
    checks["release_manifest_valid"] = manifest_ok
    errors.extend(manifest_errors)

    return GateResult(ok=all(checks.values()), checks=checks, errors=tuple(errors))

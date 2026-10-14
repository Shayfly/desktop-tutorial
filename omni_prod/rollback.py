from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class DeploymentSnapshot:
    deployment_id: str
    project_id: str
    version_id: str
    build_id: str
    environment: str
    artifact_key: str

def choose_rollback_target(
    history: list[DeploymentSnapshot],
    *,
    current_deployment_id: str,
) -> DeploymentSnapshot:
    """
    History must be newest-first. Returns the first prior immutable deployment.
    """
    seen_current = False
    for item in history:
        if not seen_current:
            if item.deployment_id == current_deployment_id:
                seen_current = True
            continue
        return item
    if not seen_current:
        raise KeyError("current deployment not found")
    raise LookupError("no previous deployment available")

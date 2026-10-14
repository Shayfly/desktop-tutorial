from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class BuildStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(frozen=True)
class BuildJob:
    id: str
    project_id: str
    version_id: str
    status: BuildStatus
    created_at: datetime
    artifact_key: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None

@dataclass(frozen=True)
class Deployment:
    id: str
    project_id: str
    version_id: str
    build_id: str
    environment: str
    artifact_key: str
    created_at: datetime
    retired_at: Optional[datetime] = None

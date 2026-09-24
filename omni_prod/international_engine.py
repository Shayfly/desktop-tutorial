from __future__ import annotations
from dataclasses import dataclass
from .autonomous_core import AutonomousProductEngine, AutonomousResult
from .quality_gate import QualityAssessment, assess_repository
from .security_testing import SecurityReport, hostile_repository_scan

@dataclass(frozen=True)
class InternationalBuildResult:
    core: AutonomousResult
    quality: QualityAssessment
    security: SecurityReport
    release_ready: bool

class InternationalProductEngine:
    """Release-gated wrapper around the autonomous core.

    A build is not considered release-ready merely because acceptance tests pass.
    It must also clear static security and a configurable quality threshold.
    """
    def __init__(self, core: AutonomousProductEngine, *, minimum_quality: int=80):
        self.core=core; self.minimum_quality=minimum_quality
    def build(self, prompt: str) -> InternationalBuildResult:
        result=self.core.build(prompt)
        quality=assess_repository(spec=result.spec,repository=result.repository,minimum_score=self.minimum_quality)
        security=hostile_repository_scan(result.repository)
        ready=result.status=='ready' and quality.passed and security.passed
        return InternationalBuildResult(result,quality,security,ready)

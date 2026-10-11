"""Safe standalone deployment verifier; integration requires explicit approval."""
from .models import CheckStatus, ErrorClass, ExecutionMode, RunConfig, VerificationResult, Verdict
from .runner import run_postdeploy_checks

__all__ = ("run_postdeploy_checks", "RunConfig", "VerificationResult", "Verdict", "CheckStatus", "ErrorClass", "ExecutionMode")

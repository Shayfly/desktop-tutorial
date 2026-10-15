"""Cross-platform scratch directory for host-side probes and acceptance runs."""
from __future__ import annotations

import os
import tempfile

__all__ = ["scratch_root"]


def scratch_root() -> str:
    return os.environ.get("OMNI_SCRATCH_DIR") or tempfile.gettempdir()

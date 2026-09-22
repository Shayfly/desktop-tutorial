from __future__ import annotations
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME_ZIP = ROOT / "omni_prod_runtime.zip"
RUNTIME_DIR = Path("/tmp/148ai_v28_runtime")
MARKER = RUNTIME_DIR / ".ready"

if not MARKER.exists():
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(RUNTIME_ZIP, "r") as zf:
        zf.extractall(RUNTIME_DIR)
    MARKER.write_text("148AI V28", encoding="utf-8")

sys.path.insert(0, str(RUNTIME_DIR))

# Vercel review mode: use the real V28 runtime with in-memory persistence.
# Production PostgreSQL/GPU/sandbox are intentionally not claimed as connected.
os.environ.setdefault("OMNI_ENV", "development")
os.environ.setdefault("OMNI_CREATOR_PERSISTENCE", "memory")

from omni_prod.investor_app import app  # noqa: E402,F401

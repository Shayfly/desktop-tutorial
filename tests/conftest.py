"""Test-process defaults.

app.py installs live_core at import time, and live_core refuses to start without
OMNI_DATABASE_URL unless memory persistence is requested by name. The test suite
(including v24-ci, which runs plain `pytest`) imports `from app import app`
without a database, so it asks for memory persistence explicitly here.

setdefault: a job that provides its own value (or a real OMNI_DATABASE_URL) wins.
"""

import os

os.environ.setdefault("OMNI_LIVE_PERSISTENCE", "memory")

"""Async control contract tests."""
import importlib.util
import threading
import time
from pathlib import Path
from unittest.mock import patch
TARGET=Path(__file__).resolve().parents[1]/"services/repo-control/server.py"
spec=importlib.util.spec_from_file_location("repo_async_target",TARGET)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_async_job_persists_after_worker_finishes(tmp_path):
    module.ROOT=tmp_path
    module.JOBS.clear()
    jid=module.launch_job([["python3","-c","print('async ok')"]])
    assert jid
    for _ in range(200):
        with module.JOBS_LOCK:
            status=module.JOBS[jid]["status"]
        if status=="done": break
        time.sleep(.01)
    with module.JOBS_LOCK:
        snapshot=dict(module.JOBS[jid])
    assert snapshot["status"]=="done"
    assert snapshot["result"]["stdout"].strip()=="async ok"
    assert snapshot["result"]["exit_code"]==0

def test_queue_rejects_when_full():
    with module.JOBS_LOCK:
        original=dict(module.JOBS)
        module.JOBS.clear()
        module.JOBS.update({str(n):{"status":"running"} for n in range(module.MAX_JOBS)})
    try:
        assert module.launch_job([["ls"]]) is None
    finally:
        with module.JOBS_LOCK:
            module.JOBS.clear()
            module.JOBS.update(original)

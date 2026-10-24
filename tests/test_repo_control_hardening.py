"""Repo Control hardening: queue accounting, partial output and timeout flags."""
import importlib.util
import threading
import time
from pathlib import Path
from unittest.mock import patch
import pytest

PATH=Path(__file__).resolve().parents[1]/"services/repo-control/server.py"
spec=importlib.util.spec_from_file_location("repo_control_hardening",PATH)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def wait_done(jid,timeout=3):
    stop=time.monotonic()+timeout
    while time.monotonic()<stop:
        with mod.JOBS_LOCK:
            job=dict(mod.JOBS[jid])
        if job["status"]=="done": return job
        time.sleep(.01)
    pytest.fail("job never finished")

def test_queued_wait_does_not_consume_execution_budget(tmp_path):
    mod.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    mod.JOBS.clear()
    entered=threading.Event()
    release=threading.Event()
    def hold():
        with mod.LOCK:
            entered.set()
            release.wait(2)
    holder=threading.Thread(target=hold)
    holder.start()
    original=mod.JOB_TIMEOUT
    try:
        assert entered.wait(1)
        mod.JOB_TIMEOUT=.25
        jid=mod.launch_job([["python3","-c","print('completed')"]])
        assert jid
        time.sleep(.4) # Longer than budget; job must remain queued, not time out
        with mod.JOBS_LOCK:
            assert mod.JOBS[jid]["status"]=="queued"
        release.set()
        job=wait_done(jid)
        assert job["queued_seconds"]>=.3
        assert job["result"]["exit_code"]==0
        assert job["timed_out"] is False
    finally:
        release.set();holder.join()
        mod.JOB_TIMEOUT=original

def test_killed_python_retains_partial_stdout(tmp_path):
    mod.ROOT=tmp_path
    r=mod.run(["python3","-c","import time;print('before timeout');time.sleep(10)"],timeout=.25)
    assert r["exit_code"]==124
    assert "before timeout" in r["stdout"]
    assert "timeout" in r["stderr"]

def test_job_timeout_flag(tmp_path):
    mod.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    mod.JOBS.clear()
    original=mod.JOB_TIMEOUT
    try:
        mod.JOB_TIMEOUT=.3
        jid=mod.launch_job([["python3","-c","import time;print('partial');time.sleep(10)"]])
        job=wait_done(jid)
        assert job["result"]["exit_code"]==124
        assert job["timed_out"] is True
        assert "partial" in job["result"]["stdout"]
    finally:
        mod.JOB_TIMEOUT=original

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

def test_queue_timeout_not_command_timeout(tmp_path):
    mod.ROOT=tmp_path
    mod.JOBS.clear()
    acquired=threading.Event()
    release=threading.Event()
    def holder():
        with mod.LOCK:
            acquired.set()
            release.wait(3)
    th=threading.Thread(target=holder)
    th.start()
    old=mod.JOB_QUEUE_MAX
    try:
        assert acquired.wait(1)
        mod.JOB_QUEUE_MAX=.15
        jid=mod.launch_job([["ls"]])
        result=wait_done(jid)
        assert result["result"]["exit_code"]==125
        assert result["queue_timeout"] is True
        assert result["timed_out"] is False
        assert result["stage"]=="queue"
        assert result["queued_seconds"]>=.1
    finally:
        release.set();th.join()
        mod.JOB_QUEUE_MAX=old

def test_short_metadata_deadline_reports_stage(tmp_path):
    mod.ROOT=tmp_path
    mod.JOBS.clear()
    with patch.object(mod,"run",return_value={"exit_code":124,"stdout":"","stderr":"timeout 0.1s","truncated":False,"_deadline_expired":True}):
        jid=mod.launch_job([["ls"]],timeout=.1)
        item=wait_done(jid)
        assert item["stage"]=="metadata"
        assert item["timed_out"] is True
        assert item["result"]["truncated"] is False

def test_checkout_explicit_remote_refspec():
    with patch.object(mod,"git",side_effect=[
        {"exit_code":0,"stdout":"","stderr":""},
        {"exit_code":0,"stdout":"","stderr":""},
        {"exit_code":1,"stdout":"","stderr":""},
        {"exit_code":0,"stdout":"","stderr":""}]) as mock_git:
        mod.checkout_branch("feature/test")
        assert mock_git.call_args_list[1].args == ("fetch","origin","+refs/heads/feature/test:refs/remotes/origin/feature/test")

def test_code_124_does_not_automatically_mean_timeout(tmp_path):
    mod.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    mod.JOBS.clear()
    with patch.object(mod,"run",side_effect=[
        {"exit_code":0,"stdout":"abcd","stderr":"","truncated":False},
        {"exit_code":0,"stdout":"","stderr":"","truncated":False},
        {"exit_code":124,"stdout":"","stderr":"application exit","truncated":False}
    ]):
        jid=mod.launch_job([["echo","hello"]],timeout=3)
        result=wait_done(jid)
    assert result["stage"]=="command"
    assert result["result"]["exit_code"]==124
    assert result["timed_out"] is False

def test_read_endpoints_skip_repo_lock_and_sync_timeout_is_rejected(tmp_path):
    import http.server, json, urllib.parse, urllib.request, urllib.error
    mod.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    (tmp_path/"a.txt").write_text("available")
    mod.TOKEN="t"*48
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),mod.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    entered=threading.Event();release=threading.Event()
    def holder():
        with mod.LOCK:
            entered.set();release.wait(3)
    h=threading.Thread(target=holder);h.start()
    assert entered.wait(1)
    try:
        base=f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base+"/read?path=a.txt&token="+mod.TOKEN,timeout=1) as response:
            assert json.load(response)["content"]=="available"
        with urllib.request.urlopen(base+"/preflight?token="+mod.TOKEN,timeout=1) as response:
            assert response.status==200
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(base+"/run?cmd=ls&timeout=5&token="+mod.TOKEN,timeout=1)
        assert error.value.code==400
    finally:
        release.set();h.join();server.shutdown();server.server_close();thread.join()

def test_fetch_allowed_and_queue_stage():
    assert mod.validate_segment(["git","fetch","origin"])

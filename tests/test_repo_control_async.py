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

def test_deadline_covers_multiple_stages(tmp_path):
    module.ROOT=tmp_path
    result=module.run_pipeline([["python3","-c","print('a')"],["python3","-c","print('b')"]],
                               deadline=time.monotonic()-0.1)
    assert result["exit_code"]==124

def test_job_not_found_and_poll_ignores_worktree_lock(tmp_path):
    import http.server, json, urllib.request, urllib.error
    module.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    module.TOKEN="t"*48
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),module.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f"http://127.0.0.1:{server.server_port}/job?token={module.TOKEN}&id="
    try:
        try:
            urllib.request.urlopen(base+"missing",timeout=2)
            assert False
        except urllib.error.HTTPError as exc:
            assert exc.code==404
        with module.JOBS_LOCK:
            module.JOBS["known"]={"status":"queued","result":None}
        acquired=threading.Event()
        release=threading.Event()
        def lock_holder():
            with module.LOCK:
                acquired.set()
                release.wait(3)
        holder=threading.Thread(target=lock_holder);holder.start()
        assert acquired.wait(1)
        with urllib.request.urlopen(base+"known",timeout=1) as response:
            assert json.load(response)["status"]=="queued"
    finally:
        release.set()
        holder.join()
        server.shutdown();server.server_close();thread.join()
        with module.JOBS_LOCK: module.JOBS.pop("known",None)

def test_two_concurrent_jobs_then_queue(tmp_path):
    module.ROOT=tmp_path
    module.JOBS.clear()
    started=threading.Event()
    release=threading.Event()
    def fake_pipeline(parts,*,deadline=None):
        started.set()
        release.wait(2)
        return {"exit_code":0,"stdout":"ok","stderr":"","truncated":False}
    with patch.object(module,"git",return_value={"exit_code":0,"stdout":"abc123","stderr":""}), patch.object(module,"run_pipeline",side_effect=fake_pipeline):
        ids=[module.launch_job([["ls"]]) for _ in range(3)]
        assert all(ids)
        assert started.wait(1)
        time.sleep(.05)
        with module.JOBS_LOCK:
            statuses=[module.JOBS[j]["status"] for j in ids]
        assert statuses.count("running")==1
        assert statuses.count("queued")==2
        release.set()
        for _ in range(200):
            with module.JOBS_LOCK:
                if all(module.JOBS[j]["status"]=="done" for j in ids): break
            time.sleep(.01)
        with module.JOBS_LOCK:
            assert all(module.JOBS[j]["status"]=="done" for j in ids)

def test_queue_wait_does_not_consume_runtime_budget(tmp_path):
    import http.server
    import json
    import urllib.request
    module.ROOT=tmp_path
    (tmp_path/".git").mkdir()
    module.TOKEN="t"*48
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),module.Handler)
    server_thread=threading.Thread(target=server.serve_forever,daemon=True)
    server_thread.start()
    taken=threading.Event()
    release=threading.Event()
    def hold_lock():
        with module.LOCK:
            taken.set()
            release.wait(3)
    holder=threading.Thread(target=hold_lock)
    holder.start()
    jid=None
    original_timeout=module.JOB_TIMEOUT
    try:
        assert taken.wait(1)
        module.JOB_TIMEOUT=0.15
        old_queue_max=module.JOB_QUEUE_MAX
        module.JOB_QUEUE_MAX=0.15
        jid=module.launch_job([["ls"]])
        assert jid
        url=f"http://127.0.0.1:{server.server_port}/job?id={jid}&token={module.TOKEN}"
        deadline=time.monotonic()+1.5
        snapshot=None
        while time.monotonic()<deadline:
            with urllib.request.urlopen(url,timeout=0.5) as response:
                snapshot=json.load(response)
            if snapshot["status"]=="done":
                break
            time.sleep(.02)
        assert snapshot["status"]=="done"
        assert snapshot["result"]["exit_code"]==125
        assert snapshot["queue_timeout"] is True
        assert snapshot["timed_out"] is False
        assert not release.is_set(), "job only expired after lock was released"
    finally:
        module.JOB_TIMEOUT=original_timeout
        module.JOB_QUEUE_MAX=old_queue_max
        release.set()
        holder.join()
        server.shutdown();server.server_close();server_thread.join()
        if jid:
            with module.JOBS_LOCK:
                module.JOBS.pop(jid,None)

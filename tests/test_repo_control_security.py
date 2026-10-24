"""Negative controls for Repo Control; run with pytest tests/test_repo_control_security.py."""
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

TARGET=Path(__file__).resolve().parents[1]/"services/repo-control/server.py"
spec=importlib.util.spec_from_file_location("repo_control_security_target",TARGET)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def test_pat_not_passed_to_untrusted_process(tmp_path):
    module.ROOT=tmp_path
    with patch.dict(os.environ,{"GITHUB_PAT":"pat-must-not-appear","SERVICE_TOKEN":"service-must-not-appear"}):
        r=module.run(["python3","-c","import os;print('GITHUB_PAT' in os.environ, 'SERVICE_TOKEN' in os.environ)"])
    assert r["exit_code"]==0
    assert "False False" in r["stdout"]
    assert "pat-must-not-appear" not in repr(r)

def test_output_memory_bounded(tmp_path):
    module.ROOT=tmp_path
    r=module.run(["python3","-c","import sys;sys.stdout.write('x'*200000)"])
    assert r["exit_code"]==0 and r["truncated"]
    assert len(r["stdout"].encode())<=module.MAX

def test_process_group_timeout(tmp_path):
    module.ROOT=tmp_path
    r=module.run(["python3","-c","import time;time.sleep(30)"],timeout=0.3)
    assert r["exit_code"]==124 and r["truncated"]

def test_disallowed_command_rejected_at_endpoint():
    import http.server, threading, urllib.request, urllib.error
    module.TOKEN="t"*48
    class Server(http.server.ThreadingHTTPServer): pass
    server=Server(("127.0.0.1",0),module.Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        module.ROOT=Path(__file__).resolve().parents[1]
        url=f"http://127.0.0.1:{server.server_port}/run?cmd=not_a_command&token="+module.TOKEN
        try:
            urllib.request.urlopen(url,timeout=3)
            assert False, "disallowed command unexpectedly accepted"
        except urllib.error.HTTPError as exc:
            assert exc.code==403
    finally:
        server.shutdown();server.server_close();thread.join()

def test_push_failure_not_success(tmp_path):
    module.ROOT=tmp_path
    with patch.object(module,"git",side_effect=[
        {"exit_code":0,"stdout":"","stderr":""},
        {"exit_code":0,"stdout":"","stderr":""},
        {"exit_code":1,"stdout":"","stderr":"remote rejected"}]):
        result=module.autosave("file.txt")
    assert result["ok"] is False and result["phase"]=="push"

def test_read_options_and_mutations():
    assert module.validate_segment(["grep","-c","needle","text.txt"])
    assert module.validate_segment(["grep","-o","needle","text.txt"])
    assert module.validate_segment(["wc","-c","text.txt"])
    assert not module.validate_segment(["sed","-i","s/a/b/","a.txt"])
    assert not module.validate_segment(["find",".","-delete"])
    assert not module.validate_segment(["find",".","-exec","sh","-c","echo bad",";"])
    assert not module.validate_segment(["bash","-c","id"])

def test_pipe_and_python_script(tmp_path):
    module.ROOT=tmp_path
    (tmp_path/"simple.py").write_text("print('ok-script')\n")
    assert module.validate_segment(["python3","simple.py"])
    assert not module.validate_segment(["python3","-c","print(1)"])
    assert not module.validate_segment(["python3","../escape.py"])
    parts=module.split_pipeline("find . | head -n 1")
    assert parts == [["find","."],["head","-n","1"]]
    assert module.run_pipeline(parts)["exit_code"] == 0
    assert module.run(["python3","simple.py"])["stdout"].strip()=="ok-script"

def test_branch_checkout_validation():
    import pytest
    with pytest.raises(ValueError):
        module.checkout_branch("../oops", True)

def test_autosave_main_refused():
    from unittest.mock import patch
    with patch.object(module,"current_branch",return_value="main"):
        assert module.autosave("test.txt")["phase"] == "preflight"

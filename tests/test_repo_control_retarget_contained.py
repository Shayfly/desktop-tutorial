"""agent-loop false failures (owner 2026-10-26): the cron failed every 15 minutes with "10 failed of 10 actions"
although the token was accepted -- every target PR's head was already contained in main, so GitHub refused the
retarget (422 "No commits between"). The service now skips a contained head, treats that 422 as a no-op, still
reports a real failure, and has op=prune for dead targets. Only GitHub's HTTP API is replaced here."""
import http.server
import importlib.util
import json
import sys
import threading
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repo_control_retarget_target", ROOT / "services/repo-control/server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.path.insert(0, str(ROOT / "scripts"))
import check_agent_loop_result as checker  # noqa: E402

SHA = {n: f"{n:040x}" for n in range(1, 6)}
# GitHub's real 422 body for PATCH /pulls/{n} {"base": "main"} when the head has nothing beyond main (verbatim shape;
# Matt's evidence on #145: "There are no new commits between ...", which an exact "No commits between" match missed).
REAL_422 = ('{{"message":"Validation Failed","errors":[{{"resource":"PullRequest","code":"custom","message":'
            '"There are no new commits between base branch \'main\' and head branch \'{0}\'."}}],'
            '"documentation_url":"https://docs.github.com/rest/pulls/pulls#update-a-pull-request","status":"422"}}')
PULLS = [{"number": n, "draft": False, "base": {"ref": "old/base"}, "head": {"ref": f"b{n}", "sha": SHA[n]}}
         for n in (1, 2, 3, 4)] + [{"number": 5, "draft": False, "base": {"ref": "main"}, "head": {"ref": "b5", "sha": SHA[5]}}]


class FakeGitHub:
    """#1 head contained in main; #2 GitHub answers 422 no commits; #3 a real refusal (403); #4 retargets ok;
    #5 is on main already and its head is contained (sweep must skip, not fail)."""

    def __init__(self):
        self.calls = []

    def __call__(self, path, method="GET", body=None):
        self.calls.append((method, path, body))
        if path.startswith("/pulls?state=open"):
            return {"ok": True, "status": 200, "data": PULLS}
        if path == "/compare/old/base...main":
            return {"ok": True, "status": 200, "data": {"status": "ahead"}}       # the old base is merged into main
        if path.startswith("/compare/main..."):
            contained = path.endswith(SHA[1]) or path.endswith(SHA[5])
            return {"ok": True, "status": 200,
                    "data": {"status": "behind" if contained else "diverged", "ahead_by": 0 if contained else 2}}
        if path.startswith("/compare/old/base...") and path != "/compare/old/base...main":
            return {"ok": False, "http_status": 500, "error": "GitHub API rejected request", "detail": ""}   # unknown
        if method == "PATCH" and path == "/pulls/2":
            return {"ok": False, "http_status": 422, "error": "GitHub API rejected request", "detail": REAL_422.format("b2")}
        if method == "PATCH" and path == "/pulls/3":
            return {"ok": False, "http_status": 403, "error": "GitHub API rejected request", "detail": "forbidden"}
        if method in ("PATCH", "POST"):
            return {"ok": True, "status": 200, "data": {}}
        return {"ok": True, "status": 200, "data": {"mergeable_state": "clean"}}


def call(query, fake):
    module.TOKEN = "t" * 48
    module.ROOT = ROOT                                   # a checkout exists (the service refuses without one)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), module.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with patch.object(module, "gh_json", fake), patch.object(module, "PAT", "x"):
            url = f"http://127.0.0.1:{server.server_port}/pr?{query}&token={module.TOKEN}"
            with urllib.request.urlopen(url, timeout=10) as r:
                return json.load(r)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def verdict(payload, op):
    """The cron's own result checker (scripts/check_agent_loop_result.py): 0 = PASS, 1 = FAIL."""
    import contextlib, io
    with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), contextlib.redirect_stdout(io.StringIO()), \
            patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": ""}):
        return checker.main(op)


def test_contained_branch_is_skipped_and_never_patched():
    fake = FakeGitHub()
    out = call("op=retarget", fake)
    assert "1 retarget old/base -> skip contained in main" in out["actions"]
    assert ("PATCH", "/pulls/1", {"base": "main"}) not in fake.calls


def test_422_no_commits_between_is_a_no_op_success():
    out = call("op=retarget", FakeGitHub())
    assert "2 retarget old/base -> skip no commits between" in out["actions"]


def test_a_real_failure_is_still_fail_and_fails_the_cron():
    out = call("op=retarget", FakeGitHub())
    assert out["actions"] == ["1 retarget old/base -> skip contained in main",
                              "2 retarget old/base -> skip no commits between",
                              "3 retarget old/base -> fail",
                              "4 retarget old/base -> ok"]
    assert verdict(out, "retarget") == 1                                   # #3 is real: still FAIL
    out["actions"] = [a for a in out["actions"] if not a.startswith("3 ")]
    out["count"] = len(out["actions"])
    assert verdict(out, "retarget") == 0                                   # skips and ok only: PASS


def test_the_old_false_failures_are_now_zero():
    # every target contained in main: the cron used to report "10 failed of 10"
    pulls = [{"number": n, "draft": False, "base": {"ref": "old/base"}, "head": {"ref": f"c{n}", "sha": SHA[1]}}
             for n in range(10)]
    global PULLS
    fake = FakeGitHub()
    saved, PULLS = PULLS, pulls
    try:
        out = call("op=retarget", fake)
    finally:
        PULLS = saved
    assert out["count"] == 10 and all("-> skip contained in main" in a for a in out["actions"])
    assert verdict(out, "retarget") == 0
    assert not [c for c in fake.calls if c[0] == "PATCH"]


def test_sweep_skips_a_contained_head_instead_of_failing_the_merge():
    fake = FakeGitHub()
    out = call("op=sweep", fake)
    assert out["actions"] == ["5 skip contained in main"]
    assert not [c for c in fake.calls if c[0] == "PUT"]
    assert verdict(out, "sweep") == 0


def test_prune_lists_dead_targets_and_closes_them_only_when_applied():
    fake = FakeGitHub()
    dry = call("op=prune", fake)
    assert dry["applied"] is False
    assert dry["actions"] == ["1 prune contained (dry run)", "5 prune contained (dry run)"]
    assert not [c for c in fake.calls if c[0] in ("PATCH", "POST")]
    fake = FakeGitHub()
    applied = call("op=prune&apply=1", fake)
    assert applied["actions"] == ["1 prune contained -> ok", "5 prune contained -> ok"]
    assert ("PATCH", "/pulls/1", {"state": "closed"}) in fake.calls
    assert ("PATCH", "/pulls/3", {"state": "closed"}) not in fake.calls     # not contained: kept


def test_the_real_github_422_message_is_a_no_op():
    """The test that was missing: GitHub's own wording, through the real gh_json error path."""
    import io
    from urllib.error import HTTPError
    body = REAL_422.format("fix/x").encode()
    err = HTTPError("https://api.github.com/repos/o/r/pulls/7", 422, "Unprocessable Entity", {}, io.BytesIO(body))
    with patch.object(module, "PAT", "x"), patch.object(module, "urlopen", side_effect=err):
        result = module.gh_json("/pulls/7", method="PATCH", body={"base": "main"})
    assert result["http_status"] == 422 and "There are no new commits between" in result["detail"]
    assert module.no_commits_between(result) is True
    assert module.no_commits_between({"ok": False, "http_status": 422, "detail": "Validation Failed: base invalid"}) is False
    assert module.no_commits_between({"ok": False, "http_status": 403, "detail": REAL_422.format("x")}) is False


def test_precheck_direction_head_behind_main_is_skipped_without_patch():
    calls = []

    def gh(path, method="GET", body=None):
        calls.append((method, path))
        if path == f"/compare/main...{SHA[1]}":
            return {"ok": True, "data": {"status": "behind", "ahead_by": 0, "behind_by": 7}}   # head is an ancestor
        if path == f"/compare/{SHA[1]}...main":
            return {"ok": True, "data": {"status": "ahead", "ahead_by": 7}}                    # the wrong direction
        return {"ok": False, "http_status": 404, "detail": ""}
    with patch.object(module, "gh_json", gh):
        assert module.head_in_main({"head": {"sha": SHA[1]}, "base": {"ref": "main"}}) is True
    assert ("GET", f"/compare/main...{SHA[1]}") in calls


def test_precheck_ancestor_of_its_own_merged_base_is_enough_when_main_compare_is_unknown():
    def gh(path, method="GET", body=None):
        if path == f"/compare/main...{SHA[3]}":
            return {"ok": False, "http_status": 502, "detail": ""}                               # cannot tell
        if path == f"/compare/old/base...{SHA[3]}":
            return {"ok": True, "data": {"status": "identical", "ahead_by": 0}}
        return {"ok": False, "http_status": 404, "detail": ""}
    with patch.object(module, "gh_json", gh):
        pr = {"head": {"sha": SHA[3]}, "base": {"ref": "old/base"}}
        assert module.head_in_main(pr) is True
        assert module.head_in_main(pr, via_base=False) is None                    # prune closes only on main itself


def test_a_contained_head_the_precheck_cannot_see_still_ends_as_a_no_op():
    # compare unreadable -> the PATCH is sent -> GitHub's real 422 -> skip, never "-> fail"
    out = call("op=retarget", FakeGitHub())
    assert "2 retarget old/base -> skip no commits between" in out["actions"]
    assert not any(a.startswith("2 ") and a.endswith("-> fail") for a in out["actions"])

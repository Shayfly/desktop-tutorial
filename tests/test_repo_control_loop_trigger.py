"""agent-loop self-trigger (owner 2026-10-26): GitHub's schedule fired once in ten hours, so the always-on repo-control
service dispatches the workflow itself every 15 minutes; the schedule moves off the crowded minutes and stays as a
second trigger; a concurrency group serialises both; 45 minutes without a successful run is a loud warning."""
import contextlib
import datetime
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("repo_control_loop_target", ROOT / "services/repo-control/server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = datetime.datetime(2026, 10, 26, 18, 0, tzinfo=datetime.timezone.utc)


class _Resp:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_dispatch_is_one_post_to_the_workflow_on_main_and_204_is_success():
    seen = []

    def fake_urlopen(req, timeout):
        seen.append((req.get_method(), req.full_url, json.loads(req.data)))
        return _Resp(204)
    with patch.object(module, "PAT", "x"), patch.object(module, "urlopen", fake_urlopen):
        r = module.dispatch_workflow()
    assert r == {"ok": True, "http_status": 204}
    assert seen == [("POST", "https://api.github.com/repos/Shayfly/desktop-tutorial/actions/workflows/agent-loop.yml/dispatches",
                     {"ref": "main"})]


def test_a_403_says_the_pat_lacks_actions_write_and_is_not_success():
    err = HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b'{"message":"Resource not accessible by personal access token"}'))
    with patch.object(module, "PAT", "x"), patch.object(module, "urlopen", side_effect=err):
        r = module.dispatch_workflow()
    assert r["ok"] is False and r["http_status"] == 403 and "actions:write" in r["error"]
    with patch.object(module, "PAT", ""):
        assert module.dispatch_workflow()["ok"] is False


def run_tick(last_success):
    out = io.StringIO()
    with patch.object(module, "last_success_at", lambda: last_success), \
            patch.object(module, "dispatch_workflow", lambda: {"ok": True, "http_status": 204}), \
            contextlib.redirect_stdout(out):
        module.loop_tick(now=NOW)
    return dict(module.LOOP_STATE), out.getvalue()


def test_45_minutes_without_a_successful_run_is_a_loud_warning():
    state, log = run_tick("2026-10-26T17:00:00Z")                       # 60 minutes ago
    assert state["stalled"] is True and '"action": "loop:STALLED"' in log and "60 min" in log
    state, log = run_tick(None)                                          # never succeeded
    assert state["stalled"] is True and "for ever" in log
    state, log = run_tick("2026-10-26T17:50:00Z")                       # 10 minutes ago
    assert state["stalled"] is False and "loop:STALLED" not in log
    assert state["last_dispatch_status"] == 204 and '"action": "loop:dispatch", "result": "ok"' in log


def test_health_exposes_the_trigger_state_without_secrets():
    module.LOOP_STATE.update(last_dispatch_at=NOW.isoformat(), last_dispatch_status=204)
    shown = json.dumps(module.LOOP_STATE)
    assert "204" in shown and "token" not in shown.lower() and "https://" not in shown


def test_the_workflow_schedule_concurrency_and_stall_step():
    wf = yaml.safe_load((ROOT / ".github/workflows/agent-loop.yml").read_text())
    on = wf[True]
    assert on["schedule"] == [{"cron": "4,19,34,49 * * * *"}]              # off :00/:15/:30/:45
    assert "workflow_dispatch" in on                                       # the service's trigger
    assert wf["concurrency"] == {"group": "agent-loop", "cancel-in-progress": False}
    assert wf["permissions"].get("actions") == "read"
    names = [s.get("name") for s in wf["jobs"]["loop"]["steps"]]
    # C10 (CEO 2026-10-27): the stall check is a gate that FAILS the run, after the work, always.
    stall_name = "stall gate (no successful run in 45 minutes fails the run)"
    assert names.index("sweep clean ready") < names.index(stall_name)
    stall = next(s for s in wf["jobs"]["loop"]["steps"] if s.get("name") == stall_name)
    assert stall.get("if") == "always()"
    assert "python scripts/check_agent_loop_stall.py" in stall["run"] and "::warning" not in stall["run"]

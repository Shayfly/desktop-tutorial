#!/usr/bin/env python3
"""Snapshot last main workflow runs using GitHub Actions API."""
import datetime as dt
import json
import os
import subprocess
import urllib.request

repo = os.environ["GH_REPO"]
token = os.environ["GH_TOKEN"]
req = urllib.request.Request(
    "https://api.github.com/repos/" + repo + "/actions/runs?branch=main&per_page=100",
    headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
             "X-GitHub-Api-Version": "2022-11-28"},
)
try:
    with urllib.request.urlopen(req, timeout=25) as response:
        runs = json.load(response)["workflow_runs"]
    fetch_note = "OK"
except Exception as exc:
    runs = []
    fetch_note = "ERROR: " + type(exc).__name__
head = subprocess.check_output(["git", "rev-parse", "origin/main"], text=True).strip()
now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
http_code = os.environ.get("HEALTH_HTTP_CODE", "000")
health = "HEALTHY" if http_code == "200" else "CHECK FAILED"
latest = {}
for run in runs:
    name = run.get("name", "")
    if name and name not in latest and name != "Repo Control Health and CI Status":
        latest[name] = run
lines = [
    "# CI STATUS — Snapshot",
    "",
    "**Captured at:** " + now,
    "**main SHA at snapshot:** " + head,
    "**Note:** The snapshot commit itself advances main; SHA above is pre-commit.",
    "**Repo Control health:** " + health + " (HTTP " + http_code + ")",
    "**GitHub Actions API:** " + fetch_note,
    "",
    "| Workflow | Run | SHA | Status | Conclusion |",
    "|---|---|---|---|---|",
]
for name, run in sorted(latest.items()):
    clean = name.replace("|", "/").replace("\n", " ")[:80]
    rid = run["id"]
    url = "https://github.com/" + repo + "/actions/runs/" + str(rid)
    sha = run.get("head_sha", "")[:12]
    lines.append("| " + clean + " | [#" + str(rid) + "](" + url + ") | " + sha + " | " + run.get("status", "unknown") + " | " + (run.get("conclusion") or "pending") + " |")
if not latest:
    lines.append("| No data | — | — | unknown | — |")
lines += [
    "",
    "Point-in-time snapshot of latest main runs for each workflow among the last 100 runs.",
    "GitHub cron may run late or be skipped; 10-minute polling cannot guarantee Render stays awake.",
    "Health checks HTTP 200 only, not clone or end-to-end functionality. No token is sent.",
    "",
]
with open("CI_STATUS.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

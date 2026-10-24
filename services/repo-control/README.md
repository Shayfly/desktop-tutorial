# Repo Control HTTP (isolated, GET-client compatible)

Deploy using Render Blueprint (`render.yaml` in repo root). Provide **GITHUB_PAT** as a secret env var. The Blueprint generates `SERVICE_TOKEN`; copy its value securely to the GET client. Token >=40 chars. PAT must be fine-grained, this repository only, with **Contents: read and write** and **Pull requests: read and write** for `GET /pr?op=create`. No production credentials in this service.

At startup the container clones `REPO_URL` using a separate GIT_ASKPASS helper and installs `requirements.txt` and `requirements-test.txt` from the cloned repo (plus pytest and related packages in Dockerfile). Startup fails visibly when clone or dependencies fail. Filesystem is disposable; after each write the service commits and pushes, reporting partial durability if push fails.

Each operation accepts `?token=SERVICE_TOKEN`; header Bearer is also supported. GET examples: `/read?path=STATE.md&token=...`, `/write?path=note.txt&b64=aGVsbG8=&append=0&token=...`, `/git?op=status&token=...`, `/pr?op=create&title=docs&head=branch&base=main&token=...`. POST /write and /git remain supported. No-store, no-referrer, and no application request-target logs. Still, **query tokens can be captured by Render/proxy/access logs or browser history**: URL secret authentication is inherently higher risk. Do not open links in browsers or share them; rotate token when exposed.

`/run` includes: pytest, python3 restricted to `-m pytest` / `-m compileall`, git read subcommands (status/diff/log/show/branch/rev-parse), grep, find, ls, cat, head, tail, wc, diff, sed, awk, tree, pwd, rg. Commands may execute repository code (e.g. pytest and awk). Never run untrusted code, and do not use this instance for production workloads or secrets. A free Render instance and container filesystem are ephemeral; deployment requires manual connection of repo + PAT value.

No automatic GitHub merge endpoint is exposed. PR is created as draft and reviewed through standard GitHub gates.

## Security boundary (explicit)

**/run is NOT a security boundary. Possession of the service token grants the capability to execute repository-controlled code**, especially via pytest. Keep this on an isolated non-production instance, with a dedicated least-privilege PAT, no production secrets. The command allowlist prevents accidental operations, not malicious code execution. The /run subprocess environment excludes GITHUB_PAT, GH_TOKEN, GITHUB_TOKEN and SERVICE_TOKEN; authenticated Git management runs in a separate credentials-enabled subprocess. This environment split does not protect the PAT against hostile code with access to the same OS user/process or service files; stronger isolation requires distinct OS security principals or containers.

## /run stage rules

Supports literal pipes (`find . | head -n 10`) as up to five **sequential** allowlisted stages without a shell. Each intermediate stage is capped to 50KB and marks `truncated=true` when incomplete. Mutating CLI switches `sed -i`, `sed --in-place`, `find -delete/-exec/-fprint` are blocked rather than silently dropping unsaved changes; changes must be made through `/write` for immediate autosave. Safe counting flags `grep -c`, `grep -o` and `wc -c` are allowed. `python3 relative_script.py` is permitted for a repository-local file: **this executes arbitrary repository code and may modify files; no read-only guarantee.** The allowlist and checks are guardrails, not a security boundary. PAT is not in `/run`'s environment but isolation of process-level credentials is not guaranteed.

## Branches and main protection
Clones the last 50 commits by default (new ephemeral instances only). Existing shallow clones must be replaced or fetched deeper separately.
Before writes, query `GET /preflight?token=...` for current branch and main push dry-run verdict. A dry run cannot fully guarantee acceptance under branch protection: `dry_run_allowed_unverified` is **not** permission to push.
`GET /git?op=checkout&branch=feature/name&create=1&token=...` creates a working branch; omit `create=1` to switch to an existing branch, fetching from origin first. Dirty worktrees refuse checkout.
To avoid discovery by losing a write, **autosave and explicit push to main are blocked by service policy**; checkout a feature branch before calling /write. Merge through reviewed GitHub API/PR process.

Preflight includes `branch` (the exact current branch) and `dirty` (true when uncommitted or untracked files exist; null if the status check fails). Following deployment, **restart the Render instance** to force the new clone depth; verify `/git?op=log` has multiple commits. Restart only after the new image is successfully deployed.

Write protection runs **before opening the file**: on `main` or detached HEAD, `/write` returns 409 without changing its contents. For branches without an upstream, autosave uses `git push --set-upstream origin <branch>`; with upstream it uses `git push`. Tests verify both paths and a rejected push. The Docker smoke uses a synthetic `.git` directory and does **not** validate real clone, dependency installation or the entrypoint end-to-end.

## Asynchronous command jobs

`GET /run?cmd=pytest&async=1&token=...` returns HTTP 202 with `{"id":"...","status":"running"}` immediately. Poll `GET /job?id=<id>&token=...` to receive `running` or `done`; done includes the complete bounded command result (`exit_code`, `stdout`, `stderr`, `truncated`). Results survive the originating HTTP request and are retained **in process memory**, capped at 32 jobs with oldest completed results evicted when necessary. **They do not survive a container restart/redeploy.** Two jobs execute concurrently; additional jobs wait in daemon threads (maximum 32 retained). All command runs retain the 120-second execution limit. Async endpoints do not acquire the Git/worktree mutation LOCK, so polling and unrelated requests remain responsive; running tests may still interact with mutable checkout, and /run remains arbitrary-code capable with a token.

Async jobs have one **120-second end-to-end deadline starting at admission**, including queue wait and every pipeline stage. States: `queued`, `running`, `done`. Every running/done job includes the Git HEAD `sha` and whether its worktree was `dirty` immediately before the command; queued jobs have null metadata until they obtain the repo lock. Async commands acquire the global repository lock for their entire execution, protecting checkout and /write; `/job` uses only the short-lived jobs-state lock. The two-executor semaphore does not mean two simultaneous worktree executions: repo-lock serialization permits only one at a time. Results remain in RAM only, and are evicted or lost on restart.

## Hardening: queue time and partial timeout output

Queued jobs retain `queued` while they wait for ACTIVE and the repository lock. The 120-second execution budget starts **after both locks are acquired**, so time in the queue does not count against execution. The `queued_seconds` field records that wait. Async `/job` responses add `timed_out` (boolean). Python commands execute with `PYTHONUNBUFFERED=1`; output captured before SIGKILL is returned on exit 124. Results remain in process memory only. This behavior intentionally supersedes the previous admission-time deadline rule.

# Repo Control HTTP (isolated, GET-client compatible)

Deploy using Render Blueprint (`render.yaml` in repo root). Provide **GITHUB_PAT** as a secret env var. The Blueprint generates `SERVICE_TOKEN`; copy its value securely to the GET client. Token >=40 chars. PAT must be fine-grained, this repository only, with **Contents: read and write** and **Pull requests: read and write** for `GET /pr?op=create`. No production credentials in this service.

At startup the container clones `REPO_URL` using a separate GIT_ASKPASS helper and installs `requirements.txt` and `requirements-test.txt` from the cloned repo (plus pytest and related packages in Dockerfile). Startup fails visibly when clone or dependencies fail. Filesystem is disposable; after each write the service commits and pushes, reporting partial durability if push fails.

Each operation accepts `?token=SERVICE_TOKEN`; header Bearer is also supported. GET examples: `/read?path=STATE.md&token=...`, `/write?path=note.txt&b64=aGVsbG8=&append=0&token=...`, `/git?op=status&token=...`, `/pr?op=create&title=docs&head=branch&base=main&token=...`. POST /write and /git remain supported. No-store, no-referrer, and no application request-target logs. Still, **query tokens can be captured by Render/proxy/access logs or browser history**: URL secret authentication is inherently higher risk. Do not open links in browsers or share them; rotate token when exposed.

`/run` includes: pytest, python3 restricted to `-m pytest` / `-m compileall`, git read subcommands (status/diff/log/show/branch/rev-parse), grep, find, ls, cat, head, tail, wc, diff, sed, awk, tree, pwd, rg. Commands may execute repository code (e.g. pytest and awk). Never run untrusted code, and do not use this instance for production workloads or secrets. A free Render instance and container filesystem are ephemeral; deployment requires manual connection of repo + PAT value.

No automatic GitHub merge endpoint is exposed. PR is created as draft and reviewed through standard GitHub gates.

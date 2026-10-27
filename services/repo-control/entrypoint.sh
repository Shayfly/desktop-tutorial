#!/bin/sh
set -eu
: "${SERVICE_TOKEN:?SERVICE_TOKEN required}"
: "${GITHUB_PAT:?GITHUB_PAT required}"
: "${REPO_URL:?REPO_URL required}"
case "$REPO_URL" in https://github.com/*) ;; *) echo "REPO_URL must be https GitHub URL" >&2; exit 1;; esac
case "$REPO_URL" in *'@'*) echo "Credentials are forbidden in REPO_URL" >&2; exit 1;; esac
if [ ! -d "$REPO_DIR/.git" ]; then
  GIT_ASKPASS=/app/askpass.sh GIT_TERMINAL_PROMPT=0 git clone --depth 50 --branch "${REPO_BRANCH:-main}" "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
git config user.name "${GIT_AUTHOR_NAME:-Repo Control}"
git config user.email "${GIT_AUTHOR_EMAIL:-repo-control@example.invalid}"
# Install the project's own runtime and test requirements after ephemeral clone.
if [ -f requirements.txt ]; then pip install --no-cache-dir --user -r requirements.txt; fi
if [ -f requirements-test.txt ]; then pip install --no-cache-dir --user -r requirements-test.txt; fi
exec python /app/server.py
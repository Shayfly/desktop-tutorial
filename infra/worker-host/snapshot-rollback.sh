#!/usr/bin/env bash
# Snapshot the RUNNING consumers as omni-rollback/<svc>:prev BEFORE `docker compose build` (2026-10-19).
# The build moves the compose tags; on this host the image object a running container was created from then
# disappears, and drain.sh can no longer tag it (deploy-worker run 39262167302 refused for exactly that).
#
# A ladder, per service. The first rung that works wins; every rung that fails is logged as a ::warning.
#   0. omni-rollback/<svc>:prev already IS the running image                       -> done (idempotent)
#   1. tag    the running container's image                                       -> fast and exact
#   2. commit the running container (--pause=false) when the image content exists but the tag fails
#   -  keep   an existing omni-rollback/<svc>:prev whose 3 code hashes match the running container (idempotent rerun)
#   3. rebuild from the REVISION OF THE RUNNING CONTAINER (never the checked-out HEAD) when the image content is gone:
#      `git archive <rev>` of this repository, `docker build` without secrets or build args, accepted ONLY if the 3
#      code hashes match the running container; otherwise ::error.
# Revision source: the container's org.opencontainers.image.revision label; containers built before that label existed
# carry it only as OMNI_SOURCE_COMMIT in their own environment (written by write-env.sh at their deploy) -- used as the
# fallback, with a warning. No revision -> no rebuild.
# Never stops, pauses, restarts or removes a container. Secrets are never printed or baked into an image (a committed
# image has every .env variable blanked; the compose env_file supplies them whenever it runs).
set -uo pipefail
cd "$(dirname "$0")"
REPO_ROOT="${SNAPSHOT_REPO_ROOT:-$(cd ../.. && pwd)}"
SERVICES=(worker intake-worker intake-maintain preview-worker)
VERIFY_FILES=(omni_prod/worker_tasks.py omni_prod/model_gateway.py omni_prod/preview_router.py)
HASH_PY='import hashlib,sys;from pathlib import Path;print(" ".join(hashlib.sha256(Path("/app",p).read_bytes()).hexdigest() for p in sys.argv[1:]))'
dockerfile_of() { [ "$1" = preview-worker ] && echo infra/preview-worker/Dockerfile || echo Dockerfile; }
oneline() { printf '%s' "$1" | tr '\n' ' ' | tail -c 300; }

env_blanks=()
if [ -f .env ]; then
  while IFS= read -r name; do env_blanks+=(--change "ENV ${name}="); done \
    < <(sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' .env | sort -u)
fi

running_hash() { docker exec "$1" python -c "$HASH_PY" "${VERIFY_FILES[@]}" 2>/dev/null; }
image_hash() { docker run --rm --network none --entrypoint python "$1" -c "$HASH_PY" "${VERIFY_FILES[@]}" 2>/dev/null; }

revision_of() {  # $1 container id. stdout: 40-hex revision; return 1 when none is known
  local rev
  rev=$(docker inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$1" 2>/dev/null)
  if [[ "$rev" =~ ^[0-9a-f]{40}$ ]]; then echo "$rev"; return 0; fi
  rev=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$1" 2>/dev/null | sed -n 's/^OMNI_SOURCE_COMMIT=//p' | head -n 1)
  if [[ "$rev" =~ ^[0-9a-f]{40}$ ]]; then echo "env:$rev"; return 0; fi
  return 1
}

BUILT=$(mktemp -d); trap 'rm -rf "$BUILT"' EXIT   # one build per revision and Dockerfile (survives $(...) subshells)
rebuild() {  # $1 rev, $2 dockerfile. stdout: image id
  local key="$BUILT/$1-${2//\//_}" src out
  [ -s "$key" ] && { cat "$key"; return 0; }
  src=$(mktemp -d)
  git -C "$REPO_ROOT" cat-file -e "$1^{commit}" 2>/dev/null || git -C "$REPO_ROOT" fetch -q --depth 1 origin "$1" >/dev/null 2>&1 \
    || { rm -rf "$src"; echo "git fetch $1 failed"; return 1; }
  git -C "$REPO_ROOT" archive "$1" | tar -x -C "$src" || { rm -rf "$src"; echo "git archive $1 failed"; return 1; }
  out=$(docker build -q --label "org.opencontainers.image.revision=$1" --label omni.rollback.method=rebuild \
        -f "$src/$2" "$src" 2>&1) || { rm -rf "$src"; echo "docker build failed: $(oneline "$out")"; return 1; }
  rm -rf "$src"
  out=$(printf '%s' "$out" | tail -n 1)
  printf '%s' "$out" > "$key"; echo "$out"
}

failed=()
for s in "${SERVICES[@]}"; do
  ref="omni-rollback/$s:prev"
  cid=$(docker compose ps -q "$s" 2>/dev/null | head -n 1)
  [ -n "$cid" ] || { echo "snapshot: $s has no container; nothing to snapshot"; continue; }
  if ! img=$(docker inspect -f '{{.Image}}' "$cid" 2>/dev/null) || [ -z "$img" ]; then
    failed+=("cannot inspect the container of $s"); continue
  fi
  have=$(docker image inspect -f '{{.Id}}' "$ref" 2>/dev/null || true)
  if [ -n "$have" ] && [ "$have" = "$img" ]; then
    echo "::notice title=snapshot::$s: rung 1 (tag): $ref is already the running image"; continue
  fi
  # rung 1: tag
  if err=$(docker tag "$img" "$ref" 2>&1); then
    echo "::notice title=snapshot::$s: rung 1 (tag)"; continue
  fi
  echo "::warning title=snapshot::$s: rung 1 (tag) failed: $(oneline "$err")"
  # rung 2: commit (needs the image content)
  rev_c=$(revision_of "$cid" || true)
  if err=$(docker commit --pause=false --change "LABEL org.opencontainers.image.revision=${rev_c#env:}" \
           --change "LABEL omni.rollback.method=docker-commit" "${env_blanks[@]}" "$cid" "$ref" 2>&1 >/dev/null); then
    echo "::warning title=snapshot::$s: committed the running container as $ref (rung 2; $(( ${#env_blanks[@]} / 2 )) .env variables blanked, not paused)"
    continue
  fi
  echo "::warning title=snapshot::$s: rung 2 (commit) failed: $(oneline "$err")"
  # an existing rollback image with the same code is kept (a rerun after a rebuild does not rebuild again)
  if ! run_h=$(running_hash "$cid") || [ -z "$run_h" ]; then failed+=("$s: cannot hash the code of the running container"); continue; fi
  if [ -n "$have" ] && [ "$(image_hash "$ref" || true)" = "$run_h" ]; then
    echo "::notice title=snapshot::$s: existing $ref has the same 3 code hashes as the running container, kept"; continue
  fi
  # rung 3: rebuild from the running container's revision
  if ! rev=$(revision_of "$cid"); then
    failed+=("$s: image content is gone and the running container records no revision; cannot rebuild"); continue
  fi
  if [ "${rev#env:}" != "$rev" ]; then
    rev=${rev#env:}
    echo "::warning title=snapshot::$s: the running container has no revision label; using its own OMNI_SOURCE_COMMIT ${rev:0:7}"
  fi
  if ! iid=$(rebuild "$rev" "$(dockerfile_of "$s")"); then failed+=("$s: rebuild from revision ${rev:0:7} failed ($iid)"); continue; fi
  img_h=$(image_hash "$iid" || true)
  if [ "$img_h" != "$run_h" ]; then
    failed+=("$s: rebuilt image from revision ${rev:0:7} does not match the running code (3 hashes); not accepted"); continue
  fi
  if ! err=$(docker tag "$iid" "$ref" 2>&1); then failed+=("$s: cannot tag the rebuilt image ($(oneline "$err"))"); continue; fi
  echo "::warning title=snapshot::$s: rebuilt rollback from revision ${rev:0:7} (3 code hashes match the running container)"
done

if [ "${#failed[@]}" -gt 0 ]; then
  echo "::error title=snapshot::NO SAFE ROLLBACK, nothing was stopped: ${failed[*]}"
  exit 1
fi
echo "snapshot: rollback images ready for: ${SERVICES[*]}"

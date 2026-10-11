#!/usr/bin/env bash
# Drain every queue consumer (build, intake, intake maintenance, preview) before anything is replaced.
# Fails closed: a drain that did not finish cleanly, a killed job (exit 137, the deadline), an OOM kill or a
# container that is still running stops the deploy BEFORE migrations; recover.sh then restores the previous
# containers. Records the previous image of every consumer so recover.sh can restore it. Never deletes data
# or volumes. Secrets are never printed.
set -uo pipefail
cd "$(dirname "$0")"
SERVICES=(worker intake-worker intake-maintain preview-worker)
STATE="${DEPLOY_STATE_DIR:-${RUNNER_TEMP:-/tmp}/deploy-state}"
DEADLINE="${DRAIN_DEADLINE_SECONDS:-1500}"
mkdir -p "$STATE"
: > "$STATE/prev-images"
rm -f "$STATE/drain-failed"

busy=0
prep=()
for s in "${SERVICES[@]}"; do
  cid=$(docker compose ps -q "$s" 2>/dev/null | head -n 1)
  ps_rc=${PIPESTATUS[0]}
  if [ "$ps_rc" -ne 0 ]; then prep+=("cannot list container of $s (exit $ps_rc)"); continue; fi
  [ -n "$cid" ] || continue
  # An existing consumer whose previous image cannot be read or preserved makes a rollback impossible: do not drain.
  if ! img=$(docker inspect -f '{{.Image}}' "$cid" 2>/dev/null) || [ -z "$img" ]; then
    prep+=("cannot inspect the image of $s"); continue
  fi
  if ! docker tag "$img" "omni-rollback/$s:prev" >/dev/null 2>&1; then
    prep+=("cannot save a rollback image for $s"); continue
  fi
  echo "$s $cid $img" >> "$STATE/prev-images"
  [ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" = "true" ] && busy=$((busy + 1))
done
if [ "${#prep[@]}" -gt 0 ]; then
  printf '%s\n' "${prep[@]}" > "$STATE/drain-failed"
  echo "::error title=drain::NOT draining, nothing was stopped: ${prep[*]}"
  exit 1
fi

start=$(date +%s)
docker compose stop -t "$DEADLINE" "${SERVICES[@]}"
rc=$?
waited=$(( $(date +%s) - start ))

reasons=()
[ "$rc" -eq 0 ] || reasons+=("docker compose stop exited $rc")
while read -r s cid img; do
  [ -n "${s:-}" ] || continue
  read -r running code oom <<<"$(docker inspect -f '{{.State.Running}} {{.State.ExitCode}} {{.State.OOMKilled}}' "$cid" 2>/dev/null || echo 'unknown 0 false')"
  [ "$running" = "false" ] || reasons+=("$s still running after drain")
  [ "$code" != "137" ] || reasons+=("$s exit 137 (a job was killed at the ${DEADLINE}s deadline)")
  [ "$oom" != "true" ] || reasons+=("$s was OOM-killed")
  echo "drain: $s exit=$code oom=$oom running=$running"
done < "$STATE/prev-images"

if [ "${#reasons[@]}" -gt 0 ]; then
  printf '%s\n' "${reasons[@]}" > "$STATE/drain-failed"
  echo "::error title=drain::drain failed after ${waited}s (consumers running before: ${busy}): ${reasons[*]}"
  exit 1
fi
echo "::notice title=drain::all consumers stopped cleanly after ${waited}s (running before: ${busy}); previous images recorded for rollback"

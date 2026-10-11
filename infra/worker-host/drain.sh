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
for s in "${SERVICES[@]}"; do
  cid=$(docker compose ps -q "$s" 2>/dev/null | head -n 1)
  [ -n "$cid" ] || continue
  img=$(docker inspect -f '{{.Image}}' "$cid" 2>/dev/null) || continue
  docker tag "$img" "omni-rollback/$s:prev" >/dev/null 2>&1 && echo "$s $cid $img" >> "$STATE/prev-images"
  [ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" = "true" ] && busy=$((busy + 1))
done

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

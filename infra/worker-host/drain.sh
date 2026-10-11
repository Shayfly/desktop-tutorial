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
# The gate is read-only and fail-closed (exit 0 verified quiet, 3 running work, 2 cannot verify). Overridable for tests.
GATE_CMD="${ACTIVE_JOBS_CMD:-docker compose run --rm --no-deps -T worker python -m omni_prod.active_jobs}"
mkdir -p "$STATE"
: > "$STATE/prev-images"
rm -f "$STATE/drain-failed" "$STATE/not-stopped"

# Refusal BEFORE anything was stopped: recover.sh must then leave the running consumers completely alone.
refuse() {
  printf '%s\n' "$@" > "$STATE/drain-failed"
  : > "$STATE/not-stopped"
  : > "$STATE/prev-images"
  echo "::error title=drain::NOT draining, nothing was stopped: $*"
  exit 1
}

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
[ "${#prep[@]}" -eq 0 ] || refuse "${prep[@]}"

# Re-check immediately before the stop (work may have started since the workflow's idle gate). Work that starts after
# this check is not killed: SIGTERM is a warm shutdown, the consumer finishes it within the deadline, and the
# post-stop check below fails the deploy (and recovery restores the old workers) if anything was left unfinished.
eval "$GATE_CMD --wait-minutes 0"
gate_rc=$?
case "$gate_rc" in
  0) ;;
  3) refuse "running work appeared before the drain (gate exit 3)" ;;
  *) refuse "the gate could not verify that nothing is running (exit $gate_rc): a DB/Redis failure or missing information blocks the deploy" ;;
esac

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

# With every consumer stopped nothing new can start here, so whatever the gate still sees RUNNING (or cannot verify)
# was cut off or abandoned. A stale heartbeat or a leftover registry entry is not proof the work finished.
eval "$GATE_CMD --wait-minutes 0"
post_rc=$?
case "$post_rc" in
  0) ;;
  3) reasons+=("work is still recorded as running after the consumers stopped (a job was cut off or abandoned)") ;;
  *) reasons+=("after the stop the gate could not verify that nothing is running (exit $post_rc)") ;;
esac

if [ "${#reasons[@]}" -gt 0 ]; then
  printf '%s\n' "${reasons[@]}" > "$STATE/drain-failed"
  echo "::error title=drain::drain failed after ${waited}s (consumers running before: ${busy}): ${reasons[*]}"
  exit 1
fi
echo "::notice title=drain::all consumers stopped cleanly after ${waited}s (running before: ${busy}); previous images recorded for rollback"

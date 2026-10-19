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

# Fallback (2026-10-19): the running container's own image object can be gone (pruned) while a
# source-equivalent rollback image already exists (.github/workflows/148ai-rebuild-safe-rollback-images.yml).
# Accept that existing omni-rollback/<svc>:prev ONLY if it carries a revision label AND the shipped code files
# hash identically in the running container and in that image. Otherwise refuse exactly as before.
VERIFY_FILES=(omni_prod/worker_tasks.py omni_prod/model_gateway.py omni_prod/preview_router.py)
HASH_PY='import hashlib,sys;from pathlib import Path;print(" ".join(hashlib.sha256(Path("/app",p).read_bytes()).hexdigest() for p in sys.argv[1:]))'
verified_existing_rollback() {  # $1 service, $2 container id. stdout: revision on success, reason on failure.
  local s=$1 cid=$2 ref="omni-rollback/$1:prev" rev run_h img_h
  docker image inspect "$ref" >/dev/null 2>&1 || { echo "no existing $ref"; return 1; }
  rev=$(docker image inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$ref" 2>/dev/null)
  if [ -z "$rev" ] || [ "$rev" = "<no value>" ]; then echo "$ref has no revision label"; return 1; fi
  if ! run_h=$(docker exec "$cid" python -c "$HASH_PY" "${VERIFY_FILES[@]}" 2>/dev/null) || [ -z "$run_h" ]; then
    echo "cannot hash the code of the running $s"; return 1
  fi
  if ! img_h=$(docker run --rm --network none --entrypoint python "$ref" -c "$HASH_PY" "${VERIFY_FILES[@]}" 2>/dev/null) || [ -z "$img_h" ]; then
    echo "cannot hash the code of $ref"; return 1
  fi
  [ "$run_h" = "$img_h" ] || { echo "$ref code differs from the running $s"; return 1; }
  echo "$rev"
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
    if why=$(verified_existing_rollback "$s" "$cid"); then
      echo "::notice title=drain::$s: its image object is gone; using the existing omni-rollback/$s:prev (revision $why; ${#VERIFY_FILES[@]} code hashes match the running container)"
      img="omni-rollback/$s:prev"
    else
      prep+=("cannot save a rollback image for $s ($why)"); continue
    fi
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
reasons=()
# intake-maintain is a maintenance loop with no jobs of its own (relay outbox -> queue, reconcile expired leases;
# a pass cut short is redone by the next one). Stop it first with a short timeout: a container still running the
# old code ignores SIGTERM as PID 1 and would otherwise hold the drain for the whole deadline (2026-10-19).
MAINTAIN_STOP="${MAINTAIN_STOP_SECONDS:-20}"
maintain_killed_ok=0
rest=()
for s in "${SERVICES[@]}"; do [ "$s" = intake-maintain ] || rest+=("$s"); done
if grep -q '^intake-maintain ' "$STATE/prev-images"; then
  docker compose stop -t "$MAINTAIN_STOP" intake-maintain
  m_rc=$?
  [ "$m_rc" -eq 0 ] || reasons+=("docker compose stop intake-maintain exited $m_rc")
  maintain_killed_ok=1
  echo "drain: intake-maintain stopped first after $(( $(date +%s) - start ))s (timeout ${MAINTAIN_STOP}s)"
fi
docker compose stop -t "$DEADLINE" "${rest[@]}"
rc=$?
waited=$(( $(date +%s) - start ))

[ "$rc" -eq 0 ] || reasons+=("docker compose stop exited $rc")
while read -r s cid img; do
  [ -n "${s:-}" ] || continue
  read -r running code oom <<<"$(docker inspect -f '{{.State.Running}} {{.State.ExitCode}} {{.State.OOMKilled}}' "$cid" 2>/dev/null || echo 'unknown 0 false')"
  [ "$running" = "false" ] || reasons+=("$s still running after drain")
  if [ "$code" = "137" ] && [ "$s" = intake-maintain ] && [ "$maintain_killed_ok" -eq 1 ]; then
    echo "::notice title=drain::intake-maintain exit 137: killed after ${MAINTAIN_STOP}s (no jobs of its own; old code ignores SIGTERM)"
  else
    [ "$code" != "137" ] || reasons+=("$s exit 137 (a job was killed at the ${DEADLINE}s deadline)")
  fi
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

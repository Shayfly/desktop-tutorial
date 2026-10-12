#!/usr/bin/env bash
# Run when a deploy step failed after drain.sh started (workflow: if: failure()). Restores the PREVIOUS consumer
# containers from the images drain.sh recorded, then VERIFIES every one of them is running again. Fails (exit 1) when
# a recorded service has no rollback image, when `up` fails, or when any service is not running afterwards; the run
# is red either way. It never touches the database or any volume: migrations are additive (the schema check treats a
# database ahead of the code as compatible), and tables such as conversation_attachments are preserved.
# No `down`, no `-v`, no `prune`.
set -uo pipefail
cd "$(dirname "$0")"
STATE="${DEPLOY_STATE_DIR:-${RUNNER_TEMP:-/tmp}/deploy-state}"
LIST="$STATE/prev-images"
if [ -e "$STATE/not-stopped" ]; then
  echo "::notice title=recover::the drain refused before stopping anything; the running consumers are untouched and nothing is restarted"
  exit 0
fi
if [ ! -s "$LIST" ]; then
  echo "::notice title=recover::nothing was drained or no previous consumer existed; nothing to restore"
  exit 0
fi
OVR="$STATE/rollback.yml"
wanted=(); missing=()
{
  echo "services:"
  while read -r s cid img; do
    [ -n "${s:-}" ] || continue
    wanted+=("$s")
    if docker image inspect "omni-rollback/$s:prev" >/dev/null 2>&1; then
      printf '  %s:\n    image: omni-rollback/%s:prev\n' "$s" "$s"
    else
      missing+=("$s")
    fi
  done < "$LIST"
} > "$OVR"
restorable=()
for s in "${wanted[@]}"; do
  skip=0; for m in "${missing[@]:-}"; do [ "$m" = "$s" ] && skip=1; done
  [ "$skip" -eq 1 ] || restorable+=("$s")
done
failed=()
[ "${#missing[@]}" -eq 0 ] || failed+=("no rollback image for: ${missing[*]}")
if [ "${#restorable[@]}" -gt 0 ]; then
  docker compose -f docker-compose.yml -f "$OVR" up -d --no-build --no-deps "${restorable[@]}"
  rc=$?
  [ "$rc" -eq 0 ] || failed+=("docker compose up exited $rc")
fi
tries="${RECOVER_WAIT_TRIES:-15}"
for s in "${restorable[@]}"; do
  ok=0
  for i in $(seq 1 "$tries"); do
    cid=$(docker compose -f docker-compose.yml -f "$OVR" ps -q "$s" 2>/dev/null | head -n 1)
    if [ -n "$cid" ] && [ "$(docker inspect -f '{{.State.Running}}' "$cid" 2>/dev/null)" = "true" ]; then ok=1; break; fi
    sleep "${RECOVER_WAIT_SLEEP:-2}"
  done
  [ "$ok" -eq 1 ] || failed+=("$s is not running after recovery")
done
for s in "${restorable[@]}"; do
  if [ "$s" = "worker" ]; then
    heard=0
    for i in $(seq 1 "$tries"); do
      docker compose -f docker-compose.yml -f "$OVR" logs worker 2>&1 | grep -q "Listening on" && { heard=1; break; }
      sleep "${RECOVER_WAIT_SLEEP:-2}"
    done
    [ "$heard" -eq 1 ] || failed+=("worker is running but not listening on its queue")
  fi
done
docker compose -f docker-compose.yml -f "$OVR" ps || true
if [ "${#failed[@]}" -gt 0 ]; then
  echo "::error title=recover::RECOVERY INCOMPLETE, customers may have no worker: ${failed[*]}"
  exit 1
fi
echo "::warning title=recover::deploy failed; PREVIOUS consumers restored and running (${restorable[*]}). Database untouched. The run stays failed."

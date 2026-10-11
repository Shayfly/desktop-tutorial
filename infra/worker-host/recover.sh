#!/usr/bin/env bash
# Run when a deploy step failed after drain.sh started (workflow: if: failure()). Restores the PREVIOUS consumer
# containers from the images drain.sh recorded, so queued customer jobs are served again while the failure is
# investigated. The job still ends red. It never touches the database or any volume: migrations are additive
# (the schema check treats a database ahead of the code as compatible), and tables such as
# conversation_attachments are preserved. No `down`, no `-v`, no `prune`.
set -uo pipefail
cd "$(dirname "$0")"
STATE="${DEPLOY_STATE_DIR:-${RUNNER_TEMP:-/tmp}/deploy-state}"
LIST="$STATE/prev-images"
if [ ! -s "$LIST" ]; then
  echo "::notice title=recover::nothing was drained or no previous consumer existed; nothing to restore"
  exit 0
fi
OVR="$STATE/rollback.yml"
{
  echo "services:"
  while read -r s cid img; do
    [ -n "${s:-}" ] || continue
    docker image inspect "omni-rollback/$s:prev" >/dev/null 2>&1 || continue
    printf '  %s:\n    image: omni-rollback/%s:prev\n' "$s" "$s"
  done < "$LIST"
} > "$OVR"
services=$(awk '/^  [a-z-]+:$/ {gsub(/[: ]/, ""); print}' "$OVR" | tr '\n' ' ')
if [ -z "$services" ]; then
  echo "::error title=recover::no rollback image is available; consumers stay stopped. Start them manually: docker compose up -d"
  exit 1
fi
# shellcheck disable=SC2086
docker compose -f docker-compose.yml -f "$OVR" up -d --no-build --no-deps $services
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "::error title=recover::restoring previous consumers failed (exit $rc)"
  exit 1
fi
for i in $(seq 1 "${RECOVER_WAIT_TRIES:-15}"); do
  docker compose -f docker-compose.yml -f "$OVR" logs worker 2>&1 | grep -q "Listening on" && break
  sleep 2
done
docker compose -f docker-compose.yml -f "$OVR" ps
echo "::warning title=recover::deploy failed; PREVIOUS consumers restored (${services}). Database untouched. The run stays failed."

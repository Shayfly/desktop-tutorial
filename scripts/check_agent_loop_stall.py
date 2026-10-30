"""agent-loop stall gate (CEO 2026-10-27, C10): a stalled loop FAILS the run; a warning would be silent green.

    python scripts/check_agent_loop_stall.py <updated_at of the last successful agent-loop run, or empty>

Exit 0 when the last successful run is at most STALE_SECONDS old; exit 1 when it is older, missing or unreadable.
The current run is never counted: it is still in progress when this step reads the run list.
"""
from __future__ import annotations

import datetime
import sys

STALE_SECONDS = 2700        # 45 minutes; the loop is expected every 15


def verdict(last: str | None, now: datetime.datetime) -> tuple[bool, str]:
    last = (last or '').strip()
    if not last or last == 'null':
        return False, 'no successful agent-loop run on record'
    try:
        at = datetime.datetime.fromisoformat(last.replace('Z', '+00:00'))
    except ValueError:
        return False, f'unreadable timestamp {last!r}'
    age = int((now - at).total_seconds())
    if age > STALE_SECONDS:
        return False, f'last successful run was {age // 60} minutes ago ({last}); expected every 15 minutes'
    return True, f'last success {age // 60} min ago'


def main(argv: list[str]) -> int:
    ok, why = verdict(argv[1] if len(argv) > 1 else None, datetime.datetime.now(datetime.timezone.utc))
    print(f'::notice title=agent-loop trigger::{why}' if ok else f'::error title=agent-loop STALLED::{why}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

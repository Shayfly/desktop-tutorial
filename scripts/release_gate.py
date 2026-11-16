"""Warehouse 111, the worker half (owner 2026-11-16): the build worker is deployed only on a release, like Vercel's
production (scripts/vercel_ignore_build.mjs).

A release is a push whose head commit message carries RELEASE_MARK ("[release]", written in the merge commit), or a
manual run (workflow_dispatch). Anything else is not a release: the deploy job is skipped and this step SAYS so, as a
::notice with the reason -- never a silent skip. Writes `release=true|false` to $GITHUB_OUTPUT.

  python scripts/release_gate.py            # reads GITHUB_EVENT_NAME, GITHUB_EVENT_PATH, GITHUB_OUTPUT
"""
from __future__ import annotations

import json
import os
import sys

RELEASE_MARK = '[release]'
EVENTS = ('push', 'workflow_dispatch')


def decide(event_name: str, message: str) -> tuple[bool, str]:
    if event_name == 'workflow_dispatch':
        return True, 'manual run (workflow_dispatch): a release'
    if event_name != 'push':
        raise ValueError(f'unknown event {event_name!r}; the release gate knows {EVENTS}')
    if RELEASE_MARK in (message or ''):
        return True, f'push with {RELEASE_MARK} in the head commit: a release'
    return False, f'push without {RELEASE_MARK}: not a release -- the worker is NOT deployed (merge with {RELEASE_MARK}, or run it by hand)'


def main() -> int:
    event = os.environ.get('GITHUB_EVENT_NAME', '')
    path = os.environ.get('GITHUB_EVENT_PATH', '')
    payload = {}
    if path:
        with open(path, encoding='utf-8') as fh:
            payload = json.load(fh)
    message = ((payload.get('head_commit') or {}).get('message')) or ''
    try:
        release, why = decide(event, message)
    except ValueError as exc:
        print(f'::error title=release gate::{exc}')
        return 2
    print(f'::notice title=release gate::{"RELEASE" if release else "SKIP"} -- {why}')
    out = os.environ.get('GITHUB_OUTPUT')
    if not out:
        print('::error title=release gate::GITHUB_OUTPUT is not set; cannot hand the decision to the deploy job')
        return 2
    with open(out, 'a', encoding='utf-8') as fh:
        fh.write(f'release={"true" if release else "false"}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())

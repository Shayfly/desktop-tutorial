"""Read a pytest junit report (2026-11-16): the v24-ci `test` job ran the whole suite twice -- once as its own step
and again inside scripts/run_international_gate.py -- 7.7 minutes each, and with the negative controls the job hit its
20-minute bound (#418 was cancelled there). The gate now reads the report the first run wrote in the same job.

`verdict(path)` -> (ok, detail). Not ok, loudly, when the report is missing, unreadable, empty, or has a failure or an
error. A skipped test is counted and said, not hidden.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def verdict(path) -> tuple[bool, str]:
    p = Path(path)
    if not p.exists():
        return False, f'{p}: no junit report (did the pytest step run?)'
    try:
        root = ET.parse(p).getroot()
    except ET.ParseError as exc:
        return False, f'{p}: unreadable junit report ({exc})'
    suites = [root] if root.tag == 'testsuite' else list(root.iter('testsuite'))
    tests = sum(int(s.get('tests', 0)) for s in suites)
    failures = sum(int(s.get('failures', 0)) for s in suites)
    errors = sum(int(s.get('errors', 0)) for s in suites)
    skipped = sum(int(s.get('skipped', 0)) for s in suites)
    detail = f'{p}: {tests} tests, {failures} failures, {errors} errors, {skipped} skipped'
    if tests == 0:
        return False, detail + ' (an empty report is not a pass)'
    return failures == 0 and errors == 0, detail

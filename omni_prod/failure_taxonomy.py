"""Failure taxonomy of one build (founder decision 2026-10-19: the business metric is first_pass_yield).

One record per failure per verification round:
  layer         which check failed (sandbox, consistency, dependency, preview, behaviour, browser, visual, quality, review)
  failure_type  a stable short key from the failure message (no product data, no numbers)
  round_index   0 = the initial build, n = after repair n
  was_repaired  True when the same (layer, failure_type) is gone in the next verified round
  chain_depth   the stage rank AutonomousProductEngine.progress() gives it (deeper = later in the chain)
first_pass    the build passed with no repair at all; first_pass_yield = first-pass builds / builds.
"""
from __future__ import annotations

import re

LAYERS = {'CONSISTENCY': 'consistency', 'UNSUPPORTED_DEPENDENCY': 'dependency', 'PREVIEW': 'preview',
          'BEHAVIOR': 'behaviour', 'BROWSER': 'browser', 'VISUAL': 'visual', 'QUALITY': 'quality', 'REVIEW': 'review'}


def layer_of(acceptance_id: str) -> str:
    for suffix in ('_EXCEPTION', '_unspecified'):          # a crashed / silent post-build check keeps its layer
        if acceptance_id.endswith(suffix) and acceptance_id[:-len(suffix)] in LAYERS:
            return LAYERS[acceptance_id[:-len(suffix)]]
    return LAYERS.get(acceptance_id, 'sandbox')       # acceptance ids (A1, ...) come from the sandbox build/verify


def failure_type(message: str, acceptance_id: str = '') -> str:
    """'the product misbehaves in a real browser: form ...' -> 'the_product_misbehaves_in_a_real_browser'."""
    if acceptance_id.endswith('_EXCEPTION'):
        return 'check_exception'
    if acceptance_id.endswith('_unspecified'):
        return 'check_failed_unspecified'
    head = (message or '').split(':', 1)[0].lower()
    head = re.sub(r"'[^']*'|\"[^\"]*\"|\d+", ' ', head)          # drop quoted names and numbers
    words = re.sub(r'[^a-z() ]+', ' ', head).split()
    return '_'.join(words)[:60] or 'unknown'


def records(rounds) -> list[dict]:
    """rounds: [(round_index, [AcceptanceFailure...]), ...] in order -> taxonomy records."""
    from .autonomous_core import AutonomousProductEngine, ExecutionReport, SUMMARY_FAILURE_ID
    keyed = []
    for idx, failures in rounds:
        rows = []
        for f in failures:
            if f.acceptance_id == SUMMARY_FAILURE_ID:
                continue
            depth = AutonomousProductEngine.progress(ExecutionReport(False, (f,)))[0]
            rows.append({'layer': layer_of(f.acceptance_id), 'failure_type': failure_type(f.message, f.acceptance_id),
                         'round_index': idx, 'chain_depth': depth})
        keyed.append((idx, rows))
    out = []
    for n, (idx, rows) in enumerate(keyed):
        nxt = {(r['layer'], r['failure_type']) for r in keyed[n + 1][1]} if n + 1 < len(keyed) else None
        for r in rows:
            out.append({**r, 'was_repaired': nxt is not None and (r['layer'], r['failure_type']) not in nxt})
    return out


def first_pass_yield(builds) -> float | None:
    builds = list(builds)
    return None if not builds else round(sum(1 for b in builds if b.get('first_pass')) / len(builds), 4)

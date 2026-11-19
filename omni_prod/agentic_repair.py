"""Agentic repair v1 (CEO order 2026-11-09, priority (b)): the repair model works INSIDE the repository.

The classic RepairAgent gets one prompt (a summary of the repository plus the failures) and must answer with full
files in one shot. Founder builds on 2026-11-08/09 showed what that costs: a 51K-char file it could not see, a fix
that broke indentation, rounds that changed nothing. Here the model works the way an engineer does -- in steps, on
a private working copy, with tools:

  read    {"action": "read",   "paths": ["api.py", ...]}             -> full text of those files
  search  {"action": "search", "pattern": "<regex>"}                 -> matching lines (path:line: text)
  edit    {"action": "edit",   "edits": [{"path", "old", "new"}],
                               "files": [{"path", "content"}]}       -> applied to the working copy, then CHECKED:
                                                                        syntax, imports, routes, static files and
                                                                        the project manifest (consistency scan)
  submit  {"action": "submit", "files": [...optional last edits...]} -> ends the round; every changed file is the patch

Bounded: at most `max_steps` model calls per round (default 6, OMNI_AGENTIC_REPAIR_STEPS, never above 10), tool
output capped, the build's model budget and hard cap unchanged (every step is an ordinary routed call). If the
working copy cannot be built (no repository given) or the agent fails before changing anything, the classic
RepairAgent answers instead, so turning this on can never make a round worse than before.

The tests run in the remote sandbox between rounds exactly as before; v1 checks edits with the in-process
consistency scan only (milliseconds, no sandbox cost). Running the sandbox inside the loop is v2.
"""
from __future__ import annotations

import json
import os
import re

from .build_control import BuildCancelled, BuildDeadline
from .repository_patch import parse_patch

_MAX_READ_CHARS = 60_000
_MAX_SEARCH_LINES = 80
_HISTORY_CHARS = 120_000
# wf_309a64e1-002 (2026-11-17): a whole app.py (~9.4-9.8K output tokens, estimate) was cut at 8,188 tokens 14 of 14
# times on the 8,192-token routes. An existing file larger than this is changed with edit blocks, never rewritten
# whole; 12,000 characters stays far below an 8K-token answer (production cuts came at ~24K characters).
WHOLE_FILE_MAX_CHARS = 12_000

_SYSTEM = (
    'You are the senior engineer repairing a generated product inside its repository. You work in steps; each '
    'answer is ONE JSON object choosing ONE action:\n'
    '{"action": "read", "paths": ["<file>", ...]}  -- read whole files (you see only their names and sizes until '
    'you read them)\n'
    '{"action": "search", "pattern": "<python regex>"}  -- find where something is defined or used\n'
    '{"action": "edit", "edits": [{"path": "<file>", "old": "<exact text now in the file>", "new": "<its '
    'replacement>"}]}  -- change existing files with exact edit blocks: "old" is copied exactly (every space and '
    'newline) and occurs exactly once in the file -- include a few surrounding lines to make it unique; all edits of '
    'one answer apply together or not at all. A NEW file is sent whole: "files": [{"path": "<file>", "content": '
    '"<the whole file>"}]; an existing file over 12000 characters is never sent whole. The answer tells you whether '
    'the code still compiles, imports resolve, routes and static files exist\n'
    '{"action": "submit", "note": "<one line: the cause you fixed>"}  -- finish; every file you edited becomes the '
    'repair\n'
    'Answer with the JSON object only: never a function call, never text before or after it.\n'
    'Method: read the failures, read the code they point at, find the root cause, edit the file that owns it, '
    'check that the edit is clean, then submit. Keep every behaviour that already passes. Never weaken a test or an '
    'acceptance step to make it pass unless it contradicts the approved acceptance text. In a test file you may only '
    'change the expected value of an assert whose assumption is wrong; a test of the customer\'s phone, price, '
    'address or hours is never edited (the code shows them as given), and any other test change is reverted and '
    'counted. File content keeps every '
    'newline and indentation. Submit before you run out of steps (steps_left).'
)


class AgenticRepairAgent:
    """Drop-in for RepairAgent.repair(spec=, repo_summary=, failures=)."""

    def __init__(self, gateway, *, fallback, max_steps: int | None = None):
        self.gateway = gateway
        self.fallback = fallback
        env = int(os.getenv('OMNI_AGENTIC_REPAIR_STEPS', '6') or 6)
        self.max_steps = max(2, min(10, max_steps if max_steps is not None else env))
        self.trace: list[dict] = []

    # -------------------------------------------------------------- tools
    @staticmethod
    def _read(work: dict, paths) -> dict:
        out, used = {}, 0
        for p in [str(x) for x in (paths or [])][:8]:
            text = work.get(p)
            if text is None:
                out[p] = '<no such file>'
                continue
            room = _MAX_READ_CHARS - used
            if room <= 0:
                out[p] = '<not shown: read limit for this step reached; read it in the next step>'
                continue
            out[p] = text if len(text) <= room else text[:room] + '\n<... truncated ...>'
            used += len(out[p])
        return {'files': out}

    @staticmethod
    def _search(work: dict, pattern) -> dict:
        try:
            rx = re.compile(str(pattern or ''))
        except re.error as exc:
            return {'error': f'invalid regex: {exc}'}
        hits = []
        for path in sorted(work):
            for n, line in enumerate(work[path].splitlines(), 1):
                if rx.search(line):
                    hits.append(f'{path}:{n}: {line.strip()[:200]}')
                    if len(hits) >= _MAX_SEARCH_LINES:
                        return {'matches': hits, 'truncated': True}
        return {'matches': hits}

    @staticmethod
    def _proposed(work: dict, data: dict) -> tuple[dict, list[dict]]:
        """The new text of every file this answer changes ('files' first, then 'edits' on top), or ({}, misses).
        Both _apply and the result the model reads use it, so they cannot disagree."""
        from .repair_edits import resolve_edits
        texts, misses = {}, []
        for f in data.get('files') or []:
            if not (isinstance(f, dict) and isinstance(f.get('path'), str) and isinstance(f.get('content'), str)):
                continue
            current = work.get(f['path'])
            if current is not None and len(current) > WHOLE_FILE_MAX_CHARS:
                misses.append({'path': f['path'], 'code': 'WHOLE_FILE_TOO_LARGE',
                               'message': f'{f["path"]} has {len(current)} characters: change it with "edits", '
                                          'not a whole new file'})
                continue
            texts[f['path']] = f['content']
        edited, edit_misses = resolve_edits({**work, **texts}, data.get('edits'))
        misses += edit_misses
        if misses:
            return {}, misses
        return {**texts, **edited}, []

    @classmethod
    def _apply(cls, work: dict, data) -> dict:
        texts, misses = cls._proposed(work, data if isinstance(data, dict) else {})
        if misses:
            return {'applied': [], 'edit_misses': misses}          # nothing applied: all or nothing
        work.update(texts)
        return {'applied': sorted(texts)}

    @staticmethod
    def _check(work: dict) -> dict:
        from .consistency_gate import scan
        report = scan(work)
        return {'clean': not report.blocking,
                'problems': [f'{f.check}: {f.where()} {f.message} (fix: {f.fix})' for f in report.blocking[:12]]}

    # -------------------------------------------------------------- loop
    def repair(self, *, spec, repo_summary: dict, failures: list[dict]):
        base = repo_summary.get('_repository') if isinstance(repo_summary, dict) else None
        if not isinstance(base, dict) or not base:
            return self.fallback.repair(spec=spec, repo_summary=repo_summary, failures=failures)
        work = dict(base)
        history: list[dict] = []
        submitted = False
        for step in range(self.max_steps):
            payload = {
                'spec': spec.to_dict() if hasattr(spec, 'to_dict') else {},
                'failures': failures[:20],
                'repository': [{'path': p, 'chars': len(t)} for p, t in sorted(work.items())],
                'candidate_files': repo_summary.get('candidate_files') or [],
                'edited': sorted(p for p in work if work[p] != base.get(p)),
                'steps_left': self.max_steps - step,
                'history': _trim(history),
            }
            try:
                kwargs = dict(system=_SYSTEM, user=json.dumps(payload, ensure_ascii=False), max_tokens=32000)
                if getattr(self.gateway, 'accepts_task_tag', False):
                    from .autonomous_agents import _code_shape_guard
                    kwargs['validate'] = lambda d: _code_shape_guard({'files': d.get('files')} if isinstance(d, dict) else {})
                data = self.gateway.complete_json(**kwargs)
            except (BuildCancelled, BuildDeadline):
                raise                       # the owner's stop and the build's time limit are never swallowed
            except Exception as exc:
                self.trace.append({'step': step, 'error': f'{type(exc).__name__}: {exc}'[:200]})
                break
            action = str((data or {}).get('action', '')).lower() if isinstance(data, dict) else ''
            if action == 'read':
                result = self._read(work, data.get('paths'))
            elif action == 'search':
                result = self._search(work, data.get('pattern'))
            elif action == 'edit':
                result = {**self._apply(work, data), **self._check(work)}
            elif action == 'submit':
                result = self._apply(work, data)
                if not result.get('edit_misses'):
                    self.trace.append({'step': step, 'action': 'submit', 'note': str(data.get('note', ''))[:300]})
                    submitted = True
                    break
                # the last edits did not apply: the model reads why and may fix them (still bounded by max_steps)
            else:
                result = {'error': 'unknown action; use read, search, edit or submit'}
            self.trace.append({'step': step, 'action': action or '?'})
            history.append({'step': step, 'request': _short(data), 'result': result})
        changed = [{'path': p, 'content': work[p]} for p in sorted(work) if work[p] != base.get(p)]
        if not changed:
            # Nothing usable from the agent: the classic one-shot repair answers this round.
            return self.fallback.repair(spec=spec, repo_summary=repo_summary, failures=failures)
        self.trace.append({'result': 'submitted' if submitted else 'steps_exhausted', 'files': [c['path'] for c in changed]})
        return parse_patch({'files': changed})


def _short(data: dict) -> dict:
    out = {k: v for k, v in data.items() if k not in ('files', 'edits')}
    if isinstance(data.get('files'), list):
        out['files'] = [str(f.get('path')) for f in data['files'] if isinstance(f, dict)]
    if isinstance(data.get('edits'), list):
        out['edits'] = [str(e.get('path')) for e in data['edits'] if isinstance(e, dict)]
    return out


def _trim(history: list[dict]) -> list[dict]:
    """Newest steps whole, oldest dropped first, so the prompt stays bounded."""
    out, used = [], 0
    for item in reversed(history):
        size = len(json.dumps(item, ensure_ascii=False))
        if used + size > _HISTORY_CHARS and out:
            break
        out.append(item)
        used += size
    return list(reversed(out))

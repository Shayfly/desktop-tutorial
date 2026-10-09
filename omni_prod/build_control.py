"""Stop a running build between steps, and tell the owner what it is doing.

Directive 2026-10-09 §10 (cancel, task states) and §12 (the user always sees
progress). The worker never kills a model call or a sandbox run half way:
`checkpoint()` runs before every model call and before every sandbox run, so
a stop takes effect at the next step boundary and nothing is left
half-written. What was really spent until then is settled; the rest of the
reservation is released by the normal settlement path.

The live log is short customer-language sentences (no code, no prompts, no
secrets). Writing it is best effort: a log failure never changes a build.
"""
from __future__ import annotations

import logging

_log = logging.getLogger(__name__)


class BuildCancelled(Exception):
    """The owner asked to stop this build; raised at a step boundary."""


TASK_LABELS = {
    'architecture': 'מתכנן את מבנה המוצר והבדיקות',
    'codegen': 'כותב את הקוד',
    'repair': 'מתקן את מה שנכשל בבדיקות',
    'review': 'בודק איכות (QA) את הקוד',
    'classification': 'מסווג את בקשת השינוי',
    'modification': 'כותב את השינוי',
}


class BuildControl:
    def __init__(self, jobs, build_id: str):
        self._jobs = jobs
        self.build_id = build_id
        self.checks = 0
        self.model_calls = 0

    def log(self, kind: str, message: str) -> None:
        add = getattr(self._jobs, 'add_event', None)
        if add is None:
            return
        try:
            add(self.build_id, kind, message)
        except Exception:  # pragma: no cover - logging must never fail a build
            _log.warning('build event write failed for %s', self.build_id, exc_info=True)

    def checkpoint(self) -> None:
        asked = getattr(self._jobs, 'cancel_requested', None)
        if asked is None:
            return
        try:
            stop = asked(self.build_id)
        except Exception:
            _log.warning('cancel check failed for %s', self.build_id, exc_info=True)
            return
        if stop:
            self.log('cancel', 'הבנייה נעצרה לבקשתך. נחויב רק מה שכבר נוצל.')
            raise BuildCancelled(f'build {self.build_id} stopped by its owner')

    # Installed on RoutedModelGateway.before_call.
    def before_model_call(self, task: str) -> None:
        self.checkpoint()
        self.model_calls += 1
        self.log('model', TASK_LABELS.get(task, 'שולח בקשה למודל'))


class ControlledExecutor:
    """Wraps the outermost executor: checkpoint before each run, one log line
    after it (passed, or how many checks failed and the first reason)."""

    def __init__(self, inner, control: BuildControl):
        self._inner = inner
        self._control = control

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        self._control.checkpoint()
        self._control.checks += 1
        n = self._control.checks
        report = self._inner.execute(repository=repository, spec=spec)
        failures = list(getattr(report, 'failures', None) or [])
        if getattr(report, 'passed', False):
            self._control.log('check', f'סבב בדיקות {n}: כל הבדיקות עברו')
        else:
            first = failures[0] if failures else None
            reason = (getattr(first, 'message', '') or '')[:180] if first else ''
            self._control.log('check', f'סבב בדיקות {n}: {len(failures) or 1} נכשלו'
                                       + (f' — {reason}' if reason else '') + '. מתקן.')
        return report


def install(engine, gateway, control: BuildControl):
    """Attach the control to a live engine and its gateway. Returns the engine."""
    if hasattr(gateway, 'before_call'):
        gateway.before_call = control.before_model_call
    if getattr(engine, 'executor', None) is not None:
        engine.executor = ControlledExecutor(engine.executor, control)
    return engine

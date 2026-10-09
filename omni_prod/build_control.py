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
        asked = getattr(self._jobs, 'checkpoint', None) or getattr(self._jobs, 'cancel_requested', None)
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


class ModificationJobs:
    """The control surface of a change (modification), same shape as the
    build repository's: heartbeat + stop flag, live log, stop request."""

    def __init__(self, pool):
        self.pool = pool

    def add_event(self, modification_id: str, kind: str, message: str) -> None:
        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute("INSERT INTO build_events(build_id, kind, message, job_kind) VALUES (%s, %s, %s, 'modification')",
                             (modification_id, kind, str(message)[:600]))

    def checkpoint(self, modification_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.transaction():
                row = conn.execute("UPDATE modification_requests SET heartbeat_at = now() WHERE id = %s "
                                   "RETURNING cancel_requested_at IS NOT NULL", (modification_id,)).fetchone()
        return bool(row and row[0])

    def request_cancel(self, modification_id: str, project_id: str, *, requested_by: str) -> str:
        with self.pool.connection() as conn:
            with conn.transaction():
                row = conn.execute("SELECT status FROM modification_requests WHERE id = %s AND project_id = %s FOR UPDATE",
                                   (modification_id, project_id)).fetchone()
                if row is None:
                    raise KeyError('modification not found or access denied')
                if row[0] == 'QUEUED':
                    conn.execute("UPDATE modification_requests SET status = 'CANCELLED', completed_at = now(), "
                                 "error_code = 'cancelled_by_user', cancel_requested_at = now() WHERE id = %s",
                                 (modification_id,))
                    conn.execute("INSERT INTO build_events(build_id, kind, message, job_kind) VALUES (%s, 'cancel', %s, 'modification')",
                                 (modification_id, 'השינוי בוטל לפני שהתחיל. לא נוצלו קרדיטים.'))
                    return 'cancelled'
                if row[0] == 'RUNNING':
                    conn.execute("UPDATE modification_requests SET cancel_requested_at = COALESCE(cancel_requested_at, now()) "
                                 "WHERE id = %s", (modification_id,))
                    conn.execute("INSERT INTO build_events(build_id, kind, message, job_kind) VALUES (%s, 'cancel', %s, 'modification')",
                                 (modification_id, 'התקבלה בקשת עצירה. השינוי ייעצר בסיום הצעד הנוכחי.'))
                    return 'cancel_requested'
                return row[0]

    def events(self, modification_id: str, project_id: str, *, after: int = 0, limit: int = 200) -> list[dict]:
        with self.pool.connection() as conn:
            if conn.execute("SELECT 1 FROM modification_requests WHERE id = %s AND project_id = %s",
                            (modification_id, project_id)).fetchone() is None:
                raise KeyError('modification not found or access denied')
            rows = conn.execute("SELECT seq, at, kind, message FROM build_events WHERE build_id = %s "
                                "AND job_kind = 'modification' AND seq > %s ORDER BY seq LIMIT %s",
                                (modification_id, int(after), int(limit))).fetchall()
        return [{'seq': r[0], 'at': r[1].isoformat() if r[1] else None, 'kind': r[2], 'message': r[3]} for r in rows]

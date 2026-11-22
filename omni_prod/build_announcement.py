"""A failed build is said in the conversation, with one action (warehouse 77c, owner 2026-11-16).

Found: a customer whose build failed saw nothing in the conversation -- the failure lived only in the build tab, so a
customer who stayed in the chat waited for a build that had already ended. Method document part B section 9: every
state has a screen, a text, an action and a way out; there is no state change without a message in the conversation.

The worker calls `announce_if_failed` after the build job ends. It writes ONE assistant message to the project's
conversation (idempotent on `build-failed:<build_id>`), saying the build failed, whether the credits went back, and
offering exactly one action: "try again" (the approval screen) or, when only the customer can supply what is missing,
"complete the details". The reason itself is rendered by the UI from the error code (app.js friendlyError), so the
server keeps no second copy of those texts.
"""
from __future__ import annotations

import logging

from .models import BuildStatus

_LOG = logging.getLogger(__name__)

# Plain words (owner 2026-11-21): what happened, what happened to the money (only when the build's record says the
# reservation was released), and the one action -- named as its button is named in assets/app.js (actRetryBuild /
# editAll; tests/test_plain_words_failure_and_approval.py compares the two).
RETRY_BUTTON = {'he': 'לנסות לבנות שוב', 'en': 'Try building again'}
EDIT_BUTTON = {'he': 'עריכת הבקשה', 'en': 'Edit requirements'}
TEXT = {
    'he': {'failed': 'לא הצלחנו לבנות את האתר הפעם.', 'refunded': 'לא חויבתם.',
           'retry': 'אפשר לנסות שוב: לחצו על "' + RETRY_BUTTON['he'] + '".',
           'needs_input': 'חסר פרט שרק אתם יכולים לתת. כתבו אותו בבקשה: לחצו על "' + EDIT_BUTTON['he'] + '".'},
    'en': {'failed': 'We could not build the site this time.', 'refunded': 'You were not charged.',
           'retry': 'You can try again: press "' + RETRY_BUTTON['en'] + '".',
           'needs_input': 'A detail only you can give is missing. Add it to the request: press "' + EDIT_BUTTON['en'] + '".'},
}
CUSTOMER_FIXES = frozenset({'needs_customer_input'})


class FailureWitness:
    """Wraps the jobs repository for one run and remembers the transition to FAILED (with its error code and
    evidence). Every other call passes through unchanged."""

    def __init__(self, jobs):
        self._jobs = jobs
        self.failed: dict | None = None

    def __getattr__(self, name):
        return getattr(self._jobs, name)

    def transition(self, **kw):
        ok = self._jobs.transition(**kw)
        if kw.get('target') == BuildStatus.FAILED and ok is not False:
            self.failed = dict(kw)
        return ok


def message_for(*, build_id: str, error_code: str | None, billing: str | None, lang: str = 'he') -> dict:
    """The assistant message for a failed build: text + the one action."""
    T = TEXT['en' if lang == 'en' else 'he']
    customer = error_code in CUSTOMER_FIXES
    parts = [T['failed']]
    if billing == 'released':
        parts.append(T['refunded'])
    parts.append(T['needs_input'] if customer else T['retry'])
    action = ({'type': 'edit_requirements', 'build_id': build_id} if customer
              else {'type': 'retry_build', 'build_id': build_id})
    return {'content': ' '.join(parts),
            'interpretation': {'intent': 'build_failed', 'build_failed': build_id, 'error_code': error_code,
                               'actions': [action]}}


def announce_if_failed(witness: FailureWitness, *, conversation, request: dict | None, build_id: str) -> bool:
    """Write the failure into the conversation when the run ended FAILED. Never changes the build's outcome; a
    failure to write is logged as an error (loud), not swallowed in silence. Returns True when a message was written."""
    if witness.failed is None or conversation is None:
        return False
    request = request or {}
    project_id, account_id = request.get('public_project_id'), request.get('user_id')
    if not project_id or not account_id:
        _LOG.error('BUILD_FAILED_NOT_ANNOUNCED build=%s: the job request has no project or account', build_id)
        return False
    evidence = witness.failed.get('evidence_json') or {}
    msg = message_for(build_id=build_id, error_code=witness.failed.get('error_code'),
                      billing=evidence.get('billing'), lang=str(request.get('lang') or 'he'))
    try:
        conversation.add_message(project_id=project_id, account_id=str(account_id), role='assistant',
                                 content=msg['content'], interpretation=msg['interpretation'],
                                 request_key=f'build-failed:{build_id}')
    except Exception:
        _LOG.exception('BUILD_FAILED_NOT_ANNOUNCED build=%s: the conversation could not be written', build_id)
        return False
    return True

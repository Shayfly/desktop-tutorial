"""A failed build is said in the conversation, with one action (warehouse 77c, owner 2026-11-16).

Found: a customer whose build failed saw nothing in the conversation -- the failure lived only in the build tab, so a
customer who stayed in the chat waited for a build that had already ended. Method document part B section 9: every
state has a screen, a text, an action and a way out; there is no state change without a message in the conversation.

The worker calls `announce_if_failed` after the build job ends. It writes ONE assistant message to the project's
conversation (idempotent on `build-failed:<build_id>`), saying the build failed, whether the credits went back, and
offering exactly one action: "try again" (the approval screen) or, when only the customer can supply what is missing,
"complete the details". The build screen renders the error code's own line (app.js friendlyError).

Warehouse 132 (the owner, 2026-11-22): the message also says WHAT stopped the build, WHY it matters and the next
action, in the customer's words -- one sentence per finding from omni_prod/gate_words (at most MAX_SHOWN, what only
the customer can change first), read from the failed checks the build's evidence carries. The one action follows the
findings: a finding only the customer can fix makes it "edit the request". A finding with no words is logged as an
error (BUILD_FINDING_UNWORDED) and left out; with none worded, the message keeps its general sentence: never a raw
check name, never no message.
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
    # Arabic (warehouse 132): the screen has no Arabic button labels yet, so the button is the one under the message.
    'ar': {'failed': 'لم نتمكن من بناء الموقع هذه المرة.', 'refunded': 'لم يُخصم منكم أي مبلغ.',
           'retry': 'يمكنكم المحاولة مرة أخرى بالضغط على الزر الذي تحت هذه الرسالة.',
           'needs_input': 'ينقص تفصيل لا يستطيع أحد غيركم أن يعطيه. أضيفوه إلى الطلب بالضغط على الزر الذي تحت هذه الرسالة.'},
}
# More findings than MAX_SHOWN: the rest are counted, not listed.
MORE = {'he': 'ועוד {n} דברים כאלה.', 'en': 'And {n} more like these.', 'ar': 'وهناك {n} أمور أخرى مثلها.'}
MAX_SHOWN = 3
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


def message_for(*, build_id: str, error_code: str | None, billing: str | None, lang: str = 'he',
                findings=()) -> dict:
    """The assistant message for a failed build: text + the one action. `findings`: gate_words keys (gate_words.
    findings), said one sentence each before the action; empty = the general sentence alone, as before."""
    lang = lang if lang in TEXT else 'en'   # #505: an Arabic customer reads English, not Hebrew, until Arabic is written
    T = TEXT[lang]
    customer = error_code in CUSTOMER_FIXES
    parts = [T['failed']]
    final = None
    keys, said = [], []
    if findings:
        from . import gate_words
        for k in findings:
            try:
                said.append(gate_words.words(k, lang))
                keys.append(k)
            except gate_words.NoWords as exc:     # D3: logged and left out, never a crash in the worker's finally
                _LOG.error('BUILD_FINDING_UNWORDED build=%s: %s -- not said', build_id, exc)
    if said:
        customer = customer or any(w['action'] == 'edit' for w in said)
        step = 'edit' if customer else 'retry'
        # D2 (review 2026-11-22): the button is named once, at the end. One finding's own step is said as it is;
        # findings with different steps of the same action share that action's general step.
        steps = list(dict.fromkeys(w['next'] for w in said if w['action'] == step))
        final = steps[0] if len(steps) == 1 else (gate_words.NEXT[lang][step] if steps else None)
        for w in said[:MAX_SHOWN]:
            parts.append(f"{w['what']} — {w['why']}.")
        if len(said) > MAX_SHOWN:
            parts.append(MORE[lang].format(n=len(said) - MAX_SHOWN))
    if billing == 'released':
        parts.append(T['refunded'])
    parts.append(final or (T['needs_input'] if customer else T['retry']))
    action = ({'type': 'edit_requirements', 'build_id': build_id} if customer
              else {'type': 'retry_build', 'build_id': build_id})
    return {'content': ' '.join(parts),
            'interpretation': {'intent': 'build_failed', 'build_failed': build_id, 'error_code': error_code,
                               **({'findings': keys} if keys else {}),
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
    from . import gate_words
    keys, unworded = gate_words.collect(gate_words.verification_failures(evidence),
                                        error_code=witness.failed.get('error_code'),
                                        error_message=witness.failed.get('error_message'))
    for reason in unworded:                   # D1: each one loud; the worded findings are still said
        _LOG.error('BUILD_FINDING_UNWORDED build=%s: %s -- not said', build_id, reason)
    msg = message_for(build_id=build_id, error_code=witness.failed.get('error_code'),
                      billing=evidence.get('billing'), lang=str(request.get('lang') or 'he'), findings=keys)
    try:
        conversation.add_message(project_id=project_id, account_id=str(account_id), role='assistant',
                                 content=msg['content'], interpretation=msg['interpretation'],
                                 request_key=f'build-failed:{build_id}')
    except Exception:
        _LOG.exception('BUILD_FAILED_NOT_ANNOUNCED build=%s: the conversation could not be written', build_id)
        return False
    return True

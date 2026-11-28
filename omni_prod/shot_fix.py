"""The customer sees their build in the conversation, takes a screenshot of it, and the model fixes the exact component
(warehouse 124, the owner 2026-11-21; released 2026-11-27, inbox/004).

What the customer does: opens the build card in the conversation (a phone / desktop switch, the build id on it), takes a
screenshot with their own device, and uploads it to the same conversation. What this module does with it, in order -- and
each step writes ONE evidence line (STAGES), kept even when the fix fails:

  receipt     the image is checked by its own bytes (attachments.validate_image) and the window width is recorded
  reduction   the long side is brought down to MAX_SIDE (1,400 px); the original AND the reduced copy are stored
  model_call  a vision model gets the reduced image, the window width, the build id and the build's own sources, with ONE
              instruction: the picture is a POINTER to what is wrong, never a brief
  edit        its answer is an exact edit block {path, old, new} on files of THIS build, applied exactly once, all or none
              (repair_edits.resolve_edits, #462); an answer that brings whole files, or an `old` that is most of a file, is
              refused, and the files nobody touched are byte-identical
  result      what the customer reads, with the next action

The edit is NOT applied here. The customer approves it once, and it goes through the existing modification pipeline, whose
candidate is these exact edits (modification_engine: the same sandbox, quality, security and rights gates as any change).
A route that patched a stored version without the gates is the known fake path (omni_prod/investor_app legacy_paths_guard).

The owner's rules, each held in code and by a mutation (tests/negative_controls/shot_fix_124.json):
  1. the image is a pointer, never a brief: no rebuilding from it (answer_edits);
  2. the window width is stored with the image and given to the model (the record and the user message);
  3. an image round is not a turn: its model call is reserved under its own budget scope (budget.PURPOSES 'shot-fix'), so the
     conversation's turn counter and its cost cap never move;
  4. the image is kept as evidence of the build, whether or not the fix worked (the record is written in every outcome);
  5. the image is reduced before the model reads it (shrink);
  6. the model is a focused candidate of its own (task 'screenshot_fix', vision models only), never the conversation agent's;
  7. no screen of its own and no frame that takes the conversation over: the card is the one of the direction sketch.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import time
from dataclasses import dataclass

from . import attachments as A
from . import repair_edits as RE

_LOG = logging.getLogger(__name__)

SCHEMA = '148ai.shot_fix/1'
TASK = 'screenshot_fix'                 # the model call's task (task_policy), quoted and reserved as this and nothing else
PURPOSE = 'shot-fix'                    # the budget scope's name (budget.PURPOSES): an image round is not a turn
MAX_SIDE = 1400                         # warehouse 124 rule 5: the long side the model reads
WIDTH_MIN, WIDTH_MAX = 240, 3840        # the window width of a screenshot, in CSS pixels
STAGES = ('receipt', 'reduction', 'model_call', 'edit', 'result')
LANGS = ('he', 'ar', 'en')
MAX_EDITS, MAX_OLD, MAX_NEW = 6, 1500, 3000
MAX_SHARE = 0.6                         # an `old` that is this much of a file of 1,000 characters or more is a rebuild
MAX_SOURCE_CHARS = 40_000               # the build's sources the model is shown (bounded, the quote counts them)
MAX_NOTE, MAX_FIELD = 500, 200
MARK = '[shot-fix edits v1]'            # first line of the followup of a modification that carries exact edits
REBUILD_KEYS = ('files', 'repository', 'page', 'html', 'rebuild', 'site', 'project')
SOURCE_EXT = ('.html', '.htm', '.css', '.js', '.mjs', '.jsx', '.tsx', '.ts', '.vue', '.svelte')
MODES = ('off', 'on')


class ShotError(ValueError):
    """The request is refused before anything is stored. `code` is machine-readable; `status` the HTTP status."""

    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.status = code, status


class ShotReadFailed(Exception):
    """The model's reading did not produce an answer. `code` is one of FAILURES; `detail` is for the log and the evidence."""

    def __init__(self, code: str, detail: str = ''):
        super().__init__(f'{code}: {detail}')
        self.code, self.detail = code, detail


FAILURES = ('not_connected', 'busy', 'late', 'unreadable', 'cannot_tell', 'rebuild_refused', 'invalid_answer',
            'no_edit', 'edit_not_applicable', 'version_unavailable')


def mode() -> str:
    """OMNI_SHOT_FIX: 'off' (the default: the screenshot is kept and the customer is told) or 'on'. Any other value raises."""
    value = os.environ.get('OMNI_SHOT_FIX', 'off').strip().lower()
    if value not in MODES:
        raise ValueError(f'OMNI_SHOT_FIX must be one of {MODES}, not {value!r}')
    return value


# ------------------------------------------------------------------------------------------- the image

@dataclass(frozen=True)
class Shrunk:
    data: bytes
    mime: str
    width: int
    height: int
    original_width: int
    original_height: int
    scaled: bool
    sha256: str
    original_sha256: str


def check_width(value) -> int:
    """The window width the screenshot was taken at: a whole number of CSS pixels, never a guess."""
    if isinstance(value, bool) or not isinstance(value, int) or not WIDTH_MIN <= value <= WIDTH_MAX:
        raise ShotError('bad_width', f'the window width must be a whole number from {WIDTH_MIN} to {WIDTH_MAX}')
    return value


def shrink(data: bytes) -> Shrunk:
    """The image with its long side at most MAX_SIDE, same format, same aspect, never enlarged. An image already that small
    is returned as it is (the reduction line says so)."""
    mime, w, h = A.validate_image(data)
    original_sha = hashlib.sha256(data).hexdigest()
    if max(w, h) <= MAX_SIDE:
        return Shrunk(data, mime, w, h, w, h, False, original_sha, original_sha)
    from PIL import Image
    scale = MAX_SIDE / max(w, h)
    size = (max(1, min(MAX_SIDE, round(w * scale))), max(1, min(MAX_SIDE, round(h * scale))))
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        small = img.resize(size, Image.LANCZOS)
    out = io.BytesIO()
    if mime == 'image/png':
        small.save(out, 'PNG', optimize=True)
    elif mime == 'image/webp':
        small.save(out, 'WEBP', quality=85)
    else:
        small.convert('RGB').save(out, 'JPEG', quality=85)
    blob = out.getvalue()
    mime2, w2, h2 = A.validate_image(blob)
    if max(w2, h2) > MAX_SIDE or mime2 != mime:
        raise ShotError('reduction_failed', 'the reduced image is not what was asked for', 500)
    return Shrunk(blob, mime2, w2, h2, w, h, True, hashlib.sha256(blob).hexdigest(), original_sha)


# ------------------------------------------------------------------------------------------- the evidence lines

class Evidence:
    """One line per stage, in order. A line is written when its stage ends, whatever it ended in."""

    def __init__(self, build_id: str):
        self.build_id, self.lines = build_id, []

    def add(self, stage: str, ok: bool, **fields) -> dict:
        if stage not in STAGES or any(line['stage'] == stage for line in self.lines):
            raise ValueError(f'stage {stage!r} is unknown or already written')
        line = {'stage': stage, 'ok': bool(ok), 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **fields}
        self.lines.append(line)
        _LOG.info('SHOT_FIX_EVIDENCE build=%s stage=%s ok=%s %s', self.build_id, stage, ok,
                  ' '.join(f'{k}={v}' for k, v in fields.items() if not isinstance(v, (dict, list)))[:400])
        return line

    def close(self, outcome: str) -> list[dict]:
        """The five lines, each stage that did not run said as skipped, so the record always has all five."""
        for stage in STAGES:
            if not any(line['stage'] == stage for line in self.lines):
                self.add(stage, False, skipped=True, because=outcome)
        return sorted(self.lines, key=lambda line: STAGES.index(line['stage']))


# ------------------------------------------------------------------------------------------- the model's side

SYSTEM = (
    'You fix ONE visual defect in a website a customer already has. The customer sends a screenshot of their own site, taken at a '
    'window width given in the message, from the build named in it. The screenshot is a POINTER to what is wrong, never a brief: '
    'never redesign, never rebuild, never rewrite a page or a file from the picture.\n'
    'Answer with one JSON object and nothing else:\n'
    '{"finding": {"section": "...", "component": "...", "what": "..."}, "edits": [{"path": "...", "old": "...", "new": "..."}], '
    '"reply": "..."}\n'
    '- "finding" says in the customer\'s language, in plain words and without any code, which part of the page (section), which '
    'element (component, for example "the booking button under the first heading") and what is wrong with it ("the button falls '
    'below the screen edge on a phone").\n'
    '- "edits" are exact edit blocks on the files shown, and nothing else: "path" is one of the files shown; "old" is text copied '
    'exactly from that file (whitespace included) that occurs there ONCE and is only the lines of that component; "new" replaces '
    'it. Change only that component. Do not send whole files, a new page or a list of files.\n'
    '- "reply" is one or two sentences to the customer, in their language, saying what you changed.\n'
    'If you cannot tell which component is wrong from the picture, answer {"cannot_tell": "one sentence in the customer\'s '
    'language asking where"} and no edits.')


def source_files(work: dict) -> dict[str, str]:
    """The build's own sources the model may edit: web source files only, smallest first, up to MAX_SOURCE_CHARS in all. A file
    that does not fit is not shown and so cannot be edited: the answer is checked against exactly this list."""
    out, used = {}, 0
    for path, text in sorted(((p, t) for p, t in work.items() if isinstance(t, str) and p.lower().endswith(SOURCE_EXT)
                              and not any(part in ('node_modules', 'vendor', '.omni', 'dist') for part in p.split('/'))
                              and not p.lower().endswith(('.min.js', '.min.css', '.bundle.js'))),
                             key=lambda pt: (len(pt[1]), pt[0])):
        if used + len(text) > MAX_SOURCE_CHARS:
            continue
        out[path], used = text, used + len(text)
    return out


def user_message(*, build_id: str, version_id: str, width: int, lang: str, note: str, files: dict) -> str:
    """What the model is told besides the picture: the window width and the build id travel with it (rule 2)."""
    return json.dumps({'build_id': build_id, 'version_id': version_id, 'viewport_width': width, 'language': lang,
                       'customer_note': note[:MAX_NOTE], 'files': files}, ensure_ascii=False)


@dataclass(frozen=True)
class Fix:
    finding: dict
    edits: list
    paths: list
    reply: str
    fingerprint: str
    new_work: dict


def _field(value, limit=MAX_FIELD) -> str:
    return ' '.join(str(value or '').split())[:limit]


def answer_edits(raw, work: dict, *, build_id: str, version_id: str) -> Fix:
    """The model's answer as an exact fix on `work` (the files shown to it), or a ShotReadFailed. The files nobody touched are
    byte-identical in `new_work`: checked here, not assumed."""
    if not isinstance(raw, dict):
        raise ShotReadFailed('invalid_answer', f'the answer is a {type(raw).__name__}, not an object')
    if raw.get('cannot_tell'):
        raise ShotReadFailed('cannot_tell', _field(raw.get('cannot_tell'), 300))
    if any(key in raw for key in REBUILD_KEYS):               # rule 1: the picture is a pointer, never a brief
        raise ShotReadFailed('rebuild_refused', f'the answer carries {[k for k in REBUILD_KEYS if k in raw]}, not edit blocks')
    edits = raw.get('edits')
    if not isinstance(edits, list) or not edits:
        raise ShotReadFailed('no_edit', 'the answer holds no edit block')
    if len(edits) > MAX_EDITS:
        raise ShotReadFailed('rebuild_refused', f'{len(edits)} edit blocks: a fix of one component is at most {MAX_EDITS}')
    clean = []
    for e in edits:
        if not (isinstance(e, dict) and all(isinstance(e.get(k), str) for k in ('path', 'old', 'new'))):
            raise ShotReadFailed('invalid_answer', 'an edit block is {"path", "old", "new"}, all text')
        if e['old'] == e['new']:
            raise ShotReadFailed('no_edit', 'an edit block changes nothing')
        if len(e['old']) > MAX_OLD or len(e['new']) > MAX_NEW:
            raise ShotReadFailed('rebuild_refused', 'an edit block this large is not one component')
        clean.append({'path': e['path'], 'old': e['old'], 'new': e['new']})
    texts, misses = RE.resolve_edits(work, clean)
    if misses:
        raise ShotReadFailed('edit_not_applicable', json.dumps(misses, ensure_ascii=False)[:600])
    from .repository_patch import normalize_repo_path
    for path in texts:                                         # an `old` that is most of a file is a rebuild in disguise
        replaced = sum(len(e['old']) for e in clean if normalize_repo_path(e['path']) == path)
        if len(work[path]) >= 1000 and replaced >= MAX_SHARE * len(work[path]):
            raise ShotReadFailed('rebuild_refused', f'the edits on {path} replace most of the file')
    new_work = {**work, **texts}
    untouched = [p for p in work if p not in texts]
    if any(new_work[p] != work[p] for p in untouched) or set(new_work) != set(work):
        raise ShotReadFailed('rebuild_refused', 'a file nobody asked to touch changed')
    finding = raw.get('finding') if isinstance(raw.get('finding'), dict) else {}
    finding = {k: _field(finding.get(k)) for k in ('section', 'component', 'what')}
    paths = sorted(texts)
    fingerprint = hashlib.sha256(json.dumps({'build': build_id, 'version': version_id, 'edits': clean},
                                            sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    return Fix(finding, clean, paths, _field(raw.get('reply'), 600), fingerprint, new_work)


def followup_for(record: dict) -> str:
    """The followup of the modification that applies a stored fix: the mark, the exact edits, and the finding in words."""
    fix = record['fix']
    said = ' / '.join(x for x in (fix['finding'].get('section'), fix['finding'].get('component'), fix['finding'].get('what')) if x)
    return f'{MARK}{json.dumps(fix["edits"], ensure_ascii=False)}\n{said or "screenshot fix"}'


def edits_of(followup: str):
    """The exact edits a modification's followup carries, or None when it carries none (an ordinary followup). A mark with edits
    that do not parse raises ValueError: never a guess."""
    if not isinstance(followup, str) or not followup.startswith(MARK):
        return None
    body = followup[len(MARK):].split('\n', 1)[0]
    edits = json.loads(body)
    if not isinstance(edits, list) or not edits:
        raise ValueError('a shot-fix followup carries no edit block')
    return edits


# ------------------------------------------------------------------------------------------- the customer's words

BUTTON = {'he': 'לתקן את זה', 'ar': 'إصلاح ذلك', 'en': 'Fix this'}
TEXT = {
    'he': {'uploaded': 'צירפתי צילום מסך של האתר',
           'fixed': 'ראיתי את זה: {what}. מצאתי את הרכיב ואת התיקון, והצילום נשמר. כדי לתקן לחצו על "{button}": רק הרכיב הזה ישתנה, ושאר האתר יישאר כמו שהוא.',
           'applied_hint': 'אפשר לצלם שוב אחרי התיקון, ונמשיך משם.',
           'not_connected': 'הצילום נשמר, אבל עדיין אין לנו דרך לקרוא אותו. כתבו לי כאן במילים איפה הבעיה, באיזה חלק של העמוד, ואטפל בזה.',
           'busy': 'הצילום נשמר, אבל הקריאה שלו עוד לא הסתיימה ואנחנו לא מחכים לה. נסו להעלות את הצילום שוב בעוד כמה דקות.',
           'late': 'הצילום נשמר, אבל הקריאה שלו לא הסתיימה בזמן. זה אצלנו, לא אצלכם: נסו להעלות אותו שוב בעוד כמה דקות.',
           'unreadable': 'הצילום נשמר, אבל לא הצלחנו לקרוא אותו הפעם. זה אצלנו, לא אצלכם: נסו להעלות אותו שוב בעוד כמה דקות.',
           'cannot_tell': 'הצילום נשמר, אבל לא הצלחתי לדעת מה בדיוק השתבש. כתבו לי כאן באיזה חלק של העמוד ומה לא נראה נכון, ואנסה שוב.',
           'unfixed': 'הצילום נשמר, אבל לא מצאתי דרך בטוחה לתקן את זה בלי לשנות דברים אחרים ולכן לא שיניתי כלום. כתבו לי כאן איפה הבעיה במילים, ואטפל בזה.',
           'version_unavailable': 'הצילום נשמר, אבל לא הצלחנו לפתוח את הגרסה שצולמה. זה אצלנו, לא אצלכם: נסו שוב בעוד כמה דקות.'},
    'ar': {'uploaded': 'أرفقت لقطة شاشة للموقع',
           'fixed': 'رأيت ذلك: {what}. وجدت العنصر والإصلاح، وحُفظت اللقطة. للإصلاح اضغطوا على "{button}": سيتغير هذا العنصر فقط، وسيبقى باقي الموقع كما هو.',
           'applied_hint': 'يمكنكم التقاط لقطة جديدة بعد الإصلاح ونكمل من هناك.',
           'not_connected': 'حُفظت اللقطة، لكن ليست لدينا طريقة لقراءتها بعد. اكتبوا لي هنا بكلماتكم أين المشكلة، وفي أي جزء من الصفحة، وسأتولى الأمر.',
           'busy': 'حُفظت اللقطة، لكن قراءتها لم تنتهِ ولا ننتظرها. حاولوا رفع اللقطة مرة أخرى بعد بضع دقائق.',
           'late': 'حُفظت اللقطة، لكن قراءتها لم تنتهِ في الوقت المناسب. هذا من جهتنا وليس من جهتكم: حاولوا رفعها مرة أخرى بعد بضع دقائق.',
           'unreadable': 'حُفظت اللقطة، لكننا لم ننجح في قراءتها هذه المرة. هذا من جهتنا وليس من جهتكم: حاولوا رفعها مرة أخرى بعد بضع دقائق.',
           'cannot_tell': 'حُفظت اللقطة، لكنني لم أستطع معرفة ما الذي حدث بالضبط. اكتبوا لي هنا في أي جزء من الصفحة وما الذي لا يبدو صحيحا، وسأحاول مرة أخرى.',
           'unfixed': 'حُفظت اللقطة، لكنني لم أجد طريقة آمنة للإصلاح دون تغيير أشياء أخرى، ولذلك لم أغيّر شيئا. اكتبوا لي هنا بكلماتكم أين المشكلة وسأتولى الأمر.',
           'version_unavailable': 'حُفظت اللقطة، لكننا لم ننجح في فتح النسخة التي صُوّرت. هذا من جهتنا وليس من جهتكم: حاولوا مرة أخرى بعد بضع دقائق.'},
    'en': {'uploaded': 'I attached a screenshot of the site',
           'fixed': 'I see it: {what}. I found the element and the fix, and the screenshot is saved. To fix it press "{button}": only that element changes and the rest of the site stays as it is.',
           'applied_hint': 'You can take a new screenshot after the fix and we will go on from there.',
           'not_connected': 'The screenshot is saved, but we cannot read it yet. Write to me here in your own words where the problem is, in which part of the page, and I will take care of it.',
           'busy': 'The screenshot is saved, but reading it has not finished and we are not waiting for it. Try uploading the screenshot again in a few minutes.',
           'late': 'The screenshot is saved, but reading it did not finish in time. This is on our side, not yours: try uploading it again in a few minutes.',
           'unreadable': 'The screenshot is saved, but we could not read it this time. This is on our side, not yours: try uploading it again in a few minutes.',
           'cannot_tell': 'The screenshot is saved, but I could not tell what exactly went wrong. Write to me here which part of the page and what does not look right, and I will try again.',
           'unfixed': 'The screenshot is saved, but I found no safe way to fix it without changing other things, so I changed nothing. Write to me here where the problem is in your own words and I will take care of it.',
           'version_unavailable': 'The screenshot is saved, but we could not open the version that was photographed. This is on our side, not yours: try again in a few minutes.'},
}
UNFIXED = ('rebuild_refused', 'invalid_answer', 'no_edit', 'edit_not_applicable')


def sentence(code: str, lang: str, *, what: str = '') -> str:
    """What the customer reads for a result code: one sentence with the next action. An unknown code raises."""
    if lang not in LANGS:
        raise ValueError(f'no shot-fix words in {lang!r}; the languages are {LANGS}')
    if code == 'fix_ready':
        return TEXT[lang]['fixed'].format(what=what or '…', button=BUTTON[lang])
    key = 'unfixed' if code in UNFIXED else code
    if key not in TEXT[lang] or key in ('uploaded', 'fixed', 'applied_hint'):
        raise ValueError(f'no customer words for the shot-fix result {code!r}')
    return TEXT[lang][key]


# ------------------------------------------------------------------------------------------- the reading, reserved

class NotConnectedReader:
    name = 'off'

    def read(self, **_):
        raise ShotReadFailed('not_connected', 'OMNI_SHOT_FIX is off, or no reservation service is configured on this host')


class FailedReader:
    """A reader that cannot read, and says why: the round is still stored whole (rule 4)."""
    name = 'unavailable'

    def __init__(self, code: str, detail: str):
        self.code, self.detail = code, detail

    def read(self, **_):
        raise ShotReadFailed(self.code, self.detail)


class ReservedShotReader:
    """The vision call, reserved first and run by the worker (as every paid intake call, Issue #12): QUOTE the worst case, RESERVE
    under the budget scope 'shot-fix' (rule 3: not a turn of the conversation), enqueue, wait a bounded time, read the settled
    result. The API host builds no gateway. A quote, a budget or a queue that fails is a ShotReadFailed with its code: nothing was
    sent, and the customer is told in words."""
    name = 'reserved'

    def __init__(self, service, enqueue, *, account_id: str, project_id: str, request_key: str | None, caps,
                 wait_seconds: float | None = None, sleep=time.sleep, clock=time.monotonic):
        self.svc, self.enqueue = service, enqueue
        self.account_id, self.project_id, self.request_key, self.caps = account_id, project_id, request_key, caps
        self.wait = float(os.getenv('OMNI_SHOT_FIX_WAIT_SECONDS', '25')) if wait_seconds is None else wait_seconds
        self.sleep, self.clock = sleep, clock
        self.reservation_id = self.model = self.cost_state = None

    def read(self, *, system: str, user: str, image: bytes, max_tokens: int = 2500) -> dict:
        import base64
        from .intake import budget as B
        try:
            quote = B.quote(system=system, user=user, max_tokens=max_tokens, task=TASK, images=1, routed_only=True)
        except B.QuoteUnavailable as exc:
            raise ShotReadFailed('not_connected', f'no quote: {exc}') from exc
        key = f'{TASK}:{self.account_id}:{self.project_id}:{self.request_key or time.time_ns()}:{hashlib.sha256(user.encode()).hexdigest()[:16]}'
        try:
            r = self.svc.reserve(idempotency_key=key[:300], account_id=self.account_id, project_id=self.project_id, quote_=quote,
                                 caps=self.caps, purpose=PURPOSE,
                                 payload={'system': system, 'user': user, 'max_tokens': max_tokens, 'task': TASK,
                                          'images_b64': [base64.b64encode(image).decode('ascii')], 'prompt_version': SCHEMA})
        except B.BudgetExceeded as exc:
            raise ShotReadFailed('busy', f'budget {exc.scope.split(":")[0]} reached') from exc
        except Exception as exc:                       # BudgetError, ValueError, a database that is not there: fail closed
            raise ShotReadFailed('not_connected', f'{type(exc).__name__}: {str(exc)[:200]}') from exc
        self.reservation_id = r.id
        if r.state == B.RESERVED:
            try:
                self.enqueue(r.id)
                self.svc.mark_enqueued(r.id)
            except Exception as exc:                   # nothing was sent: the money is given back at once
                self.svc.release(r.id, reason=f'enqueue failed: {type(exc).__name__}')
                raise ShotReadFailed('not_connected', f'the queue is not reachable: {type(exc).__name__}') from exc
        deadline = self.clock() + self.wait
        current = self.svc.get(r.id, account_id=self.account_id)
        while current is not None and current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED) and self.clock() < deadline:
            self.sleep(0.3)
            current = self.svc.get(r.id, account_id=self.account_id)
        if current is None or current.state not in (B.SETTLED, B.UNKNOWN, B.RELEASED):
            raise ShotReadFailed('late', f'reservation {r.id} had not settled in {self.wait} s; it settles on its own')
        self.model, self.cost_state = current.model, current.cost_state
        result = current.result or {}
        if current.state == B.RELEASED:
            raise ShotReadFailed('busy', 'released: ' + str(current.failure_reason)[:200])
        if current.state == B.UNKNOWN or not result.get('ok'):
            raise ShotReadFailed('unreadable', str(result.get('error') or current.failure_reason)[:300])
        return result.get('raw')


def reader_for(supervisor, *, account_id: str, project_id: str, request_key: str | None):
    """The reader for this host: off (the default) says so in words; on needs the reservation service and the queue, and a
    per-project cap that the owner sets (OMNI_SHOT_FIX_PROJECT_USD: no default, because it is spend)."""
    if mode() == 'off':
        return NotConnectedReader()
    svc, enqueue = getattr(supervisor, 'reservations', None), getattr(supervisor, 'enqueue', None)
    cap = os.environ.get('OMNI_SHOT_FIX_PROJECT_USD', '').strip()
    if svc is None or enqueue is None or not cap:
        return NotConnectedReader()
    from decimal import Decimal, InvalidOperation
    from .intake import budget as B
    try:
        caps = B.Caps(project_usd=Decimal(cap), daily_usd=Decimal(os.environ.get('OMNI_INTAKE_DAILY_BUDGET_USD', '5')),
                      project_turns=None)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'OMNI_SHOT_FIX_PROJECT_USD is not a positive amount: {cap!r}') from exc
    return ReservedShotReader(svc, enqueue, account_id=account_id, project_id=project_id, request_key=request_key, caps=caps)


# ------------------------------------------------------------------------------------------- one round

def round_of(*, project_id: str, account_id: str, build_id: str, version_id: str, work: dict, data: bytes, width, note: str,
             lang: str, repo, reader, store, request_key: str | None = None) -> dict:
    """One image round, end to end. Returns the stored record. The two images are stored, and the record -- with its five lines
    -- is written in every outcome (rule 4); only a request refused up front (a bad image, a bad width) stores nothing."""
    if lang not in LANGS:
        raise ValueError(f'no shot-fix words in {lang!r}; the languages are {LANGS}')
    width = check_width(width)
    note = ' '.join(str(note or '').split())[:MAX_NOTE]
    ev = Evidence(build_id)
    mime, w, h = A.validate_image(data)                                  # an unreadable file is refused here, before any storage
    ev.add('receipt', True, build_id=build_id, version_id=version_id, viewport_width=width, bytes=len(data), mime=mime, width=w,
           height=h, sha256=hashlib.sha256(data).hexdigest())
    shrunk = shrink(data)
    original = repo.create(project_id=project_id, account_id=account_id, kind='screenshot', data=data,
                           annotation={'note': f'build {build_id} at {width}px'})
    reduced = original if not shrunk.scaled else repo.create(
        project_id=project_id, account_id=account_id, kind='screenshot', data=shrunk.data,
        annotation={'note': f'build {build_id} at {width}px, reduced to {shrunk.width}x{shrunk.height}'})
    ev.add('reduction', True, scaled=shrunk.scaled, original={'attachment_id': original['id'], 'sha256': shrunk.original_sha256,
                                                              'width': shrunk.original_width, 'height': shrunk.original_height},
           reduced={'attachment_id': reduced['id'], 'sha256': shrunk.sha256, 'width': shrunk.width, 'height': shrunk.height},
           max_side=MAX_SIDE)
    shot_id = f'shot_{hashlib.sha256((build_id + shrunk.original_sha256 + str(width)).encode()).hexdigest()[:20]}'
    record = {'schema': SCHEMA, 'shot_id': shot_id, 'build_id': build_id, 'version_id': version_id, 'viewport_width': width,
              'note': note, 'language': lang,
              'original': {'attachment_id': original['id'], 'sha256': shrunk.original_sha256},
              'reduced': {'attachment_id': reduced['id'], 'sha256': shrunk.sha256, 'width': shrunk.width, 'height': shrunk.height},
              'outcome': None, 'fix': None}
    store.add_message(project_id=project_id, account_id=account_id, role='customer', content=TEXT[lang]['uploaded'],
                      request_key=request_key,
                      interpretation={'attachments': [{'id': original['id'], 'kind': 'screenshot'}], 'label': True,
                                      'shot': {'shot_id': shot_id, 'build_id': build_id, 'viewport_width': width}})
    outcome, fix, reply = 'unreadable', None, None
    try:
        shown = source_files(work)
        user = user_message(build_id=build_id, version_id=version_id, width=width, lang=lang, note=note, files=shown)
        try:
            raw = reader.read(system=SYSTEM, user=user, image=shrunk.data)
            ev.add('model_call', True, reader=getattr(reader, 'name', '?'), model=getattr(reader, 'model', None),
                   cost_state=getattr(reader, 'cost_state', None), reservation_id=getattr(reader, 'reservation_id', None),
                   viewport_width=width, build_id=build_id, image_long_side=max(shrunk.width, shrunk.height), files_shown=sorted(shown))
        except ShotReadFailed as exc:
            ev.add('model_call', False, reader=getattr(reader, 'name', '?'), code=exc.code, detail=exc.detail[:300],
                   reservation_id=getattr(reader, 'reservation_id', None))
            raise
        try:
            fix = answer_edits(raw, shown, build_id=build_id, version_id=version_id)
            ev.add('edit', True, paths=fix.paths, edits=len(fix.edits), fingerprint=fix.fingerprint)
        except ShotReadFailed as exc:
            ev.add('edit', False, code=exc.code, detail=exc.detail[:300])
            raise
        outcome = 'fix_ready'
        reply = sentence('fix_ready', lang, what=fix.finding.get('what', ''))
        record['fix'] = {'fingerprint': fix.fingerprint, 'finding': fix.finding, 'edits': fix.edits, 'paths': fix.paths}
    except ShotReadFailed as exc:
        outcome = exc.code
        reply = sentence(exc.code, lang)
        _LOG.warning('SHOT_FIX_NOT_FIXED build=%s code=%s detail=%s', build_id, exc.code, exc.detail[:300])
    finally:
        record['outcome'] = outcome
        ev.add('result', outcome == 'fix_ready', outcome=outcome)
        record['evidence'] = ev.close(outcome)
        actions = ([{'type': 'apply_shot_fix', 'shot_id': shot_id, 'fingerprint': fix.fingerprint, 'build_id': build_id,
                     'version_id': version_id, 'label': BUTTON[lang]}] if outcome == 'fix_ready' and fix else [])
        store.add_message(project_id=project_id, account_id=account_id, role='assistant',
                          content=reply or sentence('unreadable', lang), request_key=request_key,
                          interpretation={'shot_fix': record, 'actions': actions, 'language': lang})
    return record


# ------------------------------------------------------------------------------------------- reading the records back

def records(messages) -> list[dict]:
    """Every shot-fix record of a conversation, oldest first."""
    return [m['interpretation']['shot_fix'] for m in messages or []
            if m.get('role') == 'assistant' and isinstance(m.get('interpretation'), dict)
            and isinstance(m['interpretation'].get('shot_fix'), dict)]


def records_for_build(messages, build_id: str) -> list[dict]:
    """What the build's evidence shows of its screenshots: both images (by id and digest), the width, the five lines."""
    return [r for r in records(messages) if r.get('build_id') == build_id]


def record_for_fix(messages, fingerprint: str) -> dict | None:
    return next((r for r in reversed(records(messages)) if (r.get('fix') or {}).get('fingerprint') == fingerprint), None)

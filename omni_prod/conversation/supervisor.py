"""Conversation Supervisor (Unified Conversation OS §1-2, §4).

One persistent conversation per project. Each customer message is routed by
a DETERMINISTIC intent classifier (no model cost for routing) to existing
services:

  requirements    -> intake interpreter + confidence policy -> new brief revision
  answer          -> a quick-reply to an open question (same validated path as discovery)
  missing         -> open material questions / contradictions from the brief
  recommend       -> the recommended defaults and the provisional plan
  cost            -> credits + the plan's authorized model budget (no invented prices)
  feasibility     -> "can we add payments (later)?" -> feasibility gate on that capability
  approve         -> the approval ACTION (the customer still clicks; never auto-builds)
  status          -> durable build/agent task records
  modify          -> an existing version exists: offers the modification pipeline (customer confirms)

After any brief change the Chief Architect re-plans (deterministic, $0) and the
plan is stored as PROPOSED for that brief fingerprint. Nothing paid starts here.
A model is used only for interpretation, only when OMNI_INTAKE_MODEL=1, only
within the per-project conversation budget, and only through the routed
gateway's `conversation` task class (cheap models allowed; never for
architecture). Chat history is not the source of truth: the brief, plans,
builds and versions are.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from decimal import Decimal

from .. import discovery as d
from ..intake import agent as intake_agent
from ..intake import approval_flow as AF      # the buttons' names, said in the texts below exactly as the buttons carry them
from ..intake import contract as C
from ..intake import media_reading as MR    # warehouse 128: a file's reading is a draft the customer approves first
from ..intake.interpreter import DeterministicInterpreter, interpreter_from_env, language_of


class _AtLimit(DeterministicInterpreter):
    """The pre-check refused the paid call because a conversation limit is reached: the free interpreter answers, and
    the limit is carried as a typed outcome (owner 2026-11-18), never as the "provider is busy" text."""

    def __init__(self, kind: str, reason: str, source: str = 'precheck'):
        self.kind, self.reason, self.source = kind, reason, source

    def interpret(self, message, brief=None):
        out = super().interpret(message, brief)
        out.limit = {'kind': self.kind, 'source': self.source}
        out.dropped.append(f'model not used: {self.reason}')
        return out
from ..planning import feasibility as F
from ..planning.architect import ChiefArchitect

# #330 (Michael 2026-11-12 19:45) set a limit on how often the customer-only question was written out; since
# Michael 2026-11-13 it is never written out (the card asks), so there is no count to keep.
# Michael 2026-11-13 (#339 condition): a limit on how often the SAME card (question + buttons) is shown unanswered.
# After CARD_LIMIT shows: a privacy-safe default where one exists (nothing personal is stored), otherwise a block --
# the card stops repeating, the turn says what is missing, with a direct link to the "Requirements" tab.
CARD_LIMIT = 3
SAFE_DEFAULT = {'personal_data': 'no', 'access_scope': 'no_personal'}
SAFE_CONFIDENCE = d.SAFE_DEFAULT_CONFIDENCE
INTENTS = ('requirements', 'answer', 'missing', 'recommend', 'cost', 'feasibility', 'approve', 'status', 'modify')
_RX = {
    'status': r'(מה המצב|איפה (זה )?עומד|מה קורה עם הבנייה|סטטוס|how is it going|\bstatus\b|progress|is it done)',
    'cost': r'(כמה (זה )?(יעלה|עולה)|מה המחיר|עלות|קרדיטים|how much|what will it cost|price|cost)',
    'missing': r'(מה חסר|מה עוד צריך|מה אתה צריך ממני|what\'?s missing|what is missing|what do you need)',
    'recommend': r'(מה אתה ממליץ|מה מומלץ|תמליץ|what do you recommend|any recommendation|what would you suggest)',
    'feasibility': r'(אפשר להוסיף|האם אפשר|אפשר גם|תוכלו להוסיף|can (we|you) add|is it possible|could it also|later\?)',
    'approve': r'(תתחיל(ו)? לבנות|תבנה את זה|אפשר להתחיל|מאשר(ת)? (את )?(הבנייה|התוכנית)|go ahead|start (the )?build|build it now|let\'?s build)',
}
_MODIFY_RX = r'(תשנה|תשנו|שנה את|תוסיף|תוסיפו|להוסיף|תוריד|תמחק|הזז|change|add|remove|make the|move the|rename|fix)'
_FEAS_KEYS = (('payments', r'(תשלו[םמ]|סליקה|payment|stripe|checkout)'), ('sign-in', r'(התחברות|לוגין|login|sign ?in)'),
              ('email', r'(מייל|email)'), ('sms', r'(sms|וואטסאפ|whatsapp)'), ('mobile app', r'(אפליקציה|app store|android|ios)'),
              ('publishing', r'(לפרסם|דומיין|כתובת קבועה|publish|domain)'), ('images', r'(תמונות|image|לוגו)'))


_CAP_HE = {'payments': 'תשלומים', 'sign-in': 'התחברות משתמשים', 'email': 'שליחת מיילים', 'sms': 'הודעות SMS/וואטסאפ',
           'mobile app': 'אפליקציה לנייד', 'publishing': 'פרסום לכתובת קבועה', 'images': 'יצירת תמונות'}
_REASON_HE = {F.BLOCKED: 'עוד לא מחובר בפלטפורמה', F.UNSUPPORTED: 'עוד לא נתמך', F.WITH_CONSTRAINTS: 'אפשרי עם מגבלות'}
_INTEGRATION_HE = {'payments': 'תשלומים וסליקה', 'email': 'שליחת מיילים', 'sms': 'שליחת הודעות SMS/WhatsApp',
                   'maps': 'מפות', 'calendar': 'יומן', 'ai_model': 'מודל בינה מלאכותית'}
_ALT_HE = {'payments': 'לבנות עכשיו בלי תשלומים ולהוסיף אותם כשהחיבור יהיה זמין', 'sign-in': 'כלי פנימי בלי התחברות, בקישור פרטי',
           'email': 'לבנות עכשיו בלי שליחת מיילים', 'sms': 'לבנות עכשיו בלי הודעות', 'mobile app': 'גרסת ווב שעובדת גם בנייד',
           'publishing': 'תצוגה מקדימה פרטית והורדת קוד המקור', 'images': 'להעלות תמונות משלכם'}


# A bare "start" once a brief exists ("תתחיל", "בוא נתחיל", "go") asks for the approval screen. The first message
# of a project ("תבנה לי ...") stays a requirements message because it only matches with a brief and as a full match.
_START_BARE = (r'(?:יאללה\s+)?(?:בוא(?:ו)?\s+)?(?:נתחיל|תתחיל(?:ו)?|תתחילי|תבנה|תבנו|תבני|להתחיל|התחל)'
               r'(?:\s+לבנות)?(?:\s+(?:עכשיו|כבר|בבקשה))*|(?:ok\s+)?(?:go|start|let\'?s start)(?:\s+(?:now|please))*')


QUESTION_MAX_CHARS = 200


def _is_short_question(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return len(lines) <= 2 and len(text) <= QUESTION_MAX_CHARS


def classify_intent(message: str, *, has_version: bool, has_brief: bool) -> str:
    t = (message or '').strip().lower()
    if has_brief and re.fullmatch(_START_BARE, t.strip(' .!?,'), re.I):
        return 'approve'
    # Production 2026-11-19 (the owner's law-firm brief, project prj_4tizfrqJkgO-Eg): a 14-line request whose FAQ line
    # said "כמה עולה ייעוץ ראשון (250 ₪)" was taken for a cost question; the model was never asked and the customer
    # read "no new details". A question intent is a short question, not a phrase inside a request: a message of
    # several lines or longer than QUESTION_MAX_CHARS is a request (a modification once a version exists).
    if not _is_short_question(t):
        return 'modify' if has_version and re.search(_MODIFY_RX, t, re.I) else 'requirements'
    for intent in ('status', 'approve', 'cost', 'missing', 'recommend', 'feasibility'):
        if re.search(_RX[intent], t, re.I):
            return intent
    if has_version and re.search(_MODIFY_RX, t, re.I):
        return 'modify'
    return 'requirements'


# Content the customer adds after the brief is complete (prices, copy, links, logo text). It is recorded, verbatim,
# in the brief's "content" field as a new revision; the new fingerprint invalidates any earlier approval.
_CONTENT_RX = re.compile(r'(₪|\bnis\b|\bils\b|\$|\d{2,}\s*(ש"ח|שקל|₪)|מחיר|מחירון|מחירים|טקסט|תוכן|קישור|לינק|וואטסאפ|ווטסאפ|whatsapp|wa\.me|'
               r'לוגו|logo|price|prices|copy|link)', re.I)


def _record_content(brief, message: str):
    text = ' '.join((message or '').split())[:1500]
    cur = brief.fields.get('content')
    if cur and cur.get('source') in ('answer', 'message') and text not in str(cur.get('value')):
        text = (str(cur['value']) + ' | ' + text)[:2000]
    return d.answer(brief, {'content': text})


_PICTURE_NOTES = {
    'he': {'items': 'תמונה לכל פריט: {v}.', 'subject': 'מה רואים בתמונה: {v}.',
           'items_default': 'לא קיבלנו רשימת פריטים, ולכן לא תיווצר תמונה לכל פריט. הפריטים יוצגו כטקסט.',
           'subject_default': 'לא קיבלנו תיאור לתמונה, ולכן היא לא תיווצר.',
           'items_again': 'לא הצלחתי לקרוא מההודעה רשימת פריטים. אם גם הפעם לא תהיה רשימה, נבנה בלי תמונה לכל פריט '
                          'והפריטים יוצגו כטקסט.',
           'subject_again': 'לא הצלחתי לקרוא מההודעה מה רואים בתמונה. אם גם הפעם לא יהיה תיאור, נבנה בלי התמונה הזאת.',
           'own': 'התמונות שהעליתם ({n}) יוצגו ליד הפריטים הראשונים: {covered}.', 'own_none': 'התמונות שהעליתם ({n}) יוצגו ליד הפריטים.',
           'gen': 'תמונה תיווצר עבור: {generated}.', 'gen_none': 'לא תיווצר תמונה לפריטים.'},
    'ar': {'items': 'صورة لكل عنصر: {v}.', 'subject': 'ما يظهر في الصورة: {v}.',
           'items_default': 'لم نتلقَّ قائمة العناصر، لذلك لن تُنشأ صورة لكل عنصر. ستُعرض العناصر كنص.',
           'subject_default': 'لم نتلقَّ وصفًا للصورة، لذلك لن تُنشأ.',
           'items_again': 'لم أتمكن من قراءة قائمة عناصر من الرسالة. إذا لم تصل قائمة هذه المرة أيضًا، سنبني دون صورة لكل '
                          'عنصر وستُعرض العناصر كنص.',
           'subject_again': 'لم أتمكن من قراءة ما يظهر في الصورة من الرسالة. إذا لم يصل وصف هذه المرة أيضًا، سنبني دون '
                            'هذه الصورة.',
           'own': 'صوركم ({n}) ستُعرض بجانب العناصر الأولى: {covered}.', 'own_none': 'صوركم ({n}) ستُعرض بجانب العناصر.',
           'gen': 'ستُنشأ صورة لـ: {generated}.', 'gen_none': 'لن تُنشأ صورة للعناصر.'},
    'en': {'items': 'A picture of each item: {v}.', 'subject': 'The picture shows: {v}.',
           'items_default': 'No list of items was given, so no picture is made per item. The items are shown as text.',
           'subject_default': 'No description of the picture was given, so it is left out.',
           'items_again': 'I could not read a list of items in that message. If there is no list this time either, the '
                          'site is built without a picture per item, and the items are shown as text.',
           'subject_again': 'I could not read what the picture shows in that message. If there is no description this '
                            'time either, it is built without that picture.',
           'own': 'Your {n} photo(s) go next to the first items: {covered}.', 'own_none': 'Your {n} photo(s) go next to the items.',
           'gen': 'A picture is made for: {generated}.', 'gen_none': 'No picture is made for the items.'},
}


_ASK_ONE_AR = 'سؤال واحد قبل أن نتابع:'


def _picture_notes(brief, lang: str) -> list[str]:
    """S1: what the customer answered to a picture question, or the stated default after two questions -- said in the
    summary they approve (never a silent fallback)."""
    words = _PICTURE_NOTES[lang if lang in _PICTURE_NOTES else 'en']
    out = []
    for qid, key in (('image_items', 'items'), ('image_subject', 'subject')):
        entry = (brief.assets.get('pictures') or {}).get(qid) or {}
        if entry.get('answer'):
            out.append(words[key].format(v=entry['answer']))
        elif entry.get('default'):
            out.append(words[key + '_default'])
    # review SF1: the customer's own photos among the items, and which items they stand for -- said, not assumed
    from ..capability_planner import _picture_per_item, item_pictures
    full = (brief.prompt or '') + '\n' + d.requirements_text(brief)
    split = item_pictures(full)
    if split['own'] and _picture_per_item(full):
        out.append(words['own'].format(n=split['own'], covered=', '.join(split['covered'])) if split['covered']
                   else words['own_none'].format(n=split['own']))
        out.append(words['gen'].format(generated=', '.join(split['generated'])) if split['generated']
                   else words['gen_none'])
    return out


@dataclass
class Turn:
    intent: str
    language: str
    reply: str
    brief_row: object | None = None
    questions: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    plan: dict | None = None
    plan_id: str | None = None
    contract: dict | None = None
    interpretation: dict | None = None
    cost_usd: Decimal | None = Decimal('0')       # None = UNKNOWN / PENDING (see cost_state)
    cost_state: str = 'CONFIRMED_ZERO'
    reservation_id: str | None = None
    explained: bool = False                        # this answer explained why the open question matters
    gaps: dict | None = None                       # WP1: what the artifact still needs, and the one next question
    gate: str | None = None                        # 'spec': this turn asked for gate 1 (approve the spec)
    venice: dict | None = None                     # agent.venice: mode, the visible stage, the cost range
    blocked: list = field(default_factory=list)    # feasibility blockers said in this turn (no plan before gate 1)
    unsupported: str | None = None                 # A0 (warehouse 69): the family refused in this turn (no output profile)

    def to_dict(self, lang: str) -> dict:
        return {'intent': self.intent, 'language': self.language, 'reply': self.reply,
                'questions': [{**q.to_dict(lang), 'suggested': (self.brief_row.brief.hints.get(q.field) if self.brief_row else None)}
                              for q in self.questions],
                'actions': self.actions, 'plan_id': self.plan_id,
                'plan': _plan_view(self.plan) if self.plan else None, 'contract': self.contract,
                'interpretation': self.interpretation, 'gaps': self.gaps, 'venice': self.venice,
                'unsupported': self.unsupported}


def _plan_view(plan: dict) -> dict:
    """What the workspace shows: no provider/model internals by default."""
    return {k: plan[k] for k in ('status', 'product_family', 'complexity', 'architecture', 'feasibility', 'layers',
                                 'critical_path', 'executable', 'budget', 'milestones', 'capability_gaps', 'graph_problems',
                                 'brief_fingerprint', 'spec_gate') if k in plan} | {
        'tasks': [{'task_id': t['task_id'], 'task_type': t['task_type'], 'department': t['department'],
                   'agent': t['responsible_agent'], 'dependencies': t['dependencies'], 'stage': t['stage'],
                   'conditional': t['conditional'], 'executable': t['executable']} for t in plan['execution_graph']['tasks']]}


_TXT = {
    'he': {'got': 'הבנתי', 'assumed': 'בחרתי עבורכם (אפשר לשנות בכל רגע)', 'ask': 'כדי להמשיך אני צריך תשובה אחת קטנה',
           'content_saved': 'שמרתי את התוכן שכתבתם בסיכום הפרויקט, בדיוק כפי שנכתב. האישור הקודם בוטל — צריך לאשר את הגרסה המעודכנת.',
           'ready_again': 'התוכנית מעודכנת ומוכנה. כדי להתחיל לבנות לחצו על "' + AF.APPROVE_BUTTON['he'] + '" — שום חיוב לא מתחיל לפני האישור.',
           'ready': 'יש לי תמונה מלאה. הכנתי תוכנית עבודה — אפשר לעבור עליה ולאשר. שום בנייה ושום חיוב לא מתחילים לפני אישור.',
           'blocked': 'יש דרישה שאי אפשר לבנות כרגע', 'nothing': 'לא זיהיתי פרטים חדשים. ספרו לי עוד על מה שתרצו, או שאלו "מה חסר?".',
           # owner 2026-11-18: an overrun stops the conversation and does not crash it -- said as it is, with the way on
           'limit_budget': 'הגענו לתקרת העלות של השיחה עם הסוכן, ולכן הוא לא ממשיך בשיחה החופשית. מה שכתבתם נשמר.',
           'limit_turns': 'הגענו למספר התורות המרבי של השיחה עם הסוכן, ולכן הוא לא ממשיך בשיחה החופשית. מה שכתבתם נשמר.',
           'limit_daily': 'הסוכן הגיע לתקרת השימוש היומית ויחזור לענות בהמשך. מה שכתבתם נשמר.',
           'limit_busy': 'הסוכן עדיין עונה על ההודעה הקודמת. מה שכתבתם נשמר — שלחו שוב בעוד רגע.',
           'limit_busy_alt': 'התשובה הקודמת עוד בדרך. ההודעה שלכם נשמרה — נסו שוב בעוד רגע.',
           'limit_daily_alt': 'הסוכן עדיין בהפסקה היומית ויחזור לענות בהמשך. גם ההודעה הזאת נשמרה.',
           'limit_ready': 'הנה הסיכום — אפשר לאשר אותו או לתקן:',
           'limit_incomplete': 'עוד חסר: {missing}.',
           'limit_incomplete_any': 'כדי להתקדם, השלימו את הפרטים החסרים: לחצו על "' + AF.EDIT_BUTTON['he'] + '".',
           'limit_ask': 'ענו כאן במילים שלכם, בלי עלות:',
           'limit_still': 'השיחה עם הסוכן הסתיימה. מה שכתבתם נשמר.',
           'limit_still_alt': 'הסוכן כבר לא עונה בשיחה הזאת, אבל ההודעה נשמרה.',
           'model_unavailable': 'הסוכן לא הספיק לענות הפעם (העומס אצל ספק המודל). מה שכתבתם נשמר — שלחו שוב בעוד רגע, או כתבו עוד פרט על המוצר.',
           'model_refused': 'הסוכן לא זמין כרגע: ספק המודל סירב לבקשה בגלל החשבון שלנו אצלו, לא בגללכם. מה שכתבתם נשמר, ולא חויב דבר. אפשר להמשיך לפרט כאן, והסוכן יענה כשהחשבון יחודש.',
           'missing_none': 'לא חסר כלום — אפשר לעבור לסיכום ולאשר.', 'missing': 'חסר לי:', 'contra': 'יש סתירה שצריך להחליט עליה:',
           'conflict': 'רק לוודא לפני שאני משנה — {field}: {current}, או {proposed}?',
           'confirm_sensitive': 'זה נושא רגיש ({field}), אז אני צריך אישור מפורש שלכם בכפתור.',
           'confirm_sensitive_words': 'זה נושא רגיש ({field}), אז אני צריך תשובה מפורשת שלכם, במילים.',
           'corrected': 'עדכנתי',
           'cost': 'הבנייה תוריד {credits} מהיתרה שלכם. שום חיוב לא מתחיל לפני שתאשרו.',
           'canon_ack': 'לפני האישור: כתבו בהודעה את הפרטים החסרים שלמטה, או סמנו את התיבה שמאשרת בנייה בלעדיהם.',
           'cost_unknown': 'את המחיר המדויק אחשב אחרי שתאשרו שהבנתי נכון.', 'approve': 'כדי להתחיל, לחצו על "' + AF.APPROVE_BUTTON['he'] + '".',
           'approve_not_ready': 'עדיין אי אפשר לאשר:', 'status_none': 'עדיין לא התחילה בנייה בפרויקט הזה.',
           'status': 'הבנייה האחרונה: {status}{phase}. משימות: {done} הושלמו, {running} בתהליך, {pending} ממתינות, {failed} נכשלו.',
           'modify': 'הבנתי שתרצו לשנות את המוצר הקיים. אשרו ואשלח את השינוי לצנרת השינויים (תוצג עלות לפני ביצוע).',
           'feas_yes': '{cap}: אפשר כבר עכשיו.', 'feas_no': '{cap}: לא זמין כרגע — {reason}.{alt}',
           'recommend': 'ההמלצות שלי (כבר בתוך הסיכום, ואפשר לשנות כל אחת):', 'alt': ' חלופה: {x}.',
           'more': ' עוד {n} החלטות כאלה במסך "דרישות".',
           'ask_one': 'שאלה אחת לפני שממשיכים:', 'decide': 'יש החלטה אחת לפני שממשיכים:',
           'verify': 'רק לוודא — הבנתי מהבקשה: {label}. נכון?',
           'safe_default': 'לא קיבלתי תשובה על {topic}, אז הפעלתי ברירת מחדל בטוחה: {label}. אפשר לשנות בכל רגע במסך "דרישות".',
           'card_blocked': 'חסרה החלטה על {topic}, ובלעדיה לא ממשיכים. אפשר לבחור במסך "דרישות".',
           'image_still': 'עדיין חסרה לי תשובה על {topic} כדי להמשיך. אפשר ללחוץ על אחד הכפתורים, או לכתוב במילים: {opts}.',
           'still_in_words': 'עדיין חסרה לי תשובה על {topic} כדי להמשיך. אפשר לכתוב אחת מאלה, במילים שלכם: {opts}.',
           'image_still_text': 'עדיין חסר לי משפט קצר על התמונה כדי להמשיך — למשל "הדלת של החנות" או "סבא שמעון, הבעלים".',
           'rephrase_q': 'עוד לא קיבלתי תשובה לשאלה הזאת. אפשר ללחוץ על אחת האפשרויות למטה, או לכתוב אותה במילים.',
           'rephrase': 'לא זיהיתי שינוי מההודעה הקודמת. כתבו מה תרצו לשנות או להוסיף, או שאלו "מה חסר?".',
           'safe_suffix': ' (ברירת מחדל בטוחה)',
           'why': 'למה אני שואל: {why}', 'unsure': 'אם לא בטוחים, אפשר ללחוץ "בחרו עבורי" ואבחר {rec}. תמיד אפשר לשנות אחר כך.',
           'unsure_norec': 'אם לא בטוחים, אפשר ללחוץ "בחרו עבורי". תמיד אפשר לשנות אחר כך.',
           'options': '{q} אפשרויות: {opts}.',
           'attached_shown': '📎 {n}',
           'attached_only': 'קיבלתי {n} ושמרתי בפרויקט. עדיין אין ניתוח תמונה אוטומטי (צריך מודל עם יכולת ראייה ואישור תקציב), אז כתבו במשפט מה חשוב בה או מה לשנות.',
           'attached_note': '(שמרתי {n}; היא מועברת כהקשר לשינוי, בלי ניתוח תמונה אוטומטי.)',
           'attached_bound': '(שמרתי {n} בבקשה של הפרויקט.)',
           'image_change': 'שינוי של התמונה עצמה עוד לא זמין אצלנו. אפשר להשתמש בה כמו שהיא, או רק כהשראה.',
           'image_change_defaulted': 'שינוי של התמונה עצמה (למשל קריקטורה) עוד לא זמין, אז כדי להתקדם בחרתי: {choice}. אפשר לשנות בכל רגע.',
           'image_hero_taken': 'כבר יש בדף תמונה ראשית אחת. בחרו לתמונה הזו מקום אחר.',
           'attached_kept': '(שמרתי {n} בפרויקט; מההודעה הזו היא לא נכנסת לבנייה.)',
           'images': lambda n: 'תמונה אחת' if n == 1 else f'{n} תמונות'},
    'en': {'safe_default': 'No answer on {topic}, so I applied a safe default: {label}. You can change it any time in the "Requirements" tab.',
           'card_blocked': 'A decision on {topic} is missing, and we cannot continue without it. You can choose in the "Requirements" tab.',
           'image_still': 'I still need an answer about {topic} to continue. Press one of the buttons, or write it in words: {opts}.',
           'still_in_words': 'I still need an answer about {topic} to continue. Write one of these, in your own words: {opts}.',
           'image_still_text': 'I still need a short sentence about the image to continue, for example "the shop door" or "Shimon, the owner".',
           'rephrase_q': 'I have not had an answer to this question yet. Press one of the options below, or write it in words.',
           'rephrase': 'I did not see anything new since the last message. Tell me what to change or add, or ask "what is missing?".',
           'safe_suffix': ' (safe default)',
           'got': 'Got it', 'assumed': 'I chose for you (change anything any time)', 'ask': 'To continue I need one short answer',
           'content_saved': 'I saved the content you wrote in the project summary, exactly as written. Any earlier approval is cancelled; please approve the updated version.',
           'ready_again': 'The plan is up to date. To start, press "' + AF.APPROVE_BUTTON['en'] + '"; nothing is charged before you approve.',
           'ready': 'I have the full picture and prepared a work plan you can review and approve. Nothing is built or charged before you approve.',
           'blocked': 'Something you asked for cannot be built right now', 'nothing': 'I did not spot new details. Tell me more, or ask "what is missing?".',
           'limit_budget': 'This conversation reached its cost limit, so the assistant stops the open conversation here. What you wrote is saved.',
           'limit_turns': 'This conversation reached its maximum number of turns, so the assistant stops the open conversation here. What you wrote is saved.',
           'limit_daily': 'The assistant reached its daily usage limit and will answer again later. What you wrote is saved.',
           'limit_busy': 'The assistant is still answering your previous message. What you wrote is saved; send it again in a moment.',
           'limit_busy_alt': 'The previous answer is still on its way. Your message is saved; try again in a moment.',
           'limit_daily_alt': 'The assistant is still on its daily pause and will answer again later. This message is saved too.',
           'limit_ready': 'Here is the summary; you can approve it or correct it:',
           'limit_incomplete': 'Still missing: {missing}.',
           'limit_incomplete_any': 'To go on, fill in the missing details: press "' + AF.EDIT_BUTTON['en'] + '".',
           'limit_ask': 'Answer here in your own words, at no cost:',
           'limit_still': 'The conversation with the assistant has ended. What you wrote is saved.',
           'limit_still_alt': 'The assistant no longer answers in this conversation, but your message is saved.',
           'model_unavailable': 'The assistant could not answer in time (the model provider is busy). What you wrote is saved; send it again in a moment, or add another detail about the product.',
           'model_refused': 'The assistant is not available right now: the model provider refused the request because of our account with it, not because of you. What you wrote is saved and nothing was charged. You can keep adding details here; the assistant answers again once the account is renewed.',
           'missing_none': 'Nothing is missing: you can review the summary and approve.', 'missing': 'Still missing:',
           'contra': 'There is a contradiction to decide:',
           'conflict': 'Just to check before I change it — {field}: {current}, or {proposed}?',
           'confirm_sensitive': 'This is sensitive ({field}), so I need your explicit confirmation with the button.',
           'confirm_sensitive_words': 'This is sensitive ({field}), so I need your explicit answer, in words.',
           'corrected': 'Updated',
           'cost': 'This build takes {credits} from your balance. Nothing is charged before you approve.',
           'canon_ack': 'Before approving: send the missing details below in a message, or tick the box to build without them.',
           'cost_unknown': 'I will calculate the exact price once you confirm that I understood you.',
           'approve': 'To start, press "' + AF.APPROVE_BUTTON['en'] + '".',
           'approve_not_ready': 'It cannot be approved yet:', 'status_none': 'No build has started in this project yet.',
           'status': 'Latest build: {status}{phase}. Tasks: {done} done, {running} running, {pending} waiting, {failed} failed.',
           'modify': 'You want to change the existing product. Confirm and I will send it to the change pipeline (cost shown before it runs).',
           'feas_yes': '{cap}: available now.', 'feas_no': '{cap}: not available right now — {reason}.{alt}',
           'recommend': 'My recommendations (already in the summary; change any of them):', 'alt': ' Alternative: {x}.',
           'more': ' {n} more such decisions are in "Requirements".',
           'ask_one': 'One question before we continue:', 'decide': 'One decision before we continue:',
           'verify': 'Just to confirm — from your request I understood: {label}. Right?',
           'why': 'Why I ask: {why}', 'unsure': 'If you are not sure, tap "Choose for me" and I will use {rec}. You can change it later.',
           'unsure_norec': 'If you are not sure, tap "Choose for me". You can change it later.',
           'options': '{q} Options: {opts}.',
           'attached_shown': '📎 {n}',
           'attached_only': 'I saved {n} in the project. Automatic image analysis is not enabled yet (it needs a vision-capable model and an approved budget), so tell me in a sentence what matters in it or what to change.',
           'attached_note': '(I saved {n}; it goes with the change as context, without automatic image analysis.)',
           'attached_bound': '(I saved {n} in the project request.)',
           'image_change': 'Changing the image itself is not available yet. It can be used as is, or as inspiration only.',
           'image_change_defaulted': 'Changing the image itself (a caricature, for example) is not available yet, so to move on I chose: {choice}. You can change it any time.',
           'image_hero_taken': 'The page already has its one main image. Choose another place for this image.',
           'attached_kept': '(I saved {n} in the project; from this message it does not go into the build.)',
           'images': lambda n: 'one image' if n == 1 else f'{n} images'},
}


# Short names for decisions (directive 2026-10-11 "Conversation UX"): the
# reply names the decision in a word or two, not by repeating the question.
SHORT = {
    'he': {'audience': 'קהל', 'goal': 'מטרה', 'login': 'התחברות', 'personal_data': 'פרטים אישיים', 'access_scope': 'גישה',
           'screens': 'מסכים', 'languages': 'שפה', 'content': 'תוכן התחלתי', 'dates': 'תאריכים', 'duplicates': 'כפילויות',
           'style': 'סגנון', 'color': 'צבע', 'font': 'גופן', 'logo': 'לוגו', 'references': 'השראה',
           'content_only': 'אתר תוכן בלבד', 'unavailable': 'יכולת שאינה זמינה כרגע',
           'image_kind': 'מה בתמונה', 'image_identity': 'מי או מה בתמונה', 'image_use': 'מה לעשות עם התמונה',
           'image_place': 'איפה התמונה תופיע'},
    'en': {'audience': 'audience', 'goal': 'goal', 'login': 'sign-in', 'personal_data': 'personal data', 'access_scope': 'access',
           'screens': 'screens', 'languages': 'language', 'content': 'starting content', 'dates': 'dates',
           'duplicates': 'duplicates', 'style': 'style', 'color': 'colour', 'font': 'font', 'logo': 'logo',
           'references': 'references', 'content_only': 'content-only site', 'unavailable': 'an unavailable capability',
           'image_kind': 'what is in the image', 'image_identity': 'who or what is in the image',
           'image_use': 'what to do with the image', 'image_place': 'where the image goes'},
}
# "I don't know / what? / why?" -- explain why the open question matters and
# offer the recommendation, instead of repeating the same sentence.
def _why_prefixes():
    from ..intake.gaps import FALLBACK
    return tuple(t['_why'] for t in FALLBACK.values())


_WHY_PREFIXES = _why_prefixes()
AF_FLOW = 'two_gate'      # intake.approval_flow.FLOW (kept in sync by test_the_flow_mark_names_match)

_UNSURE_RX = (r'^\s*(מה\??|מה זה\??|למה\??|לא (יודע|יודעת|בטוח|בטוחה|הבנתי)|אין לי מושג|תסביר|תסבירי|הסבר|'
              r'\?+|what\??|why\??|i don\'?t know|not sure|no idea|what do you mean|explain|'
              r'لماذا\s*[?؟]?|ماذا\s*[?؟]?|لا أعرف|لست متأكد[ًا]*|اشرح)\s*[.!?؟]*\s*$')

# Clarification replies to the question just asked (owner + Matt 2026-10-28), kept apart on purpose:
#   NOT UNDERSTOOD ("what?", "why?", "לא הבנתי") -> the same field once more, explained; then the conversation moves on
#   DON'T KNOW ("לא יודע", "not sure")           -> not asked again: the field's default, visible as an assumption
_NOT_UNDERSTOOD_RX = (r'^\s*(מה\??|מה זה\??|למה\??|לא הבנתי(?: את השאלה)?|לא ברור(?: לי)?|תסביר|תסבירי|הסבר|\?+|'
                      r'what\??|why\??|what do you mean\??|i don\'?t understand|explain|'
                      r'لماذا\s*[?؟]?|ماذا\s*[?؟]?|لم أفهم|اشرح)\s*[.!?؟]*\s*$')
_DONT_KNOW_RX = (r'^\s*(לא (יודע|יודעת|בטוח|בטוחה)|אין לי מושג|i don\'?t know|not sure|no idea|'
                 r'لا أعرف|لست متأكد[ًا]*)\s*[.!?؟]*\s*$')


_REFUSALS = ('VeniceInsufficientCredit', 'VeniceAuthError', 'insufficient credit', 'credit balance is too low')


def _provider_refused(interp) -> str | None:
    """The refusal the model provider gave this turn (no credit, a refused key), from the interpretation's dropped
    notes -- or None when the model was merely slow or unavailable."""
    for note in getattr(interp, 'dropped', None) or ():
        if any(r in str(note) for r in _REFUSALS):
            return str(note)[:160]
    return None


def _short(field_: str, lang: str) -> str:
    q = d.BY_ID.get(field_)
    name = SHORT['he' if lang == 'he' else 'en'].get(field_)
    return name or ((q.he if lang == 'he' else q.en) if q else field_)


def _lines(items) -> str:
    """Decisions one per line (Michael 2026-11-13): a wrapped "key: value; key: value" line in an RTL bubble read as
    a swapped label and value, a duplicate key and a key without a value."""
    return '\n' + '\n'.join(f'• {x}' for x in items) + '\n'


_SENTENCE = re.compile(r'[^.!?\n]*(?:[.!?]+\)?|$)', re.S)


def _no_question(text: str) -> str:
    """The text without any sentence that asks something: used when the question itself is shown as a card, so
    the turn asks it once (Michael 2026-11-13: the model's sentence and the card asked the same thing)."""
    from ..intake.gaps import FALLBACK
    delegate = {t.get('_delegate') for t in FALLBACK.values()}
    out, after_question = [], False
    for m in _SENTENCE.finditer(text or ''):
        x = m.group(0).strip()
        if not x:
            continue
        if '?' in x or '؟' in x:
            after_question = True                   # the question goes ...
        elif after_question and x.startswith('('):
            continue                                # ... with its "(I understood: X.)" -- a guess, not a fact
        elif x in delegate:
            continue                                # "you can also say 'you decide'": the card has that button
        else:
            after_question = False
            out.append(x)
    return ' '.join(out).strip()


def _label(field_: str, value, lang: str) -> str:
    q = d.BY_ID.get(field_)
    return f'{_short(field_, lang)}: {d._label(q, value, lang) if q else value}'


def _bindable_images(attachments) -> list[dict]:
    """Owner-checked image attachments (id + digest), one per distinct image (the same bytes twice count once)."""
    out, seen = [], set()
    for a in attachments or ():
        if (a.get('kind', 'image') == 'image' and re.fullmatch(r'att_[a-f0-9]{32}', a.get('id', ''))
                and re.fullmatch(r'[a-f0-9]{64}', a.get('sha256', '')) and a['sha256'] not in seen):
            seen.add(a['sha256'])
            out.append(a)
    return out


# The fields the summary card shows, in this order (the owner, 2026-11-23). The rest is in the brief and the build.
SUMMARY_FIELDS = ('goal', 'screens', 'content', 'color', 'style', 'logo')
# a site that keeps nothing from its visitors says so in plain words, once
_PRIVACY_ROW = {'he': ('מידע מהמבקרים', 'האתר לא שומר שום מידע מהמבקרים', False),
                'en': ('Visitor data', 'The site keeps nothing from its visitors', False),
                'ar': ('بيانات الزوار', 'الموقع لا يحفظ أي معلومات من الزوار', False)}


class ConversationSupervisor:
    def __init__(self, *, briefs, store, gateway=None, architect: ChiefArchitect | None = None, credits: int | None = None,
                 budget_usd: Decimal = Decimal('0.50'), context=None, worker_interpreter=None,
                 reservations=None, enqueue=None, admission=None, credits_from_plan: bool = False):
        self.briefs = briefs            # brief repository (latest/save) -- the source of truth
        self.store = store              # conversation store (messages, plans)
        self.gateway = gateway
        self.architect = architect or ChiefArchitect()
        self.credits = credits
        # True only when `credits` was read from THIS account's plan. A default is not a price: it is never said as one.
        self.plan_credits = credits if credits_from_plan and credits is not None else None
        self.budget_usd = budget_usd
        self.context = context or (lambda project_id: {})   # durable build/version state (read-only)
        self.worker_interpreter = worker_interpreter           # injected in tests
        self.reservations = reservations                       # intake.budget.ReservationService (migration 037)
        self.enqueue = enqueue                                 # RQ enqueue of a reservation id
        # 79: the build-admission check the banner shows (plan preview: quote, plan allowance, infrastructure, gate).
        # The chat never says "ready, approve" while this says no; if they would disagree, admission wins.
        self.admission = admission                             # (project_id, row, lang) -> preview dict | None

    # ------------------------------------------------------------------ helpers
    def _unpriced_gate(self, project_id: str, account_id: str, row, lang: str, turn) -> list[str] | None:
        """77 (Michael 2026-11-11): before gate 1, a capability with no price is never left to the generic banner.
        Exactly three outcomes: it is priced (None: gate 1 as usual); the customer is asked ONE question -- build
        without it? -- and "build without" binds an explicit exclusion into the spec; or, for what cannot be left out
        (infrastructure), the reply says plainly what is missing and what to do, with no approve button."""
        if self.admission is None:
            return None
        from .. import build_readiness as R
        he = lang == 'he'
        f = row.brief.fields.get('unavailable') or {}
        known = d.unpriced_keys(row.brief)
        if f.get('value') == 'wait' and known:
            names = ', '.join(dict.fromkeys(R.display_name(k, lang) for k in known))
            turn.questions = [d.BY_ID['unavailable']]
            return [(f'בסדר. {names} עדיין לא זמין אצלנו, ולכן אי אפשר להתחיל לבנות את הבקשה כפי שהיא. '
                     'כשתרצו — בחרו "כן, לבנות בלעדיו", או ערכו את הבקשה.') if he else
                    (f'OK. {names} is not available yet, so this request cannot be built as it is. '
                     'Whenever you like, choose "Yes, build without it", or edit the request.')]
        try:
            preview = self.admission(project_id, row, lang) or {}
        except Exception:   # a bug here never silences the conversation; the gate-2 check still stands
            import logging
            logging.getLogger(__name__).warning('unpriced check failed for %s', project_id, exc_info=True)
            return None
        keys = list(dict.fromkeys(k for b in preview.get('blockers') or [] if b.get('code') == 'cost_quote_unknown'
                                  for k in b.get('capability_keys') or []))
        if not keys:
            return None
        ask = [k for k in keys if R.excludable(k)]
        if ask:
            new = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
            new.hints['unpriced'] = ','.join(sorted(set(known) | set(ask)))
            new.fields.pop('unavailable', None)          # a new unpriced item is asked again
            saved = self.briefs.save(project_id=project_id, account_id=account_id, brief=new,
                                     expected_revision=row.revision)
            turn.brief_row = saved
            turn.questions = [d.BY_ID['unavailable']]
            names = ', '.join(dict.fromkeys(R.display_name(k, lang) for k in ask))
            return [(f'{names} עדיין לא זמין אצלנו. לבנות בלעדיו? אם כן, זה ייכתב בסיכום שתאשרו, והשאר ייבנה כרגיל.') if he else
                    (f'{names} is not available yet. Build without it? If so, the summary you confirm says so and the rest is built as usual.')]
        names = ', '.join(dict.fromkeys(R.display_name(k, lang) for k in keys))
        login = 'auth_session' in keys
        nxt = (('אפשר לבנות בלי התחברות — כתבו "בלי התחברות".' if login else 'ערכו את הבקשה בלעדיו.') if he else
               ('It can be built without sign-in: write "no sign-in".' if login else 'Edit the request without it.'))
        return [(f'{names} עדיין לא זמין אצלנו, ולכן אי אפשר לבנות את הבקשה כפי שהיא. {nxt}') if he else
                (f'{names} is not available yet, so this request cannot be built as it is. {nxt}')]

    def _admission_block(self, project_id: str, row, lang: str) -> str | None:
        """79: the sentence the banner shows, when admission refuses -- or None (no admission check, or it allows).
        A failure of the check itself never blocks the chat; it is logged and the old reply stands."""
        if self.admission is None:
            return None
        try:
            preview = self.admission(project_id, row, lang)
        except Exception:   # an admission bug must not silence the conversation
            import logging
            logging.getLogger(__name__).warning('admission check failed for %s', project_id, exc_info=True)
            return None
        if not preview or preview.get('can_build'):
            return None
        from ..build_readiness import primary_blocker
        reason = preview.get('blocked_reason') or primary_blocker(preview, lang)
        head = 'לא ניתן להתחיל בבנייה כרגע' if lang == 'he' else 'The build cannot start yet'
        return f"{head}: {reason['message']} {reason['next']}"

    def intake_mode(self, project_id, account_id=None):
        from ..intake import budget as B
        from ..intake import mode as intake_mode

        def spend():
            if self.reservations is not None and account_id:
                # D10 review: counted() includes quotes still held by calls in flight. A hold is not spend yet --
                # the call may settle far lower -- so the pre-check leaves it to reserve(), which tells 'busy' from
                # 'budget' under the scope locks; otherwise a held quote closed the conversation for good.
                pscope = f'project:{account_id}:{project_id}'
                held = getattr(self.reservations, 'open_held', None)
                project = self.reservations.counted(pscope) - (held(pscope) if held else 0)
                return project, self.reservations.counted(B.DAILY_SCOPE)
            return self.store.conversation_cost(project_id), self.store.daily_cost()
        worker_route_available = self.worker_interpreter is not None or (
            self.reservations is not None and self.enqueue is not None)
        return intake_mode.resolve_with_spend(spend, has_direct_gateway=self.gateway is not None,
                                              worker_route_available=worker_route_available)

    def _interpreter(self, project_id, account_id=None, request_key=None, task='conversation'):
        """Every paid call goes through a durable reservation (Issue #12); without
        the reservation service, authorization or budget the answer is deterministic."""
        from ..intake import budget as B
        from ..intake import mode as intake_mode
        m = self.intake_mode(project_id, account_id)
        if m.mode != intake_mode.MODEL_WORKER:
            # a reached limit is said as such (owner 2026-11-18), never the "provider is busy" text
            return _AtLimit(m.limit, m.reason) if m.limit else DeterministicInterpreter()
        if self.worker_interpreter is not None:
            if hasattr(self.worker_interpreter, 'task'):
                self.worker_interpreter.task = task
            return self.worker_interpreter
        if self.reservations is None or self.enqueue is None or not account_id:
            return DeterministicInterpreter()
        from ..intake.worker_route import ReservedWorkerInterpreter
        from ..intake import conversation_agent as agent
        caps, profile = B.caps_from_env(), None
        if agent.enabled():                     # the agent's cost cap; no turn cap (owner 2026-11-23: the chat never ends)
            import dataclasses
            from ..providers import venice_gateway as VG
            caps = dataclasses.replace(caps, project_turns=agent.MAX_TURNS,
                                       project_usd=min(caps.project_usd, agent.MAX_COST_USD))
            # Sonnet for the conversation agent only, on Venice (owner 2026-11-18): every other account keeps the
            # global list and ceiling, quoted exactly as before
            profile = agent.venice_profile() if VG.selected() else None
        return ReservedWorkerInterpreter(self.reservations, self.enqueue, account_id=account_id,
                                         project_id=project_id, request_key=request_key, caps=caps, task=task,
                                         venice_profile=profile)

    def _feasibility(self, row) -> dict:
        """What can be built from the spec, WITHOUT a plan (gate 1 has not been passed yet)."""
        try:
            return F.assess(C.build(row.brief)).to_dict()
        except C.ContractInvalid:
            return {}

    def _messages(self, project_id):
        try:
            return self.store.messages_for(project_id, limit=500)
        except Exception:
            return []

    def _spec_ok(self, project_id, row) -> bool:
        from ..intake import approval_flow as AF
        # Michael 2026-11-13: an older approval does not stand when the stored messages hold facts the spec lacks, or
        # a needed fact is neither given nor waived (approval_flow.spec_invalid_reason)
        return row is not None and AF.spec_invalid_reason(row.brief, self._messages(project_id), row.fingerprint) is None

    def _collected(self, project_id, account_id, row):
        """The brief with every fact the customer's STORED messages state (Michael 2026-11-13, the cafe: the phone
        and hours were given on 2026-11-12 and lost). Idempotent -- once the brief holds them nothing is written.
        A changed brief is a new revision with a new fingerprint: an older approval no longer matches it."""
        if row is None:
            return row
        row = self._collected_skeleton(project_id, account_id, row)
        brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
        if not d.note_customer_texts(brief, d.customer_messages(self._messages(project_id))):
            return row
        return self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                expected_revision=row.revision, request_key=None)

    def _collected_skeleton(self, project_id, account_id, row):
        """Warehouse 128: the skeleton the customer approved from a competitor screenshot is the brief's, by the same
        rule as their facts (idempotent; a changed brief is a new revision, so an older approval no longer matches)."""
        brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
        if not MR.collect_skeleton(brief, self._messages(project_id)):
            return row
        return self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                expected_revision=row.revision, request_key=None)

    def _approved_plan(self, project_id, row):
        """After gate 1 only: the verified plan saved for this exact spec (None before)."""
        if not self._spec_ok(project_id, row):
            return None, None, None
        saved = self.store.plan_for(project_id, row.fingerprint)
        if saved is None:
            return None, None, None
        try:
            contract = C.build(row.brief).to_dict()
        except C.ContractInvalid:
            contract = None
        return saved['plan'], saved['id'], contract

    # Michael 2026-11-14 (b5): the build contract's open questions that the conversation can ask with a card. The
    # architect's persistence backstop is the discovery question content_only (the same two choices).
    _CONTRACT_CARD = {'persistence': 'content_only', 'persistence_stale': 'content_only'}

    def _contract_open(self, row) -> list:
        """The questions the build contract compiled from THIS brief still has -- the same compile the admission (gate
        2) runs (investor_app._brief_prompt -> ProductArchitect). Butcher, 2026-11-13: discovery had nothing pending,
        gate 1 was shown and approved three times, and gate 2 refused each time with "האם האתר שומר מידע? ענו על
        השאלה בשיחה" and no card. A compile failure is logged at ERROR and gate 2 still refuses on its own."""
        from ..product_architect import ProductArchitect
        prompt = (row.brief.prompt + '\n' + d.requirements_text(row.brief))[:12000]
        try:
            contract = ProductArchitect().compile(prompt, project_id='gate1-check', contract_version=1)
        except Exception:
            import logging
            logging.getLogger(__name__).error('GATE1_CONTRACT_CHECK_FAILED revision=%s', row.revision, exc_info=True)
            return []
        return list(contract.unresolved_questions)

    def _open_question_instead_of_gate1(self, turn, row, lang, project_id=None):
        """When the contract still has an open question, gate 1 is not shown: the question is, with its card when the
        conversation has one, else in words. Returns the reply lines, or None when nothing is open."""
        open_qs = self._contract_open(row)
        if not open_qs:
            return None
        T = _TXT['he' if lang == 'he' else 'en']
        field = self._CONTRACT_CARD.get(open_qs[0].id)
        turn.gate = None
        turn.actions = [a for a in turn.actions if a.get('type') != 'approve_spec']
        turn.interpretation = {**(turn.interpretation or {}), 'gate1_held': [q.id for q in open_qs]}
        card = d.BY_ID.get(field)
        if card is not None and card.ask_if(d._ctx(row.brief)):
            # a card only when its answer can stick: an inapplicable field is dropped again on save, and the same card
            # would come back every turn (an unbounded loop)
            turn.questions = [card]
            return [T['ask_one']]
        turn.questions = []
        turn.actions.append({'type': 'edit_requirements', 'brief_revision': row.revision})
        # S1 (release review of 550320c): the question asked in words is recorded, so the customer's next message is
        # read as its answer (_picture_answer) and the times it was asked are counted (_times_contract_asked)
        turn.interpretation['contract_asked'] = open_qs[0].id
        again = []
        if project_id is not None and open_qs[0].id in d.PICTURE_QUESTIONS and \
                self._times_contract_asked(project_id, open_qs[0].id):
            # asked before and not answered in words the planner reads: said, with what happens after this question
            words = _PICTURE_NOTES[lang if lang in _PICTURE_NOTES else 'en']
            again = [words[{'image_items': 'items', 'image_subject': 'subject'}[open_qs[0].id] + '_again']]
        # nit (review of 49d61d3): an Arabic question gets an Arabic intro (the conversation's lang is he / en)
        intro = _ASK_ONE_AR if re.search(r'[؀-ۿ]', open_qs[0].question) else T['ask_one']
        return again + [intro, open_qs[0].question]

    def _gate1(self, turn, row, lang, project_id=None):
        """Step 1 of 2: the spec + the cost range, and the approve-spec control. No plan exists here."""
        held = self._open_question_instead_of_gate1(turn, row, lang, project_id)
        if held is not None:
            return held
        from ..intake import approval_flow as AF
        t, (lo, hi) = AF.text(lang), AF.cost_range(row.brief, self.plan_credits)
        # The owner, 2026-11-23 ("סוכן ... להפוך את המלל לתוצאה מעולה"): the summary leads with what the customer cares
        # about -- what the site is for, its parts, its content (the packages, the prices, "about us"), its look -- and
        # not with "font: Heebo", "dates: none" or "login: none", which stay in the brief and in the build.
        items = [(k, row.brief.fields[k]) for k in SUMMARY_FIELDS if k in row.brief.fields]
        if row.brief.values().get('content_only') == 'yes':
            items.append(('content_only', row.brief.fields['content_only']))
        turn.gate = 'spec'
        turn.venice = {'agent': 'agent.venice', 'mode': 'understanding', 'stage': t['stage1'],
                       'cost_range_credits': [lo, hi]}
        # Michael 2026-11-10 condition 2: the fact canon is shown here and approved WITH the brief; an empty canon on a
        # business site is a visible warning (CANON_INCOMPLETE), never a silent pass.
        from .. import discovery as d
        canon = d.gate_canon(row.brief, lang)                                            # #335 (c)
        offer = d.window_offer(row.brief, lang)     # owner 2026-11-16: each window with its benefit, approve or reject
        turn.actions.append({'type': 'approve_spec', 'brief_revision': row.revision, 'brief_fingerprint': row.fingerprint,
                             'canon': {k: canon[k] for k in ('status', 'hash', 'facts')},
                             **({'windows': offer} if offer else {})})       # no offer, no key (an app has no windows)
        from .. import build_readiness as R
        excluded = [(f'{R.display_name(k, lang)} עדיין לא זמין, ולכן ייבנה בלעדיו.' if lang == 'he' else
                     f'{R.display_name(k, lang)} is not available yet, so it is built without it.')
                    for k in d.customer_exclusions(row.brief)]      # 77: said in the spec the customer approves
        excluded += _picture_notes(row.brief, lang)     # S1: a picture answer or its stated default, said here
        # the owner's example (2026-11-23, "זה מה שנבנה"): the same parts as a card the screen shows in place of one
        # paragraph; the message below stays the record (spec_card.py)
        from .spec_card import card as spec_card
        card = spec_card(
            stage=t['stage1'], lang=lang, excluded=excluded, canon_lines=list(canon['lines']),
            price=AF.range_line(lang, lo, hi), next_step=t['gate1'],
            rows=[_PRIVACY_ROW[lang if lang in _PRIVACY_ROW else 'en'] if k == 'content_only' else
                  (_short(k, lang), d._label(d.BY_ID[k], v['value'], lang) if k in d.BY_ID else str(v['value']),
                   v.get('confidence') == SAFE_CONFIDENCE) for k, v in items if 'value' in v])
        turn.actions[-1]['card'] = card
        # the message says each detail once too: its summary is the card's rows, where a segment that repeats a
        # business detail word for word was already dropped (the detail stays in the canon line below)
        safe = _TXT['he' if lang == 'he' else 'en']['safe_suffix']
        summary = '; '.join(f"{r['label']}: {r['value']}" + (safe if r['default'] else '') for r in card['rows'])
        return [t['stage1'] + ' —', t['spec'].format(summary=summary or '—'), *excluded, *canon['lines'],
                AF.range_line(lang, lo, hi), t['gate1']]

    def _plan(self, project_id, row):
        try:
            contract = C.build(row.brief)
        except C.ContractInvalid:
            return None, None, None
        plan = self.architect.plan(contract, budget_usd=self.budget_usd,
                                   status='PROPOSED' if row.complete else 'DRAFT')
        saved = self.store.save_plan(project_id=project_id, brief_revision=row.revision,
                                     brief_fingerprint=row.fingerprint, plan=plan) if row.complete else None
        return plan, (saved or {}).get('id'), contract.to_dict()

    # --------------------------------------------------------------------- turn
    def turn(self, *, project_id: str, account_id: str, message: str = '', answers: dict | None = None,
             request_key: str | None = None, lang: str | None = None, attachments: list | None = None,
             reading: dict | None = None) -> Turn:
        # the conversation agent is decided per account (OMNI_INTAKE_AGENT=accounts): every check of this turn --
        # here, in the interpreter's context, in the card limit -- reads the account set for this turn
        from ..intake import conversation_agent as agent
        token = agent.for_account(account_id)
        try:
            return self._turn(project_id=project_id, account_id=account_id, message=message, answers=answers,
                              request_key=request_key, lang=lang, attachments=attachments, reading=reading)
        finally:
            agent.release(token)

    def _turn(self, *, project_id: str, account_id: str, message: str = '', answers: dict | None = None,
              request_key: str | None = None, lang: str | None = None, attachments: list | None = None,
              reading: dict | None = None) -> Turn:
        message = (message or '').strip()[:8000]
        lang = lang or language_of(message or 'שלום')
        T = _TXT['he' if lang == 'he' else 'en']
        ctx = self.context(project_id) or {}
        row = self._collected(project_id, account_id, self.briefs.latest(project_id))
        shown = message or '; '.join(_label(d.BY_ID[q].field if q in d.BY_ID else q,
                                            v if v != d.DELEGATE else ('בחרו עבורי' if lang == 'he' else 'choose for me'), lang)
                                     for q, v in (answers or {}).items())
        attachments = list(attachments or [])
        if attachments and not shown:
            shown = T['attached_shown'].format(n=T['images'](len(attachments)))
        if shown:
            # A quick-reply button is stored with its answers (not only its label), so the conversation can be
            # replayed exactly from the store on any server (_replayed_spec); no schema change (jsonb column).
            said_meta = {**({'attachments': [{'id': a['id'], 'kind': a['kind']} for a in attachments]} if attachments else {}),
                         **({'answers': dict(answers)} if answers and not message else {}),
                         # warehouse 128: this message is the customer's approval of a reading draft (approve_reading)
                         **({'reading_decision': dict(reading)} if reading else {})}
            # Founder 2026-10-28 (option b): a conversation that STARTS now is on the two-gate flow from its first
            # message -- an explicit, durable mark, not a creation date. A project that already has a brief or a
            # conversation keeps whatever flow it was on (EarlierProjectsKeepWorking).
            # The mark is repeated on every later customer message, so it stays inside any window a reader takes
            # (_bind_execution_plan reads the last 500 messages).
            recent = self.store.messages_for(project_id, limit=2)
            if (row is None and not recent) or any((m.get('interpretation') or {}).get('flow') == AF_FLOW for m in recent):
                said_meta['flow'] = AF_FLOW
            self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                                   brief_revision=row.revision if row else None, request_key=request_key,
                                   interpretation=said_meta or None)
        intent = 'answer' if answers else classify_intent(message, has_version=bool(ctx.get('latest_version_id')),
                                                          has_brief=row is not None)
        if intent == 'recommend' and self.intake_mode(project_id,account_id).paid:
            intent='requirements'
        # An explicit withdrawal refers only to a uniquely identified blocker
        # in the previous reply. Never guess which of several requirements to drop.
        if row and not answers and re.fullmatch(r'(?:אז\s+)?(?:תוותר|וותר|תוריד)\s+(?:על\s+)?זה(?:\s+כרגע)?[.!? ]*|'
                                               r'(?:skip|remove|drop)\s+(?:that|it)(?:\s+for now)?[.!? ]*', message, re.I):
            previous = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
            last_blocked = (previous[-1].get('interpretation') or {}).get('blocked') if previous else None
            blockers = [f for f in self._feasibility(row).get('findings', [])
                        if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            if last_blocked and len(blockers) == 1 and blockers[0]['item'].startswith('sign-in'):
                answers = {'login': 'none'}
                intent = 'answer'
        if attachments and not message and not answers:
            intent = 'attachment'
        if intent == 'attachment' and row is not None and not ctx.get('latest_version_id') and _bindable_images(attachments):
            intent = 'requirements'   # an image alone, before anything was built, is part of the request: never dropped
        turn = Turn(intent, lang, '')
        if intent == 'attachment':
            turn.brief_row = row
            turn.reply = T['attached_only'].format(n=T['images'](len(attachments)))
        elif intent in ('answer', 'requirements'):
            turn = self._requirements(project_id, account_id, row, message, answers or {}, request_key, lang, T, attachments)
        else:
            turn.brief_row = row
            if row is not None:
                turn.plan, turn.plan_id, turn.contract = self._approved_plan(project_id, row)
            turn.reply = self._answer(intent, row, turn.plan, ctx, message, T, lang)
            blocked_now = (self._admission_block(project_id, row, lang)
                           if intent == 'approve' and turn.plan and turn.plan.get('executable') and row and row.complete
                           else None)
            if blocked_now:                                # 79: "approve" never gets a button the banner refuses
                turn.reply = blocked_now
            elif intent == 'approve' and turn.plan and turn.plan.get('executable') and row and row.complete:
                turn.actions.append({'type': 'approve_build', 'brief_revision': row.revision,
                                     **({'cost': turn.plan['spec_gate']['cost']} if 'spec_gate' in turn.plan else {})})
            elif intent == 'approve' and row is not None and row.complete and not self._spec_ok(project_id, row) \
                    and self._feasibility(row).get('buildable'):
                from ..intake import approval_flow as AF
                turn.reply = ' '.join([AF.text(lang)['gate1_needed']] + self._gate1(turn, row, lang))
            if intent == 'modify':
                turn.actions.append({'type': 'confirm_modification', 'version_id': ctx.get('latest_version_id'),
                                     'request': message,
                                     **({'attachment_ids': [a['id'] for a in attachments]} if attachments else {})})
            if row is not None and intent != 'attachment':
                turn.questions = intake_agent.apply(row.brief, DeterministicInterpreter().interpret('', row.brief),
                                                    infer_defaults=False).asked if intent == 'missing' else []
        if attachments and intent != 'modify':
            # say only what really happened to the image (2026-11-15: "it goes with the change as context" was said
            # while the image went nowhere). The context note stays for a change to a built version only.
            T = {**T, 'attached_note': T['attached_bound' if intent in ('answer', 'requirements')
                                         and _bindable_images(attachments) else 'attached_kept']}
        if attachments and intent != 'attachment':
            turn.reply = (turn.reply + ' ' + T['attached_note'].format(n=T['images'](len(attachments)))).strip()
        if turn.blocked and turn.plan is None:              # blocked before gate 1: edit the spec (there is no plan)
            if not any(a['type'] in ('edit_requirements', 'open_requirements') for a in turn.actions):
                turn.actions.append({'type': 'edit_requirements', 'brief_revision': turn.brief_row.revision})
        elif turn.brief_row and not (turn.plan or {}).get('executable', True):
            for action in ({'type': 'show_plan', 'brief_revision': turn.brief_row.revision},
                           {'type': 'edit_requirements', 'brief_revision': turn.brief_row.revision}):
                if not any(a['type'] == action['type'] for a in turn.actions):
                    turn.actions.append(action)
        self._label_carries_its_question(turn, lang)
        turn.reply = self._not_repeated(project_id, turn, T)
        paid = turn.reservation_id is not None
        usage = (self._conversation_usage(project_id, account_id)
                 if paid or (turn.interpretation or {}).get('limit') else None)
        self.store.add_message(project_id=project_id, account_id=account_id, role='assistant', content=turn.reply,
                               brief_revision=turn.brief_row.revision if turn.brief_row else None,
                               interpretation={'intent': turn.intent, **(turn.interpretation or {}),
                                               'asked': [q.id for q in turn.questions]
                                                        + list(getattr(turn, 'asked_in_words', None) or ()),
                                               # R1/8.6: every time the system asks the persistence decision it is
                                               # counted (the frozen-run report reads it as systemAskedDecisions)
                                               **({'decision_asked': {'field': 'persistence', 'trigger':
                                                   'stale' if (turn.brief_row and (turn.brief_row.brief.hints or {})
                                                               .get('persistence_stale')) else 'discovery'}}
                                                  if any(q.id == 'content_only' for q in turn.questions) else {}),
                                               # the detector's own question, stored for the replay (_replayed_spec):
                                               # `asked` holds catalog ids only and misses a detector-only field
                                               'gap_field': ((turn.gaps or {}).get('question') or {}).get('field'),
                                               'explained': bool(getattr(turn, 'explained', False)),
                                               'actions': turn.actions, 'plan_id': turn.plan_id,
                                               **({'gate': turn.gate} if getattr(turn, 'gate', None) else {}),
                                               **({'blocked': turn.blocked} if getattr(turn, 'blocked', None) else {}),
                                               **({'unsupported': turn.unsupported} if turn.unsupported else {}),
                                               **({'venice': turn.venice} if getattr(turn, 'venice', None) else {}),
                                               # owner 2026-11-18: tokens and cost per conversation, stored with the
                                               # message (server side; Turn.to_dict does not send it to the browser)
                                               **({'usage': usage} if usage else {})},
                               interpreter=(turn.interpretation or {}).get('interpreter', 'deterministic'),
                               cost_usd=turn.cost_usd, request_key=request_key,
                               cost_state=turn.cost_state if paid else None, reservation_id=turn.reservation_id)
        return turn

    # ------------------------------------------------------------- gate 1 -> plan -> verifier -> gate 2
    def approve_spec(self, *, project_id: str, account_id: str, brief_fingerprint: str, request_key: str | None = None,
                     lang: str | None = None, canon_ack: bool = False, windows: dict | None = None) -> Turn:
        """Gate 1: the customer approves THIS spec (by fingerprint). Only now is a plan made; the separate verifier
        checks it before the customer sees it; then gate 2 shows the exact cost next to the range said earlier."""
        from ..intake import approval_flow as AF
        row = self._collected(project_id, account_id, self.briefs.latest(project_id))
        lang = lang or language_of(row.brief.prompt if row else 'שלום')
        t, T = AF.text(lang), _TXT['he' if lang == 'he' else 'en']
        turn = Turn('approve_spec', lang, '', row)
        shown = {'he': AF.CONFIRM_BUTTON['he'], 'ar': 'وافقت على المواصفات'}.get(lang, AF.CONFIRM_BUTTON['en'])
        current = row is not None and row.complete and brief_fingerprint == row.fingerprint
        feasible = current and self._feasibility(row).get('buildable')
        settled = self._picture_default(project_id, account_id, row) if feasible else None
        if settled is not None:              # S1: asked its limit -- the default is recorded and shown as a new spec
            row, current, feasible = settled, False, False
            turn.brief_row = row
        if feasible and self._contract_open(row):
            # b5: an approve button from an earlier turn, for a spec whose contract still asks: the question, not a plan
            feasible = False
        # Michael 2026-11-10 condition 3: a shown warning is read like noise. An incomplete fact canon (a business site
        # with no phone and no address) is approved only when the customer ticked the box that says so.
        if feasible and not canon_ack:
            if d.gate_canon(row.brief, lang)['status'] == 'CANON_INCOMPLETE':                # #335 (c)
                turn.reply = ' '.join([T['canon_ack']] + self._gate1(turn, row, lang))
                return self._finish(project_id, account_id, turn, request_key)
        if feasible and canon_ack and d.missing_facts(row.brief)[0]:
            # Michael 2026-11-13: the tick is recorded -- exactly which facts the customer gave up. Only a recorded
            # waiver puts the omit line in the spec. The waiver is part of the spec, so the approval binds to the
            # fingerprint that includes it.
            brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
            turn.waived = d.waive_missing(brief)
            row = self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                   expected_revision=row.revision, request_key=None)
            turn.brief_row = row
        if feasible and windows:
            # owner 2026-11-16: the windows the customer approved or rejected on the approval screen are part of the
            # spec (an approved one is built and gated, a rejected one is not built), so the approval binds to the
            # fingerprint that includes them -- the same way as the waiver above.
            brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
            if d.decide_windows(brief, windows):
                row = self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                       expected_revision=row.revision, request_key=None)
                turn.brief_row = row
        flow = {'flow': AF.FLOW} if any((m.get('interpretation') or {}).get('flow') == AF.FLOW
                                        for m in self.store.messages_for(project_id, limit=2)) else {}
        pending = MR.pending_drafts(self._messages(project_id)) if feasible else []
        if pending:
            # warehouse 128: a draft read from the customer's file waits for their decision. Nothing is approved and no
            # plan is made until they approve it (it enters the request) or discard it -- the same rule build admission
            # applies (approval_flow.spec_invalid_reason).
            self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                                   brief_revision=row.revision, request_key=request_key,
                                   interpretation={'spec_approval_refused': brief_fingerprint,
                                                   'reason': 'reading_draft_pending', **flow})
            turn.reply = MR.text(lang)['pending']
            turn.actions = MR.actions(pending[-1])
            return self._finish(project_id, account_id, turn, request_key)
        self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=shown,
                               brief_revision=row.revision if row else None, request_key=request_key,
                               interpretation={**({'spec_approved': row.fingerprint} if feasible else
                                                  {'spec_approval_refused': brief_fingerprint}),
                                               # the facts the customer gave up with this approval (the ticked box)
                                               **({'waived': list(turn.waived)} if getattr(turn, 'waived', None) else {}),
                                               **flow})
        if not current or not feasible:        # never plan for a spec the customer did not see as it is now
            if row is None:
                turn.reply = T['nothing']
            elif not row.complete:
                pend = [(q.he if lang == 'he' else q.en) for q in d.pending(row.brief)]
                turn.reply = T['approve_not_ready'] + ' ' + '; '.join(pend[:4] or ['—'])
            elif not self._feasibility(row).get('buildable'):
                blocked = [f for f in self._feasibility(row).get('findings', [])
                           if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                turn.reply = T['blocked'] + ': ' + '; '.join(self._finding_message(f, lang, T) for f in blocked[:3])
            else:
                held = self._open_question_instead_of_gate1(turn, row, lang) if current else None
                turn.reply = ' '.join(held if held is not None else [t['stale']] + self._gate1(turn, row, lang))
            return self._finish(project_id, account_id, turn, request_key)

        contract = C.build(row.brief)
        cached = self.store.plan_for(project_id, row.fingerprint)

        def make_plan(corrective=False):
            if cached is not None and not corrective:
                return cached['plan']
            return self.architect.plan(C.build(row.brief), budget_usd=self.budget_usd, status='PROPOSED')
        plan, record = AF.verified_plan(make_plan, row.brief, row.fingerprint)
        lo_hi = AF.cost_range(row.brief, self.plan_credits)
        parts = [t['stage2'] + ' —']
        turn.venice = {'agent': 'agent.venice', 'mode': 'planning', 'stage': t['stage2'], 'cost_range_credits': list(lo_hi)}
        turn.interpretation = {'verification': record}
        if plan is None:                       # the customer never sees a plan the verifier refused
            parts.append(t['refused'].format(what='; '.join(record.get('remaining') or record['problems'])[:400]))
            turn.actions.append({'type': 'edit_requirements', 'brief_revision': row.revision})
            turn.reply = ' '.join(parts)
            return self._finish(project_id, account_id, turn, request_key)
        cmp = AF.compare(lo_hi, self.credits)
        plan = {**plan, AF.GATE_KEY: {'approved_fingerprint': row.fingerprint, 'verification': record, 'cost': cmp}}
        saved = self.store.save_plan(project_id=project_id, brief_revision=row.revision,
                                     brief_fingerprint=row.fingerprint, plan=plan)
        turn.plan, turn.plan_id, turn.contract = plan, saved.get('id'), contract.to_dict()
        parts.append(t['planned'])
        if record['corrected']:
            parts.append(t['fixed'].format(what='; '.join(record['problems'])[:400]))
        blocked_by_admission = self._admission_block(project_id, row, lang) if plan.get('executable') else None
        if blocked_by_admission:
            parts.append(blocked_by_admission)
            turn.actions += [{'type': 'show_plan', 'brief_revision': row.revision},
                             {'type': 'edit_requirements', 'brief_revision': row.revision}]
        elif plan.get('executable'):
            parts.extend(AF.budget_lines(cmp, lang, plan.get('complexity')))
            parts.append(t['gate2'])
            turn.actions += [{'type': 'show_plan', 'brief_revision': row.revision},
                             {'type': 'approve_build', 'brief_revision': row.revision, 'cost': cmp}]
        else:
            blocked = [f for f in plan['feasibility'].get('findings', []) if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            parts.append(T['blocked'] + ': ' + '; '.join(self._finding_message(f, lang, T) for f in blocked[:3]))
            turn.actions += [{'type': 'show_plan', 'brief_revision': row.revision},
                             {'type': 'edit_requirements', 'brief_revision': row.revision}]
        turn.reply = ' '.join(parts)
        return self._finish(project_id, account_id, turn, request_key)

    # ------------------------------------------------------------- warehouse 128: input by image and voice
    def _customer_says(self, project_id, account_id, row, content, meta, request_key):
        """A customer message of a reading step whose content is a platform LABEL ("📎 a handwritten note", "I approved
        the draft"), not the customer's words: marked so that no new brief starts from it and no replay hears it. The
        two-gate flow mark is carried like on every customer message."""
        meta = {**meta, 'label': True}
        recent = self.store.messages_for(project_id, limit=2)
        if (row is None and not recent) or any((m.get('interpretation') or {}).get('flow') == AF_FLOW for m in recent):
            meta = {**meta, 'flow': AF_FLOW}
        self.store.add_message(project_id=project_id, account_id=account_id, role='customer', content=content,
                               brief_revision=row.revision if row else None, request_key=request_key,
                               interpretation=meta)

    def read_attachment(self, *, project_id: str, account_id: str, attachment: dict, data: bytes, purpose: str,
                        reader, lang: str | None = None, request_key: str | None = None) -> Turn:
        """The customer's stored file is read and becomes a DRAFT they see (an assistant message): never the brief,
        never a build. A reading that fails is one sentence in their language with the next action."""
        MR.check_purpose(purpose)
        row = self.briefs.latest(project_id)
        lang = MR.check_lang(lang or language_of(row.brief.prompt if row else 'שלום'))
        evidence = {'id': str((attachment or {}).get('id') or ''), 'kind': str((attachment or {}).get('kind') or ''),
                    'sha256': str((attachment or {}).get('sha256') or '')}
        self._customer_says(project_id, account_id, row, MR.text(lang)['uploaded'][purpose],
                            {'attachments': [{'id': evidence['id'], 'kind': evidence['kind']}],
                             'reading_request': {'purpose': purpose, 'attachment_id': evidence['id'],
                                                 'sha256': evidence['sha256']}}, request_key)
        try:
            source = MR.source_of(purpose, attachment, data)
            answer = MR.read(reader, purpose, data, source['mime'])
            draft = MR.draft_from_reading(purpose, answer, source=source, lang=lang,
                                          reader=getattr(reader, 'name', type(reader).__name__))
        except MR.ReadingFailed as exc:
            logging.getLogger(__name__).warning('MEDIA_READING_NOT_DRAFTED project=%s purpose=%s code=%s detail=%s',
                                                project_id, purpose, exc.code, exc.detail)
            turn = Turn('reading_failed', lang, MR.failure_sentence(exc.code, purpose, lang), row)
            turn.interpretation = {'reading_failed': {'code': exc.code, 'purpose': purpose, 'detail': exc.detail[:300],
                                                      'attachment_id': evidence['id'], 'sha256': evidence['sha256']}}
            return self._finish(project_id, account_id, turn, request_key)
        turn = Turn('reading_draft', draft['language'], MR.draft_reply(draft), row)
        turn.actions = MR.actions(draft)
        turn.interpretation = {'reading_draft': draft}
        return self._finish(project_id, account_id, turn, request_key)

    def _reading_decided(self, project_id, account_id, draft_fingerprint, request_key, lang):
        messages = self._messages(project_id)
        found = MR.find_draft(messages, draft_fingerprint)
        if found is None:
            raise KeyError(draft_fingerprint)
        draft = MR.checked_draft(found)
        row = self.briefs.latest(project_id)
        lang = MR.check_lang(lang or draft['language'])
        if draft_fingerprint in MR.decisions(messages):
            turn = Turn('reading_decided', lang, MR.text(lang)['already'], row)
            return draft, row, lang, self._finish(project_id, account_id, turn, request_key)
        return draft, row, lang, None

    def approve_reading(self, *, project_id: str, account_id: str, draft_fingerprint: str, evidence,
                        lang: str | None = None, request_key: str | None = None) -> Turn:
        """The customer approves a draft. `evidence(attachment_id)` returns the stored attachment (KeyError when it is
        gone): the file the draft was read from must still be saved with the same digest (128.4). A note or a
        recording then enters the conversation as the customer's own message, through the same path as typed text; a
        skeleton enters the brief (collected like the customer's facts). Gate 1 and gate 2 still follow."""
        draft, row, lang, done = self._reading_decided(project_id, account_id, draft_fingerprint, request_key, lang)
        if done is not None:
            return done
        src = draft['source']
        try:
            stored = evidence(src['attachment_id'])
        except KeyError:
            stored = None
        if not stored or stored.get('sha256') != src['sha256']:
            turn = Turn('reading_failed', lang, MR.failure_sentence('evidence_missing', draft['purpose'], lang), row)
            turn.interpretation = {'reading_failed': {'code': 'evidence_missing', 'purpose': draft['purpose'],
                                                      'attachment_id': src['attachment_id'], 'sha256': src['sha256'],
                                                      'draft': draft_fingerprint}}
            return self._finish(project_id, account_id, turn, request_key)
        decision = {'fingerprint': draft_fingerprint, 'decision': 'approved', 'purpose': draft['purpose'],
                    'source': {'attachment_id': src['attachment_id'], 'sha256': src['sha256']}}
        if draft['purpose'] in MR.TEXT_PURPOSES:
            # the approved text IS the customer's message: the brief is written by the same path as typed text
            return self.turn(project_id=project_id, account_id=account_id, message=draft['text'],
                             request_key=request_key, lang=draft['language'], reading=decision)
        T = MR.text(lang)
        self._customer_says(project_id, account_id, row, T['approved_shown'],
                            {'reading_decision': {**decision, 'skeleton': draft['skeleton']}}, request_key)
        row = self._collected(project_id, account_id, self.briefs.latest(project_id))
        turn = Turn('reading_approved', lang, '', row)
        parts = [T['skeleton_in']]
        if row is None:
            parts.append(T['describe'])
        elif row.complete and self._feasibility(row).get('buildable'):
            parts += self._gate1(turn, row, lang)
        else:
            parts.append(T['continue'])
        turn.reply = ' '.join(parts)
        return self._finish(project_id, account_id, turn, request_key)

    def discard_reading(self, *, project_id: str, account_id: str, draft_fingerprint: str, lang: str | None = None,
                        request_key: str | None = None) -> Turn:
        """The customer discards a draft: nothing of it is used; the file stays saved as evidence."""
        draft, row, lang, done = self._reading_decided(project_id, account_id, draft_fingerprint, request_key, lang)
        if done is not None:
            return done
        T = MR.text(lang)
        self._customer_says(project_id, account_id, row, T['discarded_shown'],
                            {'reading_decision': {'fingerprint': draft_fingerprint, 'decision': 'discarded',
                                                  'purpose': draft['purpose'],
                                                  'source': {k: draft['source'][k] for k in ('attachment_id', 'sha256')}}},
                            request_key)
        # the next action is never lost: a draft that held gate 1 is decided, so a complete spec is shown for approval
        # again (the approve button of the earlier message is no longer the last one the customer sees)
        row = self._collected(project_id, account_id, self.briefs.latest(project_id))
        turn = Turn('reading_discarded', lang, '', row)
        parts = [T['discarded']]
        if row is not None and row.complete and self._feasibility(row).get('buildable') \
                and not MR.pending_drafts(self._messages(project_id)):
            parts += self._gate1(turn, row, lang)
        turn.reply = ' '.join(parts)
        return self._finish(project_id, account_id, turn, request_key)

    @staticmethod
    def _label_carries_its_question(turn, lang=None) -> None:
        """The owner, 2026-11-16 ("the empty question"): the chat said "One question before we continue:" and nothing
        after it. The question lived only in the card of the live turn, so the stored message asked nothing: in the
        history, after a reload, or read aloud, the customer saw a label with no question (production 2026-11-16
        11:05-11:09: five such messages in one conversation). The message now carries the question in words; the card
        adds the buttons and does not repeat the text (app.js quickReplies). A label with no question to carry is a
        bug said in the log, and the label is not shown."""
        for key, T in _TXT.items():
            label = T['ask_one']
            reply = (turn.reply or '').rstrip()
            if not reply.endswith(label):
                continue
            q = turn.questions[0] if turn.questions else None
            text = ((q.he if (lang or key) != 'en' else q.en) or '').strip() if q is not None else ''
            if text:
                turn.reply = reply + ' ' + text
            else:
                logging.getLogger(__name__).error('ASK_LABEL_WITHOUT_QUESTION questions=%s',
                                                  [getattr(x, 'id', None) for x in turn.questions or ()])
                turn.reply = reply[:-len(label)].rstrip() or T['nothing']
            return

    def _finish(self, project_id, account_id, turn, request_key):
        self._label_carries_its_question(turn)
        self.store.add_message(project_id=project_id, account_id=account_id, role='assistant', content=turn.reply,
                               brief_revision=turn.brief_row.revision if turn.brief_row else None,
                               interpretation={'intent': turn.intent, **(turn.interpretation or {}), 'asked': [],
                                               'actions': turn.actions, 'plan_id': turn.plan_id,
                                               **({'gate': turn.gate} if getattr(turn, 'gate', None) else {}),
                                               **({'blocked': turn.blocked} if getattr(turn, 'blocked', None) else {}),
                                               **({'venice': turn.venice} if getattr(turn, 'venice', None) else {})},
                               interpreter='deterministic', cost_usd=Decimal('0'), request_key=request_key)
        return turn

    def _classify(self, project_id, row, message):
        from ..intake import complexity, lanes
        history = [m for m in self.store.messages_for(project_id, limit=10)
                   if not (m.get('interpretation') or {}).get('system')][-9:]
        if history and history[-1].get('role') == 'customer':
            history = history[:-1]                        # the current message was stored at turn start
        confirmed = {k: f['value'] for k, f in (row.brief.fields.items() if row else ())
                     if f.get('source') in intake_agent.CONFIRMED_SOURCES}
        det = DeterministicInterpreter().interpret(message, row.brief if row else None)
        proposed = {p.field: p.value for p in det.proposals if p.confidence == 'high'}
        c = complexity.classify(message, history, confirmed=confirmed, proposed=proposed)
        return c, lanes.choose(c.level)

    MAX_CARRIED_MESSAGES = 5          # earlier customer messages a new brief may start from
    MAX_REQUEST_CHARS = 12_000        # the whole request a brief starts from

    def _whole_request(self, project_id, message: str) -> str:
        """The text a NEW brief starts from: everything the customer wrote in this project before a brief existed,
        then this message. Production 2026-11-17, "148 דלתות": the owner pasted a full brief, the router refused it
        (a misread word), said "ההודעה שלכם נשמרה בשיחה" -- and the brief was then started from the next message
        alone, the single word "אתר". 3,295 characters of the customer's own words never reached the build.
        A message said to be kept is part of the request. Bounded; a text cut by the bound is logged."""
        earlier = [m.get('content') or '' for m in self.store.messages_for(project_id, limit=40)
                   if m.get('role') == 'customer' and not (m.get('interpretation') or {}).get('system')
                   and not (m.get('interpretation') or {}).get('label')]   # a platform label is not their words (128)
        if earlier and earlier[-1] == message:
            earlier = earlier[:-1]                        # the current message was stored at turn start
        earlier = [e.strip() for e in earlier if e.strip() and e.strip() != message.strip()]
        earlier = earlier[-self.MAX_CARRIED_MESSAGES:]
        if not earlier:
            return message
        whole = '\n'.join(earlier + [message]).strip()
        if len(whole) > self.MAX_REQUEST_CHARS:
            import logging
            logging.getLogger(__name__).warning('REQUEST_CUT project=%s chars=%s kept=%s', project_id, len(whole),
                                                self.MAX_REQUEST_CHARS)
            # the newest words win: whole earlier messages are dropped oldest first, and the message being answered
            # is never the part that is cut
            while len(earlier) > 1 and len('\n'.join(earlier + [message])) > self.MAX_REQUEST_CHARS:
                earlier = earlier[1:]
            room = max(0, self.MAX_REQUEST_CHARS - len(message) - 1)
            whole = ('\n'.join(earlier)[:room] + '\n' + message).strip()[:self.MAX_REQUEST_CHARS]
        return whole

    def _route_output(self, row, message, lang) -> Turn | None:
        """A0 (warehouse 69, released 2026-11-15): the output type is decided before the interpreter, the model and
        the brief. A type without an output profile is refused in the customer's words -- "not yet; this, yes" --
        with no default chosen, no question asked, no brief saved and no model called. The exit is the keyboard:
        the customer describes the site or app instead and the conversation continues as usual.
        A new project reads the whole message (the classifier's rules). A project that already has a brief refuses
        only an EXPLICIT request for another product, so an answer that mentions games in passing never restarts it."""
        if not message:
            return None
        from ..intake.families import classify_family, requested_family
        from ..output_profile import route
        family = classify_family(message) if row is None else requested_family(message)
        if family is None:
            return None
        routing = route(family)                  # a family the registry does not know raises here, never defaults
        if routing.supported:
            return None
        turn = Turn('requirements', lang, routing.not_yet(lang), row, [])
        turn.unsupported = family
        turn.actions.append({'type': 'describe_web_instead', 'family': family})
        return turn

    def _requirements(self, project_id, account_id, row, message, answers, request_key, lang, T, attachments=()) -> Turn:
        from ..intake import lanes
        image_defaulted = None
        if row is not None and message and not answers and not attachments:
            # the customer answers "who is in the photo?" by typing: the message IS that answer, not a new request
            asked = d.next_image_question(row.brief)
            awaiting = self._awaiting(project_id)
            if asked is not None and asked.kind == 'text' and (asked.id in awaiting or asked.field in awaiting):
                answers, message = {asked.id: message[:300]}, ''
            elif asked is not None and (asked.id in awaiting or asked.field in awaiting):
                # warehouse 113 (owner 2026-11-16): a typed answer to an image choice ("זאת הדלת של החנות") is read by
                # words -- the loop asked again and again because only a button could answer it
                from ..intake.image_answers import answers_for
                typed = answers_for(asked, message)
                if (typed.get(asked.id) == 'change' and asked.recommended
                        and row.brief.hints.get('image_change') == 'asked'):
                    # the owner, 2026-11-17: a change was already said to be unavailable; asking a third time is the
                    # loop. One question, then the closest available choice -- the question's own recommendation, said.
                    typed, image_defaulted = {asked.id: asked.recommended}, asked.recommended
                if typed:
                    answers, message = typed, ''
        refused = self._route_output(row, message, lang)    # A0 (warehouse 69): the output type, before any model
        if refused is not None:
            return refused
        cls, lane = (self._classify(project_id, row, message) if message else (None, None))
        interp = None
        closed = self._closed(project_id)
        if message:
            # owner 2026-11-18: an overrun stops the conversation. Once it was closed at its budget or its turns, no
            # message pays a model again -- a shorter message would otherwise fit under the cap and run after the
            # closing reply (D10 review). Decided before the lane and the quote.
            source = (_AtLimit(closed, 'the conversation was closed at its limit', source='closed') if closed else
                      self._interpreter(project_id, account_id, request_key, task=lane['task'])
                      if lane['lane'] in lanes.MODEL_LANES else DeterministicInterpreter())
            source.history = [m for m in self.store.messages_for(project_id, limit=6)[:-1]
                              if not (m.get('interpretation') or {}).get('system')][-4:]   # never the flow mark
            interp = source.interpret(message, row.brief if row else None)
        from ..intake import conversation_agent as agent
        if agent.enabled() and row is not None and message and not answers:
            # phase 1 of the conversation agent (the owner, 2026-11-17): no cards, so the customer answers a question
            # by typing. It counts only for the question asked in the previous turn, and only when the words name
            # exactly one option or the model quoted this message for it -- otherwise the question stays open.
            for qid in self._awaiting(project_id):
                q = d.BY_ID.get(qid)
                if q is None or q.kind != 'choice' or q.id in {x.id for x in d.IMAGE_QUESTIONS}:
                    continue
                value = agent.typed_choice(q, message) or (agent.model_choice(q, interp) if interp else None)
                if value is not None:
                    answers = {q.id: value}
                    break
        brief = row.brief if row else d.start(self._whole_request(project_id, message or ''), d.GUIDED)
        for qid, value in answers.items():
            brief = intake_agent.answer_question(brief, qid, value)
        sensitive = bool(lane and lane.get('requires_explicit_confirmation'))
        res = intake_agent.apply(brief, interp, require_confirmation=sensitive) if interp else intake_agent.apply(
            brief, DeterministicInterpreter().interpret('', brief))
        new_brief = res.brief
        if (agent.enabled() and row is not None and message and not answers
                and agent.SUBJECT_ID in self._awaiting(project_id) and not agent.names_a_subject(new_brief.prompt)):
            # the answer to "what is this about?" is part of the request the build starts from, not a side remark
            new_brief.prompt = (new_brief.prompt.rstrip() + '\n' + message.strip()).strip()
        if agent.enabled() and message and not answers and d.is_website(new_brief):
            # the business name the customer stated, recognised once (rehearsals 45702506669 / 45702519795): their answer
            # to the name question, or the one name they quoted, joins the request as their own "שם העסק:" line
            line = agent.name_to_record(d.customer_text(new_brief), message,
                                        answering=row is not None and agent.NAME_ID in self._awaiting(project_id))
            if line:                       # S4: one "שם העסק:" line -- a stated name replaces one read earlier
                new_brief.prompt = agent.with_name_line(new_brief.prompt, line)
        if row is not None and message and not answers:
            # S1: the answer to the contract's picture question is recorded where the planner reads it; after
            # ASK_PICTURE_AT_MOST questions with no answer it can read, the stated default is recorded instead
            # review B1: a reply the interpreter also took as a change of the request is not the answer
            edited = [x['field'] for x in res.applied + res.corrected + res.conflicts if x.get('field') != 'content']
            self._picture_answer(project_id, new_brief, message, edited=edited)
        if (agent.enabled() and row is not None and message and not answers
                and agent.COLOUR_ID in self._awaiting(project_id) and agent.colour_unknown_business(row.brief)):
            # row.brief, not new_brief: the interpreter already read the colours in the order they were written
            # the answer to the colour question is the customer's "color" answer (source "answer"): their colours, most
            # space first, or "category" when they left it to us -- recorded, never inferred
            chosen = agent.colour_answer(message)
            if chosen:
                new_brief = intake_agent.answer_question(new_brief, 'color', chosen)
                logging.getLogger(__name__).info('COLOUR_CHOICE project=%s choice=%s', project_id, chosen)
        # Persist only schema- and evidence-validated model decisions in the same
        # brief revision. They remain reviewable and bind to the normal approval
        # fingerprint; deterministic fallback cannot silently invent exclusions.
        if interp is not None and getattr(interp, 'semantic_decisions', None) and str(interp.interpreter).startswith('model'):
            from ..semantic_capabilities import updated_decisions
            new_brief.semantic_decisions = updated_decisions(
                new_brief.semantic_decisions, interp.semantic_decisions)
        recorded = False
        if (message and row is not None and row.complete and not res.applied and not res.conflicts and not res.corrected
                and not answers and _CONTENT_RX.search(message) and not intake_agent._off_topic('content', message)):
            new_brief, recorded = _record_content(new_brief, message), True
        if message:
            # #335 (Michael 2026-11-13): every fact the customer states (phone, e-mail, address, hours, a closed day) is
            # kept verbatim from EVERY message -- the "מה נכון?" loop lost the cafe's phone and hours from the fields.
            # task 62: read against the question it answers, as customer_messages does for the stored ones
            asked = next((str(m.get('content') or '') for m in reversed(self._messages(project_id))
                          if m.get('role') == 'assistant'), None)
            d.note_customer_texts(new_brief, [d.answer_in_context(message, asked)])
        if len(attachments) == 1 and re.search(r'לוגו|\blogo\b', message, re.I):
            a = attachments[0]
            if re.fullmatch(r'att_[a-f0-9]{32}', a.get('id','')) and re.fullmatch(r'[a-f0-9]{64}',a.get('sha256','')):
                new_brief.assets['logo'] = {k:a[k] for k in ('id','sha256','mime','size_bytes')}
                new_brief = d.answer(new_brief, {'logo':'uploaded'})
        images = _bindable_images(attachments)
        decided = {img.get('sha256') for img in new_brief.assets.get('images') or ()}
        images = [a for a in images if a['sha256'] not in decided]    # an image whose role is decided is not re-asked
        if images and not (len(attachments) == 1 and re.search(r'לוגו|\blogo\b', message, re.I)):
            # Production 2026-11-15 ("סבא שמעון"): any other image was dropped silently. Now it is bound to the brief
            # and the customer is asked what it is for (image_use, never delegated). A NEW image asks again.
            a = images[-1]
            if (new_brief.assets.get('image') or {}).get('sha256') != a['sha256']:
                for f in d.IMAGE_FIELDS:                 # a new image: its role is asked from the start
                    new_brief.fields.pop(f, None)
                new_brief.hints.pop('image_change', None)
            new_brief.assets['image'] = {k: a.get(k) for k in ('id', 'sha256', 'mime', 'size_bytes', 'width', 'height')}
        # QUESTIONS-001: the gap detector decides what is asked. It reads the open discovery questions as candidates,
        # writes the values the request implies into the brief (shown as assumptions), and its ONE ordered question
        # replaces the questionnaire's list. Only a conflict with a confirmed value is still asked back first.
        gaps, gap_q = self._gaps(project_id, message, interp, answers, new_brief, lang,
                                 contested={c['field'] for c in res.conflicts})
        # C6 (CEO 2026-10-27): the detector decides completeness. Its open material field is recorded in the brief
        # (so the approval gate sees it), a field it asks is never also shown as an assumption, and the catalog is
        # only the fallback: when the detector has nothing material left, a catalog question that may not be assumed
        # (security/privacy, not delegable, no honest default) is still asked in the catalog's words.
        new_brief.detector = True
        # a sensitive field the customer could not settle after one explained repeat stays OPEN (held), not re-asked
        new_brief.open_material = list(dict.fromkeys(([gap_q.field] if gap_q is not None else [])
                                                     + list((gaps or {}).get('held_open') or ())))
        for name, value in ((gaps or {}).get('assumed_now') or {}).items():   # "don't know": the default, shown
            if not any(a['field'] == name for a in res.assumed):
                res.assumed.append({'field': name, 'value': value, 'why': 'not known by the customer'})
        if gap_q is not None:                    # asked now, so not also announced as "chosen for you" (the stored
            res.assumed = [a for a in res.assumed if a['field'] != gap_q.field]   # default stays until answered)
        held_open = set((gaps or {}).get('held_open') or ())   # held open: the catalog does not re-ask it either
        fallback = [q for q in d.must_ask(new_brief) if q.field not in held_open and q.id not in held_open] \
            if gap_q is None and not res.conflicts else []
        res.asked = (res.asked[:len(res.conflicts)] if res.conflicts else
                     [d.BY_ID[gap_q.field]] if gap_q is not None and gap_q.field in d.BY_ID else fallback[:1])
        if not res.asked and not res.conflicts and gap_q is None:
            # #330 (Michael 20:11): nothing else is asked, but the brief still waits for a held field the customer must
            # decide (class 2, or class 3 not confirmed): that is the next question, with its buttons -- otherwise
            # the turn says "nothing new" and the brief can never complete (production 2026-11-12, personal_data).
            waiting = [d.BY_ID[f] for f in new_brief.open_material if f in d.BY_ID]
            res.asked = [q for q in waiting if d.needs_customer(q, new_brief)][:1]
        # Michael 2026-11-13 (production, bakery): one field, one question per turn -- personal_data was asked twice
        # (a yes/no line and access_scope's three options). The covering question wins; the covered one waits.
        # Michael 2026-11-15 16:15: the image's role is asked by the conversation, in context, right when it is open --
        # one question per turn, in order (what is in it, who/what, then what to do). A2/A3 never ask the customer.
        image_q = d.next_image_question(new_brief) if not res.conflicts else None
        if image_q is not None:
            res.asked = [image_q]
        res.asked = d.one_question_per_field(res.asked)
        covered = {f for q in res.asked for f in d.COVERS.get(q.field, ())} | {
            f for c in res.conflicts for f in d.COVERS.get(c['field'], ())}
        res.conflicts = [c for i, c in enumerate(res.conflicts) if c['field'] not in covered
                         and c['field'] not in {x['field'] for x in res.conflicts[:i]}]
        expected = row.revision if row else 0
        # C6: a revision when the requirements change (fingerprint), when completeness changes, or when the detector
        # moves to another open field -- so the stored brief never names a stale open field. While the brief is
        # incomplete no approval exists, so a revision with the same fingerprint invalidates nothing.
        if row is None or new_brief.fingerprint() != row.fingerprint or d.complete(new_brief) != row.complete \
                or new_brief.open_material != row.brief.open_material:
            row = self.briefs.save(project_id=project_id, account_id=account_id, brief=new_brief,
                                   expected_revision=expected, request_key=request_key)
        turn = Turn('answer' if answers and not message else 'requirements', lang, '', row, res.asked)
        turn.interpretation = interp.to_dict() if interp else None
        if turn.interpretation is not None:
            turn.interpretation.update(complexity=cls.to_dict() if cls else None, lane=lane,
                                       conflicts=res.conflicts, corrected=res.corrected)
            if res.dropped:      # refused by the brief (e.g. technical text as the goal): logged, the turn continues
                turn.interpretation['dropped'] = list(turn.interpretation.get('dropped') or []) + res.dropped
        if interp is not None:
            turn.cost_usd = None if interp.cost_usd is None else Decimal(str(interp.cost_usd))
            turn.cost_state, turn.reservation_id = interp.cost_state, interp.reservation_id
        turn.gaps = gaps
        known_name = agent.stated_name(d.customer_text(row.brief)) if agent.enabled() and d.is_website(row.brief) else None
        if known_name and interp is not None and (interp.reply or '').strip():
            # a name the customer stated is never asked again, in the model's words either: the sentence that asks it
            # becomes one that says it (rehearsals 45702506669 / 45702519795). The turn's record keeps the model's reply.
            name_said = agent.without_name_question(interp.reply, known_name, lang)
            if name_said != interp.reply:
                import copy
                interp = copy.copy(interp)
                interp.reply = name_said
        parts = []
        if any(k.startswith('image_place_') for k in answers) and row.brief.hints.get('image_hero_taken') == 'yes':
            parts.append(T['image_hero_taken'])      # one main image per page: the place is asked again
        if any(answers.get(q) == 'change' for q in ('image_use', 'image_use_other')):
            parts.append(T['image_change'])          # not recorded: the question stays open (discovery._settle_image)
        if image_defaulted:
            parts.append(T['image_change_defaulted'].format(choice=_label('image_use', image_defaulted, lang)))
        # The model's conversational advice is not an action: the authoritative
        # questions, changes, blockers and approval controls below still apply.
        if interp is not None and interp.reply and not res.conflicts:
            parts.append(interp.reply)
        stated = [x for x in res.applied if x['field'] not in {c['field'] for c in res.corrected}]
        # the owner, 2026-11-23: when the model already said what it understood in its own words, the list of field
        # labels ("הבנתי: צבע: ...") is not said again under it
        if interp is not None and (interp.reply or '').strip() and str(getattr(interp, 'interpreter', '')).startswith('model'):
            stated = []
        if stated:
            parts.append(f'{T["got"]}: ' + '; '.join(_label(x['field'], x['value'], lang) for x in stated[:6]) + '.')
        if res.corrected:
            parts.append(f'{T["corrected"]}: ' + '; '.join(_label(c['field'], c['new'], lang) for c in res.corrected[:4]) + '.')
        for c in res.conflicts[:3]:
            name = (d.BY_ID[c['field']].he if lang == 'he' else d.BY_ID[c['field']].en) if c['field'] in d.BY_ID else c['field']
            if c['current'] is None:     # the question itself is the card below: the text names the topic only
                parts.append(T['confirm_sensitive_words' if agent.enabled() else 'confirm_sensitive'].format(
                    field=_short(c['field'], lang)))
            else:
                # the owner, 2026-11-23: one natural check, not "קודם נקבע ... לא שיניתי — מה נכון?"
                q_ = d.BY_ID.get(c['field'])
                val = (lambda v: d._label(q_, v, lang)) if q_ else str
                parts.append(T['conflict'].format(field=_short(c['field'], lang), current=val(c['current']),
                                                  proposed=val(c['proposed'])))
        short = [x for x in res.assumed if d.BY_ID.get(x['field']) and d.BY_ID[x['field']].kind == 'choice']
        if short:
            more = len(res.assumed) - len(short[:3])
            parts.append(f'{T["assumed"]}:' + _lines(_label(x['field'], x['value'], lang) for x in short[:3])
                         + (T['more'].format(n=more).lstrip() + '\n' if more > 0 else ''))
        unsure = bool(message and re.search(_UNSURE_RX, message.strip().lower(), re.I))
        # the conversation agent asks what the product is about before anything else, and never offers the approval
        # of a request that does not say it (rehearsal 44126201300: "אתר" alone reached the approval in three turns)
        no_subject = agent.enabled() and not agent.names_a_subject(row.brief.prompt)
        # 2026-11-22: a website is not offered for approval before the customer named the business (see NAME_QUESTION)
        no_name = (agent.enabled() and not no_subject and d.is_website(row.brief)
                   and not agent.declares_a_name(d.customer_text(row.brief))
                   and self._times_asked(project_id, agent.NAME_ID) < agent.ASK_NAME_AT_MOST)
        # the owner, 2026-11-22: a business we do not know is asked about colours once (see COLOUR_QUESTION)
        no_colour = (agent.enabled() and not no_subject and not no_name and d.is_website(row.brief)
                     and agent.colour_unknown_business(row.brief)
                     and self._times_asked(project_id, agent.COLOUR_ID) < agent.ASK_COLOUR_AT_MOST)
        if row.complete and gap_q is None and not no_subject and not no_name and not no_colour:
            feas = self._feasibility(row)
            if feas.get('buildable'):
                if recorded:
                    parts.append(T['content_saved'])
                if self._spec_ok(project_id, row):         # nothing changed since gate 1: the verified plan stands
                    turn.plan, turn.plan_id, turn.contract = self._approved_plan(project_id, row)
                    parts.append(self._admission_block(project_id, row, lang) or T['ready_again'])
                    turn.actions.append({'type': 'show_plan', 'brief_revision': row.revision})
                else:                                      # gate 1: the spec and the range; no plan yet
                    unpriced = self._unpriced_gate(project_id, account_id, row, lang, turn)   # 77
                    parts.extend(unpriced if unpriced else self._gate1(turn, row, lang, project_id))
            else:
                blocked = [f for f in feas.get('findings', []) if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                turn.blocked = [f['item'] for f in blocked]
                parts.append(T['blocked'] + ': ' + '; '.join(
                    self._finding_message(f, lang, T) for f in blocked[:3]))
        elif res.asked or gap_q is not None:                # still listening: no plan while a material field is open
            # C6: the detector may still ask while the catalog is already complete; a blocker is known (and said)
            # now, not after the last question -- from the feasibility check, never from a plan (no plan before gate 1)
            if row.complete or d.catalog_complete(row.brief):
                blocked = [f for f in self._feasibility(row).get('findings', [])
                           if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
                turn.blocked = [f['item'] for f in blocked]
                if blocked and not row.complete:
                    parts.append(T['blocked'] + ': ' + '; '.join(self._finding_message(f, lang, T) for f in blocked[:3]))
            if gap_q is not None and not res.conflicts and image_q is None:
                carded = gap_q.field in {q.field for q in res.asked}
                why = gap_q.text.startswith(_WHY_PREFIXES)
                # Michael 2026-11-13: when the field's card is shown, the question comes from the card only; the
                # text is short context (an explanation after "why?", without its question), never the question
                parts.append(gap_q.text if not carded else (_no_question(gap_q.text) or T['ask_one']) if why
                             else T['ask_one'])
                turn.explained = why
            else:                                           # only a conflict with a confirmed value is asked back here
                self._last_reply_was_why = False
                repeated = self._repeats(project_id, res.asked)
                explain = unsure or repeated
                parts.extend(self._ask_line(res, row, lang, T, unsure=explain))
                turn.explained = explain and not self._last_reply_was_why
        limit = self._turn_limit(project_id, interp, answers)
        if limit is not None:
            return self._closing_turn(project_id, turn, row, limit, parts, lang, T)
        if (interp is not None and (interp.reply or '').strip()
                and (any(a.get('type') == 'approve_spec' for a in turn.actions)
                     or (turn.interpretation or {}).get('contract_asked'))):
            # one message never both asks and shows the summary. The summary comes when nothing is left to ask, so the
            # model's question goes and its other words stay (rehearsals 45702506669 / 45702519795: "...האם תרצו שנתחיל
            # להכין את הסיכום? שלב 1 מתוך 2 — ..." asked a question and showed the summary in one message)
            parts = [p for p in ((_no_question(p) if p == interp.reply else p) for p in parts) if p]
        if not parts:
            parts.append(T['nothing'])
        turn.reply = re.sub(r'\n +', '\n', ' '.join(parts)).strip()
        # CEO 2026-11-08: no questionnaire. While the conversation is still listening (no gate 1, no blocker, no
        # conflict), the customer sees the model's own reply and question, not the detector's question, the
        # "chosen for you" list or quick-reply buttons. The detector still records the brief and decides
        # completeness; the approval gates, cost and blockers above stay authoritative and unchanged.
        listening = (not (row.complete and gap_q is None and not no_subject and not no_name and not no_colour) and not res.conflicts
                     and not turn.blocked)
        model_reply = (interp is not None and str(getattr(interp, 'interpreter', '')).startswith('model')
                       and bool((interp.reply or '').strip()))
        if listening and model_reply:
            turn.reply, turn.questions = interp.reply.strip(), []
            # #330 (Michael 2026-11-12): when the NEXT question is for a field only the customer may set
            # (delegable=False: content_only, access_scope, unavailable), the customer sees BOTH the model's reply and
            # that exact question with its buttons. Hiding it left a landing page unable to ever reach the summary:
            # the model asked "anything else?" while the brief waited for an answer no typed text could give.
            # When nothing is asked this turn, the next question is the open field the brief still waits for: a field
            # "held open" after an unsettled repeat is otherwise never asked again, and a customer-only one can then
            # never be set (production 2026-11-12: content_only held open, the summary unreachable).
            nxt = res.asked or [d.BY_ID[f] for f in (row.brief.open_material or ()) if f in d.BY_ID]
            held = self._customer_only_question(nxt, row.brief)
            if held is not None:
                # Michael 2026-11-13: the question comes from the card only. The model's reply keeps its context
                # and loses any sentence that asks (it asked the same field in its own words, then the card again)
                turn.reply = _no_question(turn.reply) or T['ask_one']
                turn.questions = [held]
        elif listening and os.getenv('OMNI_INTAKE_MODEL') == '1' and not answers and interp is not None:
            # the model is configured but did not answer in time: say so; never pass the questionnaire off as it.
            # 2026-11-19: a provider that REFUSED the request (no credit, a revoked key) is not "busy" -- sending
            # again changes nothing. Say what happened, and log it loudly for the owner.
            refused = _provider_refused(interp)
            turn.reply, turn.questions = T['model_refused' if refused else 'model_unavailable'], []
            if refused:
                logging.getLogger(__name__).error('INTAKE_PROVIDER_REFUSED project=%s reason=%s', project_id, refused)
        self._card_limit(project_id, account_id, turn, lang, T, request_key)
        if no_subject and not res.conflicts and not turn.blocked:
            base = _no_question(interp.reply.strip()) if model_reply else ''   # the model's own words, never a card list
            turn.reply = ((base or '') + ' ' + agent.SUBJECT_QUESTION['he' if lang == 'he' else 'en']).strip()
            turn.questions, turn.asked_in_words = [], [agent.SUBJECT_ID]
            return turn
        # never over a model failure: "the model refused / is busy" is the truth of this turn (found by
        # tests/test_venice_refusal_is_not_spend.py on this change)
        model_failed = turn.reply in (T['model_refused'], T['model_unavailable'])
        if no_name and not res.conflicts and not turn.blocked and not turn.questions and not model_failed:
            said = _no_question(interp.reply.strip()) if model_reply else ''   # the model's words, never a card list
            # two different names the customer wrote are asked back as a choice, quoting both (agent.name_question)
            turn.reply = ((said or '') + ' ' + agent.name_question(d.customer_text(row.brief), lang)).strip()
            turn.asked_in_words = [agent.NAME_ID]
            return turn
        if no_colour and not model_failed and not res.conflicts and not turn.blocked and not turn.questions:
            words = _no_question(interp.reply.strip()) if model_reply else ''   # the model's words, never a card list
            turn.reply = ((words or '') + ' ' + agent.COLOUR_QUESTION['he' if lang == 'he' else 'en']).strip()
            turn.asked_in_words = [agent.COLOUR_ID]
            return turn
        if agent.enabled() and turn.questions:
            # no card: the question is part of the reply, in words; it is still recorded as asked, so the next
            # typed message is read against it (see the top of this function)
            q = turn.questions[0]
            if not agent.has_question(turn.reply) or turn.reply.strip() in (T['ask_one'].strip(), ''):
                base = '' if turn.reply.strip() == T['ask_one'].strip() else turn.reply.strip()
                turn.reply = (base + ' ' + agent.asked_in_words(q, lang)).strip()
            turn.asked_in_words = [x.id for x in turn.questions]
            turn.questions = []
        return turn

    def _conversation_usage(self, project_id, account_id) -> dict | None:
        """The conversation's tokens and cost so far, as reported per call (owner 2026-11-18). The reservations are the
        source of truth: a recount by SQL equals this. Never fails the turn: an error is kept as `usage_error`."""
        svc = self.reservations
        if svc is None or not account_id or not hasattr(svc, 'conversation_usage'):
            return None
        from ..intake import conversation_agent as agent
        try:
            u = svc.conversation_usage(f'project:{account_id}:{project_id}')
        except Exception as exc:
            logging.getLogger(__name__).error('INTAKE_CONVERSATION_USAGE_FAILED project=%s: %s: %s', project_id,
                                              type(exc).__name__, str(exc)[:200])
            return {'usage_error': type(exc).__name__}
        u = {**u, 'max_turns': agent.MAX_TURNS if agent.enabled() else None}
        logging.getLogger(__name__).info(
            'INTAKE_CONVERSATION_USAGE project=%s turns=%s input_tokens=%s output_tokens=%s settled_usd=%s held_usd=%s '
            'unknown=%s open=%s models=%s', project_id, u['turns'], u['input_tokens'], u['output_tokens'],
            u['settled_usd'], u['held_usd'], u['unknown_calls'], u['open_calls'], ','.join(u['models']))
        return u

    def _turn_limit(self, project_id, interp, answers) -> dict | None:
        """The conversation limit this turn runs into, or None. The paid call was refused (interp.limit) -- or the message
        took the free lane (a greeting, "תודה") after the conversation had stopped: it never reaches the model, and
        must not read "the provider is busy" (skeptic of the D10 plan, 2026-11-18). A button answer is free and goes on."""
        limit = getattr(interp, 'limit', None) if interp is not None else None
        if limit:
            return dict(limit)
        if answers:
            return None
        if interp is None or str(getattr(interp, 'interpreter', '')).startswith('model') or \
                getattr(interp, 'reservation_id', None):
            # a paid call ran (its reply may be late): its own outcome stands, never a carried 'daily' (D10 review)
            return None
        closed = self._closed(project_id)
        if closed:
            return {'kind': closed, 'source': 'carried'}
        prev = self._last_assistant(project_id)
        carried = ((prev or {}).get('interpretation') or {}).get('limit')
        if carried and carried.get('kind') == 'daily':      # a pause carries to the very next message only
            return {'kind': 'daily', 'source': 'carried'}
        return None

    def _closed(self, project_id) -> str | None:
        """'budget' or 'turns' when the conversation was closed at that limit; 'daily' and 'busy' pass by themselves and
        close nothing. D10 review: read from the last assistant message that CARRIES a limit, not the last message --
        a button answer, an intent reply or an image turn in between stores none and used to reopen the paid path."""
        try:
            msgs = self.store.messages_for(project_id, limit=200)
        except Exception:
            return None
        for m in reversed(msgs):
            if m.get('role') != 'assistant':
                continue
            kind = (((m.get('interpretation') or {}).get('limit')) or {}).get('kind')
            if kind:
                # the owner, 2026-11-23: there is no turn cap, so a conversation closed at the old 8 turns is open again
                return kind if kind == 'budget' else None
        return None

    def _last_assistant(self, project_id) -> dict | None:
        try:
            msgs = self.store.messages_for(project_id, limit=6)
        except Exception:
            return None
        return next((m for m in reversed(msgs) if m.get('role') == 'assistant'), None)

    def _closing_turn(self, project_id, turn, row, limit, parts, lang, T):
        """Owner 2026-11-18: an overrun stops the conversation and does not crash it. No question and no card: the reply
        says why the assistant stopped, keeps what this message recorded, and leads to the way on -- the summary with
        its approval when the spec is ready (gate 1, built above at no model cost), else the specification tab."""
        kind = limit.get('kind') if limit.get('kind') in ('budget', 'turns', 'daily', 'busy') else 'budget'
        prev = self._last_assistant(project_id)
        prev_limit = ((prev or {}).get('interpretation') or {}).get('limit') or {}
        prev_text = (prev or {}).get('content') or ''
        if kind == 'busy':
            # the turn cap is reached only by calls still in flight: not a closing, the next message may go through.
            # Two in a row never repeat (warehouse 113), and a turn that completed the spec keeps its summary and
            # the gate-1 approval it offers (D10 review: the approve button came without the summary or the cost).
            turn.questions, turn.asked_in_words = [], []
            intro = T['limit_busy_alt'] if prev_text.startswith(T['limit_busy']) else T['limit_busy']
            if any(a.get('type') in ('approve_spec', 'show_plan') for a in turn.actions):
                turn.reply = re.sub(r'\n +', '\n', ' '.join(x for x in [intro, *parts] if x)).strip()
            else:
                got = [x for x in parts if x.startswith((T['got'], T['corrected']))]
                turn.reply = ' '.join([intro, *got]).strip()
            turn.interpretation = {**(turn.interpretation or {}), 'limit': {'kind': 'busy',
                                                                           'source': limit.get('source', 'reserve')}}
            return turn
        closing = ('budget', 'turns')
        if kind in closing and prev_limit.get('kind') in closing:
            # warehouse 113: never the same message twice in a row -- the follow-up wording alternates. Only after a
            # closing: after 'busy' a real stop says why it stopped, and 'daily' keeps saying "later" (D10 review)
            intro = T['limit_still_alt'] if prev_text.startswith(T['limit_still']) else T['limit_still']
        elif kind == 'daily' and prev_limit.get('kind') == 'daily':
            intro = T['limit_daily_alt'] if prev_text.startswith(T['limit_daily']) else T['limit_daily']
        else:
            intro = T[f'limit_{kind}']
        from ..intake import conversation_agent as agent
        if not agent.enabled():
            # the questionnaire accounts (no agent): the model stops, the cards go on -- a button answer is free
            turn.reply = re.sub(r'\n +', '\n', ' '.join(x for x in [intro, *parts] if x)).strip()
            turn.interpretation = {**(turn.interpretation or {}), 'limit': {'kind': kind,
                                                                           'source': limit.get('source', 'reserve')}}
            return turn
        turn.questions, turn.asked_in_words = [], []
        ready = any(a.get('type') in ('approve_spec', 'show_plan') for a in turn.actions)
        if ready:
            lines = [intro, T['limit_ready'], *parts]
        else:
            turn.actions = [a for a in turn.actions if a.get('type') != 'approve_spec']
            names = [_short(f, lang) for f in (row.brief.open_material or ()) if f in d.BY_ID] if row is not None else []
            # what was recorded, what was updated (D10 review: a change made at the limit is told), what blocks
            got = [x for x in parts if x.startswith((T['got'], T['corrected'], T['blocked']))]
            lines = [intro, *got, T['limit_incomplete'].format(missing=', '.join(names[:4])) if names
                     else T['limit_incomplete_any']]
            # D10 review (confirmed): the spec tab edits only answered fields and, with no card, a typed answer is
            # read only against a question that was asked -- so naming the gaps alone was a dead end. One open
            # question the words can answer is asked here and recorded as asked; the next typed message is read
            # against it by words, with no model and no cost.
            ask = self._free_question(row)
            if ask is not None:
                lines += [T['limit_ask'], agent.asked_in_words(ask, lang)]
                turn.asked_in_words = [ask.id]
            elif names:
                lines.append(T['limit_incomplete_any'])
            if row is not None and not any(a.get('type') == 'edit_requirements' for a in turn.actions):
                turn.actions.append({'type': 'edit_requirements', 'brief_revision': row.revision})
        turn.reply = re.sub(r'\n +', '\n', ' '.join(x for x in lines if x)).strip()
        turn.interpretation = {**(turn.interpretation or {}), 'limit': {'kind': kind,
                                                                       'source': limit.get('source', 'reserve')}}
        logging.getLogger(__name__).info('INTAKE_CONVERSATION_STOPPED project=%s kind=%s source=%s ready=%s',
                                         project_id, kind, limit.get('source'), ready)
        return turn

    @staticmethod
    def _free_question(row):
        """The first open field whose answer a typed message can give without a model (a choice question with words),
        or None."""
        from ..intake import conversation_agent as agent
        if row is None:
            return None
        images = {x.id for x in d.IMAGE_QUESTIONS}
        for f in row.brief.open_material or ():
            q = d.BY_ID.get(f)
            if q is not None and q.kind == 'choice' and q.id not in images and agent.WORDS.get(q.id):
                return q
        return None

    def _not_repeated(self, project_id, turn, T) -> str:
        """Warehouse 113: the assistant never sends the same message twice in a row. When nothing moved, it says so in
        other words (and, with a question card, points at the card) instead of repeating itself."""
        try:
            prev = self.store.messages_for(project_id, limit=6)
        except Exception:
            return turn.reply
        last = next((m for m in reversed(prev) if m.get('role') == 'assistant'), None)
        if not last or (last.get('content') or '').strip() != (turn.reply or '').strip():
            return turn.reply
        if list(((last.get('interpretation') or {}).get('asked') or ())) != [q.id for q in turn.questions]:
            return turn.reply                     # the same short line over a NEW question card is progress, not a repeat
        alt = T['rephrase_q'] if turn.questions else T['rephrase']
        return alt if alt.strip() != (last.get('content') or '').strip() else alt + ' (' + T['ask_one'].rstrip(':') + ')'

    def _times_asked(self, project_id, qid: str) -> int:
        """How many assistant turns of this conversation asked `qid` (their stored `asked`), within the last 60 messages."""
        try:
            prev = self.store.messages_for(project_id, limit=60)
        except Exception:
            return 0
        return sum(1 for m in prev if m.get('role') == 'assistant' and qid in ((m.get('interpretation') or {}).get('asked') or ()))

    def _contract_asked(self, project_id) -> str | None:
        """The build contract's question the last assistant turn asked in words (_open_question_instead_of_gate1)."""
        try:
            prev = self.store.messages_for(project_id, limit=6)
        except Exception:
            logging.getLogger(__name__).error('CONTRACT_ASKED_UNREAD project=%s', project_id, exc_info=True)
            return None
        last = next((m for m in reversed(prev) if m.get('role') == 'assistant'), None)
        return ((last or {}).get('interpretation') or {}).get('contract_asked')

    def _times_contract_asked(self, project_id, qid: str) -> int:
        """How many assistant turns asked the contract's question `qid`, within the last 60 messages. A store that
        cannot be read is logged at ERROR and counts as never asked (the question is asked again, never defaulted)."""
        try:
            prev = self.store.messages_for(project_id, limit=60)
        except Exception:
            logging.getLogger(__name__).error('CONTRACT_ASKED_UNCOUNTED project=%s question=%s', project_id, qid,
                                              exc_info=True)
            return 0
        return sum(1 for m in prev if m.get('role') == 'assistant'
                   and (m.get('interpretation') or {}).get('contract_asked') == qid)

    def _picture_answer(self, project_id, brief, message: str, *, edited=()) -> None:
        """S1: when the last turn asked a picture question of the contract, this message may be its answer. Review B1
        (49d61d3): only a reply that reads as one is recorded (capability_planner.read_picture_answer -- not a question,
        a change to the request, a phone / address / labelled field, or an item that is not a short noun phrase), and
        not one the interpreter also took as a change (`edited`: the fields it set). "I don't know / skip / you decide"
        records the stated default at once. Anything else is not recorded: the question is asked once more, at most
        ASK_PICTURE_AT_MOST times in all, and then the stated default is recorded (in the summary and the contract)."""
        from ..capability_planner import ASK_PICTURE_AT_MOST, read_picture_answer
        log = logging.getLogger(__name__)
        qid = self._contract_asked(project_id)
        if qid not in d.PICTURE_QUESTIONS:
            return
        kind, value = read_picture_answer(message, qid)
        if kind == 'answer' and edited:
            kind, value = 'unread', 'also read as a change of ' + ', '.join(sorted(set(edited)))
        if kind == 'answer':
            d.record_picture_answer(brief, qid, ' '.join(message.split()))
            log.info('PICTURE_ANSWER_RECORDED project=%s question=%s', project_id, qid)
        elif kind == 'decline':
            d.record_picture_answer(brief, qid, None)
            log.info('PICTURE_QUESTION_DECLINED project=%s question=%s: the stated default', project_id, qid)
        elif self._times_contract_asked(project_id, qid) >= ASK_PICTURE_AT_MOST:
            d.record_picture_answer(brief, qid, None)
            log.warning('PICTURE_QUESTION_DEFAULTED project=%s question=%s asked=%d last_reply=%s', project_id, qid,
                        ASK_PICTURE_AT_MOST, value)
        else:
            log.info('PICTURE_ANSWER_UNREAD project=%s question=%s: %s', project_id, qid, value)

    def _picture_default(self, project_id, account_id, row):
        """S1, the approve button of an earlier turn: a picture question the contract still asks after it was asked
        ASK_PICTURE_AT_MOST times gets its stated default, saved as a new revision (returned), else None."""
        from ..capability_planner import ASK_PICTURE_AT_MOST
        due = {qid for qid in d.PICTURE_QUESTIONS if self._times_contract_asked(project_id, qid) >= ASK_PICTURE_AT_MOST}
        if not due:                          # nothing asked its limit: no compile
            return None
        brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
        changed = False
        for q in self._contract_open(row):
            if q.id in due:
                changed = d.record_picture_answer(brief, q.id, None) or changed
        if not changed:
            return None
        return self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                expected_revision=row.revision, request_key=None)

    def _awaiting(self, project_id) -> set:
        """What the last assistant turn waits for: the question ids it showed (`asked`) and the fields it said were
        blocking (`blocked`). A typed answer is read against these only, never against a question nobody asked."""
        try:
            prev = self.store.messages_for(project_id, limit=6)
        except Exception:
            return set()
        last = next((m for m in reversed(prev) if m.get('role') == 'assistant'), None)
        meta = (last or {}).get('interpretation') or {}
        return set(meta.get('asked') or ()) | set(meta.get('blocked') or ())

    def _last_asked(self, project_id) -> str | None:
        """The question id the last assistant turn showed (stored as `asked`), or None."""
        try:
            prev = self.store.messages_for(project_id, limit=6)
        except Exception:
            return None
        last = next((m for m in reversed(prev) if m.get('role') == 'assistant'), None)
        asked = ((last or {}).get('interpretation') or {}).get('asked') or ()
        return asked[0] if asked else None

    def _cards_shown(self, project_id, qid) -> int:
        """How many assistant turns of this conversation already showed this question's card (stored as `asked`)."""
        try:
            prev = self.store.messages_for(project_id, limit=200)
        except Exception:
            return 0
        return sum(1 for m in prev if m.get('role') == 'assistant'
                   and qid in ((m.get('interpretation') or {}).get('asked') or ()))

    def _card_limit(self, project_id, account_id, turn, lang, T, request_key):
        """Michael 2026-11-13 (#339): the same unanswered card is shown at most CARD_LIMIT times. Then a privacy-safe
        default (said now, in this turn) or a block with a direct link to the Requirements tab."""
        row = turn.brief_row
        if not turn.questions or row is None:
            return
        q = turn.questions[0]
        if not d.needs_customer(q, row.brief) or self._cards_shown(project_id, q.id) < CARD_LIMIT:
            return
        topic = _short(q.field, lang)
        from ..intake import conversation_agent as agent
        if agent.enabled() and q.field not in SAFE_DEFAULT and q.options:
            # the conversation agent has no Requirements-tab card to send the customer to: a question it cannot
            # default stays asked, in words, with the choices named (conversation rehearsal 2026-11-17: the doors
            # conversation dead-ended on "choose it in the Requirements tab")
            turn.reply = T['still_in_words'].format(
                topic=topic, opts=' / '.join(o.he if lang == 'he' else o.en for o in q.options))
            return
        if q.field in d.IMAGE_FIELDS:
            # warehouse 113: the image's role has no safe default and is never delegated, so blocking it behind the
            # Requirements tab left the customer with no way forward in the chat. The card stays, with its buttons,
            # and the text says how to answer -- in words or by a button.
            turn.reply = T['image_still'].format(
                topic=topic, opts=' / '.join(o.he if lang == 'he' else o.en for o in q.options)) if q.options else T['image_still_text']
            return
        if q.field in SAFE_DEFAULT:
            brief = d.Brief.from_dict(json.loads(json.dumps(row.brief.to_dict())))
            value = SAFE_DEFAULT[q.field]
            brief.fields[q.field] = {'value': value, 'source': 'default', 'question_id': q.id,
                                     'confidence': SAFE_CONFIDENCE}
            if q.field == 'access_scope' and not d.confirmed(brief, 'personal_data'):
                brief.fields['personal_data'] = {'value': 'no', 'source': 'default', 'question_id': q.id,
                                                 'confidence': SAFE_CONFIDENCE}
            brief.open_material = [f for f in (brief.open_material or ()) if f not in (q.field, 'personal_data')]
            turn.brief_row = self.briefs.save(project_id=project_id, account_id=account_id, brief=brief,
                                              expected_revision=row.revision, request_key=request_key)
            turn.reply = T['safe_default'].format(topic=topic, label=_label(q.field, value, lang).split(': ', 1)[-1])
            turn.questions = []
        else:
            turn.reply = T['card_blocked'].format(topic=topic)
            turn.questions = []
            turn.blocked = list(dict.fromkeys(list(turn.blocked or ()) + [q.field]))
            turn.actions = [a for a in turn.actions if a['type'] != 'edit_requirements']
            turn.actions.append({'type': 'open_requirements', 'field': q.field,    # the direct link to the tab
                                 'brief_revision': row.revision})

    @staticmethod
    def _still_held(held, spec, brief) -> set:
        """The detector's held-open fields that stay open: answered later (typed or edited) releases one, and
        (#330, Michael 20:11) so does a CONFIRMED value in the brief -- the hold never blocks a confirmed field."""
        return {h for h in held if spec.value(h) is None and not d.confirmed(brief, h)}

    @staticmethod
    def _customer_only_question(asked, brief=None):
        """The next question when the customer must decide it -- a field only they may set (delegable=False) or a
        sensitive one not yet confirmed (d.CONFIRM_REQUIRED) -- else None. Decided by the next question itself, not
        by how many fields are still missing."""
        q = (asked or [None])[0]
        if q is None:
            return None
        if getattr(q, 'delegable', True) is False:
            return q
        return q if brief is not None and d.needs_customer(q, brief) else None

    @staticmethod
    def _heard(message, answers, proposals, lang):
        """(the customer's words, the proposals they carry, typed?) for one customer turn. A quick-reply button's
        label is the customer's words and its value is a stated answer -- but a label is never typed text."""
        from ..intake.interpreter import Proposal
        if message or not answers:
            return message or '', list(proposals or ()), True
        labels = [(q, v, next((o.he if lang == 'he' else o.en for o in d.BY_ID[q].options if o.value == v), str(v)))
                  for q, v in answers.items() if q in d.BY_ID]
        said = '; '.join(label for _, _, label in labels)
        props = [Proposal(d.BY_ID[q].field, v, 'high', label) for q, v, label in labels if v != d.DELEGATE]
        if any(v == d.DELEGATE for _, v, _ in labels):
            said += ' ' + ('תחליט אתה' if lang == 'he' else 'you decide')
        return said, props, False

    @staticmethod
    def _closed_in_brief(brief) -> set[str]:
        """Fields the brief has CLOSED to a question; the detector asks only outside this set (its own fields with
        no catalog question are never closed here). A field the customer already decided (answer / message), a skipped
        one, or one that does not apply to this brief (ask_if false) is never asked -- this filters the detector's
        list, it does not bring back the catalog's questionnaire."""
        vals = d._ctx(brief)
        closed = set()
        for q in d.QUESTIONS:
            f = brief.fields.get(q.field)
            if (f and f.get('source') in intake_agent.CONFIRMED_SOURCES) or q.id in brief.skipped or not q.ask_if(vals):
                closed.update((q.field, q.id))
        return closed

    def _gaps(self, project_id, message, interp, answers, brief, lang, contested=()):
        """(gaps evidence, the one next Question or None).

        The spec is rebuilt from the durable conversation on EVERY turn (_replayed_spec): the store is the only
        source of truth, so another server, a restart or a new instance asks exactly what this one would."""
        from ..intake.gaps import Questioner
        said, proposals, typed = self._heard(message, answers, getattr(interp, 'proposals', ()), lang)
        if not said:
            return None, None
        spec, previous, held = self._replayed_spec(project_id)
        spec = self._family_for(spec, said, typed)
        settle, unsure, hold, assume = self._clarify(spec, previous, said, typed)
        spec.hear(said, proposals, settle=settle)      # "what?" keeps the question open (explained, not skipped)
        if hold or self._unsettled_sensitive(spec, previous, settle):
            held.add(previous)
        delegated = self._delegated_defaults(spec, previous, held, said, typed, brief=brief)
        held = self._still_held(held, spec, brief)
        assumed_now = dict(delegated)
        for name, value in delegated.items():
            q0 = d.BY_ID[name]
            brief.fields[name] = {'value': value, 'source': 'delegated', 'question_id': q0.id,
                                  'confidence': 'assumed'}
        if assume and spec.value(previous) is not None:   # the default the field now holds, written and shown
            assumed_now[previous] = spec.value(previous)
            q0 = d.BY_ID.get(previous)
            f0 = brief.fields.get(previous)
            if q0 is not None and not (f0 and f0.get('source') in intake_agent.CONFIRMED_SOURCES) \
                    and (q0.kind == 'text' or assumed_now[previous] in {o.value for o in q0.options}):
                brief.fields[previous] = {'value': assumed_now[previous], 'source': 'default', 'question_id': q0.id,
                                          'confidence': 'assumed'}
        pending = [q.field for q in d.pending(brief)]
        g = spec.detect(pending)
        for name, imp in g['implied'].items():        # implied by the request: an assumption in the brief, not asked
            q = d.BY_ID.get(name)
            if q is not None and name not in brief.fields and (q.kind == 'text' or imp['value'] in {o.value for o in q.options}):
                brief.fields[name] = {'value': imp['value'], 'source': 'default', 'question_id': q.id, 'confidence': 'inferred'}
        for name, value in g['proposed'].items():     # sensitive: pre-selected, still confirmed by the customer
            brief.hints.setdefault(name, value)
        closed = self._closed_in_brief(brief)
        allowed = self._askable([n for n in g['missing_material'] if n not in held], closed, previous,
                                unsure=unsure, contested=contested)
        model_turn = str(getattr(interp, 'interpreter', '')).startswith('model')
        gateway = getattr(self.worker_interpreter, 'gateway', None) if model_turn else None   # one call, same budget
        q = Questioner(getattr(gateway, 'complete_json', None)).next(spec, pending, explain=unsure, allowed=allowed)
        return {**spec.detect(pending), 'allowed': allowed, 'previous': previous, 'held_open': sorted(held),
                'assumed_now': assumed_now,
                'question': None if q is None else q.__dict__, 'metrics': spec.metrics()}, q

    @staticmethod
    def _unsettled_sensitive(spec, previous, settle) -> bool:
        """Audit 2026-11-02 finding 5: a reply that settled the question but filled nothing on a sensitive `confirm`
        field leaves it EMPTY (Spec.hear takes no default); it is held OPEN for the approval gate, not re-asked."""
        if not settle or not previous or spec is None or spec.value(previous) is not None:
            return False
        from ..intake.artifact_fields import CONDITIONAL
        f = next((x for x in list(spec.fields) + list(CONDITIONAL.values()) if x.name == previous), None)
        return bool(f is not None and f.confirm)

    @staticmethod
    def _askable(missing, closed, previous, *, unsure=False, contested=()):
        """The detector's ordered list, minus what the brief closed, under the repeat rule (Matt 2026-10-28).

        The repeat rule is state-dependent. The field asked in the previous turn is offered again ONLY when
          (a) `unsure`: the reply asks for a clarification (see _clarify) -- the field comes back ONCE, explained,
              and first; or
          (b) the answer contradicts a value the customer confirmed (`contested`): it may be asked back.
        Clarifications (_clarify, owner + Matt 2026-10-28):
          * "לא הבנתי" / "what?" / "why?"  -> once more, explained; a second "not understood" moves on (the default,
            shown as an assumption -- or, with no valid default, the field is held OPEN);
          * "לא יודע" / "not sure"          -> never repeated: the field's default, written and shown as an assumption;
          * no valid default (a sensitive `confirm` field: privacy, data, who may see it) -> one explained repeat;
            if still unsettled the field is held OPEN (brief.open_material, so the approval gate sees it) and is not
            asked again by itself -- an open field, never a loop.
        Any other reply settles it -- a stated value, "you decide", or words that fill nothing (Spec.hear then
        records the field's default as an assumption the customer can change) -- so the same question never comes
        back by itself."""
        repeat_ok = unsure or previous in set(contested or ())
        allowed = [n for n in missing if n not in closed and (n != previous or repeat_ok)]
        if unsure and previous in allowed:
            allowed.remove(previous)
            allowed.insert(0, previous)
        return allowed

    @staticmethod
    def _clarify(spec, previous, said, typed):
        """(settle, explain again, hold open, assume the default) for a reply to the field just asked. See _askable."""
        from ..intake.artifact_fields import CONDITIONAL
        text = (said or '').strip().lower()
        kind = None
        if typed and previous and spec is not None:
            if re.search(_NOT_UNDERSTOOD_RX, text, re.I):
                kind = 'not_understood'
            elif re.search(_DONT_KNOW_RX, text, re.I):
                kind = 'dont_know'
        if kind is None:
            return True, False, False, False
        f = next((x for x in list(spec.fields) + list(CONDITIONAL.values()) if x.name == previous), None)
        no_default = f is None or f.confirm                  # sensitive: never silently assumed
        last = spec.log[-1] if spec.log else None
        explained = last is not None and last.field == previous and last.mode in ('explain', 'short')
        if kind == 'dont_know' and not no_default:
            return True, False, False, True                  # the default, shown; never repeated
        if not explained:
            return False, True, False, False                 # once more, explained
        if no_default:
            return False, False, True, False                 # held open: not asked again by itself
        return True, False, False, True                      # explained already: move on with the default, shown

    @staticmethod
    def _family_for(spec, said, typed):
        """The product family comes from what the customer TYPED. A button label never changes it (the label of
        content_only=yes, "...בלי שמירת נתונים", reads as another family and used to wipe the whole spec)."""
        from ..intake.families import classify_family, named_family
        from ..intake.gaps import Spec
        kind = named_family(said) if typed else None
        if spec is None:
            return Spec(kind or (classify_family(said) if typed else 'website'), [])
        if kind is not None and kind != spec.kind:      # the customer typed a different product: start over
            return Spec(kind, [])
        return spec

    def _replayed_spec(self, project_id):
        """(spec, the field asked in the last assistant turn, fields held open) rebuilt from the store: every customer turn before
        this one is heard again (buttons with their stored answers, typed text with the deterministic interpreter)
        and every question the assistant asked is logged again from its stored `asked`. (None, None) when there is
        no history yet. Nothing is kept in this process."""
        from ..intake.artifact_fields import CONDITIONAL
        from ..intake.gaps import LogEntry, language_of
        try:
            history = list(self.store.messages_for(project_id, limit=200))
        except Exception:
            return None, None, set()
        if history and history[-1].get('role') == 'customer':
            history = history[:-1]                            # this turn was stored before routing
        spec, previous, held = None, None, set()
        for m in history:
            meta = m.get('interpretation') or {}
            if m.get('role') == 'customer' and meta.get('label'):
                continue                                      # warehouse 128: a platform label, not the customer's words
            if m.get('role') == 'customer':
                text = m.get('content') or ''
                lang = 'he' if language_of(text) == 'he' else 'en'
                answers = meta.get('answers') if isinstance(meta.get('answers'), dict) else None
                typed_text = '' if answers else text
                props = DeterministicInterpreter().interpret(typed_text, None).proposals if typed_text else ()
                said, props, typed = self._heard(typed_text, answers, props, lang)
                said = said or text
                spec = self._family_for(spec, said, typed)
                settle, _, hold, _ = self._clarify(spec, previous, said, typed)   # the same rule as the live turn
                spec.hear(said, props, settle=settle)
                if hold or self._unsettled_sensitive(spec, previous, settle):
                    held.add(previous)
                self._delegated_defaults(spec, previous, held, said, typed)
                held = {h for h in held if spec.value(h) is None}
            elif m.get('role') == 'assistant':
                asked = list(meta.get('asked') or [])
                previous = meta.get('gap_field') or (asked[0] if asked else None)
                if spec is not None and previous is not None:
                    names = {f.name for f in spec.fields} | set(CONDITIONAL)
                    if previous in names:
                        spec.log.append(LogEntry(len(spec.ledger.messages), previous,
                                                 language_of(' '.join(spec.ledger.messages[-2:])), 'replay',
                                                 spec.fingerprint(), 'explain' if meta.get('explained') else 'ask'))
        return spec, previous, held

    @staticmethod
    def _delegated_defaults(spec, previous, held, said, typed, brief=None):
        """Explicit delegation settles only the asked/held fields, visibly and with provenance.
        Uncertainty alone is not delegation; confirmed requirements are never replaced.
        The same operation is replayed from the durable customer message."""
        from ..intake.gaps import language_of
        from ..intake.artifact_fields import CONDITIONAL
        from ..intake.sources import Requirement, Span, ASSUMED, STATED
        # A mention inside a refusal or a quoted question is not permission.
        explicit = re.fullmatch(
            r'\s*(?:בבקשה\s+|please\s+)?(?:תחליט(?: אתה|י)?|תבחר אתה|תבחרי את|לא משנה לי|'
            r'you decide|your call|up to you|قرر|اختر أنت|اختر انت|لا يهمني)'
            r'(?:\s+(?:בבקשה|please))?\s*[.!؟?]*\s*', said or '', re.I)
        if spec is None or not typed or not explicit:
            return {}
        fields = {f.name: f for f in list(spec.fields) + list(CONDITIONAL.values())}
        defaults = {}
        for name in sorted(set(held) | ({previous} if previous else set())):
            f, q = fields.get(name), d.BY_ID.get(name)
            cur = spec.ledger.current(name)
            confirmed = (brief.fields.get(name) or {}).get('source') in intake_agent.CONFIRMED_SOURCES if brief else False
            if f is None or q is None or confirmed or (cur is not None and cur.status == STATED):
                continue
            value = language_of(' '.join(spec.ledger.messages)) if name == 'languages' else f.default
            if q.kind != 'text' and value not in {o.value for o in q.options}:
                continue
            spec.ledger.add(Requirement(name, value, ASSUMED,
                Span(len(spec.ledger.messages) - 1, 0, len(said), said), why='delegated'))
            defaults[name] = value
        return defaults

    @staticmethod
    def _finding_message(f, lang, T):
        if lang == 'he' and f['item'].startswith('sign-in'):
            return 'התחברות והרשאות באתר שייבנה עדיין אינן זמינות. אפשר לערוך את דרישת ההתחברות או להשאיר אותה להמשך'
        if lang == 'he' and f['item'].startswith('integration: '):
            # 2026-11-09: the customer saw "integration: payments חלופה: build without payments now ..." in English.
            kind = f['item'].split(': ', 1)[1]
            name = _INTEGRATION_HE.get(kind, kind)
            alt = _ALT_HE.get(kind) or 'לבנות עכשיו בלי החיבור הזה ולהוסיף אותו כשיהיה זמין'
            return f'חיבור ל{name} עדיין לא זמין' + T['alt'].format(x=alt)
        return f['item'] + (T['alt'].format(x=f['alternative']) if f.get('alternative') else '')

    _last_reply_was_why = False

    def _prev_ready(self, project_id) -> bool:
        """The previous assistant turn already said the plan is ready (do not repeat the same sentence)."""
        try:
            prev = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
        except Exception:
            return False
        return bool(prev) and any(a.get('type') == 'show_plan' for a in ((prev[-1].get('interpretation') or {}).get('actions') or []))

    def _repeats(self, project_id, asked) -> bool:
        """The same open question was already the subject of the previous answer."""
        try:
            prev = [m for m in self.store.messages_for(project_id, limit=6) if m.get('role') == 'assistant']
        except Exception:
            return False
        if not prev:
            return False
        last = prev[-1].get('interpretation') or {}
        self._last_reply_was_why = bool(last.get('explained'))
        return bool(last.get('asked')) and last.get('asked') == [q.id for q in asked]

    def _ask_line(self, res, row, lang, T, *, unsure: bool) -> list[str]:
        """One short line per turn: verify a pre-selected value, explain why on
        "I don't know"/repeats, otherwise just ask. Never the same sentence twice."""
        q = res.asked[0]
        he = lang == 'he'
        if unsure and self._last_reply_was_why:
            opts = ' / '.join(o.he if he else o.en for o in q.options[:4])
            return [T['options'].format(q=_short(q.field, lang) + ' —', opts=opts) if opts else T['ask_one']]
        if unsure:
            out = [T['why'].format(why=(q.why_he if he else q.why_en).rstrip('.') + '.')]
            rec = q.recommended if q.recommended and q.recommended != '__from_request__' else None
            out.append(T['unsure'].format(rec=d._label(q, rec, lang)) if rec and q.delegable else
                       (T['unsure_norec'] if q.delegable else ''))
            return [x for x in out if x]
        # Michael 2026-11-13: the card (pre-selected from the request) asks; the text does not repeat a guessed value
        # as "I understood: X. right?" -- only confirmed facts are restated
        if res.contradictions or q.id == 'access_scope':
            return [T['decide']]
        return [T['ask_one'] if len(res.asked) == 1 else T['ask'] + ':']

    def _answer(self, intent, row, plan, ctx, message, T, lang) -> str:
        if intent == 'status':
            b = ctx.get('latest_build')
            if not b:
                return T['status_none']
            c = ctx.get('task_counts') or {}
            return T['status'].format(status=b.get('status'), phase=f' ({b["phase"]})' if b.get('phase') else '',
                                      done=c.get('SUCCEEDED', 0), running=c.get('RUNNING', 0),
                                      pending=c.get('PENDING', 0) + c.get('READY', 0), failed=c.get('FAILED', 0) + c.get('BLOCKED', 0))
        if row is None:
            return T['nothing']
        if intent == 'missing':
            # C6: what is missing is what the detector still asks (then the catalog's fallback), not the catalog list
            pend = (d.must_ask(row.brief) if row.brief.detector else d.pending(row.brief))
            names = [(d.BY_ID[f].he if lang == 'he' else d.BY_ID[f].en) if f in d.BY_ID else f
                     for f in (row.brief.open_material if row.brief.detector else ())]
            names += [(q.he if lang == 'he' else q.en) for q in pend if q.field not in row.brief.open_material]
            if not names and not d.contradictions(row.brief):
                return T['missing_none']
            return T['missing'] + ' ' + '; '.join(names[:4])
        if intent == 'recommend':
            assumed = [(k, f['value']) for k, f in row.brief.fields.items() if f.get('source') in ('delegated', 'default')
                       and d.BY_ID.get(k) and d.BY_ID[k].kind == 'choice']
            return T['recommend'] + ' ' + '; '.join(_label(k, v, lang) for k, v in assumed[:8])
        if intent == 'cost':
            if not plan or not row.complete:               # before gate 1 the range is said, never hidden
                from ..intake import approval_flow as AF
                lo, hi = AF.cost_range(row.brief, self.plan_credits)
                return AF.range_line(lang, lo, hi) + ('' if lo == hi else ' ' + T['cost_unknown'])
            return T['cost'].format(credits=self.credits if self.credits is not None else '—',
                                    cap=plan['budget']['graph_authorized_usd'])
        if intent == 'feasibility':
            return self._feasibility_answer(message, row, T)
        if intent == 'approve':
            if plan and plan.get('executable') and row.complete:
                return T['approve']
            reasons = [f['item'] for f in ((plan or {}).get('feasibility') or self._feasibility(row)).get('findings', [])
                       if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]
            pend = [(q.he if lang == 'he' else q.en) for q in d.pending(row.brief)]
            return T['approve_not_ready'] + ' ' + '; '.join((pend + reasons)[:4] or ['—'])
        if intent == 'modify':
            return T['modify']
        return T['nothing']

    def _feasibility_answer(self, message, row, T) -> str:
        """Answers "can we add X?" from the registries, never from a model."""
        import dataclasses
        from ..product_architect import strip_whatsapp_links
        message = strip_whatsapp_links(message)          # a WhatsApp link is a hyperlink, not an SMS capability
        contract = C.from_brief(row.brief)
        out = []
        for name, rx in _FEAS_KEYS:
            if not re.search(rx, message, re.I):
                continue
            probe = contract
            if name == 'sign-in':
                probe = dataclasses.replace(contract, authentication_requirements={'mode': 'simple', 'source': 'probe'})
            elif name in ('payments', 'email', 'sms'):
                probe = dataclasses.replace(contract, integrations=[{'kind': name, 'detected_from': 'question', 'status': 'probe'}])
            elif name == 'mobile app':
                probe = dataclasses.replace(contract, product_family='mobile_app')
            res = F.assess(probe)
            hit = [f for f in res.findings if name.split()[0] in f.item or (name == 'mobile app' and 'family' in f.item)
                   or (name == 'images' and False)]
            if name == 'publishing':
                hit = [f for f in res.findings if f.item == 'publishing']
            if name == 'images':
                from ..planning import registry_view as R
                st = R.agent_status('image_agent')
                hit = [] if st in R.VERIFIED else [F.Finding('images', F.BLOCKED, f'image generation is {st}', 'upload your own images')]
            if hit and hit[0].outcome in (F.BLOCKED, F.UNSUPPORTED, F.WITH_CONSTRAINTS):
                f = hit[0]
                # Customer wording; the registry status stays visible for the record.
                he = T is _TXT['he']
                cap = _CAP_HE.get(name, name) if he else name
                reason = (_REASON_HE.get(f.outcome, f.reason) + f' ({f.reason})') if he else f.reason
                alt = _ALT_HE.get(name, f.alternative) if he else f.alternative
                out.append(T['feas_no'].format(cap=cap, reason=reason, alt=T['alt'].format(x=alt) if alt else ''))
            else:
                out.append(T['feas_yes'].format(cap=_CAP_HE.get(name, name) if T is _TXT['he'] else name))
        return ' '.join(out) or T['nothing']

"""Why a build cannot start -- ONE reason from a CLOSED list, said the same way by the banner and the chat (79).

2026-11-11: a real customer saw the banner "לא ניתן להתחיל בבנייה כרגע" while the chat told him "התוכנית מוכנה,
אשרו את התקציב"; he asked "מה חוסם?" and neither could answer. Now `plan.can_build == False` always carries
`blocked_reason` = {code, family, message, next}, chosen by `primary_blocker` from the preview's own blockers, and the
chat reads the same object before it says "ready". If the two would disagree, the banner wins (the admission gate is
what actually starts or refuses a build).

Three families, each with its own wording and next step:
  requirements   the contract is not READY -- a question is still open
  gate           the approval gate refused (spec not approved, plan not verified, brief changed, unsupported need)
  quote          price, plan allowance or infrastructure (no quote, plan does not cover it, backend not configured)
"""
from __future__ import annotations

# code -> (family, he, en, next_he, next_en). Every code a preview can carry MUST be here: a test enumerates the codes
# emitted by creator_plan and the execution-plan gate and fails on any that is missing.
REASONS: dict[str, tuple[str, str, str, str, str]] = {
    'requirements_open': ('requirements',
                          'יש שאלה פתוחה על הבקשה, ולכן אי אפשר עדיין לבנות.',
                          'A question about the request is still open, so the build cannot start yet.',
                          'ענו על השאלה בשיחה.', 'Answer the question in the chat.'),
    'spec_not_approved': ('gate', 'המפרט עוד לא אושר.', 'The spec has not been approved yet.',
                          'אשרו את המפרט בשיחה.', 'Approve the spec in the chat.'),
    'plan_not_verified': ('gate', 'התוכנית עוד לא נבדקה מול המפרט.', 'The plan has not been checked against the spec yet.',
                          'אשרו את המפרט ונכין תוכנית בדוקה.', 'Approve the spec and a checked plan is made.'),
    'brief_stale': ('gate', 'הבקשה השתנתה מאז שאושרה.', 'The request changed after it was approved.',
                    'אשרו את המפרט הנוכחי.', 'Approve the current spec.'),
    'requirements_invalid': ('gate', 'יש בבקשה דרישה שלא ניתן לבנות כפי שהיא.',
                             'The request has a requirement that cannot be built as written.',
                             'ערכו את הדרישה שסומנה.', 'Edit the marked requirement.'),
    'capability_not_feasible': ('gate', 'יש בבקשה יכולת שעדיין לא זמינה.', 'The request needs a capability that is not available yet.',
                                'ערכו את הבקשה בלי היכולת הזו, או המתינו לה.', 'Edit the request without it, or wait for it.'),
    'approval_state_unavailable': ('gate', 'אי אפשר לבדוק כרגע את אישור המפרט.', 'The spec approval cannot be checked right now.',
                                   'נסו שוב בעוד כמה דקות.', 'Try again in a few minutes.'),
    'cost_quote_unknown': ('quote', 'לחלק מהדרישות אין עדיין מחיר.', 'Part of the request has no price yet.',
                           'ערכו את הבקשה בלי הדרישה שסומנה.', 'Edit the request without the marked requirement.'),
    'cost_quote_unavailable': ('quote', 'לא התקבלה הצעת מחיר לבנייה.', 'No price was returned for this build.',
                               'נסו שוב בעוד כמה דקות.', 'Try again in a few minutes.'),
    'plan_cannot_authorize_cost': ('quote', 'המסלול שלך לא מכסה את הבנייה הזו.', 'Your plan does not cover this build.',
                                   'שדרגו את המסלול, או צמצמו את הבקשה.', 'Upgrade the plan, or make the request smaller.'),
    'qa_budget_denied': ('quote', 'תקציב בדיקות הפיתוח לא מאפשר את הבנייה הזו.', 'The development-test budget does not allow this build.',
                         'בדקו את יתרת תקציב הבדיקות.', 'Check the test budget balance.'),
    'durable_backend_not_configured': ('quote', 'השרת הזה לא מוגדר לבנייה.', 'This server is not configured to build.',
                                       'פנו למפעיל השרת.', 'Contact the server operator.'),
    'infrastructure': ('quote', 'תשתית שהאפליקציה צריכה לא מוכנה.', 'Infrastructure the app needs is not ready.',
                       'פנו למפעיל השרת.', 'Contact the server operator.'),
    'image_provider': ('quote', 'יצירת אייקון ותמונות לא מוגדרת.', 'Icon and image generation is not configured.',
                       'פנו למפעיל השרת.', 'Contact the server operator.'),
}
# Dynamic codes from creator_plan: "infrastructure_<kind>_<readiness>", "image_provider_<status>".
_PREFIXES = ('infrastructure_', 'image_provider_')
# The subscription's own refusal reasons (subscription_store.authorize), said precisely instead of "not covered".
PLAN_REASONS = {
    'cost class not included in plan': ('המסלול שלך לא כולל בנייה בגודל הזה.', 'Your plan does not include a build of this size.'),
    'monthly credits exhausted': ('הקרדיטים החודשיים נגמרו.', 'The monthly credits are used up.'),
    'paid-provider budget exhausted': ('תקציב הבנייה של המסלול לחודש הזה נגמר.', "This month's build budget on your plan is used up."),
}
_ORDER = {'requirements': 0, 'gate': 1, 'quote': 2}

# 77: what the customer reads for an unpriced capability or infrastructure kind -- never the internal key.
NAMES: dict[str, tuple[str, str]] = {
    'integration.payment': ('תשלום באתר', 'online payment'),
    'integration.messaging': ('שליחת הודעות', 'sending messages'),
    'integration.email': ('שליחת מיילים', 'sending email'),
    'integration.maps': ('מפה אינטראקטיבית', 'an interactive map'),
    'integration.webhook': ('חיבור למערכת חיצונית (webhook)', 'a webhook to another system'),
    'integration.oauth': ('התחברות עם חשבון חיצוני', 'sign-in with an outside account'),
    'integration.analytics': ('מדידת תנועה', 'analytics'),
    'integration.storage': ('אחסון קבצים', 'file storage'),
    'integration.database': ('חיבור למסד נתונים חיצוני', 'an outside database'),
    'integration.source_control': ('חיבור למאגר קוד', 'a source-control connection'),
    'media.video.generate': ('יצירת וידאו', 'video generation'),
    'media.audio.tts': ('הקראה קולית', 'text to speech'),
    'media.audio.stt': ('זיהוי דיבור', 'speech recognition'),
    'media.audio.sfx': ('אפקטים קוליים', 'sound effects'),
    'media.audio.music': ('יצירת מוזיקה', 'music generation'),
    'media.audio.realtime_voice': ('שיחה קולית', 'live voice'),
    'ai.agent.tools': ('סוכן AI', 'an AI agent'),
    'ai.agent.memory': ('זיכרון לסוכן AI', 'AI agent memory'),
    'ai.agent.eval': ('בדיקות לסוכן AI', 'AI agent evaluation'),
    'target.agent': ('סוכן AI', 'an AI agent'),
    'target.mobile': ('אפליקציה לטלפון', 'a phone app'),
    'target.automation': ('אוטומציה', 'automation'),
    'database': ('מסד נתונים מנוהל', 'a managed database'),
    'auth_session': ('התחברות', 'sign-in'),
    'object_storage': ('אחסון קבצים', 'file storage'),
    'scheduled_http': ('משימות מתוזמנות', 'scheduled jobs'),
    'outbound': ('שליחה החוצה (מייל / הודעות)', 'outbound email or messages'),
}


def display_name(key: str, lang: str = 'he') -> str:
    he, en = NAMES.get(key, ('יכולת נוספת', 'an extra capability'))
    return he if lang == 'he' else en


def excludable(key: str) -> bool:
    """A capability the customer may choose to build without (77). Infrastructure kinds and the build floor are not."""
    return key.startswith(('integration.', 'media.', 'ai.agent.')) or key in ('target.agent', 'target.mobile',
                                                                              'target.automation')


def reason_key(code: str) -> str | None:
    if code in REASONS:
        return code
    for prefix in _PREFIXES:
        if code.startswith(prefix):
            return prefix[:-1]
    return None


def primary_blocker(preview: dict, lang: str = 'he') -> dict | None:
    """The ONE reason a build cannot start, or None when it can. Precedence: requirements, then the gate, then price."""
    if preview.get('can_build'):
        return None
    candidates: list[tuple[int, int, str, dict]] = []
    if preview.get('status') not in (None, 'READY'):
        candidates.append((0, 0, 'requirements_open', {}))
    for i, b in enumerate(preview.get('blockers') or []):
        key = reason_key(str(b.get('code') or ''))
        if key is None:
            key = 'cost_quote_unavailable'           # an unknown code is never shown raw; the closed list is the rule
        candidates.append((_ORDER[REASONS[key][0]], i + 1, key, b))
    if not candidates:
        candidates.append((2, 0, 'cost_quote_unavailable', {}))
    _, _, key, b = min(candidates)
    family, he, en, next_he, next_en = REASONS[key]
    message = he if lang == 'he' else en
    detail = str(b.get('detail') or '')
    if key == 'plan_cannot_authorize_cost' and detail in PLAN_REASONS:
        message = PLAN_REASONS[detail][0 if lang == 'he' else 1]
    if key == 'cost_quote_unknown' and b.get('capability_keys'):
        message += ' (' + ', '.join(dict.fromkeys(display_name(k, lang) for k in b['capability_keys'])) + ')'
    if key == 'requirements_open':
        qs = [q.get('question') for q in preview.get('clarification_questions') or [] if q.get('question')]
        if qs:
            message += ' ' + qs[0]
    return {'code': str(b.get('code') or key), 'reason': key, 'family': family, 'message': message,
            'next': next_he if lang == 'he' else next_en}

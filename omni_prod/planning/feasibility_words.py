"""The findings of the feasibility gate, in the customer's words, with the next action (warehouse 132, the owner 2026-11-22).

Root cause (found 2026-11-27 in the conversation route): a finding of `feasibility.assess` is {item, outcome, reason,
alternative} -- the item and the reason are the platform's own English ("product family mobile_app", "code-writing model",
"verification step status BLOCKED"). Four places showed it to a customer, each deriving the words on its own, and each
fell back to the raw item for every language it had no table for: `ConversationSupervisor._finding_message` (a Hebrew
sentence for two items, the raw item for every other item and for every Arabic and English customer), the "cannot be
approved yet" reply (the raw items, joined), the answer to "can you add X?" (the raw reason in English) and the plan tab's
`findingLabel` (the raw item in English and Arabic). Gate 1's blocked reply therefore read like a log line, with no next
action.

One table now says each finding once, in Hebrew, Arabic and English: WHAT is missing, WHY it matters to the customer, and
NEXT, the one thing to do, in the conversation's own terms (write to me here, press the edit button, nothing to do).

Keys, most precise first:
  <item>                  'code-writing model', 'publishing', ... (feasibility.CORE_CHECKS and the fixed items)
  product family          'product family <family>' (the family is the platform's name and is never shown)
  sign-in                 'sign-in (<mode>)'
  integration:<kind>      'integration: <kind>' (feasibility.INTEGRATION_AGENT keys)
  assignment              'assignment: <task id>' (architect.plan: a task nobody can run)
  images                  the supervisor's own probe of image generation

tests/test_feasibility_words.py reads every `Finding(` of the code, every check of CORE_CHECKS and every integration kind,
and fails for one with no words, for words with no next action, for a platform word (customer_words.machine_terms) and for
the wrong script in a language. A finding that reaches `say` with no words raises NoWords -- never a guess; the callers log
it as an error and say the general sentence (`GENERAL`), which names no cause and still gives a next action.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

LANGS = ('he', 'ar', 'en')
MAX_SHOWN = 3                          # more findings than this are counted, not listed
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class Entry:
    he: tuple[str, str, str]           # (what, why, next)
    ar: tuple[str, str, str]
    en: tuple[str, str, str]


class NoWords(LookupError):
    """A finding with no customer words: raised, never shown raw and never guessed."""


_OURS = {                              # "this is on our side": the one next action of a gate we could not run
    'he': 'זה אצלנו, לא אצלכם. נסו שוב בעוד כמה דקות',
    'ar': 'هذا من جهتنا وليس من جهتكم. حاولوا مرة أخرى بعد بضع دقائق',
    'en': 'This is on our side, not yours. Try again in a few minutes',
}
_CHAT = {                              # "write it to me here"
    'he': 'כתבו לי כאן', 'ar': 'اكتبوا لي هنا', 'en': 'Write to me here'}


def _integration(name_he: str, name_ar: str, name_en: str) -> Entry:
    return Entry(
        (f'החיבור ל{name_he} עדיין לא זמין', 'אנשים לא יוכלו להשתמש בזה באתר',
         'כתבו לי כאן לבנות עכשיו בלי זה ולהוסיף את זה כשיהיה זמין'),
        (f'الربط مع {name_ar} غير متاح بعد', 'لن يتمكن الناس من استخدام ذلك في الموقع',
         'اكتبوا لي هنا أن نبني الآن بدون ذلك ونضيفه عندما يتوفر'),
        (f'The connection to {name_en} is not available yet', 'people will not be able to use it on the site',
         'Write to me here to build without it now and add it when it is available'))


_CHECK = Entry(                        # a verification step that is not proven end to end (a CORE_CHECKS item)
    ('אחד משלבי הבדיקה של האתר עוד לא נבדק אצלנו עד הסוף', 'אנחנו לא מוסרים אתר שלא בדקנו עד הסוף',
     'אפשר להמשיך ולאשר. אם הבנייה תיעצר, נגיד לכם בדיוק מה קרה ומה לעשות'),
    ('إحدى مراحل فحص الموقع لم تُختبر عندنا حتى النهاية', 'نحن لا نسلّم موقعا لم نفحصه حتى النهاية',
     'يمكنكم المتابعة والموافقة. إذا توقف البناء سنخبركم بالضبط بما حدث وبما يجب فعله'),
    ('One of the checks of the site has not been proven all the way on our side', 'we do not hand over a site we have not finished checking',
     'You can go on and approve. If the build stops, we will tell you exactly what happened and what to do'))
_GENERAL = Entry(
    ('יש משהו בבקשה שאי אפשר לבנות כרגע', 'לכן הבנייה לא יכולה להתחיל',
     f'{_CHAT["he"]} מה חשוב לכם, ונחפש דרך אחרת'),
    ('هناك أمر في الطلب لا يمكن بناؤه حاليا', 'ولذلك لا يمكن أن يبدأ البناء',
     f'{_CHAT["ar"]} ما الأهم بالنسبة لكم وسنبحث عن طريقة أخرى'),
    ('Something in the request cannot be built right now', 'so the build cannot start',
     f'{_CHAT["en"]} what matters most to you and we will look for another way'))
GENERAL = _GENERAL

WORDS: dict[str, Entry] = {
    'unresolved requirement': Entry(
        ('יש בבקשה פרט שעדיין לא ברור לי', 'בלי להבין אותו אני עלול לבנות משהו אחר ממה שרציתם',
         'ענו כאן בצ׳אט על השאלה ששאלתי, ואמשיך משם'),
        ('هناك تفصيل في الطلب لم يتضح لي بعد', 'بدون فهمه قد أبني شيئا مختلفا عمّا أردتموه',
         'أجيبوا هنا في المحادثة عن السؤال الذي طرحته وسأكمل من هناك'),
        ('A detail in the request is still unclear to me', 'without it I could build something different from what you wanted',
         'Answer my question here in the chat and I will go on from there')),
    'product family': Entry(
        ('סוג המוצר שביקשתם עדיין לא נבנה אצלנו', 'בשלב הזה אנחנו בונים אתרים ואפליקציות שנפתחים בדפדפן',
         'כתבו לי כאן שתרצו גרסה שנפתחת בדפדפן במחשב ובנייד, ונבנה אותה'),
        ('نوع المنتج الذي طلبتموه لا نبنيه بعد', 'في هذه المرحلة نبني مواقع وتطبيقات تُفتح في المتصفح',
         'اكتبوا لي هنا أنكم تريدون نسخة تُفتح في المتصفح على الحاسوب والهاتف وسنبنيها'),
        ('The kind of product you asked for is not something we build yet', 'for now we build sites and apps that open in a browser',
         'Write to me here that you want a version that opens in a browser on a computer and a phone, and we will build it')),
    'sign-in': Entry(
        ('התחברות והרשאות באתר שייבנה עדיין אינן זמינות', 'מי שיפתח את האתר לא יוכל להתחבר אליו',
         'כתבו לי כאן שאפשר לבנות כלי פנימי בלי התחברות, בקישור פרטי, או להשאיר את זה להמשך'),
        ('تسجيل الدخول والصلاحيات في الموقع الذي سيُبنى غير متاحَين بعد', 'من يفتح الموقع لن يتمكن من الدخول إليه',
         'اكتبوا لي هنا أنه يمكن بناء أداة داخلية بدون تسجيل دخول برابط خاص، أو ترك ذلك لوقت لاحق'),
        ('Sign-in and permissions on the site we will build are not available yet', 'people who open the site will not be able to sign in',
         'Write to me here that we can build an internal tool without sign-in behind a private link, or leave it for later')),
    'integration:payments': _integration('תשלומים וסליקה', 'المدفوعات', 'payments'),
    'integration:email': _integration('שליחת מיילים', 'إرسال البريد الإلكتروني', 'sending email'),
    'integration:sms': _integration('שליחת הודעות טקסט ווטסאפ', 'إرسال الرسائل النصية وواتساب', 'text messages and WhatsApp'),
    'integration:maps': _integration('מפות', 'الخرائط', 'maps'),
    'integration:calendar': _integration('יומן', 'التقويم', 'a calendar'),
    'integration:ai_model': _integration('בינה מלאכותית בתוך האתר', 'الذكاء الاصطناعي داخل الموقع', 'artificial intelligence inside the site'),
    'code-writing model': Entry(
        ('כרגע אין לנו דרך לבנות את האתר באיכות שאנחנו דורשים', 'ולכן הבנייה לא יכולה להתחיל',
         _OURS['he']),
        ('لا توجد لدينا حاليا طريقة لبناء الموقع بالجودة التي نشترطها', 'ولذلك لا يمكن أن يبدأ البناء',
         _OURS['ar']),
        ('Right now we have no way to build the site at the quality we require', 'so the build cannot start',
         _OURS['en'])),
    'conversation model': Entry(
        ('השיחה איתי רצה כרגע בצורה פשוטה יותר', 'אבין פחות ניסוחים חופשיים',
         'אפשר להמשיך כרגיל ולענות על השאלות במילים פשוטות'),
        ('المحادثة معي تعمل حاليا بطريقة أبسط', 'سأفهم عددا أقل من الصياغات الحرة',
         'يمكنكم المتابعة كالمعتاد والإجابة عن الأسئلة بكلمات بسيطة'),
        ('Our conversation is running in a simpler way right now', 'I will understand fewer free-form sentences',
         'You can go on as usual and answer the questions in plain words')),
    'independent model review': Entry(
        ('בדיקה נוספת של האתר על ידי מערכת שנייה עדיין לא פעילה אצלנו', 'הבדיקות האוטומטיות כן רצות לפני כל מסירה',
         'אין מה לעשות: אפשר להמשיך'),
        ('فحص إضافي للموقع بواسطة نظام ثانٍ غير مفعّل عندنا بعد', 'الفحوصات الآلية تعمل قبل كل تسليم',
         'لا يلزمكم أي إجراء: يمكنكم المتابعة'),
        ('An extra check of the site by a second system is not running on our side yet', 'the automatic checks still run before every handover',
         'There is nothing to do: you can go on')),
    'publishing': Entry(
        ('פרסום בכתובת קבועה עדיין אינו זמין', 'האתר ייפתח בתצוגה פרטית, ואפשר להוריד אותו',
         'אפשר להמשיך כך, ולפרסם כשהאפשרות תיפתח'),
        ('النشر على عنوان دائم غير متاح بعد', 'سيُفتح الموقع في معاينة خاصة ويمكن تنزيله',
         'يمكنكم المتابعة هكذا والنشر عندما يصبح الخيار متاحا'),
        ('Publishing at a permanent address is not available yet', 'the site opens in a private preview and you can download it',
         'You can go on like this and publish when the option opens')),
    'personal data without sign-in': Entry(
        ('פרטים אישיים יהיו גלויים לכל מי שיש לו את הקישור', 'בחרתם בזה במפורש',
         'אם זה לא מה שרציתם, כתבו לי כאן שצריך התחברות'),
        ('ستكون البيانات الشخصية ظاهرة لكل من لديه الرابط', 'لقد اخترتم ذلك صراحة',
         'إذا لم يكن هذا ما أردتموه فاكتبوا لي هنا أنكم تريدون تسجيل دخول'),
        ('Personal details will be visible to anyone who has the link', 'you chose this explicitly',
         'If that is not what you wanted, write to me here that sign-in is needed')),
    'registries': Entry(
        ('לא הצלחנו כרגע לבדוק מה אפשר לבנות', 'אנחנו לא מניחים שאפשר כשלא בדקנו', _OURS['he']),
        ('لم ننجح حاليا في فحص ما يمكن بناؤه', 'نحن لا نفترض أن ذلك ممكن عندما لا نفحص', _OURS['ar']),
        ('We could not check right now what can be built', 'we do not assume it can be done when we have not checked', _OURS['en'])),
    'assignment': Entry(
        ('חלק מתוכנית העבודה של האתר לא ניתן לביצוע כרגע', 'ולכן הבנייה לא תתחיל', _OURS['he']),
        ('جزء من خطة عمل الموقع لا يمكن تنفيذه حاليا', 'ولذلك لن يبدأ البناء', _OURS['ar']),
        ('Part of the work plan for the site cannot be carried out right now', 'so the build will not start', _OURS['en'])),
    'images': Entry(
        ('יצירת תמונות עדיין לא זמינה', 'לא נוכל ליצור לכם תמונות', 'אפשר להעלות כאן תמונות משלכם'),
        ('إنشاء الصور غير متاح بعد', 'لن نتمكن من إنشاء صور لكم', 'يمكنكم رفع صوركم الخاصة هنا'),
        ('Creating pictures is not available yet', 'we cannot make pictures for you', 'You can upload your own pictures here')),
}
# every item of feasibility.CORE_CHECKS says the same thing; one entry, listed by the code's own names (the test reads them)
for _name in ('code generation', 'sandbox verification', 'preview smoke', 'behavioural acceptance', 'browser check',
              'visual QA', 'release policy'):
    WORDS[_name] = _CHECK

_INTEGRATION = re.compile(r'^integration: ([a-z_]+)$')
_FAMILY = re.compile(r'^product family \S+$')
_SIGN_IN = re.compile(r'^sign-in \((?:simple|roles)\)$')
_ASSIGNMENT = re.compile(r'^assignment: \S+$')


def key_of(item: str) -> str:
    """The WORDS key of a finding's item, or NoWords. The item is the platform's name and is never shown."""
    item = str(item or '')
    m = _INTEGRATION.match(item)
    if m:
        key = f'integration:{m.group(1)}'
    elif _FAMILY.match(item):
        key = 'product family'
    elif _SIGN_IN.match(item):
        key = 'sign-in'
    elif _ASSIGNMENT.match(item):
        key = 'assignment'
    else:
        key = item
    if key not in WORDS:
        raise NoWords(f'no customer words for the feasibility finding {item!r}')
    return key


def words(item: str, lang: str) -> dict:
    """{'what', 'why', 'next'} of one finding in one language; raises NoWords (no entry) or ValueError (a language we
    have no words in, or an entry that cannot be said)."""
    if lang not in LANGS:
        raise ValueError(f'no feasibility words in {lang!r}; the languages are {LANGS}')
    return _parts(WORDS[key_of(item)], lang)


def _parts(entry: Entry, lang: str) -> dict:
    what, why, nxt = getattr(entry, lang)
    for part in (what, why, nxt):
        if not isinstance(part, str) or not part.strip():
            raise ValueError('a finding needs what, why and a next action in every language')
    return {'what': what, 'why': why, 'next': nxt}


def say(finding: dict, lang: str) -> dict:
    """One finding as the customer reads it: {'what', 'why', 'next', 'worded'}. A finding with no words is logged as an
    error and gets the general sentence (worded False): the customer is told something true and given a next action; the
    platform's own words are not."""
    try:
        return {**words(finding.get('item'), lang), 'worded': True}
    except NoWords as exc:
        _LOG.error('FEASIBILITY_FINDING_UNWORDED %s', exc)
        return {**_parts(_GENERAL, lang), 'worded': False}


def attach(findings) -> list[dict]:
    """The findings, each with `words`: {lang: {what, why, next}} for the three languages (a copy; the input is not
    changed). The workspace and the blocker list read these; nothing else of the finding is shown to a customer."""
    out = []
    for f in findings or []:
        # a graph problem is a string: a part of the work plan that nobody can run
        f = dict(f) if isinstance(f, dict) else {'item': 'assignment: graph', 'outcome': 'BLOCKED', 'reason': str(f)}
        f['words'] = {lang: {k: v for k, v in say(f, lang).items() if k != 'worded'} for lang in LANGS}
        out.append(f)
    return out


_INTRO = {'he': 'יש דרישה שאי אפשר לבנות כרגע.', 'ar': 'هناك طلب لا يمكن بناؤه حاليا.',
          'en': 'Something you asked for cannot be built right now.'}
_MORE = {'he': 'ועוד {n} כאלה.', 'ar': 'وهناك {n} أخرى مثلها.', 'en': 'And {n} more like these.'}


def unique(findings) -> list[dict]:
    """The findings that say different things: several unresolved questions are one sentence to the customer, said once."""
    seen, out = set(), []
    for f in findings or []:
        try:
            said = id(WORDS[key_of(f.get('item'))])      # seven checks that share one entry are one sentence
        except NoWords:
            said = str(f.get('item'))
        if said not in seen:
            seen.add(said)
            out.append(f)
    return out


def sentence(finding: dict, lang: str) -> str:
    """One finding in one sentence: what, why, and the next action."""
    w = say(finding, lang)
    return f'{w["what"]}: {w["why"]}. {w["next"]}.'


def reply(findings, lang: str) -> str:
    """The reply that says what blocks the build: the intro, the first MAX_SHOWN findings each with its next action, and
    the rest counted. With no finding at all it still says the general sentence, so the customer has a next action."""
    findings = unique(findings)
    if lang not in LANGS:
        raise ValueError(f'no feasibility words in {lang!r}; the languages are {LANGS}')
    if not findings:
        what, why, nxt = getattr(_GENERAL, lang)
        return f'{_INTRO[lang]} {what}: {why}. {nxt}.'
    parts = [_INTRO[lang]] + [sentence(f, lang) for f in findings[:MAX_SHOWN]]
    if len(findings) > MAX_SHOWN:
        parts.append(_MORE[lang].format(n=len(findings) - MAX_SHOWN))
    return ' '.join(parts)


# What the customer asked about, named in each language (the keys are the supervisor's _FEAS_KEYS: "can you add X?").
CAPABILITY = {
    'payments': ('תשלומים', 'المدفوعات', 'Payments'),
    'sign-in': ('התחברות משתמשים', 'تسجيل دخول المستخدمين', 'Sign-in for users'),
    'email': ('שליחת מיילים', 'إرسال البريد الإلكتروني', 'Sending email'),
    'sms': ('הודעות טקסט ווטסאפ', 'الرسائل النصية وواتساب', 'Text messages and WhatsApp'),
    'mobile app': ('אפליקציה לנייד', 'تطبيق للهاتف', 'A phone app'),
    'publishing': ('פרסום לכתובת קבועה', 'النشر على عنوان دائم', 'Publishing at a permanent address'),
    'images': ('יצירת תמונות', 'إنشاء الصور', 'Creating pictures'),
}
_YES = {'he': '{cap}: אפשר כבר עכשיו.', 'ar': '{cap}: متاح الآن.', 'en': '{cap}: available now.'}


def available(name: str, lang: str) -> str:
    """The answer to "can you add X?" when the registries say yes."""
    if lang not in LANGS:
        raise ValueError(f'no feasibility words in {lang!r}; the languages are {LANGS}')
    if name not in CAPABILITY:
        raise NoWords(f'no customer name for the capability {name!r}')
    return _YES[lang].format(cap=CAPABILITY[name][LANGS.index(lang)])

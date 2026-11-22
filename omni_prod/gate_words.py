"""Every blocking finding in the customer's words, with the next action (warehouse 132, the owner 2026-11-22).

The owner's brief (4.5): every finding in a person's language, with the next action -- "a gate that cannot say the
action does not go to production". Until now a failed build told the customer only that it failed: the reason lived
in the check's own words (acceptance ids, unit codes, English repair instructions), which no customer reads.

WORDS maps every way the platform can fail a build to one sentence per language (Hebrew, Arabic, English): WHAT is
missing or wrong, WHY it matters to the customer's business, and NEXT -- the one thing to do, named as its button is
named (build_announcement.RETRY_BUTTON / EDIT_BUTTON; in Arabic, the button under the message, because the screen has
no Arabic labels yet). Every entry has an ACTION: 'retry' (the cause is on our side, a new build can clear it) or
'edit' (only a change to the request can: a fact only the customer has, a need we cannot build).

Keys, from the most precise to the least:
  <check>:<kind>     a check with a closed list of kinds in its own code: the consistency checks (consistency_gate.
                     CHECKS), the browser kinds (browser_probe.BLOCKING), the static review findings (owners.
                     REVIEW_RULES), the window codes (window_catalog.CODES), the load and game codes (runtime_load.
                     CODES, game_runtime.CODES)
  <acceptance id>    every check id the executor chain produces (tests/test_site_content_owners.produced_ids)
  LAYER<suffix>      a post-build stage that crashed, said nothing, contradicted itself, judged nothing or could
                     not run (owners.LAYER_SUFFIXES)
  SANDBOX:<type>     the product's own acceptance criteria, failed by the sandbox build or its tests; their ids are
                     the spec's (any text), so the sandbox's own message type says what happened (failure_taxonomy)
  <prefix>           accept-, APPROVED-, window-: an id family
  needs:<fact>       a fact only the customer can give (fact_canon._NEEDS), from needs_customer_input

tests/test_gate_words.py walks every id and kind from the code and fails for one with no words, for words with no
action, for a machinery word (customer_words.machine_terms) and for English in a Hebrew or Arabic sentence. A finding
that reaches `key_of` at run time with no words raises NoWords -- never a guess; the announcement logs it as an
error and says the general sentence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .build_announcement import EDIT_BUTTON, RETRY_BUTTON

LANGS = ('he', 'ar', 'en')
ACTIONS = ('retry', 'edit')

# The next action, said once per action. Hebrew and English name the button exactly as the screen does.
NEXT = {
    'he': {'retry': 'זה אצלנו, לא אצלכם. אפשר לנסות שוב: לחצו על "' + RETRY_BUTTON['he'] + '".',
           'edit': 'כדי שנוכל לבנות, צריך לשנות את הבקשה: לחצו על "' + EDIT_BUTTON['he'] + '".'},
    'ar': {'retry': 'هذا من جهتنا وليس من جهتكم. يمكنكم المحاولة مرة أخرى بالضغط على الزر الذي تحت هذه الرسالة.',
           'edit': 'لكي نتمكن من البناء، يجب تعديل الطلب: اضغطوا على الزر الذي تحت هذه الرسالة.'},
    'en': {'retry': 'This is on our side, not yours. You can try again: press "' + RETRY_BUTTON['en'] + '".',
           'edit': 'To build it, the request has to change: press "' + EDIT_BUTTON['en'] + '".'},
}


@dataclass(frozen=True)
class Entry:
    action: str
    he: tuple[str, str]               # (what, why)
    ar: tuple[str, str]
    en: tuple[str, str]
    next: dict | None = None          # a next action of its own, per language; None = NEXT[lang][action]


class NoWords(LookupError):
    """A finding with no customer words: raised, never shown raw and never guessed."""


def _r(he, ar, en, next=None):
    return Entry('retry', he, ar, en, next)


def _e(he, ar, en, next=None):
    return Entry('edit', he, ar, en, next)


_SECRET_WHY = ('כל מי שנכנס לאתר יכול למצוא את זה ולהשתמש בזה על חשבונכם',
               'أي شخص يدخل الموقع يمكنه أن يجد ذلك ويستخدمه على حسابكم',
               'anyone who opens the site could find it and use it at your expense')
_HE_WHY = ('טעות כזו נראית לא מקצועית בעיני הלקוחות שלכם', 'خطأ كهذا يبدو غير احترافي في عيون زبائنكم',
           'a mistake like that looks unprofessional to your customers')
_RIGHTS_WHY = ('אי אפשר להראות שמותר לכם להשתמש בזה', 'لا يمكن إثبات أنه مسموح لكم استخدامه',
               'there is no way to show you are allowed to use it')
_UNCHECKED_WHY = ('אנחנו לא מוסרים אתר שלא בדקנו עד הסוף', 'نحن لا نسلّم موقعا لم نفحصه حتى النهاية',
                  'we do not hand over a site we have not finished checking')
_NOT_BUILT = _r(('האתר לא נבנה עד הסוף', 'אין עדיין אתר שאפשר לפתוח'),
                ('لم يكتمل بناء الموقع', 'لا يوجد بعد موقع يمكن فتحه'),
                ('The site did not finish building', 'there is no site to open yet'))
_PART_FAILED = _r(('חלק מהאתר לא עבד כשניסינו אותו', 'אנשים שינסו אותו ייתקעו'),
                  ('جزء من الموقع لم يعمل عندما جرّبناه', 'من يجرّبه سيتعثر'),
                  ('Part of the site did not work when we tried it', 'people who try it will get stuck'))
_NO_START_FILE = _r(('חסרה באתר הוראת ההפעלה שלו', 'בלי זה אי אפשר להפעיל אותו'),
                    ('تنقص الموقع تعليمات تشغيله', 'بدون ذلك لا يمكن تشغيله'),
                    ('The site is missing its start instructions', 'without them it cannot be started'))
_SIGN_IN = _r(('אי אפשר להתחבר לאתר בנוחות ממסך קטן', 'שדות בטופס הכניסה לא נכנסים במסך או לא אומרים מה לכתוב בהם'),
              ('لا يمكن تسجيل الدخول إلى الموقع بسهولة من شاشة صغيرة',
               'حقول نموذج الدخول لا تتسع في الشاشة أو لا تقول ماذا يُكتب فيها'),
              ('Signing in to the site is hard on a small screen',
               'the sign-in fields do not fit the screen or do not say what to write in them'))
_MISSING_FACT = (('פרט שנתתם, כמו טלפון, כתובת או שעות פתיחה, לא מופיע באתר כמו שכתבתם',
                  'אנשים לא יוכלו ליצור איתכם קשר או להגיע אליכם'),
                 ('تفصيل أعطيتموه، مثل الهاتف أو العنوان أو ساعات العمل، لا يظهر في الموقع كما كتبتموه',
                  'لن يتمكن الناس من التواصل معكم أو الوصول إليكم'),
                 ('A detail you gave, like a phone, an address or opening hours, is not on the site as you wrote it',
                  'people will not be able to contact you or find you'))

WORDS: dict[str, Entry] = {
    # ---- the skill gates (skill_units/gate.WORKER_GATES): one entry per unit, one failure code each
    'gate-G3-a11y_alt_text': _r(
        ('לתמונה באתר אין תיאור', 'בלי זה אנשים שלא רואים את המסך לא יודעים מה יש בה'),
        ('صورة في الموقع بلا وصف', 'بدون ذلك لا يعرف من لا يرى الشاشة ما فيها'),
        ('A picture on the site has no description', 'without it, people who cannot see the screen do not know what it shows')),
    'gate-G3-a11y_contrast': _r(
        ('טקסט באתר כמעט לא נראה על הרקע שלו', 'אנשים יתקשו לקרוא אותו, בעיקר בטלפון ובשמש'),
        ('نص في الموقع بالكاد يظهر على خلفيته', 'سيصعب على الناس قراءته، خاصة على الهاتف وفي الشمس'),
        ('Some text on the site is hard to see against its background',
         'people will struggle to read it, especially on a phone in the sun')),
    'gate-G3-a11y_focus': _r(
        ('מי שגולש עם המקלדת לא רואה איפה הוא נמצא בעמוד', 'בלי זה חלק מהאנשים לא יכולים להשתמש באתר'),
        ('من يتصفح بلوحة المفاتيح لا يرى أين هو في الصفحة', 'بدون ذلك لا يستطيع بعض الناس استخدام الموقع'),
        ('People who browse with a keyboard cannot see where they are on the page',
         'without it, some people cannot use the site')),
    'gate-G3-a11y_heading_order': _r(
        ('הכותרות בעמוד לא מסודרות לפי הסדר', 'מנועי חיפוש ומי שמשתמש בהקראה מבינים פחות טוב על מה העמוד'),
        ('العناوين في الصفحة ليست مرتبة', 'محركات البحث ومن يستخدم القراءة الصوتية يفهمون الصفحة بشكل أقل'),
        ('The headings on the page are out of order',
         'search engines and people using a screen reader understand the page less well')),
    'gate-G3-a11y_labels': _r(
        ('לשדה בטופס אין שם', 'מי שממלא את הטופס לא יודע מה לכתוב בו'),
        ('حقل في النموذج بلا اسم', 'من يملأ النموذج لا يعرف ماذا يكتب فيه'),
        ('A field in a form has no name', 'people filling in the form do not know what to write in it')),
    'gate-G4-perf_blocking_script': _r(
        ('העמוד מתעכב לפני שהוא מופיע על המסך', 'האתר נפתח לאט, ואנשים עוזבים לפני שהם רואים אותו'),
        ('الصفحة تتأخر قبل أن تظهر على الشاشة', 'يُفتح الموقع ببطء، ويغادر الناس قبل أن يروه'),
        ('The page is held back before it appears on the screen', 'the site opens slowly, and people leave before they see it')),
    'gate-G4-perf_font_display': _r(
        ('הטקסט באתר מוסתר עד שהגופן נטען', 'בטלפון איטי אנשים רואים עמוד ריק'),
        ('النص في الموقع مخفي حتى يتم تحميل الخط', 'على هاتف بطيء يرى الناس صفحة فارغة'),
        ('The text is hidden until its font has loaded', 'on a slow phone, people see an empty page')),
    'gate-G4-perf_font_preconnect': _r(
        ('הגופנים של האתר נטענים באיחור', 'הטקסט מופיע לאט וקופץ כשהעמוד נפתח'),
        ('خطوط الموقع تُحمَّل متأخرة', 'يظهر النص ببطء ويقفز عند فتح الصفحة'),
        ("The site's fonts load late", 'the text appears slowly and jumps while the page opens')),
    'gate-G4-perf_hero_eager': _r(
        ('התמונה הראשית נטענת אחרונה', 'החלק הראשון שאנשים רואים מופיע באיחור'),
        ('الصورة الرئيسية تُحمَّل في الأخير', 'أول ما يراه الناس يظهر متأخرا'),
        ('The main picture loads last', 'the first thing people see appears late')),
    'gate-G4-perf_inline_image_weight': _r(
        ('תמונה כבדה מדי נמצאת בתוך העמוד עצמו', 'העמוד כבד ונפתח לאט, בעיקר בטלפון'),
        ('صورة ثقيلة جدا موجودة داخل الصفحة نفسها', 'الصفحة ثقيلة وتُفتح ببطء، خاصة على الهاتف'),
        ('A very heavy picture is packed inside the page itself', 'the page is heavy and opens slowly, especially on a phone')),
    'gate-G4-perf_lazy_images': _r(
        ('כל התמונות נטענות מיד, גם אלה שלמטה', 'העמוד נפתח לאט ומבזבז חבילת גלישה'),
        ('كل الصور تُحمَّل فورا، حتى التي في الأسفل', 'تُفتح الصفحة ببطء وتستهلك باقة الإنترنت'),
        ('Every picture loads at once, even the ones further down', 'the page opens slowly and uses up mobile data')),
    'gate-G5-rights_font_source': _r(
        ('באתר יש גופן שלא ידוע מאיפה הוא בא', _RIGHTS_WHY[0]),
        ('في الموقع خط لا يُعرف مصدره', _RIGHTS_WHY[1]),
        ('The site uses a font from an unknown source', _RIGHTS_WHY[2])),
    'gate-G5-rights_image_source': _r(
        ('באתר יש תמונה שלא ידוע מאיפה היא באה', _RIGHTS_WHY[0]),
        ('في الموقع صورة لا يُعرف مصدرها', _RIGHTS_WHY[1]),
        ('The site shows a picture from an unknown source', _RIGHTS_WHY[2])),
    'gate-G5-rights_media_source': _r(
        ('באתר יש סרטון או צליל שלא ידוע מאיפה הם באים', _RIGHTS_WHY[0]),
        ('في الموقع فيديو أو صوت لا يُعرف مصدره', _RIGHTS_WHY[1]),
        ('The site has a video or a sound from an unknown source', _RIGHTS_WHY[2])),
    'gate-G6-secrets_api_keys': _r(
        ('סיסמה סודית לשירות חיצוני נשארה בתוך האתר', _SECRET_WHY[0]),
        ('كلمة سر سرية لخدمة خارجية بقيت داخل الموقع', _SECRET_WHY[1]),
        ('A secret password for an outside service was left inside the site', _SECRET_WHY[2])),
    'gate-G6-secrets_assignment': _r(
        ('סיסמה נכתבה בתוך האתר עצמו', _SECRET_WHY[0]),
        ('كلمة سر كُتبت داخل الموقع نفسه', _SECRET_WHY[1]),
        ('A password was written into the site itself', _SECRET_WHY[2])),
    'gate-G6-secrets_bearer': _r(
        ('אישור כניסה סודי נשאר בתוך האתר', _SECRET_WHY[0]),
        ('تصريح دخول سري بقي داخل الموقع', _SECRET_WHY[1]),
        ('A secret sign-in pass was left inside the site', _SECRET_WHY[2])),
    'gate-G6-secrets_db_url': _r(
        ('הסיסמה למקום שבו נשמרים הפרטים נשארה בתוך האתר', _SECRET_WHY[0]),
        ('كلمة السر للمكان الذي تُحفظ فيه التفاصيل بقيت داخل الموقع', _SECRET_WHY[1]),
        ('The password to where the details are kept was left inside the site', _SECRET_WHY[2])),
    'gate-G6-secrets_private_key': _r(
        ('מפתח הצפנה סודי נשאר בתוך האתר', _SECRET_WHY[0]),
        ('مفتاح تشفير سري بقي داخل الموقع', _SECRET_WHY[1]),
        ('A secret encryption key was left inside the site', _SECRET_WHY[2])),
    'gate-HE-he_gender': _r(
        ('בטקסט יש טעות בזכר ונקבה', _HE_WHY[0]),
        ('في النص العبري خطأ في التذكير والتأنيث', _HE_WHY[1]),
        ('The Hebrew text mixes up masculine and feminine', _HE_WHY[2])),
    'gate-HE-he_grammar': _r(
        ('בטקסט יש טעות דקדוק', _HE_WHY[0]),
        ('في النص العبري خطأ نحوي', _HE_WHY[1]),
        ('The Hebrew text has a grammar mistake', _HE_WHY[2])),
    'gate-HE-he_translationese': _r(
        ('משפט בטקסט נשמע כמו תרגום מילה במילה', 'זה נשמע זר, ולקוחות מרגישים שזה לא נכתב בשבילם'),
        ('جملة في النص العبري تبدو كترجمة حرفية', 'تبدو غريبة، ويشعر الزبائن أنها لم تُكتب لهم'),
        ('A sentence in the Hebrew text reads like a word-for-word translation',
         'it sounds foreign, and customers feel it was not written for them')),
    'gate-G10-copy_filler': _r(
        ('יש בעמוד משפט כללי שלא אומר כלום על העסק שלכם', 'משפטים כאלה גורמים לאתר להיראות כמו כל אתר אחר'),
        ('في الصفحة جملة عامة لا تقول شيئا عن عملكم', 'جمل كهذه تجعل الموقع يبدو مثل أي موقع آخر'),
        ('The page has a generic sentence that says nothing about your business',
         'sentences like that make the site look like any other site')),
    'gate-G10-copy_placeholder': _r(
        ('נשאר בעמוד טקסט זמני שהיה צריך להחליף', 'אנשים יראו את זה ויחשבו שהאתר לא גמור'),
        ('بقي في الصفحة نص مؤقت كان يجب استبداله', 'سيراه الناس ويظنون أن الموقع غير مكتمل'),
        ('Temporary text that should have been replaced was left on the page',
         'people will see it and think the site is unfinished')),
    'gate-G11-links_address': _r(
        ('הכתובת בעמוד חסרה מספר בית או עיר', 'בלי זה אנשים לא יכולים להגיע אליכם'),
        ('العنوان في الصفحة ينقصه رقم البيت أو المدينة', 'بدون ذلك لا يستطيع الناس الوصول إليكم'),
        ('The address on the page is missing a house number or a city', 'without it, people cannot find you')),
    'gate-G11-links_anchor': _r(
        ('קישור בעמוד מוביל למקום שלא קיים', 'אנשים לוחצים ושום דבר לא קורה'),
        ('رابط في الصفحة يقود إلى مكان غير موجود', 'يضغط الناس ولا يحدث شيء'),
        ('A link on the page leads nowhere', 'people tap it and nothing happens')),
    'gate-G11-links_tel': _r(
        ('מספר הטלפון בעמוד לא מחייג נכון', 'בלי זה אנשים לא יכולים להתקשר אליכם בלחיצה'),
        ('رقم الهاتف في الصفحة لا يتصل بشكل صحيح', 'بدون ذلك لا يستطيع الناس الاتصال بكم بضغطة'),
        ('The phone number on the page does not dial correctly', 'without it, people cannot call you with one tap')),
    'gate-G1-blocks_empty': _r(
        ('יש בעמוד כותרת בלי שום תוכן מתחתיה', 'זה נראה כמו אתר שלא נגמר'),
        ('في الصفحة عنوان بلا أي محتوى تحته', 'يبدو ذلك كموقع غير مكتمل'),
        ('The page has a heading with nothing under it', 'it looks like an unfinished site')),
    'gate-BRAND-brand_name': _r(
        ('שם העסק שלכם לא מופיע בעמוד', 'אנשים לא יודעים של מי האתר'),
        ('اسم عملكم لا يظهر في الصفحة', 'لا يعرف الناس لمن هذا الموقع'),
        ('Your business name is not on the page', 'people do not know whose site it is')),
    'gate-SHARE-share_meta': _r(
        ('כששולחים קישור לאתר, לא מופיעים שם ותיאור', 'בוואטסאפ ובפייסבוק הקישור נראה ריק, ופחות אנשים לוחצים עליו'),
        ('عند إرسال رابط الموقع لا يظهر اسم ولا وصف', 'في واتساب وفيسبوك يبدو الرابط فارغا، فيضغط عليه عدد أقل من الناس'),
        ('When someone shares a link to the site, no name or description shows',
         'on WhatsApp and Facebook the link looks empty, and fewer people tap it')),
    'gate-PRO-design_minimum': _r(
        ('העמוד עוד פשוט מדי בשביל עסק', 'חסרים בו חלקים, תמונה או כפתור יצירת קשר בולט, והוא לא נראה מקצועי'),
        ('الصفحة ما زالت بسيطة جدا لعمل تجاري', 'تنقصها أقسام أو صورة أو زر تواصل واضح، ولا تبدو احترافية'),
        ('The page is still too basic for a business',
         'it is missing sections, a picture or a clear contact button, and does not look professional')),
    # ---- the other gates the worker installs
    'gate-APPLE': _r(
        ('בעיצוב העמוד יש בעיה שרואים על המסך: טקסט חתוך, כפתור קטן מדי או גלילה הצידה',
         'בטלפון זה נראה שבור וקשה להשתמש בזה'),
        ('في تصميم الصفحة مشكلة ظاهرة: نص مقطوع أو زر صغير جدا أو تمرير جانبي', 'على الهاتف يبدو ذلك معطوبا ويصعب استخدامه'),
        ('The page design has a visible problem: cut-off text, a button that is too small, or sideways scrolling',
         'on a phone it looks broken and is hard to use')),
    'gate-G8-runtime-load': _r(
        ('האתר לא עמד בהרבה מבקרים בבת אחת', 'ביום עמוס אנשים יקבלו עמוד שלא נפתח'),
        ('لم يتحمل الموقع زوارا كثيرين في وقت واحد', 'في يوم مزدحم سيصل الناس إلى صفحة لا تُفتح'),
        ('The site could not take many visitors at once', 'on a busy day, people will get a page that does not open')),
    'gate-G8-runtime-load:LOAD_ERRORS': _r(
        ('כשהרבה אנשים נכנסו יחד, חלק מהם לא קיבלו את העמוד', 'ביום עמוס לקוחות יפספסו אתכם'),
        ('عندما دخل كثيرون معا، لم تصل الصفحة إلى بعضهم', 'في يوم مزدحم سيفوتكم زبائن'),
        ('When many people came in together, some of them did not get the page', 'on a busy day, customers will miss you')),
    'gate-G8-runtime-load:RUNTIME_CRASHED': _r(
        ('האתר הפסיק לעבוד כשניסינו אותו', 'אם זה יקרה כשהוא באוויר, אף אחד לא יוכל להיכנס'),
        ('توقف الموقع عن العمل عندما جرّبناه', 'إذا حدث ذلك وهو منشور، فلن يستطيع أحد الدخول'),
        ('The site stopped working while we tried it', 'if that happens while it is online, nobody can get in')),
    'gate-G8-runtime-load:LOAD_SLOW': _r(
        ('האתר נפתח לאט כשהרבה אנשים נכנסים', 'אנשים לא מחכים ועוזבים'),
        ('يُفتح الموقع ببطء عندما يدخل كثيرون', 'الناس لا ينتظرون ويغادرون'),
        ('The site opens slowly when many people come in', 'people do not wait, they leave')),
    'gate-G8-runtime-load:MEMORY_HIGH': _r(
        ('האתר צורך יותר מדי כוח כשהרבה אנשים נכנסים', 'בסוף הוא עלול להפסיק לעבוד'),
        ('يستهلك الموقع قدرة أكثر من اللازم عندما يدخل كثيرون', 'في النهاية قد يتوقف عن العمل'),
        ('The site uses too much power when many people come in', 'in the end it may stop working')),
    'gate-G8-runtime-load:LOAD_NOT_STARTED': _r(
        ('האתר לא עלה כשניסינו לפתוח אותו', 'אי אפשר להראות אותו לאנשים'),
        ('لم يعمل الموقع عندما حاولنا فتحه', 'لا يمكن عرضه على الناس'),
        ('The site did not come up when we tried to open it', 'it cannot be shown to anyone')),
    'gate-GAME-runtime': _r(
        ('המשחק לא עובד כמו שצריך', 'מי שייכנס לא יוכל לשחק'),
        ('اللعبة لا تعمل كما يجب', 'من يدخل لن يستطيع اللعب'),
        ('The game does not work as it should', 'people who open it will not be able to play')),
    'gate-GAME-runtime:GAME_NO_CANVAS': _r(
        ('המשחק לא מופיע על המסך', 'אין במה לשחק'),
        ('اللعبة لا تظهر على الشاشة', 'لا يوجد ما يُلعب به'),
        ('The game does not appear on the screen', 'there is nothing to play')),
    'gate-GAME-runtime:GAME_BLANK': _r(
        ('המסך של המשחק נשאר ריק', 'מי שנכנס רואה מסך ריק ועוזב'),
        ('تبقى شاشة اللعبة فارغة', 'من يدخل يرى شاشة فارغة ويغادر'),
        ("The game's screen stays empty", 'people see an empty screen and leave')),
    'gate-GAME-runtime:GAME_FROZEN': _r(
        ('המשחק קפוא ולא זז', 'אי אפשר לשחק בו'),
        ('اللعبة متجمدة ولا تتحرك', 'لا يمكن اللعب بها'),
        ('The game is frozen and does not move', 'it cannot be played')),
    'gate-GAME-runtime:GAME_IGNORES_INPUT': _r(
        ('המשחק לא מגיב למקשים או למגע', 'אי אפשר לשחק בו'),
        ('اللعبة لا تستجيب للأزرار أو للمس', 'لا يمكن اللعب بها'),
        ('The game does not respond to keys or touch', 'it cannot be played')),
    'gate-GAME-runtime:GAME_ERROR': _r(
        ('המשחק נתקע בגלל תקלה', 'מי שמשחק נתקע באמצע'),
        ('اللعبة تتعطل بسبب خلل', 'من يلعب يتوقف في المنتصف'),
        ('The game breaks down partway', 'players get stuck in the middle')),
    'gate-GAME-runtime:GAME_OFFSCREEN': _r(
        ('המשחק לא נכנס כולו במסך', 'בטלפון חלק מהמשחק לא נראה'),
        ('اللعبة لا تتسع كلها في الشاشة', 'على الهاتف لا يظهر جزء من اللعبة'),
        ('The game does not fit on the screen', 'on a phone, part of the game cannot be seen')),
    'gate-GAME-runtime:GAME_NOT_STARTED': _r(
        ('המשחק לא עלה כשניסינו לפתוח אותו', 'אי אפשר לשחק בו'),
        ('لم تعمل اللعبة عندما حاولنا فتحها', 'لا يمكن اللعب بها'),
        ('The game did not come up when we tried to open it', 'it cannot be played')),
    'gate-SITE_CLAIMS': _r(
        ('בעמוד נכתבה טענה כמו "הכי טוב" או "מספר 1" בלי שום עובדה מאחוריה',
         'טענה כזו פוגעת באמון, ולפעמים אסור לכתוב אותה'),
        ('كُتب في الصفحة ادعاء مثل "الأفضل" أو "رقم 1" بلا أي حقيقة تدعمه', 'ادعاء كهذا يضر بالثقة، وأحيانا يُمنع كتابته'),
        ('The page makes a claim like "the best" or "number 1" with no fact behind it',
         'a claim like that hurts trust, and sometimes it is not allowed')),
    'gate-SITE_PARITY': _r(
        ('העמוד שמוצג לאנשים שונה מהעמוד שהכנו', 'אנשים יראו משהו אחר ממה שאישרתם'),
        ('الصفحة التي تظهر للناس تختلف عن الصفحة التي أعددناها', 'سيرى الناس شيئا غير الذي وافقتم عليه'),
        ('The page people see is different from the page we prepared', 'people would see something other than what you approved')),
    'window-': _r(
        ('חלון באתר לא עובד כמו שאישרתם', 'אנשים ייתקעו בו או יפספסו אותו'),
        ('نافذة في الموقع لا تعمل كما وافقتم', 'سيتعثر الناس فيها أو تفوتهم'),
        ('A window on the site does not work the way you approved', 'people will get stuck in it or miss it')),
    'window-:WINDOW_MISSING': _r(
        ('חלון שאישרתם, כמו הודעת עוגיות או סל קניות, לא מופיע באתר', 'אנשים לא יקבלו את מה שהחלון הזה נותן'),
        ('نافذة وافقتم عليها، مثل رسالة ملفات تعريف الارتباط أو سلة المشتريات، لا تظهر في الموقع',
         'لن يحصل الناس على ما تقدمه هذه النافذة'),
        ('A window you approved, like a cookie notice or a shopping cart, is not on the site',
         'people will not get what that window gives them')),
    'window-:WINDOW_RULE': _r(
        ('חלון באתר לא נסגר כמו שצריך או לא נוח לשימוש', 'אנשים ייתקעו בו ולא יגיעו לתוכן'),
        ('نافذة في الموقع لا تُغلق كما يجب أو غير مريحة للاستخدام', 'سيتعثر الناس فيها ولن يصلوا إلى المحتوى'),
        ('A window on the site does not close properly or is awkward to use', 'people will get stuck in it and not reach the content')),
    'window-:WINDOW_ORDER': _r(
        ('החלונות באתר מופיעים בסדר הלא נכון', 'למשל שאלת הגיל צריכה להופיע לפני הודעת העוגיות'),
        ('النوافذ في الموقع تظهر بترتيب خاطئ', 'مثلا سؤال العمر يجب أن يظهر قبل رسالة ملفات تعريف الارتباط'),
        ('The windows on the site appear in the wrong order', 'for example, the age question has to come before the cookie notice')),
    'window-:WINDOW_TWO_OPEN': _r(
        ('שני חלונות נפתחים יחד כשנכנסים לאתר', 'אנשים לא יודעים במה לטפל ראשון ועוזבים'),
        ('نافذتان تُفتحان معا عند دخول الموقع', 'لا يعرف الناس بأيهما يبدؤون فيغادرون'),
        ('Two windows open together when someone comes to the site', 'people do not know which to deal with first, and leave')),
    'window-:WINDOW_REJECTED': _r(
        ('באתר יש חלון שביקשתם לא לשים', 'זה לא מה שאישרתם'),
        ('في الموقع نافذة طلبتم عدم وضعها', 'هذا ليس ما وافقتم عليه'),
        ('The site has a window you asked us to leave out', 'that is not what you approved')),
    'asset-plan': _r(
        ('תמונה באתר לא נמצאת במקום שלה', 'למשל תמונת הצוות לא נמצאת בחלק שמספר עליכם'),
        ('صورة في الموقع ليست في مكانها', 'مثلا صورة الفريق ليست في القسم الذي يعرّف بكم'),
        ('A picture on the site is not in its place', 'for example, the team photo is not in the part about you')),
    'asset-marker': _r(
        ('תמונה באתר לא נטענת ומופיעה שבורה', 'אנשים רואים ריבוע ריק במקום תמונה'),
        ('صورة في الموقع لا تُحمَّل وتظهر معطوبة', 'يرى الناس مربعا فارغا بدل الصورة'),
        ('A picture on the site does not load and shows as broken', 'people see an empty box instead of a picture')),
    'generated-image': _r(
        ('תמונה שהכנו לאתר לא מופיעה בעמוד', 'העמוד נראה ריק בלעדיה'),
        ('صورة أعددناها للموقع لا تظهر في الصفحة', 'تبدو الصفحة فارغة بدونها'),
        ('A picture we made for the site is not on the page', 'the page looks empty without it')),
    'uploaded-logo': _r(
        ('הלוגו ששלחתם לא מופיע באתר', 'אנשים לא יזהו שזה העסק שלכם'),
        ('الشعار الذي أرسلتموه لا يظهر في الموقع', 'لن يعرف الناس أن هذا عملكم'),
        ('The logo you sent is not on the site', 'people will not recognise it as your business')),
    'uploaded-main-image': _r(
        ('תמונה ששלחתם לא מופיעה באתר, או לא במקום שביקשתם', 'אנשים לא יראו את מה שרציתם להראות'),
        ('صورة أرسلتموها لا تظهر في الموقع، أو ليست في المكان الذي طلبتموه', 'لن يرى الناس ما أردتم أن تعرضوه'),
        ('A picture you sent is not on the site, or not where you asked', 'people will not see what you wanted to show')),
    # ---- what the worker's wrappers add to every spec
    'CUSTOMER-FACTS': _r(*_MISSING_FACT),
    'DESIGN-CONTRACT': _r(
        ('העיצוב יצא שונה מהסגנון שנקבע לאתר', 'האתר ייראה לא אחיד ולא מקצועי'),
        ('خرج التصميم مختلفا عن الأسلوب الذي حُدد للموقع', 'سيبدو الموقع غير متناسق وغير احترافي'),
        ('The design came out different from the style set for the site', 'the site will look uneven and unprofessional')),
    'CUSTOMER-PAGE-STRUCTURE': _r(
        ('מבנה העמוד שביקשתם לא נשמר', 'החלקים לא מופיעים בסדר שביקשתם'),
        ('لم يُحفظ ترتيب الصفحة الذي طلبتموه', 'الأقسام لا تظهر بالترتيب الذي طلبتموه'),
        ('The page layout you asked for was not kept', 'the parts do not appear in the order you asked for')),
    'PLATFORM-CHECKS': _r(
        ('האתר עוד לא עומד בכל מה שאנחנו דורשים מכל אתר', 'אנחנו לא מוסרים אתר עם בעיות שאנשים ירגישו'),
        ('الموقع لا يلبي بعد كل ما نطلبه من كل موقع', 'نحن لا نسلّم موقعا فيه مشاكل سيشعر بها الناس'),
        ('The site does not yet meet everything we require of every site',
         'we do not hand over a site with problems people will notice')),
    'accept-': _r(
        ('חלק מהאתר עוד לא עובד כמו שהבקשה אומרת', 'אנשים שינסו להשתמש בו לא יקבלו את מה שביקשתם'),
        ('جزء من الموقع لا يعمل بعد كما يقول الطلب', 'من يحاول استخدامه لن يحصل على ما طلبتموه'),
        ('Part of the site does not work yet the way the request says', 'people who try to use it will not get what you asked for')),
    'APPROVED-': _r(
        ('משהו שאישרתם שצריך לעבוד באתר עוד לא עובד', 'זה חלק ממה שסיכמנו, ואנחנו לא מוסרים בלעדיו'),
        ('شيء وافقتم على أنه يجب أن يعمل في الموقع لا يعمل بعد', 'هذا جزء مما اتفقنا عليه، ولا نسلّم بدونه'),
        ('Something you approved as working on the site does not work yet',
         'it is part of what we agreed, and we do not hand over without it')),
    'ROUND_unspecified': _r(
        ('הניסיון לבנות נעצר בלי להגיד למה', 'אנחנו עוד לא יודעים מה בדיוק לא עבד'),
        ('توقفت محاولة البناء دون أن تقول السبب', 'لا نعرف بعد ما الذي لم يعمل بالضبط'),
        ('The build attempt stopped without saying why', 'we do not know yet exactly what did not work')),
    # ---- the checks before and after the build
    'CONSISTENCY': _r(
        ('חלקים של האתר לא מתאימים זה לזה', 'האתר לא יעבוד כמו שצריך'),
        ('أجزاء من الموقع لا تتوافق مع بعضها', 'لن يعمل الموقع كما يجب'),
        ('Parts of the site do not fit together', 'the site will not work as it should')),
    'CONSISTENCY:syntax': _r(
        ('יש באתר טעות כתיבה שמונעת ממנו לעבוד', 'האתר לא ייפתח בכלל'),
        ('في الموقع خطأ كتابة يمنعه من العمل', 'لن يُفتح الموقع أبدا'),
        ('The site has a writing mistake that stops it from working', 'the site will not open at all')),
    'CONSISTENCY:imports': _r(
        ('חלק באתר מחפש רכיב שלא קיים', 'האתר לא ייפתח בכלל'),
        ('جزء من الموقع يبحث عن مكوّن غير موجود', 'لن يُفتح الموقع أبدا'),
        ('Part of the site looks for a piece that does not exist', 'the site will not open at all')),
    'CONSISTENCY:routes': _r(
        ('כפתור או טופס באתר שולח לכתובת שלא קיימת', 'אנשים ילחצו ולא יקרה כלום'),
        ('زر أو نموذج في الموقع يرسل إلى عنوان غير موجود', 'سيضغط الناس ولن يحدث شيء'),
        ('A button or a form on the site sends to an address that does not exist', 'people will tap it and nothing will happen')),
    'CONSISTENCY:static': _r(
        ('האתר מנסה לטעון תמונה או קובץ שלא קיימים', 'אנשים יראו חלקים שבורים'),
        ('الموقع يحاول تحميل صورة أو ملف غير موجود', 'سيرى الناس أجزاء معطوبة'),
        ('The site tries to load a picture or a file that does not exist', 'people will see broken parts')),
    'CONSISTENCY:manifest': _NO_START_FILE,
    'CONSISTENCY:accessibility': _r(
        ('העמוד לא מסומן נכון לשפה ולכיוון שלו, או שתמונה בו בלי תיאור',
         'הטקסט עלול להופיע הפוך, ומי שלא רואה לא ידע מה יש בתמונה'),
        ('الصفحة غير معلّمة بشكل صحيح للغتها واتجاهها، أو فيها صورة بلا وصف',
         'قد يظهر النص معكوسا، ومن لا يرى لن يعرف ما في الصورة'),
        ('The page is not marked for its language and direction, or a picture on it has no description',
         'the text may show the wrong way round, and people who cannot see will not know what the picture shows')),
    'UNSUPPORTED_DEPENDENCY': _e(
        ('הבקשה צריכה משהו שאנחנו עוד לא יודעים לבנות', 'אם נבנה בלעדיו, האתר לא יעבוד כמו שביקשתם'),
        ('الطلب يحتاج شيئا لا نعرف بناءه بعد', 'إذا بنينا بدونه، فلن يعمل الموقع كما طلبتم'),
        ('The request needs something we cannot build yet', 'built without it, the site would not work the way you asked')),
    'PREVIEW': _r(
        ('האתר לא נפתח כשניסינו להציג אותו', 'אי אפשר להראות אותו לכם או לאנשים'),
        ('لم يُفتح الموقع عندما حاولنا عرضه', 'لا يمكن عرضه عليكم ولا على الناس'),
        ('The site did not open when we tried to show it', 'it cannot be shown to you or to anyone')),
    'BEHAVIOR': _r(
        ('משהו שביקשתם לא עבד כשניסינו אותו כמו מבקר באתר', 'אנשים שינסו את אותו דבר ייתקעו'),
        ('شيء طلبتموه لم يعمل عندما جرّبناه كزائر للموقع', 'من يجرّب الشيء نفسه سيتعثر'),
        ('Something you asked for did not work when we tried it as a visitor', 'people who try the same will get stuck')),
    'BROWSER': _r(
        ('האתר לא התנהג כמו שצריך כשהשתמשנו בו כמו מבקר', 'אנשים ייתקעו באמצע'),
        ('لم يتصرف الموقع كما يجب عندما استخدمناه كزائر', 'سيتعثر الناس في المنتصف'),
        ('The site did not behave right when we used it as a visitor', 'people will get stuck partway')),
    'BROWSER:dead_form': _r(
        ('טופס באתר לא עשה כלום כשמילאנו ושלחנו אותו', 'אנשים לא יוכלו להשאיר לכם פרטים'),
        ('نموذج في الموقع لم يفعل شيئا عندما ملأناه وأرسلناه', 'لن يتمكن الناس من ترك تفاصيلهم لكم'),
        ('A form on the site did nothing when we filled it in and sent it', 'people will not be able to leave you their details')),
    'BROWSER:feedback_disappears': _r(
        ('אחרי שליחה שנייה של טופס לא הופיעה שום הודעה', 'אנשים לא יודעים אם הפרטים שלהם נשלחו'),
        ('بعد إرسال النموذج مرة ثانية لم تظهر أي رسالة', 'لا يعرف الناس إن كانت تفاصيلهم قد أُرسلت'),
        ('After a form was sent a second time, no message appeared', 'people cannot tell whether their details were sent')),
    'BROWSER:page_error': _r(
        ('העמוד נתקע בגלל תקלה כשפתחנו אותו', 'חלק מהכפתורים לא יעבדו לאנשים'),
        ('تعطلت الصفحة بسبب خلل عندما فتحناها', 'بعض الأزرار لن تعمل عند الناس'),
        ('The page broke down when we opened it', 'some buttons will not work for people')),
    'BROWSER:server_error': _r(
        ('האתר לא ענה כמו שצריך כשמילאנו בו פרטים', 'אנשים שישאירו פרטים יקבלו הודעת תקלה'),
        ('لم يستجب الموقع كما يجب عندما ملأنا فيه تفاصيل', 'من يترك تفاصيله سيتلقى رسالة خلل'),
        ('The site did not answer properly when we filled in details', 'people who leave their details will see a failure message')),
    'VISUAL': _r(
        ('העמוד נראה שבור על מסך של טלפון או מחשב', 'למשל טקסט חתוך, כפתורים זה על זה או תמונה שלא נטענת'),
        ('تبدو الصفحة معطوبة على شاشة هاتف أو حاسوب', 'مثلا نص مقطوع أو أزرار فوق بعضها أو صورة لا تُحمَّل'),
        ('The page looks broken on a phone or computer screen',
         'for example, cut-off text, buttons on top of each other, or a picture that does not load')),
    'AUTH_FORM': _SIGN_IN,
    'AUTHFORM': _SIGN_IN,
    'REVIEW': _r(
        ('בעמוד יש משהו שלא מתאים למה שביקשתם', 'אנחנו לא מוסרים אתר שאומר משהו שלא אמרתם'),
        ('في الصفحة شيء لا يطابق ما طلبتموه', 'نحن لا نسلّم موقعا يقول شيئا لم تقولوه'),
        ('Something on the page does not match what you asked for', 'we do not hand over a site that says something you did not say')),
    'REVIEW:missing_facts': _r(*_MISSING_FACT),
    'REVIEW:invented_contact': _r(
        ('בעמוד הופיעו פרטי קשר שלא נתתם', 'אנשים עלולים להתקשר למספר שהוא לא שלכם'),
        ('ظهرت في الصفحة تفاصيل تواصل لم تعطوها', 'قد يتصل الناس برقم ليس لكم'),
        ('The page shows contact details you did not give', 'people might call a number that is not yours')),
    'REVIEW:invented_hours': _r(
        ('בעמוד הופיעו שעות פתיחה שלא נתתם', 'אנשים עלולים להגיע כשאתם סגורים'),
        ('ظهرت في الصفحة ساعات عمل لم تعطوها', 'قد يأتي الناس وأنتم مغلقون'),
        ('The page shows opening hours you did not give', 'people might come when you are closed')),
    'REVIEW:contradicted_hours': _r(
        ('שעות הפתיחה בעמוד שונות ממה שכתבתם', 'אנשים עלולים להגיע כשאתם סגורים'),
        ('ساعات العمل في الصفحة تختلف عما كتبتموه', 'قد يأتي الناس وأنتم مغلقون'),
        ('The opening hours on the page differ from what you wrote', 'people might come when you are closed')),
    'REVIEW:invented_counts': _r(
        ('בעמוד הופיעו מספרים של ביקורות או דירוג שלא נתתם', 'מספרים מומצאים פוגעים באמון, ולפעמים אסור לכתוב אותם'),
        ('ظهرت في الصفحة أعداد مراجعات أو تقييم لم تعطوها', 'الأرقام المختلقة تضر بالثقة، وأحيانا يُمنع كتابتها'),
        ('The page shows review or rating numbers you did not give', 'made-up numbers hurt trust, and sometimes they are not allowed')),
    'REVIEW:invented_testimonials': _r(
        ('בעמוד הופיעו המלצות של לקוחות שלא נתתם', 'המלצות מומצאות פוגעות באמון, ולפעמים אסור לפרסם אותן'),
        ('ظهرت في الصفحة توصيات زبائن لم تعطوها', 'التوصيات المختلقة تضر بالثقة، وأحيانا يُمنع نشرها'),
        ('The page shows customer recommendations you did not give',
         'made-up recommendations hurt trust, and sometimes they are not allowed')),
    'REVIEW:placeholder': _r(
        ('נשאר בעמוד טקסט זמני', 'אנשים יחשבו שהאתר לא גמור'),
        ('بقي في الصفحة نص مؤقت', 'سيظن الناس أن الموقع غير مكتمل'),
        ('Temporary text was left on the page', 'people will think the site is unfinished')),
    'QUALITY': _r(
        ('האתר עוד לא מספיק טוב כדי שנמסור אותו לכם', 'אנחנו לא מוסרים אתר שחסרים בו חלקים חשובים'),
        ('الموقع ليس جيدا بما يكفي بعد لنسلّمه لكم', 'نحن لا نسلّم موقعا تنقصه أجزاء مهمة'),
        ('The site is not good enough yet for us to hand it over', 'we do not hand over a site that is missing important parts')),
    'DESIGN': _r(
        ('העיצוב עוד לא מספיק טוב', 'אתר שנראה חובבני מבריח לקוחות'),
        ('التصميم ليس جيدا بما يكفي بعد', 'الموقع الذي يبدو هاويا يُبعد الزبائن'),
        ('The design is not good enough yet', 'a site that looks amateurish drives customers away')),
    # ---- a post-build stage that did not judge (owners.LAYER_SUFFIXES): the check, not the site
    'LAYER_EXCEPTION': _r(
        ('לא הצלחנו לסיים לבדוק את האתר', _UNCHECKED_WHY[0]),
        ('لم نتمكن من إنهاء فحص الموقع', _UNCHECKED_WHY[1]),
        ('We could not finish checking the site', _UNCHECKED_WHY[2])),
    'LAYER_unspecified': _r(
        ('אחד הניסיונות שלנו על האתר נגמר בלי תשובה', _UNCHECKED_WHY[0]),
        ('إحدى تجاربنا على الموقع انتهت بلا جواب', _UNCHECKED_WHY[1]),
        ('One of our tries on the site ended without an answer', _UNCHECKED_WHY[2])),
    'LAYER_contradictory': _r(
        ('קיבלנו תשובות סותרות כשניסינו את האתר', _UNCHECKED_WHY[0]),
        ('حصلنا على أجوبة متناقضة عندما جرّبنا الموقع', _UNCHECKED_WHY[1]),
        ('We got answers that contradict each other when we tried the site', _UNCHECKED_WHY[2])),
    'LAYER_NO_CHECKS': _r(
        ('לא היה בעמוד שום דבר שאפשר לנסות', _UNCHECKED_WHY[0]),
        ('لم يكن في الصفحة أي شيء يمكن تجربته', _UNCHECKED_WHY[1]),
        ('There was nothing on the page we could try', _UNCHECKED_WHY[2])),
    'LAYER_UNVERIFIED': _r(
        ('לא הצלחנו לנסות את האתר כמו מבקר', _UNCHECKED_WHY[0]),
        ('لم نتمكن من تجربة الموقع كزائر', _UNCHECKED_WHY[1]),
        ('We could not try the site as a visitor', _UNCHECKED_WHY[2])),
    # ---- the product's own acceptance criteria (spec ids), by the sandbox's message type (failure_taxonomy)
    'SANDBOX:build_command_failed': _NOT_BUILT,
    'SANDBOX:remote_build_failed': _NOT_BUILT,
    'SANDBOX:verification_failed': _PART_FAILED,
    'SANDBOX:remote_verification_failed': _PART_FAILED,
    'SANDBOX:invalid_omni_project_json': _NO_START_FILE,
    'SANDBOX:no_verification_command_covers_this_acceptance_criterion': _r(
        ('לא הספקנו לנסות חלק ממה שביקשתם', 'אנחנו לא מוסרים משהו שלא ניסינו'),
        ('لم نتمكن من تجربة جزء مما طلبتموه', 'نحن لا نسلّم شيئا لم نجرّبه'),
        ('We did not get to try part of what you asked for', 'we do not hand over something we have not tried')),
    # ---- a fact only the customer can give (fact_canon._NEEDS): the owner's example, word for word
    'needs:phone': _e(
        ('חסר מספר טלפון', 'בלי זה אנשים לא יכולים להתקשר אליכם'),
        ('ينقص رقم الهاتف', 'بدون ذلك لا يستطيع الناس الاتصال بكم'),
        ('The phone number is missing', 'without it, people cannot call you'),
        next={'he': 'כתבו את המספר בבקשה: לחצו על "' + EDIT_BUTTON['he'] + '".',
              'ar': 'أضيفوا الرقم إلى الطلب بالضغط على الزر الذي تحت هذه الرسالة.',
              'en': 'Add the number to the request: press "' + EDIT_BUTTON['en'] + '".'}),
    'needs:hours': _e(
        ('חסרות שעות הפתיחה', 'בלי זה אנשים לא יודעים מתי אפשר להגיע'),
        ('تنقص ساعات العمل', 'بدون ذلك لا يعرف الناس متى يمكنهم المجيء'),
        ('The opening hours are missing', 'without them, people do not know when they can come'),
        next={'he': 'כתבו את שעות הפתיחה בבקשה: לחצו על "' + EDIT_BUTTON['he'] + '".',
              'ar': 'أضيفوا ساعات العمل إلى الطلب بالضغط على الزر الذي تحت هذه الرسالة.',
              'en': 'Add the opening hours to the request: press "' + EDIT_BUTTON['en'] + '".'}),
}

# The engine's own notes to its repairer (autonomous_core, plan_floor): no defect of the site, nothing to tell a
# customer. Each one is 'advisory' in site_content/owners.OWNER (tests/test_gate_words.py holds the two together).
NOT_A_FINDING = {
    'ALSO_FAILING': 'a summary line listing the other failures',
    'NO_PROGRESS': 'a note that a repair changed nothing',
    'TEST_EDIT_REVERTED': 'a note that a repair edit to a test was undone',
    'REPAIR_REGRESSION': 'a note that a repair made things worse',
    'REPAIR_PLAN_WEAKENED': 'a note that a repair plan dropped a requirement',
}
PREFIXES = ('accept-', 'APPROVED-', 'window-')
LAYER_SUFFIXES = ('_EXCEPTION', '_unspecified', '_contradictory', '_NO_CHECKS', '_UNVERIFIED')
# The message markers of the kinds whose code has no code token in the message. Each marker is the producer's own
# text (browser_probe.PROBE; skills_runtime / owners.REVIEW_RULES); tests/test_gate_words.py reads them there.
BROWSER_KINDS = (('dead_form', 'submitting it sent no request and changed nothing'),
                 ('feedback_disappears', 'the second successful submit showed no message'),
                 ('page_error', 'uncaught JavaScript error'),
                 ('server_error', 'server error during the browser flow'))
REVIEW_KINDS = (('missing_facts', 'facts the customer gave are missing from the page'),
                ('invented_contact', 'contact details not in the approved request (invented)'),
                ('invented_hours', 'opening hours the customer never gave (invented)'),
                ('contradicted_hours', 'opening hours contradict what the customer wrote'),
                ('invented_counts', 'review/rating counts not in the approved request'),
                ('invented_testimonials', 'testimonials with no source in the approved request'),
                ('placeholder', 'placeholder text in the product'))
_CONSISTENCY = re.compile(r'^consistency \(([a-z_]+)\):')
_CODE_COLON = re.compile(r'^([A-Z][A-Z0-9_]+):')           # runtime_load, window_catalog: "<CODE>: ..."
_CODE_PAREN = re.compile(r'^([A-Z][A-Z0-9_]+) \(')         # game_runtime: "<CODE> (<viewport>): ..."
_MISSING = re.compile(r'missing from the customer: ([a-z_, ]+)')
MAX_SHOWN = 3


def _kind(aid: str, msg: str) -> tuple[str, str] | None:
    """(family, kind) of a finding whose check has a closed list of kinds, or None when the message names none."""
    m = None
    if aid == 'CONSISTENCY':
        m = _CONSISTENCY.match(msg)
    elif aid in ('gate-G8-runtime-load',) or aid.startswith('window-'):
        m = _CODE_COLON.match(msg)
    elif aid == 'gate-GAME-runtime':
        m = _CODE_PAREN.match(msg)
    elif aid in ('BROWSER', 'REVIEW'):
        for kind, marker in (BROWSER_KINDS if aid == 'BROWSER' else REVIEW_KINDS):
            if marker in msg:
                return aid, kind
        return None                  # a finding with no known marker: the check's own words are true for all of them
    if m is None:
        return None
    return ('window-' if aid.startswith('window-') else aid), m.group(1)


def key_of(acceptance_id, message='') -> str | None:
    """The WORDS key of one failed check, or None for an engine note (NOT_A_FINDING). Raises NoWords when the
    platform has no customer words for it -- an id, or a kind its check names, that WORDS does not hold."""
    from .failure_taxonomy import failure_type
    aid, msg = str(acceptance_id or ''), str(message or '')
    if aid in NOT_A_FINDING:
        return None
    kind = _kind(aid, msg)
    if kind is not None:
        key = f'{kind[0]}:{kind[1]}'
        if key not in WORDS:
            raise NoWords(f'no customer words for the kind {key!r} (omni_prod/gate_words.WORDS)')
        return key
    if aid in WORDS:
        return aid
    for suffix in LAYER_SUFFIXES:
        if aid.endswith(suffix) and aid[:-len(suffix)] in WORDS:
            return 'LAYER' + suffix
    sandbox = 'SANDBOX:' + failure_type(msg, aid)
    if sandbox in WORDS:
        return sandbox
    for prefix in PREFIXES:
        if aid.startswith(prefix):
            return prefix
    raise NoWords(f'no customer words for the check {aid!r} ({msg[:80]!r}) (omni_prod/gate_words.WORDS)')


def words(key: str, lang: str) -> dict:
    """{'what', 'why', 'next', 'action'} of one key in one language. An unknown key, language or action raises."""
    if lang not in LANGS:
        raise ValueError(f'gate_words: no language {lang!r}; one of {LANGS}')
    if key not in WORDS:
        raise NoWords(f'no customer words for {key!r} (omni_prod/gate_words.WORDS)')
    entry = WORDS[key]
    if entry.action not in ACTIONS:
        raise ValueError(f'gate_words: {key!r} has the action {entry.action!r}; one of {ACTIONS}')
    what, why = getattr(entry, lang)
    nxt = entry.next.get(lang) if entry.next is not None else NEXT[lang][entry.action]
    if not nxt:                      # D3 (review 2026-11-22): a next action of its own, missing in this language
        raise NoWords(f'no next action in {lang!r} for {key!r} (omni_prod/gate_words.WORDS)')
    return {'what': what, 'why': why, 'next': nxt, 'action': entry.action}


def findings(failures, *, error_code=None, error_message=None) -> list[str]:
    """The keys of what stopped a build, each once, in the order the customer reads them: what only the customer can
    change first. A build that waits for a fact from the customer is said by that fact alone (fact_canon); with no
    fact named, [] (the announcement's own sentence asks for the detail). Raises NoWords (see key_of) for the first
    finding with no words; `collect` says the worded ones and lists the rest."""
    keys, unworded = collect(failures, error_code=error_code, error_message=error_message)
    if unworded:
        raise NoWords(unworded[0])
    return keys


def collect(failures, *, error_code=None, error_message=None) -> tuple[list[str], list[str]]:
    """(keys, unworded): the keys of `findings`, and one NoWords reason per finding that has no words. A finding with
    no words is listed, never guessed, and never takes the worded ones down with it (D1, review 2026-11-22: one new
    check with no words used to leave the customer with the general sentence alone)."""
    keys: list[str] = []
    unworded: list[str] = []
    if error_code == 'needs_customer_input':
        m = _MISSING.search(str(error_message or ''))
        for name in (m.group(1).split(',') if m else ()):
            name = name.strip()
            if not name:
                continue
            if 'needs:' + name not in WORDS:
                unworded.append(f'no customer words for the missing fact {name!r} (omni_prod/gate_words.WORDS)')
            elif 'needs:' + name not in keys:
                keys.append('needs:' + name)
        return keys, unworded
    for f in failures or ():
        if not isinstance(f, dict):
            continue
        try:
            key = key_of(f.get('acceptance_id'), f.get('message'))
        except NoWords as exc:
            unworded.append(str(exc))
            continue
        if key is not None and key not in keys:
            keys.append(key)
    return sorted(keys, key=lambda k: WORDS[k].action != 'edit'), unworded      # stable: the checks' order otherwise


def verification_failures(evidence) -> list:
    """The failed checks a build's evidence carries (worker_tasks: evidence.gates.verification.failures)."""
    gates = evidence.get('gates') if isinstance(evidence, dict) else None
    verification = gates.get('verification') if isinstance(gates, dict) else None
    failures = verification.get('failures') if isinstance(verification, dict) else None
    return failures if isinstance(failures, list) else []

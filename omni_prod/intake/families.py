"""Product families and which ones the build engine can execute today.

The classifier is deterministic (keywords in Hebrew and English, tolerant of
common misspellings). `EXECUTABLE` is the truth about the engine: only web
applications/websites have a verified execution path (Golden E2E). Every other
family is recognized and planned, and its plan reports the capability gap
instead of pretending to build it.
"""
from __future__ import annotations

import re

FAMILIES = ('web_app', 'website', 'mobile_app', 'game', 'ai_agent', 'automation', 'api_integration', 'media',
            '3d_experience')
EXECUTABLE = {'web_app', 'website'}

# "שיר" (a song) as a WORD: alone or after one Hebrew prefix letter ("השיר", "לשיר", "ושיר", "בשיר"), never the tail
# of another word. Production 2026-11-17, "148 דלתות": the owner pasted a full brief for a doors company's site; its
# line "טון: ישיר, מקצועי" (a DIRECT tone) matched "שיר", the request was classified as media and refused with "שיר,
# סרטון או מוזיקה עוד לא" -- and the site was then built from the one word "אתר".
_SONG = r'(?<![א-ת])[הבלו]?שיר(?:ים)?(?![א-ת])'

# The words by which a request names a website or its page. A family the engine cannot build is refused when the
# customer ASKS for it (a request verb, or the product the message opens with) or when nothing in the message names a
# site; a brief that describes a page and mentions a video in passing is a website.
_NAMES_A_SITE = re.compile(r'אתר|דף נחיתה|דף (?:סטטי|מכירה|הבית)|מבנה הדף|landing page|web ?site|web ?page', re.I)

_RULES = (
    ('game', r'(משחק|גיים|game\b|games\b|platformer|multiplayer|מולטיפלייר|שלבים במשחק)'),
    ('3d_experience', r'(תלת[- ]?מימד|\b3d\b|three\.?js|מודל תלת)'),
    ('mobile_app', r'(אפליקציה (?:לנייד|לטלפון|לאייפון|לאנדרואיד)|אפליקצי[הת] מובייל|\bios\b|android|אנדרואיד|app store|play store|mobile app)'),
    ('media', r'(סרטו[ןנ]|וידאו|וידיאו|video|פודקאסט|podcast|מוזיקה|' + _SONG + r'|music|קריינות|voice ?over)'),
    ('automation', r'(אוטומצי|automation|workflow|זרימת עבודה|תזמון אוטומטי|zapier|n8n|כל בוקר שלח)'),
    ('ai_agent', r'(סוכן ai|ai agent|צ\'?אטבוט|chatbot|בוט שעונה|assistant bot)'),
    ('api_integration', r'(\bapi\b(?! key)|webhook|אינטגרציה|integration with|לחבר ל)'),
    ('website', r'(דף נחיתה|landing page|אתר תדמית|אתר אינטרנט|אתר לחברת|אתר של חברת|אתר לעסק|אתר לחנות|portfolio|תיק עבודות|בלוג|blog|website)'),
)

# Match the requested deliverable immediately after a creation/request verb.
# Feature keywords later in the sentence cannot change this product family.
_REQUEST = (r'(?:\b(?:build|create|make|generate|develop)\b|'
            r'\b(?:i\s+)?want(?:\s+to\s+(?:build|create|make|generate|develop))?\b|'
            r'אני רוצה(?:\s+(?:לבנות|ליצור))?|לבנות|ליצור|בנה|בני|צור|צרי)'
            r'\s+(?:(?:me|a|an|the|new|responsive|simple|modern|public|internal|static|לי)\s+)*')
_PRODUCTS = (
    ('game', r'(?:(?:2d|3d)\s+)?games?\b|משחק'),
    ('website', r'websites?\b|site\b|landing page\b|portfolio\b|blog\b|אתר|דף נחיתה|תיק עבודות|בלוג'),
    ('web_app', r'web (?:app(?:lication)?|dashboard)\b|saas\b|אפליקציית ווב|יישום ווב'),
    ('mobile_app', r'(?:mobile|native|ios|android)\s+app(?:lication)?\b|'
                   r'אפליקציה (?:לנייד|לטלפון|לאייפון|לאנדרואיד)|אפליקציית מובייל'),
    ('ai_agent', r'ai agent\b|chatbot\b|assistant bot\b|סוכן\s+ai|צ\'?אטבוט'),
    ('automation', r'automation\b|workflow\b|אוטומציה|זרימת עבודה'),
    ('api_integration', r'(?:api\s+)?integration\b|webhook\b|אינטגרציה'),
    ('media', r'video\b|podcast\b|music\b|image\b|texture\b|audio\b|voice ?over\b|'
              r'סרטון|וידאו|וידיאו|פודקאסט|מוזיקה|' + _SONG + r'|תמונה|טקסטורה|קריינות'),
    ('3d_experience', r'3d\s+(?:scene|model|experience|mesh)\b|'
                      r'(?:מודל|סצנה|חוויה)\s+תלת[- ]?מימד'),
)


def _norm(text: str) -> str:
    t = (text or '').lower()
    t = re.sub(r'(.)\1{2,}', r'\1\1', t)          # "סרטוןןן" -> "סרטוןן"
    return t.replace('אפלקציה', 'אפליקציה').replace('אפליקציא', 'אפליקציה').replace('משחר', 'משחק')


# Greetings and articles a request may open with, before the product it names.
_LEAD = re.compile(r'^\W*(?:(?:שלום|היי|הי|אהלן|בוקר טוב|ערב טוב|hi|hello|hey)\W+)*(?:(?:me|a|an|the|new|simple|לי)\s+)*', re.I)
# The products a request may OPEN with. Media without "image"/"texture": a photo's caption ("תמונה של החנות") is not
# a request for a media product.
_LEADING = tuple((f, p) for f, p in _PRODUCTS if f != 'media') + (
    ('media', r'video\b|podcast\b|music\b|audio\b|voice ?over\b|סרטון|וידאו|וידיאו|פודקאסט|מוזיקה|' + _SONG + r'|קריינות'),)


def _explicit(t: str) -> list[tuple[int, str]]:
    """(position, family) for every product the customer explicitly asked for with a request verb ("תבנה לי משחק",
    "I want a website"). Feature words later in the sentence never count."""
    explicit = []
    for family, product in _PRODUCTS:
        for match in re.finditer(_REQUEST + '(?:' + product + ')', t, re.I):
            clause = re.split(r'[.;!?\n,]|\b(?:and|but|instead)\b|אבל|אלא', t[:match.start()])[-1]
            if re.search(r"\b(?:not|never|don't|dont)\b|(?:^|\s)(?:לא|אל)(?:\s|$)", clause):
                continue
            explicit.append((match.start(), family))
    return explicit


def _opening(t: str) -> str | None:
    """The product a request OPENS with, after a greeting ("שלום, אתר לעסק שלי" -> website), or None.

    Warehouse 69 (2026-11-15): "אתר לחנות משחקים" is a website and "אתר לאולפן מוזיקה" is a website, so the router
    never refuses a shop that sells games or a studio that records music. Hebrew requests often have no verb: the
    first word is the deliverable."""
    start = _LEAD.match(t).end()
    for family, product in _LEADING:
        if re.match('(?:' + product + ')', t[start:], re.I):
            return family
    return None


def classify_family(text: str) -> str:
    t = _norm(text)
    explicit = _explicit(t)         # the explicitly requested product wins over incidental feature keywords
    if explicit:
        return min(explicit, key=lambda match: match[0])[1]
    for family, pattern in _RULES:
        if re.search(pattern, t, re.I):
            # the product the request opens with resolves a conflict between keyword cues ("אתר לחנות משחקים" is
            # not a game). A request with no cue keeps the web_app default as before: "אתר לניהול ספרייה עם מנויים"
            # stays web_app (tests/test_discovery_and_approval.py relies on it), and both families are built.
            opening = _opening(t)
            if opening is None and family not in EXECUTABLE and _NAMES_A_SITE.search(t):
                return 'website'           # a passing word in a text that describes a site is not a request for it
            return opening or family
    return 'web_app'


def requested_family(text: str) -> str | None:
    """The family the customer explicitly asked to have built: a request verb + product, or the product the message
    opens with. None when products are only mentioned in passing ("המטרה: למכור משחקים לילדים") or the message is a
    photo's caption ("תמונה של החנות"). The router uses it on a project that already has a brief, so a passing word
    never restarts or refuses the project."""
    t = _norm(text)
    explicit = _explicit(t)
    if explicit:
        return min(explicit, key=lambda match: match[0])[1]
    return _opening(t)


def named_family(text: str) -> str | None:
    """The family only when the text actually names a product; None for a follow-up such as an answer."""
    t = _norm(text)
    if any(re.search(product, t, re.I) for _, product in _PRODUCTS) or any(re.search(p, t, re.I) for _, p in _RULES):
        return classify_family(text)
    return None


def executable(family: str) -> bool:
    return family in EXECUTABLE

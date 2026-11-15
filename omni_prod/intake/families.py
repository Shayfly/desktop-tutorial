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

_RULES = (
    ('game', r'(משחק|גיים|game\b|games\b|platformer|multiplayer|מולטיפלייר|שלבים במשחק)'),
    ('3d_experience', r'(תלת[- ]?מימד|\b3d\b|three\.?js|מודל תלת)'),
    ('mobile_app', r'(אפליקציה (?:לנייד|לטלפון|לאייפון|לאנדרואיד)|אפליקצי[הת] מובייל|\bios\b|android|אנדרואיד|app store|play store|mobile app)'),
    ('media', r'(סרטו[ןנ]|וידאו|וידיאו|video|פודקאסט|podcast|מוזיקה|שיר\b|music|קריינות|voice ?over)'),
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
              r'סרטון|וידאו|וידיאו|פודקאסט|מוזיקה|שיר|תמונה|טקסטורה|קריינות'),
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
    ('media', r'video\b|podcast\b|music\b|audio\b|voice ?over\b|סרטון|וידאו|וידיאו|פודקאסט|מוזיקה|שיר\b|קריינות'),)


def _explicit(t: str) -> list[tuple[int, str]]:
    """(position, family) for every product the customer explicitly asked for: a request verb followed by the
    product, or the product opening the message. Feature words later in the sentence never count."""
    explicit = []
    for family, product in _PRODUCTS:
        for match in re.finditer(_REQUEST + '(?:' + product + ')', t, re.I):
            clause = re.split(r'[.;!?\n,]|\b(?:and|but|instead)\b|אבל|אלא', t[:match.start()])[-1]
            if re.search(r"\b(?:not|never|don't|dont)\b|(?:^|\s)(?:לא|אל)(?:\s|$)", clause):
                continue
            explicit.append((match.start(), family))
    _leading(t, explicit)
    return explicit


def _leading(t: str, explicit: list) -> None:
    """Warehouse 69 (2026-11-15): a request that OPENS with the product names it. "אתר לחנות משחקים" is a website and
    "אתר לאולפן מוזיקה" is a website, so the router never refuses a shop that sells games or a studio that records
    music. Hebrew requests often have no verb: the first word is the deliverable."""
    start = _LEAD.match(t).end()
    for family, product in _LEADING:
        if re.match('(?:' + product + ')', t[start:], re.I):
            explicit.append((start, family))
            return


def classify_family(text: str) -> str:
    t = _norm(text)
    explicit = _explicit(t)         # the explicitly requested product wins over incidental feature keywords
    if explicit:
        return min(explicit, key=lambda match: match[0])[1]
    for family, pattern in _RULES:
        if re.search(pattern, t, re.I):
            return family
    return 'web_app'


def requested_family(text: str) -> str | None:
    """The family the customer explicitly asked to have built (a request verb + product, or the product opening the
    message); None when products are only mentioned in passing ("המטרה: למכור משחקים לילדים"). The router uses it
    on a project that already has a brief, so a passing word never restarts or refuses the project."""
    explicit = _explicit(_norm(text))
    return min(explicit, key=lambda match: match[0])[1] if explicit else None


def named_family(text: str) -> str | None:
    """The family only when the text actually names a product; None for a follow-up such as an answer."""
    t = _norm(text)
    if any(re.search(product, t, re.I) for _, product in _PRODUCTS) or any(re.search(p, t, re.I) for _, p in _RULES):
        return classify_family(text)
    return None


def executable(family: str) -> bool:
    return family in EXECUTABLE

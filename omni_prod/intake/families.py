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
    ('website', r'(דף נחיתה|landing page|אתר תדמית|אתר אינטרנט|portfolio|תיק עבודות|בלוג|blog|website)'),
)


def _norm(text: str) -> str:
    t = (text or '').lower()
    t = re.sub(r'(.)\1{2,}', r'\1\1', t)          # "סרטוןןן" -> "סרטוןן"
    return t.replace('אפלקציה', 'אפליקציה').replace('אפליקציא', 'אפליקציה').replace('משחר', 'משחק')


def classify_family(text: str) -> str:
    t = _norm(text)
    for family, pattern in _RULES:
        if re.search(pattern, t, re.I):
            return family
    return 'web_app'


def executable(family: str) -> bool:
    return family in EXECUTABLE

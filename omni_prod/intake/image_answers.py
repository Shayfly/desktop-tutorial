"""Free-text answers to the image questions (warehouse 113, owner 2026-11-16).

The loop it ends: a customer uploaded a photo of the shop's door and, asked "what is in it?", typed "זאת הדלת של
החנות", then "דלת עם ידית", then "מוצר". None of it was read -- the question is a choice, only a button answered it --
the same question came back, and after three cards the buttons disappeared ("חסרה החלטה על ..."). The customer could
not build.

Deterministic word maps, no model (plan part A section 1.8: a judgement that can be coded is coded). The first
category word in the message wins ("הדלת של החנות" is a product: the door comes first). A message with no category
word maps to nothing -- the question stays, never a guess.
"""
from __future__ import annotations

import re

# a Hebrew word may carry up to two one-letter prefixes (ה, ו, ב, ש, ל, מ, כ): "והדלת", "שבחנות"
_PRE = r'(?:(?<=^)|(?<=[^\w֐-׿]))[הובשלמכ]{0,2}'
_END = r'(?![\w֐-׿])'

KIND_WORDS: tuple[tuple[str, str], ...] = (
    ('logo', r'לוגו|סמל|logo'),
    ('person', r'אדם|איש|אישה|בעלים|בעל|בעלת|אני|סבא|סבתא|אבא|אמא|עובד|עובדת|צוות|השם|שמו|שמה|person|owner|me|man|woman'),
    ('product', r'מוצר|מוצרים|דלת|דלתות|ידית|ידיות|פריט|מנה|מנות|מאכל|בשר|עוף|עוגה|product|item|door|handle|dish'),
    ('place', r'מקום|חנות|דלפק|מסעדה|סניף|חלל|אולם|מבנה|place|shop|store|counter|venue'),
)
_OTHER = r'משהו אחר|אחר|something else|other'

USE_WORDS: tuple[tuple[str, str], ...] = (
    ('inspiration', r'השראה|לא להציג|inspiration'),
    # the owner's own words, 2026-11-17 ("תעשו ממנו קריקטורה של קצב"): a drawing made FROM the photo is a change
    ('change', r'לשנות|לערוך|לעבד|שנה|קריקטורה|קריקטורות|ציור|איור|מצויר|מצוירת|לצייר|תצייר|תציירו|'
               r'change|edit|cartoon|caricature|illustration'),
    ('as_is', r'כמו שהיא|כמו שהוא|כמו שזה|כמו שהן|להשתמש|תשתמש|בלי שינוי|בלי לשנות|as is|use it'),
)

PLACE_WORDS: tuple[tuple[str, str], ...] = (
    ('hero', r'ראשית|ראשי|למעלה|בראש|באנר|hero|main|top'),
    ('products', r'מוצרים|המוצרים|products'),
    ('story', r'סיפור|אודות|עלינו|about|story'),
    ('gallery', r'גלריה|gallery'),
)

# words that only introduce the answer; what is left after them is the customer's description
_FILLER = re.compile(r'^\s*(?:זאת|זה|זו|זוהי|זהו|יש בה|יש בתמונה|בתמונה|בתמונה יש|התמונה של|תמונה של|it is|this is|it\'s)\s*',
                     re.I)


# "do what you want" (the owner, 2026-11-17, after the same image question came back three times): the customer hands
# the choice over -- the question's own recommendation is taken, said, and never asked again.
DELEGATE = re.compile(r'תחליט|תחליטו|תבחר|תבחרו|מה שאתה רוצה|מה שאתם רוצים|מה שבא לך|מה שנראה לך|לא משנה לי|'
                      r'you decide|up to you|whatever you want|your call', re.I)


def _first(text: str, table) -> str | None:
    t = (text or '').lower()
    hits = []
    for value, words in table:
        m = re.search(_PRE + '(?:' + words + ')' + _END, t, re.I)
        if m:
            hits.append((m.start(), value))
    return min(hits)[1] if hits else None


# The owner's rule (2026-11-16): a door or a handle is a product, wherever it stands ("the shop door").
_DOOR = r'דלת|דלתות|ידית|ידיות|door|doors|handle|handles'


def kind_of(text: str) -> str | None:
    if re.search(_PRE + '(?:' + _DOOR + ')' + _END, (text or '').lower()) and not _first(text, KIND_WORDS[:1]):
        return 'product'
    kind = _first(text, KIND_WORDS)
    if kind is None and re.search(_PRE + '(?:' + _OTHER + ')' + _END, (text or '').lower()):
        return 'other'
    return kind


def description(text: str) -> str:
    """The customer's own words for the image, without the opening filler ("זאת הדלת של החנות" -> "הדלת של החנות").
    Empty when the message is only the category word ("מוצר")."""
    t = _FILLER.sub('', (text or '').strip()).strip(' .,!')
    only_word = re.fullmatch(r'[הובשלמכ]{0,2}(?:' + '|'.join(w for _, w in KIND_WORDS) + '|' + _OTHER + r')', t.lower())
    return '' if not t or only_word else t[:300]


def answers_for(question, text: str) -> dict[str, str]:
    """The answers a typed message gives to the pending image question, or {} when it names no option."""
    if question is None or not (text or '').strip():
        return {}
    qid = question.id
    if qid == 'image_kind':
        kind = kind_of(text)
        if kind is None:
            return {}
        out = {'image_kind': kind}
        words = description(text)
        if words and kind != 'logo':
            out[f'image_who_{kind}'] = words      # the description answers "who/what exactly" too: not asked twice
        return out
    if qid in ('image_use', 'image_use_other'):
        use = _first(text, USE_WORDS)
        if use is None and DELEGATE.search(text) and question.recommended:
            use = question.recommended
        return {qid: use} if use else {}
    if qid.startswith('image_place_'):
        place = _first(text, PLACE_WORDS)
        return {qid: place} if place else {}
    return {}

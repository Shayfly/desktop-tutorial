"""What one page cannot hold: a request the content route would accept and then silently not build (route-honesty).

The content route renders ONE page (render.APP_PY serves GET / and nothing else, every other path is 404), with a
picture only in the hero and story places, and nothing on it can be changed by its owner after the build. The owner's
build bld_3938e570 (2026-11-25) asked for all three -- "ליד כל נושא ... תשים תמונה של הנושא", "לפתוח כל נושא ...
לעמוד חדש", "אני יוכל אחר כך להעלות עוד מוצרים" -- and the route said "all preconditions hold": a4.pictures counted ONE
picture (it counts only a number written next to the picture word), and nothing looked for pages or later editing.

`beyond(text)` reads the customer's words (facts.customer_text: the request and the brief lines that quote it) and
returns every kind it finds, each with the words that show it:

  picture_per_item   a picture for EACH item: a picture word and "כל <one item>" in one sentence ("תמונה של כל נושא",
                     "לכל מוצר תמונה", "a photo for each product"), or pictures of a set of items ("תמונות של
                     המוצרים", "תמונות לכל הקטגוריות", "photos of the dishes", "product photos")
  separate_pages     a page per item, or separate pages ("עמוד נפרד לכל קטגוריה", "דף לכל מוצר", "כל נושא ... לעמוד
                     חדש", "עמודים נפרדים", "כמה עמודים", "a separate page", "a page for each category")
  owner_edits_later  the owner adds or changes content after the build ("אני אוכל אחר כך להעלות עוד מוצרים",
                     "לעדכן בעצמי", "ממשק ניהול", "I will add new products myself", "an admin panel")

Each kind needs its own words in one sentence, never one word alone. These stay on the route: a hero picture that fits
"כל מסך"; "רשימה של כל המוצרים" (all of them, on the page); a link that opens "בעמוד חדש"; "לכל שירות פסקה בעמוד";
"דף נחיתה"; "בלי תמונות"; "אני אעלה לכם תמונות" / "I can send you photos" (the customer sending pictures now); "אוכל
טרי" (food). A negation ("בלי", "ללא", "לא", "אין", "without", "no", "not") in the three words before a match cancels
it. Deterministic, no model.
"""
from __future__ import annotations

import re

_HE = 'א-ת'
_START = r'(?<![\w' + _HE + r'])'
_P = _START + r'[ובשלמהכ]{0,3}'                     # a Hebrew word start, with up to three prefix letters
_E = r'(?![\w' + _HE + r'])'                         # a Hebrew word end
_CLAUSE = re.compile(r'[.!?;\n]+')


def _alt(words) -> str:
    return '(?:' + '|'.join(sorted(map(re.escape, words), key=len, reverse=True)) + ')'


# Things a site lists one by one. "כל" + ONE of these is "each item"; "כל" + anything else ("כל מסך", "כל הקישורים",
# "כל המידע") is not, and "כל ה<items>" is "all of them" -- a set only with a plural picture word.
ONE_ITEM_HE = ('נושא', 'מוצר', 'קטגוריה', 'מנה', 'שירות', 'פריט', 'סוג', 'דגם', 'טיפול', 'חדר', 'צימר', 'חבילה',
               'פרויקט', 'תחום', 'מחלקה', 'אוסף', 'קורס', 'שיעור', 'סדנה', 'אירוע', 'מותג', 'נכס', 'דירה', 'רכב',
               'ספר', 'יין', 'עוגה', 'זר', 'תכשיט', 'בגד', 'מתכון', 'מאמר')
ITEMS_HE = ('נושאים', 'מוצרים', 'קטגוריות', 'מנות', 'שירותים', 'פריטים', 'סוגים', 'דגמים', 'טיפולים', 'חדרים',
            'צימרים', 'חבילות', 'פרויקטים', 'תחומים', 'מחלקות', 'אוספים', 'קורסים', 'שיעורים', 'סדנאות', 'אירועים',
            'מותגים', 'נכסים', 'דירות', 'רכבים', 'ספרים', 'יינות', 'עוגות', 'זרים', 'תכשיטים', 'בגדים', 'מתכונים',
            'מאמרים')
ITEMS_EN = ('item', 'product', 'category', 'dish', 'service', 'room', 'package', 'project', 'collection', 'course',
            'class', 'topic', 'brand', 'model', 'treatment', 'property', 'car', 'book', 'wine', 'cake', 'recipe', 'one')
# "כל אחד" alone is "everyone" ("תמונה שכל אחד יאהב"); "כל אחד מהמוצרים" is each of them
_ONE_HE = '(?:' + _alt(ONE_ITEM_HE) + r'|(?:אחד|אחת)\s+מה\S+)'
_ITEMS_EN = r'(?:' + '|'.join(sorted(ITEMS_EN, key=len, reverse=True)) + r')(?:s|es|ies)?'
_ITEMS_EN_PLURAL = (r'(?:items|products|categories|dishes|services|rooms|packages|projects|collections|courses|classes'
                    r'|topics|brands|models|treatments|properties|cars|books|wines|cakes|recipes)')

_EACH_HE = re.compile(_START + r'[ובשלמהכ]{0,2}(?:ליד\s+|עבור\s+|בשביל\s+)?כל\s+' + _ONE_HE + _E)
_EACH_EN = re.compile(r'\b(?:each|every)\s+(?:\w+\s+)?' + _ITEMS_EN + r'\b', re.I)
_PICTURE_HE = re.compile(_P + r'(?:תמונה|תמונות|תמונת|איור|איורים|צילום|צילומים)' + _E)
_PICTURE_EN = re.compile(r'\b(?:picture|image|photo|photograph|illustration)s?\b', re.I)
_PICTURES_OF_SET_HE = re.compile(_P + r'(?:תמונות|צילומים|איורים)\s+(?:של\s+|מ|ל)?(?:כל\s+)?ה' + _alt(ITEMS_HE) + _E)
_PICTURES_OF_SET_EN = re.compile(r'\b(?:pictures|images|photos|photographs)\s+(?:of|for)\s+'
                                 r'(?:the\s+|our\s+|my\s+|all\s+(?:the\s+|our\s+)?)?' + _ITEMS_EN_PLURAL
                                 + r'\b|\b' + _ITEMS_EN + r'\s+(?:pictures|images|photos)\b', re.I)

_PAGE_HE = r'(?:עמוד|עמודים|דף|דפים)'
_OWN = 'נפרד|נפרדים|נפרדת|נפרדות|משלו|משלה|משלהם|משלהן|ייעודי|ייעודיים'
_OWN_HE = '(?:' + _OWN + ')'                       # a page of its own
_OWN_OR_NEW_HE = '(?:' + _OWN + '|חדש|חדשים)'         # ... or a new one
_PAGE_FOR_EACH_HE = re.compile(_P + _PAGE_HE + r'(?:\s+' + _OWN_OR_NEW_HE + r')?\s+(?:עבור\s+|בשביל\s+|ל)כל\s+'
                               + _ONE_HE + _E)
_EACH_HAS_PAGE_HE = re.compile(_P + r'כל\s+' + _ONE_HE + r'(?:\s+\S+){0,8}?\s+[ולב]{0,2}' + _PAGE_HE
                               + r'\s+' + _OWN_OR_NEW_HE + _E)
_EACH_GETS_PAGE_HE = re.compile(_START + r'ו?לכל\s+' + _ONE_HE + r'(?:\s+\S+){0,3}?\s+' + _PAGE_HE + _E)
_SEPARATE_HE = re.compile(_P + _PAGE_HE + r'\s+' + _OWN_HE + _E + '|' + _START
                          + r'(?:כמה|מספר|\d+|שני|שלושה|ארבעה|חמישה|שישה)\s+(?:עמודים|דפים)' + _E)
_SEPARATE_EN = re.compile(
    r'\b(?:separate|individual|dedicated)\s+pages?\b|\b(?:its|their)\s+own\s+pages?\b|\bpages?\s+(?:for|per)\s+'
    r'(?:each|every)\b|\b(?:multi-?page|multiple\s+pages|several\s+pages|many\s+pages|sub-?pages?)\b'
    r'|\b(?:each|every)\s+' + _ITEMS_EN + r'\s+(?:gets|has|with|on|in|opens(?:\s+in)?|goes\s+to)\s+(?:its\s+own|a\s+'
    r'separate|a\s+new|a\s+dedicated|a)\s+page\b', re.I)

# The owner, first person ("אני יוכל" is how the owner wrote it; a bare "אוכל" is food unless a verb follows at once)
_EDIT_HE = r'(?:להעלות|להוסיף|לעדכן|לערוך|לשנות|למחוק|לנהל|להחליף)'
_ABLE_EDIT_HE = re.compile(
    _P + r'(?:(?:אני|אנחנו)\s+(?:אוכל|יוכל|יכול|יכולה|נוכל|יכולים)|ש(?:אוכל|נוכל)|(?:תהיה|יהיה)\s+לי\s+(?:אפשרות|אפשר))'
    r'(?:\s+\S+){0,4}?\s+' + _EDIT_HE + _E
    + '|' + _START + r'(?:אוכל|נוכל)(?:\s+(?:אחר\s+כך|אח["״]כ|בהמשך|גם|בעצמי|לבד))?\s+' + _EDIT_HE + _E)
_TO_YOU_HE = re.compile(r'^\s*(?:\S+\s+)?(?:לך|לכם|לכן|אליך|אליכם|אלייך)' + _E)
_LATER_HE = re.compile(_P + r'(?:אחר\s+כך|אח["״]כ|אחר-כך|בהמשך|בעתיד|בעצמי|בעצמנו|לבד|עצמאי|עצמאית|כל\s+פעם|מדי\s+פעם'
                       r'|כל\s+הזמן|עוד|נוספים|נוספות|חדשים|חדשות|באתר)' + _E)
_SELF_EDIT_HE = re.compile(_P + _EDIT_HE + r'(?:\s+\S+){0,4}?\s+(?:בעצמי|בעצמנו|לבד|באופן\s+עצמאי)' + _E)
_ADMIN_HE = re.compile(_P + r'(?:ממשק|פאנל|לוח|אזור|עמוד|דף|מערכת)\s+ניהול' + _E
                       + '|' + _P + r'ניהול\s+(?:ה)?תוכן' + _E)
_ABLE_EDIT_EN = re.compile(r"\b(?:i|we)(?:'ll|\s+will|\s+can|\s+could|\s+should|\s+want\s+to|\s+would\s+like\s+to|"
                           r"\s+need\s+to)(?:\s+be\s+able\s+to)?(?:\s+\w+)?\s+(?:add|upload|update|edit|change|manage|"
                           r"post|remove|replace)\b", re.I)
_LATER_EN = re.compile(r'\b(?:later|myself|ourselves|on\s+my\s+own|on\s+our\s+own|whenever|over\s+time|more|new|from\s+'
                       r'time\s+to\s+time|in\s+the\s+future)\b', re.I)
_TO_YOU_EN = re.compile(r'^\s*(?:\w+\s+){0,3}?(?:to|for|with)\s+you\b', re.I)
_ADMIN_EN = re.compile(r'\badmin(?:istration)?\s+(?:panel|area|page|dashboard|section|interface)\b|\bcms\b|'
                       r'\bcontent\s+management\b|\bback-?office\b', re.I)

_NEGATION = re.compile(r'(?:^|\s)ו?(?:בלי|ללא|לא|אין)(?:\s|$)|\b(?:without|no|not|don\'t)\b', re.I)


def _negated(clause: str, start: int) -> bool:
    """A negation in the three words before `start`, inside the clause."""
    return bool(_NEGATION.search(' '.join(clause[:start].split()[-3:])))


def _first(pattern: re.Pattern, clause: str):
    return next((m for m in pattern.finditer(clause) if not _negated(clause, m.start())), None)


def _picture_per_item(clause: str) -> str | None:
    m = _first(_PICTURES_OF_SET_HE, clause) or _first(_PICTURES_OF_SET_EN, clause)
    if m:
        return m.group(0)
    for picture, each in ((_PICTURE_HE, _EACH_HE), (_PICTURE_EN, _EACH_EN)):
        p, e = _first(picture, clause), _first(each, clause)
        if p and e:
            a, b = sorted((p, e), key=lambda x: x.start())
            return clause[a.start():b.end()] if b.end() - a.start() <= 80 else f'{a.group(0)} ... {b.group(0)}'
    return None


def _separate_pages(clause: str) -> str | None:
    for pattern in (_PAGE_FOR_EACH_HE, _EACH_HAS_PAGE_HE, _EACH_GETS_PAGE_HE, _SEPARATE_HE, _SEPARATE_EN):
        m = _first(pattern, clause)
        if m:
            return m.group(0)
    return None


def _owner_edits_later(clause: str) -> str | None:
    for able, to_you, later in ((_ABLE_EDIT_HE, _TO_YOU_HE, _LATER_HE), (_ABLE_EDIT_EN, _TO_YOU_EN, _LATER_EN)):
        for m in able.finditer(clause):
            if _negated(clause, m.start()) or to_you.match(clause[m.end():]):
                continue
            if later.search(clause[m.start():]):
                return m.group(0)
    m = _first(_SELF_EDIT_HE, clause) or _first(_ADMIN_HE, clause) or _first(_ADMIN_EN, clause)
    return m.group(0) if m else None


KINDS = (('picture_per_item', _picture_per_item), ('separate_pages', _separate_pages),
         ('owner_edits_later', _owner_edits_later))


def beyond(text: str) -> list[tuple[str, str]]:
    """[(kind, the customer's words that show it)] for every kind of KINDS the text asks for, in KINDS order (the
    first sentence that shows each). [] when one page holds everything the text asks."""
    clauses = [' '.join(c.split()) for c in _CLAUSE.split(text or '')]
    out = []
    for kind, find in KINDS:
        for clause in clauses:
            words = find(clause) if clause else None
            if words:
                out.append((kind, words.strip()[:80]))
                break
    return out

"""The legal page of a content site (warehouse 127, acceptance 6; the owner's answer to DECISIONS.md question 13,
2026-11-22, standing release of 2026-11-27).

A site whose business has a domain file gets `public/legal.html`, derived from section 7 of that file, and a link to it
in the home page's footer. The page holds only what the platform knows:

  * what the site collects -- read from the rendered home page (a form that hands its text to WhatsApp, a cookie
    window), never assumed;
  * who is responsible and where to reach them -- the business name, and the home page, which holds the contact facts
    the customer gave (this page carries no phone or e-mail link of its own, so the gates that judge a business page
    have nothing to judge on it);
  * what the platform checked for accessibility -- exactly the skill units of gate G3, named, and what was NOT checked;
  * "זה לא ייעוץ משפטי", in plain Hebrew, first on the page;
  * the domain's questions for a lawyer -- the bullets of section 7 "Applies almost everywhere" and the jurisdiction of
    the page's script (Israel for a Hebrew page), as written in the domain file (English, "not verified" kept), grouped,
    then once more as one block of text to copy.

It never writes a company number, a regulator, a licence, or the wording of terms: a fact not given is said as not
given. A domain with no file gets no legal page, and the build evidence says so (`legal.page: null`). Any script but
Hebrew raises LegalNotBuilt: the page's own words exist in Hebrew only (warehouse 129 has not opened another script on
this route).
"""
from __future__ import annotations

import json
from typing import Mapping

LEGAL_PAGE = 'public/legal.html'
LEGAL_JSON = 'content/legal.json'
HREF = 'legal.html'
JURISDICTION_BY_SCRIPT = {'hebrew': 'Israel'}
NOT_ADVICE = 'זה לא ייעוץ משפטי.'
# The skill units of gate G3 (omni_prod/skill_units): what the page says was checked is this list, in the customer's words.
ACCESSIBILITY_CHECKS = {
    'a11y_alt_text': 'טקסט חלופי לכל תמונה',
    'a11y_contrast': 'ניגודיות מספקת בין הטקסט לרקע',
    'a11y_focus': 'סימון ברור של הרכיב הפעיל כשמנווטים במקלדת',
    'a11y_heading_order': 'סדר תקין של הכותרות',
    'a11y_labels': 'תווית לכל שדה בטופס',
}


class LegalNotBuilt(ValueError):
    """The legal page cannot be written for this script."""


def _units_exist() -> None:
    from ..skill_units import manifest, units
    known = set(units())
    missing = sorted(set(ACCESSIBILITY_CHECKS) - known)
    if missing:
        raise RuntimeError(f'the legal page names accessibility checks that are not skill units: {missing}')
    for unit in ACCESSIBILITY_CHECKS:
        if manifest(unit)['gate'] != 'G3':
            raise RuntimeError(f'the legal page says {unit} is checked by gate G3; its manifest says {manifest(unit)["gate"]}')


def collects(html: str) -> dict:
    """What the rendered home page does with a visitor's data: whether it has the form that hands its text to WhatsApp
    (the library's only form) and whether it has the cookie window. Read from the page itself."""
    return {'form': 'data-wa="' in html, 'cookie_window': 'data-148-window="cookie_banner"' in html}


def _groups(domain: dict, script: str) -> list[dict]:
    if script not in JURISDICTION_BY_SCRIPT:
        raise LegalNotBuilt(f'the legal page is written in Hebrew only; a {script} page has no jurisdiction mapped')
    from ..domain_registry import LEGAL_EVERYWHERE
    wanted = (LEGAL_EVERYWHERE, JURISDICTION_BY_SCRIPT[script])
    by_heading = {g['heading']: g for g in domain['legal']['groups']}
    missing = [h for h in wanted if h not in by_heading]
    if missing:
        raise LegalNotBuilt(f'{domain["slug"]}: the domain file has no legal group {missing}')
    return [by_heading[h] for h in wanted]


def document(domain: dict, c: dict, html: str, *, script: str = 'hebrew') -> dict:
    """The legal page's text. `c` is the section library's content (name and the contact facts as the customer gave
    them); `html` is the rendered home page, which says what the site collects."""
    _units_exist()
    seen = collects(html)
    name = c['name']
    paragraphs = []
    if seen['form']:
        paragraphs.append('באתר יש טופס יצירת קשר. מה שתכתבו בו (שם, טלפון, נושא והודעה) לא נשמר באתר. כשתלחצו על שליחה '
                          'נפתחת שיחה בוואטסאפ עם ההודעה מוכנה, והיא נשלחת רק אם תלחצו שם על שליחה.')
    else:
        paragraphs.append('באתר אין טופס ששומר פרטים. מי שרוצה ליצור קשר מתקשר או כותב לפרטים שמופיעים באתר.')
    if seen['cookie_window']:
        paragraphs.append('באתר יש הודעת עוגיות. הבחירה שלכם נשמרת בדפדפן שלכם, לביקור הנוכחי בלבד.')
    paragraphs.append('השרת של האתר רושם כל בקשה אליו ביומן טכני, כולל כתובת הרשת של המבקר. כמה זמן היומן נשמר נקבע '
                      'אצל מי שמארח את האתר, ואינו ידוע לנו.')
    sections = [
        {'id': 'legal-collected', 'title': 'אילו פרטים האתר אוסף', 'paragraphs': paragraphs},
        {'id': 'legal-responsible', 'title': 'מי אחראי על האתר',
         'paragraphs': [f'האחראי על האתר ועל התוכן שבו הוא {name}. אפשר לפנות אליו בכל נושא שנוגע לפרטים שלכם, '
                        'בפרטי הקשר שבעמוד הבית.',
                        'מספר עוסק או חברה לא נמסר לנו, ולכן הוא לא מופיע כאן.']},
        {'id': 'legal-accessibility', 'title': 'נגישות',
         'paragraphs': ['לפני שהאתר נמסר בדקנו אותו אוטומטית בנקודות האלה:'],
         'items': list(ACCESSIBILITY_CHECKS.values())
                  + ['לא נבדק: שימוש בקורא מסך, והתאמה מלאה לתקן הנגישות. זו לא הצהרת נגישות רשמית. '
                     'מי שנתקל בקושי בגלישה מוזמן לפנות בפרטי הקשר שבעמוד הבית.']},
    ]
    groups = _groups(domain, script)
    lines = [f'Questions for my lawyer: {domain["name"]}']
    for g in groups:
        lines += ['', f'{g["heading"]}:'] + [f'- {i}' for i in g['items']]
    return {
        'title': 'מידע משפטי ופרטיות',
        'lead': f'מה האתר של {name} אוסף, מי אחראי עליו, ומה נבדק בנגישות.',
        'notice': f'{NOT_ADVICE} העמוד הזה הוא טיוטה: הוא מסכם רק מה שהאתר עושה בפועל ומה שנמסר לנו, ושווה לעבור עליו '
                  'עם עורך דין.',
        'sections': sections,
        'questions': {
            'title': 'שאלות לעורך הדין שלכם',
            'lead': 'אלה שאלות לבדיקה, לא תשובות. הן נכתבו באנגלית עבור התחום "' + domain['name'] + '". מה שמסומן '
                    '"not verified" לא נבדק מול חוק או תקנה. כאן רק מה שחל על כל מקום ועל ישראל; עסק במדינה אחרת '
                    'צריך לשאול גם על המדינה שלו.',
            'groups': [{'heading': g['heading'], 'items': list(g['items'])} for g in groups],
            'copy_label': 'לחצו בתוך התיבה, בחרו הכול והעתיקו, כדי להעביר את השאלות לעורך הדין:',
            'copy_text': '\n'.join(lines),
        },
    }


def files(domain: dict | None, c: dict, html: str, contract: dict, *, script: str = 'hebrew') -> dict[str, str]:
    """{path: text} of the legal page and its data; {} when the business has no domain file."""
    if domain is None:
        return {}
    from .. import section_library as L
    doc = document(domain, c, html, script=script)
    page = L.legal_page({k: v for k, v in c.items() if k != 'legal_href'}, contract, doc)
    data = {'domain': domain['slug'], 'script': script, 'collects': collects(html), 'document': doc,
            'editable': True, 'about': 'written by the platform from what the site does and the domain file; the text '
            'is data, so it can be changed without writing the page again'}
    return {LEGAL_PAGE: page, LEGAL_JSON: json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + '\n'}


def summary(domain: dict | None, produced: Mapping[str, str]) -> dict:
    """For the build evidence: the page, the domain it was derived from, the groups and how many questions it carries."""
    if domain is None or LEGAL_JSON not in produced:
        return {'page': None, 'why': 'no domain file for this business'}
    data = json.loads(produced[LEGAL_JSON])
    q = data['document']['questions']
    return {'page': LEGAL_PAGE, 'domain': domain['slug'], 'groups': [g['heading'] for g in q['groups']],
            'questions': sum(len(g['items']) for g in q['groups']), 'collects': data['collects'],
            'accessibility_checks': sorted(ACCESSIBILITY_CHECKS)}


def findings(repository: Mapping[str, str], domain: dict | None, script: str = 'hebrew') -> list[str]:
    """What is wrong with the legal page of a repository, as sentences: a business with a domain and no page, a page
    without the 'not legal advice' line or without one of its questions, a home page that does not link to it, a data
    file that names another domain. A business without a domain must have no legal page."""
    page, data = repository.get(LEGAL_PAGE), repository.get(LEGAL_JSON)
    if domain is None:
        return [f'{p} exists but the business has no domain file' for p in (LEGAL_PAGE, LEGAL_JSON) if p in repository]
    out = []
    if not isinstance(page, str):
        out.append(f'{LEGAL_PAGE} is missing: the business reads the domain {domain["slug"]!r}, so its site needs a legal page')
    if not isinstance(data, str):
        out.append(f'{LEGAL_JSON} is missing')
    index = repository.get('public/index.html')
    if isinstance(index, str) and f'href="{HREF}"' not in index:
        out.append(f'the home page does not link to {HREF}')
    if not isinstance(page, str):
        return out
    from ..section_library import e
    if NOT_ADVICE not in page:
        out.append(f'{LEGAL_PAGE} does not say {NOT_ADVICE!r}')
    for g in _groups(domain, script):
        for item in g['items']:
            if e(item) not in page:
                out.append(f'{LEGAL_PAGE} lacks the question {item[:60]!r} of the group {g["heading"]!r}')
                break
    if isinstance(data, str):
        try:
            slug = json.loads(data).get('domain')
        except ValueError:
            slug = None
        if slug != domain['slug']:
            out.append(f'{LEGAL_JSON} names the domain {slug!r}, not {domain["slug"]!r}')
    return out

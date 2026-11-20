"""The demo page: the owner's own law-firm brief (2026-11-19, bld_b0eb47a5), assembled from the library.

Only what the brief says is stated as fact (name, city, address, phone, e-mail, hours, since 2008, 3 lawyers, more
than 1,500 cases, the four practice areas, the three process steps, the first-consultation price, no testimonials).
Connecting sentences describe a practice area or a step; they claim nothing the brief did not give (v2 removed
"בלבד", "תחום אחד", "שנת ההקמה", "בדיסקרטיות" and "שוטף", and a note that said the form sends what it only drafts).
Each number appears once in the top half: the panel carries the cases, the strip the years, lawyers and areas.
"""
from __future__ import annotations

from ..g_apple import contract as C
from . import page

BRIEF_DESIGN = ('\n--- Approved project brief\nDesign: style clean; primary colour #1e3a5f; palette #1e3a5f, #b45309, '
                "#f8fafc, #0f172a (primary, accent, background, text: navy and white); font 'Heebo', system-ui, "
                "sans-serif (load it from Google Fonts); display font 'Frank Ruhl Libre', serif")

CONTENT = {
    'title': 'כהן ושות׳ – דיני עבודה | משרד עורכי דין בתל אביב',
    'description': 'מייצגים עובדים ומעסיקים בדיני עבודה מאז 2008. דרך מנחם בגין 132, תל אביב. 03-5551234.',
    'name': 'כהן ושות׳', 'tagline': 'דיני עבודה · תל אביב', 'year': '2026',
    'direction': 'formal', 'schema_type': 'LegalService',
    'phone': '03-5551234', 'whatsapp': '050-5551234',   # the brief: "וואטסאפ: 050-5551234" 'email': 'office@cohen-law.co.il',
    'address': 'דרך מנחם בגין 132, תל אביב', 'hours': 'א׳–ה׳ 09:00–18:00',
    'nav': [('services', 'תחומי התמחות'), ('about', 'על המשרד'), ('process', 'איך זה עובד'), ('faq', 'שאלות נפוצות'),
            ('contact', 'יצירת קשר')],
    'hero': {
        'eyebrow': 'משרד עורכי דין לדיני עבודה',
        'title': 'מייצגים עובדים ומעסיקים בדיני עבודה מאז 2008',
        'lead': 'ליווי משפטי בדיני עבודה, משיחת הייעוץ הראשונה ועד סיום ההליך.',
        'cta': 'לתיאום פגישת ייעוץ',
        'note': 'פגישת ייעוץ ראשונה: 250 ₪',
        'panel_label': 'המשרד בקצרה', 'art': 'columns',
        'panel_figure': '+1,500', 'panel_caption': 'תיקים בדיני עבודה',
        'panel_facts': [('שעות', 'א׳–ה׳ 09:00–18:00'), ('כתובת', 'דרך מנחם בגין 132, תל אביב'),
                        ('טלפון', '03-5551234', 'tel:035551234')],
    },
    'stats': [('2008', 'פעילים מאז'), ('3', 'עורכי דין'), ('4', 'תחומי ייצוג')],
    'services': {
        'eyebrow': 'תחומי התמחות', 'title': 'ייצוג בכל שלבי יחסי העבודה',
        'items': [('פיטורים שלא כדין', 'בדיקת ההליך שקדם לפיטורים ותביעה בגינם.'),
                  ('הטרדה במקום העבודה', 'ליווי בתלונה ובהליך המשפטי.'),
                  ('זכויות סוציאליות', 'בדיקת שכר, פיצויים, הפרשות וזכויות שלא שולמו.'),
                  ('ייצוג מעסיקים', 'ייעוץ וייצוג בהליכים מול עובדים.')],
    },
    'about': {
        'eyebrow': 'על המשרד', 'title': 'שלושה עורכי דין בדיני עבודה',
        'paragraphs': ['כהן ושות׳ הוא משרד עורכי דין בתל אביב שעוסק בדיני עבודה, ומייצג עובדים ומעסיקים מאז 2008.',
                       'עד היום ליווינו יותר מ-1,500 תיקים.'],
        'facts': [('מייצגים', 'עובדים ומעסיקים'), ('תחומים', 'פיטורים, הטרדה, זכויות סוציאליות, ייצוג מעסיקים'),
                  ('מיקום', 'דרך מנחם בגין 132, תל אביב')],
    },
    'process': {
        'eyebrow': 'איך זה עובד', 'title': 'שלושה שלבים, ליווי אחד',
        'steps': [('שיחת ייעוץ', 'מספרים לנו מה קרה, ומקבלים הערכה ראשונית של המצב.'),
                  ('בדיקת מסמכים', 'עוברים יחד על חוזה העבודה, תלושי השכר וההתכתבויות.'),
                  ('ליווי עד סיום ההליך', 'מייצגים אתכם בכל שלב, עד שההליך מסתיים.')],
    },
    'faq': {
        'eyebrow': 'שאלות נפוצות', 'title': 'מה שואלים אותנו לפני הפגישה',
        'items': [('כמה עולה ייעוץ ראשון?', 'פגישת ייעוץ ראשונה עולה 250 ₪.'),
                  ('כמה זמן לוקח הליך?', 'משך ההליך תלוי בסוג התיק. בפגישת הייעוץ נעריך יחד את לוח הזמנים לתיק שלכם.'),
                  ('האם צריך להגיע למשרד?', 'את אופן הפגישה נתאם איתכם בשיחה הראשונה.')],
    },
    'cta': {'title': 'רוצים לבדוק את המקרה שלכם?', 'text': 'התקשרו או כתבו לנו בוואטסאפ, ונתאם פגישת ייעוץ.'},
    'contact': {
        'eyebrow': 'יצירת קשר', 'title': 'נשמח לשמוע מכם', 'lead': 'כתבו לנו כמה פרטים, ונמשיך את השיחה בוואטסאפ.',
        'topics': ['פיטורים שלא כדין', 'הטרדה במקום העבודה', 'זכויות סוציאליות', 'ייצוג מעסיקים', 'אחר'],
        'submit': 'המשך בוואטסאפ',
    },
}


def build() -> tuple[str, dict, list[str]]:
    contract = C.build(BRIEF_DESIGN)
    doc, skipped = page(CONTENT, contract)
    return doc, contract, skipped

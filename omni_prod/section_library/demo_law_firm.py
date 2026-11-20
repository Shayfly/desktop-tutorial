"""The demo page: the owner's own law-firm brief (2026-11-19, bld_b0eb47a5), assembled from the library.

Only what the brief says is stated as fact (name, city, address, phone, e-mail, hours, since 2008, 3 lawyers, more
than 1,500 cases, the four practice areas, the three process steps, the first-consultation price, no testimonials).
Connecting sentences describe a practice area or a step; they claim nothing the brief did not give.
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
    'phone': '03-5551234', 'whatsapp': '03-5551234', 'email': 'office@cohen-law.co.il',
    'address': 'דרך מנחם בגין 132, תל אביב', 'hours': 'א׳–ה׳ 09:00–18:00',
    'nav': [('services', 'תחומי התמחות'), ('about', 'על המשרד'), ('process', 'איך זה עובד'), ('faq', 'שאלות נפוצות'),
            ('contact', 'צור קשר')],
    'hero': {
        'eyebrow': 'משרד עורכי דין לדיני עבודה',
        'title': 'מייצגים עובדים ומעסיקים בדיני עבודה מאז 2008',
        'lead': 'ליווי משפטי בדיני עבודה, משיחת הייעוץ הראשונה ועד סיום ההליך.',
        'cta': 'לתיאום פגישת ייעוץ',
        'note': 'פגישת ייעוץ ראשונה: 250 ₪',
        'panel_label': 'המשרד בקצרה',
        'panel_figure': '+1,500', 'panel_caption': 'תיקים בדיני עבודה',
        'panel_facts': [('שעות', 'א׳–ה׳ 09:00–18:00'), ('כתובת', 'דרך מנחם בגין 132, תל אביב'),
                        ('טלפון', '03-5551234', 'tel:035551234')],
    },
    'stats': [('2008', 'שנת ההקמה'), ('+1,500', 'תיקים'), ('3', 'עורכי דין'), ('250 ₪', 'פגישת ייעוץ ראשונה')],
    'services': {
        'eyebrow': 'תחומי התמחות', 'title': 'ייצוג בכל שלבי יחסי העבודה',
        'items': [('פיטורים שלא כדין', 'בדיקת ההליך שקדם לפיטורים ותביעה בגינם.'),
                  ('הטרדה במקום העבודה', 'ליווי בתלונה ובהליך המשפטי, בדיסקרטיות.'),
                  ('זכויות סוציאליות', 'בדיקת שכר, פיצויים, הפרשות וזכויות שלא שולמו.'),
                  ('ייצוג מעסיקים', 'ייעוץ שוטף וייצוג בהליכים מול עובדים.')],
    },
    'about': {
        'eyebrow': 'על המשרד', 'title': 'שלושה עורכי דין, תחום אחד',
        'paragraphs': ['כהן ושות׳ הוא משרד עורכי דין בתל אביב שעוסק בדיני עבודה בלבד, ומייצג עובדים ומעסיקים מאז 2008.',
                       'עד היום ליווינו יותר מ-1,500 תיקים.'],
        'facts': [('עורכי דין', '3'), ('תיקים', 'יותר מ-1,500'), ('פעילים מאז', '2008'), ('מיקום', 'דרך מנחם בגין 132, תל אביב')],
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
    'cta': {'title': 'רוצים לבדוק את הזכויות שלכם?', 'text': 'התקשרו או כתבו לנו בוואטסאפ, ונתאם פגישת ייעוץ.'},
    'contact': {
        'eyebrow': 'צור קשר', 'title': 'נשמח לשמוע מכם', 'lead': 'השאירו פרטים, וההודעה תישלח אלינו בוואטסאפ.',
        'topics': ['פיטורים שלא כדין', 'הטרדה במקום העבודה', 'זכויות סוציאליות', 'ייצוג מעסיקים', 'אחר'],
        'submit': 'שליחה בוואטסאפ', 'note': 'הפרטים נשלחים ישירות אלינו בוואטסאפ ולא נשמרים באתר.',
    },
}


def build() -> tuple[str, dict, list[str]]:
    contract = C.build(BRIEF_DESIGN)
    doc, skipped = page(CONTENT, contract)
    return doc, contract, skipped

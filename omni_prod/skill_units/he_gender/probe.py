"""skill.he.gender -- static, Hebrew page text: a noun and the adjective right after it disagree in gender ("מנה
טעים", "הבשר הטרייה"), or a number word disagrees with its noun ("שני שעות", "שתי מוצרים"). The nouns and adjectives
are a closed list (the words business sites use); a word outside the list is not judged -- never guessed."""
import re

from omni_prod.skill_units import text_nodes

_W = r'[א-ת]'
MASC = {'בשר', 'עוף', 'מוצר', 'שירות', 'טיפול', 'מקום', 'יום', 'שבוע', 'חודש', 'לקוח', 'מבצע', 'משלוח', 'תפריט',
        'אוכל', 'קפה', 'יין', 'מחיר', 'צוות', 'מטבח', 'נתח', 'לחם', 'סלט', 'קינוח', 'ייעוץ', 'אימון', 'שולחן'}
FEM = {'מנה', 'עוגה', 'חוויה', 'שעה', 'דקה', 'ארוחה', 'הזמנה', 'מסעדה', 'חנות', 'איכות', 'תוצאה', 'הנחה',
       'עבודה', 'שנה', 'פגישה', 'קציצה', 'אווירה', 'פיצה', 'שירה', 'חבילה', 'מתנה', 'סדנה', 'עוגייה', 'תמונה'}
ADJ = {'טרי': 'טרייה', 'טעים': 'טעימה', 'איכותי': 'איכותית', 'מקצועי': 'מקצועית', 'מיוחד': 'מיוחדת',
       'חדש': 'חדשה', 'נקי': 'נקייה', 'מוכן': 'מוכנה', 'ביתי': 'ביתית', 'מהיר': 'מהירה', 'אישי': 'אישית',
       'משפחתי': 'משפחתית', 'נהדר': 'נהדרת', 'מושלם': 'מושלמת', 'גדול': 'גדולה', 'קטן': 'קטנה', 'חם': 'חמה',
       'כשר': 'כשרה', 'מובחר': 'מובחרת', 'זול': 'זולה', 'יקר': 'יקרה', 'מעולה': 'מעולה'}
_FEM_ADJ = {f: m for m, f in ADJ.items() if f != m}
_MASC_ADJ = {m for m, f in ADJ.items() if f != m}
_PAIR = re.compile(rf'(?<!{_W})(?:[ובלמש]?(ה))?({_W}+)\s+(ה)?({_W}+)(?!{_W})')
_NUM = re.compile(rf'(?<!{_W})(שני|שתי)\s+({_W}+)(?!{_W})')


def _gender(noun):
    return 'm' if noun in MASC else 'f' if noun in FEM else None


def probe(html):
    findings = []
    for node in text_nodes(html):
        for m in _PAIR.finditer(node):
            noun, adj = m.group(2), m.group(4)
            g = _gender(noun)
            if g == 'f' and adj in _MASC_ADJ:
                findings.append({'where': node[:80], 'why': f'"{noun}" is feminine: "{ADJ[adj]}", not "{adj}"'})
            elif g == 'm' and adj in _FEM_ADJ:
                findings.append({'where': node[:80], 'why': f'"{noun}" is masculine: "{_FEM_ADJ[adj]}", not "{adj}"'})
        for m in _NUM.finditer(node):
            num, noun = m.groups()
            word = noun[:-2] + ('ה' if noun.endswith('ות') else '') if noun.endswith(('ים', 'ות')) else noun
            g = _gender(word) or _gender(noun)
            if (num == 'שני' and g == 'f') or (num == 'שתי' and g == 'm'):
                findings.append({'where': node[:80], 'why': f'"{num} {noun}": {"שתי" if g == "f" else "שני"}'})
    return {'status': 'fail', 'code': 'HE_GENDER', 'findings': findings} if findings else {'status': 'pass'}

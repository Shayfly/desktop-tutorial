"""skill.he.grammar -- static, Hebrew page text (one text node at a time, never joined across elements):
  - a word written twice in a row ("טרי טרי"), except the reduplications Hebrew uses on purpose ("לאט לאט");
  - a double superlative ("הכי טרי ביותר");
  - a definite construct with the article on the first noun ("הבית קפה" for "בית הקפה").
Rules, not a model: each finding names the words and the correct form."""
import re

from omni_prod.skill_units import text_nodes

_W = r'[א-ת]'
REDUPLICATION = {'לאט', 'יום', 'פעם', 'קצת', 'רגע', 'צעד', 'אחד', 'אחת', 'טיפה', 'שוב', 'מאוד', 'ממש', 'כן', 'לא'}
CONSTRUCTS = (('בית', 'קפה'), ('בית', 'ספר'), ('בית', 'מרקחת'), ('בית', 'חולים'), ('עורך', 'דין'), ('עורכת', 'דין'),
              ('רואה', 'חשבון'), ('חדר', 'כושר'), ('יום', 'הולדת'), ('ארוחת', 'בוקר'), ('ארוחת', 'ערב'),
              ('שעות', 'פתיחה'), ('מספר', 'טלפון'), ('דף', 'הבית'), ('תפריט', 'ילדים'))
_REPEAT = re.compile(rf'(?<!{_W})({_W}{{2,}})\s+\1(?!{_W})')
_SUPER = re.compile(rf'(?<!{_W})הכי\s+(?:{_W}+\s+){{1,3}}?ביותר(?!{_W})')
_CONSTRUCT = [(re.compile(rf'(?<!{_W})[ובלמש]?ה{a}\s+{b}(?!{_W})'), a, b) for a, b in CONSTRUCTS]


def probe(html):
    findings = []
    for node in text_nodes(html):
        for m in _REPEAT.finditer(node):
            if m.group(1) not in REDUPLICATION:
                findings.append({'where': node[:80], 'why': f'the word "{m.group(1)}" is written twice'})
        for m in _SUPER.finditer(node):
            findings.append({'where': node[:80], 'why': f'double superlative "{m.group()}": "הכי" or "ביותר", not both'})
        for rx, a, b in _CONSTRUCT:
            for m in rx.finditer(node):
                findings.append({'where': node[:80], 'why': f'"{m.group().strip()}": the article goes on the second '
                                                              f'noun ("{a} ה{b}")'})
    return {'status': 'fail', 'code': 'HE_GRAMMAR', 'findings': findings} if findings else {'status': 'pass'}

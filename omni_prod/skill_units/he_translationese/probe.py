"""skill.he.translationese -- static, Hebrew page text: phrases translated word for word from English that a Hebrew
writer would not use ("בסוף היום", "אל תהססו ל..."). A closed list, each with the natural Hebrew; never a guess."""
import re

from omni_prod.skill_units import text_nodes

_W = r'[א-ת]'
PHRASES = {
    'בסוף היום': 'בסופו של דבר',
    'לקחת החלטה': 'להחליט',
    'לוקחים החלטה': 'מחליטים',
    'לעשות את ההבדל': 'לשנות',
    'עושה הבדל': 'משנה',
    'עושה שכל': 'הגיוני',
    'אל תהסס': 'פנו אלינו',
    'אל תהססו': 'פנו אלינו',
    'הרגישו חופשי': 'אתם מוזמנים',
    'תרגישו חופשי': 'אתם מוזמנים',
    'על בסיס יומי': 'מדי יום',
    'לוקח מקום': 'מתקיים',
    'מגיע עם': 'כולל',
    'מגיעה עם': 'כוללת',
    'בצורה הטובה ביותר': 'הכי טוב',
    'ליצור קשר איתנו': 'לפנות אלינו',
    'יותר מאשר שמחים': 'נשמח מאוד',
    'בחוויה בלתי נשכחת': 'בחוויה מיוחדת',
}
_RX = [(re.compile(rf'(?<!{_W})[ובלמש]?{re.escape(p)}(?!{_W})'), p, fix) for p, fix in PHRASES.items()]


def probe(html):
    findings = [{'where': node[:80], 'why': f'"{p}" is translated from English; in Hebrew: "{fix}"'}
                for node in text_nodes(html) for rx, p, fix in _RX if rx.search(node)]
    return {'status': 'fail', 'code': 'HE_TRANSLATIONESE', 'findings': findings} if findings else {'status': 'pass'}

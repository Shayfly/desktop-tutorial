"""skill.copy.filler -- static, page text: generic filler sentences that say nothing about this business ("ברוכים
הבאים לאתר שלנו", "שירות ברמה הגבוהה ביותר", "Welcome to our website"). A closed list; each finding says to replace it
with a fact the customer gave."""
import re

from omni_prod.skill_units import text_nodes

_W = r'[\wא-ת]'
FILLER = (
    'ברוכים הבאים לאתר שלנו', 'ברוכים הבאים לאתר', 'אנחנו כאן בשבילכם', 'אנחנו כאן בשבילך', 'שירות ברמה הגבוהה ביותר',
    'שירות ברמה הכי גבוהה', 'המקום המושלם עבורך', 'המקום המושלם עבורכם', 'הפתרון המושלם עבורך', 'הפתרון המושלם עבורכם',
    'איכות ללא פשרות', 'שביעות רצון מלאה', 'צוות מקצועי ומנוסה', 'הכל במקום אחד', 'חוויה שלא תשכחו',
    'welcome to our website', 'we are here for you', 'your satisfaction is our priority', 'the best service in town',
    'quality you can trust', 'one-stop shop',
)
_RX = [(re.compile(rf'(?<!{_W}){re.escape(p)}(?!{_W})', re.I), p) for p in FILLER]


def probe(html):
    findings = [{'where': node[:80], 'why': f'"{p}" is filler: say something only this business can say'}
                for node in text_nodes(html) for rx, p in _RX if rx.search(node)]
    return {'status': 'fail', 'code': 'COPY_FILLER', 'findings': findings} if findings else {'status': 'pass'}

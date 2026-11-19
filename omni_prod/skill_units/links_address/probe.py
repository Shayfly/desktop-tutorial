"""skill.links.address -- static, page text: an address the page labels ("כתובת:") is whole -- a house number and a
city -- so a customer can get there. Cities are a closed list; a page with no address label is not judged."""
import re

from omni_prod.skill_units import text_nodes

CITIES = ('ירושלים', 'תל אביב', 'תל-אביב', 'חיפה', 'ראשון לציון', 'פתח תקווה', 'פתח תקוה', 'אשדוד', 'נתניה',
          'באר שבע', 'בני ברק', 'חולון', 'רמת גן', 'אשקלון', 'רחובות', 'בת ים', 'בית שמש', 'כפר סבא', 'הרצליה',
          'חדרה', 'מודיעין', 'נצרת', 'רמלה', 'לוד', 'רעננה', 'מודיעין עילית', 'ראש העין', 'הוד השרון', 'גבעתיים',
          'קריית גת', 'קרית גת', 'נהריה', 'עפולה', 'אילת', 'טבריה', 'קריית אתא', 'קרית אתא', 'יבנה', 'אור יהודה',
          'צפת', 'דימונה', 'נס ציונה', 'קריית מוצקין', 'קרית מוצקין', 'כרמיאל', 'עכו', 'גבעת שמואל', 'אריאל',
          'מעלה אדומים', 'זכרון יעקב', 'קיסריה', 'יקנעם', 'שוהם', 'ערד', 'אופקים', 'שדרות', 'נתיבות', 'עומר')
_LABEL = re.compile(r'^\s*(?:ה)?כתובת\s*(?::\s*(.*)|$)')   # "כתובת:" or "כתובת" alone; not "כתובת והתקשרות"


_FORM_LABEL = re.compile(r'<label\b[^>]*>\s*(?:ה)?כתובת\s*</label>', re.I)


def probe(html):
    nodes, findings = text_nodes(html), []
    # Calibration 2026-11-19 (bld_d36b3b4e): "כתובת" alone inside <label> names a form field, not an address the page
    # shows; the next text was the next field's label ("תאריך שירות"). A bare form label is not judged.
    form_label = bool(_FORM_LABEL.search(html or ''))
    for i, node in enumerate(nodes):
        m = _LABEL.match(node)
        if not m:
            continue
        if form_label and not (m.group(1) or '').strip():
            continue
        address = (m.group(1) or '').strip() or (nodes[i + 1] if i + 1 < len(nodes) else '')
        missing = [w for w, ok in (('a house number', re.search(r'\d', address)),
                                   ('a city', any(c in address for c in CITIES))) if not ok]
        if missing:
            findings.append({'where': address[:80] or node[:80], 'why': 'the address has no ' + ' and no '.join(missing)})
    return {'status': 'fail', 'code': 'ADDRESS_INCOMPLETE', 'findings': findings} if findings else {'status': 'pass'}

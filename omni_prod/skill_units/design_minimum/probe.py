"""skill.design.minimum -- static: a business site meets a professional minimum (the owner, 2026-11-19, on the law-firm
site bld_b0eb47a5: "רמה נמוכה ... אני רוצה מקצועיות"). It judges only a business page -- one with a contact action
(tel:, WhatsApp, mailto: or #contact); an app screen or a game is not judged.

Fails when the page has: not exactly one <h1>; fewer than 4 <section> blocks; no visual at all (<img>, <svg>,
<picture>, <video>, or a CSS background-image / url()); or the main contact action only once."""
import re

_CONTACT = re.compile(r'href\s*=\s*["\'](?:tel:|https?://(?:wa\.me|api\.whatsapp\.com|chat\.whatsapp\.com)|whatsapp:|'
                      r'mailto:|#contact\b|#צור-קשר)', re.I)
MIN_SECTIONS = 4


def probe(html):
    html = html or ''
    contact = len(_CONTACT.findall(html))
    if not contact:
        return {'status': 'pass'}                      # not a business page: not judged
    findings = []
    h1 = len(re.findall(r'<h1\b', html, re.I))
    if h1 != 1:
        findings.append({'where': f'{h1} <h1>', 'why': 'a page has exactly one main heading'})
    sections = len(re.findall(r'<section\b', html, re.I))
    if sections < MIN_SECTIONS:
        findings.append({'where': f'{sections} <section>',
                         'why': f'at least {MIN_SECTIONS} content sections; this page is one bare block'})
    visual = re.search(r'<(?:img|svg|picture|video)\b', html, re.I) or re.search(r'background(?:-image)?\s*:[^;"]*url\(',
                                                                                  html, re.I)
    if not visual:
        findings.append({'where': 'the page', 'why': 'no image or visual anywhere: a hero visual is expected'})
    if contact < 2:
        findings.append({'where': 'the contact action', 'why': 'it appears once: repeat it at the end of the page'})
    return {'status': 'fail', 'code': 'DESIGN_TOO_BASIC', 'findings': findings} if findings else {'status': 'pass'}

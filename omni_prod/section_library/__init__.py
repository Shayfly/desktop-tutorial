"""148AI section library (the owner, 2026-11-20: "תכין את הסקשנים אתה אבל ברמה הכי גבוהה שיש").

Business sites were written from scratch by the model every time and came out bare (bld_b0eb47a5, the law-firm site:
"רמה נמוכה"). Tools that produce professional sites do not let the model design from nothing: the model assembles
designed sections and fills them with the customer's content. This module is that library.

* Every section is a function from the customer's content to HTML. Every string is escaped; nothing is invented:
  a section whose content was not given is not rendered (`render_page` skips it and says so in `skipped`).
* The styling is `library.css`, written against the G-APPLE design contract (omni_prod/g_apple/contract.py): only
  the contract's tokens, the 8-grid, two weights, one radius. `page()` puts the contract's own :root block first.
* Right-to-left by logical properties; one <h1>; a skip link; native <details> for the menu and the FAQ; a phone action
  bar; the main action (call / WhatsApp) at the top and again at the end.

This first slice is the library and its demo page (the owner judges the look first). Wiring it into the generator is
the next step, after the look is approved.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
# shipped without its comments: a comment that names what the page avoids must not read as the thing itself
CSS = re.sub(r'/\*.*?\*/', '', (HERE / 'library.css').read_text(encoding='utf-8'), flags=re.S).strip()
def font_links(contract: dict) -> str:
    """Google Fonts for the contract's body and heading fonts (each loaded once, weights 400 and 700, display=swap);
    a system font stack loads nothing."""
    names = []
    for token in ('--font-family', '--font-display'):
        m = re.match(r"\s*'([^']+)'", contract['tokens'].get(token, ''))
        if m and m.group(1) not in names:
            names.append(m.group(1))
    if not names:
        return ''
    families = '&'.join('family=' + n.replace(' ', '+') + ':wght@400;700' for n in names)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{families}&display=swap">')

e = html.escape


def _icon(name: str) -> str:
    """Line icons drawn here (no third-party icon set): phone, whatsapp, mail, arrow."""
    paths = {
        'phone': '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/>',
        'whatsapp': '<path d="M3 21l1.6-4.8A8.5 8.5 0 1 1 8 19.6z"/><path d="M9 9.5c.5 2 2 3.5 4 4l1.2-1.2 2 1-.6 1.7c-3.4.4-7-3.2-6.6-6.6l1.7-.6 1 2z"/>',
        'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
        'arrow': '<path d="M19 12H5"/><path d="m11 6-6 6 6 6"/>',
    }
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true" focusable="false">{paths[name]}</svg>')


def _art() -> str:
    """The hero panel's drawing: architectural lines (columns and a pediment), no stock photo of a gavel."""
    cols = ''.join(f'<rect x="{60 + i * 70}" y="170" width="34" height="300" rx="3"/>' for i in range(6))
    return ('<svg class="panel-art" viewBox="0 0 520 520" preserveAspectRatio="xMidYMid slice" fill="none" '
            'stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">'
            '<path d="M30 160 260 40l230 120Z"/><path d="M40 168h440M40 480h440M20 500h480"/>'
            f'{cols}<circle cx="260" cy="110" r="24"/></svg>')


def img(image: dict, *, eager: bool = False, cls: str = '') -> str:
    """A customer image: src, alt (required, said, never empty for content), optional width/height. The first screen's
    image loads eagerly with high priority; every other image is lazy (perf gates)."""
    if not image.get('alt'):
        raise ValueError(f"an image without alt text: {image.get('src')!r}")
    size = ''.join(f' {k}="{int(image[k])}"' for k in ('width', 'height') if image.get(k))
    load = ' loading="eager" fetchpriority="high"' if eager else ' loading="lazy"'
    klass = f' class="{e(cls)}"' if cls else ''
    return f'<img{klass} src="{e(image["src"])}" alt="{e(image["alt"])}"{size}{load} decoding="async">'


def tel(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit() or c == '+')
    return 'tel:' + digits


def wa(phone: str, text: str = '') -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('0'):
        digits = '972' + digits[1:]
    return f'https://wa.me/{digits}' + (f'?text={quote(text)}' if text else '')


def header(c: dict) -> str:
    links = ''.join(f'<a href="#{e(i)}">{e(t)}</a>' for i, t in c['nav'])
    call = (f'<a class="btn btn-primary header-call" href="{tel(c["phone"])}">{_icon("phone")}'
            f'<span>{e(c["phone"])}</span></a>')
    return (f'<header class="site-header"><div class="wrap">'
            f'<a class="brand" href="#top"><b>{e(c["name"])}</b><span>{e(c["tagline"])}</span></a>'
            f'<nav class="nav" aria-label="ניווט ראשי">{links}</nav>'
            f'<details class="menu"><summary>תפריט</summary><nav aria-label="ניווט ראשי בטלפון">{links}</nav></details>'
            f'{call}</div></header>')


def hero(c: dict) -> str:
    h = c['hero']
    facts = ''.join(f'<div><dt>{e(f[0])}</dt><dd>' + (f'<a href="{e(f[2])}">{e(f[1])}</a>' if len(f) > 2 else e(f[1]))
                    + '</dd></div>' for f in h['panel_facts'])
    return (f'<section class="hero" id="top" aria-labelledby="hero-title"><div class="wrap"><div>'
            f'<p class="eyebrow">{e(h["eyebrow"])}</p><h1 id="hero-title">{e(h["title"])}</h1>'
            f'<p class="lead">{e(h["lead"])}</p><div class="actions">'
            f'<a class="btn btn-primary" href="#contact">{e(h["cta"])}</a>'
            f'<a class="btn btn-secondary" href="{wa(c["whatsapp"])}">{_icon("whatsapp")}<span>וואטסאפ</span></a>'
            f'</div><p class="hero-note">{e(h["note"])}</p></div>'
            f'<aside class="panel{" panel--photo" if h.get("image") else ""}" aria-label="{e(h["panel_label"])}">'
            f'{img(h["image"], eager=True, cls="panel-photo") if h.get("image") else _art()}'
            f'<p class="panel-figure">{e(h["panel_figure"])}</p><p class="panel-caption">{e(h["panel_caption"])}</p>'
            f'<dl>{facts}</dl></aside></div></section>')


def stats(c: dict) -> str:
    items = ''.join(f'<div class="stat"><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for value, label in c['stats'])
    return f'<section class="stats" aria-label="המשרד במספרים"><div class="wrap"><dl>{items}</dl></div></section>'


def _head(eyebrow: str, title: str, lead: str = '', hid: str = '') -> str:
    lead_html = f'<p class="lead">{e(lead)}</p>' if lead else ''
    return (f'<div class="section-head"><p class="eyebrow">{e(eyebrow)}</p>'
            f'<h2 class="title" id="{e(hid)}">{e(title)}</h2>{lead_html}</div>')


def services(c: dict) -> str:
    s = c['services']
    cards = ''.join(f'<article class="card"><h3>{e(t)}</h3><p>{e(d)}</p></article>' for t, d in s['items'])
    return (f'<section class="section section--tint" id="services" aria-labelledby="services-title"><div class="wrap">'
            f'{_head(s["eyebrow"], s["title"], s.get("lead", ""), "services-title")}<div class="cards">{cards}</div>'
            f'</div></section>')


def about(c: dict) -> str:
    a = c['about']
    paras = ''.join(f'<p>{e(p)}</p>' for p in a['paragraphs'])
    facts = ''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k, v in a['facts'])
    return (f'<section class="section" id="about" aria-labelledby="about-title"><div class="wrap split"><div>'
            f'{_head(a["eyebrow"], a["title"], "", "about-title")}{paras}</div>'
            + (f'<figure class="about-photo">{img(a["image"])}</figure>' if a.get('image') else f'<dl class="facts">{facts}</dl>')
            + '</div></section>')


def team(c: dict) -> str:
    t = c['team']

    def member(m):
        face = img(m['photo'], cls='member-photo') if m.get('photo') else \
            f'<span class="member-initials" aria-hidden="true">{e("".join(w[0] for w in m["name"].split()[:2]))}</span>'
        # the heading comes first in the markup (a row of three never opens with an image); CSS shows the face on top
        return f'<article class="member"><h3>{e(m["name"])}</h3><p>{e(m["role"])}</p>{face}</article>'
    return (f'<section class="section" id="team" aria-labelledby="team-title"><div class="wrap">'
            f'{_head(t["eyebrow"], t["title"], t.get("lead", ""), "team-title")}'
            f'<div class="members">{"".join(member(m) for m in t["members"])}</div></div></section>')


def testimonials(c: dict) -> str:
    """Only the customer's own testimonials, each with the name the customer gave; none given -> not rendered."""
    t = c['testimonials']
    quotes = ''.join(f'<figure class="quote"><blockquote><p>{e(q["text"])}</p></blockquote>'
                     f'<figcaption>{e(q["name"])}</figcaption></figure>' for q in t['items'])
    return (f'<section class="section section--tint" id="testimonials" aria-labelledby="testimonials-title"><div class="wrap">'
            f'{_head(t["eyebrow"], t["title"], "", "testimonials-title")}<div class="quotes">{quotes}</div></div></section>')


def process(c: dict) -> str:
    p = c['process']
    steps = ''.join(f'<li><h3>{e(t)}</h3><p>{e(d)}</p></li>' for t, d in p['steps'])
    return (f'<section class="section section--tint" id="process" aria-labelledby="process-title"><div class="wrap">'
            f'{_head(p["eyebrow"], p["title"], p.get("lead", ""), "process-title")}<ol class="steps">{steps}</ol>'
            f'</div></section>')


def faq(c: dict) -> str:
    f = c['faq']
    items = ''.join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in f['items'])
    return (f'<section class="section" id="faq" aria-labelledby="faq-title"><div class="wrap">'
            f'{_head(f["eyebrow"], f["title"], "", "faq-title")}<div class="faq">{items}</div></div></section>')


def cta(c: dict) -> str:
    b = c['cta']
    return (f'<section class="section" aria-labelledby="cta-title"><div class="wrap"><div class="band"><div>'
            f'<h2 id="cta-title">{e(b["title"])}</h2><p>{e(b["text"])}</p></div><div class="actions">'
            f'<a class="btn btn-primary" href="{tel(c["phone"])}">{_icon("phone")}<span>{e(c["phone"])}</span></a>'
            f'<a class="btn btn-secondary" href="{wa(c["whatsapp"])}">{_icon("whatsapp")}<span>וואטסאפ</span></a>'
            f'</div></div></div></section>')


def contact(c: dict) -> str:
    k = c['contact']
    rows = [('טלפון', f'<a href="{tel(c["phone"])}">{e(c["phone"])}</a>')]
    if c.get('email'):
        rows.append(('דוא״ל', f'<a href="mailto:{e(c["email"])}">{e(c["email"])}</a>'))
    rows += [('כתובת', e(c['address'])), ('שעות פעילות', e(c['hours']))]
    info = ''.join(f'<div><dt>{t}</dt><dd>{v}</dd></div>' for t, v in rows)
    topics = ''.join(f'<option>{e(t)}</option>' for t in k['topics'])
    return (f'<section class="section section--tint" id="contact" aria-labelledby="contact-title"><div class="wrap contact">'
            f'<div>{_head(k["eyebrow"], k["title"], k.get("lead", ""), "contact-title")}<dl class="contact-list">{info}</dl></div>'
            f'<form class="form" data-wa="{e(wa(c["whatsapp"]))}" aria-label="טופס יצירת קשר">'
            f'<div class="field"><label for="f-name">שם מלא</label><input id="f-name" name="name" autocomplete="name" required></div>'
            f'<div class="field"><label for="f-phone">טלפון</label><input id="f-phone" name="phone" type="tel" '
            f'autocomplete="tel" inputmode="tel" required></div>'
            f'<div class="field"><label for="f-topic">נושא הפנייה</label><select id="f-topic" name="topic">{topics}</select></div>'
            f'<button class="btn btn-primary" type="submit">{_icon("whatsapp")}<span>{e(k["submit"])}</span></button>'
            f'<p class="form-note">{e(k["note"])}</p></form></div></section>')


def footer(c: dict) -> str:
    return (f'<footer class="site-footer"><div class="wrap"><div><b>{e(c["name"])}</b><p>{e(c["address"])}</p></div>'
            f'<p>© {e(c["year"])} {e(c["name"])}</p></div></footer>')


def mobile_bar(c: dict) -> str:
    return (f'<div class="mobile-bar"><a class="btn btn-primary" href="{tel(c["phone"])}">{_icon("phone")}<span>התקשרו</span></a>'
            f'<a class="btn btn-secondary" href="{wa(c["whatsapp"])}">{_icon("whatsapp")}<span>וואטסאפ</span></a></div>')


SCRIPT = ('<script>document.querySelectorAll("form[data-wa]").forEach(function(f){f.addEventListener("submit",function(ev){'
          'ev.preventDefault();var d=new FormData(f),t="שלום, שמי "+d.get("name")+". טלפון: "+d.get("phone")+". נושא: "'
          '+d.get("topic");window.location.href=f.dataset.wa+"?text="+encodeURIComponent(t);});});'
          'document.querySelectorAll(".menu nav a").forEach(function(a){a.addEventListener("click",function(){'
          'a.closest("details").removeAttribute("open");});});</script>')

# order on the page; a section whose key is missing from the content is skipped, never filled with invention
ORDER = (('hero', hero), ('stats', stats), ('services', services), ('about', about), ('team', team),
         ('process', process), ('testimonials', testimonials), ('faq', faq), ('cta', cta), ('contact', contact))


def page(content: dict, contract: dict) -> tuple[str, list[str]]:
    """(html, skipped section keys). `contract` is a G-APPLE contract (contract.build)."""
    c = content
    body, skipped = [], []
    for key, fn in ORDER:
        if c.get(key):
            body.append(fn(c))
        else:
            skipped.append(key)
    head = (f'<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(c["title"])}</title><meta name="description" content="{e(c["description"])}">'
            f'<meta property="og:title" content="{e(c["title"])}"><meta property="og:description" content="{e(c["description"])}">'
            f'<meta property="og:type" content="website">{font_links(contract)}<style>{contract["css"]}\n{CSS}</style>')
    doc = (f'<!doctype html><html lang="he" dir="rtl"><head>{head}</head><body>'
           f'<a class="skip" href="#main">דלגו לתוכן</a>{header(c)}<main id="main">{"".join(body)}</main>'
           f'{footer(c)}{mobile_bar(c)}{SCRIPT}</body></html>')
    from ..bidi_ranges import wrap_ranges        # "09:00–18:00" stays in its order on a right-to-left page
    return wrap_ranges(doc), skipped

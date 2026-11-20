"""148AI section library (the owner, 2026-11-20: "תכין את הסקשנים אתה אבל ברמה הכי גבוהה שיש"; "המטרה שלך זה רמה בין
לאומית"; "צריך להכין את זה בנושאים כללים ... לא רק לעורכי דין").

Business sites were written from scratch by the model every time and came out bare (bld_b0eb47a5, the law-firm site:
"רמה נמוכה"). Tools that produce professional sites do not let the model design from nothing: the model assembles
designed sections and fills them with the customer's content. This module is that library, for every kind of business.

* Every section is a function from the customer's content to HTML. Every string is escaped; nothing is invented:
  a section whose content was not given is not rendered (`page` skips it and says so in `skipped`), a fact that was not
  given (an e-mail, opening hours, a WhatsApp number) is left out, and a missing required fact raises.
* The styling is `library.css`, written against the G-APPLE design contract (omni_prod/g_apple/contract.py): only
  the contract's tokens, the 8-grid, two weights, one radius. `page()` puts the contract's own :root block first.
* Four art directions (directions.json: formal, warm, bold, elegant), chosen by the business's palette, change the
  hero, the panel, the numbers strip and the cards, never the structure.
* Section tones come from the position on the page (plain and tint alternate, one primary-coloured beat), so any subset
  of sections keeps a rhythm.
* Right-to-left by logical properties; one <h1>; a skip link; native <details> for the menu and the FAQ; a phone action
  bar; the main action (call / WhatsApp) at the top, in the middle and at the end; LocalBusiness structured data from the
  given facts only.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
# shipped without its comments: a comment that names what the page avoids must not read as the thing itself
LIBRARY_VERSION = '2'


def _minify(css: str) -> str:
    """Comments out, whitespace collapsed around braces and semicolons only (never inside a selector or a calc()): the
    page must fit the 45,000 characters the truth gate reads (preview_smoke)."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = re.sub(r'\s+', ' ', css)
    return re.sub(r'\s*([{};])\s*', r'\1', css).strip()


CSS = _minify((HERE / 'library.css').read_text(encoding='utf-8'))
DIRECTIONS = json.loads((HERE / 'directions.json').read_text(encoding='utf-8'))
NBSP = ' '


def e(s) -> str:
    """The customer's text in a text node: escaped (& < >) but quotes kept as typed (בע"מ, ושות'), and a shekel sign never
    wraps away from its number ("250 ₪")."""
    return html.escape(str(s), quote=False).replace(' ₪', NBSP + '₪')


def ea(s) -> str:
    """The customer's text inside an attribute value: quotes escaped too."""
    return html.escape(str(s), quote=True)


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
    families = '&'.join('family=' + n.replace(' ', '+') + ('' if n in DIRECTIONS['single_weight_display'] else ':wght@400;700')
                        for n in names)
    return ('<link rel="preconnect" href="https://fonts.googleapis.com">'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{families}&display=swap">')


def direction_for(palette: str) -> dict:
    """{'direction', 'display'} of a vertical palette (vertical_palettes.json). An unknown palette raises."""
    if palette not in DIRECTIONS['palettes']:
        raise KeyError(f'no art direction for palette {palette!r}')
    return DIRECTIONS['palettes'][palette]


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


# The hero panel's drawing, one per direction (no stock photo, no clip-art of the trade). It sits in the panel's top part
# and fades out above the figure. 'columns' is the classical one a law or finance office may ask for by name.
ARTS = {
    'lines': ''.join(f'<path d="M{40 + i * 44} 0v{180 + (i * 67) % 140}"/>' for i in range(11))
             + '<circle cx="372" cy="150" r="118"/><circle cx="372" cy="150" r="70"/>',
    'columns': '<path d="M30 160 260 40l230 120Z"/><path d="M40 168h440"/><circle cx="260" cy="110" r="24"/>'
               + ''.join(f'<rect x="{60 + i * 70}" y="176" width="34" height="320" rx="3"/>' for i in range(6)),
    'arches': ''.join(f'<path d="M{30 + i * 160} 330V170a70 70 0 0 1 140 0v160"/>'
                      f'<path d="M{55 + i * 160} 330V180a45 45 0 0 1 90 0v150"/>' for i in range(3))
              + '<path d="M0 330h520"/><circle cx="430" cy="70" r="34"/>',
    'diagonals': ''.join(f'<path d="M{-200 + i * 70} 360 {160 + i * 70} 0"/>' for i in range(11))
                 + '<path d="M300 0 520 220" stroke-width="18"/>',
}
DEFAULT_ART = {'formal': 'lines', 'warm': 'arches', 'bold': 'diagonals', 'elegant': None}


def _art(name: str | None) -> str:
    if name is None:
        return ''
    if name not in ARTS:
        raise ValueError(f'unknown hero art {name!r}; one of {sorted(ARTS)} or "none"')
    return ('<svg class="panel-art" viewBox="0 0 520 520" preserveAspectRatio="xMidYMin slice" fill="none" '
            f'stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">{ARTS[name]}</svg>')


def img(image: dict, *, eager: bool = False, cls: str = '') -> str:
    """A customer image: src, alt (required, said, never empty for content), optional width/height. The first screen's
    image loads eagerly with high priority; every other image is lazy (perf gates)."""
    if not image.get('alt'):
        raise ValueError(f"an image without alt text: {image.get('src')!r}")
    size = ''.join(f' {k}="{int(image[k])}"' for k in ('width', 'height') if image.get(k))
    load = ' loading="eager" fetchpriority="high"' if eager else ' loading="lazy"'
    klass = f' class="{ea(cls)}"' if cls else ''
    return f'<img{klass} src="{ea(image["src"])}" alt="{ea(image["alt"])}"{size}{load} decoding="async">'


def tel(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit() or c == '+')
    return 'tel:' + digits


def wa(phone: str, text: str = '') -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('0'):
        digits = '972' + digits[1:]
    return f'https://wa.me/{digits}' + (f'?text={quote(text)}' if text else '')


def _call(c: dict, label: str | None = None, cls: str = 'btn btn-primary') -> str:
    return f'<a class="{cls}" href="{tel(c["phone"])}">{_icon("phone")}<span>{e(label or c["phone"])}</span></a>'


def _whatsapp(c: dict, cls: str = 'btn btn-secondary') -> str:
    return f'<a class="{cls}" href="{wa(c["whatsapp"])}">{_icon("whatsapp")}<span>וואטסאפ</span></a>' if c.get('whatsapp') else ''


def _need(d: dict, keys: tuple, where: str) -> None:
    missing = [k for k in keys if not d.get(k)]
    if missing:
        raise ValueError(f'{where}: missing {missing} (a section is given in full or left out; nothing is filled in)')


def _head(d: dict, key: str) -> str:
    _need(d, ('title',), key)
    eyebrow = f'<p class="eyebrow">{e(d["eyebrow"])}</p>' if d.get('eyebrow') else ''
    lead = f'<p class="lead">{e(d["lead"])}</p>' if d.get('lead') else ''
    return f'<div class="section-head">{eyebrow}<h2 class="title" id="{key}-title">{e(d["title"])}</h2>{lead}</div>'


def _section(key: str, tone: str, inner: str, wrap: str = '') -> str:
    cls = ' '.join(['section'] + tone.split())
    return (f'<section class="{cls}" id="{key}" aria-labelledby="{key}-title"><div class="wrap{" " + wrap if wrap else ""}">'
            f'{inner}</div></section>')


_LONG_NAV = 48          # characters of link text: more than this does not fit beside the brand on a laptop


def header(c: dict, rendered: list[str]) -> str:
    items = [(i, t) for i, t in c.get('nav', ()) if i in rendered]       # never a link to a section that was left out
    links = ''.join(f'<a href="#{ea(i)}">{e(t)}</a>' for i, t in items)
    long = len(items) > 5 or sum(len(t) for _, t in items) > _LONG_NAV
    tagline = f'<span>{e(c["tagline"])}</span>' if c.get('tagline') else ''
    nav = f'<nav class="nav" aria-label="ניווט ראשי">{links}</nav>' if items else ''
    menu = (f'<details class="menu"><summary>תפריט</summary><nav aria-label="ניווט ראשי בטלפון">{links}</nav></details>'
            if items else '')
    return (f'<header class="site-header{" site-header--long" if long else ""}"><div class="wrap">'
            f'<a class="brand" href="#top"><b>{e(c["name"])}</b>{tagline}</a>{nav}'
            f'<div class="header-actions">{_call(c, cls="btn btn-primary header-call")}{menu}</div></div></header>')


def hero(c: dict, tone: str, direction: str) -> str:
    h = c['hero']
    _need(h, ('title', 'lead', 'cta'), 'hero')
    primary_href = '#contact' if c.get('contact') else tel(c['phone'])
    second = _whatsapp(c) or (_call(c, cls='btn btn-secondary') if c.get('contact') else '')
    eyebrow = f'<p class="eyebrow">{e(h["eyebrow"])}</p>' if h.get('eyebrow') else ''
    note = f'<p class="hero-note">{e(h["note"])}</p>' if h.get('note') else ''
    copy = (f'<div class="hero-copy">{eyebrow}<h1 id="hero-title">{e(h["title"])}</h1><p class="lead">{e(h["lead"])}</p>'
            f'<div class="actions"><a class="btn btn-primary" href="{primary_href}">{e(h["cta"])}</a>{second}</div>{note}</div>')
    if not (h.get('image') or h.get('panel_figure') or h.get('panel_facts')):
        return (f'<section class="hero hero--solo" id="top" aria-labelledby="hero-title"><div class="wrap">{copy}</div>'
                f'</section>')
    facts = ''.join(f'<div><dt>{e(f[0])}</dt><dd>' + (f'<a href="{ea(f[2])}">{e(f[1])}</a>' if len(f) > 2 else e(f[1]))
                    + '</dd></div>' for f in h.get('panel_facts', ()))
    art = h.get('art', DEFAULT_ART[direction])
    visual = img(h['image'], eager=True, cls='panel-photo') if h.get('image') else _art(None if art == 'none' else art)
    figure = (f'<p class="panel-figure">{e(h["panel_figure"])}</p><p class="panel-caption">{e(h.get("panel_caption", ""))}</p>'
              if h.get('panel_figure') else '')
    return (f'<section class="hero" id="top" aria-labelledby="hero-title"><div class="wrap">{copy}'
            f'<div class="panel{" panel--photo" if h.get("image") else ""}" role="group" '
            f'aria-label="{ea(h.get("panel_label") or c["name"])}">{"" if h.get("image") else visual}{figure}'
            f'{f"<dl>{facts}</dl>" if facts else ""}{visual if h.get("image") else ""}</div></div></section>')


def stats_shown(c: dict) -> list:
    """The strip's numbers less the one the hero panel already shows (a number is said once in the top half)."""
    figure = c['hero'].get('panel_figure')
    return [(v, label) for v, label in c.get('stats') or () if v != figure]


def stats(c: dict, tone: str) -> str:
    items = ''.join(f'<div class="stat"><dt>{e(label)}</dt><dd>{e(value)}</dd></div>' for value, label in stats_shown(c))
    label = c.get('stats_label') or f'{c["name"]} במספרים'
    return f'<section class="stats" aria-label="{ea(label)}"><div class="wrap"><dl>{items}</dl></div></section>'


def services(c: dict, tone: str) -> str:
    s = c['services']
    cards = ''.join(f'<article class="card"><h3>{e(t)}</h3><p>{e(d)}</p></article>' for t, d in s['items'])
    return _section('services', tone, f'{_head(s, "services")}<div class="cards">{cards}</div>')


def about(c: dict, tone: str) -> str:
    a = c['about']
    paras = ''.join(f'<p>{e(p)}</p>' for p in a.get('paragraphs', ()))
    side = (f'<figure class="about-photo">{img(a["image"])}</figure>' if a.get('image') else
            f'<dl class="facts">{"".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in a["facts"])}</dl>'
            if a.get('facts') else '')
    return _section('about', tone, f'<div>{_head(a, "about")}{paras}</div>{side}', 'split')


_TITLES = {'ד״ר', 'ד"ר', 'דר׳', 'עו״ד', 'עו"ד', 'פרופ׳', "פרופ'", 'רו״ח', 'רו"ח', 'מר', 'גב׳', 'הרב', 'Dr.', 'Dr', 'Prof.'}


def initials(name: str) -> str:
    """Two letters for a member without a photo; a title ('ד״ר', 'עו״ד') is not part of a name."""
    words = [w for w in name.split() if w not in _TITLES] or name.split()
    return ''.join(w[0] for w in words[:2])


def team(c: dict, tone: str) -> str:
    t = c['team']

    def member(m):
        face = img(m['photo'], cls='member-photo') if m.get('photo') else \
            f'<span class="member-initials" aria-hidden="true">{e(initials(m["name"]))}</span>'
        # the heading comes first in the markup (a row of three never opens with an image); CSS puts the face beside it
        return f'<article class="member"><h3>{e(m["name"])}</h3><p>{e(m["role"])}</p>{face}</article>'
    return _section('team', tone, f'{_head(t, "team")}<div class="members">{"".join(member(m) for m in t["members"])}</div>')


def testimonials(c: dict, tone: str) -> str:
    """Only the customer's own testimonials, each with the name the customer gave; none given -> not rendered."""
    t = c['testimonials']
    quotes = ''.join(f'<figure class="quote"><blockquote><p>{e(q["text"])}</p></blockquote>'
                     f'<figcaption>{e(q["name"])}</figcaption></figure>' for q in t['items'])
    return _section('testimonials', tone, f'{_head(t, "testimonials")}<div class="quotes">{quotes}</div>')


def pricelist(c: dict, tone: str) -> str:
    """A menu or price list -- only the items and prices the customer gave. Groups (e.g. "שתייה חמה") are optional;
    an item without a price shows none (never a guessed price)."""
    p = c['pricelist']

    def row(i):
        price = f'<span class="price">{e(i["price"])}</span>' if i.get('price') else ''
        desc = f'<p>{e(i["desc"])}</p>' if i.get('desc') else ''
        return f'<li><div class="item-head"><h4>{e(i["name"])}</h4>{price}</div>{desc}</li>'
    groups = ''.join(f'<div class="price-group"><h3>{e(g["title"])}</h3><ul class="items">'
                     f'{"".join(row(i) for i in g["items"])}</ul></div>' for g in p['groups'])
    return _section('pricelist', tone, f'{_head(p, "pricelist")}<div class="price-groups">{groups}</div>')


def gallery(c: dict, tone: str) -> str:
    """The customer's own photos of their work; captions only when given."""
    g = c['gallery']
    figs = ''.join(f'<figure>{img(i)}' + (f'<figcaption>{e(i["caption"])}</figcaption>' if i.get('caption') else '')
                   + '</figure>' for i in g['images'])
    return _section('gallery', tone, f'{_head(g, "gallery")}<div class="gallery">{figs}</div>')


def process(c: dict, tone: str) -> str:
    p = c['process']
    steps = ''.join(f'<li><h3>{e(t)}</h3><p>{e(d)}</p></li>' for t, d in p['steps'])
    return _section('process', tone, f'{_head(p, "process")}<ol class="steps">{steps}</ol>')


def faq(c: dict, tone: str) -> str:
    f = c['faq']
    items = ''.join(f'<details><summary>{e(q)}</summary><div><p>{e(a)}</p></div></details>' for q, a in f['items'])
    return _section('faq', tone, f'{_head(f, "faq")}<div class="faq">{items}</div>', 'faq-layout')


def cta(c: dict, tone: str) -> str:
    b = c['cta']
    _need(b, ('title',), 'cta')
    text = f'<p>{e(b["text"])}</p>' if b.get('text') else ''
    return _section('cta', tone, f'<div class="band"><div><h2 id="cta-title">{e(b["title"])}</h2>{text}</div>'
                                 f'<div class="actions">{_call(c)}{_whatsapp(c)}</div></div>')


FORM_NOTE = 'השליחה פותחת את וואטסאפ עם ההודעה מוכנה. היא נשלחת רק כשתלחצו שם על שליחה, ולא נשמרת באתר.'


def contact(c: dict, tone: str) -> str:
    k = c['contact']
    rows = [('טלפון', f'<a href="{tel(c["phone"])}">{e(c["phone"])}</a>')]
    if c.get('email'):
        rows.append(('דוא״ל', f'<a href="mailto:{ea(c["email"])}">{e(c["email"])}</a>'))
    if c.get('address'):
        q = quote(c['address'])
        rows.append(('כתובת', e(c['address']) + f'<span class="directions">ניווט: <a href="https://waze.com/ul?q={q}">Waze</a>'
                     f' · <a href="https://www.google.com/maps/search/?api=1&amp;query={q}">Google Maps</a></span>'))
    if c.get('hours'):
        rows.append(('שעות פעילות', e(c['hours'])))
    info = ''.join(f'<div><dt>{t}</dt><dd>{v}</dd></div>' for t, v in rows)
    form = ''
    if c.get('whatsapp'):                       # the form hands the message to WhatsApp; no number -> no form
        req = ' <span class="req">(חובה)</span>'
        topics = (f'<div class="field"><label for="f-topic">נושא הפנייה{req}</label><select id="f-topic" name="topic" required>'
                  '<option value="" disabled selected>בחרו נושא</option>'
                  + ''.join(f'<option>{e(t)}</option>' for t in k['topics']) + '</select></div>') if k.get('topics') else ''
        form = (f'<form class="form" action="{ea(wa(c["whatsapp"]))}" method="get" data-wa="{ea(wa(c["whatsapp"]))}" '
                f'aria-label="טופס יצירת קשר">'
                f'<div class="field"><label for="f-name">שם מלא{req}</label><input id="f-name" name="name" autocomplete="name" required></div>'
                f'<div class="field"><label for="f-phone">טלפון{req}</label><input id="f-phone" name="phone" type="tel" '
                f'autocomplete="tel" inputmode="tel" required></div>{topics}'
                f'<div class="field"><label for="f-message">כמה מילים על הפנייה</label><textarea id="f-message" name="message" rows="3">'
                f'</textarea></div>'
                f'<button class="btn btn-primary" type="submit">{_icon("whatsapp")}<span>{e(k.get("submit") or "המשך בוואטסאפ")}</span></button>'
                f'<p class="form-note">{e(k.get("note") or FORM_NOTE)}</p></form>')
    return _section('contact', tone, f'<div>{_head(k, "contact")}<dl class="contact-list">{info}</dl></div>{form}', 'contact')


def footer(c: dict, rendered: list[str]) -> str:
    links = ''.join(f'<a href="#{ea(i)}">{e(t)}</a>' for i, t in c.get('nav', ()) if i in rendered)
    nav = f'<nav aria-label="ניווט בתחתית העמוד">{links}</nav>' if links else ''
    reach = [f'<a href="{tel(c["phone"])}">{e(c["phone"])}</a>']
    if c.get('email'):
        reach.append(f'<a href="mailto:{ea(c["email"])}">{e(c["email"])}</a>')
    if c.get('address'):
        reach.append(e(c['address']))
    tagline = f'<p>{e(c["tagline"])}</p>' if c.get('tagline') else ''
    year = f'{e(c["year"])} ' if c.get('year') else ''
    return (f'<footer class="site-footer"><div class="wrap"><div><b>{e(c["name"])}</b>{tagline}</div>{nav}'
            f'<div><b>יצירת קשר</b>{"".join(f"<p>{r}</p>" for r in reach)}</div>'
            f'<p class="legal">© {year}{e(c["name"])}</p></div></footer>')


def mobile_bar(c: dict) -> str:
    return (f'<nav class="mobile-bar" aria-label="פעולות מהירות">{_call(c, "התקשרו")}{_whatsapp(c)}</nav>')


# the form opens WhatsApp with the message ready; the menu closes on a link, a tap outside it or Escape; the phone action
# bar steps aside while the page's own call-to-action band or the form is on screen
SCRIPT = ('<script>document.querySelectorAll("form[data-wa]").forEach(function(f){f.addEventListener("submit",function(ev){'
          'ev.preventDefault();var d=new FormData(f),t="שלום, שמי "+d.get("name")+". טלפון: "+d.get("phone")'
          '+(d.get("topic")?". נושא: "+d.get("topic"):"")+(d.get("message")?". "+d.get("message"):"");'
          'window.location.href=f.dataset.wa+"?text="+encodeURIComponent(t);});});'
          'var m=document.querySelector(".menu");if(m){m.querySelectorAll("nav a").forEach(function(a){'
          'a.addEventListener("click",function(){m.removeAttribute("open");});});'
          'document.addEventListener("click",function(ev){if(m.open&&!m.contains(ev.target))m.removeAttribute("open");});'
          'document.addEventListener("keydown",function(ev){if(ev.key==="Escape"&&m.open){m.removeAttribute("open");'
          'm.querySelector("summary").focus();}});}'
          'var bar=document.querySelector(".mobile-bar");if(bar&&"IntersectionObserver" in window){var on=new Set();'
          'var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting)on.add(x.target);'
          'else on.delete(x.target);});bar.classList.toggle("is-away",on.size>0);});'
          'document.querySelectorAll(".band, #contact form").forEach(function(t){io.observe(t);});}</script>')

# order on the page; a section whose key is missing from the content is skipped, never filled with invention. The
# call-to-action band sits in the middle, after the process, so the action is offered again before the long tail.
ORDER = (('hero', hero), ('stats', stats), ('services', services), ('pricelist', pricelist), ('gallery', gallery),
         ('about', about), ('team', team), ('process', process), ('cta', cta), ('testimonials', testimonials),
         ('faq', faq), ('contact', contact))
REQUIRED = ('title', 'description', 'name', 'phone', 'direction', 'hero')


def tones(keys: list[str], direction: str) -> dict[str, str]:
    """Background tone of every rendered section, from its position: plain and tint alternate (the first section after
    the hero is tinted), the process is the page's one primary-coloured beat (not in the restrained elegant
    direction), the call-to-action band sits on plain. Two neighbours on the same tone share their padding
    (section--flush), so no gap is ever doubled."""
    out, prev, n = {}, None, 0
    for k in keys:
        if k in ('hero', 'stats'):
            continue
        if k == 'process' and direction != 'elegant':
            tone, n = 'section--primary', 1
        elif k == 'cta':
            tone, n = '', 0
        else:
            tone, n = ('section--tint', '')[n % 2], n + 1
        out[k] = tone + (' section--flush' if prev == tone else '')
        prev = tone
    return out


def _schema(c: dict) -> str:
    """schema.org LocalBusiness from the given facts only (a fact not given is not written)."""
    kind = c.get('schema_type', 'LocalBusiness')
    if not re.fullmatch(r'[A-Z][A-Za-z]+', kind):
        raise ValueError(f'schema_type {kind!r} is not a schema.org type name')
    data = {'@context': 'https://schema.org', '@type': kind, 'name': c['name'], 'description': c['description'],
            'telephone': c['phone']}
    for key, prop in (('email', 'email'), ('address', 'address'), ('hours', 'openingHours')):
        if c.get(key):
            data[prop] = c[key]
    raw = json.dumps(data, ensure_ascii=False).replace('<', '\\u003c')
    return f'<script type="application/ld+json">{raw}</script>'


def page(content: dict, contract: dict, order: list[str] | None = None) -> tuple[str, list[str]]:
    """(html, skipped section keys). `contract` is a G-APPLE contract (contract.build). `order` is the customer's own
    outline as section keys (the hero always opens the page); without it, ORDER. A missing required fact, an unknown
    section key or an unknown art direction raises; nothing is filled in silently."""
    c = content
    _need(c, REQUIRED, 'page')
    sequence = ORDER
    if order is not None:
        known = dict(ORDER)
        unknown = [k for k in order if k not in known]
        if unknown or len(set(order)) != len(order):
            raise ValueError(f'outline {order!r}: unknown or repeated sections {unknown}')
        keys = ['hero'] + [k for k in order if k != 'hero']
        sequence = tuple((k, known[k]) for k in keys) + tuple((k, f) for k, f in ORDER if k not in keys)
    direction = c['direction']
    if direction not in DIRECTIONS['directions']:
        raise ValueError(f'unknown art direction {direction!r}')
    rendered, skipped = [], []
    for key, fn in sequence:
        if (order is None or key in order or key == 'hero') and c.get(key) and (key != 'stats' or stats_shown(c)):
            rendered.append(key)
        else:
            skipped.append(key)
    # a number the panel already shows is said once; the strip's copy is left out and reported
    skipped += [f'stats:{v} (shown in the hero panel)' for v, _ in c.get('stats') or () if v == c['hero'].get('panel_figure')]
    tone = tones(rendered, direction)
    fns = dict(sequence)
    body = ''.join(hero(c, '', direction) if k == 'hero' else fns[k](c, tone.get(k, '')) for k in rendered)
    if not c['hero'].get('image'):
        # no hero photo: the page's first image is still the first one the browser meets -- it is not deferred
        body = body.replace(' loading="lazy"', ' loading="eager"', 1)
    head = (f'<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{e(c["title"])}</title><meta name="description" content="{ea(c["description"])}">'
            f'<meta property="og:title" content="{ea(c["title"])}"><meta property="og:description" content="{ea(c["description"])}">'
            f'<meta property="og:type" content="website"><meta property="og:locale" content="he_IL">'
            f'{font_links(contract)}<style>{contract["css"]}\n{CSS}</style>{_schema(c)}')
    single = any(n in contract['tokens'].get('--font-display', '') for n in DIRECTIONS['single_weight_display'])
    doc = (f'<!doctype html><html lang="he" dir="rtl"><head>{head}</head>'
           f'<body data-direction="{direction}" data-148-kit="section-library/{LIBRARY_VERSION}"'
           f'{" data-display-weight=regular" if single else ""}>'
           f'<a class="skip" href="#main">דלגו לתוכן</a>{header(c, rendered)}<main id="main">{body}</main>'
           f'{footer(c, rendered)}{mobile_bar(c)}{SCRIPT}</body></html>')
    from ..bidi_ranges import wrap_ranges        # "09:00–18:00" stays in its order on a right-to-left page
    return wrap_ranges(doc), skipped

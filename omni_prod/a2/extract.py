"""Deterministic extraction (task document step 5, spec section 5): structure, palette, type, hero, images, CTAs,
forms and in-page windows, measured from the rendered DOM by fixed selectors and rules. No model.

Taken: numbers, enums and colours of roles, read from computed styles. NOT taken: text, logos, images, code -- page
text is read only to classify a section (e.g. the words of an hours block), and is never stored.

Output: {'skeleton': <reference_card.schema.json skeleton>, 'extraction': <...#/$defs/extraction>}, both checked
against the card schema. Tone (closed list) is the one field left to a model (Gemini slice, step 12): it is absent
here, never guessed.
"""
from __future__ import annotations

import json
from functools import lru_cache

from pathlib import Path

CARD_SCHEMA = Path(__file__).resolve().parents[2] / 'docs' / 'spec' / 'reference_card.schema.json'

EXTRACTION_VERSION = 'x1'
SECTION_ENUM = ('nav', 'hero', 'trust', 'products', 'services', 'story', 'gallery', 'hours', 'location', 'contact',
                'cta', 'testimonials', 'faq', 'pricing_table', 'team', 'footer')
RATIOS = {'16:9': 16 / 9, '4:3': 4 / 3, '3:2': 3 / 2, '1:1': 1.0, '21:9': 21 / 9, '4:5': 4 / 5}
COLUMNS = (4, 6, 8, 12, 16)

# section words (he + en), read to classify a block, never stored
_SECTION_WORDS = {
    'hours': r'שעות|hours|opening',
    'location': r'כתובת|איך מגיעים|address|find us|location',
    'contact': r'צור קשר|צרו קשר|contact|התקשר|call us',
    'products': r'המוצרים|מוצרים|תפריט|products|menu|shop',
    'services': r'שירותים|services',
    'story': r'הסיפור|אודות|עלינו|about|our story',
    'gallery': r'גלריה|gallery',
    'testimonials': r'המלצות|לקוחות מספרים|testimonials|reviews',
    'faq': r'שאלות נפוצות|faq',
    'pricing_table': r'מחירון|pricing|price list',
    'team': r'הצוות|team',
    'trust': r'כשר|תעודה|certified|trusted|award',
}

_JS = r"""
(words) => {
  const vw = document.documentElement.clientWidth;
  const S = el => getComputedStyle(el);
  const box = el => el.getBoundingClientRect();
  const visible = el => { const r = box(el), s = S(el);
    return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden' && +s.opacity > 0; };
  const solid = c => c && !/rgba\([^)]*,\s*0\)$/.test(c) && c !== 'transparent';
  const body = document.body;
  // top-level blocks: header/nav/main children/section/footer, in page order
  let blocks = [];
  for (const el of body.querySelectorAll(':scope > *, :scope > main > *, :scope > div > section, :scope > div > header, :scope > div > footer')) {
    if (['SCRIPT','STYLE','NOSCRIPT','MAIN'].includes(el.tagName) || !visible(el)) continue;
    if (S(el).position === 'fixed') continue;
    if (box(el).height < 16) continue;
    blocks.push(el);
  }
  blocks = blocks.filter((el, i) => !blocks.some((o, j) => j !== i && o.contains(el)));
  const docTop = el => box(el).top + window.scrollY;
  blocks.sort((a, b) => docTop(a) - docTop(b));
  const textOf = el => (el.innerText || '').slice(0, 400).toLowerCase();
  const match = (el, key) => new RegExp(words[key], 'i').test(textOf(el.querySelector('h1,h2,h3') || el).slice(0, 120))
                           || new RegExp(words[key], 'i').test((el.id || '') + ' ' + (el.className || ''));
  const sections = [];
  let heroEl = null;
  blocks.forEach((el, i) => {
    let kind = null;
    if (el.tagName === 'NAV' || (el.tagName === 'HEADER' && el.querySelector('nav, a') && !el.querySelector('h1'))) kind = 'nav';
    else if (el.tagName === 'FOOTER') kind = 'footer';
    else if (!heroEl && el.querySelector('h1')) { kind = 'hero'; heroEl = el; }
    else for (const k of Object.keys(words)) { if (match(el, k)) { kind = k; break; } }
    if (!kind && el.querySelector('a[href^="tel:"], form')) kind = 'contact';
    if (!kind && el.querySelectorAll('img').length >= 4) kind = 'gallery';
    if (!kind && el.querySelector('a.cta, button, a[role=button]') && textOf(el).length < 160) kind = 'cta';
    sections.push({kind, top: docTop(el), height: box(el).height,
                   padTop: parseFloat(S(el).paddingTop) || 0, padBottom: parseFloat(S(el).paddingBottom) || 0});
  });
  // rhythm: section gaps = own vertical padding + the distance to the next block; inner gaps = margins between children
  const sectionGaps = sections.map((s, i) => {
    if (s.kind === 'nav' || s.kind === 'footer') return 0;      // the rhythm is between content sections
    const next = sections[i + 1];
    const between = next ? Math.max(0, next.top - (s.top + s.height)) : 0;
    return Math.round(s.padTop + between);
  }).filter(v => v > 0);
  const inner = [];
  for (const el of blocks) for (const kid of el.children) {
    const s = S(kid); const g = (parseFloat(s.marginTop) || 0) + (parseFloat(s.marginBottom) || 0);
    if (g > 0) inner.push(Math.round(g));
    const gap = parseFloat(S(el).rowGap); if (gap > 0) inner.push(Math.round(gap));
  }
  // type scale: font sizes of headings and body text actually shown
  const sizes = {};
  for (const el of body.querySelectorAll('h1,h2,h3,h4,p,li,a,span,td,th,button')) {
    if (!visible(el) || !(el.innerText || '').trim()) continue;
    const fs = Math.round(parseFloat(S(el).fontSize)); sizes[fs] = (sizes[fs] || 0) + 1;
  }
  // hero
  let hero = {type: 'none', image_ratio: 'none', headline_lines: 1, cta_count: 0, img: null};
  if (heroEl) {
    const h1 = heroEl.querySelector('h1');
    const range = document.createRange(); range.selectNodeContents(h1);          // lines = distinct rows of text boxes
    const rows = new Set([...range.getClientRects()].filter(r => r.width > 0).map(r => Math.round(r.top / 4)));
    hero.headline_lines = Math.max(1, Math.min(4, rows.size));
    const ctas = [...heroEl.querySelectorAll('a, button')].filter(b => visible(b) && solid(S(b).backgroundColor));
    hero.cta_count = Math.min(2, ctas.length);
    const media = [...heroEl.querySelectorAll('img, picture, video, [class*=ph], div')]
      .filter(m => visible(m) && (m.tagName === 'IMG' || m.tagName === 'VIDEO' || S(m).backgroundImage !== 'none'
                                   || (m.tagName === 'DIV' && !m.children.length && box(m).height > 120 && solid(S(m).backgroundColor))));
    const bg = S(heroEl).backgroundImage !== 'none';
    const m = media.sort((a, b) => box(b).width * box(b).height - box(a).width * box(a).height)[0];
    const hb = box(h1);
    if (bg) { hero.type = 'full_bleed'; const r = box(heroEl); hero.img = [r.width, r.height]; }
    else if (m) {
      const r = box(m); hero.img = [r.width, r.height];
      const sideBySide = Math.abs((r.top + r.height / 2) - (hb.top + hb.height / 2)) < Math.max(r.height, hb.height) / 2
                         && (r.right <= hb.left + 4 || r.left >= hb.right - 4);
      hero.type = r.width >= vw * 0.9 ? 'full_bleed' : sideBySide ? 'split' : 'stacked';
    } else {
      hero.type = S(h1).textAlign === 'center' || Math.abs((hb.left + hb.right) / 2 - vw / 2) < vw * 0.05 ? 'centered' : 'stacked';
    }
  }
  // palette by role, from computed styles weighted by area
  const area = {}; const add = (k, c, w) => { if (!solid(c)) return; area[k] = area[k] || {}; area[k][c] = (area[k][c] || 0) + w; };
  add('bg', S(body).backgroundColor, vw * 100000);
  add('bg', S(document.documentElement).backgroundColor, vw * 50000);
  const inWindow = el => { for (let e = el; e && e !== body; e = e.parentElement)
                            if (['fixed', 'sticky'].includes(S(e).position)) return true; return false; };
  for (const el of body.querySelectorAll('*')) {
    // the page's palette, not its windows (an age gate or a cookie banner has its own colours)
    if (!visible(el) || inWindow(el)) continue; const s = S(el), r = box(el), a = r.width * r.height;
    const fs = parseFloat(s.fontSize); const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (ownText && fs >= 15) add('text', s.color, (el.innerText || '').length);
    if (ownText && fs < 15) add('muted', s.color, (el.innerText || '').length);
    if (solid(s.borderTopColor) && parseFloat(s.borderTopWidth) > 0) add('line', s.borderTopColor, r.width);
    if (solid(s.borderBottomColor) && parseFloat(s.borderBottomWidth) > 0) add('line', s.borderBottomColor, r.width);
    const isCta = (el.tagName === 'A' || el.tagName === 'BUTTON') && solid(s.backgroundColor);
    if (isCta) { add('accent', s.backgroundColor, a); add('accent_text', s.color, a); }
    else if (solid(s.backgroundColor) && a < vw * 2000 && a > 2000 && (el.children.length || ownText)) add('surface', s.backgroundColor, a);
    else if (solid(s.backgroundColor) && a >= vw * 2000) add('bg', s.backgroundColor, a);
  }
  // CTAs
  const ctaEls = [...body.querySelectorAll('a, button')].filter(b => visible(b) && solid(S(b).backgroundColor));
  const radii = ctaEls.map(b => parseFloat(S(b).borderTopLeftRadius) || 0);
  // forms
  const forms = [...body.querySelectorAll('form')].filter(visible).map(f => ({
    fields: f.querySelectorAll('input:not([type=hidden]):not([type=submit]), select, textarea').length,
    types: [...new Set([...f.querySelectorAll('input')].map(i => (i.type || 'text').toLowerCase()))]}));
  // images
  const imgs = [...body.querySelectorAll('img, picture, svg, [style*="background-image"]')].filter(visible);
  const photos = imgs.filter(i => i.tagName === 'IMG' || i.tagName === 'PICTURE' || S(i).backgroundImage !== 'none');
  const svgs = imgs.filter(i => i.tagName === 'svg' || i.tagName === 'SVG');
  const fullBleed = photos.filter(i => box(i).width >= vw * 0.9).length;
  // components: in-page windows and widgets, by fixed DOM rules
  const fixed = [...body.querySelectorAll('*')].filter(e => visible(e) && ['fixed','sticky'].includes(S(e).position));
  const comp = new Set();
  const has = (sel) => !!body.querySelector(sel);
  const ftext = e => (e.innerText || '').toLowerCase();
  for (const e of fixed) {
    const r = box(e); const t = ftext(e);
    const cover = r.width * r.height >= vw * window.innerHeight * 0.5;
    if (/גיל|18|age|legal drinking/.test(t) && (cover || e.matches('dialog,[role=dialog]'))) comp.add('age_gate');
    else if (/עוגיות|cookie/.test(t)) comp.add('cookie_banner');
    else if (cover || e.matches('dialog,[role=dialog]')) comp.add('entry_popup');
    else if ((e.matches('a[href^="tel:"]') || e.querySelector('a[href^="tel:"]')) && r.width < vw * 0.5) comp.add('floating_call_button');
    else if (r.top <= 2 && r.height < 60 && !e.querySelector('nav')) comp.add('promo_bar');
    else if (/סל|cart|basket/.test(t) && (r.left > vw * 0.5 || r.right < vw * 0.5)) comp.add('cart_drawer');
    else if (/שאלה|chat|צ'אט|question/.test(t) && r.width < vw * 0.5) comp.add('question_widget');
  }
  for (const d of body.querySelectorAll('dialog, [role=dialog]')) {
    const t = ftext(d);
    if (/גיל|age/.test(t)) comp.add('age_gate'); else if (/עוגיות|cookie/.test(t)) comp.add('cookie_banner');
  }
  const nav = body.querySelector('nav');
  if (nav && nav.querySelectorAll('ul ul, [class*=mega], [class*=dropdown]').length) comp.add('mega_menu');
  if (body.querySelectorAll('[class*=chip], [role=tab]').length >= 3) comp.add('chips');
  if (has('iframe[src*="map"], [class*=map]')) comp.add('map_embed');
  if (has('form')) comp.add('form');
  if (has('table')) comp.add('table');
  // row count for columns: most side-by-side siblings in one row
  let row = 1;
  for (const el of body.querySelectorAll('ul, ol, div, section')) {
    const kids = [...el.children].filter(visible); if (kids.length < 2) continue;
    const tops = {}; kids.forEach(k => { const t = Math.round(box(k).top); tops[t] = (tops[t] || 0) + 1; });
    row = Math.max(row, ...Object.values(tops));
  }
  const dark = (() => {          // the hero's own background, else the first solid one above it, else the page's
    let el = heroEl || body;
    while (el && !solid(S(el).backgroundColor) && S(el).backgroundImage === 'none') el = el.parentElement;
    if (el && S(el).backgroundImage !== 'none' && !solid(S(el).backgroundColor)) return true;
    const c = ((el ? S(el).backgroundColor : 'rgb(255,255,255)').match(/\d+/g) || [255, 255, 255]).map(Number);
    return (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) < 90; })();
  return {sections, sectionGaps, inner, sizes, hero, area, radii, forms, photos: photos.length, svgs: svgs.length,
          fullBleed, components: [...comp], row, dark, vw,
          tel: has('a[href^="tel:"]'), stickyTel: fixed.some(e => e.matches('a[href^="tel:"]') || e.querySelector('a[href^="tel:"]')),
          hoursTable: [...body.querySelectorAll('table')].some(t => new RegExp(words.hours, 'i').test(ftext(t.closest('section') || t))),
          };
}
"""


@lru_cache(maxsize=1)
def _schema():
    return json.loads(CARD_SCHEMA.read_text(encoding='utf-8'))


def _check(sub: str, doc: dict) -> dict:
    from jsonschema import Draft202012Validator, FormatChecker
    schema = _schema()
    sub_schema = schema['properties'][sub] if sub == 'skeleton' else {**schema['$defs'][sub], '$defs': schema['$defs']}
    errors = list(Draft202012Validator(sub_schema, format_checker=FormatChecker()).iter_errors(doc))
    if errors:
        raise ValueError(f'{sub} outside reference_card.schema.json: {errors[0].message[:200]}')
    return doc


def _hex(css: str) -> str | None:
    import re
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)', css or '')
    if not m or (m.group(4) is not None and float(m.group(4)) < 0.99):
        return None
    return '#' + ''.join(f'{int(m.group(i)):02x}' for i in (1, 2, 3))


def _top(d: dict | None) -> tuple[str | None, float]:
    if not d:
        return None, 0.0
    total = sum(d.values())
    colour, weight = max(sorted(d.items()), key=lambda kv: kv[1])
    return _hex(colour), round(weight / total, 2) if total else 0.0


def _clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def from_measures(m: dict) -> dict:
    """Map raw DOM measures to the card's skeleton and the extraction block. Pure, so the rules are unit-tested."""
    order, seen = [], set()
    for s in m['sections']:
        k = s['kind']
        if k in SECTION_ENUM and k not in seen:
            order.append(k)
            seen.add(k)
    order = order[:12]
    gaps = sorted(g for g in m['sectionGaps'] if g > 0) or [16]
    inner = sorted(g for g in m['inner'] if g > 0) or [4]
    q = lambda xs, p: xs[min(len(xs) - 1, int(p * (len(xs) - 1) + 0.5))]
    sizes = sorted({_clamp(fs, 12, 96) for fs, n in m['sizes'].items() if int(fs) >= 12 and n >= 1}
                   if isinstance(m['sizes'], dict) else (), reverse=True)
    # the scale is the distinct sizes actually used, largest first, at most six (the smallest dropped first)
    scale = [int(s) for s in sizes][:6]
    hero = m['hero']
    ratio = 'none'
    if hero.get('img') and hero['img'][1] > 0:
        r = hero['img'][0] / hero['img'][1]
        ratio = min(RATIOS, key=lambda k: abs(RATIOS[k] - r))
    row = int(m['row'])
    columns = 4 if row <= 1 else 16 if row in (8, 16) else 12      # the grid the widest row fits
    traits = set()
    if hero.get('cta_count') == 1:
        traits.add('single_cta')
    if m.get('stickyTel'):
        traits.add('sticky_call_button')
    if m.get('hoursTable'):
        traits.add('hours_as_table')
    if 'map_embed' in m['components']:
        traits.add('map_embed')
    if m.get('fullBleed'):
        traits.add('large_photography')
    if m.get('svgs', 0) >= 3 and not m.get('photos'):
        traits.add('illustration')
    traits.add('dark_hero' if m.get('dark') else 'light_hero')
    skeleton = {'section_order': order,
                'hero': {'type': hero['type'], 'image_ratio': ratio,
                         'headline_lines': _clamp(hero['headline_lines'], 1, 4), 'cta_count': _clamp(hero['cta_count'], 0, 2)},
                'rhythm': {'section_gap_px': [_clamp(gaps[0], 16, 240), _clamp(gaps[-1], 16, 240)],
                           'inner_gap_px': [_clamp(q(inner, .25), 4, 64), _clamp(q(inner, .75), 4, 64)]},
                'type_scale_px': scale, 'columns': columns, 'traits': sorted(traits)}
    palette = {}
    for role in ('bg', 'surface', 'line', 'text', 'muted', 'accent', 'accent_text'):
        weights = dict(m['area'].get(role) or {})
        twin = {'muted': 'text', 'surface': 'bg'}.get(role)  # a second colour of its kind, never the first again
        if twin in palette:
            weights = {c: w for c, w in weights.items() if _hex(c) != palette[twin]['hex']}
        hexv, share = _top(weights)
        if hexv:
            palette[role] = {'hex': hexv, 'provenance': 'observed', 'confidence': share}
    radius = sorted(m['radii'])[len(m['radii']) // 2] if m['radii'] else None
    images = ('none' if not m.get('photos') and not m.get('svgs') else
              'illustration' if m.get('svgs', 0) > m.get('photos', 0) else
              'photo_full_bleed' if m.get('fullBleed') else 'photo_framed')
    extraction = {'extraction_version': EXTRACTION_VERSION, 'palette': palette,
                  'components': sorted(set(m['components'])), 'image_treatment': images,
                  'cta': {'count': len(m['radii']),
                          'shape': None if radius is None else 'pill' if radius >= 999 or radius >= 20 else
                          'rounded' if radius >= 4 else 'square'},
                  'forms': [{'fields': min(int(f['fields']), 30), 'types': sorted(t for t in f['types']
                             if t in ('text', 'tel', 'email', 'number', 'date', 'checkbox', 'radio', 'search'))[:8]}
                            for f in m['forms']][:5]}
    return {'skeleton': skeleton, 'extraction': extraction}


def extract(session, url: str, *, width: int = 1440) -> dict:
    """Open the page (offline session: only allowed hosts) and extract. Both parts are schema-checked."""
    with session.page(width=width, height=900) as page:
        page.goto(url, wait_until='load', timeout=15000)
        measures = page.evaluate(_JS, _SECTION_WORDS)
    out = from_measures(measures)
    _check('skeleton', out['skeleton'])
    _check('extraction', out['extraction'])
    return out

"""Visual quality engineering (Production Assurance v2 §6; issue #6 P1 "Visual QA").

For each viewport (desktop 1440x900, mobile 390x844 with touch) the product is
started inside the browser sandbox (no network, headless Chromium, the same
start contract as the preview), "/" is opened in its initial (empty) state and
a DOM audit runs. Findings are measured, never inferred from pixels alone:

  no_mobile_viewport mobile: no meta viewport, the phone shows the page zoomed out
  h_overflow        the page scrolls sideways (wider than the viewport)
  offscreen_control a button/link/field lies outside the viewport horizontally
  overlap           two visible controls cover each other
  clipped_text      text cut by its box (overflow hidden, content wider)
  small_touch       mobile: a control smaller than 24x24 CSS px (WCAG 2.2 AA 2.5.8)
  broken_image      an <img> that failed to load
  unnamed_control   a button/link with no accessible name
  unlabelled_field  a form field with no label / aria-label / title
  low_contrast      text below WCAG AA contrast (4.5:1, 3:1 for large text)
  tiny_text         mobile: text under 12px
  missing_lang      <html> has no lang
  rtl_mismatch      mostly-Hebrew page not rendered right-to-left
  positive_tabindex tabindex > 0 (breaks keyboard order)
  console_error     console error or uncaught exception on load

Visual plan S2 (2026-11-27): the same run also MEASURES how much picture the page has (`measures` per viewport) and four
advisory rules read the measures against one thresholds table (`visual_thresholds` in section_library/directions.json,
read from the platform, never from the built repository). They start at warn: they are in RULES (so the owner can
enforce them with OMNI_VISUAL_QA_ENFORCE) and not in DEFAULT_ENFORCED.
  no_picture               a business page with no picture of at least min_picture_px x min_picture_px
  small_hero_picture       the biggest picture that starts on the first screen is under the share of the screen
  text_on_picture          text over a picture below its contrast (pixels sampled with the text made transparent)
  long_run_without_picture a page with pictures that goes more than N screens without one

Since bld_cb2d1b90a90f430c98603d14f8afa1a8 (2026-11-24): no_mobile_viewport reads the meta tag itself -- a page that
overflows is zoomed out WITH one, and "no meta viewport" sent six repairs to the wrong place -- and h_overflow names the
element that sticks out furthest (tag, class, x range, size; not one inside a clipping box or a fixed one) and, on a
phone with a meta viewport, measures the page against the phone's own width.

Screenshots (JPEG) are returned for evidence and stored by the caller; they
are never sent to any third party. Only rules proven free of false positives on
stored working products block (DEFAULT_ENFORCED; OMNI_VISUAL_QA_ENFORCE
overrides, '' = shadow); the rest are recorded as advisories.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from .autonomous_core import AcceptanceFailure, ExecutionReport
from .browser_probe import BROWSER_PROFILE
from .sandbox_script import staged_script

VISUAL_FAILURE_ID = 'VISUAL'
VIEWPORTS = {'desktop': {'width': 1440, 'height': 900, 'mobile': False},
             'mobile': {'width': 390, 'height': 844, 'mobile': True}}
RULES = ('no_mobile_viewport', 'h_overflow', 'offscreen_control', 'overlap', 'clipped_text', 'small_touch', 'broken_image', 'unnamed_control',
         'unlabelled_field', 'low_contrast', 'tiny_text', 'missing_lang', 'rtl_mismatch', 'positive_tabindex',
         'console_error', 'no_picture', 'small_hero_picture', 'text_on_picture', 'long_run_without_picture')
PICTURE_RULES = ('no_picture', 'small_hero_picture', 'text_on_picture', 'long_run_without_picture')
THRESHOLDS_PATH = '.omni/_sandbox/visual_thresholds.json'          # staged next to the script; the script reads it

# Runs inside the sandbox; argv[1] = viewport name. Free of omni_prod imports.
SCRIPT = r'''
import base64, json, os, subprocess, sys, time, urllib.request
VIEW = {"desktop": (1440, 900, False), "mobile": (390, 844, True)}[sys.argv[1]]
c = json.load(open(".omni/project.json"))
port = int(c["port"])
env = dict(os.environ, PORT=str(port), HOME="/tmp", DATA_DIR="/tmp", PYTHONDONTWRITEBYTECODE="1")
srv = subprocess.Popen(c["start"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = "http://127.0.0.1:%d" % port
for _ in range(60):
    try:
        urllib.request.urlopen(base + c.get("health_path", "/"), timeout=2); break
    except Exception:
        time.sleep(0.5)
AUDIT = r"""(mobile) => {
  const F = [];
  const add = (kind, el, detail) => F.push({kind, detail: (detail || '').slice(0, 160),
      at: el ? (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : '')) : ''});
  const vw = window.innerWidth, vh = window.innerHeight;
  const vis = (el) => { const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05 && r.width > 0 && r.height > 0; };
  const doc = document.documentElement;
  const meta = document.querySelector('meta[name="viewport" i]');
  const metaOk = !!(meta && /width|initial-scale/i.test(meta.getAttribute('content') || ''));
  if (mobile && !metaOk) add('no_mobile_viewport', meta, (meta ? 'meta viewport "' + (meta.getAttribute('content') || '') + '" sets no width' : 'no meta viewport in the page') + ': the phone shows it zoomed out (layout width ' + vw + 'px on a ' + screen.width + 'px phone)');
  const limit = (mobile && metaOk) ? Math.min(vw, screen.width) : vw;
  if (doc.scrollWidth > limit + 2) {
    const sx = window.scrollX;
    const clipped = (el) => { for (let a = el; a && a !== document.body && a !== doc; a = a.parentElement) { const s = getComputedStyle(a);
      if (s.position === 'fixed') return true; if (a !== el && ['hidden', 'clip', 'auto', 'scroll'].includes(s.overflowX)) return true; } return false; };
    let worst = null, out = 0, box = null;
    const all = document.querySelectorAll('body *');
    for (let i = 0; i < all.length && i < 4000; i++) {
      const r = all[i].getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      const left = r.left + sx, right = r.right + sx, beyond = Math.max(right - limit, -left);
      if (beyond > out + 0.5 && !clipped(all[i])) { worst = all[i]; out = beyond; box = [left, right, r.width, r.height].map(Math.round); }
    }
    add('h_overflow', worst, 'page width ' + doc.scrollWidth + 'px > viewport ' + limit + 'px' + (box ? '; it sticks out at x ' + box[0] + '..' + box[1] + ' (' + box[2] + 'x' + box[3] + ')' : ''));
  }
  if (!doc.getAttribute('lang')) add('missing_lang', doc, '');
  const text = document.body ? document.body.innerText : '';
  const heb = (text.match(/[֐-׿]/g) || []).length, lat = (text.match(/[A-Za-z]/g) || []).length;
  if (heb > 20 && heb > lat && getComputedStyle(document.body).direction !== 'rtl') add('rtl_mismatch', document.body, 'Hebrew text rendered ' + getComputedStyle(document.body).direction);
  const controls = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button]')].filter(vis);
  for (const el of controls) {
    const r = el.getBoundingClientRect();
    if (r.right > vw + 2 || r.left < -2) add('offscreen_control', el, 'x ' + Math.round(r.left) + '..' + Math.round(r.right));
    if (mobile && (r.width < 24 || r.height < 24) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
      add('small_touch', el, Math.round(r.width) + 'x' + Math.round(r.height));
    const name = (el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('aria-labelledby') || '').trim();
    if ((el.tagName === 'BUTTON' || el.tagName === 'A' || el.getAttribute('role') === 'button') && !name && !(el.innerText || '').trim()
        && !el.querySelector('img[alt]:not([alt=""]), svg title')) add('unnamed_control', el, '');
    if (['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) && !['submit', 'button', 'reset', 'image'].includes(el.type)) {
      const labelled = name || el.closest('label') || (el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]'));
      if (!labelled) add('unlabelled_field', el, el.getAttribute('placeholder') ? 'placeholder only' : '');
    }
    if (parseInt(el.getAttribute('tabindex') || '0', 10) > 0) add('positive_tabindex', el, el.getAttribute('tabindex'));
  }
  const boxes = controls.slice(0, 80).map(el => [el, el.getBoundingClientRect()]);
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const [a, ra] = boxes[i], [b, rb] = boxes[j];
    if (a.contains(b) || b.contains(a)) continue;
    const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left), h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
    if (w > 4 && h > 4) add('overlap', a, 'overlaps ' + b.tagName.toLowerCase() + ' by ' + Math.round(w) + 'x' + Math.round(h));
  }
  for (const img of document.querySelectorAll('img')) if (img.complete && img.naturalWidth === 0 && vis(img)) add('broken_image', img, img.getAttribute('src') || '');
  const lum = (c) => { const m = c.match(/[\d.]+/g); if (!m) return null; const [r, g, b] = m.slice(0, 3).map(v => { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const alpha = (c) => { const m = c.match(/[\d.]+/g); return m && m.length > 3 ? parseFloat(m[3]) : 1; };
  const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== 'none') return null; if (alpha(s.backgroundColor) > 0.9) return s.backgroundColor; } return 'rgb(255, 255, 255)'; };
  let checked = 0;
  for (const el of document.querySelectorAll('body *')) {
    if (checked > 300) break;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!own || !vis(el)) continue;
    checked++;
    const s = getComputedStyle(el), size = parseFloat(s.fontSize), bold = parseInt(s.fontWeight, 10) >= 700;
    if (mobile && size < 12) add('tiny_text', el, size + 'px');
    if (el.scrollWidth > el.clientWidth + 2 && ['hidden', 'clip'].includes(s.overflowX) && el.children.length === 0) add('clipped_text', el, el.innerText.slice(0, 60));
    const bg = bgOf(el); if (!bg) continue;
    const L1 = lum(s.color), L2 = lum(bg); if (L1 === null || L2 === null || alpha(s.color) < 0.5) continue;
    const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const need = (size >= 24 || (bold && size >= 18.66)) ? 3 : 4.5;
    if (ratio < need) add('low_contrast', el, ratio.toFixed(2) + ':1 (needs ' + need + ')');
  }
  return {findings: F, text_elements: checked, controls: controls.length, scroll_width: doc.scrollWidth};
}"""
# Visual plan S2: how much picture the page has, measured where the audit already opened it. Pictures are what a visitor
# sees as a picture: <img>, <video> and elements with a CSS background url(), at least THRESH["min_picture_px"] each way
# (an icon is not one). Free of omni_prod imports like the rest of the script.
MEASURE = r"""(cfg) => {
  const vw = window.innerWidth, vh = window.innerHeight, doc = document.documentElement, sx = window.scrollX, sy = window.scrollY;
  const pageH = Math.max(doc.scrollHeight, document.body ? document.body.scrollHeight : 0, vh);
  const vis = (el) => { const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity || '1') > 0.05 && r.width > 0 && r.height > 0; };
  const box = (el) => { const r = el.getBoundingClientRect(); return {l: r.left + sx, t: r.top + sy, r: r.right + sx, b: r.bottom + sy}; };
  const area = (p) => Math.max(0, p.r - p.l) * Math.max(0, p.b - p.t);
  const clip = (p, x0, y0, x1, y1) => ({l: Math.max(p.l, x0), t: Math.max(p.t, y0), r: Math.min(p.r, x1), b: Math.min(p.b, y1)});
  const union = (rs) => { rs = rs.filter(r => area(r) > 0);
    const xs = [...new Set(rs.flatMap(r => [r.l, r.r]))].sort((a, b) => a - b); let total = 0;
    for (let i = 0; i + 1 < xs.length; i++) { const x0 = xs[i], x1 = xs[i + 1];
      const iv = rs.filter(r => r.l <= x0 && r.r >= x1).map(r => [r.t, r.b]).sort((a, b) => a[0] - b[0]);
      let cur = null, len = 0;
      for (const [a, b] of iv) { if (!cur || a > cur[1]) { if (cur) len += cur[1] - cur[0]; cur = [a, b]; } else cur[1] = Math.max(cur[1], b); }
      if (cur) len += cur[1] - cur[0]; total += len * (x1 - x0); }
    return total; };
  const pics = [];
  const add = (el, kind) => { if (!vis(el)) return; const r = box(el);
    if (r.r - r.l < cfg.min_picture_px || r.b - r.t < cfg.min_picture_px) return; pics.push(Object.assign({el, kind}, r)); };
  for (const el of document.querySelectorAll('img, video')) if (!(el.tagName === 'IMG' && el.complete && el.naturalWidth === 0)) add(el, el.tagName.toLowerCase());
  const all = document.querySelectorAll('body *');
  for (let i = 0; i < all.length && i < 4000; i++) { const bi = getComputedStyle(all[i]).backgroundImage; if (bi && /url\(/.test(bi)) add(all[i], 'background'); }
  const shot = (p) => clip(p, 0, 0, vw, vh);
  const heroArea = Math.max(0, ...pics.filter(p => p.t < vh).map(p => area(shot(p))));
  const ivs = pics.map(p => [Math.max(0, p.t), Math.min(pageH, p.b)]).filter(i => i[1] > i[0]).sort((a, b) => a[0] - b[0]);
  let longest = 0, cursor = 0;
  for (const [a, b] of ivs) { longest = Math.max(longest, a - cursor); cursor = Math.max(cursor, b); }
  longest = Math.max(longest, pageH - cursor);
  // what a section is made of: how many columns its blocks stand in, whether it holds a picture, whether that picture
  // reaches the edge of the screen. Columns are the merged horizontal extents of its blocks (never the text's own width).
  const sigs = [];
  for (const sec of document.querySelectorAll('main > section, body > section')) {
    if (!vis(sec)) continue;
    const sr = box(sec), inside = pics.filter(p => area(clip(p, sr.l, sr.t, sr.r, sr.b)) >= 0.5 * area(p));
    const spans = [...sec.querySelectorAll('h1, h2, h3, p, li, dt, dd, img, figure, blockquote, summary, form')].filter(vis)
      .map(el => box(el)).filter(b => b.r - b.l > 8).map(b => [b.l, b.r]).sort((a, b) => a[0] - b[0]);
    const cols = []; for (const [a, b] of spans) { const last = cols[cols.length - 1]; if (last && a < last[1] + 8) last[1] = Math.max(last[1], b); else cols.push([a, b]); }
    const bleed = inside.some(p => p.l <= 1 || p.r >= vw - 1);
    sigs.push(Math.min(cols.length, 4) + '|' + (inside.length ? 'pic' : 'text') + '|' + (bleed ? 'bleed' : 'boxed'));
  }
  const canvas = document.createElement('canvas').getContext('2d');
  const rgb = (c) => { canvas.fillStyle = '#000'; canvas.fillStyle = c; canvas.fillRect(0, 0, 1, 1); const d = canvas.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2]]; };
  const candidates = [];
  if (pics.length) for (const el of document.querySelectorAll('body *')) {
    if (candidates.length >= 40) break;
    const nodes = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim());
    if (!nodes.length || !vis(el)) continue;
    const s = getComputedStyle(el), am = s.color.match(/[\d.]+/g);
    if (am && am.length > 3 && parseFloat(am[3]) < 0.5) continue;
    const rects = [];
    for (const n of nodes) { const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) { const b = {l: r.left + sx, t: r.top + sy, r: r.right + sx, b: r.bottom + sy};
        if (area(b) > 0 && b.b <= 15000 && pics.some(p => area(clip(b, p.l, p.t, p.r, p.b)) >= 0.25 * area(b))) rects.push([b.l, b.t, b.r, b.b]); } }
    if (!rects.length) continue;
    const size = parseFloat(s.fontSize), bold = parseInt(s.fontWeight, 10) >= 700;
    candidates.push({at: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/)[0] : ''),
                     rects: rects.slice(0, 6), colour: rgb(s.color), large: size >= 24 || (bold && size >= 18.66)});
  }
  const contact = !!document.querySelector('a[href^="tel:" i], a[href^="mailto:" i], a[href*="wa.me"], a[href*="whatsapp"], a[href="#contact"]');
  return {measures: {pictures: pics.length, hero_picture_share: +(heroArea / (vw * vh)).toFixed(3),
            first_screen_picture_share: +(union(pics.map(shot)) / (vw * vh)).toFixed(3),
            page_picture_share: +(union(pics.map(p => clip(p, 0, 0, vw, pageH))) / (vw * pageH)).toFixed(3),
            longest_run_without_picture: +(longest / vh).toFixed(2), page_height: Math.round(pageH),
            compositions: new Set(sigs).size, composition_sections: sigs.length, composition_signatures: [...new Set(sigs)].sort(),
            scope: {kit: !!document.querySelector('[data-148-kit]'), contact}},
          candidates};
}"""
# Text over a picture: the rendered pixels under each text box, with the text itself made transparent by the caller, are
# decoded in the page (PNG -> canvas) and the worst contrast of the text colour against the lightest and the darkest pixel
# under each box is returned. What the visitor sees is sampled -- a scrim, an overlay and the picture together.
PIXELS = r"""async (arg) => {
  const bin = atob(arg.png), bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const bmp = await createImageBitmap(new Blob([bytes], {type: 'image/png'}));
  const cv = document.createElement('canvas'); cv.width = bmp.width; cv.height = bmp.height;
  const g = cv.getContext('2d', {willReadFrequently: true}); g.drawImage(bmp, 0, 0);
  const lin = new Float64Array(256); for (let i = 0; i < 256; i++) { const v = i / 255; lin[i] = v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  const lum = (r, gg, b) => 0.2126 * lin[r] + 0.7152 * lin[gg] + 0.0722 * lin[b];
  const out = [];
  for (const c of arg.boxes) {
    let lo = 2, hi = -1;
    for (const [l, t, r, b] of c.rects) {
      const x = Math.max(0, Math.floor(l)), y = Math.max(0, Math.floor(t)), w = Math.min(bmp.width - x, Math.ceil(r - l) + 1), h = Math.min(bmp.height - y, Math.ceil(b - t) + 1);
      if (w <= 0 || h <= 0) continue;
      const d = g.getImageData(x, y, w, h).data, step = Math.max(1, Math.floor(Math.sqrt(w * h / 20000))) * 4;
      for (let i = 0; i < d.length; i += step) { const L = lum(d[i], d[i + 1], d[i + 2]); if (L < lo) lo = L; if (L > hi) hi = L; }
    }
    if (hi < 0) continue;
    const lt = lum(c.colour[0], c.colour[1], c.colour[2]);
    const ratio = (a, b) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    out.push({at: c.at, ratio: +Math.min(ratio(lt, lo), ratio(lt, hi)).toFixed(2), large: c.large});
  }
  return out;
}"""
THRESH = json.load(open(".omni/_sandbox/visual_thresholds.json"))
out = {"viewport": sys.argv[1], "console": [], "findings": [], "screenshot": None}
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("OMNI_CHROMIUM", "/usr/bin/chromium"),
                          args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    ctx = b.new_context(viewport={"width": VIEW[0], "height": VIEW[1]}, is_mobile=VIEW[2], has_touch=VIEW[2],
                        device_scale_factor=1, locale="he-IL")
    page = ctx.new_page()
    # "Failed to load resource" console lines are replaced by the exact failed
    # request below; the browser's own /favicon.ico probe is not the product's.
    page.on("console", lambda m: m.type == "error" and not m.text.startswith("Failed to load resource")
            and out["console"].append(m.text[:200]))
    def on_resp(r):
        if r.status >= 400 and r.url.startswith(base) and not r.url.split("?")[0].endswith("/favicon.ico"):
            out["console"].append(("%s %s -> %s" % (r.request.method, r.url[len(base):], r.status))[:200])
    page.on("response", on_resp)
    page.on("pageerror", lambda e: out["console"].append(("uncaught: " + str(e))[:200]))
    page.goto(base + "/", wait_until="load", timeout=15000)
    page.wait_for_timeout(1200)
    audit = page.evaluate(AUDIT, VIEW[2])
    out.update(audit)
    measured = page.evaluate(MEASURE, THRESH)
    out["measures"] = measured["measures"]
    for q in (50, 30, 15):
        shot = page.screenshot(type="jpeg", quality=q, full_page=False)
        if len(shot) * 4 // 3 < 70000:
            out["screenshot"] = base64.b64encode(shot).decode()
            break
    # after the evidence screenshot: the text is made transparent, so the pixels under it can be read
    out["measures"]["text_on_picture"] = []
    if measured["candidates"]:
        page.add_style_tag(content="* { color: transparent !important; text-shadow: none !important; -webkit-text-fill-color: transparent !important; }")
        page.wait_for_timeout(100)
        height = min(int(out["measures"]["page_height"]), 15000)
        png = page.screenshot(type="png", full_page=True, clip={"x": 0, "y": 0, "width": VIEW[0], "height": height})
        out["measures"]["text_on_picture"] = page.evaluate(PIXELS, {"png": base64.b64encode(png).decode(), "boxes": measured["candidates"]})[:40]
    b.close()
srv.terminate()
for e in out["console"][:5]:
    out["findings"].append({"kind": "console_error", "detail": e, "at": ""})
shot = out.pop("screenshot")
if shot:
    print("OMNI_VISUAL_SHOT " + shot)
print("OMNI_VISUAL_QA " + json.dumps(out, ensure_ascii=False))
'''


def parse(stdout: str) -> tuple[dict | None, bytes | None]:
    report, shot = None, None
    for line in str(stdout).splitlines():
        if line.startswith('OMNI_VISUAL_QA '):
            try:
                report = json.loads(line[len('OMNI_VISUAL_QA '):])
            except ValueError:
                report = None
        elif line.startswith('OMNI_VISUAL_SHOT '):
            try:
                shot = base64.b64decode(line[len('OMNI_VISUAL_SHOT '):], validate=True)
            except (ValueError, base64.binascii.Error):
                shot = None
    return report, shot


# Enforced by default: layout rules with 0 findings on the 5 working stored
# products x 2 viewports (verify-replay 38082307056) -- no false positives.
# Contrast/labels found real WCAG defects in 3 of 5 working products; they stay
# advisory until the founder decides the cost/quality trade-off.
DEFAULT_ENFORCED = ('no_mobile_viewport', 'h_overflow', 'offscreen_control', 'overlap', 'broken_image')


def enforced_rules() -> set[str]:
    raw = os.getenv('OMNI_VISUAL_QA_ENFORCE')
    if raw is None:
        return set(DEFAULT_ENFORCED)
    return {r.strip() for r in raw.split(',') if r.strip() in RULES}


# ---- the picture rules (visual plan S2) -----------------------------------------------------------------------------
THRESHOLDS_FILE = Path(__file__).resolve().parent / 'section_library' / 'directions.json'
_VIEWS = tuple(VIEWPORTS)
_SHAPE = {'measure': {'min_picture_px': 'number'},
          'no_picture': {},
          'small_hero_picture': {'hero_picture_share_min': 'per_viewport'},
          'text_on_picture': {'normal': 'number', 'large': 'number'},
          'long_run_without_picture': {'min_pictures': 'number', 'max_viewport_heights': 'per_viewport'}}


def visual_thresholds(path: Path | None = None) -> dict:
    """The one thresholds table of the picture rules (directions.json, key `visual_thresholds`), read from the platform
    at run time -- never from the repository under test (CLAUDE.md section 4). A missing table, a missing key, an unknown
    rule name or a value that is not a positive number raises: a rule with no threshold is not judged by a default."""
    data = json.loads((path or THRESHOLDS_FILE).read_text(encoding='utf-8'))
    table = data.get('visual_thresholds')
    if not isinstance(table, dict):
        raise ValueError('directions.json has no visual_thresholds table')
    unknown = sorted(set(table) - set(_SHAPE) - {'_about'})
    if unknown:
        raise ValueError(f'visual_thresholds names rules this module does not have: {unknown}; it has {sorted(_SHAPE)}')
    out = {}
    for rule, keys in _SHAPE.items():
        if rule not in table:
            raise ValueError(f'visual_thresholds has no entry for {rule!r}')
        entry = table[rule]
        if not isinstance(entry, dict) or set(entry) != set(keys):
            raise ValueError(f'visual_thresholds[{rule!r}] must have exactly the keys {sorted(keys)}, not {sorted(entry) if isinstance(entry, dict) else entry!r}')
        for key, kind in keys.items():
            values = entry[key] if kind == 'per_viewport' else {None: entry[key]}
            if kind == 'per_viewport' and (not isinstance(values, dict) or set(values) != set(_VIEWS)):
                raise ValueError(f'visual_thresholds[{rule!r}][{key!r}] must have exactly the viewports {list(_VIEWS)}')
            for v in values.values():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
                    raise ValueError(f'visual_thresholds[{rule!r}][{key!r}] must be a positive number, not {v!r}')
        out[rule] = entry
    return out


def threshold_file_text(table: dict) -> str:
    """What the in-sandbox script reads from THRESHOLDS_PATH: only the number it measures with. The rules' thresholds
    stay on the platform side (picture_rules)."""
    return json.dumps({'min_picture_px': table['measure']['min_picture_px']})


def picture_rules(measures: dict, viewport: str, table: dict) -> list[dict]:
    """The picture findings of one viewport's measures. A business page (the library's body marker or a contact action) is
    judged by the layout rules; text over a picture is judged on every page."""
    f: list[dict] = []
    scope = measures.get('scope') or {}
    business = bool(scope.get('kit') or scope.get('contact'))
    pics = int(measures.get('pictures') or 0)
    if business and pics == 0:
        px = int(table['measure']['min_picture_px'])
        f.append({'kind': 'no_picture', 'at': '', 'detail': f'no picture of at least {px}x{px} px on the page'})
    need = table['small_hero_picture']['hero_picture_share_min'][viewport]
    if business and pics and measures.get('hero_picture_share', 0) < need:
        f.append({'kind': 'small_hero_picture', 'at': '',
                  'detail': f"the biggest picture on the first screen covers {measures.get('hero_picture_share', 0):.2f} of it (needs {need})"})
    top = table['text_on_picture']
    for t in measures.get('text_on_picture') or ():
        floor = top['large'] if t.get('large') else top['normal']
        if t['ratio'] < floor:
            f.append({'kind': 'text_on_picture', 'at': str(t.get('at', '')), 'detail': f"{t['ratio']}:1 over a picture (needs {floor})"})
    run = table['long_run_without_picture']
    if business and pics >= run['min_pictures'] and measures.get('longest_run_without_picture', 0) > run['max_viewport_heights'][viewport]:
        f.append({'kind': 'long_run_without_picture', 'at': '',
                  'detail': f"{measures['longest_run_without_picture']} screens without a picture (at most {run['max_viewport_heights'][viewport]})"})
    return f


class VisualQAExecutor:
    """Runs after the inner chain passed. Records per-viewport findings and
    screenshots (`last_visual`; screenshots go to `screenshot_sink(viewport,
    jpeg_bytes) -> key` when set). Blocks only on rules listed in
    OMNI_VISUAL_QA_ENFORCE (shadow mode otherwise)."""

    def __init__(self, inner, *, enabled: bool = True):
        self._inner = inner
        self._enabled = enabled
        self.screenshot_sink = None
        self.design_critic = None          # design_review.DesignCritic, installed per build (2026-11-09)
        self.last_shots = None             # {viewport: screenshot bytes} of the last check (G-APPLE's reviewers read them)
        self.last_visual: dict | None = None
        self.visual_rounds: list[dict] = []

    def __getattr__(self, item):
        return getattr(self._inner, item)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        if not report.passed:
            return report
        return self.check(repository=repository, spec=spec, report=report)

    def check(self, *, repository, spec, report):
        """This stage's own check on a report in which everything before it passed (VerificationGroup runs it
        directly; execute() keeps the standalone short-circuit)."""
        if not self._enabled:
            return report
        from .verification_verdict import no_checks, reraise_control, unverified
        run = getattr(self._inner, '_run', None)
        if not callable(run):
            self.last_visual = {'status': 'NOT_RUN', 'reason': 'no sandbox runner'}
            return unverified(VISUAL_FAILURE_ID, 'no sandbox runner', report.build_log)        # T4: never a pass
        viewports, status, shots = {}, 'PASS', {}
        table = visual_thresholds()                    # a broken table stops the check loudly, before any run
        for name in VIEWPORTS:
            try:
                staged, argv = staged_script(repository, 'visual_qa', SCRIPT, name)
                staged[THRESHOLDS_PATH] = threshold_file_text(table)
                result = run(staged, argv, f'visual-{name}', profile=BROWSER_PROFILE)
            except Exception as exc:
                reraise_control(exc)                   # T4: cancel / ledger / budget stop the build
                viewports[name] = {'status': 'NOT_RUN', 'reason': f'{type(exc).__name__}: {exc}'[:200]}
                status = 'NOT_RUN'
                continue
            data, shot = parse(result.get('stdout', ''))
            if data is not None and not (isinstance(data, dict) and isinstance(data.get('findings'), list)):
                viewports[name] = {'status': 'NOT_RUN', 'reason': 'malformed visual report'}   # T4: schema first
                status = 'NOT_RUN'
                continue
            if data is not None and int(result.get('returncode', 0) or 0) != 0:
                viewports[name] = {'status': 'NOT_RUN', 'reason': f"visual QA exited {result.get('returncode')}"}
                status = 'NOT_RUN'
                continue
            if data is None:
                viewports[name] = {'status': 'NOT_RUN', 'reason': 'no visual report',
                                   'tail': (str(result.get('stdout', '')) + str(result.get('stderr', '')))[-300:]}
                status = 'NOT_RUN'
                continue
            measures = data.get('measures')
            findings = list(data['findings']) + (picture_rules(measures, name, table) if isinstance(measures, dict) else [])
            entry = {'status': 'PASS' if not findings else 'FINDINGS', 'findings': findings[:40],
                     'counts': _counts(findings), 'controls': data.get('controls'),
                     'text_elements': data.get('text_elements'), 'screenshot_bytes': len(shot) if shot else 0,
                     'measures': measures}
            if shot:
                shots[name] = shot
            if shot and self.screenshot_sink is not None:
                try:
                    entry['screenshot_key'] = self.screenshot_sink(name, shot)
                except Exception as exc:  # evidence storage must not change the outcome
                    entry['screenshot_error'] = type(exc).__name__
            viewports[name] = entry
        enforce = enforced_rules()
        self.last_shots = dict(shots)
        blocking = [(v, f) for v, e in viewports.items() for f in e.get('findings', []) if f['kind'] in enforce]
        if status == 'NOT_RUN' and not blocking:       # T4: a viewport that was not inspected verified nothing
            self.last_visual = {'status': 'NOT_RUN', 'mode': 'enforce' if enforce else 'shadow', 'viewports': viewports}
            self.visual_rounds.append({'status': 'NOT_RUN', 'counts': {}})
            why = '; '.join(f"{v}: {e.get('reason')}" for v, e in viewports.items() if e.get('status') == 'NOT_RUN')
            return unverified(VISUAL_FAILURE_ID, why, report.build_log)
        inspected = sum(int(e.get('controls') or 0) + int(e.get('text_elements') or 0) for e in viewports.values())
        if not blocking and inspected == 0 and not any(e.get('findings') for e in viewports.values()):
            self.last_visual = {'status': 'NO_CHECKS', 'mode': 'enforce' if enforce else 'shadow', 'viewports': viewports}
            self.visual_rounds.append({'status': 'NO_CHECKS', 'counts': {}})
            return no_checks(VISUAL_FAILURE_ID, 'no control and no text element was inspected', report.build_log)
        if status == 'PASS' and any(e.get('findings') for e in viewports.values()):
            status = 'FINDINGS'
        self.last_visual = {'status': 'FAIL' if blocking else status, 'mode': 'enforce' if enforce else 'shadow',
                            'enforced_rules': sorted(enforce), 'viewports': viewports}
        self.visual_rounds.append({'status': self.last_visual['status'],
                                   'counts': {v: e.get('counts', {}) for v, e in viewports.items()}})
        if not blocking:
            critic = self.design_critic
            if critic is not None:
                try:
                    review = critic.review(spec=spec, shots=shots)
                    self.last_visual['design_review'] = review
                    polish = critic.failures(review)
                except Exception as exc:          # the critic never decides a build by crashing
                    self.last_visual['design_review'] = {'status': 'NOT_RUN', 'reason': type(exc).__name__}
                    polish = ()
                if polish:
                    return ExecutionReport(False, polish, report.build_log)
            return report
        failures = tuple(AcceptanceFailure(VISUAL_FAILURE_ID, f"visual ({v}) {f['kind']}: {f['at']} {f['detail']}".strip(),
                                           'Fix the layout so it works on desktop (1440x900) and mobile (390x844).')
                         for v, f in blocking[:8])
        return ExecutionReport(False, failures, report.build_log)


def _counts(findings) -> dict:
    out: dict[str, int] = {}
    for f in findings:
        out[f['kind']] = out.get(f['kind'], 0) + 1
    return out

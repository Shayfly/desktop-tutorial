// Checks for the colour decision card prototype (Michael 2026-11-14): the Chromium accessibility tree (what a screen
// reader receives), keyboard (arrows move focus and never decide), DC-01 (>= 7:1 on every text node, light and
// dark), 16px and 48px floors, reduced motion, largest text. Runs the real .dc.html with the Design runtime:
//   node colour_card_check.cjs <dir with Main.dc.html, Dark.dc.html, support.js> <out dir>
// Not wired into CI: the card is a prototype, not product code yet.
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const dir = process.argv[2], out = process.argv[3];
const res = []; const ok = (name, pass, detail) => { res.push({ name, pass, detail }); console.log(`${pass ? 'PASS' : 'FAIL'} ${name}${detail ? ' — ' + detail : ''}`); };
const srv = http.createServer((q, r) => { const f = path.join(dir, decodeURIComponent(q.url.split('?')[0])); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, {'content-type': f.endsWith('.js') ? 'text/javascript' : 'text/html; charset=utf-8'}); fs.createReadStream(f).pipe(r); }).listen(0, async () => {
  const base = `http://127.0.0.1:${srv.address().port}`;
  const b = await chromium.launch();
  async function open(file, opts = {}) { const p = await b.newPage({ viewport: { width: 390, height: 844 }, ...opts }); const errs = []; p.on('pageerror', e => errs.push(e.message)); await p.goto(`${base}/${file}`); await p.locator('[role=radio]').first().waitFor(); p._errs = errs; return p; }
  const focusInfo = p => p.evaluate(() => { const a = document.activeElement; return { role: a.getAttribute('role'), text: (a.innerText || a.value || '').split('\n')[0].trim(), checked: a.getAttribute('aria-checked') }; });
  const checkedAll = p => p.$$eval('[role=radio]', els => els.map(e => e.getAttribute('aria-checked')).join(','));

  // ---------- screen reader view (Chromium accessibility tree: what NVDA/VoiceOver/TalkBack receive) ----------
  let p = await open('Main.dc.html');
  const cdp = await p.context().newCDPSession(p);
  const { nodes } = await cdp.send('Accessibility.getFullAXTree');
  const byId = new Map(nodes.map(n => [n.nodeId, n]));
  const val = (n, k) => n[k] && n[k].value;
  const prop = (n, k) => { const x = (n.properties || []).find(q => q.name === k); return x && x.value && x.value.value; };
  const lines = [], radios = [];
  (function walk(id, d) { const n = byId.get(id); if (!n) return; let dd = d;
    const role = val(n, 'role'), name = val(n, 'name'), desc = val(n, 'description');
    if (!n.ignored && role && !['generic', 'none', 'InlineTextBox', 'StaticText', 'LineBreak'].includes(role)) {
      const checked = prop(n, 'checked'); const focusable = prop(n, 'focusable');
      lines.push('  '.repeat(d) + [role, name ? `"${name}"` : '', desc ? `תיאור="${desc}"` : '', checked !== undefined ? `checked=${checked}` : ''].filter(Boolean).join(' '));
      if (role === 'radio') radios.push({ name, description: desc, checked });
      dd = d + 1; }
    (n.childIds || []).forEach(c => walk(c, dd)); })(nodes[0].nodeId, 0);
  fs.writeFileSync(path.join(out, 'a11y-tree.txt'), lines.join('\n')); console.log(lines.join('\n'));
  ok('two radios with short names', radios.length === 2 && radios.every(r => r.name && r.name.length < 50), radios.map(r => r.name).join(' | '));
  ok('the palette radio describes the area split, as sentences', /שמנת לרקע: בערך 70% מהדף\./.test(radios[0]?.description || ''), radios[0]?.description);
  ok('each option says its own outcome', /אם תבחרו בצבעים שכתבתם/.test(radios[0]?.description || '') && /אם תבקשו שנבחר עבורכם/.test(radios[1]?.description || ''), radios[1]?.description);
  const group = await p.$eval('section[role=group]', s => document.getElementById(s.getAttribute('aria-labelledby')).innerText.trim());
  ok('card is a group named by its title', group === 'צבעי האתר', group);
  const rg = await p.$eval('[role=radiogroup]', s => document.getElementById(s.getAttribute('aria-labelledby')).innerText.trim());
  ok('radiogroup is named by the question', rg === 'אלה הצבעים לאתר?', rg);

  // ---------- keyboard: arrows move focus, never decide ----------
  const tabbable = await p.$$eval('[role=radio]', els => els.map(e => e.tabIndex).join(','));
  ok('one tab stop in the group (roving tabindex)', tabbable === '0,-1', tabbable);
  await p.locator('#msg').focus(); let hops = 0; let f = await focusInfo(p);
  while (f.role !== 'radio' && hops < 12) { await p.keyboard.press('Shift+Tab'); f = await focusInfo(p); hops++; }
  ok('Tab reaches the first option', f.role === 'radio' && /כמו שכתבתם/.test(f.text), f.text);
  await p.keyboard.press('ArrowDown'); f = await focusInfo(p);
  ok('ArrowDown moves focus to the next option', /בחרו עבורי/.test(f.text), f.text);
  const cons = (await p.locator('section[role=group] p').first().innerText()).trim();
  ok('the outcome line follows the focused option', /^אם תבקשו שנבחר עבורכם/.test(cons), cons);
  ok('...without choosing', (await checkedAll(p)) === 'false,false' && await p.locator('section[role=group]').count() === 1, await checkedAll(p));
  await p.keyboard.press('ArrowDown'); f = await focusInfo(p); ok('ArrowDown wraps to the first', /כמו שכתבתם/.test(f.text), f.text);
  await p.keyboard.press('ArrowLeft'); f = await focusInfo(p); ok('ArrowLeft (RTL: forward) moves too', /בחרו עבורי/.test(f.text), f.text);
  await p.keyboard.press('Home'); f = await focusInfo(p); ok('Home → first', /כמו שכתבתם/.test(f.text), f.text);
  await p.keyboard.press('End'); f = await focusInfo(p); ok('End → last', /בחרו עבורי/.test(f.text), f.text);
  ok('nothing chosen after six arrow presses', (await checkedAll(p)) === 'false,false', await checkedAll(p));
  const tab2 = await p.$$eval('[role=radio]', els => els.map(e => e.tabIndex).join(','));
  ok('the tab stop follows focus', tab2 === '-1,0', tab2);
  await p.keyboard.press('Home'); await p.keyboard.press('Enter');
  await p.waitForTimeout(150);
  const live = (await p.locator('[aria-live=polite]').innerText()).trim();
  ok('Enter decides: card folds into a receipt', await p.locator('section[role=group]').count() === 0 && /✓ אושר · צבעים: חום קרמל, שמנת, לבן/.test(await p.locator('main').innerText()));
  ok('the decision is announced (aria-live polite)', live === 'נקלט: צבעים: חום קרמל, שמנת, לבן', live);
  f = await focusInfo(p); ok('focus moves to the receipt\'s "change"', f.text === 'שינוי', f.text);
  await p.keyboard.press('Enter'); await p.waitForTimeout(150); f = await focusInfo(p);
  ok('reopen returns focus into the card, on the chosen option', f.role === 'radio' && f.checked === 'true', JSON.stringify(f));
  ok('reopen is announced', (await p.locator('[aria-live=polite]').innerText()).trim() === 'נפתח מחדש: צבעי האתר');
  await p.keyboard.press('Space'); await p.waitForTimeout(100);
  ok('Space decides too', await p.locator('section[role=group]').count() === 0);
  await p.close();

  // ---------- typing closes the card like a click ----------
  p = await open('Main.dc.html');
  await p.fill('#msg', 'כחול כהה ולבן'); await p.getByRole('button', { name: 'שליחה' }).click(); await p.waitForTimeout(150);
  ok('typing closes the card into a receipt with the customer\'s words', await p.locator('section[role=group]').count() === 0 && /צבעים: כחול כהה ולבן/.test(await p.locator('main').innerText()));
  await p.close();

  // ---------- floors: 7:1, 16px, 48px, reduced motion ----------
  async function floors(file, label) {
    const q = await open(file);
    await q.screenshot({ path: path.join(out, `${label}.png`) });
    const r = await q.evaluate(() => {
      function lin(c) { c /= 255; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
      function lum(rgb) { const [r, g, b] = rgb; return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b); }
      function parse(s) { const m = s.match(/[\d.]+/g); return m ? m.slice(0, 4).map(Number) : null; }
      function bg(el) { for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c && (c.length < 4 || c[3] > 0)) return c; } return [255, 255, 255]; }
      const card = document.querySelector('section[role=group]'); const rows = [];
      const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT); let n;
      while ((n = walker.nextNode())) { const t = n.textContent.trim(); if (!t) continue; const el = n.parentElement; const cs = getComputedStyle(el);
        const fg = parse(cs.color), b = bg(el); const L1 = lum(fg), L2 = lum(b); const ratio = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
        rows.push({ t: t.slice(0, 30), ratio: +ratio.toFixed(2), px: parseFloat(cs.fontSize) }); }
      const targets = [...document.querySelectorAll('button, input')].map(e => { const r = e.getBoundingClientRect(); return { t: (e.innerText || e.placeholder || '').split('\n')[0].slice(0, 24), w: Math.round(r.width), h: Math.round(r.height) }; });
      return { rows, targets };
    });
    const minRatio = Math.min(...r.rows.map(x => x.ratio)); const worst = r.rows.find(x => x.ratio === minRatio);
    ok(`${label}: every text in the decision card ≥ 7:1`, minRatio >= 7, `min ${minRatio} ("${worst.t}")`);
    const minPx = Math.min(...r.rows.map(x => x.px)); ok(`${label}: no text under 16px in the card`, minPx >= 16, `min ${minPx}px`);
    const small = r.targets.filter(x => x.w < 48 || x.h < 48); ok(`${label}: every touch target ≥ 48×48`, small.length === 0, small.length ? JSON.stringify(small) : `${r.targets.length} targets`);
    await q.close(); return r;
  }
  const light = await floors('Main.dc.html', 'light'); await floors('Dark.dc.html', 'dark');
  fs.writeFileSync(path.join(out, 'contrast-light.json'), JSON.stringify(light, null, 1));
  p = await open('Main.dc.html', { reducedMotion: 'reduce' });
  const anim = await p.$eval('section[role=group]', s => getComputedStyle(s).animationName); ok('prefers-reduced-motion: no card animation', anim === 'none', anim); await p.close();
  p = await open('Main.dc.html', { reducedMotion: 'no-preference' });
  const anim2 = await p.$eval('section[role=group]', s => getComputedStyle(s).animationName); ok('...and the animation exists otherwise (the check can fail)', anim2 === 'rise', anim2);
  // larger text: card still fits, nothing clipped
  await p.getByRole('button', { name: /גודל טקסט/ }).click(); await p.getByRole('button', { name: /גודל טקסט/ }).click();
  await p.screenshot({ path: path.join(out, 'text-xl.png') });
  const clip = await p.$eval('section[role=group]', s => ({ sh: s.scrollHeight, ch: s.clientHeight, fs: getComputedStyle(s.querySelector('#card-q')).fontSize }));
  ok('largest text: question grows to 23px', clip.fs === '23px', clip.fs);
  const reach = await p.$eval('section[role=group]', s => { s.scrollTop = s.scrollHeight; const last = [...s.querySelectorAll('p')].pop().getBoundingClientRect(), box = s.getBoundingClientRect(); return last.bottom <= box.bottom + 1 && last.top >= box.top - 1; });
  ok('largest text: the last line of the card is reachable inside the card', reach, `scrollHeight ${clip.sh} / visible ${clip.ch}`);
  const thread = await p.$eval('main', m => Math.round(m.getBoundingClientRect().height));
  ok('largest text: the conversation above the card keeps at least 96px', thread >= 96, `${thread}px`);
  await p.screenshot({ path: path.join(out, 'text-xl.png') });
  ok('no page errors in any run', p._errs.length === 0, p._errs.join(' | '));
  await p.close(); await b.close(); srv.close();
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(res, null, 1));
  console.log(`\n${res.filter(x => x.pass).length}/${res.length} PASS`);
});

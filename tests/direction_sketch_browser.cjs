/* The direction sketch's card (S6.3 slice 4) in real Chromium, on the real app.js, with the real sketch page in its frame.
 *
 * The conversation and the sketch routes are mocked (as tests/spec_card_browser.cjs does); what they answer is built by the
 * REAL functions: tests/direction_sketch_fixture.py runs omni_prod/direction_sketch/service.py (view and page) on a sketch
 * row, so the frame shows the page the build's own direction functions draw. The page route answers with the headers the
 * server sends (CSP sandbox, no scripts), and the two Google font hosts are answered here (no network in CI).
 *
 * Proved: the card is in the reply with the draft pill; the frame has loaded -- within 60 s of the reply, the time is
 * printed -- with the worker stopped (the words never arrive in the first run); it says in TEXT that the words are
 * placeholders; when the words arrive the frame loads again and the state line changes; the frame's font requests reach both
 * Google hosts and no console error says a policy refused anything; the frame is sandboxed with a title; the switch is
 * reachable by keyboard and 44 px; no sideways scroll at 320 px; the approve-spec button is still the one button and the card
 * has none of its own. Each mutation of app.js below must make this test FAIL, or the test proves nothing.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const SPEC = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'spec_card_owner.json'), 'utf8'));
const FIX = JSON.parse(execFileSync('python3', [path.join(__dirname, 'direction_sketch_fixture.py')], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }));
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};
const PAGE_HEADERS = {
  'content-type': 'text/html; charset=utf-8', 'cache-control': 'private, no-store', 'x-frame-options': 'SAMEORIGIN',
  'content-security-policy': "default-src 'none'; style-src 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src data:; frame-ancestors 'self'; sandbox",
};
const FONT_CSS = "@font-face{font-family:'David Libre';src:url(https://fonts.gstatic.com/s/davidlibre/test.woff2) format('woff2')}";

async function run(browser, width, app, options = {}) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  const seen = { created: 0, polls: 0, pages: 0, hosts: new Set(), consoleErrors: [] };
  let answered = 0, replyAt = null;
  page.on('console', m => { if (m.type() === 'error') seen.consoleErrors.push(m.text()); });
  await page.addInitScript(() => { try { localStorage.setItem('148ai_lang', 'he'); } catch (e) { /* */ } });
  await page.route('**/*', async route => {
    const u = new URL(route.request().url()), p = u.pathname, j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (u.host === 'fonts.googleapis.com') { seen.hosts.add(u.host); return route.fulfill({ contentType: 'text/css', body: FONT_CSS }); }
    if (u.host === 'fonts.gstatic.com') { seen.hosts.add(u.host); return route.fulfill({ contentType: 'font/woff2', body: Buffer.alloc(8) }); }
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: app });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'סטודיו נועה' }] });
    if (/\/conversation$/.test(p)) {
      replyAt = Date.now();
      const actions = [{ type: 'direction_sketch', direction_fp: FIX.direction_fp, copy_fp: 'c'.repeat(64), brief_revision: 1 }];
      if (options.withSpec) actions.push({ type: 'approve_spec', brief_revision: 1, brief_fingerprint: 'f'.repeat(64), canon: { status: 'OK', facts: [] }, card: SPEC.card });
      return j({ messages: [{ role: 'customer', content: 'אתר למספרה שלי' }, { role: 'assistant', content: options.withSpec ? SPEC.message : 'הבנתי. הנה סקיצת כיוון.', actions }], turn: { actions } });
    }
    if (/\/sketches$/.test(p) && route.request().method() === 'POST') { seen.created += 1; return j({ sketch: FIX.pending.view, words: { state: 'pending' } }); }
    if (/\/sketches\/[^/]+$/.test(p)) {
      seen.polls += 1; answered += 1;
      const arrive = !options.neverWritten && answered >= 2;                 // the worker's answer, on the second poll
      return j({ sketch: (arrive ? FIX.written : FIX.pending).view });
    }
    if (/\/sketches\/[^/]+\/page$/.test(p)) {
      seen.pages += 1;
      const written = !options.neverWritten && answered >= 2;
      return route.fulfill({ status: 200, headers: PAGE_HEADERS, body: (written ? FIX.written : FIX.pending).page });
    }
    if (/\/builds\/latest$/.test(p)) return j({ build: null });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat);
  const out = { width, seen, problems: [] };
  const bad = msg => out.problems.push(msg);
  const frameLocator = page.frameLocator('iframe.sketchFrame');
  try { await page.waitForSelector('iframe.sketchFrame', { timeout: 15000 }); } catch (e) { bad('no frame in the card'); }
  if (out.problems.length === 0) {
    try { await frameLocator.locator('.draft-ribbon').waitFor({ timeout: 15000 }); out.firstPaintSeconds = (Date.now() - replyAt) / 1000; } catch (e) { bad('the frame did not load its draft page'); }
  }
  out.cards = await page.locator('.sketchCard').count();
  out.pill = (await page.locator('.sketchCard .pill').first().innerText().catch(() => '')).trim();
  out.sandbox = await page.locator('iframe.sketchFrame').first().getAttribute('sandbox').catch(() => null);
  out.title = await page.locator('iframe.sketchFrame').first().getAttribute('title').catch(() => null);
  out.stateBefore = (await page.locator('.sketchState').first().innerText().catch(() => '')).trim();
  out.placeholderBefore = await frameLocator.locator('body').innerText().catch(() => '');
  out.firstSrc = await page.locator('iframe.sketchFrame').first().getAttribute('src').catch(() => null);
  if (!options.neverWritten) {
    try { await page.waitForFunction(() => /נכתבו/.test((document.querySelector('.sketchState') || {}).textContent || ''), null, { timeout: 15000 }); } catch (e) { bad('the words never reached the card'); }
    try { await frameLocator.getByText('תספורת שמתאימה לכם').first().waitFor({ timeout: 15000 }); } catch (e) { bad('the frame did not load again with the words'); }
    out.stateAfter = (await page.locator('.sketchState').first().innerText().catch(() => '')).trim();
    out.srcAfter = await page.locator('iframe.sketchFrame').first().getAttribute('src').catch(() => null);
  }
  // the switch: reachable by keyboard, 44 px, and it changes the frame's width class
  const buttons = page.locator('.sketchTools button');
  out.buttons = await buttons.count();
  if (out.buttons) {
    await buttons.first().focus();
    out.focusOnSwitch = await page.evaluate(() => document.activeElement && document.activeElement.closest('.sketchTools') !== null);
    out.boxes = [];
    for (let i = 0; i < out.buttons; i++) out.boxes.push(await buttons.nth(i).boundingBox());
    await buttons.nth(1).focus(); await page.keyboard.press('Enter');
    out.frameClass = await page.locator('iframe.sketchFrame').first().getAttribute('class');
  }
  out.approveButtons = await page.locator('#thread button', { hasText: 'כן, זה נכון' }).count();
  out.specCards = await page.locator('.specCard').count();
  out.cardButtons = await page.locator('.sketchCard button', { hasText: /אישור|מאשר|בנו|approve/i }).count();
  out.over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  out.hosts = [...seen.hosts].sort();
  await page.close();
  return out;
}

function problems(r, expect = {}) {
  const p = [...r.problems];
  if (r.cards !== 1) p.push(`${r.cards} sketch cards, not one`);
  if (r.pill !== 'טיוטה') p.push(`the pill says "${r.pill}", not "טיוטה"`);
  if (r.sandbox === null) p.push('the frame has no sandbox attribute');
  else if (r.sandbox !== '') p.push(`the frame's sandbox allows ${r.sandbox}`);
  if (!r.title) p.push('the frame has no title for screen readers');
  if (!/מקום שמור|בדרך/.test(r.stateBefore)) p.push(`the state before the words does not say they are placeholders or on their way: "${r.stateBefore}"`);
  if (!r.placeholderBefore.includes('כאן תופיע')) p.push('the first page does not show the marked placeholder line');
  if (r.seen.created !== 1) p.push(`the sketch was created ${r.seen.created} times, not once`);
  if (r.firstPaintSeconds === undefined || r.firstPaintSeconds > 60) p.push(`first paint ${r.firstPaintSeconds}s: not within 60 s`);
  if (!expect.neverWritten) {
    if (!/נכתבו/.test(r.stateAfter || '')) p.push(`the state after the words does not say they were written: "${r.stateAfter}"`);
    if (r.srcAfter === r.firstSrc) p.push('the frame did not load again when the words arrived');
  }
  if (r.hosts.join() !== 'fonts.googleapis.com,fonts.gstatic.com') p.push(`font hosts reached: ${r.hosts.join() || 'none'}`);
  // the page's own script (the menu, the WhatsApp form) must NOT run in the sandbox: Chromium says so; nothing else may be refused
  if (!r.seen.consoleErrors.some(e => /Blocked script execution/i.test(e))) p.push('the frame did not block the page\'s script: it is not sandboxed');
  const refused = r.seen.consoleErrors.filter(e => /Refused|Content Security Policy/i.test(e) && !/Blocked script execution/i.test(e));
  if (refused.length) p.push(`the console says a policy refused something: ${refused[0].slice(0, 120)}`);
  if (r.buttons !== 2 || !r.focusOnSwitch) p.push('the phone / desktop switch is not reachable by keyboard');
  for (const b of r.boxes || []) if (!b || b.height < 43.5 || b.width < 43.5) p.push(`a switch button is ${b && Math.round(b.width)}x${b && Math.round(b.height)}, under 44 px`);
  if (!/desktop/.test(r.frameClass || '')) p.push('the switch did not change the frame');
  if (r.cardButtons) p.push('the card has an approve button of its own');
  if (r.over > 1) p.push(`${r.over}px sideways scroll`);
  return p;
}

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const width of [320, 390, 1440]) {
      const r = await run(browser, width, APP);
      const found = problems(r);
      if (found.length) failures.push(`${width}px: ${found.join('; ')}`);
      else console.log(`::notice title=direction sketch card::${width}px: card with the draft pill, frame painted ${r.firstPaintSeconds.toFixed(1)} s after the reply (worker stopped), words as text, both font hosts, switch by keyboard at 44 px, no sideways scroll`);
    }
    // the words never arrive (the worker is down): the sketch is still there and says so in text, and the polling stops
    const stuck = await run(browser, 390, APP, { neverWritten: true });
    const found = problems(stuck, { neverWritten: true });
    if (found.length) failures.push(`words never written: ${found.join('; ')}`);
    else console.log(`::notice title=direction sketch card::words never written: the draft page stays, painted ${stuck.firstPaintSeconds.toFixed(1)} s after the reply, ${stuck.seen.polls} polls so far`);
    // the approval beside the card: the spec card and its one approve button are what they were
    const both = await run(browser, 1440, APP, { withSpec: true });
    if (both.specCards !== 1 || both.approveButtons !== 1) failures.push(`with the spec card: ${both.specCards} spec cards, ${both.approveButtons} approve buttons`);
    else console.log('::notice title=direction sketch card::beside the approval card: one spec card, one approve button, none of the sketch card\'s own');
    // mutations: each must make the test fail
    const mutations = [
      ['the draft pill is taken out', "h('span', { class: 'pill warn' }, t('sketchDraft'))", "h('span', { class: 'pill warn' }, '')"],
      ['the frame is not sandboxed', "title: t('sketchFrameTitle'), sandbox: '',", "title: t('sketchFrameTitle'),"],
      ['the card waits for the words before it shows the frame', "if (st.id && v) {\n    nodes.frame", "if (st.id && v && v.state === 'written') {\n    nodes.frame"],
      ['the create call is made on every render', "if (st.id || st.creating || st.error) return;                  // once per offer (a guard, as accessPending)", ''],
      ['the state says nothing in text', "function sketchWordsLine(st) {\n  const v = st.view;", "function sketchWordsLine(st) {\n  return '';\n  const v = st.view;"],
    ];
    for (const [what, from, to] of mutations) {
      assert.equal(APP.split(from).length, 2, `the mutation line for "${what}" is in app.js exactly once`);
      let broke;
      try { broke = problems(await run(browser, 390, APP.replace(from, to))); } catch (e) { broke = [`threw: ${e.message.slice(0, 80)}`]; }
      if (!broke.length) failures.push(`with "${what}" the test still passes: it proves nothing`);
      else console.log(`::notice title=direction sketch card::fails when ${what}, as it must (${broke[0].slice(0, 90)})`);
    }
  } finally {
    await browser.close();
  }
  if (failures.length) { for (const f of failures) console.error(`::error title=direction sketch card::${f}`); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });

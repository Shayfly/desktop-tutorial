/* Gate 1's spec as the card "זה מה שנבנה" (the owner's example, 2026-11-23), in real Chromium.
 *
 * The conversation is mocked with the owner's own approval message (production screenshot, 2026-11-22 23:47) and the
 * card the server builds for it (tests/fixtures/spec_card_owner.json, kept equal to omni_prod/conversation/spec_card.py
 * by tests/test_spec_card.py). On the screen: the card, not the paragraph; each business detail once; the price and
 * the next step; the approve button still there. The same run with the card's one line taken out must FAIL.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const FIX = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'spec_card_owner.json'), 'utf8'));
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const CARD_LINE = "    if (specAct) { bubble.lastChild.replaceWith(specCard(specAct.card)); bubble.classList.add('withCard'); }\n";
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

async function run(browser, width, app, shot) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.addInitScript(() => { try { localStorage.setItem('148ai_lang', 'he'); } catch (e) { /* */ } });
  await page.route('**/*', async route => {
    const u = new URL(route.request().url()), p = u.pathname, j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: app });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'סטודיו נועה' }] });
    if (/\/conversation$/.test(p)) return j({ messages: [{ role: 'customer', content: 'אתר למספרה שלי' }, { role: 'assistant', content: FIX.message }],
      turn: { actions: [{ type: 'approve_spec', brief_revision: 3, brief_fingerprint: 'f'.repeat(64), canon: { status: 'OK', facts: [] }, card: FIX.card }] } });
    if (/\/builds\/latest$/.test(p)) return j({ build: null });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat);
  await page.waitForTimeout(300);
  const thread = await page.locator('#thread').innerText();
  if (shot) await page.screenshot({ path: shot, fullPage: false });
  const out = {
    card: await page.locator('.specCard').count(),
    title: thread.includes('זה מה שנבנה'),
    paragraph: thread.includes('זה מה שהבנתי שאתם רוצים'),
    phoneTimes: thread.split('03-5551234').length - 1,
    hoursTimes: thread.split('א׳–ה׳ 09:00–19:00').length - 1,
    price: thread.includes(FIX.card.price), next: thread.includes(FIX.card.next),
    approve: await page.locator('#thread button', { hasText: 'כן, זה נכון' }).count(),
    over: await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth),
  };
  await page.close();
  return out;
}

function problems(r) {
  const p = [];
  if (r.card !== 1 || !r.title) p.push('the card "זה מה שנבנה" is not on the screen');
  if (r.paragraph) p.push('the paragraph is still shown');
  if (r.phoneTimes !== 1 || r.hoursTimes !== 1) p.push(`a detail is shown more than once (phone ${r.phoneTimes}, hours ${r.hoursTimes})`);
  if (!r.price || !r.next) p.push('the price or the next step is missing');
  if (r.approve !== 1) p.push(`the approve button is shown ${r.approve} times`);
  if (r.over > 1) p.push(`${r.over}px sideways scroll`);
  return p;
}

(async () => {
  assert.equal(APP.split(CARD_LINE).length, 2, 'the card line is in app.js exactly once');
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const width of [390, 1440]) {
      const found = problems(await run(browser, width, APP, process.env.SPEC_CARD_SHOT ? `${process.env.SPEC_CARD_SHOT}-${width}.png` : null));
      if (found.length) failures.push(`${width}px: ${found.join('; ')}`);
      else console.log(`::notice title=spec card::${width}px: the card, each detail once, price, next step, one approve button`);
    }
    const without = problems(await run(browser, 390, APP.replace(CARD_LINE, ''), null));
    if (!without.length) failures.push('with the card line taken out the test still passes: it proves nothing');
    else console.log(`::notice title=spec card::fails without the card line, as it must (${without[0]})`);
  } finally {
    await browser.close();
  }
  if (failures.length) { for (const f of failures) console.log(`::error title=spec card::${f}`); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });

/* The owner's phone report, 2026-11-23 17:07-17:52 (iPhone screenshots), in real Chromium:
 *
 *   enter     on a phone, Enter in the message box is a new line and sends nothing; on a computer it still sends
 *   viewport  the workspace takes the visible height (--vvh) and a page pushed up by the keyboard is put back at the
 *             top when the keyboard closes (the composer and tabs were left in the middle of the screen)
 *   sheet     on a phone a card ("תוכנית ועלות") opens as one full sheet with a plain "סגירה" button, not a box cut
 *             inside the conversation; the button and Escape close it
 *
 * Each check runs on the real files and must hold, then on a copy with its fault and must FAIL.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, 'omni_prod/assets', f), 'utf8');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

const FAULTS = [
  { id: 'enter_sends_on_phone', check: 'enter',
    js: ["if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && !touchTyping()) submitChat(e); });",
         "if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) submitChat(e); });"] },
  { id: 'page_left_pushed_up', check: 'viewport',
    js: ['    window.scrollTo(0, 0); document.documentElement.scrollTop = 0; document.body.scrollTop = 0;\n', ''] },
  { id: 'height_not_measured', check: 'viewport',
    js: ["  if (vv) document.documentElement.style.setProperty('--vvh', `${Math.round(vv.height)}px`);\n", ''] },
  { id: 'card_cut_inside_chat', check: 'sheet', css: '\n@media (max-width:900px){.ctx.open{position:static!important;max-height:42vh!important}}' },
];

function served(fault) {
  let app = read('app.js'), css = read('app.css');
  if (fault && fault.css) css += fault.css;
  if (fault && fault.js) {
    if (app.split(fault.js[0]).length !== 2) throw new Error(`fault ${fault.id}: its text is not in app.js exactly once`);
    app = app.replace(fault.js[0], fault.js[1]);
  }
  return { app, css };
}

async function open(browser, files, phone) {
  const ctx = await browser.newContext(phone
    ? { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }
    : { viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();
  page.sent = 0;
  await page.addInitScript(() => { try { localStorage.setItem('148ai_lang', 'he'); } catch (e) { /* */ } });
  await page.route('**/*', async route => {
    const req = route.request(), p = new URL(req.url()).pathname;
    const j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: read('index.html') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: files.app });
    if (p === '/assets/app.css') return route.fulfill({ contentType: 'text/css', body: files.css });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'ShayFly' }] });
    if (/\/conversation$/.test(p) && req.method() === 'POST') { page.sent += 1; return j({ messages: [], turn: { actions: [] } }); }
    if (/\/conversation$/.test(p)) return j({ messages: [{ role: 'customer', content: 'אתר לסוכן נסיעות' }], turn: { actions: [] } });
    if (/\/builds\/latest$/.test(p)) return j({ build: null });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat);
  await page.waitForTimeout(300);
  return page;
}

const CHECKS = {
  async enter(page, phone) {
    await page.locator('#chatInput').click();
    await page.keyboard.type('שורה ראשונה');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(250);
    const value = await page.locator('#chatInput').inputValue();
    if (phone) {
      if (page.sent) return `Enter sent the message on the phone (${page.sent} request)`;
      if (!value.includes('\n')) return 'Enter did not make a new line on the phone';
    } else if (!page.sent) return 'Enter no longer sends on the computer';
    return null;
  },
  async viewport(page, phone) {
    if (!phone) return null;
    const r = await page.evaluate(async () => {
      const vh = Math.round(window.visualViewport.height);
      const body = Math.round(document.body.getBoundingClientRect().height);
      const vvh = getComputedStyle(document.documentElement).getPropertyValue('--vvh').trim();
      // what iOS does while the keyboard is open: the page is scrolled up, although it cannot scroll by itself
      document.body.style.height = '1500px';
      document.documentElement.style.overflow = 'auto';
      window.scrollTo(0, 300);
      const pushed = window.scrollY;
      document.getElementById('chatInput').focus();
      document.getElementById('chatInput').blur();          // the keyboard closes
      await new Promise(res => setTimeout(res, 200));
      const after = window.scrollY;
      document.body.style.height = ''; document.documentElement.style.overflow = '';
      return { vh, body, pushed, after, vvh };
    });
    if (r.vvh !== `${r.vh}px`) return `--vvh is ${r.vvh || 'not set'}, the visible height is ${r.vh}px`;
    if (Math.abs(r.body - r.vh) > 1) return `the workspace is ${r.body}px tall, the visible height is ${r.vh}px`;
    if (!r.pushed) return `the test could not push the page up (${JSON.stringify(r)})`;
    if (r.after !== 0) return `after the keyboard closed the page stayed pushed up by ${r.after}px`;
    return null;
  },
  async sheet(page, phone) {
    if (!phone) return null;
    await page.evaluate(() => { document.getElementById('planPanel').hidden = false;
      document.getElementById('planPanel').textContent = 'תוכנית ועלות: 500 מהיתרה'; renderTabs(); openTab('plan'); });
    await page.waitForTimeout(150);
    const box = await page.locator('#ctx').boundingBox();
    const vp = page.viewportSize();
    if (!box || box.y > 1 || box.height < vp.height - 2 || box.width < vp.width - 2)
      return `the card is not a full sheet (${box ? `${Math.round(box.width)}x${Math.round(box.height)} at y=${Math.round(box.y)}` : 'not shown'})`;
    const close = page.locator('#ctxMinimize');
    const cb = await close.boundingBox();
    if (!cb || cb.width < 44 || cb.height < 44) return 'the close button is smaller than 44px';
    const label = await close.evaluate(el => getComputedStyle(el, '::after').content);
    if (!label.includes('סגירה')) return `the close button does not say "סגירה" (${label})`;
    await close.tap();
    await page.waitForTimeout(100);
    if (await page.locator('#ctx.open').count()) return 'the close button did not close the sheet';
    await page.evaluate(() => openTab('plan'));
    await page.keyboard.press('Escape');
    await page.waitForTimeout(100);
    if (await page.locator('#ctx.open').count()) return 'Escape did not close the sheet';
    return null;
  },
};

(async () => {
  const browser = await chromium.launch(browserOptions);
  const failures = [];
  try {
    const real = served(null);
    for (const phone of [true, false]) for (const [name, check] of Object.entries(CHECKS)) {
      const page = await open(browser, real, phone);
      const problem = await check(page, phone);
      await page.context().close();
      if (problem) failures.push(`${name} (${phone ? 'phone' : 'computer'}): ${problem}`);
    }
    for (const f of FAULTS) {
      const page = await open(browser, served(f), true);
      const problem = await CHECKS[f.check](page, true);
      await page.context().close();
      if (!problem) failures.push(`fault ${f.id} was NOT caught by "${f.check}"`);
      else console.log(`::notice title=phone chat fault::${f.id}: caught (${problem.slice(0, 90)})`);
    }
  } finally { await browser.close(); }
  if (failures.length) { for (const f of failures) console.log(`::error title=phone chat::${f}`); process.exit(1); }
  console.log(`::notice title=phone chat::3 checks hold on the phone and the computer; ${FAULTS.length}/${FAULTS.length} faults caught`);
})().catch(e => { console.error(e); process.exit(1); });

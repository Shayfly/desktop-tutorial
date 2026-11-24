/* The platform UI speaks each of its languages whole (the owner, 2026-11-22: "תוצאות בהרבה שפות").
 *
 * Real Chromium, the real index.html, app.js and app.css, the server mocked. For every language in LANGS:
 *   1. every key the English dictionary has (all its blocks) exists in that language -- nothing falls back to English;
 *   2. the page's lang and dir follow the language (Arabic and Hebrew right to left);
 *   3. no text the customer can read is in another language's script: on the entry and the workspace screens there is
 *      no Hebrew letter in the English or Arabic UI, and no Arabic letter in the Hebrew or English UI (content the
 *      customer typed is not on these screens);
 *   4. the picker offers every language, each named in its own script, and choosing one switches the page.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};
const SCRIPT = { he: /[֐-׿]/, ar: /[؀-ۿ]/ };

async function open(browser, lang) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* private mode */ } }, lang);
  await page.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.pathname === '/api/v28/me') return route.fulfill({ status: 401, contentType: 'application/json', body: '{}' });
    if (u.pathname === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (u.pathname.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', u.pathname) });
    if (u.pathname.startsWith('/api/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ projects: [], messages: [], versions: [], turn: { actions: [] } }) });
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && typeof showView === 'function');
  await page.waitForTimeout(300);
  return { page, errors };
}

// the visible text of the page, without the language picker (it names every language in its own script, by design)
const visibleText = page => page.evaluate(() => {
  const out = [];
  const walk = el => {
    if (el.id === 'langBtn' || el.id === 'langBtn2') return;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || !el.checkVisibility()) return;
    for (const n of el.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim()) out.push(n.textContent.trim());
      else if (n.nodeType === 1) walk(n);
    }
    for (const a of ['aria-label', 'placeholder', 'title']) if (el.getAttribute(a)) out.push(el.getAttribute(a));
  };
  walk(document.body);
  return out;
});

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    const { page: probe } = await open(browser, 'he');
    const langs = await probe.evaluate(() => Object.keys(LANGS));
    await probe.close();
    assert.deepEqual(langs, ['he', 'en', 'ar'], 'the platform languages');
    for (const lang of langs) {
      const { page, errors } = await open(browser, lang);
      const missing = await page.evaluate(l => Object.keys(T.en).filter(k => !(k in T[l])), lang);
      if (missing.length) failures.push(`${lang}: ${missing.length} keys fall back to English: ${missing.slice(0, 10).join(', ')}`);
      const dir = await page.evaluate(() => [document.documentElement.lang, document.documentElement.dir]);
      const wantDir = lang === 'en' ? 'ltr' : 'rtl';
      if (dir[0] !== lang || dir[1] !== wantDir) failures.push(`${lang}: html lang/dir is ${dir.join('/')}, expected ${lang}/${wantDir}`);
      const screens = [['entry', await visibleText(page)]];
      await page.evaluate(() => {
        S.signedIn = true; S.me = { email: 'lang@example.test' };
        S.projects = [{ id: 'p', title: 'P1' }]; S.projectId = 'p';
        showView(); try { renderProjects(); } catch (e) { /* the list renders on its own call too */ }
      });
      await page.waitForTimeout(250);
      screens.push(['workspace', await visibleText(page)]);
      for (const [screen, texts] of screens) {
        for (const [other, rx] of Object.entries(SCRIPT)) {
          if (other === lang) continue;
          const wrong = texts.filter(x => rx.test(x));
          if (wrong.length) failures.push(`${lang} ${screen}: ${wrong.length} texts in ${other} script: ${wrong.slice(0, 5).map(x => JSON.stringify(x.slice(0, 40))).join(', ')}`);
        }
      }
      if (errors.length) failures.push(`${lang}: page errors ${errors.slice(0, 2).join(' | ')}`);
      console.log(`::notice title=ui languages::${lang}: ${missing.length} missing keys, dir ${dir[1]}`);
      await page.close();
    }
    // the check catches its own faults: a key missing in Arabic, and Hebrew text on the Arabic screen
    {
      const { page: f } = await open(browser, 'ar');
      const caughtKey = await f.evaluate(() => { delete T.ar.login; return Object.keys(T.en).filter(k => !(k in T.ar)); });
      if (!caughtKey.includes('login')) failures.push('fault "a key missing in Arabic" was NOT caught');
      await f.evaluate(() => { const p = document.createElement('p'); p.textContent = 'כניסה לחשבון'; document.body.prepend(p); });
      const leaked = (await visibleText(f)).filter(x => SCRIPT.he.test(x));
      if (!leaked.length) failures.push('fault "Hebrew text on the Arabic screen" was NOT caught');
      else console.log('::notice title=ui languages::both deliberate faults caught');
      await f.close();
    }
    // the picker switches the page
    const { page } = await open(browser, 'he');
    const options = await page.locator('#langBtn option').evaluateAll(os => os.map(o => [o.value, o.textContent, o.lang]));
    assert.deepEqual(options.map(o => o[0]), ['he', 'en', 'ar']);
    assert.deepEqual(options.map(o => o[1]), ['עברית', 'English', 'العربية'], 'each language is named in its own script');
    await page.locator('#langBtn').selectOption('ar');
    await page.waitForTimeout(200);
    const after = await page.evaluate(() => [document.documentElement.lang, document.documentElement.dir, localStorage.getItem('148ai_lang')]);
    if (after.join() !== 'ar,rtl,ar') failures.push(`choosing Arabic gave ${after.join('/')}`);
    await page.close();
  } finally {
    await browser.close();
  }
  if (failures.length) { for (const f of failures) console.log(`::error title=ui languages::${f}`); process.exit(1); }
  console.log('::notice title=ui languages::every language whole: no key falls back, no text in another script, the picker switches');
})().catch(e => { console.error(e); process.exit(1); });

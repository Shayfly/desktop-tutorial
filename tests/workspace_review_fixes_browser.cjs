/* The platform design (warehouse 133) as released: the defects its independent review found stay fixed (2026-11-22).
 *
 * Real Chromium, the real index.html, app.js and app.css, the server mocked. Each scenario runs twice: on the code as it
 * is, where it must pass, and on the code with that one fix taken out again (OLD below: the exact line the review
 * found), where it must FAIL. A scenario that also passes on the old code proves nothing, and fails this run.
 *
 *   F1  a failed rebuild does not hide the preview of the version that already works
 *   F2  a project not opened in this session shows its real build status, read from its latest build
 *   F3  a screen reader hears who said each message in the conversation
 *   F5  a reply that arrives after the customer moved to another project changes neither that project's view nor its
 *       composer, and a message in flight is not saved as a draft
 *   A3  on a 320px phone the status chip does not squeeze the project name (it was 28px wide in English)
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const CSS = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.css'), 'utf8');
// the CSS fixes, taken out the same way (the rule block the fix added)
const OLD_CSS = {
  A3: [`  .workspace .mobileWorkspaceHead .pill{order:9;flex:1 0 100%;max-width:100%;text-align:center}\n`, ''],
};
for (const [id, [now]] of Object.entries(OLD_CSS)) assert.equal(CSS.split(now).length, 2, `${id}: the fixed rule is in app.css exactly once`);
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

// the line each fix replaced, put back for the "old code" run
const OLD = {
  F1: [`  if (canRetry) empty.append(h('button', { class: 'secondary', onclick: () => startPreview(currentVersionId()) }, t('startPreview')));`,
       `  if (canRetry && !buildFailed) empty.append(h('button', { class: 'secondary', onclick: () => startPreview(currentVersionId()) }, t('startPreview')));`],
  F2: [`  loadProjectStates(shown);\n`, `\n`],
  F3: ["    const bubble = h('div', { class: `bubble ${m.role}`, dir: 'auto' }, h('span', { class: 'sr' }, `${m.role === 'customer' ? t('you') : t('assistant')}: `), m.content);",
       "    const bubble = h('div', { class: `bubble ${m.role}`, dir: 'auto', 'aria-label':m.role === 'customer' ? t('you') : t('assistant') }, m.content);"],
  F5: [`    if (S.projectId !== project) { if ((projectDrafts.get(project) || '').trim() === S.inFlight.text) projectDrafts.delete(project); return true; }\n`, ''],
};
for (const [id, [now]] of Object.entries(OLD)) assert.equal(APP.split(now).length, 2, `${id}: the fixed line is in app.js exactly once`);

async function open(browser, fix, routes = {}, viewport = { width: 1440, height: 900 }, lang = 'he') {
  const page = await browser.newPage({ viewport });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* private mode */ } }, lang);
  await page.route('**/*', async route => {
    const u = new URL(route.request().url());
    for (const [suffix, handler] of Object.entries(routes)) if (u.pathname.endsWith(suffix)) return handler(route, u);
    if (u.pathname === '/api/v28/me') return route.fulfill({ status: 401, contentType: 'application/json', body: '{}' });
    if (u.pathname === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (u.pathname === '/assets/app.js' && OLD[fix]) return route.fulfill({ contentType: 'text/javascript', body: APP.replace(OLD[fix][0], OLD[fix][1]) });
    if (u.pathname === '/assets/app.css' && OLD_CSS[fix]) return route.fulfill({ contentType: 'text/css', body: CSS.replace(OLD_CSS[fix][0], OLD_CSS[fix][1]) });
    if (u.pathname.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', u.pathname) });
    if (u.pathname.startsWith('/api/')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ projects: [], messages: [], versions: [], history: [], turn: { actions: [] } }) });
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && typeof showView === 'function');
  await page.waitForTimeout(300);
  await page.evaluate(() => { S.signedIn = true; S.me = { email: 'fixes@example.test' }; showView(); });
  return { page, errors };
}

const SCENARIOS = {
  async A3(browser, fix) {
    const { page } = await open(browser, fix, {}, { width: 320, height: 844 }, 'en');
    await page.evaluate(() => { S.projects = [{ id: 'p', title: 'Noa Studio hair salon' }]; S.projectId = 'p'; S.plan = { can_build: true }; showView(); renderProjects(); });
    await page.waitForTimeout(300);
    const width = await page.evaluate(() => document.querySelector('.mobileWorkspaceHead .chatTitle').getBoundingClientRect().width);
    await page.close();
    assert.ok(width >= 120, `the project name keeps room on a 320px phone (${Math.round(width)}px)`);
  },
  async F1(browser, fix) {
    const { page } = await open(browser, fix);
    const shown = await page.evaluate(() => {
      S.projectId = 'p'; S.versions = [{ id: 'ver_1', title: 'גרסה 1' }]; S.preview = null; S.build = { build_id: 'b2', status: 'FAILED' };
      renderPreview();
      const empty = document.getElementById('previewEmpty');
      return { buttons: [...empty.querySelectorAll('button')].map(b => b.textContent.trim()), failed: empty.classList.contains('previewFailed') };
    });
    await page.close();
    assert.ok(shown.failed, 'the failure is still explained');
    assert.ok(shown.buttons.includes('הפעלת תצוגה מקדימה'), `the working version can still be previewed (buttons: ${shown.buttons.join(', ')})`);
  },
  async F2(browser, fix) {
    const { page } = await open(browser, fix, {
      '/projects/b/builds/latest': route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ build: { build_id: 'x', status: 'READY' } }) }),
      '/projects/c/builds/latest': route => route.fulfill({ contentType: 'application/json', body: JSON.stringify({ build: null }) }),
    });
    await page.evaluate(() => { S.projects = [{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }, { id: 'c', title: 'C' }]; S.projectId = 'a'; renderSidebarProjects(); });
    await page.waitForTimeout(400);
    const rows = await page.evaluate(() => Object.fromEntries([...document.querySelectorAll('#sbProjects button[data-project]')]
      .map(b => [b.dataset.project, b.querySelector('.sbStatus').textContent])));
    await page.close();
    assert.equal(rows.b, 'נבנה', `a built project says so (rows: ${JSON.stringify(rows)})`);
    assert.equal(rows.c, 'עוד לא נבנה', 'a project with no build says so');
  },
  async F3(browser, fix) {
    const { page } = await open(browser, fix);
    await page.evaluate(() => { S.projectId = 'p'; S.chat = { messages: [{ role: 'customer', content: 'אתר למספרה' }, { role: 'assistant', content: 'איך קוראים לעסק?' }] }; renderChat(); });
    const heard = await page.locator('#thread').ariaSnapshot();
    await page.close();
    assert.match(heard, /אתם:?\s*אתר למספרה/, `the customer is named (heard: ${heard})`);
    assert.match(heard, /148AI:?\s*איך קוראים לעסק/, 'the assistant is named');
  },
  async F5(browser, fix) {
    let release;
    const held = new Promise(r => { release = r; });
    const { page } = await open(browser, fix, {
      '/projects/a/conversation': async (route) => {
        if (route.request().method() !== 'POST') return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ messages: [] }) });
        await held;
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ messages: [{ role: 'customer', content: 'תעשו את זה ורוד' }, { role: 'assistant', content: 'A ANSWER' }], turn: { actions: [] } }) });
      },
    });
    await page.evaluate(() => { S.projects = [{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }]; selectProject('a'); });
    await page.waitForTimeout(300);
    await page.locator('#chatInput').fill('תעשו את זה ורוד');
    await page.evaluate(() => { submitChat(); });
    await page.waitForTimeout(200);
    await page.evaluate(() => selectProject('b'));
    await page.waitForTimeout(300);
    await page.locator('#chatInput').fill('B DRAFT');
    release();
    await page.waitForTimeout(500);
    const onB = await page.evaluate(() => ({ composer: document.getElementById('chatInput').value, thread: document.getElementById('thread').textContent }));
    await page.evaluate(() => selectProject('a'));
    await page.waitForTimeout(300);
    const backOnA = await page.locator('#chatInput').inputValue();
    await page.close();
    assert.equal(onB.composer, 'B DRAFT', "the late reply does not empty the other project's composer");
    assert.ok(!onB.thread.includes('A ANSWER'), "the late reply is not shown in the other project");
    assert.equal(backOnA, '', 'the message that was sent does not come back as a draft');
  },
};

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const [id, run] of Object.entries(SCENARIOS)) {
      try { await run(browser, null); console.log(`PASS ${id}`); }
      catch (e) { failures.push(`${id} fails on the current code: ${e.message}`); }
      try { await run(browser, id); failures.push(`${id} also passes with its fix taken out: it proves nothing`); }
      catch (e) { console.log(`::notice title=review fixes::${id} fails with its fix taken out, as it must (${e.message.split('\n')[0].slice(0, 120)})`); }
    }
  } finally {
    await browser.close();
  }
  if (failures.length) { for (const f of failures) console.log(`::error title=review fixes::${f}`); process.exit(1); }
  console.log(`::notice title=review fixes::${Object.keys(SCENARIOS).length} fixes hold, and each test fails without its fix`);
})().catch(e => { console.error(e); process.exit(1); });

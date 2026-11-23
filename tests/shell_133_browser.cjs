/* Warehouse 133's mutation table, the five rows no other test plants (2026-11-23). Real Chromium, the real files.
 *
 *   secondary_yellow   a secondary action has the primary's yellow fill
 *   secondary_looks_disabled  an active secondary action is faded like a disabled one
 *   status_colour_only the project row's status text is hidden, leaving colour alone
 *   failure_empty      a failed build shows an empty preview frame instead of the card with a next step
 *   raw_id_in_row      the version row's main line shows the raw id; the id belongs in "details"
 *
 * Each check runs on the real files and must hold, then on a copy with its fault and must FAIL. An uncaught fault
 * fails the run. (The other three rows -- contrast, 44px targets, sideways scroll at 320 -- are planted
 * by platform_a11y_browser.cjs and platform_for_everyone_browser.cjs.)
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, 'omni_prod/assets', f), 'utf8');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

const FAULTS = [
  { id: 'secondary_yellow', check: 'secondary', css: '\nbutton.secondary { background: #ffd43b !important }' },
  { id: 'secondary_looks_disabled', check: 'secondary', css: '\nbutton.secondary { opacity: .45 !important }' },
  { id: 'status_colour_only', check: 'status', css: '\n.sbStatus { font-size: 0 !important; color: transparent !important }' },
  { id: 'failure_empty', check: 'failure', js: ["    empty.append(h('div', { class: 'previewRecovery' }, recover));\n", ''] },
  { id: 'raw_id_in_row', check: 'versions', js: ["h('details', {}, h('summary', {}, t('tab_details')), h('code', { dir:'ltr' }, v.id))",
                                                 "h('code', { dir:'ltr' }, v.id)"] },
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

async function open(browser, files, width) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.addInitScript(() => { try { localStorage.setItem('148ai_lang', 'he'); } catch (e) { /* */ } });
  await page.route('**/*', async route => {
    const p = new URL(route.request().url()).pathname, j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: read('index.html') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: files.app });
    if (p === '/assets/app.css') return route.fulfill({ contentType: 'text/css', body: files.css });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'סטודיו נועה', status: 'READY' }, { id: 'p2', title: 'קפה הגפן' }] });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn);
  await page.waitForTimeout(300);
  return page;
}

const CHECKS = {
  // a secondary action never wears the primary's yellow
  async secondary(page) {
    await page.evaluate(() => { S.versions = [{ id: 'ver_2', title: 'גרסה 2', created_at: '2026-11-23T08:00:00Z' }]; S.preview = { status: 'EXPIRED' };
      renderPreview && renderPreview(); window.VE && VE.setPane('preview'); });
    await page.waitForTimeout(150);
    return page.evaluate(() => {
      const primary = getComputedStyle(document.querySelector('#chatSend')).backgroundColor;
      const shown = [...document.querySelectorAll('button.secondary')].filter(b => b.checkVisibility() && !b.disabled);
      if (!shown.length) return ['no secondary action on the screen to check'];
      return [...shown.filter(b => getComputedStyle(b).backgroundColor === primary).map(b => `"${b.textContent.trim()}" has the primary's fill`),
              ...shown.filter(b => parseFloat(getComputedStyle(b).opacity) < 0.95).map(b => `"${b.textContent.trim()}" looks disabled`)];
    });
  },
  // each project row says its state in text a person can read
  async status(page) {
    return page.evaluate(() => [...document.querySelectorAll('#sbProjects .sbStatus')].filter(s => {
      const st = getComputedStyle(s); return !s.textContent.trim() || parseFloat(st.fontSize) < 12 || st.color === 'rgba(0, 0, 0, 0)';
    }).map(s => `a project row's state "${s.textContent.trim()}" cannot be read`));
  },
  // a failed build shows the card with the reason and a next step, not an empty frame
  async failure(page) {
    await page.evaluate(() => { S.build = { id: 'b1', status: 'failed', error_code: 'TESTS_FAILED' }; S.preview = null; S.versions = [];
      renderPreview(); window.VE && VE.setPane('preview'); });
    await page.waitForTimeout(150);
    return page.evaluate(() => {
      const card = document.querySelector('.previewRecovery button');
      return card && card.checkVisibility() && card.textContent.trim() ? [] : ['a failed build shows no next step in the preview'];
    });
  },
  // the version row's main line is a name and a date; the raw id is only inside "details"
  async versions(page) {
    await page.evaluate(() => { S.versions = [{ id: 'ver_8f3a2c', title: 'גרסה 2', created_at: '2026-11-23T08:00:00Z' },
      { id: 'ver_11aa01', title: 'גרסה 1', created_at: '2026-11-22T08:00:00Z' }]; renderVersions(); window.VE && VE.setPane('versions'); });
    await page.waitForTimeout(150);
    return page.evaluate(() => [...document.querySelectorAll('#versionsList li')].filter(li => {
      const outside = [...li.querySelectorAll('code')].filter(c => !c.closest('details')).some(c => c.checkVisibility());
      return outside;
    }).map(() => 'a raw version id is on the main line of its row')
      .concat(document.querySelectorAll('#versionsList li').length === 2 ? [] : ['the two versions are not on the screen']));
  },
};

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const width of [390, 1440]) for (const [name, check] of Object.entries(CHECKS)) {
      const page = await open(browser, served(null), width);
      const found = await check(page); await page.close();
      if (found.length) failures.push(`${name} ${width}px: ${found.join('; ')}`);
      else console.log(`::notice title=shell 133::${name} ${width}px holds`);
    }
    for (const f of FAULTS) {
      const page = await open(browser, served(f), 1440);
      const found = await CHECKS[f.check](page); await page.close();
      if (!found.length) failures.push(`fault ${f.id} was NOT caught by "${f.check}"`);
      else console.log(`::notice title=shell 133 fault::${f.id}: caught (${found[0].slice(0, 80)})`);
    }
  } finally { await browser.close(); }
  if (failures.length) { for (const f of failures) console.log(`::error title=shell 133::${f}`); process.exit(1); }
  console.log(`::notice title=shell 133::4 checks x 2 widths hold; ${FAULTS.length}/${FAULTS.length} faults caught`);
})().catch(e => { console.error(e); process.exit(1); });

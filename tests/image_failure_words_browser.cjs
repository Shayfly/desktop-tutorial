/* What the customer is told when a generated image stopped the build (the owner, 2026-11-23, bld_7b541f93).
 *
 * Two different things must read differently, in Hebrew, English and Arabic:
 *   not_run   the image was never checked ("without the subject they were made from"): the words must NOT claim the
 *             picture fails to show what was asked -- nobody looked at it. They say it was not clear what the picture
 *             should show, and what to write next.
 *   mismatch  a real verdict ('asked "X"; the image shows "Y"'): the words still name what was asked and what was seen.
 *
 * Each check runs on the real app.js and must hold, then on a copy with its fault and must FAIL.
 */
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, 'omni_prod/assets', f), 'utf8');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

const NOT_RUN = 'ImageDoesNotMatch: generated image(s) without the subject they were made from: cap-media-image-generate';
const MISMATCH = 'image_mismatch: asked "נתחי בקר טריים"; the image shows "ביצים"; reason: different subject';

const FAULTS = [
  { id: 'never_checked_reads_as_a_mismatch', check: 'notRun',
    js: ["    if (/without the subject they were made from|could not be checked against the request/.test(String(b.error_message || '')))\n      return (t('errCodes') || {}).image_not_described || known;\n", ''] },
  { id: 'a_real_mismatch_loses_what_was_seen', check: 'mismatch',
    js: ['    if (m) return known + ({ en: ` Asked: "${m[1]}". The image shows: "${m[2]}".`,', '    if (false) return known + ({ en: ` x`,'] },
];

function served(fault) {
  let app = read('app.js');
  if (fault && fault.js) {
    if (app.split(fault.js[0]).length !== 2) throw new Error(`fault ${fault.id}: its text is not in app.js exactly once`);
    app = app.replace(fault.js[0], fault.js[1]);
  }
  return app;
}

async function open(browser, app, lang) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* */ } }, lang);
  await page.route('**/*', async route => {
    const p = new URL(route.request().url()).pathname;
    const j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: read('index.html') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: app });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'shay@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'ShayFly' }] });
    if (/\/conversation$/.test(p)) return j({ messages: [], turn: { actions: [] } });
    if (/\/builds\/latest$/.test(p)) return j({ build: null });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat);
  await page.waitForTimeout(200);
  return page;
}

const words = (page, message) => page.evaluate(m => friendlyError({ id: 'b1', status: 'failed',
  error_code: 'image_mismatch', error_message: m }), message);

// what each language must and must not say when the image was never checked
const CLAIMS_IT_DOES_NOT_SHOW = { he: 'לא מראה את מה שביקשתם', en: 'does not show what you asked', ar: 'لا تُظهر ما طلبتموه' };
const SAYS_WHAT_IT_NEEDS = { he: 'מה היא מראה', en: 'what it should show', ar: 'ما تُظهره' };

const CHECKS = {
  async notRun(page, lang) {
    const text = await words(page, NOT_RUN);
    if (text.includes(CLAIMS_IT_DOES_NOT_SHOW[lang]))
      return `an image nobody checked is reported as not showing what was asked: "${text.slice(0, 90)}"`;
    if (!text.includes(SAYS_WHAT_IT_NEEDS[lang]))
      return `the words do not say what the picture needed: "${text.slice(0, 90)}"`;
    return null;
  },
  async mismatch(page, lang) {
    const text = await words(page, MISMATCH);
    if (!text.includes('ביצים')) return `a real verdict does not say what the image shows: "${text.slice(0, 90)}"`;
    if (!text.includes(CLAIMS_IT_DOES_NOT_SHOW[lang])) return `a real mismatch lost its own words: "${text.slice(0, 90)}"`;
    return null;
  },
};

(async () => {
  const browser = await chromium.launch(browserOptions);
  const failures = [];
  try {
    const real = served(null);
    for (const lang of ['he', 'en', 'ar']) for (const [name, check] of Object.entries(CHECKS)) {
      if (name === 'mismatch' && lang !== 'he') continue;        // the quoted subject is Hebrew in this fixture
      const page = await open(browser, real, lang);
      const problem = await check(page, lang);
      await page.close();
      if (problem) failures.push(`${name} (${lang}): ${problem}`);
    }
    for (const f of FAULTS) {
      const page = await open(browser, served(f), 'he');
      const problem = await CHECKS[f.check](page, 'he');
      await page.close();
      if (!problem) failures.push(`fault ${f.id} was NOT caught by "${f.check}"`);
      else console.log(`::notice title=image failure fault::${f.id}: caught (${problem.slice(0, 90)})`);
    }
  } finally { await browser.close(); }
  if (failures.length) { for (const f of failures) console.log(`::error title=image failure words::${f}`); process.exit(1); }
  console.log(`::notice title=image failure words::never-checked and a real mismatch read differently in he/en/ar; `
    + `${FAULTS.length}/${FAULTS.length} faults caught`);
})().catch(e => { console.error(e); process.exit(1); });

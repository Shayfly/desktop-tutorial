/* The build card, the screenshot upload and the fix (warehouse 124) in real Chromium, on the real app.js.
 *
 * The routes are mocked (as tests/spec_card_browser.cjs does); what they answer is built by the REAL round (tests/shot_fix_fixture.py runs
 * omni_prod/shot_fix.round_of on a real PNG, a real site and the model's edit block, in Hebrew, Arabic and English), and the test uploads
 * that very PNG, so the card, the width it sends and what comes back are checked against the server's own code.
 *
 * Proved: the build is in the conversation as the direction sketch's card (the same component: `.sketchCard`, its frame, its phone / desktop
 * switch) with the build id on it; the frame shows the running site at the width of the switch (390 on a phone, the card's on a computer);
 * the upload sends the PNG exactly as it is, to THIS build, with the width the frame has at that moment (390, then the computer's); the
 * reply is in the customer's language with the next action and one button; the click asks the change pipeline to apply that stored fix
 * (its fingerprint), not edits of the browser's own; the card has no screen of its own and does not take the conversation over.
 * Each mutation of app.js below must make this test FAIL, or the test proves nothing. Every wait is bounded.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const FIX = JSON.parse(execFileSync('python3', [path.join(__dirname, 'shot_fix_fixture.py')], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }));
const PNG = Buffer.from(FIX.png_b64, 'base64');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};
const LONG_MS = 10000, SHORT_MS = 5000;
const WATCHDOG_MS = 4 * 60 * 1000;
const TEXT = {
  he: { title: 'האתר שנבנה', upload: 'העלו כאן את הצילום', note: 'הצילום הוא רק מצביע', start: 'הפעלת תצוגה מקדימה', width: 'רוחב החלון' },
  ar: { title: 'الموقع الذي بُني', upload: 'ارفعوا اللقطة هنا', note: 'اللقطة مجرد مؤشر', start: 'تشغيل المعاينة', width: 'عرض النافذة' },
  en: { title: 'The site we built', upload: 'Upload it here', note: 'The screenshot is only a pointer', start: 'Start preview', width: 'Window width' },
};

async function run(browser, lang, app, options = {}) {
  const page = await browser.newPage({ viewport: { width: options.viewport || 1440, height: 1000 } });
  page.setDefaultTimeout(options.mutated ? SHORT_MS : LONG_MS);
  const seen = { shots: [], mods: [], shotPaths: [], consoleErrors: [], posts: 0 };
  page.on('console', m => { if (m.type() === 'error') seen.consoleErrors.push(m.text()); });
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* */ } }, lang);
  const view = FIX.views[lang];
  let uploaded = false;
  await page.route('**/*', async route => {
    const u = new URL(route.request().url()), p = u.pathname, method = route.request().method(), j = (x, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: app });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/site/') return route.fulfill({ contentType: 'text/html; charset=utf-8', body: FIX.site.html });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test' });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'סטודיו נועה' }] });
    if (/\/builds\/latest$/.test(p)) return j({ build: { build_id: FIX.build_id, status: 'READY' } });
    if (p.endsWith(`/builds/${FIX.build_id}/shots`) && method === 'POST') {
      seen.posts += 1; seen.shotPaths.push(p + u.search); seen.shots.push(JSON.parse(route.request().postData()));
      uploaded = true;
      return j(view.after);
    }
    if (p.endsWith(`/builds/${FIX.build_id}`)) return j({ build_id: FIX.build_id, status: 'READY', phase: 'DONE', result_version_id: FIX.version_id, evidence: {}, error_code: null });
    if (/\/history$/.test(p)) return j({ versions: [{ id: FIX.version_id, created_at: '2026-11-27T10:00:00Z' }] });
    if (/\/conversation$/.test(p)) return j(uploaded ? view.after : view.before);
    if (p.endsWith(`/versions/${FIX.version_id}/previews`) && method === 'POST') return j({ preview_id: 'pv1' });
    if (p.endsWith('/previews/pv1')) return j({ id: 'pv1', status: 'RUNNING', preview_url: 'https://prv.test/', access_mode: 'PRIVATE', data_storage: 'temporary', version_id: FIX.version_id });
    if (p.endsWith('/previews/pv1/access')) return j({ url: '/site/' });
    if (p.endsWith(`/versions/${FIX.version_id}/modifications`) && method === 'POST') {
      seen.mods.push(JSON.parse(route.request().postData()));
      return j({ status: 'queued', modification_id: 'mod_1', dispatch: 'enqueued' }, 202);
    }
    if (/\/modifications\/latest$/.test(p)) return j({});
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat && S.build);
  const out = { lang, problems: [], seen, cards: 0, sketchCards: 0, widths: {}, widthLines: {}, cardText: '', replyText: '', buttons: [],
    buildIdOnCard: false, thumbs: 0, over: 0, frames: 0, switchPressed: {}, modBody: null };
  const bad = m => out.problems.push(m);
  const waitFor = async (what, fn, arg) => { try { await page.waitForFunction(fn, arg, { timeout: options.mutated ? SHORT_MS : LONG_MS }); return true; } catch (e) { bad(what); return false; } };
  // 1. the card, with its build id, and the preview started from it
  if (!(await waitFor('no build card in the conversation', () => document.querySelector('#thread .buildCard')))) return finish();
  out.cards = await page.locator('#thread .buildCard').count();
  out.sketchCards = await page.locator('#thread .sketchCard.buildCard').count();                 // the sketch card's own component
  out.buildIdOnCard = (await page.locator('#thread .buildCard .buildId').first().textContent().catch(() => '')) === FIX.build_id;
  out.cardText = await page.locator('#thread .buildCard').first().innerText();
  const start = page.locator('#thread .buildCard button', { hasText: TEXT[lang].start });
  if (await start.count() !== 1) { bad(`the card has ${await start.count()} "start preview" buttons, not one`); return finish(); }
  await start.click();
  if (!(await waitFor('the running site is not in the card', () => { const f = document.querySelector('#thread .buildCard iframe.sketchFrame'); return f && f.src.includes('/site/'); }))) return finish();
  out.frames = await page.locator('#thread .buildCard iframe').count();
  const frame = page.frameLocator('#thread .buildCard iframe.sketchFrame');
  try { await frame.locator('.cta').waitFor({ timeout: options.mutated ? SHORT_MS : LONG_MS }); } catch (e) { bad('the frame did not load the running site'); }
  // 2. the switch: a phone's width, then a computer's; the width line follows the frame
  const buttons = page.locator('#thread .buildCard .sketchTools button');
  if (await buttons.count() !== 2) { bad('the card has no phone / desktop switch of the sketch card'); return finish(); }
  const widthOf = async () => Math.round((await page.locator('#thread .buildCard iframe.sketchFrame').boundingBox()).width);
  out.widths.phone = await widthOf();
  await waitFor('the width line does not say the phone width', w => (document.querySelector('#thread .buildCard .shotWidth') || { textContent: '' }).textContent.includes(String(w)), out.widths.phone);
  out.widthLines.phone = await page.locator('#thread .buildCard .shotWidth').first().textContent().catch(() => '');
  await buttons.nth(1).click();
  await waitFor('the switch did not change the frame', () => /desktop/.test(document.querySelector('#thread .buildCard iframe.sketchFrame').className), null);
  out.widths.desktop = await widthOf();
  out.widthLines.desktop = await page.locator('#thread .buildCard .shotWidth').first().textContent().catch(() => '');
  out.switchPressed = { phone: await buttons.nth(0).getAttribute('aria-pressed'), desktop: await buttons.nth(1).getAttribute('aria-pressed') };
  // 3. a screenshot taken on the computer's width, then on the phone's
  const timeout = options.mutated ? SHORT_MS : LONG_MS;
  const sent = () => page.waitForRequest(r => /\/shots/.test(r.url()) && r.method() === 'POST', { timeout }).catch(() => { bad('an upload did not reach the server'); });
  let waiting = sent();
  await page.setInputFiles('#shotFile', { name: 'shot.png', mimeType: 'image/png', buffer: PNG });
  await waiting;
  if (!(await waitFor('the first reply is not in the conversation', () => document.querySelectorAll('#thread .thumbs img').length >= 1, null))) return finish();
  await buttons.nth(0).click();
  await waitFor('the switch did not go back to the phone', () => /phone/.test(document.querySelector('#thread .buildCard iframe.sketchFrame').className), null);
  await waitFor('the width line did not follow the switch', w => (document.querySelector('#thread .buildCard .shotWidth') || {}).textContent.includes(String(w)), out.widths.phone);
  waiting = sent();
  await page.setInputFiles('#shotFile', { name: 'shot2.png', mimeType: 'image/png', buffer: PNG });
  await waiting;
  if (!(await waitFor('the second reply was not taken in', () => !document.getElementById('chatSend').disabled && document.querySelectorAll('#thread .thumbs img').length >= 1, null))) return finish();
  // 4. what the customer reads, and the one button
  out.replyText = await page.locator('#thread .bubble.assistant').last().innerText();
  out.buttons = await page.locator('#thread .bubble.assistant').last().locator('.acts button').allInnerTexts();
  out.thumbs = await page.locator('#thread .thumbs img').count();
  out.cardAfter = await page.locator('#thread .buildCard').count();
  const apply = page.locator('#thread .acts button', { hasText: view.button });
  if (await apply.count()) {
    const asked = page.waitForRequest(r => /\/modifications$/.test(r.url()) && r.method() === 'POST', { timeout }).catch(() => null);
    await apply.last().click();
    await asked;
    out.modBody = seen.mods[0] || null;
  }
  out.over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  return finish();
  async function finish() { await page.close(); return out; }
}

function problems(r, expect = {}) {
  const p = [...r.problems], view = FIX.views[r.lang], t = TEXT[r.lang];
  if (r.cards !== 1) p.push(`${r.cards} build cards, not one`);
  if (r.sketchCards !== 1) p.push('the build card is not the sketch card\'s component (.sketchCard)');
  if (!r.buildIdOnCard) p.push('the build id is not on the card');
  if (!r.cardText.includes(t.title)) p.push('the card has no title in this language');
  if (r.frames !== 1) p.push(`${r.frames} frames in the card`);
  if (expect.narrow) {            // a small phone: the card is narrower than a phone's frame, so the frame is the card's
    if (!(r.widths.phone > 200 && r.widths.phone <= expect.narrow)) p.push(`the phone frame is ${r.widths.phone} px in a ${expect.narrow} px window`);
  } else {
    if (r.widths.phone !== 390) p.push(`the phone frame is ${r.widths.phone} px wide, not 390`);
    if (!(r.widths.desktop > 700)) p.push(`the computer frame is ${r.widths.desktop} px wide`);
  }
  if (r.switchPressed.desktop !== 'true' || r.switchPressed.phone !== 'false') p.push('the switch does not say which width is shown');
  if (!new RegExp(String(r.widths.phone)).test(r.widthLines.phone || '') || !(r.widthLines.phone || '').includes(t.width)) p.push(`the phone width line says "${r.widthLines.phone}", the frame is ${r.widths.phone}`);
  if (!new RegExp(String(r.widths.desktop)).test(r.widthLines.desktop || '')) p.push(`the computer width line says "${r.widthLines.desktop}", the frame is ${r.widths.desktop}`);
  // the uploads: this build, this PNG as it is, the width the frame had
  if (r.seen.shots.length !== 2) p.push(`${r.seen.shots.length} uploads reached the server, not two`);
  else {
    const [a, b] = r.seen.shots;
    if (a.data_base64 !== FIX.png_b64 || b.data_base64 !== FIX.png_b64) p.push('the upload is not the file the customer chose, byte for byte');
    if (a.viewport_width !== r.widths.desktop) p.push(`the first upload carries width ${a.viewport_width}, the frame was ${r.widths.desktop}`);
    if (b.viewport_width !== r.widths.phone) p.push(`the second upload carries width ${b.viewport_width}, the phone frame was ${r.widths.phone}`);
    if (!expect.narrow && a.viewport_width === b.viewport_width) p.push('the width does not follow the switch');
  }
  for (const sp of r.seen.shotPaths) if (!sp.includes(`/builds/${FIX.build_id}/shots`) || !sp.includes(`lang=${r.lang}`)) p.push(`the upload went to ${sp}`);
  // what the customer reads
  if (!r.replyText.includes(view.reply.slice(0, 40))) p.push('the reply of the server is not what the customer reads');
  if (!r.replyText.includes(view.button)) p.push('the reply does not name the one button');
  if (r.buttons.length !== 1 || !r.buttons[0].includes(view.button)) p.push(`the reply has ${r.buttons.length} buttons: ${r.buttons.join(' | ')}`);
  if (r.thumbs < 1) p.push('the screenshot is not in the conversation');
  if (r.cardAfter !== 1) p.push('the build card is gone after the reply (it must stay beside the conversation)');
  // the click: the stored fix by its fingerprint, never edits of the browser's own
  if (!r.modBody) p.push('the click did not ask the change pipeline for anything');
  else {
    if (r.modBody.shot_fix !== view.fingerprint) p.push(`the click sends shot_fix ${r.modBody.shot_fix}, the stored fix is ${view.fingerprint}`);
    if ('edits' in r.modBody || 'files' in r.modBody || 'old' in r.modBody) p.push('the click sends edits of its own');
    if (typeof r.modBody.followup !== 'string' || r.modBody.followup.length < 3) p.push('the click sends no sentence');
  }
  if (r.over > 1) p.push(`${r.over}px sideways scroll`);
  const refused = r.seen.consoleErrors.filter(e => /Refused|Content Security Policy/i.test(e));
  if (refused.length) p.push(`the console says a policy refused something: ${refused[0].slice(0, 120)}`);
  return p;
}

const watchdog = setTimeout(() => { console.error(`::error title=shot fix::the test ran past ${WATCHDOG_MS / 1000} s: something waits without end`); process.exit(2); }, WATCHDOG_MS);
(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const lang of ['he', 'ar', 'en']) {
      const r = await run(browser, lang, APP);
      const found = problems(r);
      if (found.length) failures.push(`${lang}: ${found.join('; ')}`);
      else console.log(`::notice title=shot fix::${lang}: the build card is the sketch card's component with build id ${FIX.build_id}; frame ${r.widths.phone} px on the phone and ${r.widths.desktop} px on the computer; uploads carried the file as it is with widths ${r.seen.shots.map(s => s.viewport_width).join(' and ')}; one button, and the click sent fix ${r.modBody.shot_fix.slice(0, 12)}`);
    }
    // a small phone (a 360 px window): the frame is the card's width, the upload carries that width, and nothing scrolls sideways
    const narrow = await run(browser, 'he', APP, { viewport: 360 });
    const narrowFound = problems(narrow, { narrow: 360 });
    if (narrowFound.length) failures.push(`360 px: ${narrowFound.join('; ')}`);
    else console.log(`::notice title=shot fix::360 px window: frame ${narrow.widths.phone} px, the upload carried ${narrow.seen.shots[1].viewport_width}, no sideways scroll`);
    // mutations: each must make the test fail
    const mutations = [
      ['the width is not sent as the frame has it', 'viewport_width: width }, t(\'shotSent\')', 'viewport_width: 390 }, t(\'shotSent\')'],
      ['the build id is not on the card', "h('code', { dir: 'ltr', class: 'buildId' }, String(b.id))", "h('code', { dir: 'ltr', class: 'buildId' }, '')"],
      ['the build card is a second card of its own', "class: 'sketchCard buildCard'", "class: 'buildCard'"],
      ['the switch changes nothing', 'onclick: () => { st.device = device; onChange(); } }, label));', 'onclick: () => { onChange(); } }, label));'],
      ['the click sends no stored fix', 'sendModification({ shot_fix: a.fingerprint }); }', 'sendModification({}); }'],
      ['the upload goes to another build', '/builds/${encodeURIComponent(S.build.id)}/shots`', '/builds/bld_other/shots`'],
      ['the file is changed on the way (a prefix of it)', "r.onload = () => resolve(String(r.result).split(',', 2)[1]); r.onerror = reject; r.readAsDataURL(blob);\n  });\n}\nconst shotPath", "r.onload = () => resolve(String(r.result).split(',', 2)[1].slice(8)); r.onerror = reject; r.readAsDataURL(blob);\n  });\n}\nconst shotPath"],
    ];
    for (const [what, from, to] of mutations) {
      assert.equal(APP.split(from).length, 2, `the mutation line for "${what}" is in app.js exactly once`);
      let broke;
      try { broke = problems(await run(browser, 'he', APP.replace(from, to), { mutated: true })); } catch (e) { broke = [`threw: ${e.message.slice(0, 80)}`]; }
      if (!broke.length) failures.push(`with "${what}" the test still passes: it proves nothing`);
      else console.log(`::notice title=shot fix::fails when ${what}, as it must (${broke[0].slice(0, 90)})`);
    }
  } finally {
    await browser.close();
    clearTimeout(watchdog);
  }
  if (failures.length) { for (const f of failures) console.error(`::error title=shot fix::${f}`); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });

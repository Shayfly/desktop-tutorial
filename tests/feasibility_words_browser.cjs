/* The findings of the feasibility gate on the plan screen (warehouse 132), in real Chromium, on the real app.js.
 *
 * The conversation route is mocked (as tests/spec_card_browser.cjs does); what it answers is built by the REAL functions:
 * tests/feasibility_words_fixture.py runs the brief, the contract, ChiefArchitect.plan and the supervisor's _plan_view for a
 * request the gate cannot build (a phone app with sign-in, payments and email), so the findings are the gate's own, each with
 * the words the server attached.
 *
 * Proved, in Hebrew, Arabic and English: the panel says every finding as its words (what, why, the next action) in the customer's
 * language and in its own script; none of the platform's item names or reasons ("product family mobile_app", "verification
 * step status ...") is on the screen; a finding several checks share is said once; the item and reason are the owner's alone
 * (a customer has no "technical details"); and the "build did not start" sentence the blocker list shows is the same words.
 * Each mutation of app.js below must make this test FAIL, or the test proves nothing. Every wait is bounded.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const FIX = JSON.parse(execFileSync('python3', [path.join(__dirname, 'feasibility_words_fixture.py')], { cwd: ROOT, encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 }));
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};
const LONG_MS = 10000, SHORT_MS = 5000;
const WATCHDOG_MS = 3 * 60 * 1000;
const HEBREW = /[֐-׿]/, ARABIC = /[؀-ۿ]/, LATIN_WORD = /[A-Za-z]{3,}/;
const PLATFORM = [/product family/i, /mobile_app/, /verification step/i, /NOT_IMPLEMENTED/, /integration_agent/, /not supported yet/i,
                  /sandbox verification/i, /behavioural acceptance/i, /release policy/i, /sign-in \(simple\)/];

const bare = fs => ({ ...fs, words: undefined });         // a finding as an older server sent it: no words
const PLAN_UNWORDED = { ...FIX.plan, feasibility: { ...FIX.plan.feasibility, findings: FIX.plan.feasibility.findings.map(bare) } };
const BLOCKER_UNWORDED = { ...FIX.blocker, findings: FIX.blocker.findings.map(bare) };

async function run(browser, lang, width, app, options = {}) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.setDefaultTimeout(options.mutated ? SHORT_MS : LONG_MS);
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* */ } }, lang);
  await page.route('**/*', async route => {
    const u = new URL(route.request().url()), p = u.pathname, j = x => route.fulfill({ contentType: 'application/json', body: JSON.stringify(x) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (p === '/assets/app.js') return route.fulfill({ contentType: 'application/javascript', body: app });
    if (p.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    if (p === '/api/v28/me') return j({ email: 'noa@example.test', ...(options.owner ? { is_founder: true } : {}) });
    if (p === '/api/v28/m5/status') return j({ blockers: [] });
    if (p === '/api/v28/projects') return j({ projects: [{ id: 'p1', title: 'x' }] });
    if (/\/conversation$/.test(p)) return j({ messages: [{ role: 'customer', content: '.' }, { role: 'assistant', content: '.' }], turn: { actions: [] }, plan: options.unworded ? PLAN_UNWORDED : FIX.plan });
    if (/\/builds\/latest$/.test(p)) return j({ build: null });
    if (p.startsWith('/api/')) return j({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && S.signedIn && S.chat && S.arch);
  const out = { lang, width, problems: [], text: '', items: [], details: -1, block: '' };
  const bad = m => out.problems.push(m);
  try { await page.waitForSelector('#archPanel li', { state: 'attached', timeout: options.mutated ? SHORT_MS : LONG_MS }); } catch (e) { bad('the panel lists no finding'); }
  out.text = await page.locator('#archPanel').evaluate(n => n.textContent);
  out.items = await page.locator('#archPanel li').evaluateAll(ns => ns.map(n => n.firstChild ? n.firstChild.textContent : ''));
  out.details = await page.locator('#archPanel li details').count();
  out.block = await page.evaluate(b => capabilityBlockMessage(b), options.unworded ? BLOCKER_UNWORDED : FIX.blocker);
  out.over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  await page.close();
  return out;
}

function problems(r, expect = {}) {
  const p = [...r.problems];
  const want = expect.unworded ? [FIX.general[r.lang]] : FIX.sentences[r.lang];
  if (r.items.length !== want.length) p.push(`${r.items.length} findings listed, ${want.length} expected (a finding several checks share is said once)`);
  for (const s of want) if (!r.items.includes(s)) p.push(`a finding is not said as its words: ${s.slice(0, 60)}`);
  if (new Set(r.items).size !== r.items.length) p.push('the same sentence is listed twice');
  for (const re of PLATFORM) if (re.test(r.items.join(' ')) || re.test(r.block)) p.push(`the platform's own name is on the screen: ${re}`);
  const joined = r.items.join(' ') + ' ' + r.block;
  if (r.lang === 'he' && (LATIN_WORD.test(joined) || ARABIC.test(joined))) p.push('the Hebrew findings carry Latin or Arabic words');
  if (r.lang === 'ar' && (LATIN_WORD.test(joined) || HEBREW.test(joined))) p.push('the Arabic findings carry Latin or Hebrew words');
  if (r.lang === 'en' && (HEBREW.test(joined) || ARABIC.test(joined))) p.push('the English findings carry Hebrew or Arabic');
  const intro = { he: 'הבנייה לא התחילה: ', ar: 'لم يبدأ البناء: ', en: 'The build did not start: ' }[r.lang];
  if (!r.block.startsWith(intro)) p.push(`the blocker sentence does not start with "${intro}": ${r.block.slice(0, 50)}`);
  for (const s of want.slice(0, 3)) if (!r.block.includes(s)) p.push('the blocker sentence lacks a finding of the panel');
  if (expect.unworded) { /* the technical lines are the owner's; counted below as for any customer */ }
  if (expect.owner) { if (r.details !== want.length) p.push(`the owner sees ${r.details} technical lines, ${want.length} expected`); }
  else if (r.details !== 0) p.push(`a customer sees ${r.details} technical details`);
  if (r.over > 1) p.push(`${r.over}px sideways scroll`);
  return p;
}

const watchdog = setTimeout(() => { console.error(`::error title=feasibility words::the test ran past ${WATCHDOG_MS / 1000} s: something waits without end`); process.exit(2); }, WATCHDOG_MS);
(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const lang of ['he', 'ar', 'en']) {
      for (const width of [390, 1440]) {
        const r = await run(browser, lang, width, APP);
        const found = problems(r);
        if (found.length) failures.push(`${lang} ${width}px: ${found.join('; ')}`);
        else console.log(`::notice title=feasibility words::${lang} ${width}px: ${r.items.length} findings, each as its words with the next action, none of the platform's names, no technical details for a customer`);
      }
    }
    const owner = await run(browser, 'he', 1440, APP, { owner: true });
    const found = problems(owner, { owner: true });
    if (found.length) failures.push(`owner: ${found.join('; ')}`);
    else console.log(`::notice title=feasibility words::owner: the same words, and ${owner.details} technical lines that only the owner sees`);
    // a finding with no words (an older server): the general sentence, said once, never its item or reason
    for (const lang of ['he', 'ar', 'en']) {
      const r = await run(browser, lang, 390, APP, { unworded: true });
      const found = problems(r, { unworded: true });
      if (found.length) failures.push(`${lang} unworded: ${found.join('; ')}`);
      else console.log(`::notice title=feasibility words::${lang}: a finding with no words says the general sentence once, never its item or reason`);
    }
    // mutations: each must make the test fail
    const mutations = [
      ['the finding is printed as the gate wrote it (item: reason)', 'return `${w.what}: ${w.why}. ${w.next}.`;', 'return `${x.item}: ${x.reason}`;', 'ar'],
      ['the words ignore the customer\'s language', 'x.words[S.lang] || x.words.en', 'x.words.en', 'ar'],
      ['a customer sees the technical lines', "ownerView() ? h('details', {}, h('summary', {}, t('techDetails'))", "true ? h('details', {}, h('summary', {}, t('techDetails'))", 'he'],
      ['a finding several checks share is listed each time', 'return seen.has(said) ? false : (seen.add(said), true);', 'return true;', 'en'],
      ['a finding with no words says its item', "return w && w.what && w.why && w.next ? w : { what: t('findingGeneralWhat'), why: t('findingGeneralWhy'), next: t('findingGeneralNext') };",
        "return w && w.what && w.why && w.next ? w : { what: x.item, why: x.reason, next: '' };", 'he', { unworded: true }],
      ['the blocker sentence is the server\'s English message', "return t('buildNotStarted') + (rows.length", "return (detail.message || 'The build did not start. ') + (rows.length", 'ar'],
    ];
    for (const [what, from, to, lang, extra = {}] of mutations) {
      assert.equal(APP.split(from).length, 2, `the mutation line for "${what}" is in app.js exactly once`);
      let broke;
      try { broke = problems(await run(browser, lang, 390, APP.replace(from, to), { mutated: true, ...extra }), extra); } catch (e) { broke = [`threw: ${e.message.slice(0, 80)}`]; }
      if (!broke.length) failures.push(`with "${what}" the test still passes: it proves nothing`);
      else console.log(`::notice title=feasibility words::fails when ${what}, as it must (${broke[0].slice(0, 90)})`);
    }
  } finally {
    await browser.close();
    clearTimeout(watchdog);
  }
  if (failures.length) { for (const f of failures) console.error(`::error title=feasibility words::${f}`); process.exit(1); }
})().catch(e => { console.error(e); process.exit(1); });

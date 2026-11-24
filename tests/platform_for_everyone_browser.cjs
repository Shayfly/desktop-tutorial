/* The platform is usable by anyone who can read, from a child to an older person who knows nothing about computers
 * (the owner, 2026-11-22). Inbox 001 §6: the number of technical terms a person needs to start and finish is zero.
 *
 * Real Chromium, the real index.html, app.js, visual-edit.js and app.css; the server is mocked and goes through the
 * real boot path (sign-in, project list, conversation). Five checks, each in Hebrew and in English:
 *
 *   first      a first-time customer is not asked to name anything: the screen offers the conversation box and six
 *              examples; the first message creates the project, named from the message, and is sent to it. "New
 *              project" in the drawer opens an empty conversation the same way.
 *   words      no technical term on the entry, the first screen, the drawer, its dialogs, the preview or the history.
 *              The count per screen is printed: it is the owner's measure.
 *   text       reading text is at least 16px; only small print that labels other text (status, tag, speaker, id) is
 *              smaller, and never under 14px.
 *   targets    every control a finger can reach is at least 44x44px (warehouse 133), not only WCAG's 24px.
 *   size       "Text size" makes the text larger (16 -> 18 -> 20px), is kept after a reload, and at the largest size
 *              nothing scrolls sideways at 320px.
 *   look       the owner's example (2026-11-23): on a computer the project rail is open on the first visit; the top bar
 *              and the rail are dark, on a phone too; the preview's "Phone" switch shows the page 390px wide, and
 *              nothing scrolls sideways when it is on.
 *   build      the build screen (the example, screens 07 and 08): each step says its state in words, not colour alone,
 *              and neither the steps nor the check names use a technical term.
 *
 * A check that never fails proves nothing: every run also serves deliberately broken copies (MUTATIONS) and requires
 * the matching check to fail on each. A mutation that is not caught fails the run.
 *
 * Needs: playwright (CI: the browser-tests job). Local: NODE_PATH=<playwright's node_modules> CHROMIUM_PATH=<chrome>.
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const read = f => fs.readFileSync(path.join(ROOT, 'omni_prod/assets', f), 'utf8');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

// Technical terms a customer must not need. Hebrew and English; matched on what is on screen (innerText).
const TERMS = {
  he: [/SaaS/i, /ווב/, /קוד/, /דומיין/, /תבני(ת|ות)/, /\bZIP\b/i, /\bAPI\b/, /webhook/i, /טוקן/, /סשן/, /ארכיטקטורה/, /פריסה/, /רכיב/],
  en: [/SaaS/i, /\bweb app/i, /\bcode\b/i, /\bdomains?\b/i, /\btemplates?\b/i, /\bZIP\b/i, /\bAPI\b/, /webhook/i, /\btokens?\b/i,
    /\bsessions?\b/i, /\bdeploy/i, /\bsource\b/i, /\belement\b/i],
  ar: [/SaaS/i, /\bZIP\b/i, /\bAPI\b/, /webhook/i, /الكود|كود المصدر/, /نطاق/, /قوالب|القالب/, /عنصر/, /توكن/, /جلسة/],
};
// small print that labels other text; everything else that is read is at least 16px
const SMALL_PRINT = '.pill, .who, .sbStatus, .sidebar h3, .email, .sbFoot, .meta, code, pre, .url, .tech, .dept, .tk, .cost span';

// each deliberate fault: the file it changes, the exact text it replaces, and the check that must catch it
const MUTATIONS = [
  { id: 'name_asked_first', check: 'first', file: 'app.js',
    old: "    try { await createProject(titleFrom(text)); }", new: "    try { openNewProject(); return; }" },
  { id: 'term_back', check: 'words', file: 'app.js',
    old: "  scope: 'כרגע אפשר לבנות אתרים ומערכות", new: "  scope: 'כרגע אפשר לבנות אפליקציות ווב ו-SaaS, אתרים ומערכות" },
  { id: 'term_back_en', check: 'words', file: 'app.js', lang: 'en',
    old: "workspaceDomains: 'Web address',", new: "workspaceDomains: 'Domains'," },
  { id: 'small_text', check: 'text', file: 'app.css', append: '\n.welcomeChat p, .hint { font-size: 13px !important }' },
  { id: 'small_target', check: 'targets', file: 'app.css',
    append: '\n#chatSend { min-width: 36px !important; min-height: 36px !important; width: 36px !important; height: 36px !important }' },
  { id: 'size_not_kept', check: 'size', file: 'app.js',
    old: "  try { localStorage.setItem('148ai_text', currentTextSize); } catch { /* see above */ }", new: '' },
  { id: 'size_does_nothing', check: 'size', file: 'app.css', append: '\nhtml[data-text] { font-size: 100% !important }' },
  { id: 'rail_closed', check: 'look', file: 'visual-edit.js', width: 1440,
    old: "    } catch { /* defaults */ }\n    syncSidebar();", new: "      ws().classList.add('sb-collapsed');\n    } catch { /* defaults */ }\n    syncSidebar();" },
  { id: 'steps_hidden_on_phone', check: 'look', file: 'app.css', append: '\n@media (max-width:900px){ .welcomeCopy .howto { display: none !important } }' },
  { id: 'steps_before_form', check: 'look', file: 'app.css', append: '\n@media (max-width:900px){ .auth { order: 9 !important } }' },
  { id: 'light_top_bar', check: 'look', file: 'app.css', append: '\n.workspace > .mobileWorkspaceHead { background: #ffffff !important }' },
  { id: 'phone_view_ignored', check: 'look', file: 'app.css', width: 1440,
    append: '\n.workspace[data-device="phone"] .stage .viewport { width: 100% !important }' },
  { id: 'state_in_colour_only', check: 'build', file: 'app.js',
    old: "h('span', { class: 'pill stepTag' }, t('stepState')[state] || state),", new: "" },
  { id: 'step_term_back', check: 'build', file: 'app.js',
    old: "stepGenerate: 'בונים את האתר'", new: "stepGenerate: 'יצירת קוד ובנייה בסביבת ווב'" },
];

function served(mutation) {
  const files = { 'app.js': read('app.js'), 'visual-edit.js': read('visual-edit.js'), 'app.css': read('app.css') };
  if (mutation) {
    const f = files[mutation.file];
    if (mutation.append) files[mutation.file] = f + mutation.append;
    else {
      assert.equal(f.split(mutation.old).length, 2, `mutation ${mutation.id}: its text is in ${mutation.file} exactly once`);
      files[mutation.file] = f.replace(mutation.old, mutation.new);
    }
  }
  return files;
}

// the server: real boot path, a new account with no project
async function open(browser, { lang, width, signedIn = true, files, projects = [] }) {
  const page = await browser.newPage({ viewport: { width, height: 844 } });
  const server = { signedIn, projects: projects.slice(), created: [], sent: [], errors: [] };
  page.on('pageerror', e => server.errors.push(String(e)));
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* private mode */ } }, lang);
  await page.route('**/*', async route => {
    const req = route.request(), u = new URL(req.url()), p = u.pathname, json = b => route.fulfill({ contentType: 'application/json', body: JSON.stringify(b) });
    if (p === '/fixture') return route.fulfill({ contentType: 'text/html', body: read('index.html') });
    if (p.startsWith('/assets/')) {
      const name = p.slice('/assets/'.length);
      if (files[name] !== undefined) return route.fulfill({ contentType: name.endsWith('.css') ? 'text/css' : 'application/javascript', body: files[name] });
      return route.fulfill({ path: path.join(ROOT, 'omni_prod', p) });
    }
    if (p === '/api/v28/me') return server.signedIn ? json({ email: 'new@example.test' }) : route.fulfill({ status: 401, contentType: 'application/json', body: '{}' });
    if (p === '/api/v28/m5/status') return json({ blockers: [] });
    if (p === '/api/v28/projects' && req.method() === 'POST') {
      const project = { id: `p${server.projects.length + 1}`, title: req.postDataJSON().title, created_at: new Date().toISOString() };
      server.projects.unshift(project); server.created.push(project.title);
      return json(project);
    }
    if (p === '/api/v28/projects') return json({ projects: server.projects });
    if (/\/conversation$/.test(p) && req.method() === 'POST') {
      const body = req.postDataJSON(); server.sent.push({ project: p.split('/')[4], message: body.message });
      return json({ messages: [{ role: 'customer', content: body.message }, { role: 'assistant', content: lang === 'he' ? 'איך קוראים לעסק?' : 'What is the business called?' }], turn: { actions: [] } });
    }
    if (/\/conversation$/.test(p)) return json({ messages: [], turn: { actions: [] } });
    if (/\/builds\/latest$/.test(p)) return json({ build: null });
    if (/\/history$/.test(p)) return json({ versions: [] });
    if (p.startsWith('/api/')) return json({});
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && typeof showView === 'function');
  await page.waitForFunction(s => s ? Boolean(S.signedIn) : !document.getElementById('welcomeView').hidden, signedIn);
  await page.waitForTimeout(250);
  return { page, server };
}

const visibleText = page => page.evaluate(() => document.body.innerText);
async function termsOn(page, lang) {
  const text = await visibleText(page);
  return TERMS[lang].filter(re => re.test(text)).map(re => `${re.source} in "${(text.match(re) || [''])[0]}"`);
}

// every visible text smaller than 16px that is not small print, and small print under 14px
async function smallText(page) {
  return page.evaluate(small => {
    const out = [], walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode, el = node.parentElement;
      if (!node.textContent.trim() || !el || el.closest('.sr, [aria-hidden="true"]')) continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height || !el.checkVisibility({ visibilityProperty: true })) continue;
      const size = parseFloat(getComputedStyle(el).fontSize), isSmall = Boolean(el.closest(small));
      if (size < (isSmall ? 14 : 16) - 0.01) out.push(`${size}px "${node.textContent.trim().slice(0, 30)}"`);
    }
    return out;
  }, SMALL_PRINT);
}

// every control under 44x44 (an inline link inside a sentence is exempt, as in WCAG; a checkbox counts with its label)
async function smallTargets(page) {
  return page.evaluate(() => {
    const out = [];
    for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=tab]')) {
      if (el.disabled) continue;
      if (el.tagName === 'A' && getComputedStyle(el).display === 'inline') continue;
      if (el.classList.contains('skip') && document.activeElement !== el) continue;      // shown only when focused
      const box = (['checkbox', 'radio'].includes(el.type) && el.closest('label')) || el;
      const r = box.getBoundingClientRect();
      if (!r.width || !r.height || !el.checkVisibility({ visibilityProperty: true })) continue;
      if (r.width < 43.5 || r.height < 43.5) out.push(`${el.id ? '#' + el.id : el.tagName.toLowerCase()} "${(el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 20)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    return out;
  });
}
async function sideScroll(page) { return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth); }

// the screens a customer meets: each is opened, measured, and closed again
async function screens(page, width, measure) {
  const found = {};
  const take = async name => { found[name] = await measure(page); };
  await take('first screen');
  const opener = page.locator(width <= 900 ? '#mobileMenuBtn' : '#sbOpen');
  if (await opener.isVisible()) {
    await opener.click(); await page.waitForTimeout(150);
    await take('drawer');
    for (const id of ['sbTemplates', 'sbDomains']) {
      await page.locator(`#${id}`).click(); await page.waitForTimeout(100);
      await take(`drawer: ${id === 'sbTemplates' ? 'ideas' : 'web address'}`);
      await page.locator('#workspaceDialog form[method=dialog] button').click(); await page.waitForTimeout(100);
      if (width <= 900 && !(await page.locator('#sidebar').evaluate(el => el.inert === false))) { await opener.click(); await page.waitForTimeout(100); }
    }
    if (width <= 900) { await page.keyboard.press('Escape'); await page.waitForTimeout(100); }
  }
  for (const pane of ['preview', 'versions']) {
    await page.evaluate(p => window.VE && VE.setPane(p), pane); await page.waitForTimeout(100);
    await take(pane === 'preview' ? 'preview' : 'history');
  }
  await page.evaluate(() => window.VE && VE.setPane('chat'));
  return found;
}

// relative luminance of an element's own background (WCAG formula); dark is under 0.05
const DARK = () => { const lum = el => { const m = getComputedStyle(el).backgroundColor.match(/[\d.]+/g).map(Number);
  const [r, g, b] = m.slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  return { head: lum(document.querySelector('.workspace > .mobileWorkspaceHead')), rail: lum(document.getElementById('sidebar')) }; };

const CHECKS = {
  async build(browser, lang, width, files) {
    const fail = [];
    const { page } = await open(browser, { lang, width, files, projects: [{ id: 'p1', title: lang === 'he' ? 'סטודיו נועה' : 'Noa Studio' }] });
    await page.evaluate(() => {
      S.build = { id: 'b1', status: 'running', phase: 'GENERATE', evidence: {} };
      S.plan = { status: 'READY', can_build: true, capabilities: [], infrastructure: [], product: {} };
      renderTrack(); openTab('build');
    });
    await page.waitForTimeout(250);
    const steps = await page.evaluate(() => [...document.querySelectorAll('#track .step')].map(li => ({
      name: (li.querySelector('.name') || {}).textContent || '', tag: (li.querySelector('.stepTag') || {}).textContent || '' })));
    if (steps.length < 5) fail.push(`${steps.length} build steps on the screen`);
    for (const st of steps) if (!st.tag.trim()) fail.push(`the step "${st.name.trim()}" says its state in colour alone`);
    const text = await page.locator('#progressPanel').innerText();
    const terms = TERMS[lang].filter(re => re.test(text)).map(re => re.source);
    if (terms.length) fail.push(`build screen: ${terms.join(', ')}`);
    console.log(`::notice title=technical terms::${lang} ${width}px build screen: ${terms.length}`);
    await page.close();
    return fail;
  },
  async look(browser, lang, width, files) {
    const fail = [];
    // the entry (2026-11-23): on a phone the form comes first and the three steps follow it, visible
    const entry = await open(browser, { lang, width, files, signedIn: false });
    const where = await entry.page.evaluate(() => {
      const top = s => { const el = document.querySelector(s); return el && el.checkVisibility() ? el.getBoundingClientRect().top : null; };
      return { form: top('#authForm'), steps: top('.welcomeCopy .howto'), lead: top('.auth .authLead') };
    });
    await entry.page.close();
    if (where.steps === null) fail.push('the entry does not show the three steps');
    else if (width <= 900 && !(where.form < where.steps)) fail.push('on a phone the steps push the sign-in form down');
    if (where.lead === null) fail.push('the sign-in card does not say nothing happens without approval');
    const { page } = await open(browser, { lang, width, files, projects: [{ id: 'p1', title: lang === 'he' ? 'סטודיו נועה' : 'Noa Studio' }] });
    if (width > 900) {
      const rail = await page.evaluate(() => { const r = document.getElementById('sidebar').getBoundingClientRect();
        return { w: Math.round(r.width), inView: r.left >= 0 && r.right <= window.innerWidth + 1, inert: document.getElementById('sidebar').inert }; });
      if (rail.w < 200 || !rail.inView || rail.inert) fail.push(`the project rail is not open on a computer (${JSON.stringify(rail)})`);
    } else {
      await page.locator('#mobileMenuBtn').click(); await page.waitForTimeout(200);
    }
    // the preview as a phone sees it (screen 09 of the example)
    if (width <= 900) { await page.keyboard.press('Escape'); await page.waitForTimeout(100); }
    await page.evaluate(() => window.VE && VE.setPane('preview')); await page.waitForTimeout(100);
    const vpWidth = () => page.evaluate(() => Math.round(document.getElementById('viewport').getBoundingClientRect().width));
    await page.locator('#devPhone').click(); await page.waitForTimeout(100);
    const phone = await vpWidth();
    if (phone > 391) fail.push(`"Phone" shows the page ${phone}px wide, not 390`);
    if ((await page.locator('#devPhone').getAttribute('aria-pressed')) !== 'true') fail.push('"Phone" is not marked as chosen');
    const over = await sideScroll(page);
    if (over > 1) fail.push(`"Phone" on: ${over}px sideways scroll`);
    await page.locator('#devDesktop').click(); await page.waitForTimeout(100);
    if (width > 900 && (await vpWidth()) < 600) fail.push('"Computer" does not give the page its width back');
    await page.evaluate(() => window.VE && VE.setPane('chat'));
    if (width <= 900) { await page.locator('#mobileMenuBtn').click(); await page.waitForTimeout(200); }
    const dark = await page.evaluate(DARK);
    if (!(dark.head < 0.05)) fail.push(`the top bar is not dark (luminance ${dark.head.toFixed(3)})`);
    if (!(dark.rail < 0.05)) fail.push(`the project rail is not dark (luminance ${dark.rail.toFixed(3)})`);
    await page.close();
    return fail;
  },
  async first(browser, lang, width, files) {
    const { page, server } = await open(browser, { lang, width, files });
    const fail = [];
    if (await page.locator('#firstProjectName, #newProjectName').count()) fail.push('a project name field is still on the page');
    if (!(await page.locator('#chatInput').isVisible())) fail.push('the conversation box is not on the first screen');
    const examples = page.locator('.welcomeChat .workspaceExamples button');
    if ((await examples.count()) < 6) fail.push(`${await examples.count()} examples, not 6`);
    else {
      await examples.nth(1).click();
      const prompt = await page.locator('#chatInput').inputValue();
      await page.locator('#chatSend').click();
      await page.waitForTimeout(600);
      const title = server.created[0] || '';
      if (server.created.length !== 1) fail.push(`${server.created.length} projects created by the first message, not 1`);
      else if (!title || title === (lang === 'he' ? 'פרויקט חדש' : 'New project') || title.length > 41) fail.push(`project named "${title}"`);
      if (!server.sent.length || server.sent[0].message !== prompt) fail.push('the first message did not reach the new project');
      else if (!(await page.locator('#thread').innerText()).includes(prompt.slice(0, 20))) fail.push('the first message is not in the conversation');
      // "New project" in the drawer: an empty conversation, no name asked
      if (!fail.length) {
        const opener = page.locator(width <= 900 ? '#mobileMenuBtn' : '#sbOpen');
        if (await opener.isVisible()) await opener.click();
        await page.locator('#newProjectTopBtn').click(); await page.waitForTimeout(250);
        const dialogs = await page.evaluate(() => [...document.querySelectorAll('dialog')].filter(d => d.open).length);
        if (dialogs) fail.push('"New project" opened a dialog');
        if (!(await page.locator('.welcomeChat').isVisible())) fail.push('"New project" did not open an empty conversation');
        await page.locator('#chatInput').fill(lang === 'he' ? 'אני רוצה דף לחוג הריקוד שלי, עם שעות ומחיר' : 'I want a page for my dance class, with hours and price');
        await page.locator('#chatSend').click(); await page.waitForTimeout(600);
        const second = server.created[1] || '';
        if (second !== (lang === 'he' ? 'דף לחוג הריקוד שלי' : 'a page for my dance class')) fail.push(`second project named "${second}"`);
      }
    }
    if (server.errors.length) fail.push(`page errors: ${server.errors.slice(0, 2).join(' | ')}`);
    await page.close();
    return fail;
  },
  async words(browser, lang, width, files) {
    const fail = [];
    const entry = await open(browser, { lang, width, files, signedIn: false });
    const onEntry = await termsOn(entry.page, lang);
    console.log(`::notice title=technical terms::${lang} ${width}px entry: ${onEntry.length}`);
    if (onEntry.length) fail.push(`entry: ${onEntry.join(', ')}`);
    await entry.page.close();
    const { page } = await open(browser, { lang, width, files });
    const found = await screens(page, width, p => termsOn(p, lang));
    for (const [screen, terms] of Object.entries(found)) {
      console.log(`::notice title=technical terms::${lang} ${width}px ${screen}: ${terms.length}`);
      if (terms.length) fail.push(`${screen}: ${terms.join(', ')}`);
    }
    await page.close();
    return fail;
  },
  async text(browser, lang, width, files) {
    const fail = [];
    const entry = await open(browser, { lang, width, files, signedIn: false });
    const onEntry = await smallText(entry.page);
    if (onEntry.length) fail.push(`entry: ${onEntry.slice(0, 6).join(', ')}`);
    await entry.page.close();
    const { page } = await open(browser, { lang, width, files, projects: [{ id: 'p1', title: lang === 'he' ? 'סטודיו נועה' : 'Noa Studio' }] });
    for (const [screen, small] of Object.entries(await screens(page, width, smallText))) if (small.length) fail.push(`${screen}: ${small.slice(0, 6).join(', ')}`);
    await page.close();
    return fail;
  },
  async targets(browser, lang, width, files) {
    const fail = [];
    const entry = await open(browser, { lang, width, files, signedIn: false });
    const onEntry = await smallTargets(entry.page);
    if (onEntry.length) fail.push(`entry: ${onEntry.slice(0, 6).join(', ')}`);
    await entry.page.close();
    const { page } = await open(browser, { lang, width, files, projects: [{ id: 'p1', title: lang === 'he' ? 'סטודיו נועה' : 'Noa Studio' }] });
    for (const [screen, small] of Object.entries(await screens(page, width, smallTargets))) if (small.length) fail.push(`${screen}: ${small.slice(0, 6).join(', ')}`);
    await page.close();
    return fail;
  },
  async size(browser, lang, width, files) {
    const fail = [];
    const { page } = await open(browser, { lang, width: 320, files, signedIn: false });
    const px = () => page.evaluate(() => parseFloat(getComputedStyle(document.querySelector('#heroLead')).fontSize));
    const base = await px();
    await page.locator('#textSizeBtn').click(); const large = await px();
    await page.locator('#textSizeBtn').click(); const xlarge = await px();
    if (!(large > base * 1.1 && xlarge > large * 1.05)) fail.push(`text did not grow: ${base} -> ${large} -> ${xlarge}px`);
    await page.reload(); await page.waitForFunction(() => typeof S === 'object'); await page.waitForTimeout(250);
    if ((await px()) !== xlarge) fail.push(`after a reload the text is ${await px()}px, not the chosen ${xlarge}px`);
    const over = await sideScroll(page);
    if (over > 1) fail.push(`entry at 320px, largest text: ${over}px sideways scroll`);
    await page.close();
    // the workspace at the largest size, kept from the entry (same device)
    const ws = await open(browser, { lang, width: 320, files, projects: [{ id: 'p1', title: lang === 'he' ? 'סטודיו נועה' : 'Noa Studio' }] });
    await ws.page.evaluate(() => { localStorage.setItem('148ai_text', 'xlarge'); });
    await ws.page.reload(); await ws.page.waitForFunction(() => typeof S === 'object' && S.signedIn); await ws.page.waitForTimeout(250);
    const found = await screens(ws.page, 320, sideScroll);
    for (const [screen, o] of Object.entries(found)) if (o > 1) fail.push(`${screen} at 320px, largest text: ${o}px sideways scroll`);
    await ws.page.close();
    return fail;
  },
};

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    const real = served(null);
    for (const lang of ['he', 'en', 'ar']) {
      for (const [name, check] of Object.entries(CHECKS)) {
        for (const width of name === 'size' ? [320] : [390, 1440]) {
          const fail = await check(browser, lang, width, real);
          if (fail.length) failures.push(`${name} ${lang} ${width}px: ${fail.join('; ')}`);
          else console.log(`::notice title=for everyone::${name} ${lang} ${width}px holds`);
        }
      }
    }
    for (const m of MUTATIONS) {
      const lang = m.lang || 'he';
      const fail = await CHECKS[m.check](browser, lang, m.width || 390, served(m));
      if (!fail.length) failures.push(`mutation ${m.id} was NOT caught by the "${m.check}" check`);
      else console.log(`::notice title=for everyone mutation::${m.id}: caught by "${m.check}" (${fail[0].slice(0, 120)})`);
    }
  } finally {
    await browser.close();
  }
  if (failures.length) {
    for (const f of failures) console.log(`::error title=for everyone::${f}`);
    process.exit(1);
  }
  console.log(`::notice title=for everyone::${Object.keys(CHECKS).length} checks x 3 languages hold; ${MUTATIONS.length}/${MUTATIONS.length} mutations caught`);
})().catch(e => { console.error(e); process.exit(1); });

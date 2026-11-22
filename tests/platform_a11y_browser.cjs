/* The platform UI meets WCAG 2.2 AA (the owner, 2026-11-22: "נגישה לכל אדם"; DECISIONS, the platform UI moves to Claude Code).
 *
 * Real Chromium, the real index.html, app.js and app.css, the server mocked (no live provider, no build). For every
 * language the UI offers and at 320, 390 and 1440 px, each screen -- the entry, the chat, the preview, the versions and
 * the project drawer -- is checked by axe-core (rules tagged wcag2a, wcag2aa, wcag21a, wcag21aa, wcag22aa) and by two
 * measures of our own: no horizontal scroll, and a visible focus on every control the keyboard reaches.
 *
 * A check that never fails proves nothing, so every run also injects deliberate faults (MUTATIONS below) and requires
 * the same check to catch each one. A mutation that is not caught fails the run, as does any violation on the real UI.
 *
 * Needs: playwright and axe-core (CI: npm install --no-save playwright@1.62.1 axe-core@4.10.3). Local:
 *   AXE_PATH=/path/to/axe-core/axe.min.js node tests/platform_a11y_browser.cjs
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const AXE = process.env.AXE_PATH || require.resolve('axe-core/axe.min.js');
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const WIDTHS = [320, 390, 1440];
const LANGS = ['he', 'en'];
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

// each fault, and the finding that must catch it
const MUTATIONS = [
  { id: 'low_contrast', css: 'body, body * { color: #9a9a9a !important; background-color: #ffffff !important }', expect: 'color-contrast' },
  { id: 'button_without_name', js: `(() => { const b = document.querySelector('#workspaceView button:not([hidden])') || document.querySelector('button');
      b.textContent = ''; b.removeAttribute('aria-label'); b.removeAttribute('title'); b.removeAttribute('aria-labelledby');
      b.setAttribute('data-i18n', ''); b.removeAttribute('data-i18n-label'); })()`, expect: 'button-name' },
  { id: 'horizontal_scroll', css: 'body { min-width: 360px !important; overflow: visible !important }', expect: 'horizontal-scroll', width: 320 },
  // small AND adjacent: WCAG 2.5.8 exempts a small target with 24px of spacing around it
  { id: 'small_target', css: '#mobileTabs { display: flex !important; gap: 0 !important; justify-content: flex-start !important } #mobileTabs button { flex: 0 0 12px !important; min-height: 12px !important; height: 12px !important; min-width: 12px !important; width: 12px !important; padding: 0 !important; margin: 0 !important; border: 0 !important; font-size: 4px !important; overflow: hidden }',
    expect: 'target-size', width: 390 },
  { id: 'image_without_alt', js: `(() => { const i = document.createElement('img'); i.src = 'data:image/gif;base64,R0lGODlhAQABAAAAACw='; i.width = 40; i.height = 40;
      (document.querySelector('main') || document.body).appendChild(i); })()`, expect: 'image-alt' },
  { id: 'no_language', js: `document.documentElement.removeAttribute('lang')`, expect: 'html-has-lang' },
  // every :focus rule removed from the page's stylesheets, and the browser's own ring turned off: no focus sign at all
  { id: 'focus_hidden', css: '* { outline: none !important }',
    js: `for (const sheet of document.styleSheets) { let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
      for (let i = rules.length - 1; i >= 0; i--) { if (/:focus/.test(rules[i].selectorText || '')) sheet.deleteRule(i); } }`,
    expect: 'focus-visible' },
];

async function open(browser, lang, width, mutation) {
  const page = await browser.newPage({ viewport: { width, height: 844 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(l => { try { localStorage.setItem('148ai_lang', l); } catch (e) { /* private mode */ } }, lang);
  await page.route('**/*', async route => {
    const u = new URL(route.request().url());
    if (u.pathname === '/api/v28/me') return route.fulfill({ status: 401, contentType: 'application/json', body: '{}' });
    if (u.pathname === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (u.pathname === '/assets/app.css' && mutation && mutation.css) {
      return route.fulfill({ contentType: 'text/css', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.css'), 'utf8') + '\n' + mutation.css });
    }
    if (u.pathname.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', u.pathname) });
    if (u.pathname.startsWith('/api/')) {
      return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ projects: [], messages: [], versions: [], turn: { actions: [] } }) });
    }
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && typeof showView === 'function');
  await page.waitForTimeout(300);
  return { page, errors };
}

async function signIn(page) {
  await page.evaluate(() => {
    S.signedIn = true; S.me = { email: 'a11y@example.test' };
    S.projects = [{ id: 'p', title: 'סטודיו נועה', status: 'READY' }, { id: 'q', title: 'Noa Studio' }];
    S.projectId = 'p';
    S.chat = { messages: [{ role: 'customer', content: 'אתר תדמית למספרה' }, { role: 'assistant', content: 'איך קוראים לעסק?' }] };
    showView();
    try { renderProjects(); } catch (e) { /* the list renders on its own call too */ }
  });
  await page.waitForTimeout(200);
}

// our own measures, reported in axe's shape so one list holds every finding
async function ownFindings(page) {
  return page.evaluate(() => {
    const found = [];
    const over = document.documentElement.scrollWidth - window.innerWidth;
    if (over > 1) found.push({ id: 'horizontal-scroll', nodes: [`document ${over}px wider than the ${window.innerWidth}px viewport`] });
    const visible = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
    const controls = [...document.querySelectorAll('a[href], button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"])')]
      .filter(el => !el.disabled && visible(el)).slice(0, 40);
    // a focus indicator may be drawn on the control or on its wrapper (:focus-within): the control and two ancestors
    const one = el => { if (!el) return ''; const s = getComputedStyle(el);
      return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.backgroundColor, s.textDecorationLine].join('|'); };
    const look = el => [el, el.parentElement, el.parentElement && el.parentElement.parentElement].map(one).join('#');
    const unfocused = [];
    for (const el of controls) {
      const before = look(el);
      el.focus({ focusVisible: true });
      if (document.activeElement === el && look(el) === before) unfocused.push(el.id ? `#${el.id}` : el.tagName.toLowerCase());
      el.blur();
    }
    if (unfocused.length) found.push({ id: 'focus-visible', nodes: unfocused.slice(0, 8) });
    // WCAG 2.5.8 (AA): a target under 24x24 passes only if a 24px circle on its centre touches no other target.
    // axe leaves roving-tabindex tabs (tabindex=-1) as "incomplete", so this is measured here for every control;
    // an inline link inside text is exempt, as in the standard.
    const targets = [...document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=tab], [role=button]')]
      .filter(el => visible(el) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'));
    const rects = targets.map(el => el.getBoundingClientRect());
    const small = [];
    targets.forEach((el, i) => {
      const r = rects[i];
      if (r.width >= 24 && r.height >= 24) return;
      const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      const near = rects.some((o, j) => j !== i && !targets[j].contains(el) && !el.contains(targets[j]) &&
        Math.hypot(Math.max(o.left - cx, 0, cx - o.right), Math.max(o.top - cy, 0, cy - o.bottom)) < 12);
      if (near) small.push(`${el.id ? '#' + el.id : el.tagName.toLowerCase()} ${Math.round(r.width)}x${Math.round(r.height)}`);
    });
    if (small.length) found.push({ id: 'target-size', nodes: small.slice(0, 8) });
    return found;
  });
}

async function check(page) {
  await page.addScriptTag({ path: AXE });
  const axe = await page.evaluate(async tags => {
    const r = await window.axe.run(document, { runOnly: { type: 'tag', values: tags } });
    return r.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.slice(0, 5).map(n => n.target.join(' ')) }));
  }, TAGS);
  return [...axe, ...await ownFindings(page)];
}

async function screens(page, width) {
  const out = [];
  out.push(['workspace', await check(page)]);
  if (width <= 900) {
    for (const pane of ['preview', 'versions', 'chat']) {
      const tab = page.locator(`#mobileTabs button[data-pane="${pane}"]`);
      assert.ok(await tab.isVisible(), `the ${pane} tab is visible at ${width}px`);
      await tab.click();
      await page.waitForTimeout(150);
      assert.equal(await page.locator('#workspaceView').getAttribute('data-pane'), pane);
      out.push([pane, await check(page)]);
    }
  }
  const opener = page.locator(width <= 900 ? '#mobileMenuBtn' : '#sbOpen');
  if (await opener.isVisible().catch(() => false)) {
    await opener.click();
    await page.waitForTimeout(200);
    out.push(['drawer', await check(page)]);
  }
  return out;
}

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    // the real UI: no finding on any screen, in any language, at any width
    for (const lang of LANGS) {
      for (const width of WIDTHS) {
        const { page, errors } = await open(browser, lang, width);
        const entry = await check(page);
        await signIn(page);
        const all = [['entry', entry], ...await screens(page, width)];
        for (const [screen, found] of all) {
          const line = `${lang} ${width}px ${screen}`;
          if (found.length) failures.push(`${line}: ${found.map(f => `${f.id} ${JSON.stringify(f.nodes)}`).join('; ')}`);
          else console.log(`::notice title=platform a11y::${line}: no WCAG 2.2 AA finding`);
        }
        if (errors.length) failures.push(`${lang} ${width}px: page errors ${errors.slice(0, 3).join(' | ')}`);
        await page.close();
      }
    }
    // the check catches each deliberate fault
    for (const m of MUTATIONS) {
      const width = m.width || 390;
      const { page } = await open(browser, 'he', width, m);
      await signIn(page);
      if (m.js) await page.evaluate(m.js);
      const found = await check(page);
      const caught = found.some(f => f.id === m.expect);
      if (!caught) failures.push(`mutation ${m.id} was NOT caught (expected ${m.expect}; found ${found.map(f => f.id).join(', ') || 'nothing'})`);
      else console.log(`::notice title=platform a11y mutation::${m.id}: caught by ${m.expect}`);
      await page.close();
    }
  } finally {
    await browser.close();
  }
  if (failures.length) {
    for (const f of failures) console.log(`::error title=platform a11y::${f}`);
    process.exit(1);
  }
  console.log(`::notice title=platform a11y::${LANGS.length} languages x ${WIDTHS.length} widths clean; ${MUTATIONS.length}/${MUTATIONS.length} mutations caught`);
})().catch(e => { console.error(e); process.exit(1); });

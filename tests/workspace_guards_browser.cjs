/* The guards the platform design added against late answers (warehouse 133, review item T2, 2026-11-22).
 *
 * Codex's design added three guards to app.js and no test caught any of them: taking one out passed every check.
 * Real Chromium, the real index.html, app.js and app.css, the server mocked and its answers held back on purpose. Each
 * scenario runs twice: on the code as it is, where it must pass, and with its one guard taken out (OLD below: the
 * exact line), where it must FAIL. A scenario that also passes without its guard proves nothing, and fails this run.
 *
 *   Q1  a quote that was asked first but answers last does not replace the newer quote (loadProposal)
 *   P1  a plan answered after a newer plan request does not replace it (requestBriefPlan, the request check)
 *   P2  a plan answered after the brief changed is not shown for the new brief (requestBriefPlan, the revision check)
 *   R1  a restore answered after the customer moved to another project does not clear that project's preview
 *   R2  "restored" is not announced on the other project when the move happened while the versions reloaded
 *   R3  a failed restore does not show its error on the other project
 *   R4  a second click on "restore" while the first is running sends no second rollback
 *   R5  on the same project, a restore announces itself and clears the old preview (the guards block nothing real)
 */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const APP = fs.readFileSync(path.join(ROOT, 'omni_prod/assets/app.js'), 'utf8');
const browserOptions = process.env.CHROMIUM_PATH
  ? { executablePath: process.env.CHROMIUM_PATH, args: ['--no-sandbox', '--disable-gpu'] } : {};

// the guard each scenario stands on, and the code without it
const OLD = {
  Q1: ['  if (S.proposalLoad !== load) return;\n', ''],
  P1: ['    if (!current()) return;\n    S.plan = plan;\n', '    S.plan = plan;\n'],
  P2: ['  const current = () => S.planRequest === request && S.disc?.brief?.revision === briefRevision;\n',
       '  const current = () => S.planRequest === request;\n'],
  R1: ['    if (!stillOn(project)) return;\n    clearTimeout(S.timers.preview);\n', '    clearTimeout(S.timers.preview);\n'],
  R2: ["    if (stillOn(project)) { notice.className = 'msg ok'; notice.textContent = t('restored'); }\n",
       "    notice.className = 'msg ok'; notice.textContent = t('restored');\n"],
  R3: ["    if (stillOn(project)) { notice.className = 'msg'; notice.textContent = explain(e); }\n",
       "    notice.className = 'msg'; notice.textContent = explain(e);\n"],
  R4: ['  if (activeVersionRestores.has(project)) return;\n', ''],
};
for (const [id, [now]] of Object.entries(OLD)) assert.equal(APP.split(now).length, 2, `${id}: the guard is in app.js exactly once`);

const json = (route, body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
const hold = () => { let release; const held = new Promise(r => { release = r; }); return { held, release }; };
const settle = page => page.waitForTimeout(350);

async function open(browser, guard, routes = {}) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.addInitScript(() => { try { localStorage.setItem('148ai_lang', 'he'); } catch (e) { /* private mode */ } });
  await page.route('**/*', async route => {
    const u = new URL(route.request().url());
    for (const [suffix, handler] of Object.entries(routes)) if (u.pathname.endsWith(suffix)) return handler(route, u);
    if (u.pathname === '/api/v28/me') return json(route, {}, 401);
    if (u.pathname === '/fixture') return route.fulfill({ contentType: 'text/html', body: fs.readFileSync(path.join(ROOT, 'omni_prod/assets/index.html'), 'utf8') });
    if (u.pathname === '/assets/app.js' && OLD[guard]) return route.fulfill({ contentType: 'text/javascript', body: APP.replace(OLD[guard][0], OLD[guard][1]) });
    if (u.pathname.startsWith('/assets/')) return route.fulfill({ path: path.join(ROOT, 'omni_prod', u.pathname) });
    if (u.pathname.startsWith('/api/')) return json(route, { projects: [], messages: [], versions: [], history: [], turn: { actions: [] } });
    return route.fulfill({ status: 404, body: '' });
  });
  await page.goto('http://platform.test/fixture');
  await page.waitForFunction(() => typeof S === 'object' && typeof showView === 'function');
  await page.waitForTimeout(300);
  await page.evaluate(() => { S.signedIn = true; S.me = { email: 'guards@example.test' }; S.projects = [{ id: 'a', title: 'A' }, { id: 'b', title: 'B' }]; showView(); });
  return { page, errors };
}

const VERSIONS = { versions: [{ id: 'ver_2', title: 'גרסה 2', created_at: '2026-11-22T12:00:00Z' }, { id: 'ver_1', title: 'גרסה 1', created_at: '2026-11-22T11:00:00Z' }] };

const SCENARIOS = {
  async Q1(browser, guard) {
    const first = hold();
    let calls = 0;
    const { page, errors } = await open(browser, guard, {
      '/projects/a/proposal': async route => {
        calls += 1;
        if (calls === 1) { await first.held; return json(route, { revision: 1, price: { amount_ils: 111 } }); }
        return json(route, { revision: 2, price: { amount_ils: 222 } });
      },
    });
    await page.evaluate(() => { S.projectId = 'a'; loadProposal(); loadProposal(); });
    await settle(page);
    first.release();
    await settle(page);
    const shown = await page.evaluate(() => ({ amount: S.proposal && S.proposal.price.amount_ils, chip: document.getElementById('workspaceProjectChip').textContent }));
    await page.close();
    assert.equal(calls, 2, 'both quotes were asked');
    assert.equal(shown.amount, 222, `the newer quote stays (shown: ${JSON.stringify(shown)})`);
    assert.match(shown.chip, /222/, 'the header shows the newer quote');
    assert.deepEqual(errors, []);
  },
  async P1(browser, guard) {
    const first = hold();
    let calls = 0;
    const { page, errors } = await open(browser, guard, {
      '/projects/a/build-contracts': async route => {
        calls += 1;
        if (calls === 1) { await first.held; return json(route, { contract_id: 'old_request', can_build: true }); }
        return json(route, { contract_id: 'new_request', can_build: true });
      },
    });
    await page.evaluate(() => {
      S.projectId = 'a'; S.disc = { complete: true, prompt: 'אתר למספרה', brief: { revision: 1 }, questions: [] };
      requestBriefPlan(false); requestBriefPlan(false);
    });
    await settle(page);
    first.release();
    await settle(page);
    const plan = await page.evaluate(() => S.plan && S.plan.contract_id);
    await page.close();
    assert.equal(calls, 2, 'both plans were asked');
    assert.equal(plan, 'new_request', `the plan of the newer request stays (shown: ${plan})`);
    assert.deepEqual(errors, []);
  },
  async P2(browser, guard) {
    const first = hold();
    const { page, errors } = await open(browser, guard, {
      '/projects/a/build-contracts': async route => { await first.held; return json(route, { contract_id: 'for_revision_1', can_build: true }); },
    });
    await page.evaluate(() => {
      S.projectId = 'a'; S.disc = { complete: true, prompt: 'אתר למספרה', brief: { revision: 1 }, questions: [] };
      requestBriefPlan(false);
    });
    await settle(page);
    await page.evaluate(() => { S.disc.brief.revision = 2; });   // the customer changed the brief meanwhile
    first.release();
    await settle(page);
    const plan = await page.evaluate(() => S.plan && S.plan.contract_id);
    await page.close();
    assert.equal(plan ?? null, null, `a plan for the old brief is not shown for the new one (shown: ${plan})`);
    assert.deepEqual(errors, []);
  },
  async R1(browser, guard) {
    const rollback = hold();
    const { page, errors } = await open(browser, guard, {
      '/projects/a/history': route => json(route, VERSIONS),
      '/projects/a/rollback': async route => { await rollback.held; return json(route, { ok: true }); },
    });
    await page.evaluate(() => selectProject('a'));
    await settle(page);
    await page.evaluate(() => { restoreVersion('ver_1'); });
    await settle(page);
    await page.evaluate(() => selectProject('b'));
    await settle(page);
    await page.evaluate(() => { S.preview = { preview_id: 'pv_b', status: 'ready' }; S.previewId = 'pv_b'; });
    rollback.release();
    await settle(page);
    const onB = await page.evaluate(() => ({ preview: S.previewId, notice: document.getElementById('versionNotice').textContent }));
    await page.close();
    assert.equal(onB.preview, 'pv_b', `project B keeps its preview (shown: ${JSON.stringify(onB)})`);
    assert.equal(onB.notice, '', 'nothing is announced on project B');
    assert.deepEqual(errors, []);
  },
  async R2(browser, guard) {
    let historyCalls = 0;
    const reload = hold();
    const { page, errors } = await open(browser, guard, {
      '/projects/a/history': async route => { historyCalls += 1; if (historyCalls === 2) await reload.held; return json(route, VERSIONS); },
      '/projects/a/rollback': route => json(route, { ok: true }),
    });
    await page.evaluate(() => selectProject('a'));
    await settle(page);
    await page.evaluate(() => { restoreVersion('ver_1'); });   // the rollback answers at once; the versions reload is held
    await settle(page);
    await page.evaluate(() => selectProject('b'));
    await settle(page);
    reload.release();
    await settle(page);
    const notice = await page.evaluate(() => document.getElementById('versionNotice').textContent);
    await page.close();
    assert.equal(historyCalls, 2, 'the versions were reloaded after the restore');
    assert.equal(notice, '', `"restored" is not announced on project B (shown: ${JSON.stringify(notice)})`);
    assert.deepEqual(errors, []);
  },
  async R3(browser, guard) {
    const rollback = hold();
    const { page, errors } = await open(browser, guard, {
      '/projects/a/history': route => json(route, VERSIONS),
      '/projects/a/rollback': async route => { await rollback.held; return json(route, { detail: 'rollback failed' }, 409); },
    });
    await page.evaluate(() => selectProject('a'));
    await settle(page);
    await page.evaluate(() => { restoreVersion('ver_1'); });
    await settle(page);
    await page.evaluate(() => selectProject('b'));
    await settle(page);
    rollback.release();
    await settle(page);
    const notice = await page.evaluate(() => document.getElementById('versionNotice').textContent);
    await page.close();
    assert.equal(notice, '', `project A's failure is not shown on project B (shown: ${JSON.stringify(notice)})`);
    assert.deepEqual(errors, []);
  },
  async R4(browser, guard) {
    const rollback = hold();
    let posts = 0;
    const { page, errors } = await open(browser, guard, {
      '/projects/a/history': route => json(route, VERSIONS),
      '/projects/a/rollback': async route => { posts += 1; await rollback.held; return json(route, { ok: true }); },
    });
    await page.evaluate(() => selectProject('a'));
    await settle(page);
    await page.locator('#workspaceTabVersions').click();
    const restore = page.locator('#versionsList button', { hasText: 'שחזור' }).first();
    await restore.click();
    await restore.click();
    await settle(page);
    rollback.release();
    await settle(page);
    await page.close();
    assert.equal(posts, 1, `a second click sends no second rollback (sent: ${posts})`);
    assert.deepEqual(errors, []);
  },
  async R5(browser, guard) {
    let posts = 0;
    const { page, errors } = await open(browser, guard, {
      '/projects/a/history': route => json(route, VERSIONS),
      '/projects/a/rollback': route => { posts += 1; return json(route, { ok: true }); },
    });
    await page.evaluate(() => selectProject('a'));
    await settle(page);
    await page.evaluate(() => { S.preview = { preview_id: 'pv_old', status: 'ready' }; S.previewId = 'pv_old'; return restoreVersion('ver_1'); });
    await settle(page);
    const after = await page.evaluate(() => ({ preview: S.previewId, notice: document.getElementById('versionNotice').textContent, restored: t('restored') }));
    await page.close();
    assert.equal(posts, 1, 'the rollback was sent');
    assert.equal(after.notice, after.restored, `the restore announces itself (shown: ${JSON.stringify(after.notice)})`);
    assert.equal(after.preview, null, 'the preview of the replaced version is cleared');
    assert.deepEqual(errors, []);
  },
};

(async () => {
  const browser = await chromium.launch({ headless: true, ...browserOptions });
  const failures = [];
  try {
    for (const [id, scenario] of Object.entries(SCENARIOS)) {
      try { await scenario(browser, null); console.log(`::notice title=workspace guards::${id} holds`); }
      catch (e) { failures.push(`${id}: fails on the current code: ${e.message}`); continue; }
      if (!OLD[id]) continue;
      let caught = false;
      try { await scenario(browser, id); } catch (e) { caught = true; console.log(`::notice title=workspace guards::${id} fails without its guard, as it must: ${e.message.split('\n')[0]}`); }
      if (!caught) failures.push(`${id}: also passes WITHOUT its guard -- the scenario proves nothing`);
    }
  } finally {
    await browser.close();
  }
  if (failures.length) { for (const f of failures) console.log(`::error title=workspace guards::${f}`); process.exit(1); }
  console.log(`::notice title=workspace guards::all ${Object.keys(SCENARIOS).length} scenarios hold, and each of the ${Object.keys(OLD).length} guards is caught when taken out`);
})().catch(e => { console.error(e); process.exit(1); });

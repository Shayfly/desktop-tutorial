/* Run against a disposable development server with in-memory creator accounts. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');

const baseURL = 'http://127.0.0.1:18749';
const mutations = {
  secondary_accent: '#sidebar #sbAll { background: var(--nav-accent) }',
  secondary_disabled: '#sidebar #sbAll { opacity: .45 }',
  contrast: '#sidebar #sbAll { color: var(--nav-bg) }',
  color_only: '.sbStatus { display: none }',
  target_size: '#sidebar #sbAll { min-height: 24px; height: 24px; padding: 0 }',
  horizontal_scroll: 'body { min-width: 340px; overflow: visible !important }',
};
const scriptMutations = {
  hash_in_version_row: [`h('strong', {}, v.title || v.message || t('workspaceVersion'))`, "h('strong', {}, v.id)"],
  empty_failure_preview: ["empty.classList.toggle('previewFailed', buildFailed);", "empty.classList.toggle('previewFailed', buildFailed); return;"],
};
const browserOptions = process.env.CHROMIUM_PATH ? {
  executablePath: process.env.CHROMIUM_PATH,
  args: ['--no-sandbox', '--disable-gpu'],
} : {};

async function createFromForm(page, title) {
  await page.locator('#newProjectName').fill(title);
  await page.locator('#newProjectCreate').click();
  await page.locator('#newProjectDialog').waitFor({ state: 'hidden' });
  assert.equal(await page.locator('#chatTitle').textContent(), title);
}

(async () => {
  const browser = await chromium.launch(browserOptions);
  try {
    for (const width of [320, 390, 1440]) {
      const page = await browser.newPage({ baseURL, viewport: { width, height: 844 }, colorScheme: width === 390 ? 'dark' : 'light' });
      const errors = [];
      page.on('pageerror', error => errors.push(String(error)));
      const mutation = process.env.WORKSPACE_MUTATION;
      if (scriptMutations[mutation]) {
        const [from, to] = scriptMutations[mutation];
        await page.route('**/assets/app.js*', async route => {
          const response = await route.fetch();
          const script = await response.text();
          assert.ok(script.includes(from), 'mutation anchor missing');
          await route.fulfill({ response, body: script.replace(from, to) });
        });
      } else if (mutation) {
        assert.ok(mutations[mutation], 'unknown mutation');
        await page.route('**/assets/app.css*', async route => {
          const response = await route.fetch();
          await route.fulfill({ response, body: (await response.text()) + '\n' + mutations[mutation] });
        });
      }
      await page.goto('/');
      await page.locator('#email').fill(`sidebar-${width}-${Date.now()}@example.test`);
      await page.locator('#password').fill('local-sidebar-test-only');
      await page.locator('#registerBtn').click();
      await page.locator('#workspaceView').waitFor();
      const mobile = width <= 900;
      const openSidebar = async () => {
        if (mobile || await page.locator('#sbOpen').isVisible()) {
          await page.locator(mobile ? '#mobileMenuBtn' : '#sbOpen').click();
        }
      };
      await openSidebar();
      assert.equal(await page.locator('#mobileTabs #mobileMenuBtn').count(), 0);
      const geometry = await page.evaluate(() => {
        const sidebar = document.getElementById('sidebar');
        const controls = [...sidebar.querySelectorAll('button,input,summary')].filter(el => el.getClientRects().length);
        return {
          overflow: document.documentElement.scrollWidth > innerWidth,
          sidebarWidth: sidebar.getBoundingClientRect().width,
          undersized: controls.filter(el => el.getBoundingClientRect().height < 44).map(el => el.id),
        };
      });
      assert.equal(geometry.overflow, false, `root overflow at ${width}`);
      assert.deepEqual(geometry.undersized, [], `touch targets at ${width}`);
      if (mobile) assert.equal(geometry.sidebarWidth, Math.min(302, width - 58));
      await page.locator('#sbSearch').focus();
      const appearance = await page.evaluate(() => {
        const style = id => getComputedStyle(document.getElementById(id));
        const rgb = value => value.match(/[\d.]+/g).map(Number);
        const luminance = value => rgb(value).slice(0, 3).map(channel => {
          const light = channel / 255;
          return light <= .04045 ? light / 12.92 : ((light + .055) / 1.055) ** 2.4;
        }).reduce((sum, channel, index) => sum + channel * [.2126, .7152, .0722][index], 0);
        const contrast = (fg, bg) => {
          const pair = [luminance(fg), luminance(bg)].sort((a, b) => b - a);
          return (pair[0] + .05) / (pair[1] + .05);
        };
        const primary = style('newProjectTopBtn');
        const secondary = style('sbAll');
        const surface = style('sidebar');
        return {
          focus: style('sbSearch').outlineStyle,
          secondaryAccent: secondary.backgroundColor === primary.backgroundColor,
          secondaryOpacity: Number(secondary.opacity),
          minimumContrast: Math.min(contrast(primary.color, primary.backgroundColor), contrast(secondary.color, surface.backgroundColor)),
        };
      });
      assert.equal(appearance.focus, 'solid', 'visible keyboard focus');
      assert.equal(appearance.secondaryAccent, false, 'accent reserved for primary action');
      assert.equal(appearance.secondaryOpacity, 1, 'secondary action appears enabled');
      assert.ok(appearance.minimumContrast >= 4.5, 'text contrast below 4.5');
      const credits = await page.evaluate(async () => {
        const response = await fetch('/api/v28/me', { credentials: 'same-origin' });
        if (!response.ok) throw new Error(`GET me returned ${response.status}`);
        return (await response.json()).subscription.credits_remaining;
      });
      if (Number.isFinite(credits)) assert.match(await page.locator('#sbBalance').textContent(), new RegExp(String(credits)));

      await page.locator('#newProjectTopBtn').click();
      await createFromForm(page, 'אוורסט');
      await page.locator('#chatInput').fill('טיוטה ששייכת לאוורסט');
      await openSidebar();
      await page.locator('#sbTemplates').click();
      await page.locator('#workspaceDialogBody button').first().click();
      await createFromForm(page, 'אתר שני');
      assert.match(await page.locator('#chatInput').inputValue(), /אתר לעסק/);
      await page.evaluate(() => {
        S.proposal = {price:{amount_ils:93}};
        renderWorkspaceHeader();
      });
      assert.match(await page.locator('#workspaceProjectChip').textContent(), /93/);
      await page.locator('#workspaceTabVersions').click();
      await openSidebar();
      await page.locator('#sbAll').click();
      assert.equal(await page.locator('#workspaceProjectList button').count(), 2);
      await page.locator('#workspaceProjectState').selectOption('ready');
      assert.equal(await page.locator('#workspaceProjectList button').count(), 0);
      await page.locator('#workspaceProjectState').selectOption('unknown');
      assert.equal(await page.locator('#workspaceProjectList button').count(), 2);
      assert.equal(await page.locator('#workspaceProjectList .sbStatus').first().isVisible(), true, 'status is visible in text');
      await page.locator('#workspaceProjectSearch').fill('אוורסט');
      assert.equal(await page.locator('#workspaceProjectList button').count(), 1);
      await page.locator('#workspaceProjectList button').click();
      assert.equal(await page.locator('#chatInput').inputValue(), 'טיוטה ששייכת לאוורסט');
      assert.equal(await page.locator('#workspaceDialog').isVisible(), false);
      assert.equal(await page.locator('#workspaceTabChat').getAttribute('aria-selected'), 'true');
      assert.doesNotMatch(await page.locator('#workspaceProjectChip').textContent(), /93/);
      await page.locator('#workspaceTabPreview').click();
      if (!mobile) {
        await page.locator('#sbCollapse').click();
        await page.locator('#sbOpen').click();
        assert.equal(await page.locator('#sidebar').isVisible(), true);
      }
      assert.equal(await page.locator('#workspaceTabPreview').getAttribute('aria-selected'), 'true');
      await page.locator('#previewEditBtn').click();
      assert.equal(await page.locator('#editor').isVisible(), true);
      await page.evaluate(() => {
        S.versions = [{ id:'v_internal_123', title:'עדכון הטופס', created_at:'2026-11-22T11:55:00Z' }];
        renderVersions();
      });
      await page.locator('#workspaceTabVersions').click();
      assert.match(await page.locator('#versionsList').innerText(), /עדכון הטופס/, 'version row shows a human title');
      assert.doesNotMatch(await page.locator('#versionsList').innerText(), /v_internal_123/);
      await page.locator('#versionsList details summary').click();
      assert.match(await page.locator('#versionsList').innerText(), /v_internal_123/);
      await page.evaluate(() => {
        S.build = {status:'failed', error_code:'worker_lost'};
        S.preview = null;
        renderTrack();
      });
      await page.locator('#workspaceTabPreview').click();
      assert.equal(await page.locator('.previewRecovery button').isVisible(), true, 'failed build shows a recovery action');
      assert.equal(await page.locator('#previewFrame').isVisible(), false);
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`PASS sidebar and real development API at ${width}px`);
    }
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exit(1); });

const $ = (id) => document.getElementById(id);

const I18N = {
  en: {
    eyebrow: 'FROM IDEA TO WORKING PRODUCT',
    headline: 'What do you want to build?',
    subheadline: 'Describe the outcome. 148AI creates the project, generates the files, validates the result and prepares a working preview.',
    authTitle: 'Your private build workspace.',
    authCopy: 'Sign in once, then create and improve products from one natural-language prompt.',
    createAccount: 'Create account',
    signIn: 'Sign in',
    email: 'Email',
    password: 'Password',
    passwordHint: 'Use at least 10 characters.',
    show: 'Show',
    hide: 'Hide',
    workspaceLabel: 'Your workspace',
    workspaceReady: 'Workspace ready. Describe what you want to build.',
    recentProjects: 'RECENT PROJECTS',
    newProject: 'New project from this prompt',
    noProjects: 'No projects yet — your first prompt will create one.',
    createLabel: 'CREATE',
    buildTitle: 'Describe the product. 148AI handles the rest.',
    promptPlaceholder: 'Example: Build a Hebrew learning game for first graders with writing practice, vowels, levels, stars and rewards.',
    advanced: 'Advanced',
    targetMarkets: 'Target markets',
    buildHint: 'No product-type selection required. 148AI infers the structure from your request.',
    build: 'Build with 148AI →',
    building: 'Building…',
    buildProgress: 'BUILD PROGRESS',
    timelineTitle: 'What 148AI is doing',
    planning: 'Planning',
    generating: 'Generating',
    running: 'Running',
    testing: 'Testing',
    repairing: 'Repairing',
    ready: 'Ready',
    failed: 'Failed',
    resultReady: 'Your product is ready to review',
    preview: 'Preview',
    previewTitle: 'Working product preview',
    openNewTab: 'Open in new tab',
    export: 'Export ZIP',
    versions: 'Versions',
    versionHistory: 'Version history',
    selectVersion: 'Select a version',
    restore: 'Restore',
    restored: 'Version restored.',
    signOut: 'Sign out',
    describe: 'Describe what you want to build.',
    buildFailed: 'Build failed.',
    exportFailed: 'Export failed.',
    previewFailed: 'Preview failed.',
    noVersion: 'No ready version yet.',
    current: 'Current',
    footerNote: 'Prompt → Build → Validate → Preview → Improve → Export',
    accountExists: 'An account already exists for this email. Switch to Sign in.',
    enterEmail: 'Enter your email.',
    passwordMin: 'Password must be at least 10 characters.',
    signedOut: 'Signed out',
    projectCount: (n) => `${n} project${n === 1 ? '' : 's'}`,
    versionLabel: (n) => `Version ${n}`,
  },
  he: {
    eyebrow: 'מרעיון למוצר עובד',
    headline: 'מה תרצו לבנות?',
    subheadline: 'תארו את התוצאה שאתם רוצים. 148AI יוצרת את הפרויקט, מייצרת את הקבצים, בודקת את התוצאה ומכינה תצוגה מקדימה עובדת.',
    authTitle: 'סביבת העבודה הפרטית שלכם.',
    authCopy: 'מתחברים פעם אחת, ואז בונים ומשפרים מוצרים בעזרת בקשה אחת בשפה טבעית.',
    createAccount: 'יצירת חשבון',
    signIn: 'כניסה',
    email: 'אימייל',
    password: 'סיסמה',
    passwordHint: 'השתמשו בלפחות 10 תווים.',
    show: 'הצג',
    hide: 'הסתר',
    workspaceLabel: 'סביבת העבודה שלכם',
    workspaceReady: 'סביבת העבודה מוכנה. כתבו מה תרצו לבנות.',
    recentProjects: 'פרויקטים אחרונים',
    newProject: 'פרויקט חדש מהבקשה הזאת',
    noProjects: 'אין עדיין פרויקטים — הבקשה הראשונה תיצור אחד אוטומטית.',
    createLabel: 'יצירה',
    buildTitle: 'תארו את המוצר. 148AI מטפלת בשאר.',
    promptPlaceholder: 'לדוגמה: בנה משחק לימודי בעברית לכיתה א׳ לתרגול כתיבה וניקוד, עם שלבים, כוכבים ופרסים.',
    advanced: 'אפשרויות מתקדמות',
    targetMarkets: 'שווקי יעד',
    buildHint: 'אין צורך לבחור סוג מוצר. 148AI מסיקה את המבנה מתוך הבקשה שלכם.',
    build: 'בנה עם 148AI ←',
    building: 'בונה…',
    buildProgress: 'התקדמות הבנייה',
    timelineTitle: 'מה 148AI עושה עכשיו',
    planning: 'מתכננת',
    generating: 'מייצרת',
    running: 'מריצה',
    testing: 'בודקת',
    repairing: 'מתקנת',
    ready: 'מוכן',
    failed: 'נכשל',
    resultReady: 'המוצר מוכן לבדיקה',
    preview: 'תצוגה מקדימה',
    previewTitle: 'תצוגה מקדימה של המוצר העובד',
    openNewTab: 'פתח בחלון חדש',
    export: 'הורדת ZIP',
    versions: 'גרסאות',
    versionHistory: 'היסטוריית גרסאות',
    selectVersion: 'בחרו גרסה',
    restore: 'שחזור',
    restored: 'הגרסה שוחזרה.',
    signOut: 'התנתקות',
    describe: 'כתבו מה תרצו לבנות.',
    buildFailed: 'הבנייה נכשלה.',
    exportFailed: 'ההורדה נכשלה.',
    previewFailed: 'התצוגה המקדימה נכשלה.',
    noVersion: 'אין עדיין גרסה מוכנה.',
    current: 'נוכחית',
    footerNote: 'בקשה ← בנייה ← בדיקה ← תצוגה מקדימה ← שיפור ← הורדה',
    accountExists: 'כבר קיים חשבון עם האימייל הזה. עברו לכניסה.',
    enterEmail: 'הזינו אימייל.',
    passwordMin: 'הסיסמה חייבת להכיל לפחות 10 תווים.',
    signedOut: 'התנתקת',
    projectCount: (n) => `${n} פרויקטים`,
    versionLabel: (n) => `גרסה ${n}`,
  },
};

let locale = localStorage.getItem('148ai_locale') || 'en';
let mode = 'register';
let currentProjectId = localStorage.getItem('148ai_last_project') || '';
let currentVersionId = '';
let currentPreviewUrl = '';
let pollTimer = null;

const token = () => localStorage.getItem('148ai_live_token') || '';
const auth = () => ({ Authorization: `Bearer ${token()}` });
const t = (key, ...args) => {
  const value = (I18N[locale] || I18N.en)[key] ?? I18N.en[key] ?? key;
  return typeof value === 'function' ? value(...args) : value;
};

async function req(url, opts = {}) {
  const response = await fetch(url, opts);
  const type = response.headers.get('content-type') || '';
  const data = type.includes('json') ? await response.json() : await response.text();
  if (!response.ok) {
    const message = typeof data === 'object' ? (data.detail || data.error || JSON.stringify(data)) : (data || `Request failed (${response.status})`);
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

function msg(id, text, type = '') {
  const element = $(id);
  if (!element) return;
  element.textContent = text || '';
  element.className = `message ${type}`;
}

function applyLocale(next = locale) {
  locale = I18N[next] ? next : 'en';
  localStorage.setItem('148ai_locale', locale);
  document.documentElement.lang = locale;
  document.documentElement.dir = locale === 'he' ? 'rtl' : 'ltr';
  $('lang').value = locale;
  document.querySelectorAll('[data-i18n]').forEach((element) => {
    const key = element.dataset.i18n;
    if (key) element.textContent = t(key);
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((element) => {
    const key = element.dataset.i18nPlaceholder;
    if (key) element.placeholder = t(key);
  });
  if ($('authSubmit')) $('authSubmit').textContent = mode === 'register' ? t('createAccount') : t('signIn');
  if ($('togglePassword')) $('togglePassword').textContent = $('password').type === 'password' ? t('show') : t('hide');
  renderEmptyTimeline();
}

function setMode(next) {
  mode = next;
  const registering = mode === 'register';
  $('signupTab').classList.toggle('active', registering);
  $('signinTab').classList.toggle('active', !registering);
  $('password').autocomplete = registering ? 'new-password' : 'current-password';
  $('authHint').textContent = registering ? t('passwordHint') : t('password');
  $('authSubmit').textContent = registering ? t('createAccount') : t('signIn');
  msg('accountState', '');
}

function showWorkspace(email = '') {
  $('authPanel').classList.add('hidden');
  $('workspace').classList.remove('hidden');
  $('userEmail').textContent = email || localStorage.getItem('148ai_email') || '';
}

function showAuth() {
  $('workspace').classList.add('hidden');
  $('authPanel').classList.remove('hidden');
}

async function authenticate() {
  const email = $('email').value.trim();
  const password = $('password').value;
  if (!email) return msg('accountState', t('enterEmail'), 'error');
  if (password.length < 10) return msg('accountState', t('passwordMin'), 'error');
  $('authSubmit').disabled = true;
  try {
    const data = await req(`/api/live/auth/${mode}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('148ai_live_token', data.token);
    localStorage.setItem('148ai_email', data.user.email);
    showWorkspace(data.user.email);
    await loadProjects();
    msg('state', t('workspaceReady'), 'good');
  } catch (error) {
    let text = error.message;
    if (mode === 'register' && /already|exists/i.test(text)) text = t('accountExists');
    msg('accountState', text, 'error');
  } finally {
    $('authSubmit').disabled = false;
    $('authSubmit').textContent = mode === 'register' ? t('createAccount') : t('signIn');
  }
}

function logout() {
  if (token()) {
    fetch('/api/live/auth/logout', { method: 'POST', headers: auth() }).catch(() => {});
  }
  localStorage.removeItem('148ai_live_token');
  localStorage.removeItem('148ai_email');
  clearTimeout(pollTimer);
  showAuth();
  setMode('login');
  msg('accountState', t('signedOut'));
}

async function loadProjects() {
  if (!token()) return;
  try {
    const data = await req('/api/live/projects', { headers: auth() });
    const select = $('projectSelect');
    select.replaceChildren();
    const fresh = document.createElement('option');
    fresh.value = '';
    fresh.textContent = t('newProject');
    select.append(fresh);
    data.projects.forEach((project) => {
      const option = document.createElement('option');
      option.value = project.id;
      option.textContent = project.title;
      option.dataset.version = project.active_version_id || '';
      select.append(option);
    });
    if (currentProjectId && data.projects.some((p) => p.id === currentProjectId)) {
      select.value = currentProjectId;
      const project = data.projects.find((p) => p.id === currentProjectId);
      currentVersionId = project?.active_version_id || '';
      await loadVersions(currentProjectId, false);
      await reloadLastBuild(currentProjectId);
    } else {
      currentProjectId = '';
      currentVersionId = '';
      select.value = '';
      renderEmptyTimeline();
    }
    msg('projectState', data.projects.length ? t('projectCount', data.projects.length) : t('noProjects'));
  } catch (error) {
    if (error.status === 401) return logout();
    msg('projectState', error.message, 'error');
  }
}

function stageOrder() {
  return ['planning', 'generating', 'running', 'testing', 'repairing', 'ready'];
}

function renderEmptyTimeline() {
  const timeline = $('timeline');
  if (!timeline) return;
  timeline.replaceChildren();
  ['planning', 'generating', 'running', 'testing', 'ready'].forEach((stage) => {
    const row = document.createElement('div');
    row.className = 'timelineStep idle';
    row.dataset.stage = stage;
    row.innerHTML = `<span class="stepDot"></span><div><b>${t(stage)}</b><small></small></div>`;
    timeline.append(row);
  });
}

function renderTimeline(build) {
  const events = build.events || [];
  const timeline = $('timeline');
  timeline.replaceChildren();
  events.forEach((event, index) => {
    const row = document.createElement('div');
    const terminalFail = event.stage === 'failed';
    const current = index === events.length - 1 && !['ready', 'failed'].includes(event.stage);
    row.className = `timelineStep ${terminalFail ? 'fail' : current ? 'current' : 'done'}`;
    const safeMessage = event.message || '';
    row.innerHTML = `<span class="stepDot"></span><div><b>${t(event.stage)}</b><small></small></div>`;
    row.querySelector('small').textContent = safeMessage;
    timeline.append(row);
  });
  if (!events.length) renderEmptyTimeline();
  $('buildStatus').textContent = t(build.stage || 'ready');
  $('buildStatus').className = `status ${build.stage === 'ready' ? 'ok' : build.stage === 'failed' ? 'bad' : 'working'}`;
}

function markets() {
  return $('targetMarkets').value.split(',').map((value) => value.trim()).filter(Boolean);
}

async function fetchBuild(buildId) {
  return req(`/api/live/builds/${encodeURIComponent(buildId)}`, { headers: auth() });
}

async function waitForBuild(buildId) {
  const build = await fetchBuild(buildId);
  renderTimeline(build);
  if (!['ready', 'failed'].includes(build.stage)) {
    pollTimer = setTimeout(() => waitForBuild(buildId).catch((error) => msg('state', error.message, 'error')), 900);
  }
  return build;
}

function rememberBuild(projectId, buildId) {
  if (!projectId || !buildId) return;
  localStorage.setItem(`148ai_last_build_${projectId}`, buildId);
}

async function reloadLastBuild(projectId) {
  const buildId = localStorage.getItem(`148ai_last_build_${projectId}`);
  if (!buildId) return renderEmptyTimeline();
  try {
    const build = await fetchBuild(buildId);
    renderTimeline(build);
    if (build.stage === 'ready' && build.version_id) showReady(build);
  } catch (_) {
    renderEmptyTimeline();
  }
}

function showReady(build) {
  currentProjectId = build.project_id;
  currentVersionId = build.version_id || currentVersionId;
  localStorage.setItem('148ai_last_project', currentProjectId);
  $('resultCard').classList.remove('hidden');
  $('resultMeta').textContent = `${t('ready')} · ${currentVersionId ? currentVersionId.slice(0, 8) : ''}`;
  msg('state', t('resultReady'), 'good');
}

async function build() {
  const prompt = $('prompt').value.trim();
  if (prompt.length < 3) return msg('state', t('describe'), 'error');
  clearTimeout(pollTimer);
  $('buildBtn').disabled = true;
  $('buildBtn').textContent = t('building');
  $('resultCard').classList.add('hidden');
  $('previewPanel').classList.add('hidden');
  msg('state', t('building'));
  try {
    const data = await req('/api/live/builds', {
      method: 'POST',
      headers: { ...auth(), 'content-type': 'application/json' },
      body: JSON.stringify({
        prompt,
        project_id: $('projectSelect').value || null,
        target_markets: markets(),
      }),
    });
    currentProjectId = data.project_id;
    rememberBuild(data.project_id, data.id);
    const full = await waitForBuild(data.id);
    if (full.stage === 'ready') {
      showReady(full);
      await loadProjects();
      $('projectSelect').value = currentProjectId;
      await loadVersions(currentProjectId, false);
    } else if (full.stage === 'failed') {
      msg('state', full.error || t('buildFailed'), 'error');
    }
  } catch (error) {
    $('buildStatus').textContent = t('failed');
    $('buildStatus').className = 'status bad';
    msg('state', error.message || t('buildFailed'), 'error');
  } finally {
    $('buildBtn').disabled = false;
    $('buildBtn').textContent = t('build');
  }
}

async function loadVersions(projectId = currentProjectId, reveal = true) {
  if (!projectId) {
    msg('versionState', t('noVersion'));
    return;
  }
  try {
    const data = await req(`/api/live/projects/${encodeURIComponent(projectId)}/versions`, { headers: auth() });
    const select = $('versionSelect');
    select.replaceChildren();
    data.versions.forEach((version, index) => {
      const option = document.createElement('option');
      option.value = version.id;
      const suffix = version.id === currentVersionId ? ` · ${t('current')}` : '';
      option.textContent = `${t('versionLabel', index + 1)}${suffix}`;
      select.append(option);
    });
    if (currentVersionId && data.versions.some((v) => v.id === currentVersionId)) select.value = currentVersionId;
    else if (data.versions.length) {
      currentVersionId = data.versions[data.versions.length - 1].id;
      select.value = currentVersionId;
    }
    if (reveal) $('versionsPanel').classList.remove('hidden');
    msg('versionState', data.versions.length ? '' : t('noVersion'));
  } catch (error) {
    msg('versionState', error.message, 'error');
  }
}

async function restoreVersion() {
  const versionId = $('versionSelect').value;
  if (!currentProjectId || !versionId) return msg('versionState', t('noVersion'), 'error');
  try {
    const project = await req(`/api/live/projects/${encodeURIComponent(currentProjectId)}/versions/${encodeURIComponent(versionId)}/restore`, {
      method: 'POST', headers: auth(),
    });
    currentVersionId = project.active_version_id;
    msg('versionState', t('restored'), 'good');
    await loadVersions(currentProjectId, true);
  } catch (error) {
    msg('versionState', error.message, 'error');
  }
}

async function preview() {
  if (!currentProjectId || !currentVersionId) return msg('state', t('noVersion'), 'error');
  try {
    const data = await req(`/api/live/projects/${encodeURIComponent(currentProjectId)}/versions/${encodeURIComponent(currentVersionId)}/preview`, {
      method: 'POST', headers: auth(),
    });
    currentPreviewUrl = data.url;
    $('previewFrame').src = data.url;
    $('previewPanel').classList.remove('hidden');
    $('previewPanel').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    msg('state', `${t('previewFailed')} ${error.message}`, 'error');
  }
}

function openPreview() {
  if (currentPreviewUrl) window.open(currentPreviewUrl, '_blank', 'noopener,noreferrer');
}

async function exportVersion() {
  if (!currentProjectId || !currentVersionId) return msg('state', t('noVersion'), 'error');
  try {
    const response = await fetch(`/api/live/projects/${encodeURIComponent(currentProjectId)}/versions/${encodeURIComponent(currentVersionId)}/export`, { headers: auth() });
    if (!response.ok) {
      let detail = `${t('exportFailed')} (${response.status})`;
      try { const body = await response.json(); detail = body.detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = '148AI-project.zip';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  } catch (error) {
    msg('state', `${t('exportFailed')} ${error.message}`, 'error');
  }
}

async function selectProject() {
  currentProjectId = $('projectSelect').value || '';
  localStorage.setItem('148ai_last_project', currentProjectId);
  $('resultCard').classList.add('hidden');
  $('previewPanel').classList.add('hidden');
  $('versionsPanel').classList.add('hidden');
  currentVersionId = '';
  if (!currentProjectId) return renderEmptyTimeline();
  const selected = $('projectSelect').selectedOptions[0];
  currentVersionId = selected?.dataset.version || '';
  await loadVersions(currentProjectId, false);
  await reloadLastBuild(currentProjectId);
}

document.addEventListener('DOMContentLoaded', async () => {
  applyLocale(locale);
  renderEmptyTimeline();
  $('lang').onchange = () => applyLocale($('lang').value);
  $('signupTab').onclick = () => setMode('register');
  $('signinTab').onclick = () => setMode('login');
  $('authSubmit').onclick = authenticate;
  $('password').onkeydown = (event) => { if (event.key === 'Enter') authenticate(); };
  $('togglePassword').onclick = () => {
    const hidden = $('password').type === 'password';
    $('password').type = hidden ? 'text' : 'password';
    $('togglePassword').textContent = hidden ? t('hide') : t('show');
  };
  $('logoutBtn').onclick = logout;
  $('projectSelect').onchange = selectProject;
  $('buildBtn').onclick = build;
  $('previewBtn').onclick = preview;
  $('openPreviewBtn').onclick = openPreview;
  $('versionsBtn').onclick = () => loadVersions(currentProjectId, true);
  $('restoreBtn').onclick = restoreVersion;
  $('exportBtn').onclick = exportVersion;

  if (token()) {
    try {
      const me = await req('/api/live/me', { headers: auth() });
      localStorage.setItem('148ai_email', me.email);
      showWorkspace(me.email);
      await loadProjects();
    } catch (_) {
      logout();
    }
  } else {
    showAuth();
  }
});

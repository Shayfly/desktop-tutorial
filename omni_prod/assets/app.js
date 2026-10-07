'use strict';
/* 148AI creator workspace (M5-UX01).
   Uses only existing V28 endpoints plus the plan step
   (POST /api/v28/projects/{id}/build-contracts). Never shows a preview,
   publish result or cost that the backend did not report. */

const T = {
  he: {
    skip:'דילוג לתוכן', projects:'פרויקטים', manage:'ניהול', logout:'התנתקות',
    hero:'תארו את אפליקציית הווב שלכם.', lead:'148AI מתכננת, בונה, בודקת ומציגה אותה.',
    how1:'כותבים מה האפליקציה צריכה לעשות ולמי.', how2:'מקבלים תוכנית ועלות מקסימלית, ומאשרים.',
    how3:'צופים בבנייה, בודקים בתצוגה מקדימה, משנים ומורידים את הקוד.',
    scope:'כרגע: אפליקציות ווב ו-SaaS. מובייל, משחקים ומדיה עוד לא זמינים.',
    signinTitle:'כניסה לחשבון', email:'אימייל', password:'סיסמה', passwordHint:'לפחות 10 תווים.',
    login:'כניסה', register:'יצירת חשבון חינם',
    firstProject:'הפרויקט הראשון שלכם', projectName:'שם הפרויקט', createProject:'יצירת פרויקט',
    request:'מה תרצו לבנות?', build:'בנה עם 148AI', planHint:'קודם תוצג תוכנית ועלות. שום חיוב לא מתבצע לפני אישור.',
    builtTitle:'מה נבנה עד עכשיו', newBuild:'בנייה חדשה מאפס', builtVersion:'גרסה נוכחית', files:'קבצים',
    progress:'התקדמות הבנייה', modifyTitle:'מה תרצו לשנות?', modifySend:'שליחת שינוי', versions:'גרסאות',
    evidence:'פרטים טכניים ועדויות', refresh:'רענון', openTab:'פתיחה בלשונית חדשה',
    noPreview:'כאן תופיע האפליקציה אחרי שהבנייה תסתיים.', download:'הורדת קוד המקור (ZIP)', publish:'פרסום',
    publishNotConfigured:'הפרסום לאוויר עוד לא מוגדר בשרת הזה. אפשר להוריד את הקוד ולבדוק בתצוגה המקדימה.',
    manageProject:'ניהול פרויקט', rename:'שינוי שם', saveName:'שמירת השם', archive:'העברה לארכיון',
    newProject:'פרויקט חדש', close:'סגירה',
    promptPlaceholder:'לדוגמה: מערכת לניהול תורים למספרה, עם יומן לספרים, הזמנה עצמית ללקוחות ותזכורות במייל.',
    planTitle:'התוכנית', understood:'מה הבנו', roles:'משתמשים', data:'נתונים', integrations:'חיבורים',
    capabilities:'יכולות שהבנייה צריכה', infrastructure:'תשתית לאפליקציה', cost:'עלות',
    estimated:'הערכה', maximum:'מקסימום מאושר', questions:'שאלות לפני שמתחילים', blockersTitle:'מה חוסם כרגע',
    creditsRequired:'קרדיטים לבנייה', creditsRemaining:'קרדיטים שנותרו', quoteStatus:'תמחור',
    confirm:'אשרו והתחילו בנייה', editRequest:'עריכת הבקשה', costUnknown:'לא ניתן לחשב',
    byPipeline:'בתוך הבנייה', byProvider:'ספק חיצוני', required:'נדרש', optional:'רשות',
    st_LIVE:'פעיל', st_PARTIAL:'מוגדר, לא נבדק', st_NOT_CONFIGURED:'לא מוגדר', st_BLOCKED:'חסום',
    st_SELF_CONTAINED:'מובנה באפליקציה', st_PRICED:'מאושר', st_UNKNOWN:'לא ניתן לתמחר', st_NOT_AUTHORIZED:'לא מאושר',
    stepPlanning:'תכנון', stepContract:'חוזה בנייה', stepInfra:'תשתית', stepAssets:'נכסים (אייקון ותמונות)',
    stepGenerate:'יצירת קוד, בנייה, בדיקות ותיקונים', stepGates:'בדיקות איכות, אבטחה וזכויות', stepPreview:'תצוגה מקדימה',
    noteGenerate:'הבנייה, הבדיקות והתיקונים רצים בשלב אחד. מספר סבבי התיקון מדווח בסיום.',
    repairs:n=>`סבבי תיקון: ${n}`, queued:'ממתין בתור', started:'הבנייה התחילה', buildReady:'הבנייה הסתיימה בהצלחה.',
    buildFailed:'הבנייה נכשלה',
    errCodes:{verification_failed:'הקוד שנוצר לא עבר את הבדיקות האוטומטיות גם אחרי סבבי תיקון.',
      quality_gate_failed:'הקוד עבד, אבל לא עמד ברף האיכות הנדרש גם אחרי סבבי תיקון.',
      preview_not_ready:'הקוד עבר את הבדיקות, אבל האתר לא עלה בהפעלת ניסיון ולכן לא אושר.',
      security_gate_failed:'נמצאה בעיית אבטחה בקוד שנוצר, ולכן הוא לא אושר.',
      rights_gate_not_clear:'הגרסה נשמרה, אבל חסר אישור זכויות לפני פרסום.',
      unsupported_dependency:'הקוד ביקש ספרייה חיצונית שעדיין לא נתמכת בפלטפורמה.',
      worker_lost:'הבנייה הפסיקה להגיב ושוחררה. לא חויבו קרדיטים. אפשר לנסות שוב.',
      worker_exception:'אירעה תקלה פנימית במהלך הבנייה. הצוות קיבל את הפרטים.',
      capability_gate_failed:'יכולת נדרשת (למשל יצירת תמונות) לא אומתה, ולכן הבנייה לא אושרה.'},
    techDetails:'פרטים טכניים', previewStarting:'מפעילים תצוגה מקדימה…', previewRunning:'התצוגה המקדימה פועלת.',
    previewNotPreviewable:'הגרסה הזאת לא ניתנת להצגה מקדימה: ', previewUnavailable:'תצוגה מקדימה לא זמינה בשרת הזה: ',
    previewFailed:'התצוגה המקדימה נכשלה: ', previewExpired:'התצוגה המקדימה פגה. אפשר להפעיל אותה מחדש.',
    startPreview:'הפעלת תצוגה מקדימה',
    current:'נוכחית', restore:'שחזור לגרסה הזו', restored:'שוחזר. נוצרה גרסה חדשה.', noVersions:'עדיין אין גרסאות.',
    modQueued:'השינוי נשלח. בונים גרסה מועמדת ובודקים אותה…', modReview:'הגרסה המועמדת עברה את הבדיקות. מה תרצו לעשות?',
    accept:'אישור השינוי', reject:'דחייה', modAccepted:'השינוי אושר ונשמר כגרסה חדשה.', modRejected:'השינוי נדחה.',
    modFailed:'השינוי נכשל: ', classification:'סיווג',
    gates:'בדיקות', usage:'שימוש בספקים', costActual:'עלות בפועל', costBasis:'בסיס העלות', warnings:'אזהרות',
    requestIds:'מזהי בקשות', tokens:'טוקנים (קלט/פלט)', none:'אין',
    backendMissing:'<b>בנייה לא זמינה בשרת הזה.</b> נדרשים PostgreSQL ואחסון S3. אפשר להירשם, לנהל פרויקטים ולראות תוכנית ועלות.',
    emailUnverified:'האימייל עדיין לא אומת.',
    err401:'פג תוקף ההתחברות. היכנסו שוב.', err402:'אין מספיק קרדיטים או שהמסלול לא מאפשר זאת: ',
    err403:'אין הרשאה לפעולה הזו.', err404:'לא נמצא.', err409:'צריך הבהרה לפני שממשיכים.',
    err503:'השירות הזה עוד לא מוגדר בשרת: ', errNet:'אין חיבור לשרת. בדקו את החיבור ונסו שוב.',
    needPrompt:'כתבו לפחות כמה מילים על האפליקציה.', needEmail:'הזינו אימייל וסיסמה של 10 תווים לפחות.',
    registered:'החשבון נוצר.', created:'הפרויקט נוצר.', renamed:'השם נשמר.', archived:'הפרויקט הועבר לארכיון.',
    downloadReady:'ההורדה התחילה.', untitled:'פרויקט חדש',
    lifecycle:'מחזור בנייה מלא: תכנון, קוד, התקנה, בנייה, בדיקות, תיקונים, תצוגה וייצוא', operatorDetails:'פרטים למפעיל השרת',
    b_durable_backend_not_configured:'הבנייה דורשת שרת עם PostgreSQL ואחסון S3.',
    b_infrastructure:k=>`התשתית של האפליקציה לא מוכנה: ${k}`, b_image_provider:'יצירת אייקון ותמונות לא מוגדרת.',
    b_plan_cannot_authorize_cost:'המסלול הנוכחי לא מאשר עלות משתנה בתשלום.',
    b_cost_quote_unknown:'חלק מהעלויות של הבנייה לא ידועות, ולכן אי אפשר לאשר אותה.',
    k_database:'מסד נתונים', k_auth_session:'התחברות וסשנים', k_object_storage:'אחסון קבצים', k_scheduled_http:'משימות מתוזמנות', k_outbound:'מיילים ו-webhooks',
  },
  en: {
    skip:'Skip to content', projects:'Projects', manage:'Manage', logout:'Sign out',
    hero:'Describe your web app.', lead:'148AI plans, builds, tests and previews it.',
    how1:'Write what the app should do and for whom.', how2:'Get a plan and a maximum cost, then approve it.',
    how3:'Watch the build, try it in a preview, ask for changes and download the code.',
    scope:'Today: web apps and SaaS. Mobile, games and media are not available yet.',
    signinTitle:'Sign in', email:'Email', password:'Password', passwordHint:'At least 10 characters.',
    login:'Sign in', register:'Create free account',
    firstProject:'Your first project', projectName:'Project name', createProject:'Create project',
    request:'What do you want to build?', build:'Build with 148AI', planHint:'You will see a plan and cost first. Nothing is charged before you approve.',
    builtTitle:'What has been built', newBuild:'New build from scratch', builtVersion:'Current version', files:'files',
    progress:'Build progress', modifyTitle:'What would you like to change?', modifySend:'Send change', versions:'Versions',
    evidence:'Technical details and evidence', refresh:'Refresh', openTab:'Open in new tab',
    noPreview:'Your app appears here once the build finishes.', download:'Download source (ZIP)', publish:'Publish',
    publishNotConfigured:'Publishing is not configured on this server yet. You can download the code and test it in the preview.',
    manageProject:'Manage project', rename:'Rename', saveName:'Save name', archive:'Archive',
    newProject:'New project', close:'Close',
    promptPlaceholder:'For example: an appointment system for a barbershop, with a calendar for barbers, self-booking for customers and email reminders.',
    planTitle:'The plan', understood:'What we understood', roles:'Users', data:'Data', integrations:'Integrations',
    capabilities:'Capabilities the build needs', infrastructure:'App infrastructure', cost:'Cost',
    estimated:'Estimate', maximum:'Approved maximum', questions:'Questions before we start', blockersTitle:'What is blocking right now',
    creditsRequired:'Credits for this build', creditsRemaining:'Credits remaining', quoteStatus:'Pricing',
    confirm:'Approve and start build', editRequest:'Edit request', costUnknown:'Cannot be calculated',
    byPipeline:'in the build', byProvider:'external provider', required:'required', optional:'optional',
    st_LIVE:'Live', st_PARTIAL:'Configured, not verified', st_NOT_CONFIGURED:'Not configured', st_BLOCKED:'Blocked',
    st_SELF_CONTAINED:'Built into the app', st_PRICED:'Authorized', st_UNKNOWN:'Cannot be priced', st_NOT_AUTHORIZED:'Not authorized',
    stepPlanning:'Planning', stepContract:'Build contract', stepInfra:'Infrastructure', stepAssets:'Assets (icon and images)',
    stepGenerate:'Generating code, building, testing and repairing', stepGates:'Quality, security and rights gates', stepPreview:'Preview',
    noteGenerate:'Build, tests and repairs run as one step. The number of repair rounds is reported at the end.',
    repairs:n=>`Repair rounds: ${n}`, queued:'Waiting in queue', started:'Build started', buildReady:'Build finished successfully.',
    buildFailed:'Build failed',
    errCodes:{verification_failed:'The generated code did not pass its automated checks, even after repair rounds.',
      quality_gate_failed:'The code works but did not meet the quality bar, even after repair rounds.',
      preview_not_ready:'The code passed its checks but the site did not start in a trial run, so it was not accepted.',
      security_gate_failed:'A security problem was found in the generated code, so it was not accepted.',
      rights_gate_not_clear:'The version was saved but needs rights clearance before publishing.',
      unsupported_dependency:'The code asked for an external library the platform does not support yet.',
      worker_lost:'The build stopped responding and was released. No credits were charged. You can try again.',
      worker_exception:'An internal error occurred during the build. The details were recorded.',
      capability_gate_failed:'A required capability (such as image generation) was not verified, so the build was not accepted.'},
    techDetails:'Technical details', previewStarting:'Starting preview…', previewRunning:'Preview is running.',
    previewNotPreviewable:'This version cannot be previewed: ', previewUnavailable:'Preview is not available on this server: ',
    previewFailed:'Preview failed: ', previewExpired:'The preview expired. You can start it again.',
    startPreview:'Start preview',
    current:'Current', restore:'Restore this version', restored:'Restored as a new version.', noVersions:'No versions yet.',
    modQueued:'Change sent. Building and testing a candidate version…', modReview:'The candidate version passed its checks. What would you like to do?',
    accept:'Accept change', reject:'Reject', modAccepted:'Change accepted and saved as a new version.', modRejected:'Change rejected.',
    modFailed:'Change failed: ', classification:'Classification',
    gates:'Checks', usage:'Provider usage', costActual:'Actual cost', costBasis:'Cost basis', warnings:'Warnings',
    requestIds:'Request IDs', tokens:'Tokens (in/out)', none:'None',
    backendMissing:'<b>Building is not available on this server.</b> It needs PostgreSQL and S3 storage. You can sign up, manage projects and see a plan and cost.',
    emailUnverified:'Your email is not verified yet.',
    err401:'Your session expired. Sign in again.', err402:'Not enough credits or not allowed on your plan: ',
    err403:'You do not have access to this.', err404:'Not found.', err409:'Clarification is needed before continuing.',
    err503:'This service is not configured on the server yet: ', errNet:'Cannot reach the server. Check your connection and try again.',
    needPrompt:'Write at least a few words about the app.', needEmail:'Enter an email and a password of at least 10 characters.',
    registered:'Account created.', created:'Project created.', renamed:'Name saved.', archived:'Project archived.',
    downloadReady:'Download started.', untitled:'New project',
    lifecycle:'Full build lifecycle: plan, code, install, build, test, repair, preview and export', operatorDetails:'Details for the server operator',
    b_durable_backend_not_configured:'Building needs a server with PostgreSQL and S3 storage.',
    b_infrastructure:k=>`App infrastructure is not ready: ${k}`, b_image_provider:'Icon and image generation is not configured.',
    b_plan_cannot_authorize_cost:'Your current plan does not authorize paid variable cost.',
    b_cost_quote_unknown:'Some build costs are unknown, so the build cannot be authorized.',
    k_database:'database', k_auth_session:'sign-in and sessions', k_object_storage:'file storage', k_scheduled_http:'scheduled jobs', k_outbound:'email and webhooks',
  },
};

const S = {
  lang: localStorage.getItem('148ai_lang') || 'he',
  signedIn: false,
  me: null, projects: [], projectId: localStorage.getItem('148ai_project') || '',
  durable: false, plan: null, build: null, versions: [], previewId: null, preview: null,
  mod: null, timers: {},
};

const $ = id => document.getElementById(id);
const t = key => (T[S.lang] && T[S.lang][key]) ?? T.en[key] ?? key;

function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid.nodeType ? kid : String(kid));
  return el;
}

/* ---------- API ---------- */
class ApiError extends Error {
  constructor(status, detail) { super(typeof detail === 'string' ? detail : (detail && (detail.error || detail.reason)) || `HTTP ${status}`); this.status = status; this.detail = detail; }
}
async function api(path, { method = 'GET', body, raw = false } = {}) {
  // The session travels in the HttpOnly cookie set by the server; the token is
  // never readable by or stored in this page.
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let res;
  try { res = await fetch(path, { method, headers, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body) }); }
  catch { throw new ApiError(0, t('errNet')); }
  if (raw && res.ok) return res;
  let data = null;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const detail = data && typeof data === 'object' && 'detail' in data ? data.detail : data;
    if (res.status === 401 && S.signedIn) signOutLocal();
    throw new ApiError(res.status, detail);
  }
  return data;
}
function explain(err) {
  if (!(err instanceof ApiError)) return String(err && err.message || err);
  const msg = err.message || '';
  switch (err.status) {
    case 0: return t('errNet');
    case 401: return t('err401');
    case 402: return t('err402') + msg;
    case 403: return t('err403');
    case 404: return t('err404');
    case 409: return t('err409');
    case 503: return t('err503') + msg;
    default: return msg;
  }
}
const pid = () => encodeURIComponent(S.projectId);

/* ---------- language ---------- */
function applyLang() {
  document.documentElement.lang = S.lang;
  document.documentElement.dir = S.lang === 'he' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  $('langBtn').textContent = S.lang === 'he' ? 'English' : 'עברית';
  $('langBtn').lang = S.lang === 'he' ? 'en' : 'he';
  $('prompt').placeholder = t('promptPlaceholder');
  $('publishNote').textContent = t('publishNotConfigured');
  document.title = S.lang === 'he' ? '148AI · סביבת יצירה' : '148AI · Creator workspace';
  renderBanner(); renderPlan(); renderTrack(); renderVersions(); renderEvidence(); renderPreview(); renderMod();
}

/* ---------- auth ---------- */
function signOutLocal() {
  S.signedIn = false; S.me = null;
  Object.values(S.timers).forEach(clearTimeout); S.timers = {};
  showView();
}
async function authSubmit(kind) {
  const email = $('email').value.trim(), password = $('password').value;
  const msg = $('authMsg'); msg.className = 'msg'; msg.textContent = '';
  if (!email.includes('@') || password.length < 10) { msg.textContent = t('needEmail'); return; }
  try {
    const path = kind === 'register' ? '/api/v28/auth/register' : '/api/v28/auth/login';
    await api(path, { method: 'POST', body: { email, password } });
    $('password').value = '';
    await enterWorkspace();
  } catch (e) { msg.textContent = explain(e); }
}
async function logout() {
  try { await api('/api/v28/auth/logout', { method: 'POST' }); } catch { /* local sign-out still happens */ }
  signOutLocal();
}

/* ---------- views ---------- */
function showView() {
  const signedIn = Boolean(S.signedIn && S.me);
  $('welcomeView').hidden = signedIn;
  $('workspaceView').hidden = !signedIn;
  $('projectbar').hidden = !signedIn;
  $('accountBox').hidden = !signedIn;
  if (signedIn) {
    const unverified = S.me.email_verified === false ? ` (${t('emailUnverified')})` : '';
    $('accountEmail').textContent = S.me.email + unverified;
  }
  renderBanner();
}
function renderBanner() {
  const b = $('backendBanner');
  const show = Boolean(S.me) && !S.durable;
  b.hidden = !show;
  if (show) b.innerHTML = t('backendMissing'); // static copy from T, no user data
}
async function loadStatus() {
  try { const s = await api('/api/v28/m5/status'); S.durable = !(s.blockers || []).includes('durable_postgres_s3_backend_required'); }
  catch { S.durable = false; }
}
async function enterWorkspace() {
  S.me = await api('/api/v28/me');
  S.signedIn = true;
  await loadStatus();
  showView();
  await loadProjects();
}

/* ---------- projects ---------- */
async function loadProjects() {
  const d = await api('/api/v28/projects');
  S.projects = (d.projects || []).filter(p => !p.archived_at && p.status !== 'ARCHIVED');
  if (!S.projects.find(p => p.id === S.projectId)) S.projectId = S.projects[0] ? S.projects[0].id : '';
  renderProjects();
  await selectProject(S.projectId);
}
function renderProjects() {
  const sel = $('projectSelect');
  sel.replaceChildren(...S.projects.map(p => h('option', { value: p.id, selected: p.id === S.projectId }, p.title || t('untitled'))));
  $('emptyProjects').hidden = S.projects.length > 0;
  $('composer').hidden = S.projects.length === 0;
  $('projectMenuBtn').disabled = false;
}
async function createProject(title) {
  const p = await api('/api/v28/projects', { method: 'POST', body: { title: title || t('untitled') } });
  S.projectId = p.id;
  await loadProjects();
}
async function selectProject(id) {
  Object.values(S.timers).forEach(clearTimeout); S.timers = {};
  S.projectId = id || ''; localStorage.setItem('148ai_project', S.projectId);
  S.plan = null; S.build = null; S.preview = null; S.previewId = null; S.mod = null; S.versions = []; S.newBuildOpen = false;
  $('planPanel').hidden = true; $('progressPanel').hidden = true;
  applyLang();
  if (!S.projectId) return;
  await loadVersions();
}

/* ---------- plan + quote ---------- */
async function requestPlan() {
  const prompt = $('prompt').value.trim();
  const msg = $('composerMsg'); msg.textContent = '';
  if (prompt.length < 12) { msg.textContent = t('needPrompt'); return; }
  $('planBtn').disabled = true;
  try {
    S.plan = await api(`/api/v28/projects/${pid()}/build-contracts`, { method: 'POST', body: { prompt } });
    S.build = null; renderPlan(); renderTrack();
    $('planPanel').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
  } catch (e) { msg.textContent = explain(e); }
  finally { $('planBtn').disabled = false; }
}
function pill(status) {
  const cls = { LIVE: 'ok', SELF_CONTAINED: 'ok', PRICED: 'ok', PARTIAL: 'warn', UNKNOWN: 'warn', NOT_CONFIGURED: 'bad', BLOCKED: 'bad', NOT_AUTHORIZED: 'bad' }[status] || 'muted';
  return h('span', { class: `pill ${cls}` }, t(`st_${status}`) || status || '—');
}
const money = v => (v === null || v === undefined) ? t('costUnknown') : `$${Number(v).toFixed(2)}`;
function renderPlan() {
  const panel = $('planPanel'); const p = S.plan;
  if (!p) { panel.hidden = true; return; }
  panel.hidden = false;
  const facts = (label, items) => items && items.length ? [h('h3', {}, label), h('ul', { class: 'facts' }, items.map(x => h('li', {}, x)))] : [];
  const required = p.capabilities.filter(c => c.required);
  const lifecycle = required.filter(c => c.key.startsWith('software.'));
  const caps = [];
  if (lifecycle.length) caps.push(h('li', {}, h('span', {}, t('lifecycle')), h('span', { class: 'pill muted' }, t('byPipeline'))));
  for (const c of required.filter(c => !c.key.startsWith('software.'))) {
    caps.push(h('li', {}, h('span', {}, c.purpose || c.key),
      h('span', { class: 'pill muted' }, c.executed_by === 'external provider' ? t('byProvider') : t('byPipeline'))));
  }
  const infra = p.infrastructure.map(i => h('li', {}, h('span', {}, t(`k_${i.kind}`) || i.purpose), pill(i.readiness)));
  const kids = [
    h('h2', {}, t('planTitle')),
    h('h3', {}, t('understood')),
    h('p', { class: 'summary' }, p.product.summary || p.product.title),
    ...facts(t('roles'), p.product.user_roles), ...facts(t('data'), p.product.data_requirements),
    ...facts(t('integrations'), p.product.required_integrations),
    h('h3', {}, t('capabilities')), h('ul', { class: 'checklist' }, caps),
    h('h3', {}, t('infrastructure')), h('ul', { class: 'checklist' }, infra),
    h('h3', {}, t('cost')),
    h('div', { class: 'cost' },
      h('div', {}, h('span', {}, t('creditsRequired')), h('b', {}, p.credits_required ?? t('costUnknown'))),
      h('div', {}, h('span', {}, t('creditsRemaining')),
        h('b', {}, (p.allowance && p.allowance.credits_remaining != null) ? p.allowance.credits_remaining : '—')),
      h('div', {}, h('span', {}, t('quoteStatus')), pill(p.build_authorization || 'UNKNOWN'))),
  ];
  if (p.clarification_questions.length) {
    kids.push(h('h3', {}, t('questions')), h('ul', { class: 'checklist' }, p.clarification_questions.map(q => h('li', {}, q.question))));
  }
  if (p.blockers.length) {
    const title = b => {
      if (b.code.startsWith('infrastructure_')) {
        const kind = (p.infrastructure.find(i => b.code.startsWith(`infrastructure_${i.kind}_`)) || {}).kind;
        return t('b_infrastructure')(kind ? t(`k_${kind}`) : b.code);
      }
      if (b.code.startsWith('image_provider_')) return t('b_image_provider');
      return T[S.lang][`b_${b.code}`] || T.en[`b_${b.code}`] || b.message;
    };
    const titles = [...new Set(p.blockers.map(title))];
    kids.push(h('h3', {}, t('blockersTitle')), h('ul', { class: 'blockers' }, titles.map(x => h('li', {}, x))),
      h('details', { class: 'tech' }, h('summary', {}, t('operatorDetails')),
        h('ul', { dir: 'ltr' }, p.blockers.map(b => h('li', {}, h('code', {}, b.code), ': ', b.message)))));
  }
  kids.push(h('div', { class: 'row' },
    h('button', { id: 'confirmBtn', disabled: !p.can_build || Boolean(S.build && !isTerminal(S.build.status)), onclick: startBuild }, t('confirm')),
    h('button', { class: 'secondary', onclick: () => { $('prompt').focus(); } }, t('editRequest'))));
  panel.replaceChildren(...kids);
}

/* ---------- build ---------- */
const isTerminal = s => ['ready', 'failed', 'cancelled', 'READY', 'FAILED', 'CANCELLED'].includes(s);
async function startBuild() {
  if (!S.plan || !S.plan.can_build) return;
  $('buildMsg').textContent = '';
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds`, { method: 'POST',
      body: { prompt: $('prompt').value.trim() || 'build', build_contract_id: S.plan.build_contract_id } });
    S.build = { id: d.build_id, status: 'queued', phase: 'QUEUED', evidence: {} };
    renderPlan(); renderTrack(); renderBuilt(); pollBuild();
  } catch (e) {
    $('progressPanel').hidden = false; $('buildMsg').textContent = explain(e);
  }
}
async function pollBuild() {
  if (!S.build) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/builds/${encodeURIComponent(S.build.id)}`);
    S.build = { ...S.build, ...d };
    renderTrack(); renderEvidence();
    if (isTerminal(d.status)) {
      renderPlan();
      if (String(d.status).toLowerCase() === 'ready' && d.result_version_id) {
        S.newBuildOpen = false;
        await loadVersions();
        startPreview(d.result_version_id);
      } else if (d.result_version_id) { await loadVersions(); }
      else renderBuilt();
      return;
    }
  } catch (e) { $('buildMsg').textContent = explain(e); }
  S.timers.build = setTimeout(pollBuild, 2500);
}
const PHASE_ORDER = ['PLANNING', 'INFRASTRUCTURE', 'ASSETS', 'GENERATING', 'VERIFYING'];
function renderTrack() {
  const panel = $('progressPanel');
  if (!S.plan && !S.build) { panel.hidden = true; return; }
  panel.hidden = false;
  const b = S.build; const ev = (b && b.evidence) || {};
  const status = b ? String(b.status).toLowerCase() : null;
  const phase = b ? String(b.phase || '').toUpperCase() : null;
  const reached = PHASE_ORDER.indexOf(phase);
  const failedCode = status === 'failed' ? (b.error_code || '') : '';
  // Step at which a failed build stopped. Steps after it never ran: they are
  // shown as skipped, never as done (a failed build once showed the quality
  // gates as passed although generation had failed before them).
  const FAIL_STEP = { infrastructure_not_configured: 1, capability_not_configured: 2, capability_gate_failed: 2,
    worker_exception: 3, verification_failed: 3, quality_gate_failed: 4, security_gate_failed: 4, rights_gate_not_clear: 4 };
  const failedIdx = failedCode in FAIL_STEP ? FAIL_STEP[failedCode] : -1;
  const preview = S.preview;
  const steps = [];
  const push = (name, state, note) => steps.push(h('li', { class: `step ${state}` }, h('span', { class: 'dot', 'aria-hidden': 'true' }),
    h('div', {}, h('span', { class: 'name' }, name), note ? h('span', { class: 'note' }, note) : null,
      h('span', { class: 'sr' }, ` (${state})`))));
  push(t('stepPlanning'), S.plan ? 'done' : 'active');
  push(t('stepContract'), S.plan ? (S.plan.status === 'READY' ? 'done' : 'failed') : 'pending',
    S.plan && S.plan.status !== 'READY' ? t('err409') : null);
  const backendStep = (key, idx, failCodes, note) => {
    if (!b) return push(t(key), 'pending', note);
    if (failCodes.includes(failedCode)) return push(t(key), 'failed', friendlyError(b));
    if (status === 'ready') return push(t(key), 'done', note);
    if (status === 'failed') return push(t(key), (failedIdx >= 0 ? idx < failedIdx : reached > idx) ? 'done' : 'skipped', note);
    if (status === 'queued') return push(t(key), 'pending', idx === 0 ? t('queued') : note);
    return push(t(key), reached === idx ? 'active' : reached > idx ? 'done' : 'pending', note);
  };
  const infraEv = ev.infrastructure; const capEv = ev.capabilities;
  backendStep('stepInfra', 1, ['infrastructure_not_configured'], infraEv === null && status === 'ready' ? t('none') : null);
  backendStep('stepAssets', 2, ['capability_not_configured', 'capability_gate_failed'], null);
  const repairNote = b && b.repair_rounds !== undefined && b.repair_rounds !== null && isTerminal(b.status) ? t('repairs')(b.repair_rounds) : t('noteGenerate');
  backendStep('stepGenerate', 3, ['worker_exception', 'verification_failed'], repairNote);
  backendStep('stepGates', 4, ['quality_gate_failed', 'security_gate_failed', 'rights_gate_not_clear'], null);
  let pState = 'pending', pNote = null;
  if (preview) {
    const ps = preview.status;
    if (ps === 'RUNNING') pState = 'done';
    else if (['FAILED', 'NOT_PREVIEWABLE', 'UNAVAILABLE'].includes(ps)) { pState = 'failed'; pNote = preview.error_message; }
    else if (ps === 'EXPIRED' || ps === 'STOPPED') { pState = 'skipped'; pNote = t('previewExpired'); }
    else pState = 'active';
  }
  push(t('stepPreview'), pState, pNote);
  $('track').replaceChildren(...steps);
  const msg = $('buildMsg'); msg.className = 'msg';
  if (status === 'ready') { msg.className = 'msg ok'; msg.textContent = t('buildReady'); }
  else if (status === 'failed') {
    // Customer-facing reason; the raw technical message stays one click away.
    msg.replaceChildren(`${t('buildFailed')}: ${friendlyError(b)}`);
    if (b.error_message) msg.append(h('details', { class: 'tech' }, h('summary', {}, t('techDetails')), h('code', { dir: 'ltr' }, b.error_message)));
  }
  else msg.textContent = '';
}

/* ---------- preview ---------- */
async function startPreview(versionId) {
  S.preview = { status: 'STARTING', version_id: versionId }; renderPreview(); renderTrack();
  try {
    const d = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(versionId)}/previews`, { method: 'POST' });
    S.previewId = d.preview_id; pollPreview();
  } catch (e) {
    const notPreviewable = e.status === 422;
    S.preview = { status: notPreviewable ? 'NOT_PREVIEWABLE' : 'UNAVAILABLE', version_id: versionId,
      error_message: notPreviewable ? (e.detail && e.detail.reason) || e.message : explain(e) };
    renderPreview(); renderTrack();
  }
}
async function pollPreview() {
  if (!S.previewId) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/previews/${encodeURIComponent(S.previewId)}`);
    S.preview = d; renderPreview(); renderTrack();
    if (['RUNNING', 'FAILED', 'NOT_PREVIEWABLE', 'EXPIRED', 'STOPPED'].includes(d.status)) return;
  } catch (e) { S.preview = { status: 'UNAVAILABLE', error_message: explain(e) }; renderPreview(); return; }
  S.timers.preview = setTimeout(pollPreview, 2000);
}
function renderPreview() {
  const p = S.preview; const frame = $('previewFrame'); const empty = $('previewEmpty'); const text = $('previewEmptyText');
  const link = $('openPreviewLink'); const refresh = $('refreshPreviewBtn');
  const running = p && p.status === 'RUNNING' && p.preview_url;
  frame.hidden = !running; empty.hidden = Boolean(running);
  refresh.disabled = !running; link.setAttribute('aria-disabled', running ? 'false' : 'true');
  $('previewUrl').textContent = running ? p.preview_url : '—';
  if (running) {
    if (frame.src !== p.preview_url) frame.src = p.preview_url;
    link.href = p.preview_url;
    return;
  }
  link.removeAttribute('href');
  if (frame.src) frame.removeAttribute('src');
  let message = t('noPreview');
  if (p) {
    if (p.status === 'NOT_PREVIEWABLE') message = t('previewNotPreviewable') + (p.error_message || '');
    else if (p.status === 'UNAVAILABLE') message = t('previewUnavailable') + (p.error_message || '');
    else if (p.status === 'FAILED') message = t('previewFailed') + (p.error_message || '');
    else if (p.status === 'EXPIRED' || p.status === 'STOPPED') message = t('previewExpired');
    else message = t('previewStarting');
  }
  text.textContent = message;
  // A project opened later (or a preview that was unavailable) can start one
  // for its current version too, not only right after a build or a change.
  const canRetry = currentVersionId() && (!p || ['EXPIRED', 'STOPPED', 'FAILED', 'UNAVAILABLE'].includes(p.status));
  const existing = empty.querySelector('button'); if (existing) existing.remove();
  if (canRetry) empty.append(h('button', { class: 'secondary', onclick: () => startPreview(currentVersionId()) }, t('startPreview')));
}

function friendlyError(b) {
  const known = (t('errCodes') || {})[b.error_code];
  return known || b.error_message || b.error_code || '';
}

/* ---------- versions ---------- */
function currentVersionId() { return S.versions.length ? S.versions[0].id : null; }
async function loadVersions() {
  try {
    const d = await api(`/api/v28/projects/${pid()}/history`);
    S.versions = (d.versions || []).slice().sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  } catch { S.versions = []; }
  renderVersions(); renderMod(); renderBuilt(); renderPreview();
  $('downloadBtn').disabled = !currentVersionId();
}
/* Once a project has a product, lead with what it is and how to change it;
   a new build from scratch stays one click away. */
function renderBuilt() {
  const v = S.versions[0];
  const building = (!!S.plan && !S.build) || (!!S.build && !isTerminal(S.build.status));
  $('builtPanel').hidden = !v;
  $('newBuildRow').hidden = !v || S.newBuildOpen || building;
  $('composer').hidden = !!v && !S.newBuildOpen && !building;
  if (!v) return;
  $('builtName').textContent = v.title || v.message || v.id;
  $('builtSummary').textContent = v.summary || '';
  $('builtFeatures').replaceChildren(...(v.features || []).map((f) => h('li', {}, f)));
  let when = v.created_at;
  try { when = new Intl.DateTimeFormat(S.lang === 'he' ? 'he-IL' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(v.created_at)); } catch { /* keep raw */ }
  $('builtMeta').replaceChildren(t('builtVersion'), ': ', h('code', { dir: 'ltr' }, String(v.id).slice(0, 12)), ` · ${when}`,
    v.file_count ? ` · ${v.file_count} ${t('files')}` : '');
}
function renderVersions() {
  const panel = $('versionsPanel');
  panel.hidden = !S.projectId || !S.me;
  const list = $('versionsList');
  if (!S.versions.length) { list.replaceChildren(h('li', { class: 'meta' }, t('noVersions'))); return; }
  const fmt = new Intl.DateTimeFormat(S.lang === 'he' ? 'he-IL' : 'en-GB', { dateStyle: 'short', timeStyle: 'short' });
  list.replaceChildren(...S.versions.map((v, i) => {
    let when = v.created_at; try { when = fmt.format(new Date(v.created_at)); } catch { /* keep raw */ }
    return h('li', {},
      h('div', {}, h('div', {}, v.title || v.message || v.id), h('div', { class: 'meta' }, when, ' ', h('code', { dir: 'ltr' }, String(v.id).slice(0, 12)))),
      i === 0 ? h('span', { class: 'pill ok' }, t('current')) : h('button', { class: 'ghost', onclick: () => restoreVersion(v.id) }, t('restore')));
  }));
}
async function restoreVersion(versionId) {
  try {
    await api(`/api/v28/projects/${pid()}/rollback`, { method: 'POST', body: { target_version_id: versionId, message: 'rollback from workspace' } });
    await loadVersions();
    $('buildMsg').className = 'msg ok'; $('buildMsg').textContent = t('restored'); $('progressPanel').hidden = false;
  } catch (e) { $('progressPanel').hidden = false; $('buildMsg').className = 'msg'; $('buildMsg').textContent = explain(e); }
}

/* ---------- modification ---------- */
async function sendModification() {
  const followup = $('followup').value.trim(); const vid = currentVersionId();
  if (followup.length < 3 || !vid) return;
  $('modifyBtn').disabled = true;
  try {
    const d = await api(`/api/v28/projects/${pid()}/versions/${encodeURIComponent(vid)}/modifications`, { method: 'POST', body: { followup } });
    S.mod = { id: d.modification_id, status: 'QUEUED' }; renderMod(); pollMod();
  } catch (e) { S.mod = { status: 'ERROR', error_message: explain(e) }; renderMod(); }
  finally { $('modifyBtn').disabled = false; }
}
async function pollMod() {
  if (!S.mod || !S.mod.id) return;
  try {
    const d = await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}`);
    S.mod = { ...S.mod, ...d }; renderMod();
    if (['READY_FOR_REVIEW', 'FAILED', 'ACCEPTED', 'REJECTED', 'SUPERSEDED', 'CLARIFICATION_REQUIRED', 'NEEDS_CLARIFICATION', 'CONFLICT'].includes(d.status)) return;
  } catch (e) { S.mod = { ...S.mod, status: 'ERROR', error_message: explain(e) }; renderMod(); return; }
  S.timers.mod = setTimeout(pollMod, 3000);
}
async function decideMod(accept) {
  try {
    const d = await api(`/api/v28/projects/${pid()}/modifications/${encodeURIComponent(S.mod.id)}/${accept ? 'accept' : 'reject'}`,
      { method: 'POST', body: accept ? { message: 'accepted in workspace' } : { reason: 'rejected in workspace' } });
    S.mod = { ...S.mod, status: accept ? 'ACCEPTED' : 'REJECTED', promoted_version_id: d.version_id || d.promoted_version_id };
    renderMod();
    if (accept) { await loadVersions(); if (currentVersionId()) startPreview(currentVersionId()); }
  } catch (e) { S.mod = { ...S.mod, status: 'ERROR', error_message: explain(e) }; renderMod(); }
}
function renderMod() {
  $('modifyPanel').hidden = !currentVersionId();
  const box = $('modifyState'); const m = S.mod;
  if (!m) { box.replaceChildren(); return; }
  const kids = [];
  if (m.status === 'READY_FOR_REVIEW') {
    kids.push(h('p', {}, t('modReview')),
      m.classification ? h('p', { class: 'hint' }, `${t('classification')}: ${m.classification}`) : null,
      h('div', { class: 'row' }, h('button', { onclick: () => decideMod(true) }, t('accept')),
        h('button', { class: 'secondary', onclick: () => decideMod(false) }, t('reject'))));
  } else if (m.status === 'ACCEPTED') kids.push(h('p', { class: 'msg ok' }, t('modAccepted')));
  else if (m.status === 'REJECTED') kids.push(h('p', { class: 'hint' }, t('modRejected')));
  else if (['FAILED', 'ERROR', 'CLARIFICATION_REQUIRED', 'NEEDS_CLARIFICATION', 'CONFLICT'].includes(m.status)) kids.push(h('p', { class: 'msg' }, t('modFailed') + (m.error_message || m.classification_reason || m.status)));
  else kids.push(h('p', { class: 'hint' }, t('modQueued')));
  box.replaceChildren(...kids);
}

/* ---------- evidence ---------- */
function renderEvidence() {
  const panel = $('evidencePanel'); const ev = S.build && S.build.evidence;
  if (!ev || !isTerminal(S.build.status)) { panel.hidden = true; return; }
  panel.hidden = false;
  const gates = ev.gates || {};
  const gateText = Object.entries(gates).map(([k, v]) => `${k}: ${v && v.passed === false ? '✗' : '✓'}`).join(', ') || t('none');
  const warnings = [];
  if (ev.capabilities && ev.capabilities.status && ev.capabilities.status !== 'VERIFIED') warnings.push(`capabilities: ${ev.capabilities.status}`);
  const row = (k, v) => [h('dt', {}, k), h('dd', {}, v)];
  $('evidenceBody').replaceChildren(
    h('dl', {},
      row(t('gates'), gateText),
      row(t('repairs')(S.build.repair_rounds ?? '—'), ''),
      row('billing', ev.billing || '—'),
      row(t('warnings'), warnings.join(', ') || t('none'))),
    h('pre', {}, JSON.stringify({ build_contract: ev.build_contract, infrastructure: ev.infrastructure, capabilities: ev.capabilities }, null, 2)));
}

/* ---------- download / publish ---------- */
async function downloadZip() {
  const vid = currentVersionId(); if (!vid) return;
  try {
    const res = await api(`/api/v28/projects/${pid()}/export?version_id=${encodeURIComponent(vid)}`, { raw: true });
    const blob = await res.blob();
    const a = h('a', { href: URL.createObjectURL(blob), download: `${S.projectId}-148ai.zip` });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  } catch (e) { $('publishNote').textContent = explain(e); }
}
function publishNotConfigured() { $('publishNote').textContent = t('publishNotConfigured'); $('publishNote').focus?.(); }

/* ---------- project dialog ---------- */
function openProjectDialog() {
  const p = S.projects.find(x => x.id === S.projectId);
  $('renameInput').value = p ? p.title : ''; $('newProjectInput').value = ''; $('projectMsg').textContent = '';
  $('archiveBtn').disabled = !p; $('renameBtn').disabled = !p;
  $('projectDialog').showModal();
}
async function dialogAction(fn, okKey) {
  const msg = $('projectMsg'); msg.className = 'msg'; msg.textContent = '';
  try { await fn(); msg.className = 'msg ok'; msg.textContent = t(okKey); }
  catch (e) { msg.textContent = explain(e); }
}

/* ---------- wiring ---------- */
function wire() {
  $('authForm').addEventListener('submit', e => { e.preventDefault(); authSubmit('login'); });
  $('registerBtn').addEventListener('click', () => authSubmit('register'));
  $('logoutBtn').addEventListener('click', logout);
  $('langBtn').addEventListener('click', () => { S.lang = S.lang === 'he' ? 'en' : 'he'; localStorage.setItem('148ai_lang', S.lang); applyLang(); });
  $('projectSelect').addEventListener('change', e => selectProject(e.target.value));
  $('projectMenuBtn').addEventListener('click', openProjectDialog);
  $('firstProjectForm').addEventListener('submit', async e => {
    e.preventDefault();
    try { await createProject($('firstProjectName').value.trim()); } catch (err) { $('composerMsg').textContent = explain(err); }
  });
  $('renameBtn').addEventListener('click', () => dialogAction(async () => {
    await api(`/api/v28/projects/${pid()}`, { method: 'PATCH', body: { title: $('renameInput').value.trim() } });
    await loadProjects();
  }, 'renamed'));
  $('archiveBtn').addEventListener('click', () => dialogAction(async () => {
    await api(`/api/v28/projects/${pid()}/archive`, { method: 'POST' });
    await loadProjects();
  }, 'archived'));
  $('newProjectBtn').addEventListener('click', () => dialogAction(async () => {
    await createProject($('newProjectInput').value.trim());
  }, 'created'));
  $('planBtn').addEventListener('click', requestPlan);
  $('newBuildBtn').addEventListener('click', () => { S.newBuildOpen = true; renderBuilt(); $('prompt').focus(); });
  $('modifyBtn').addEventListener('click', sendModification);
  $('refreshPreviewBtn').addEventListener('click', () => { const f = $('previewFrame'); if (f.src) f.src = f.src; });
  $('downloadBtn').addEventListener('click', downloadZip);
  $('publishBtn').addEventListener('click', publishNotConfigured);
}

async function boot() {
  wire(); applyLang();
  localStorage.removeItem('148ai_token'); // tokens from older versions are never kept in page storage
  try { await enterWorkspace(); return; } catch { /* no valid session cookie */ }
  showView();
}
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
document.addEventListener('DOMContentLoaded', boot);

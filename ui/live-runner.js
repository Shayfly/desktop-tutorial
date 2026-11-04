// B3 (#235): state shared by the runner. Undeclared, the first click threw a
// ReferenceError on clearTimeout(pollTimer) before any request was sent.
let pollTimer = null;
let currentProjectId = null;

// B3: minimal translation lookup. Falls back to the key itself so a missing string
// never stops the runner. Loading the server copy (/api/v28/ui/translations) is a later step.
let LIVE_COPY = {};
function t(key) {
  return (LIVE_COPY && typeof LIVE_COPY[key] === 'string' && LIVE_COPY[key]) || key;
}

// B3: the last build per project, so the catch path can recover a build that
// finished while the request that started it failed (read in runPromptFirstBuild).
function rememberBuild(projectId, buildId) {
  if (!projectId || !buildId) return;
  try {
    localStorage.setItem(`148ai_last_build_${projectId}`, buildId);
  } catch (_) {}
}

// B3: draw the build's stages into #liveTimeline. Accepts the build object from
// fetchBuild ({stage, status, events: [...]}) or a bare events array. Missing,
// empty or malformed events draw nothing and never throw. Text only (no innerHTML):
// event messages come from the server.
function renderTimeline(buildOrEvents) {
  const list = $('liveTimeline');
  if (!list) return;
  const events = Array.isArray(buildOrEvents)
    ? buildOrEvents
    : (buildOrEvents && Array.isArray(buildOrEvents.events) ? buildOrEvents.events : []);
  list.replaceChildren();
  for (const event of events) {
    if (!event || typeof event !== 'object') continue;
    const item = document.createElement('li');
    item.className = 'timelineStep';
    const stage = document.createElement('b');
    stage.textContent = String(event.stage || '');
    item.append(stage);
    if (event.message) {
      const message = document.createElement('span');
      message.textContent = ` ${String(event.message)}`;
      item.append(message);
    }
    list.append(item);
  }
}

// B3: show the "ready" card for a finished build. A missing or partial build
// still shows the card, with whatever fields it has.
function showReady(build) {
  const card = $('resultCard');
  if (card) card.classList.remove('hidden');
  const meta = $('resultMeta');
  if (meta) {
    const parts = [];
    if (build && build.version_id) parts.push(`version ${build.version_id}`);
    if (build && build.stage) parts.push(String(build.stage));
    meta.textContent = parts.join(' · ');
  }
  const status = $('buildStatus');
  if (status) {
    // Plain text on purpose: the copy key "ready" is the GLOBAL READINESS heading, and a new
    // key would have to exist in all 20 locales (test_i18n_contract).
    status.textContent = 'Ready';
    status.className = 'status ok';
  }
}

// B3: the project's live_core versions, shown in #output. reveal=false keeps the
// "Advanced controls" panel closed (the build flow loads versions in the background).
async function loadVersions(projectId, reveal = true) {
  if (!projectId) return [];
  const data = await req(`/api/live/projects/${encodeURIComponent(projectId)}/versions`, { headers: auth() });
  const versions = (data && Array.isArray(data.versions)) ? data.versions : [];
  const output = $('output');
  if (output) output.textContent = JSON.stringify(versions, null, 2);
  if (reveal) {
    const panel = document.querySelector('.advanced');
    if (panel) panel.open = true;
  }
  return versions;
}

// B3: one build's state and events from live_core.
async function fetchBuild(buildId) {
  return req(`/api/live/builds/${encodeURIComponent(buildId)}`, { headers: auth() });
}

async function pollLiveBuild(buildId, timeoutMs = 55000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const state = await fetchBuild(buildId);
    renderTimeline(state);
    if (state.stage === 'ready' || state.stage === 'failed') return state;
    await new Promise((resolve) => setTimeout(resolve, 450));
  }
  throw new Error('Build status timed out');
}

async function runPromptFirstBuild() {
  // B3 step 4: no live_core session means the sign-in form, not a request that 401s.
  if (!liveToken()) {
    showAuth();
    setMode('login');
    return msg('accountState', 'Sign in to build.', 'error');
  }
  const prompt = $('prompt').value.trim();
  if (prompt.length < 3) return msg('state', t('describe'), 'error');

  clearTimeout(pollTimer);
  $('buildBtn').disabled = true;
  $('buildBtn').textContent = t('building');
  $('resultCard').classList.add('hidden');
  msg('state', t('building'));

  try {
    const started = await req('/api/live/builds', {
      method: 'POST',
      headers: { ...auth(), 'content-type': 'application/json' },
      body: JSON.stringify({
        prompt,
        project_id: $('projectSelect').value || null,
        target_markets: markets(),
      }),
    });

    currentProjectId = started.project_id;
    rememberBuild(started.project_id, started.id);
    localStorage.setItem('148ai_last_project', currentProjectId);

    // Persist the prompt-first project in the visible workspace before execution.
    // If generation/testing fails, the next attempt remains on this project instead
    // of silently creating a second project.
    await loadProjects();
    $('projectSelect').value = currentProjectId;

    const initial = await fetchBuild(started.id);
    renderTimeline(initial);

    const runRequest = req(`/api/live/builds/${encodeURIComponent(started.id)}/run`, {
      method: 'POST',
      headers: { ...auth(), 'content-type': 'application/json' },
      body: JSON.stringify({ target_markets: markets() }),
    });

    const [runResult, observed] = await Promise.all([
      runRequest,
      pollLiveBuild(started.id),
    ]);

    const full = observed.stage === 'ready' || observed.stage === 'failed'
      ? observed
      : await fetchBuild(runResult.id || started.id);

    renderTimeline(full);
    if (full.stage === 'ready') {
      showReady(full);
      await loadProjects();
      $('projectSelect').value = currentProjectId;
      await loadVersions(currentProjectId, false);
    } else {
      // Keep the failed build's project selected so a corrected prompt improves
      // the same project instead of spawning a duplicate.
      $('projectSelect').value = currentProjectId;
      msg('state', full.error || t('buildFailed'), 'error');
    }
  } catch (error) {
    try {
      const buildId = currentProjectId ? localStorage.getItem(`148ai_last_build_${currentProjectId}`) : '';
      if (buildId) {
        const latest = await fetchBuild(buildId);
        renderTimeline(latest);
        if (latest.stage === 'ready') {
          showReady(latest);
          return;
        }
      }
    } catch (_) {}
    if (currentProjectId) $('projectSelect').value = currentProjectId;
    $('buildStatus').textContent = t('failed');
    $('buildStatus').className = 'status bad';
    msg('state', error.message || t('buildFailed'), 'error');
  } finally {
    $('buildBtn').disabled = false;
    $('buildBtn').textContent = t('build');
  }
}

// Decision #232, blocker 3: the preview opens in a new tab, never in an iframe.
async function openLivePreview(projectId, versionId) {
  const created = await req(
    `/api/live/projects/${encodeURIComponent(projectId)}/versions/${encodeURIComponent(versionId)}/preview`,
    { method: 'POST', headers: auth() },
  );
  window.open(created.url, '_blank', 'noopener');
}

// B3: buildBtn runs the live_core flow. ui/app.js no longer binds it to the v28 build.
document.addEventListener('DOMContentLoaded', () => {
  $('buildBtn').onclick = runPromptFirstBuild;
});

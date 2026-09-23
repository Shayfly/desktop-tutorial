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
  const prompt = $('prompt').value.trim();
  if (prompt.length < 3) return msg('state', t('describe'), 'error');

  clearTimeout(pollTimer);
  $('buildBtn').disabled = true;
  $('buildBtn').textContent = t('building');
  $('resultCard').classList.add('hidden');
  $('previewPanel').classList.add('hidden');
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
    $('buildStatus').textContent = t('failed');
    $('buildStatus').className = 'status bad';
    msg('state', error.message || t('buildFailed'), 'error');
  } finally {
    $('buildBtn').disabled = false;
    $('buildBtn').textContent = t('build');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  $('buildBtn').onclick = runPromptFirstBuild;
});

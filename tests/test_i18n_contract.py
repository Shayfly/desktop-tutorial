from pathlib import Path


def test_primary_ui_is_prompt_first_and_uses_live_core():
    html = Path("ui/index.html").read_text("utf-8")
    js = Path("ui/app.js").read_text("utf-8")
    assert 'id="prompt"' in html
    assert 'id="buildBtn"' in html
    assert 'id="timeline"' in html
    assert 'id="previewFrame"' in html
    assert 'id="createProjectBtn"' not in html
    assert 'id="projectTitle"' not in html
    assert "/api/live/builds" in js
    assert "/api/v28/projects" not in js


def test_live_runner_drives_run_endpoint_and_is_syntax_checked_in_ci():
    html = Path("ui/index.html").read_text("utf-8")
    runner = Path("ui/live-runner.js").read_text("utf-8")
    workflow = Path(".github/workflows/verify.yml").read_text("utf-8")
    assert '/ui/live-runner.js' in html
    assert '/api/live/builds/${encodeURIComponent(started.id)}/run' in runner
    assert 'node --check ui/live-runner.js' in workflow


def test_primary_ui_has_real_english_and_hebrew_dictionary():
    js = Path("ui/app.js").read_text("utf-8")
    assert "const I18N" in js
    assert "en:" in js
    assert "he:" in js
    for key in [
        "headline", "subheadline", "promptPlaceholder", "build", "planning",
        "generating", "running", "testing", "repairing", "ready", "failed",
        "preview", "export", "versions", "restore", "signOut", "recentProjects",
    ]:
        assert key in js, key
    assert "document.documentElement.dir" in js
    assert "localStorage.setItem('148ai_locale'" in js or 'localStorage.setItem("148ai_locale"' in js


def test_export_uses_authenticated_fetch_not_location_navigation():
    js = Path("ui/app.js").read_text("utf-8")
    assert "application/zip" not in js or "blob" in js.lower()
    assert "window.location.assign('/api/live" not in js
    assert "URL.createObjectURL" in js

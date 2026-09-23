import io
import zipfile

import pytest

from live_core.executor import (
    UnsafeArtifact,
    execute_web_artifact,
    repair_web_artifact,
    validate_zip,
)


def zip_bytes(files: dict[str, str | bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    return out.getvalue()


def test_rejects_path_traversal():
    blob = zip_bytes({"../escape.txt": "no"})
    with pytest.raises(UnsafeArtifact):
        validate_zip(blob, 5 * 1024 * 1024)


def test_requires_web_entrypoint():
    blob = zip_bytes({"README.txt": "no app"})
    with pytest.raises(UnsafeArtifact, match="index.html"):
        validate_zip(blob, 5 * 1024 * 1024)


def test_repairs_single_html_entrypoint():
    blob = zip_bytes({"site/app.html": "<h1>Recovered</h1>"})
    repaired = repair_web_artifact(blob, 5 * 1024 * 1024)
    assert repaired is not None
    manifest = validate_zip(repaired, 5 * 1024 * 1024)
    assert manifest.entrypoint == "index.html"
    with zipfile.ZipFile(io.BytesIO(repaired)) as z:
        assert z.read("index.html") == b"<h1>Recovered</h1>"


def test_executes_valid_static_bundle():
    blob = zip_bytes({
        "index.html": "<!doctype html><html><body><script src='app.js'></script></body></html>",
        "app.js": "const answer = 42; console.log(answer);",
    })
    result = execute_web_artifact(blob, timeout_seconds=10)
    assert result.ok is True, result.error
    assert result.entrypoint == "index.html"


def test_missing_referenced_local_asset_never_reaches_ready():
    blob = zip_bytes({
        "index.html": "<!doctype html><html><head><link rel='stylesheet' href='missing.css'></head><body><script src='missing.js'></script></body></html>",
    })
    result = execute_web_artifact(blob, timeout_seconds=10)
    assert result.ok is False
    assert "missing" in (result.error or "").lower()


def test_invalid_javascript_never_passes_execution():
    blob = zip_bytes({
        "index.html": "<!doctype html><html><body><script src='app.js'></script></body></html>",
        "app.js": "const = ;",
    })
    result = execute_web_artifact(blob, timeout_seconds=10)
    assert result.ok is False
    assert "JavaScript" in (result.error or "") or "syntax" in (result.error or "").lower()

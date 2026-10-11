"""Font previews have narrowly scoped CSP access, without widening scripts."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from omni_prod.web_security import configure_web_security


def test_font_hosts_are_allowed_without_allowing_external_scripts():
    app=FastAPI()
    configure_web_security(app,raw_origins='http://localhost:8000',production=False)
    @app.get('/')
    def root():
        return {}
    with TestClient(app) as client:
        policy=client.get('/').headers['Content-Security-Policy']
    assert "style-src 'self' https://fonts.googleapis.com" in policy
    assert "font-src 'self' https://fonts.gstatic.com" in policy
    assert "default-src 'self'" in policy
    assert 'unsafe-inline' not in policy
    assert 'unsafe-eval' not in policy

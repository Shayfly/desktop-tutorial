"""Gate regression on products that were already approved (Michael 2026-11-10 condition 4).

#288 changed the truth gate. Before the frozen run, the CURRENT gates are run on the builds that already passed (the
first production build and the cafe): both must still pass, otherwise the baseline moved and the frozen run would
not know what it measures.

For each build: the final repository (the version zip) and the APPROVED prompt (the build contract) are given; the
product is started exactly as the preview smoke starts it -- same script, same contract, loopback only -- and the
markup gates judge the page it serves, with the fact canon built from the approved prompt. Only gates run here; no
model is called and nothing is written anywhere.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def served_page(repository: dict[str, str], *, timeout: int = 60) -> tuple[dict | None, str]:
    """Start the product as the preview smoke does and return (rendered pages, smoke verdict line)."""
    from .preview_smoke import _SMOKE, _rendered_pages
    from .sandbox_script import staged_script
    staged, argv = staged_script(repository, 'preview_smoke', _SMOKE)
    with tempfile.TemporaryDirectory(prefix='gate-regression-') as root:
        for path, text in staged.items():
            target = Path(root) / path
            if not target.resolve().is_relative_to(Path(root).resolve()):
                raise ValueError(f'path escapes the repository: {path}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1'}
        cmd = [sys.executable if argv[0] == 'python' else argv[0], *argv[1:]]
        proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, timeout=timeout)
    out = proc.stdout or ''
    verdict = next((ln for ln in out.splitlines() if ln.startswith('PREVIEW-SMOKE')), 'PREVIEW-SMOKE (no verdict)')
    return _rendered_pages(out), verdict


def run(repository: dict[str, str], prompt: str, *, pages: dict | None = None) -> dict:
    """Current static gates on an approved build. `pages` may be given (tests); otherwise the product is started."""
    from .fact_canon import build_canon
    from .skills_runtime import static_findings
    verdict = 'given'
    if pages is None:
        pages, verdict = served_page(repository)
    ctx = {'request': prompt, 'canon': build_canon(prompt)}
    if pages:
        ctx['rendered_pages'] = pages
    findings = [f.to_dict() for f in static_findings(repository, ctx)]
    blocking = [f for f in findings if f['severity'] == 'blocking']
    return {'passed': bool(pages) and not blocking, 'served': bool(pages), 'smoke': verdict,
            'canon_hash': ctx['canon'].hash, 'canon_facts': [f.to_dict() for f in ctx['canon'].facts],
            'blocking': blocking, 'advisory': [f for f in findings if f['severity'] != 'blocking']}

from __future__ import annotations
import hmac
import json
import os
from pathlib import Path
import tempfile
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from .sandbox_request_policy import (MAX_BODY_BYTES, SandboxRequestRejected, validate_snapshot, validate_command)
from .repair_contracts import sanitized_tail
from .remote_sandbox import sign_body
from .sandbox import SandboxLimits, run_sandbox

app=FastAPI(title='Omni Isolated Sandbox Runner',version='1.0')

class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    repository: dict[str,str]
    argv: list[str]=Field(min_length=1,max_length=64)
    build_id: str=Field(min_length=1,max_length=120)
    # 'browser': the same isolation (no network, read-only source, caps
    # dropped) in the image that also has headless Chromium + Playwright.
    profile: str=Field(default='default',pattern='^(default|browser)$')

PROFILES={
    'default': SandboxLimits(),
    'browser': SandboxLimits(image='omni-browser-sandbox:latest',timeout_seconds=150,memory='1536m',pids=1024,nofile=4096),
}

def _runner_ready() -> tuple[bool, str]:
    """Health reflects whether a run can work at all: the Docker client on
    run_sandbox's PATH and the host daemon socket. A runner without them used to
    report healthy and fail every build with HTTP 500."""
    import shutil
    if shutil.which('docker', path='/usr/bin:/bin') is None:
        return False, 'docker client not installed'
    host = os.getenv('DOCKER_HOST', '')
    if not host and not Path('/var/run/docker.sock').exists():
        return False, 'docker daemon socket not mounted'
    return True, 'ready'

@app.get('/health')
def health():
    ready, reason = _runner_ready()
    if not ready:
        raise HTTPException(503, reason)
    return {'ok':True,'runner':'docker-isolated'}

@app.post('/run')
async def run(req: Request):
    secret=os.getenv('OMNI_SANDBOX_SHARED_SECRET','')
    if len(secret)<32: raise HTTPException(503,'sandbox shared secret not configured')
    chunks = []
    size = 0
    async for chunk in req.stream():
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise HTTPException(413, 'sandbox request exceeds byte ceiling')
        chunks.append(chunk)
    body = b''.join(chunks)
    supplied=req.headers.get('x-omni-signature','')
    if not hmac.compare_digest(supplied,sign_body(secret,body)): raise HTTPException(401,'invalid signature')
    try: payload=RunRequest.model_validate_json(body)
    except Exception as exc: raise HTTPException(400,'invalid request') from exc
    try:
        validate_snapshot(payload.repository)
        validate_command(payload.argv, build_id=payload.build_id,
                         profile=payload.profile, repository=payload.repository,
                         strict=os.getenv('OMNI_SANDBOX_STRICT_REQUEST_V1') == '1')
    except SandboxRequestRejected as exc:
        raise HTTPException(400, 'unsafe sandbox request') from exc
    with tempfile.TemporaryDirectory(prefix='omni-remote-src-') as td, tempfile.TemporaryDirectory(prefix='omni-remote-out-') as out:
        root=Path(td)
        for rel,content in payload.repository.items():
            p=Path(rel)
            if p.is_absolute() or '..' in p.parts: raise HTTPException(400,'unsafe repository path')
            dest=root/p; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(content,encoding='utf-8')
        # The sandbox container runs as an unprivileged uid (SandboxLimits.user),
        # but TemporaryDirectory creates 0700 directories owned by this process,
        # so the sandbox could not even open /workspace/probe.py ("python exited
        # 2" in the first deploy sandbox probe, 2026-10-07). Same fix as
        # SandboxRepositoryExecutor (M4.9): readable source, writable output.
        os.chmod(root,0o755); os.chmod(out,0o777)
        r=run_sandbox(source_dir=root,build_id=payload.build_id,limits=PROFILES[payload.profile],command=payload.argv,output_dir=out)
        return {'returncode':r.returncode,
                'stdout':sanitized_tail(r.stdout or '',limit=100000),
                'stderr':sanitized_tail(r.stderr or '',limit=100000)}

from __future__ import annotations
from dataclasses import dataclass
import hashlib
import hmac
import json
from urllib import request, error
from .autonomous_core import ExecutionReport, AcceptanceFailure
from .product_spec import ProductSpec
from .project_manifest import ProjectManifest, invalid_manifest_report

class RemoteSandboxError(RuntimeError): pass

@dataclass(frozen=True)
class RemoteSandboxConfig:
    base_url: str
    shared_secret: str
    timeout_seconds: float=240
    def __post_init__(self):
        if not self.base_url.startswith(('http://','https://')): raise ValueError('sandbox URL must be http(s)')
        if len(self.shared_secret)<32: raise ValueError('sandbox shared secret must be at least 32 chars')


def sign_body(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()

class RemoteSandboxRepositoryExecutor:
    def __init__(self, config: RemoteSandboxConfig, *, urlopen=None):
        self.config=config; self._urlopen=urlopen or request.urlopen
    def _run(self, repository: dict[str,str], argv: tuple[str,...], build_id: str) -> dict:
        body=json.dumps({'repository':repository,'argv':list(argv),'build_id':build_id},separators=(',',':')).encode()
        req=request.Request(self.config.base_url.rstrip('/')+'/run',data=body,method='POST',headers={'content-type':'application/json','x-omni-signature':sign_body(self.config.shared_secret,body)})
        try:
            with self._urlopen(req,timeout=self.config.timeout_seconds) as resp: data=json.loads(resp.read().decode())
        except (error.URLError,TimeoutError,json.JSONDecodeError) as exc: raise RemoteSandboxError(str(exc)) from exc
        if not all(k in data for k in ('returncode','stdout','stderr')): raise RemoteSandboxError('invalid sandbox response')
        return data
    def execute(self, *, repository: dict[str,str], spec: ProductSpec) -> ExecutionReport:
        valid={a.id for a in spec.acceptance}; failures=[]; logs=[]; n=0
        try:
            manifest=ProjectManifest.from_repository(repository)
            unknown=sorted({x for c in manifest.verify for x in c.acceptance_ids} - valid)
            if unknown: raise ValueError('verification references unknown acceptance id: '+', '.join(unknown[:10]))
        except ValueError as exc:
            return invalid_manifest_report(exc, spec)
        for command in manifest.build:
            n+=1; r=self._run(repository,command,f'b{n}'); logs += [r['stdout'],r['stderr']]
            if int(r['returncode'])!=0:
                return ExecutionReport(False,tuple(AcceptanceFailure(a.id,'remote build failed',r['stderr'][-2000:]) for a in spec.acceptance),'\n'.join(logs)[-10000:])
        for check in manifest.verify:
            n+=1; r=self._run(repository,check.argv,f't{n}'); logs += [r['stdout'],r['stderr']]
            if int(r['returncode'])!=0:
                failures.extend(AcceptanceFailure(aid,f'remote verification failed: {check.name}',r['stderr'][-2000:]) for aid in check.acceptance_ids)
        return ExecutionReport(not failures,tuple(failures),'\n'.join(logs)[-10000:])

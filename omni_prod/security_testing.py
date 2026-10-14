from __future__ import annotations
from dataclasses import dataclass, asdict
import json
import re
from .project_manifest import ProjectManifest

@dataclass(frozen=True)
class SecurityFinding:
    code: str
    severity: str
    detail: str

@dataclass(frozen=True)
class SecurityReport:
    passed: bool
    findings: tuple[SecurityFinding,...]
    def to_dict(self): return {'passed':self.passed,'findings':[asdict(x) for x in self.findings]}

_DANGEROUS_ARGS = {'--privileged','--network=host','/var/run/docker.sock'}
_SHELLS = {'sh','bash','zsh','cmd','powershell','pwsh'}

def hostile_repository_scan(repository: dict[str,str]) -> SecurityReport:
    findings=[]
    for p,c in repository.items():
        if p.startswith('/') or '..' in p.split('/'):
            findings.append(SecurityFinding('PATH_ESCAPE','blocker',p))
        if re.search(r'(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----', c):
            findings.append(SecurityFinding('PRIVATE_KEY','blocker',p))
        if re.search(r'(?i)(aws_secret_access_key|stripe_secret_key)\s*[:=]', c):
            findings.append(SecurityFinding('SECRET_LITERAL','high',p))
    try:
        manifest=ProjectManifest.from_repository(repository)
        commands=[*manifest.build,*[x.argv for x in manifest.verify]]
        for cmd in commands:
            if cmd and cmd[0].lower() in _SHELLS:
                findings.append(SecurityFinding('SHELL_COMMAND','high',' '.join(cmd[:3])))
            if any(arg in _DANGEROUS_ARGS for arg in cmd):
                findings.append(SecurityFinding('PRIVILEGE_ESCAPE','blocker',' '.join(cmd)))
    except Exception as exc:
        findings.append(SecurityFinding('INVALID_MANIFEST','high',str(exc)))
    return SecurityReport(not any(x.severity in {'blocker','high'} for x in findings), tuple(findings))

from __future__ import annotations
from dataclasses import dataclass, asdict
import json

@dataclass(frozen=True)
class ReviewFinding:
    role: str
    severity: str
    title: str
    detail: str
    paths: tuple[str,...]=()

class SpecialistReviewAgent:
    def __init__(self, gateway, *, role: str):
        self.gateway=gateway; self.role=role
    def review(self, *, spec: dict, repository_summary: dict) -> tuple[ReviewFinding,...]:
        system=(f'You are Omni {self.role} reviewer. Return only JSON with findings array. '
                'Each finding has severity(blocker|high|medium|low), title, detail, paths. '
                'Review against the approved product spec. Do not invent requirements.')
        data=self.gateway.complete_json(system=system,user=json.dumps({'spec':spec,'repository':repository_summary},ensure_ascii=False),max_tokens=5000)
        out=[]
        for item in data.get('findings',[]):
            sev=str(item.get('severity','')).lower()
            if sev not in {'blocker','high','medium','low'}: continue
            out.append(ReviewFinding(self.role,sev,str(item.get('title',''))[:200],str(item.get('detail',''))[:2000],tuple(str(x) for x in item.get('paths',[])[:20])))
        return tuple(out)

class MultiAgentReviewTeam:
    def __init__(self, gateway, roles=('qa','security','ux','architecture')):
        self.agents=tuple(SpecialistReviewAgent(gateway,role=r) for r in roles)
    def review(self, *, spec: dict, repository_summary: dict) -> tuple[ReviewFinding,...]:
        findings=[]
        for agent in self.agents: findings.extend(agent.review(spec=spec,repository_summary=repository_summary))
        return tuple(findings)

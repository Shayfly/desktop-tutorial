#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, sys, time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.benchmark_suite import CASES
from omni_prod.unified_engine import UnifiedOmniEngine
from omni_prod.demo_project import demo_spec
from omni_prod.quality_gate import assess_repository
from omni_prod.security_testing import hostile_repository_scan

engine=UnifiedOmniEngine(token_secret='benchmark-'+'x'*48)
rows=[]
started=time.monotonic()
for idx,case in enumerate(CASES,1):
    t=time.monotonic()
    try:
        r=engine.build(project_id=f'bench-{case.id}',prompt=case.prompt)
        repo=engine.repository(project_id=f'bench-{case.id}',version_id=r.version_id)
        q=assess_repository(spec=demo_spec(case.prompt),repository=repo,minimum_score=75)
        s=hostile_repository_scan(repo)
        ok=r.status=='READY' and r.launch_ready and q.passed and s.passed
        rows.append({'id':case.id,'category':case.category,'difficulty':case.difficulty,'ok':ok,'status':r.status,'files':r.file_count,'quality':q.score,'security':s.passed,'duration_ms':int((time.monotonic()-t)*1000)})
    except Exception as exc:
        rows.append({'id':case.id,'category':case.category,'difficulty':case.difficulty,'ok':False,'error':str(exc)[:500],'duration_ms':int((time.monotonic()-t)*1000)})
passed=sum(1 for x in rows if x['ok'])
durations=sorted(x['duration_ms'] for x in rows)
p95=durations[min(len(durations)-1,int((len(durations)-1)*.95))] if durations else 0
by={}
for x in rows:
    d=by.setdefault(x['category'],{'total':0,'passed':0}); d['total']+=1; d['passed']+=int(x['ok'])
payload={'engine':'V25 Unified Core deterministic/offline baseline','cases':len(rows),'passed':passed,'failed':len(rows)-passed,'success_rate':round(passed/len(rows),4) if rows else 0,'p95_duration_ms':p95,'wall_ms':int((time.monotonic()-started)*1000),'by_category':by,'results':rows,'truth_note':'This benchmark exercises deterministic V25 planning/repository/runtime contracts without a live GPU model or Docker execution.'}
(ROOT/'BENCHMARK_V25_OFFLINE.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in payload.items() if k!='results'},ensure_ascii=False,indent=2))
raise SystemExit(0 if passed==len(rows) else 1)

#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.benchmark_suite import CASES
from omni_prod.v28_platform import V28Platform
from omni_prod.demo_project import demo_spec
from omni_prod.quality_gate import assess_repository
from omni_prod.security_testing import hostile_repository_scan

p=V28Platform(token_secret='bench-'+'b'*48,generated_app_token_secret='runtime-'+'r'*48)
pw='Benchmark'+'Pass123!'; r=p.register(email='benchmark@148ai.local',password=pw); token=r['token']; p.assign_plan_admin(user_id=r['user']['id'],plan='business')
rows=[]; started=time.monotonic()
for case in CASES:
    t=time.monotonic(); project=p.create_project(token=token,title='Benchmark '+case.id)
    try:
        b=p.build(token=token,project_id=project['id'],prompt=case.prompt,target_markets=('US','EU'))
        repo=p.repository(token=token,project_id=project['id'])
        q=assess_repository(spec=demo_spec(case.prompt),repository=repo,minimum_score=75)
        sec=hostile_repository_scan(repo)
        ok=b['status']=='READY' and q.passed and sec.passed and '.148ai/provenance.json' in repo and '.148ai/brand-manifest.json' in repo
        rows.append({'id':case.id,'category':case.category,'ok':ok,'status':b['status'],'files':len(repo),'quality':q.score,'security':sec.passed,'rights':b['rights']['status'],'ms':int((time.monotonic()-t)*1000)})
    except Exception as exc:
        rows.append({'id':case.id,'category':case.category,'ok':False,'error':str(exc)[:500],'ms':int((time.monotonic()-t)*1000)})
passed=sum(1 for x in rows if x['ok']); durations=sorted(x['ms'] for x in rows); p95=durations[min(len(durations)-1,int((len(durations)-1)*.95))]
payload={'engine':'148AI V28 deterministic/offline commercial-shell benchmark','cases':len(rows),'passed':passed,'failed':len(rows)-passed,'success_rate':round(passed/len(rows),4),'p95_ms':p95,'wall_ms':int((time.monotonic()-started)*1000),'results':rows,'truth_note':'This verifies deterministic V28 build/rights/branding/quality/security contracts. It does not claim a live GPU model, live media provider or live Docker sandbox.'}
(ROOT/'BENCHMARK_V28_OFFLINE.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in payload.items() if k!='results'},ensure_ascii=False,indent=2)); raise SystemExit(0 if passed==len(rows) else 1)

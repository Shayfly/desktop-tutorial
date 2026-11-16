#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.benchmark_suite import CASES
from omni_prod.demo_project import demo_spec,create_demo_repository
from omni_prod.quality_gate import assess_repository
from omni_prod.security_testing import hostile_repository_scan
from omni_prod.native_source import android_project,ios_project,game_project
from omni_prod.secret_scan import scan_tree

checks={}
def check(name,ok,detail=''): checks[name]={'ok':bool(ok),'detail':detail}; return bool(ok)
def run(name,argv):
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    checks[name]={'ok':p.returncode==0,'returncode':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:]}
    return p.returncode==0
ok=True
ok &= run('compileall',[sys.executable,'-m','compileall','-q','omni_prod','tests'])
# 2026-11-16: in the v24-ci test job the suite has already run (pytest-report.xml); running it a second time here
# took 7.7 minutes and pushed the job past its 20-minute bound. With OMNI_PYTEST_REPORT the gate reads that report;
# without it (a local run) it runs pytest as before.
import os
from scripts.junit_report import verdict
_report=os.environ.get('OMNI_PYTEST_REPORT')
if _report:
    _ok,_detail=verdict(ROOT/_report)
    ok &= check('pytest',_ok,_detail)
else:
    ok &= run('pytest',[sys.executable,'-m','pytest','-q'])
ok &= check('benchmark_catalog',len(CASES)>=200,f'{len(CASES)} cases')
spec=demo_spec('Build an international multilingual CRM with teams and mobile workflow'); repo=create_demo_repository('Build an international multilingual CRM with teams and mobile workflow',spec)
q=assess_repository(spec=spec,repository=repo,minimum_score=75); sec=hostile_repository_scan(repo)
ok &= check('quality_gate',q.passed,json.dumps(q.to_dict()))
ok &= check('security_gate',sec.passed,json.dumps(sec.to_dict()))
ok &= check('native_android',len(android_project())>=6)
ok &= check('native_ios',len(ios_project())>=3)
ok &= check('games',all(len(game_project(e))>=2 for e in ('godot','unity','unreal')))
findings=scan_tree(ROOT)
secret_detail=json.dumps({
    'count': len(findings),
    'locations': [{'kind': f.kind, 'path': f.path, 'line': f.line} for f in findings],
}, separators=(',', ':'))
ok &= check('secret_scan',not findings,secret_detail)
payload={'ok':bool(ok),'checks':checks,'live_claims':{'gpu_model_verified':False,'docker_sandbox_verified':False,'postgres_redis_s3_verified':False,'signed_mobile_binaries_verified':False}}
print(json.dumps(payload,indent=2))
raise SystemExit(0 if ok else 1)

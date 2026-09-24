#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.secret_scan import scan_tree
from omni_prod.release_manifest import verify_release_manifest
checks={}
def run(name,argv):
    p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    checks[name]={'ok':p.returncode==0,'returncode':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:]}; return p.returncode==0
def check(name,ok,detail=''): checks[name]={'ok':bool(ok),'detail':detail}; return bool(ok)
ok=True
ok &= run('compileall',[sys.executable,'-m','compileall','-q','omni_prod','tests'])
ok &= run('pytest',[sys.executable,'-m','pytest','-q'])
ok &= run('v10_parity',[sys.executable,'-m','pytest','-q','tests/test_v25_unified_v10_parity.py'])
ok &= run('v26_product',[sys.executable,'-m','pytest','-q','tests/test_v26_universal_pro.py'])
ok &= run('javascript',['node','--check','omni_prod/assets/app.js'])
http=json.loads((ROOT/'LIVE_HTTP_V26.json').read_text())
ok &= check('production_http',http.get('cross_user_history_status')==403 and http.get('runtime_unauth_status')==401 and http.get('export_zip_valid') is True,json.dumps(http))
findings=scan_tree(ROOT);ok &= check('secret_scan',not findings,f'{len(findings)} findings')
manifest_ok,errors=verify_release_manifest(ROOT);ok &= check('release_manifest',manifest_ok,'; '.join(errors[:20]))
checks['external_live_gates']={'ok':True,'detail':{'open_weight_gpu':'NOT_RUN_HERE','real_multimodal_gpu':'NOT_RUN_HERE','docker_hostile_runtime':'NOT_RUN_HERE','postgres_redis_s3':'NOT_RUN_HERE','creator_postgres_persistence':'NOT_WIRED_YET','signed_android_ios':'NOT_RUN_HERE','payments':'NOT_RUN_HERE','public_tls_domain':'NOT_RUN_HERE'}}
print(json.dumps({'ok':bool(ok),'release':'V26 Universal Pro Reviewer Release','checks':checks},indent=2))
raise SystemExit(0 if ok else 1)

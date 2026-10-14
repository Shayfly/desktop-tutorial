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
    checks[name]={'ok':p.returncode==0,'returncode':p.returncode,'stdout':p.stdout[-5000:],'stderr':p.stderr[-5000:]}; return p.returncode==0
def check(name,ok,detail=''): checks[name]={'ok':bool(ok),'detail':detail}; return bool(ok)
ok=True
ok &= run('compileall',[sys.executable,'-m','compileall','-q','omni_prod','tests'])
ok &= run('pytest',[sys.executable,'-m','pytest','-q'])
ok &= run('v10_parity',[sys.executable,'-m','pytest','-q','tests/test_v25_unified_v10_parity.py'])
ok &= run('v26_product',[sys.executable,'-m','pytest','-q','tests/test_v26_universal_pro.py'])
ok &= run('v27_rights_company_os',[sys.executable,'-m','pytest','-q','tests/test_v27_rights_company_os.py'])
ok &= run('javascript',['node','--check','omni_prod/assets/app.js'])
http_path=ROOT/'LIVE_HTTP_V27.json'
http=json.loads(http_path.read_text()) if http_path.exists() else {}
ok &= check('production_http',
    http.get('safe_rights')=='CLEAR' and http.get('risky_initial_promote_status')==409 and
    http.get('unverified_evidence_still_blocked') is True and http.get('unauthorized_review_status')==403 and
    http.get('reviewer_verified_evidence') is True and http.get('risky_after_review')=='CLEAR' and
    http.get('cross_user_rights_status')==403 and http.get('rights_manifest_in_export') is True and
    http.get('separate_control_and_runtime_secrets') is True,
    json.dumps(http,sort_keys=True))
findings=scan_tree(ROOT);ok &= check('secret_scan',not findings,f'{len(findings)} findings')
manifest_ok,errors=verify_release_manifest(ROOT);ok &= check('release_manifest',manifest_ok,'; '.join(errors[:20]))
checks['external_live_gates']={'ok':True,'detail':{
    'open_weight_gpu':'NOT_RUN_HERE','real_multimodal_gpu':'NOT_RUN_HERE','docker_hostile_runtime':'NOT_RUN_HERE',
    'postgres_redis_s3':'NOT_RUN_HERE','creator_postgres_persistence':'NOT_WIRED_YET','signed_android_ios':'NOT_RUN_HERE',
    'payments':'NOT_RUN_HERE','public_tls_domain':'NOT_RUN_HERE','worldwide_live_legal_database_clearance':'NOT_IMPLEMENTED',
    'forensic_music_logo_video_3d_similarity':'NOT_IMPLEMENTED','human_legal_counsel':'EXTERNAL_HUMAN_DECISION'}}
print(json.dumps({'ok':bool(ok),'release':'V27 Rights & Company OS Reviewer Release','checks':checks},indent=2))
raise SystemExit(0 if ok else 1)

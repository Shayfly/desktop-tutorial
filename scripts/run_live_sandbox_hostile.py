#!/usr/bin/env python3
from pathlib import Path
import json,os,sys,tempfile
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.sandbox import SandboxLimits,run_sandbox
if os.getenv('OMNI_RUN_LIVE_SANDBOX')!='1': raise SystemExit('Set OMNI_RUN_LIVE_SANDBOX=1 only on an isolated Docker-capable test host.')
checks=[]
with tempfile.TemporaryDirectory() as td:
    p=Path(td); (p/'x.py').write_text('print("ok")')
    net=run_sandbox(source_dir=p,build_id='hostile-net',limits=SandboxLimits(timeout_seconds=10),command=['python','-c',"import socket; socket.create_connection(('1.1.1.1',53),2)"])
    checks.append({'name':'network_blocked','passed':net.returncode!=0,'stderr':net.stderr[-500:]})
    ro=run_sandbox(source_dir=p,build_id='hostile-rootfs',limits=SandboxLimits(timeout_seconds=10),command=['python','-c',"open('/etc/omni-owned','w').write('x')"])
    checks.append({'name':'rootfs_readonly','passed':ro.returncode!=0,'stderr':ro.stderr[-500:]})
    src=run_sandbox(source_dir=p,build_id='hostile-source',limits=SandboxLimits(timeout_seconds=10),command=['python','-c',"open('/workspace/x.py','w').write('bad')"])
    checks.append({'name':'source_readonly','passed':src.returncode!=0,'stderr':src.stderr[-500:]})
ok=all(x['passed'] for x in checks); print(json.dumps({'ok':ok,'checks':checks},indent=2)); raise SystemExit(0 if ok else 2)

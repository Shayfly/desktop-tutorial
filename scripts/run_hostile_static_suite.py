#!/usr/bin/env python3
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from omni_prod.demo_project import demo_spec,create_demo_repository
from omni_prod.security_testing import hostile_repository_scan
spec=demo_spec('Build CRM')
base=create_demo_repository('Build CRM',spec)
cases=[]
def run(name,mutate):
    repo=dict(base); mutate(repo); report=hostile_repository_scan(repo); cases.append({'name':name,'blocked':not report.passed,'findings':[x.__dict__ for x in report.findings]})
run('path_traversal',lambda r:r.__setitem__('../escape.txt','x'))
run('private_key',lambda r:r.__setitem__('secret.pem','-----BEGIN PRIVATE'+' KEY-----\nFAKE\n-----END PRIVATE'+' KEY-----'))
def shell(r):
    m=json.loads(r['.omni/project.json']); m['verify'][0]['argv']=['bash','-lc','id']; r['.omni/project.json']=json.dumps(m)
run('shell_command',shell)
def privileged(r):
    m=json.loads(r['.omni/project.json']); m['verify'][0]['argv']=['python','--privileged']; r['.omni/project.json']=json.dumps(m)
run('privileged_arg',privileged)
ok=all(x['blocked'] for x in cases); print(json.dumps({'ok':ok,'cases':cases},indent=2)); raise SystemExit(0 if ok else 2)

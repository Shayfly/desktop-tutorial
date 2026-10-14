from __future__ import annotations
from pathlib import Path
import json
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from omni_prod.secret_scan import scan_tree
from omni_prod.release_manifest import verify_release_manifest

checks = {}

def run(name, argv):
    p = subprocess.run(argv, cwd=root, text=True, capture_output=True)
    checks[name] = {'ok': p.returncode == 0, 'returncode': p.returncode, 'stdout': p.stdout[-3000:], 'stderr': p.stderr[-3000:]}
    return p.returncode == 0

ok = True
ok &= run('compileall', [sys.executable, '-m', 'compileall', '-q', 'omni_prod', 'tests'])
ok &= run('pytest', [sys.executable, '-m', 'pytest', '-q'])
findings = scan_tree(root)
checks['secret_scan'] = {'ok': not findings, 'findings': [f.__dict__ for f in findings]}
ok &= not findings
manifest_ok, errors = verify_release_manifest(root)
checks['release_manifest'] = {'ok': manifest_ok, 'errors': errors}
ok &= manifest_ok
payload = {'ok': bool(ok), 'checks': checks}
print(json.dumps(payload, indent=2))
raise SystemExit(0 if ok else 1)

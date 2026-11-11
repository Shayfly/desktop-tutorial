"""Fail when a gate file changes while the gate freeze is active (docs/gate-freeze.json). One annotation per result.

usage: gate_freeze_check.py <file with changed paths, one per line> [freeze json]
"""
import json
import sys

changed = {ln.strip() for ln in open(sys.argv[1], encoding='utf-8') if ln.strip()}
freeze = json.load(open(sys.argv[2] if len(sys.argv) > 2 else 'docs/gate-freeze.json', encoding='utf-8'))
if 'docs/gate-freeze.json' in changed:
    print('::notice title=gate freeze::this PR changes the freeze definition itself (a reviewed decision)')
    sys.exit(0)
touched = sorted(changed & set(freeze['gate_files']))
if freeze.get('active') and touched:
    print(f"::error title=gate freeze::{', '.join(touched)} changed during the {freeze.get('hours')}h gate freeze")
    sys.exit(1)
print(f"::notice title=gate freeze::{'active' if freeze.get('active') else 'inactive'}; gate files touched: {len(touched)}")

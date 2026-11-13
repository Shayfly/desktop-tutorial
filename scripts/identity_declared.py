"""Declared identity changes (Michael 2026-11-13).

While identity.yml blocks (a gate freeze, or a PR touching site_auth_v2), the flag-off pipeline must equal the
anchor. An INTENDED change passes only with one signed entry in docs/identity/allowed-identity-changes.json that
matches it EXACTLY:
  * from_digest / to_digest -- the anchor's and this commit's flag-off digest (python -m omni_prod.pipeline_identity);
  * added / removed / changed / data_changed -- the exact sets of gate-closure paths (no wildcards, no extra, none
    missing; file hashes are not stored because an AST dump differs between interpreters);
  * reason, author, reviewer (not the author, not "claude"/"author"/"pending"), reviewed_at.
Anything else -- an undeclared digest, an unsigned entry, one path more or less -- is refused, loudly.

CLI (identity.yml): identity_declared.py BASE_DIGEST HEAD_DIGEST BASE_MANIFEST HEAD_MANIFEST
prints one ::notice / ::error line and exits 0 only on an exact signed match.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

DECLARATIONS = Path(__file__).resolve().parent.parent / 'docs' / 'identity' / 'allowed-identity-changes.json'
_SETS = ('added', 'removed', 'changed', 'data_changed')
_WILD = set('*?[]{}')
_NOT_A_REVIEWER = {'', 'claude', 'author', 'pending'}


def diff(base: dict, head: dict) -> dict:
    """The exact path sets that differ between two source manifests (pipeline_identity --source)."""
    bf, hf, bd, hd = base['files'], head['files'], base.get('data', {}), head.get('data', {})
    return {'added': sorted(set(hf) - set(bf)), 'removed': sorted(set(bf) - set(hf)),
            'changed': sorted(p for p in set(hf) & set(bf) if hf[p] != bf[p]),
            'data_changed': sorted(sorted(set(hd) ^ set(bd)) + [p for p in set(hd) & set(bd) if hd[p] != bd[p]])}


def problems(entry: dict) -> list[str]:
    """Why an entry is not a valid signed declaration (empty when it is)."""
    out = []
    for key in ('id', 'from_digest', 'to_digest', 'reason', 'author', 'reviewed_at'):
        if not str(entry.get(key) or '').strip():
            out.append(f'{key} is empty')
    reviewer = str(entry.get('reviewer') or '').strip()
    if reviewer.lower() in _NOT_A_REVIEWER or reviewer == entry.get('author'):
        out.append('no reviewer other than the author')
    for key in _SETS:
        value = entry.get(key)
        if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
            out.append(f'{key} must be a list of paths')
        elif any(_WILD & set(p) for p in value):
            out.append(f'{key} has a wildcard')
    return out


def match(entries: list, base_digest: str, head_digest: str, change: dict) -> tuple[dict | None, list[str]]:
    """(the one signed entry that declares exactly this change, why the others did not)."""
    why = []
    for entry in entries:
        name = entry.get('id', '?')
        bad = problems(entry)
        if bad:
            why.append(f'{name}: ' + '; '.join(bad))
            continue
        if (entry['from_digest'], entry['to_digest']) != (base_digest, head_digest):
            why.append(f'{name}: declares {entry["from_digest"][:8]} -> {entry["to_digest"][:8]}, '
                       f'not {base_digest[:8]} -> {head_digest[:8]}')
            continue
        diffs = [f'{k}: declared {sorted(entry[k])} != actual {change[k]}' for k in _SETS
                 if sorted(entry[k]) != change[k]]
        if diffs:
            why.append(f'{name}: ' + '; '.join(diffs))
            continue
        return entry, why
    return None, why or ['no declarations']


def load(path: Path | None = None) -> list:
    return json.loads((path or DECLARATIONS).read_text(encoding='utf-8')).get('changes', [])


def main(argv: list[str]) -> int:
    base_digest, head_digest, base_manifest, head_manifest = argv
    change = diff(json.loads(Path(base_manifest).read_text(encoding='utf-8')),
                  json.loads(Path(head_manifest).read_text(encoding='utf-8')))
    entry, why = match(load(), base_digest, head_digest, change)
    if entry is None:
        print(f'::error title=identity change not declared::{base_digest[:12]} -> {head_digest[:12]} '
              f'{json.dumps(change)} | ' + ' | '.join(why)[:2500])
        return 1
    print(f"::notice title=identity change declared::{entry['id']}: {base_digest[:12]} -> {head_digest[:12]}, "
          f"{json.dumps(change)} (author {entry['author']}, reviewer {entry['reviewer']} {entry['reviewed_at']}): "
          f"{entry['reason'][:1500]}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

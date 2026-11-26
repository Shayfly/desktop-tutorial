"""Declared identity changes (Michael 2026-11-13).

While identity.yml blocks (a gate freeze, or a PR touching site_auth_v2), the flag-off pipeline must equal the
anchor. An INTENDED change passes only with one signed entry in docs/identity/allowed-identity-changes.json that
matches it EXACTLY:
  * from_digest / to_digest -- the anchor's and this commit's flag-off digest (python -m omni_prod.pipeline_identity);
  * added / removed / changed / data_changed -- the exact sets of gate-closure paths (no wildcards, no extra, none
    missing; file hashes are not stored because an AST dump differs between interpreters);
  * reason, author, reviewer (not the author, not "claude"/"author"/"pending"), reviewed_at;
  * to_digest is UNIQUE in the file: a consumed entry is never used twice (a duplicate refuses the whole file).
Anything else -- an undeclared digest, an unsigned entry, one path more or less -- is refused, loudly.

A revert (release review 2026-11-26, docs/ops/worker-rollback.md): deploy-worker deploys only main, so a worker
rollback is a fix-forward PR that restores the code of before a release, i.e. the change B -> A undoing an entry
A -> B. Digest A is already the to_digest of the entry that introduced it, so B -> A could not be declared at all.
An entry with "revert_of": "<id>" may repeat a to_digest only when it is the EXACT revert of that one entry:
  * revert_of names exactly one other entry, and no other entry reverts that entry too;
  * from_digest / to_digest are that entry's to_digest / from_digest (swapped);
  * added / removed are that entry's removed / added, changed / data_changed are equal to its own;
  * signed like any entry (the reviewer rule above is unchanged); an unsigned revert is a repeat like any other.
A reverted entry is consumed: it never matches again (re-landing the reverted change needs its own revert_of entry,
naming the revert). Any other repeat -- without revert_of, revert_of naming no entry, other digests, other paths --
still refuses the whole file.

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


def _paths(value):
    return sorted(value) if isinstance(value, list) else value


def revert_problems(entry: dict, entries: list) -> list[str]:
    """Why an entry with revert_of is not the exact revert of the one entry it names (empty when it is, or when it has
    no revert_of). The swap is checked against the named entry, never against the change at hand."""
    if 'revert_of' not in entry:
        return []
    target_id = str(entry.get('revert_of') or '').strip()
    if not target_id:
        return ['revert_of is empty']
    if target_id == entry.get('id'):
        return ['revert_of names the entry itself']
    targets = [e for e in entries if e.get('id') == target_id]
    if len(targets) != 1:
        return [f'revert_of {target_id}: names {len(targets)} entries, not exactly one']
    target, out = targets[0], []
    if any(e is not entry and e.get('revert_of') == target_id for e in entries):
        out.append(f'revert_of {target_id}: that entry is reverted by more than one entry')
    if (entry.get('from_digest'), entry.get('to_digest')) != (target.get('to_digest'), target.get('from_digest')):
        out.append(f'revert_of {target_id}: declares {str(entry.get("from_digest"))[:8]} -> '
                   f'{str(entry.get("to_digest"))[:8]}, not the swap {str(target.get("to_digest"))[:8]} -> '
                   f'{str(target.get("from_digest"))[:8]}')
    for mine, theirs in (('added', 'removed'), ('removed', 'added'), ('changed', 'changed'),
                         ('data_changed', 'data_changed')):
        if _paths(entry.get(mine)) != _paths(target.get(theirs)):
            out.append(f'revert_of {target_id}: {mine} {_paths(entry.get(mine))} != its {theirs} '
                       f'{_paths(target.get(theirs))}')
    return out


def exact_revert(entry: dict, entries: list) -> bool:
    """A signed entry with revert_of that is the exact revert of the one entry it names."""
    return 'revert_of' in entry and not problems(entry) and not revert_problems(entry, entries)


def reverted_by(entries: list) -> dict[str, str]:
    """id of each consumed entry -> id of the exact revert that consumed it (only exact reverts consume)."""
    return {str(e.get('revert_of') or '').strip(): e.get('id', '?') for e in entries if exact_revert(e, entries)}


def duplicates(entries: list) -> list[str]:
    """to_digest values that appear more than once. Michael 2026-11-13: declarations accumulate in main forever; each
    new digest is declared ONCE, so an entry that was consumed can never match a later change by accident. The one
    exception is an exact, signed revert (exact_revert()): it restores an earlier digest, so it may repeat it."""
    seen, dup = set(), []
    for entry in entries:
        if exact_revert(entry, entries):
            continue
        to = str(entry.get('to_digest') or '')
        if to in seen and to not in dup:
            dup.append(to)
        seen.add(to)
    return dup


def match(entries: list, base_digest: str, head_digest: str, change: dict) -> tuple[dict | None, list[str]]:
    """(the one signed entry that declares exactly this change, why the others did not)."""
    dup = duplicates(entries)
    if dup:   # a file with a reused to_digest is refused whole: which entry was meant is not decidable
        return None, ['to_digest declared more than once: ' + ', '.join(d[:12] for d in dup)]
    why, consumed = [], reverted_by(entries)
    for entry in entries:
        name = entry.get('id', '?')
        bad = problems(entry) + revert_problems(entry, entries)
        if bad:
            why.append(f'{name}: ' + '; '.join(bad))
            continue
        if name in consumed:
            why.append(f'{name}: reverted by {consumed[name]}, consumed (never matches again)')
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
    revert = f" (revert of {entry['revert_of']})" if 'revert_of' in entry else ''
    print(f"::notice title=identity change declared::{entry['id']}{revert}: {base_digest[:12]} -> {head_digest[:12]}, "
          f"{json.dumps(change)} (author {entry['author']}, reviewer {entry['reviewer']} {entry['reviewed_at']}): "
          f"{entry['reason'][:1500]}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

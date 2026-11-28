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
  * revert_of is the id exactly (no surrounding white space) of one entry that stands EARLIER in the file, and no
    other entry reverts that entry too;
  * that entry is itself valid: signed, and, when it is a revert too, the exact revert of its own target;
  * from_digest / to_digest are that entry's to_digest / from_digest (swapped);
  * added / removed are that entry's removed / added, changed / data_changed are equal to its own;
  * signed like any entry (the reviewer rule above is unchanged); an unsigned revert is a repeat like any other.
A reverted entry is consumed: it never matches again (re-landing the reverted change needs its own revert_of entry,
naming the revert); only an exact revert consumes. File order is the order of declaration here: a revert is appended
at the END of "changes", and the to_digest rule reads the file from the top -- a plain entry whose to_digest an entry
above it (a revert included) already declared is a repeat. Any other repeat -- without revert_of, revert_of naming no
entry or a later one, other digests, other paths -- still refuses the whole file.

Source only (the owner, 2026-11-28, #570, option 1): a change to the gate code that leaves the flag-off behavioural
digest EQUAL (the code moved or gained flag-only branches; the flag-off pipeline is the same) has no new digest to
declare, and to_digest is unique, so it could not be declared at all. An entry with "kind": "source_only" declares it:
  * from_digest == to_digest: the one digest of before and after (the anchor's);
  * added / removed / changed / data_changed are the exact path sets, as for any entry; at least one is not empty;
  * it never carries revert_of, and it is exempt from the to_digest rule (its digest is an old one by definition);
  * instead, (digest, the four path sets) is unique among source_only entries: the same change is declared once;
  * it matches only a change whose base and head digests are both that digest -- never a change of behaviour.
"kind" has one known value; any other value refuses the entry.

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
SOURCE_ONLY = 'source_only'


def source_only(entry: dict) -> bool:
    return entry.get('kind') == SOURCE_ONLY


def _key(entry: dict) -> tuple:
    return (str(entry.get('to_digest') or ''),) + tuple(tuple(_paths(entry.get(k)) or ()) for k in _SETS)


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
    if 'kind' in entry and entry.get('kind') != SOURCE_ONLY:
        out.append(f'kind {entry.get("kind")!r} is not known (the one kind is {SOURCE_ONLY!r})')
    if source_only(entry):
        if entry.get('from_digest') != entry.get('to_digest'):
            out.append('a source_only entry declares one digest: from_digest must equal to_digest')
        if 'revert_of' in entry:
            out.append('a source_only entry is never a revert')
        if not any(isinstance(entry.get(k), list) and entry.get(k) for k in _SETS):
            out.append('a source_only entry names at least one path')
    return out


def _paths(value):
    return sorted(value) if isinstance(value, list) else value


def revert_problems(entry: dict, entries: list) -> list[str]:
    """Why an entry with revert_of is not the exact revert of the one entry it names (empty when it is, or when it has
    no revert_of). The swap is checked against the named entry, never against the change at hand."""
    if 'revert_of' not in entry:
        return []
    raw = entry.get('revert_of')
    if not isinstance(raw, str) or raw != raw.strip():
        return [f'revert_of {raw!r} is not an id exactly (a string without surrounding white space)']
    target_id = raw
    if not target_id:
        return ['revert_of is empty']
    targets = [i for i, e in enumerate(entries) if e.get('id') == target_id]
    if len(targets) != 1:
        return [f'revert_of {target_id}: names {len(targets)} entries, not exactly one']
    here = [i for i, e in enumerate(entries) if e is entry]
    if len(here) != 1 or targets[0] >= here[0]:   # also an entry naming itself; the chain below only goes up the file
        return [f'revert_of {target_id}: that entry is not earlier in the file than this revert']
    target, out = entries[targets[0]], []
    if problems(target):
        out.append(f'revert_of {target_id}: the reverted entry is not a valid signed entry ({"; ".join(problems(target))})')
    if 'revert_of' in target and revert_problems(target, entries):
        out.append(f'revert_of {target_id}: the reverted entry is a revert but not the exact revert of its own target')
    if any(e is not entry and str(e.get('revert_of') or '').strip() == target_id for e in entries):
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
    exception is an exact, signed revert (exact_revert()): it restores an earlier digest, so it may repeat it. Read
    from the top: a plain entry repeating any to_digest above it, a revert's included, is a repeat."""
    seen, dup, keys = set(), [], set()
    for entry in entries:
        to = str(entry.get('to_digest') or '')
        if source_only(entry):   # exempt from the digest rule; the same source-only change is declared once
            key = _key(entry)
            if key in keys and f'{to} (source_only)' not in dup:
                dup.append(f'{to} (source_only)')
            keys.add(key)
            continue
        if exact_revert(entry, entries):   # it may repeat; a plain entry below it may not repeat what it declares
            seen.add(to)
            continue
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

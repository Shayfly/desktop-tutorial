"""Registry Auditor: computes what each agent role and skill really is.

Separate dimensions (master directive 2026-10-09 §6), never one optimistic word:
  implementation  the named code imports / the named file exists
  configuration   its configuration/provider was observed (names only)
  verification    live evidence, its scope (what the run asserted) and its
                  freshness: evidence is STALE when the implementation files
                  changed after the commit that ran ("has a run id" is not enough)
  blocked         a named credential, permission or service is missing

Status:
  DEFINED          catalog only
  NOT_IMPLEMENTED  (skills) no code serves it -- said explicitly
  IMPLEMENTED      code exists, nothing verified it
  CONNECTED/TESTED code + configuration observed / unit tests only
  VERIFIED         fresh live evidence; always printed with its scope
  STALE            was verified, the code changed since; needs re-verification
  BLOCKED          a named dependency is missing

Freshness needs the content of each implementation file at the evidence
commit. `--write` reads it with git once and stores digests in
`omni_prod/registry_evidence_lock.json`, so tests and CI (shallow clones)
compute the same answer without history. A missing digest = freshness
unknown = not VERIFIED.

    python -m omni_prod.registry_audit            # markdown to stdout
    python -m omni_prod.registry_audit --write    # lock + docs/AGENT_SKILL_STATUS.md
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .agent_catalog import CATALOG, AgentRole
from .runtime_bindings import BY_ROLE, Binding, Evidence

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / 'omni_prod' / 'registry_evidence_lock.json'

DEFINED, NOT_IMPLEMENTED, IMPLEMENTED, CONNECTED, TESTED, VERIFIED, STALE, BLOCKED = (
    'DEFINED', 'NOT_IMPLEMENTED', 'IMPLEMENTED', 'CONNECTED', 'TESTED', 'VERIFIED', 'STALE', 'BLOCKED')
ORDER = (VERIFIED, STALE, CONNECTED, TESTED, IMPLEMENTED, BLOCKED, DEFINED, NOT_IMPLEMENTED)


@dataclass
class Row:
    role: AgentRole
    lifecycle: str
    implementation: str
    configuration: str
    verification: str
    evidence: str
    cost: str
    gap: str
    issues: list[str] = field(default_factory=list)
    blocked: str = ''


# ---- implementation ---------------------------------------------------------

def _importable(target: str) -> bool:
    if target.startswith('path:'):
        return (ROOT / target[5:]).is_file()
    module, _, symbol = target.partition(':')
    try:
        obj = importlib.import_module(module)
    except Exception:
        return False
    for part in symbol.split('.') if symbol else ():
        if not hasattr(obj, part):
            return False
        obj = getattr(obj, part)
    return True


def implementation_files(targets) -> tuple[str, ...]:
    files = []
    for t in targets:
        rel = t[5:] if t.startswith('path:') else t.partition(':')[0].replace('.', '/') + '.py'
        if rel not in files:
            files.append(rel)
    return tuple(sorted(files))


def _label(target: str) -> str:
    return target[5:] if target.startswith('path:') else (target.split(':')[1] or target)


# ---- freshness --------------------------------------------------------------

def _digest(data: bytes | None) -> str:
    if data is None:
        return 'absent'
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


def _current_digest(rel: str) -> str:
    p = ROOT / rel
    return _digest(p.read_bytes() if p.is_file() else None)


def load_lock() -> dict:
    try:
        return json.loads(LOCK_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def refresh_lock(evidence_files) -> dict:
    """For each (commit, file) the evidence needs, store the file's digest at
    that commit (read with git). Existing entries are kept: history does not
    change. Raises if git cannot resolve a commit (fix the evidence)."""
    lock = load_lock()
    for commit, rel in sorted(evidence_files):
        key = f'{commit}|{rel}'
        if key in lock:
            continue
        r = subprocess.run(['git', 'show', f'{commit}:{rel}'], cwd=ROOT, capture_output=True)
        if r.returncode != 0 and b'does not exist' not in r.stderr and b'exists on disk, but not in' not in r.stderr:
            raise RuntimeError(f'git cannot read {key}: {r.stderr.decode(errors="replace")[:200]}')
        lock[key] = _digest(r.stdout if r.returncode == 0 else None)
    LOCK_PATH.write_text(json.dumps(dict(sorted(lock.items())), indent=1) + '\n', encoding='utf-8')
    return lock


def freshness(ev: Evidence, files, lock: Mapping[str, str]) -> tuple[str, tuple[str, ...]]:
    """('fresh'|'stale'|'unknown', changed files)."""
    if not ev.commit:
        return 'unknown', ()
    changed, unknown = [], False
    for rel in files:
        locked = lock.get(f'{ev.commit}|{rel}')
        if locked is None:
            unknown = True
        elif locked != _current_digest(rel):
            changed.append(rel)
    if changed:
        return 'stale', tuple(changed)
    return ('unknown' if unknown else 'fresh'), ()


def _verification(evidence, files, lock, scope_text: str) -> tuple[str, str]:
    """(status, text) from evidence + freshness."""
    live = [e for e in evidence if e.kind == 'live']
    unit = [e for e in evidence if e.kind == 'unit']
    if live:
        states = [(e, *freshness(e, files, lock)) for e in live]
        fresh = [e for e, s, _ in states if s == 'fresh']
        if fresh:
            # Scope = what the FRESH runs asserted, not everything ever claimed.
            asserted = '; '.join(dict.fromkeys(a for e in fresh for a in e.asserts)) or scope_text
            return VERIFIED, f'VERIFIED for: {asserted} (fresh: {", ".join(e.ref.split()[0] + "@" + e.commit for e in fresh[:3])})'
        changed = sorted({c for _, s, ch in states if s == 'stale' for c in ch})
        newest = live[-1]
        why = ('code changed since: ' + ', '.join(changed)) if changed else 'freshness unknown (no digest for the evidence commit)'
        return STALE, f'STALE — was verified for: {scope_text} at {newest.commit or "?"}; {why}'
    if unit:
        return TESTED, 'unit tests only'
    return '', 'none'


def evidence_files() -> set[tuple[str, str]]:
    """Every (commit, file) pair the current evidence needs digests for."""
    from .skill_catalog import CATALOG as SKILLS
    from .runtime_bindings import BINDINGS, SKILL_BINDINGS
    pairs = set()
    for b in BINDINGS:
        for e in b.evidence:
            if e.kind == 'live' and e.commit:
                pairs |= {(e.commit, f) for f in implementation_files(b.implementation)}
    for s in SKILLS:
        for e in s.evidence:
            if e.kind == 'live' and e.commit:
                pairs |= {(e.commit, f) for f in implementation_files(s.implementation)}
    for b in SKILL_BINDINGS:
        for e in b.evidence:
            if e.kind == 'live' and e.commit:
                pairs.add((e.commit, 'omni_prod/skills_runtime.py'))
    return pairs


# ---- roles ------------------------------------------------------------------

def _config_state(binding: Binding, env: Mapping[str, str]) -> tuple[bool, str]:
    missing, notes = [], []
    for req in binding.config:
        present = req.observed or all((env.get(n) or '').strip() for n in req.names)
        notes.append(f"{'/'.join(req.names)}: {'ok' if present else 'MISSING'}" + (f' ({req.observed})' if req.observed else ''))
        if not present:
            missing.extend(req.names)
    return (not missing), ('; '.join(notes) or 'none needed')


def audit_role(role: AgentRole, env: Mapping[str, str] | None = None, registry_status: str | None = None,
               lock: Mapping[str, str] | None = None) -> Row:
    env = os.environ if env is None else env
    lock = load_lock() if lock is None else lock
    binding = BY_ROLE.get(role.key)
    issues: list[str] = []
    if binding is None:
        row = Row(role, DEFINED, '—', '—', 'not verified', '—', '—', 'not implemented')
    else:
        bad = [t for t in binding.implementation if not _importable(t)]
        if bad:
            issues.append('implementation does not import: ' + ', '.join(bad))
        configured, config_text = _config_state(binding, env)
        scope_text = '; '.join(binding.verified_scope) or binding.scope
        vstatus, vtext = _verification(binding.evidence, implementation_files(binding.implementation), lock, scope_text)
        unit = any(e.kind == 'unit' for e in binding.evidence)
        if bad:
            lifecycle = DEFINED
        elif binding.blocked_by or not configured:
            lifecycle = BLOCKED
        elif vstatus in (VERIFIED, STALE):
            lifecycle = vstatus
        elif binding.config or unit:
            lifecycle = CONNECTED
        else:
            lifecycle = IMPLEMENTED
        if vstatus == VERIFIED and not binding.verified_scope:
            issues.append('live evidence without a declared verified scope')
        evidence = '; '.join(e.ref + (f' — {e.note}' if e.note else '') + (f' [{e.env}@{e.commit}]' if e.commit else '')
                             for e in binding.evidence) or '—'
        row = Row(role, lifecycle, ', '.join(_label(t) for t in binding.implementation), config_text, vtext, evidence,
                  binding.cost or '—', '; '.join(binding.gaps) or '—', issues,
                  binding.blocked_by or ('' if configured else 'configuration missing'))
    if registry_status in ('LIVE',) and row.lifecycle != VERIFIED:
        row.issues.append(f'older registry says {registry_status} but there is no fresh live evidence')
    if registry_status in ('PARTIAL', 'LIVE') and row.lifecycle == DEFINED:
        row.issues.append(f'older registry says {registry_status} but no code on a runtime path serves this role')
    return row


def _registry_statuses() -> dict[str, str]:
    try:
        from .agents_registry import build_canonical_agents_registry
        from .skills_registry import build_canonical_skills_registry
        agents = build_canonical_agents_registry(build_canonical_skills_registry())
        return {a.key: a.status.value for a in agents.all()}
    except Exception:
        return {}


def skill_registry_findings() -> list[str]:
    """Older skills registry entries that claim more than the code delivers."""
    findings = []
    try:
        from .skills_registry import build_canonical_skills_registry
        skills = build_canonical_skills_registry().all()
    except Exception as exc:
        return [f'skills registry could not be built: {type(exc).__name__}']
    off_path = {}
    for s in skills:
        if s.implementation_location and not (ROOT / s.implementation_location).exists():
            findings.append(f'{s.key}: implementation file {s.implementation_location} does not exist')
        if s.status.value in ('PARTIAL', 'LIVE') and not s.key.startswith(('skill.software.', 'skill.target.web', 'skill.target.saas',
                                                                         'skill.target.backend', 'skill.target.database',
                                                                         'skill.internal.')):
            family = s.key.split('.')[1]
            off_path[family] = off_path.get(family, 0) + 1
    for family, n in sorted(off_path.items()):
        findings.append(f'{n} "{family}" skills are PARTIAL in the registry but none runs on a verified path')
    if skills and all(s.last_verified_version == 'registry-governance-v1' for s in skills if s.last_verified_version):
        findings.append('every older-registry skill\'s "last_verified" is the 2026-10-04 metadata check, not a capability run')
    return findings


def audit(env: Mapping[str, str] | None = None) -> list[Row]:
    statuses, lock = _registry_statuses(), load_lock()
    return [audit_role(r, env, statuses.get(r.registry_key) if r.registry_key else None, lock) for r in CATALOG]


# ---- skills -----------------------------------------------------------------

def catalog_skill_rows(lock: Mapping[str, str] | None = None) -> list[list[str]]:
    """Directive §9 catalog: kind, implementation, status with scope/freshness."""
    from .skill_catalog import CATALOG as SKILLS
    lock = load_lock() if lock is None else lock
    rows = []
    for s in SKILLS:
        if not s.implementation:
            status, vtext = NOT_IMPLEMENTED, 'none'
        elif not all(_importable(t) for t in s.implementation):
            status, vtext = DEFINED, 'implementation does not import'
        else:
            scope = '; '.join(a for e in s.evidence if e.kind == 'live' for a in e.asserts) or s.area
            vstatus, vtext = _verification(s.evidence, implementation_files(s.implementation), lock, scope)
            status = vstatus or IMPLEMENTED
        rows.append([s.key, s.area, s.kind, status, ', '.join(_label(t) for t in s.implementation) or '—',
                     ', '.join(s.depends) or '—', vtext, s.gap or '—'])
    return rows


def skill_rows(lock: Mapping[str, str] | None = None) -> list[list[str]]:
    """Runtime prompt skills (omni_prod.skills_runtime): INSTRUCTION, plus
    VALIDATOR when they carry static checks."""
    from .runtime_bindings import SKILL_BY_KEY
    from .skills_runtime import WEB_SKILLS
    lock = load_lock() if lock is None else lock
    rows = []
    for skill in WEB_SKILLS:
        b = SKILL_BY_KEY.get(skill.key)
        evidence = b.evidence if b else ()
        scope = '; '.join(a for e in evidence if e.kind == 'live' for a in e.asserts) or 'web'
        vstatus, vtext = _verification(evidence, ('omni_prod/skills_runtime.py',), lock, scope)
        rows.append([f'{skill.key}@{skill.version}', 'INSTRUCTION' + (' + VALIDATOR' if skill.static_checks else ''),
                     vstatus or CONNECTED, 'injected into: ' + ', '.join(skill.roles), vtext,
                     '; '.join(e.ref + (f' — {e.note}' if e.note else '') for e in evidence) or 'tests/test_skills_runtime_and_review.py',
                     '; '.join(b.gaps) if b and b.gaps else '—'])
    return rows


# ---- report -----------------------------------------------------------------

def _cell(text):
    return str(text).replace('|', '/').replace('\n', ' ')


def markdown(rows: list[Row], findings: list[str]) -> str:
    lock = load_lock()
    counts = {k: sum(1 for r in rows if r.lifecycle == k) for k in ORDER if any(r.lifecycle == k for r in rows)}
    srows = catalog_skill_rows(lock)
    scounts = {k: sum(1 for r in srows if r[3] == k) for k in ORDER if any(r[3] == k for r in srows)}
    out = ['# Agent/Skill status — computed by `python -m omni_prod.registry_audit --write`', '',
           'Generated from `omni_prod/agent_catalog.py` (roles), `omni_prod/skill_catalog.py` (directive §9 skills) and '
           '`omni_prod/runtime_bindings.py` (what runs, with evidence). Do not edit by hand.', '',
           'Dimensions are separate: implementation · configuration · verification (scope + freshness) · blocked. '
           'VERIFIED always names what the run asserted, and only counts while the implementation is unchanged since '
           'the commit that ran; otherwise the row is STALE and needs re-verification.', '',
           f'Roles ({len(rows)}): ' + ', '.join(f'{k} {v}' for k, v in counts.items()), '',
           f'Skills in the §9 catalog ({len(srows)}): ' + ', '.join(f'{k} {v}' for k, v in scounts.items()), '']
    for family in dict.fromkeys(r.role.family for r in rows):
        out += [f'## {family}', '',
                '| Agent | Status | Implementation | Configuration | Verification | Blocked | Evidence | Cost | Remaining gap |',
                '|---|---|---|---|---|---|---|---|---|']
        for r in (x for x in rows if x.role.family == family):
            out.append('| ' + ' | '.join(_cell(c) for c in (
                r.role.name, r.lifecycle + (' ⚠' if r.issues else ''), r.implementation, r.configuration,
                r.verification, r.blocked or '—', r.evidence, r.cost, r.gap)) + ' |')
        out.append('')
    out += ['## Skills catalog (directive §9)', '',
            '| Skill | Area | Kind | Status | Implementation | Depends on | Verification | Gap |',
            '|---|---|---|---|---|---|---|---|']
    out += ['| ' + ' | '.join(_cell(c) for c in r) + ' |' for r in srows] + ['']
    out += ['## Runtime prompt skills (web)', '',
            '| Skill | Kind | Status | Wiring | Verification | Evidence | Remaining gap |',
            '|---|---|---|---|---|---|---|']
    out += ['| ' + ' | '.join(_cell(c) for c in r) + ' |' for r in skill_rows(lock)] + ['']
    issues = [f'- {r.role.name}: {i}' for r in rows for i in r.issues]
    out += ['## Mismatches found', ''] + (issues or ['- none in agent roles']) + [f'- {f}' for f in findings] + ['']
    return '\n'.join(out)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if '--write' in argv:
        refresh_lock(evidence_files())
    rows = audit()
    text = markdown(rows, skill_registry_findings())
    if '--write' in argv:
        path = ROOT / 'docs' / 'AGENT_SKILL_STATUS.md'
        path.write_text(text + '\n', encoding='utf-8')
        print(f'wrote {path}')
    else:
        print(text)
    hard = [i for r in rows for i in r.issues if 'does not import' in i]
    return 1 if hard else 0


if __name__ == '__main__':
    raise SystemExit(main())

from __future__ import annotations
from dataclasses import dataclass
import re
_REQ=re.compile(r'^\s*([A-Za-z0-9_.-]+)(?:\[([A-Za-z0-9_.,-]+)\])?\s*(.*)$')
@dataclass(frozen=True)
class Dependency:
    name:str
    constraint:str
    pinned_version:str|None

def parse_requirement_line(line:str)->Dependency|None:
    s=line.strip()
    if not s or s.startswith('#'): return None
    if s.startswith(('-r ','--requirement ','-c ','--constraint ')):
        raise ValueError('nested requirement files are not allowed')
    if '@' in s: raise ValueError('direct URL/VCS dependencies require explicit provenance')
    m=_REQ.match(s)
    if not m: raise ValueError(f'invalid requirement: {line!r}')
    name=m.group(1).replace('_','-').lower(); extras=m.group(2); constraint=m.group(3).strip()
    exact=re.fullmatch(r'==\s*([A-Za-z0-9_.+-]+)',constraint)
    return Dependency(name+(f'[{extras}]' if extras else ''),constraint,exact.group(1) if exact else None)

def parse_requirements(text:str)->list[Dependency]:
    out=[]; seen=set()
    for line in text.splitlines():
        d=parse_requirement_line(line)
        if d is None: continue
        if d.name in seen: raise ValueError(f'duplicate dependency: {d.name}')
        seen.add(d.name); out.append(d)
    return out

def lock_status(deps:list[Dependency])->dict:
    unpinned=[d.name for d in deps if d.pinned_version is None]
    return {'locked':not unpinned,'total':len(deps),'unpinned':unpinned}

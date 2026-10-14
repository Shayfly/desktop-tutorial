from __future__ import annotations
from dataclasses import dataclass

_ALLOWED_KINDS = {'functional', 'quality', 'security', 'data', 'deployment'}

@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    kind: str = 'functional'
    mandatory: bool = True

@dataclass(frozen=True)
class AcceptanceCriterion:
    id: str
    requirement_id: str
    text: str

@dataclass(frozen=True)
class ProductSpec:
    title: str
    summary: str
    stack: tuple[str, ...]
    requirements: tuple[Requirement, ...]
    acceptance: tuple[AcceptanceCriterion, ...]

    @classmethod
    def from_dict(cls, data: dict) -> 'ProductSpec':
        if not isinstance(data, dict):
            raise TypeError('spec must be object')
        title = str(data.get('title', '')).strip()
        summary = str(data.get('summary', '')).strip()
        if not title or not summary:
            raise ValueError('title and summary are required')
        stack = tuple(str(x).strip() for x in data.get('stack', []) if str(x).strip())
        if not stack:
            raise ValueError('stack cannot be empty')
        reqs = []
        for raw in data.get('requirements', []):
            rid = str(raw.get('id', '')).strip()
            text = str(raw.get('text', '')).strip()
            kind = str(raw.get('kind', 'functional')).strip()
            if not rid or not text:
                raise ValueError('requirement id/text required')
            if kind not in _ALLOWED_KINDS:
                raise ValueError(f'invalid requirement kind: {kind}')
            reqs.append(Requirement(rid, text, kind, bool(raw.get('mandatory', True))))
        if not reqs:
            raise ValueError('at least one requirement required')
        if len({r.id for r in reqs}) != len(reqs):
            raise ValueError('duplicate requirement id')
        acc = []
        req_ids = {r.id for r in reqs}
        for raw in data.get('acceptance', []):
            aid = str(raw.get('id', '')).strip()
            rid = str(raw.get('requirement_id', '')).strip()
            text = str(raw.get('text', '')).strip()
            if not aid or not rid or not text:
                raise ValueError('acceptance id/requirement/text required')
            if rid not in req_ids:
                raise ValueError(f'acceptance references unknown requirement: {rid}')
            acc.append(AcceptanceCriterion(aid, rid, text))
        if len({a.id for a in acc}) != len(acc):
            raise ValueError('duplicate acceptance id')
        covered = {a.requirement_id for a in acc}
        missing = [r.id for r in reqs if r.mandatory and r.id not in covered]
        if missing:
            raise ValueError('mandatory requirements missing acceptance criteria: ' + ','.join(missing))
        return cls(title, summary, stack, tuple(reqs), tuple(acc))

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'summary': self.summary,
            'stack': list(self.stack),
            'requirements': [r.__dict__ for r in self.requirements],
            'acceptance': [a.__dict__ for a in self.acceptance],
        }

from __future__ import annotations
from dataclasses import dataclass
from .product_spec import ProductSpec

_ALLOWED = {'system_bug', 'missing_requirement', 'change_request', 'ambiguous'}

@dataclass(frozen=True)
class ChangeAssessment:
    category: str
    reason: str
    acceptance_ids: tuple[str, ...]
    billable: bool

    @classmethod
    def from_dict(cls, data: dict, *, spec: ProductSpec) -> 'ChangeAssessment':
        category = str(data.get('category', '')).strip()
        reason = str(data.get('reason', '')).strip()
        ids = tuple(str(x).strip() for x in data.get('acceptance_ids', []) if str(x).strip())
        if category not in _ALLOWED:
            raise ValueError('invalid change category')
        if not reason:
            raise ValueError('change reason required')
        valid = {a.id for a in spec.acceptance}
        if any(x not in valid for x in ids):
            raise ValueError('unknown acceptance criterion reference')
        if category in {'system_bug', 'missing_requirement'}:
            if not ids:
                raise ValueError('free repair must reference failed acceptance criteria')
            billable = False
        elif category == 'change_request':
            billable = True
        else:
            billable = False
        return cls(category, reason, ids, billable)

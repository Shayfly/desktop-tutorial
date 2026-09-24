from __future__ import annotations
from dataclasses import dataclass

ROLE_PERMISSIONS = {
    'owner': frozenset({'project:read','project:write','deploy','billing','team:manage','secrets:manage'}),
    'admin': frozenset({'project:read','project:write','deploy','team:manage','secrets:manage'}),
    'developer': frozenset({'project:read','project:write','deploy'}),
    'designer': frozenset({'project:read','project:write'}),
    'viewer': frozenset({'project:read'}),
    'billing': frozenset({'project:read','billing'}),
}

@dataclass(frozen=True)
class Membership:
    org_id: str
    user_id: str
    role: str

    def __post_init__(self):
        if self.role not in ROLE_PERMISSIONS:
            raise ValueError('unknown role')

def can(member: Membership, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS[member.role]

def require(member: Membership, permission: str) -> None:
    if not can(member, permission):
        raise PermissionError(f'{member.role} lacks {permission}')

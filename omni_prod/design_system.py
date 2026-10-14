from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256

@dataclass(frozen=True)
class DesignTokens:
    radius_scale: tuple[int,...]
    spacing_scale: tuple[int,...]
    type_scale: tuple[int,...]
    density: str
    motion: str
    visual_personality: str

    def to_dict(self): return asdict(self)

PERSONALITIES = ('editorial','technical','luxury','playful','minimal','bold','calm','commerce')

def derive_tokens(project_seed: str) -> DesignTokens:
    if not project_seed.strip(): raise ValueError('project_seed required')
    n=int(sha256(project_seed.encode()).hexdigest()[:8],16)
    personality=PERSONALITIES[n % len(PERSONALITIES)]
    density=('compact','balanced','spacious')[n % 3]
    motion=('subtle','standard','expressive')[(n//3)%3]
    radius=((4,8,12,18),(2,6,10,16),(8,14,20,28))[n%3]
    spacing=((4,8,12,16,24,32,48),(4,8,16,24,32,48,64),(6,12,18,24,36,48,72))[n%3]
    type=((12,14,16,20,28,40,56),(13,15,17,22,30,44,64),(12,14,18,24,32,48,72))[n%3]
    return DesignTokens(radius,spacing,type,density,motion,personality)

def anti_template_fingerprint(tokens: DesignTokens) -> str:
    return sha256(repr(tokens).encode()).hexdigest()[:16]

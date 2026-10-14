from __future__ import annotations
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class ArtifactDigest:
    sha256: str
    size: int

def digest_bytes(data: bytes) -> ArtifactDigest:
    return ArtifactDigest(hashlib.sha256(data).hexdigest(), len(data))

def verify_bytes(data: bytes, expected: ArtifactDigest) -> None:
    actual = digest_bytes(data)
    if actual.size != expected.size:
        raise RuntimeError("artifact size mismatch")
    if actual.sha256 != expected.sha256:
        raise RuntimeError("artifact checksum mismatch")

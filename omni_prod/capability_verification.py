from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from typing import Iterable

from .provider_contracts import CapabilityArtifact


class ArtifactVerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArtifactVerificationResult:
    verified: bool
    sha256: str
    size_bytes: int
    checks: tuple[str, ...]


def _validate_glb(prefix: bytes, total_size: int) -> None:
    if len(prefix) < 20:
        raise ArtifactVerificationError("GLB is too small for header and first chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", prefix, 0)
    if magic != b"glTF":
        raise ArtifactVerificationError("GLB magic header is invalid")
    if version != 2:
        raise ArtifactVerificationError(f"GLB version must be 2, got {version}")
    if declared_length != total_size:
        raise ArtifactVerificationError(
            f"GLB declared length {declared_length} does not match actual size {total_size}"
        )
    chunk_length, chunk_type = struct.unpack_from("<I4s", prefix, 12)
    if chunk_type not in {b"JSON", b"BIN\x00"}:
        raise ArtifactVerificationError("GLB first chunk type is invalid")
    if 20 + chunk_length > total_size:
        raise ArtifactVerificationError("GLB first chunk exceeds declared file length")


def _validate_magic(mime_type: str, prefix: bytes, total_size: int) -> tuple[str, ...]:
    checks: list[str] = []
    normalized = mime_type.lower().strip()
    if normalized == "model/gltf-binary":
        _validate_glb(prefix, total_size)
        checks.append("glb-structure")
    elif normalized == "image/png":
        if not prefix.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ArtifactVerificationError("PNG magic header is invalid")
        checks.append("png-signature")
    elif normalized in {"image/jpeg", "image/jpg"}:
        if not prefix.startswith(b"\xff\xd8\xff"):
            raise ArtifactVerificationError("JPEG magic header is invalid")
        checks.append("jpeg-signature")
    elif normalized in {"audio/wav", "audio/x-wav", "audio/wave"}:
        if len(prefix) < 12 or prefix[:4] != b"RIFF" or prefix[8:12] != b"WAVE":
            raise ArtifactVerificationError("WAV container header is invalid")
        checks.append("wav-header")
    elif normalized == "application/zip":
        if not prefix.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            raise ArtifactVerificationError("ZIP signature is invalid")
        checks.append("zip-signature")
    return tuple(checks)


def verify_capability_artifact_stream(
    expected: CapabilityArtifact,
    chunks: Iterable[bytes],
    *,
    max_size_bytes: int | None = None,
) -> ArtifactVerificationResult:
    if max_size_bytes is not None and max_size_bytes < 1:
        raise ValueError("max_size_bytes must be >= 1 when configured")

    digest = hashlib.sha256()
    total = 0
    prefix = bytearray()
    prefix_limit = 64 * 1024

    for raw in chunks:
        chunk = bytes(raw)
        if not chunk:
            continue
        total += len(chunk)
        if max_size_bytes is not None and total > max_size_bytes:
            raise ArtifactVerificationError(
                f"artifact exceeds maximum size of {max_size_bytes} bytes"
            )
        digest.update(chunk)
        if len(prefix) < prefix_limit:
            prefix.extend(chunk[: prefix_limit - len(prefix)])

    if total == 0:
        raise ArtifactVerificationError("artifact is empty")
    if total != expected.size_bytes:
        raise ArtifactVerificationError(
            f"artifact size mismatch: expected {expected.size_bytes}, got {total}"
        )
    actual_digest = digest.hexdigest()
    if actual_digest.lower() != expected.sha256.lower():
        raise ArtifactVerificationError("artifact checksum mismatch")

    checks = ["non-empty", "size", "sha256"]
    checks.extend(_validate_magic(expected.mime_type, bytes(prefix), total))
    return ArtifactVerificationResult(
        verified=True,
        sha256=actual_digest,
        size_bytes=total,
        checks=tuple(checks),
    )


def verify_capability_artifact(
    expected: CapabilityArtifact,
    data: bytes,
    *,
    max_size_bytes: int | None = None,
) -> ArtifactVerificationResult:
    return verify_capability_artifact_stream(
        expected,
        (bytes(data),),
        max_size_bytes=max_size_bytes,
    )

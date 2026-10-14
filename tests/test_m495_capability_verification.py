import hashlib
import io
import struct
import tempfile
import unittest
from pathlib import Path

from omni_prod.capability_verification import (
    ArtifactVerificationError,
    verify_capability_artifact,
    verify_capability_artifact_stream,
)
from omni_prod.provider_contracts import CapabilityArtifact
from omni_prod.storage import ArtifactIntegrityError, S3ArtifactStore


def artifact_for(data: bytes, *, mime="application/octet-stream", key="artifact.bin", capability="publish.asset"):
    return CapabilityArtifact(
        artifact_key=key,
        mime_type=mime,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        provider="fake",
        capability_key=capability,
        metadata={},
        provenance={},
    )


def minimal_glb() -> bytes:
    json_chunk = b"{}  "
    length = 12 + 8 + len(json_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, length)
        + struct.pack("<I4s", len(json_chunk), b"JSON")
        + json_chunk
    )


class CapabilityArtifactVerificationTests(unittest.TestCase):
    def test_checksum_mismatch_is_rejected(self):
        expected = artifact_for(b"hello")
        with self.assertRaisesRegex(ArtifactVerificationError, "checksum"):
            verify_capability_artifact(expected, b"jello")

    def test_empty_artifact_is_rejected_even_if_metadata_matches(self):
        expected = artifact_for(b"")
        with self.assertRaisesRegex(ArtifactVerificationError, "empty"):
            verify_capability_artifact(expected, b"")

    def test_random_bytes_cannot_claim_to_be_glb(self):
        data = b"not-a-glb-but-hash-is-correct"
        expected = artifact_for(
            data,
            mime="model/gltf-binary",
            key="mesh.glb",
            capability="media.3d.mesh.generate",
        )
        with self.assertRaisesRegex(ArtifactVerificationError, "GLB"):
            verify_capability_artifact(expected, data)

    def test_minimal_valid_glb_passes_structural_validation(self):
        data = minimal_glb()
        expected = artifact_for(
            data,
            mime="model/gltf-binary",
            key="mesh.glb",
            capability="media.3d.mesh.generate",
        )
        result = verify_capability_artifact(expected, data)
        self.assertTrue(result.verified)
        self.assertIn("glb-structure", result.checks)

    def test_glb_declared_length_must_match_actual_size(self):
        data = bytearray(minimal_glb())
        struct.pack_into("<I", data, 8, len(data) + 4)
        payload = bytes(data)
        expected = artifact_for(payload, mime="model/gltf-binary", key="mesh.glb", capability="media.3d.mesh.generate")
        with self.assertRaisesRegex(ArtifactVerificationError, "declared length"):
            verify_capability_artifact(expected, payload)

    def test_stream_verification_hashes_incrementally_and_enforces_max_size(self):
        data = b"a" * 1024 + b"b" * 2048 + b"c" * 3072
        expected = artifact_for(data)
        result = verify_capability_artifact_stream(
            expected,
            (data[:1024], data[1024:3072], data[3072:]),
            max_size_bytes=len(data),
        )
        self.assertTrue(result.verified)
        self.assertEqual(result.size_bytes, len(data))
        with self.assertRaisesRegex(ArtifactVerificationError, "maximum size"):
            verify_capability_artifact_stream(
                expected,
                (data[:1024], data[1024:]),
                max_size_bytes=2048,
            )


class ChunkedBody:
    def __init__(self, data: bytes):
        self._io = io.BytesIO(data)
        self.read_sizes = []
    def read(self, size=-1):
        self.read_sizes.append(size)
        if size is None or size < 0:
            raise AssertionError("streaming path must never call unbounded read()")
        return self._io.read(size)


class FakeS3Client:
    def __init__(self, data: bytes, digest: str):
        self.body = ChunkedBody(data)
        self.digest = digest
    def get_object(self, *, Bucket, Key):
        return {"Body": self.body, "Metadata": {"sha256": self.digest}, "ContentLength": None}


class StorageStreamingTests(unittest.TestCase):
    def _store(self, data: bytes, digest: str | None = None):
        store = object.__new__(S3ArtifactStore)
        store.bucket = "bucket"
        store.client = FakeS3Client(data, digest or hashlib.sha256(data).hexdigest())
        return store

    def test_iter_bytes_verifies_checksum_without_unbounded_read(self):
        data = b"0123456789" * 100
        store = self._store(data)
        streamed = b"".join(store.iter_bytes("x", chunk_size=37, verify=True))
        self.assertEqual(streamed, data)
        self.assertTrue(all(size == 37 for size in store.client.body.read_sizes[:-1]))
        self.assertNotIn(-1, store.client.body.read_sizes)

    def test_iter_bytes_detects_corruption(self):
        data = b"correct-body"
        store = self._store(data, digest=hashlib.sha256(b"different").hexdigest())
        with self.assertRaises(ArtifactIntegrityError):
            b"".join(store.iter_bytes("x", chunk_size=4, verify=True))

    def test_download_file_uses_streaming_path(self):
        data = b"video-data" * 1000
        store = self._store(data)
        with tempfile.TemporaryDirectory() as td:
            path = store.download_file("x", Path(td) / "nested" / "asset.bin", verify=True, chunk_size=128)
            self.assertEqual(path.read_bytes(), data)
            self.assertNotIn(-1, store.client.body.read_sizes)


if __name__ == "__main__":
    unittest.main()

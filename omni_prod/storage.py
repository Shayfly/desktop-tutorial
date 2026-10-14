from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import io
from urllib.parse import urlsplit

@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size: int

class ArtifactIntegrityError(RuntimeError):
    pass

class S3ArtifactStore:
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ):
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        host = (urlsplit(endpoint).hostname or '').lower()
        r2_options = {}
        if host.endswith('.r2.cloudflarestorage.com'):
            # Recent boto3 defaults add optional streaming checksum trailers.
            # R2 does not support x-amz-sdk-checksum-algorithm on PutObject.
            # Keep SigV4 and our independently verified SHA256 object metadata.
            # https://developers.cloudflare.com/r2/api/s3/api/
            region = 'auto'
            r2_options = {'signature_version': 's3v4',
                          's3': {'addressing_style': 'path'},
                          'request_checksum_calculation': 'when_required',
                          'response_checksum_validation': 'when_required'}
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
                **r2_options,
                connect_timeout=5,
                read_timeout=30,
                retries={"max_attempts": 4, "mode": "standard"},
            ),
        )

    @staticmethod
    def _digest(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def ping(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False

    def put_bytes(self, key: str, data: bytes) -> StoredObject:
        payload = bytes(data)
        digest = self._digest(payload)
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=payload,
            Metadata={"sha256": digest},
        )
        return StoredObject(key=key, sha256=digest, size=len(payload))

    def iter_bytes(
        self,
        key: str,
        *,
        chunk_size: int = 1024 * 1024,
        verify: bool = True,
        max_size_bytes: int | None = None,
    ):
        if chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        if max_size_bytes is not None and max_size_bytes < 1:
            raise ValueError("max_size_bytes must be >= 1 or None")
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"]
        expected = (response.get("Metadata") or {}).get("sha256")
        digest = hashlib.sha256()
        size = 0
        try:
            while True:
                chunk = body.read(chunk_size)
                if not chunk:
                    break
                payload = bytes(chunk)
                size += len(payload)
                if max_size_bytes is not None and size > max_size_bytes:
                    raise ArtifactIntegrityError(
                        f"artifact exceeds maximum size for {key}"
                    )
                if verify:
                    digest.update(payload)
                yield payload
            if verify and expected and digest.hexdigest() != expected:
                raise ArtifactIntegrityError(f"checksum mismatch for {key}")
        finally:
            close = getattr(body, "close", None)
            if callable(close):
                close()

    def get_bytes(self, key: str, *, verify: bool = True) -> bytes:
        """Small-object compatibility path; use iter_bytes/download_file for large artifacts."""
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        data = response["Body"].read()
        if verify:
            expected = (response.get("Metadata") or {}).get("sha256")
            if expected and self._digest(data) != expected:
                raise ArtifactIntegrityError(f"checksum mismatch for {key}")
        return data

    def put_file(
        self,
        path: str | Path,
        key: str,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> StoredObject:
        if chunk_size < 1:
            raise ValueError("chunk_size must be >= 1")
        p = Path(path)
        digest = hashlib.sha256()
        size = 0
        with p.open("rb") as source:
            while True:
                chunk = source.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        hexdigest = digest.hexdigest()
        with p.open("rb") as source:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=source,
                ContentLength=size,
                Metadata={"sha256": hexdigest},
            )
        return StoredObject(key=key, sha256=hexdigest, size=size)

    def download_file(
        self,
        key: str,
        destination: str | Path,
        *,
        verify: bool = True,
        chunk_size: int = 1024 * 1024,
        max_size_bytes: int | None = None,
    ) -> Path:
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.name + ".part")
        try:
            with partial.open("wb") as target:
                for chunk in self.iter_bytes(
                    key,
                    chunk_size=chunk_size,
                    verify=verify,
                    max_size_bytes=max_size_bytes,
                ):
                    target.write(chunk)
            partial.replace(dest)
            return dest
        except Exception:
            partial.unlink(missing_ok=True)
            raise

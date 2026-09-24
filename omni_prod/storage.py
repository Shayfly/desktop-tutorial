from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import io

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
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(
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

    def get_bytes(self, key: str, *, verify: bool = True) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        data = response["Body"].read()
        if verify:
            expected = (response.get("Metadata") or {}).get("sha256")
            if expected and self._digest(data) != expected:
                raise ArtifactIntegrityError(f"checksum mismatch for {key}")
        return data

    def put_file(self, path: str | Path, key: str) -> StoredObject:
        p = Path(path)
        return self.put_bytes(key, p.read_bytes())

    def download_file(
        self,
        key: str,
        destination: str | Path,
        *,
        verify: bool = True,
    ) -> Path:
        data = self.get_bytes(key, verify=verify)
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest

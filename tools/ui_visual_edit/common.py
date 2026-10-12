"""Local harness pieces shared by the API server and the preview host (UI test only)."""
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
DB = os.environ['VE_DB']


class LocalFileStore:
    """Object storage for the local UI test: files under store/, sha256 verified.
    (Production uses S3/R2 via omni_prod.storage.S3ArtifactStore.)"""
    bucket = 'local'

    def __init__(self, root=ROOT / 'store'):
        self.root = Path(root)
        self.client = SimpleNamespace(delete_object=lambda Bucket, Key: (self.root / Key).unlink())

    def put_bytes(self, key, data):
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes(data))
        (p.parent / (p.name + '.sha256')).write_text(hashlib.sha256(data).hexdigest())
        return SimpleNamespace(key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))

    def get_bytes(self, key, verify=True):
        p = self.root / key
        data = p.read_bytes()
        if verify and hashlib.sha256(data).hexdigest() != (p.parent / (p.name + '.sha256')).read_text():
            raise RuntimeError('integrity')
        return data

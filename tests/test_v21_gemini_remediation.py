import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_prod.config import Settings
from omni_prod.db import DatabasePool
from omni_prod.production_adapters import assert_not_memory_adapter
from omni_prod.memory_adapters import MemoryBuildRepository
from omni_prod.redis_circuit_breaker import (
    RedisCircuitBreaker, RedisCircuitPolicy
)
from omni_prod.sandbox import SandboxLimits, build_docker_command
from omni_prod.storage import S3ArtifactStore, ArtifactIntegrityError

class ProductionAdapterSafetyTests(unittest.TestCase):
    def test_memory_adapter_rejected(self):
        with self.assertRaises(RuntimeError):
            assert_not_memory_adapter(MemoryBuildRepository())

    def test_production_factory_module_does_not_import_memory_adapters(self):
        path = Path("omni_prod/production_adapters.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
        self.assertFalse(any("memory_adapters" in name for name in imports))

class DatabasePoolTests(unittest.TestCase):
    def test_invalid_pool_sizes_rejected_by_settings(self):
        env = {
            "OMNI_ENV":"production",
            "OMNI_SECRET_KEY":"x"*64,
            "OMNI_DATABASE_URL":"postgresql://db",
            "OMNI_REDIS_URL":"redis://redis",
            "OMNI_S3_ENDPOINT":"http://s3",
            "OMNI_S3_BUCKET":"bucket",
            "OMNI_S3_ACCESS_KEY":"access",
            "OMNI_S3_SECRET_KEY":"secret",
            "OMNI_DB_POOL_MIN_SIZE":"10",
            "OMNI_DB_POOL_MAX_SIZE":"2",
        }
        with patch.dict("os.environ", env, clear=True):
            with self.assertRaises(RuntimeError):
                Settings.from_env()

class SandboxHardeningTests(unittest.TestCase):
    def test_command_contains_nonroot_and_resource_hardening(self):
        with tempfile.TemporaryDirectory() as td:
            cmd = build_docker_command(
                source_dir=td,
                build_id="secure-1",
                limits=SandboxLimits(),
                command=["python","-V"],
            )
        joined = " ".join(cmd)
        self.assertIn("--network none", joined)
        self.assertIn("--read-only", joined)
        self.assertIn("--cap-drop ALL", joined)
        self.assertIn("--user 10001:10001", joined)
        self.assertIn("--memory-swap 1024m", joined)
        self.assertIn("--ulimit nofile=1024:1024", joined)
        self.assertNotIn("/var/run/docker.sock", joined)

class FakeBody:
    def __init__(self, data): self.data=data
    def read(self): return self.data

class FakeS3:
    def __init__(self):
        self.objects={}
    def put_object(self, **kw):
        body=bytes(kw["Body"])
        self.objects[(kw["Bucket"],kw["Key"])] = {
            "Body":body, "Metadata":dict(kw.get("Metadata") or {})
        }
    def get_object(self, **kw):
        obj=self.objects[(kw["Bucket"],kw["Key"])]
        return {"Body":FakeBody(obj["Body"]), "Metadata":obj["Metadata"]}
    def head_bucket(self, **kw): return {}

class StorageTests(unittest.TestCase):
    def make_store(self):
        store = object.__new__(S3ArtifactStore)
        store.bucket = "b"
        store.client = FakeS3()
        return store

    def test_s3_roundtrip_verifies_hash(self):
        store=self.make_store()
        store.put_bytes("x",b"hello")
        self.assertEqual(store.get_bytes("x"),b"hello")

    def test_s3_detects_tamper(self):
        store=self.make_store()
        store.put_bytes("x",b"hello")
        store.client.objects[("b","x")]["Body"]=b"evil"
        with self.assertRaises(ArtifactIntegrityError):
            store.get_bytes("x")

class FakePipe:
    def __init__(self,r): self.r=r
    def hset(self,*a,**kw): self.r.hset(*a,**kw); return self
    def delete(self,*a,**kw): self.r.delete(*a,**kw); return self
    def execute(self): return []

class FakeRedis:
    def __init__(self):
        self.h={}
        self.kv={}
    def hgetall(self,key): return dict(self.h.get(key,{}))
    def hincrby(self,key,field,amount):
        d=self.h.setdefault(key,{})
        bfield=field.encode() if isinstance(field,str) else field
        value=int(d.get(bfield,0))+amount
        d[bfield]=value
        return value
    def hset(self,key,mapping):
        d=self.h.setdefault(key,{})
        for k,v in mapping.items():
            bk=k.encode() if isinstance(k,str) else k
            d[bk]=v.encode() if isinstance(v,str) else v
    def set(self,key,value,nx=False,ex=None):
        if nx and key in self.kv: return False
        self.kv[key]=value
        return True
    def delete(self,key):
        self.kv.pop(key,None)
    def pipeline(self): return FakePipe(self)

class DistributedCircuitTests(unittest.TestCase):
    def test_cross_instance_state_uses_shared_redis(self):
        r=FakeRedis()
        a=RedisCircuitBreaker(r,name="provider",policy=RedisCircuitPolicy(2,10))
        b=RedisCircuitBreaker(r,name="provider",policy=RedisCircuitPolicy(2,10))
        a.failure(now=0)
        a.failure(now=1)
        self.assertFalse(b.allow(now=5))
        self.assertTrue(b.allow(now=12))
        self.assertFalse(a.allow(now=12))
        b.success()
        self.assertTrue(a.allow(now=13))

if __name__ == "__main__":
    unittest.main()

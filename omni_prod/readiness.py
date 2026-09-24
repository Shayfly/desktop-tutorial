from __future__ import annotations
from dataclasses import dataclass, asdict
import os
import shutil

@dataclass(frozen=True)
class ReadinessGate:
    name: str
    passed: bool
    required_for_live: bool
    detail: str

def _any_env(*names): return next((os.getenv(n) for n in names if os.getenv(n)), None)

def collect_readiness() -> list[ReadinessGate]:
    local_model=os.getenv('OMNI_LOCAL_MODEL_URL','http://127.0.0.1:8001/v1')
    db=_any_env('OMNI_DATABASE_URL','DATABASE_URL')
    redis=_any_env('OMNI_REDIS_URL','REDIS_URL')
    s3=all(_any_env(a,b) for a,b in (
        ('OMNI_S3_ENDPOINT','S3_ENDPOINT_URL'),('OMNI_S3_BUCKET','S3_BUCKET'),
        ('OMNI_S3_ACCESS_KEY','S3_ACCESS_KEY_ID'),('OMNI_S3_SECRET_KEY','S3_SECRET_ACCESS_KEY')))
    return [
        ReadinessGate('python',bool(shutil.which('python')),True,'Python runtime available'),
        ReadinessGate('docker',bool(shutil.which('docker')),True,'Required for isolated generated-code execution'),
        ReadinessGate('local_model_config',bool(local_model),True,f'Configured endpoint: {local_model}'),
        ReadinessGate('postgres_config',bool(db),True,'PostgreSQL configured' if db else 'PostgreSQL not configured'),
        ReadinessGate('redis_config',bool(redis),True,'Redis configured' if redis else 'Redis not configured'),
        ReadinessGate('s3_config',bool(s3),True,'S3-compatible object storage configured' if s3 else 'S3-compatible object storage not fully configured'),
        ReadinessGate('live_build_switch',os.getenv('OMNI_ENABLE_LIVE_BUILD')=='1',False,'Live AI build endpoint is opt-in'),
        ReadinessGate('zero_cost_mode',os.getenv('OMNI_ZERO_COST_MODE','1')=='1',False,'External model spend blocked by default'),
        ReadinessGate('android_toolchain',bool(shutil.which('java')),False,'JDK available for Android builds'),
        ReadinessGate('ios_toolchain',bool(shutil.which('xcodebuild')),False,'Xcode required for signed iOS builds'),
    ]

def readiness_payload() -> dict:
    gates=collect_readiness(); required=[g for g in gates if g.required_for_live]
    return {'live_ready':all(g.passed for g in required),'required_passed':sum(g.passed for g in required),
            'required_total':len(required),'gates':[asdict(g) for g in gates]}

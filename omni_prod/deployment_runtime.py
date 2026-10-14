from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class AutoscalingPolicy:
    min_replicas: int=2
    max_replicas: int=20
    target_cpu_percent: int=65
    max_queue_depth_per_worker: int=5

    def __post_init__(self):
        if self.min_replicas < 1 or self.max_replicas < self.min_replicas: raise ValueError('invalid replica bounds')
        if not 10 <= self.target_cpu_percent <= 95: raise ValueError('invalid cpu target')
        if self.max_queue_depth_per_worker < 1: raise ValueError('invalid queue threshold')

@dataclass(frozen=True)
class RuntimeTopology:
    api_replicas: AutoscalingPolicy
    worker_replicas: AutoscalingPolicy
    database_pool_max: int
    object_storage_required: bool=True
    queue_required: bool=True

    def to_dict(self): return asdict(self)

def international_default_topology() -> RuntimeTopology:
    return RuntimeTopology(AutoscalingPolicy(2,30,65,10), AutoscalingPolicy(2,100,70,3), 40)

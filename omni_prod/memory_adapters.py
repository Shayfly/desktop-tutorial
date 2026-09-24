from __future__ import annotations
from dataclasses import dataclass
from .models import BuildStatus

class MemoryBuildRepository:
    def __init__(self): self.jobs={}
    def create(self, *, build_id, project_id, version_id):
        if build_id in self.jobs: raise KeyError('duplicate build')
        self.jobs[build_id]={'project_id':project_id,'version_id':version_id,'status':BuildStatus.QUEUED,'artifact_key':None}
    def transition(self, *, build_id, expected, target, artifact_key=None, error_code=None, error_message=None):
        j=self.jobs[build_id]
        if j['status']!=expected: return False
        j.update(status=target,artifact_key=artifact_key,error_code=error_code,error_message=error_message)
        return True
    def get_status(self, build_id): return self.jobs[build_id]['status'] if build_id in self.jobs else None

class MemoryArtifactStore:
    def __init__(self): self.objects={}
    def put_bytes(self,key,data:bytes):
        if key in self.objects: raise KeyError('immutable object already exists')
        self.objects[key]=bytes(data)
    def get_bytes(self,key): return self.objects[key]

class MemoryDeploymentRepository:
    def __init__(self): self.history=[]
    def promote(self, promotion):
        self.history.insert(0,promotion)
    def current(self, *, project_id, environment):
        for p in self.history:
            if p.project_id==project_id and p.environment==environment:
                return p
        return None

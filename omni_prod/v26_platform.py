from __future__ import annotations
from dataclasses import asdict
from .account_tenant import AccountService
from .unified_engine import UnifiedOmniEngine
from .universal_brain import OmniUniversalBrain
from .repository_patch import FilePatch, apply_patch

class V26UniversalPlatform:
    """Owner-isolated control plane combining account, brain and unified engine."""
    def __init__(self,*,token_secret:str,generated_app_token_secret:str|None=None):
        self.accounts=AccountService(token_secret=token_secret)
        self.engine=UnifiedOmniEngine(token_secret=generated_app_token_secret or token_secret)
        self.brain=OmniUniversalBrain()

    def register(self,*,email:str,password:str)->dict:
        account,issued=self.accounts.register(email=email,password=password)
        return {'user':{'id':account.id,'email':account.email,'created_at':account.created_at},'token':issued}

    def login(self,*,email:str,password:str)->dict:
        account,issued=self.accounts.login(email=email,password=password)
        return {'user':{'id':account.id,'email':account.email},'token':issued}

    def account(self,token:str): return self.accounts.authenticate(token)

    def create_project(self,*,token:str,title:str)->dict:
        account=self.account(token); rec=self.accounts.create_project(owner_id=account.id,title=title)
        return asdict(rec)

    def list_projects(self,*,token:str)->list[dict]:
        account=self.account(token); return [asdict(x) for x in self.accounts.list_projects(owner_id=account.id)]

    def _key(self,*,token:str,project_id:str)->tuple[object,str]:
        account=self.account(token); self.accounts.require_project(owner_id=account.id,project_id=project_id)
        return account,self.accounts.internal_project_key(owner_id=account.id,project_id=project_id)


    def resolve_project_key(self,*,token:str,project_id:str)->tuple[object,str]:
        return self._key(token=token,project_id=project_id)

    def build(self,*,token:str,project_id:str,prompt:str)->dict:
        account,key=self._key(token=token,project_id=project_id)
        decision=self.brain.decide(prompt)
        result=self.engine.build(project_id=key,prompt=prompt)
        # Make creative obligations part of the immutable project history.
        patches=[FilePatch(path=p,content=c) for p,c in decision.creative and self.brain.creative.repository_files(decision.creative).items()]
        current=self.engine.workspace.current(key)
        repo=apply_patch(current.repository(),patches) if patches else current.repository()
        final_version=self.engine.workspace.commit(project_id=key,repository=repo,message='V26 creative/rights manifest')
        return {
            'status':result.status,'project_id':project_id,'owner_id':account.id,
            'version_id':final_version.id,'checksum':final_version.checksum,
            'file_count':len(repo),'launch_score':result.launch_score,'launch_ready':result.launch_ready,
            'brain':decision.to_dict(),
            'creative_assets':{'planned':len(decision.creative.requests),'materialized':0,'truth':'planned assets are not claimed as generated until a configured provider returns files'},
        }

    def export(self,*,token:str,project_id:str,version_id:str|None=None)->bytes:
        _,key=self._key(token=token,project_id=project_id)
        return self.engine.export_zip(project_id=key,version_id=version_id)

    def history(self,*,token:str,project_id:str)->list[dict]:
        _,key=self._key(token=token,project_id=project_id)
        return [{'id':v.id,'parent_id':v.parent_id,'created_at':v.created_at,'message':v.message,'checksum':v.checksum,'file_count':len(v.files)} for v in self.engine.workspace.history(key)]

    def patch(self,*,token:str,project_id:str,payload:dict,message:str='user edit')->dict:
        _,key=self._key(token=token,project_id=project_id)
        v=self.engine.patch(project_id=key,payload=payload,message=message)
        return {'project_id':project_id,'version_id':v.id,'parent_id':v.parent_id,'checksum':v.checksum}


    def restore(self,*,token:str,project_id:str,version_id:str)->dict:
        _,key=self._key(token=token,project_id=project_id)
        v=self.engine.workspace.restore(project_id=key,version_id=version_id,message='user restore')
        return {'project_id':project_id,'version_id':v.id,'parent_id':v.parent_id,'checksum':v.checksum}

    def repository(self,*,token:str,project_id:str,version_id:str|None=None)->dict[str,str]:
        _,key=self._key(token=token,project_id=project_id)
        return self.engine.repository(project_id=key,version_id=version_id)

    def promote(self,*,token:str,project_id:str,version_id:str|None=None)->dict:
        account,key=self._key(token=token,project_id=project_id)
        snap=self.engine.promote(project_id=key,version_id=version_id)
        return {'deployment_id':snap.deployment_id,'project_id':project_id,'owner_id':account.id,'version_id':snap.version_id,'repository_checksum':snap.repository_checksum}

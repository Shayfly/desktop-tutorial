from __future__ import annotations
from datetime import datetime,timezone
import json,uuid
from .dependency_inventory import Dependency

def build_cyclonedx_bom(deps:list[Dependency],*,component_name:str,version:str)->dict:
    components=[]
    for d in deps:
        package_name=d.name.split('[',1)[0]
        c={'type':'library','name':d.name,'bom-ref':f'pkg:pypi/{package_name}'+(f'@{d.pinned_version}' if d.pinned_version else '')}
        if d.pinned_version:
            c['version']=d.pinned_version; c['purl']=f'pkg:pypi/{package_name}@{d.pinned_version}'
        else:
            c['properties']=[{'name':'omni:declaredConstraint','value':d.constraint or '*'}, {'name':'omni:resolved','value':'false'}]
        components.append(c)
    return {'bomFormat':'CycloneDX','specVersion':'1.5','serialNumber':f'urn:uuid:{uuid.uuid4()}','version':1,
            'metadata':{'timestamp':datetime.now(timezone.utc).isoformat(),'component':{'type':'application','name':component_name,'version':version}},
            'components':components}

def write_bom(path,bom:dict):
    from pathlib import Path
    Path(path).write_text(json.dumps(bom,indent=2,sort_keys=True),encoding='utf-8')

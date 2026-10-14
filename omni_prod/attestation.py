from __future__ import annotations
from pathlib import Path
import hashlib,json

def sha256_file(path:str|Path)->str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def build_attestation(*,subject_name:str,subject_sha256:str,builder:str,metadata:dict)->dict:
    if len(subject_sha256)!=64: raise ValueError('subject sha256 must be a 64-char digest')
    int(subject_sha256,16)
    return {'_type':'https://in-toto.io/Statement/v1','subject':[{'name':subject_name,'digest':{'sha256':subject_sha256}}],
            'predicateType':'https://omnicreator.ai/attestation/release/v1',
            'predicate':{'builder':builder,'metadata':metadata,'signed':False,'signature_status':'UNSIGNED_LOCAL_ATTESTATION'}}

def write_attestation(path:str|Path,a:dict)->None:
    Path(path).write_text(json.dumps(a,indent=2,sort_keys=True),encoding='utf-8')

from __future__ import annotations
from dataclasses import dataclass
import base64,json,urllib.request,urllib.error
from .media_pipeline import AssetRequest

class MediaGatewayError(RuntimeError): pass

@dataclass(frozen=True)
class MediaEndpoint:
    name:str
    base_url:str
    api_key:str=''
    external:bool=False
    timeout_seconds:int=120

@dataclass(frozen=True)
class GeneratedAsset:
    asset_id:str
    mime_type:str
    data:bytes
    provider:str
    metadata:dict

class HTTPMediaGateway:
    """Provider-neutral media adapter.

    Self-hosted services implement POST /v1/assets/generate and return JSON:
    {content_base64, mime_type, metadata}. Paid/external endpoints are not
    selected by this class automatically; routing policy belongs above it.
    """
    def __init__(self,endpoint:MediaEndpoint): self.endpoint=endpoint
    def generate(self,request:AssetRequest,*,idempotency_key:str|None=None)->GeneratedAsset:
        payload_body={'id':request.id,'kind':request.kind.value,'purpose':request.purpose,'prompt':request.prompt,'required':request.required}
        if idempotency_key: payload_body['idempotency_key']=idempotency_key
        payload=json.dumps(payload_body).encode()
        headers={'content-type':'application/json'}
        if self.endpoint.api_key: headers['authorization']='Bearer '+self.endpoint.api_key
        req=urllib.request.Request(self.endpoint.base_url.rstrip('/')+'/v1/assets/generate',data=payload,headers=headers,method='POST')
        try:
            with urllib.request.urlopen(req,timeout=self.endpoint.timeout_seconds) as r: body=json.loads(r.read().decode())
        except Exception as exc: raise MediaGatewayError(f'{self.endpoint.name} media generation failed: {exc}') from exc
        try:
            data=base64.b64decode(body['content_base64'],validate=True); mime=str(body['mime_type']); meta=dict(body.get('metadata') or {})
        except Exception as exc: raise MediaGatewayError('invalid media provider response') from exc
        if not data or '/' not in mime: raise MediaGatewayError('empty/invalid generated asset')
        return GeneratedAsset(request.id,mime,data,self.endpoint.name,meta)

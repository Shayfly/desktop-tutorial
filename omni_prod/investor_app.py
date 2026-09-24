from __future__ import annotations
from decimal import Decimal
import os
import shutil
import hmac
import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel, Field

from .agent_team import plan_team
from .auth import verify_token, AuthError
from .metrics import MetricsRegistry
from .observability import configure_observability
from .web_security import configure_web_security
from .autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
from .autonomous_core import AutonomousProductEngine
from .benchmark_suite import CASES
from .billing import classify_charge
from .demo_project import demo_spec, create_demo_repository, StaticDemoVerifier
from .design_system import derive_tokens, anti_template_fingerprint
from .game_pipeline import engine_plan
from .integrations import catalog as integration_catalog
from .international_readiness import payload as international_payload
from .i18n import SUPPORTED_LOCALES
from .mobile_pipeline import build_plan as mobile_build_plan
from .native_source import android_project, ios_project, game_project, omni_android_release_project
from .remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor
from .model_runtime_config import ModelRuntimeConfig
from .project_memory import ProjectMemory
from .quality_gate import assess_repository
from .readiness import readiness_payload
from .routed_gateway import ProviderRoute, RoutedModelGateway
from .sandbox import SandboxLimits
from .sandbox_executor import SandboxRepositoryExecutor
from .security_testing import hostile_repository_scan
from .specialist_agents import MultiAgentReviewTeam
from .workspace import ProjectWorkspace
from .unified_engine import UnifiedOmniEngine
from .v26_platform import V26UniversalPlatform
from .v27_platform import V27UniversalPlatform
from .v28_platform import V28Platform
from .integration_center import IntegrationCenter
from .pricing import CostClass, catalog_payload
from .creator_accounts import PostgresAccountService
from .subscription_store import PostgresSubscriptionService
from .db import DatabasePool
from .rights_ip import JURISDICTIONS
from .universal_brain import OmniUniversalBrain
from .brand_clearance import brand_readiness
from .ui_translations import ui_translation_payload
from .stripe_billing import StripeCheckoutClient, StripeSubscriptionWebhookProcessor, StripeBillingError, verify_stripe_signature
from .launch_readiness_v28 import launch_readiness_payload
from .brand_native_clients import android_client, ios_client

app = FastAPI(title='148AI', version='28.0.0')
_metrics=MetricsRegistry()
configure_observability(app,_metrics)
configure_web_security(app,raw_origins=os.getenv('OMNI_ALLOWED_ORIGINS','http://127.0.0.1:8000,http://localhost:8000'),production=os.getenv('OMNI_ENV','development')=='production')

_PUBLIC_PREFIXES=('/api/v26/auth/','/api/v27/auth/','/api/v28/auth/','/api/v28/pricing','/api/v28/brand/readiness','/api/v28/launch/readiness','/api/v28/ui/translations','/api/v28/billing/stripe/webhook','/api/status','/api/international/readiness','/api/integrations','/api/benchmark/catalog','/api/targets/','/api/source/','/api/v28/source/','/api/agent-team','/_omni/metrics')
@app.middleware('http')
async def production_auth(request:Request,call_next):
    if os.getenv('OMNI_ENV','development')=='production' and request.url.path.startswith('/api/') and not any(request.url.path==p or (p.endswith('/') and request.url.path.startswith(p)) for p in _PUBLIC_PREFIXES):
        raw=request.headers.get('authorization','')
        if not raw.startswith('Bearer '):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'authentication required'},status_code=401)
        try:
            claims=verify_token(raw[7:],secret=os.getenv('OMNI_SECRET_KEY',''))
            request.state.auth=claims
        except AuthError:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'invalid authentication'},status_code=401)
    return await call_next(request)
_workspace=ProjectWorkspace()
_memory=ProjectMemory()

def _generated_runtime_secret()->str:
    value=os.getenv('OMNI_GENERATED_APP_TOKEN_SECRET') or os.getenv('OMNI_SECRET_KEY')
    if value: return value
    if os.getenv('OMNI_ENV','development')=='production':
        raise RuntimeError('OMNI_GENERATED_APP_TOKEN_SECRET or OMNI_SECRET_KEY is required in production')
    return 'v25-generated-dev-'+'x'*40

def _control_plane_secret()->str:
    value=os.getenv('OMNI_SECRET_KEY')
    if value: return value
    if os.getenv('OMNI_ENV','development')=='production':
        raise RuntimeError('OMNI_SECRET_KEY is required for creator/control-plane authentication in production')
    return 'v27-control-dev-'+'c'*40

_unified=UnifiedOmniEngine(token_secret=_generated_runtime_secret())
_v26=V26UniversalPlatform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret())
_v27=V27UniversalPlatform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret())
_v28_pool=None
def _build_v28_platform():
    global _v28_pool
    mode=os.getenv('OMNI_CREATOR_PERSISTENCE','memory').strip().lower()
    if mode=='postgres':
        database_url=os.getenv('OMNI_DATABASE_URL','').strip()
        if not database_url:
            raise RuntimeError('OMNI_DATABASE_URL required when OMNI_CREATOR_PERSISTENCE=postgres')
        _v28_pool=DatabasePool(database_url)
        accounts=PostgresAccountService(token_secret=_control_plane_secret(),pool=_v28_pool)
        subscriptions=PostgresSubscriptionService(pool=_v28_pool)
        return V28Platform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret(),account_service=accounts,subscription_service=subscriptions)
    return V28Platform(token_secret=_control_plane_secret(),generated_app_token_secret=_generated_runtime_secret())
_v28=_build_v28_platform()
_integrations_v28=IntegrationCenter()
_stripe_webhooks_v28=StripeSubscriptionWebhookProcessor(_v28.subscriptions)

class PromptRequest(BaseModel):
    prompt: str = Field(min_length=3,max_length=8000)
    project_id: str = Field(default='demo-project',min_length=1,max_length=120)

class ChangeRequest(BaseModel):
    category: str
    estimated_compute_units: int=1

class V25PatchRequest(BaseModel):
    files: list[dict]
    message: str = 'change request'

class RuntimeRegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8,max_length=256)

class RuntimeLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8,max_length=256)

class RuntimeDataRequest(BaseModel):
    payload: dict


class V26AuthRequest(BaseModel):
    email: str = Field(min_length=5,max_length=320)
    password: str = Field(min_length=10,max_length=256)

class V26ProjectCreateRequest(BaseModel):
    title: str = Field(min_length=1,max_length=120)

class V26BuildRequest(BaseModel):
    prompt: str = Field(min_length=3,max_length=12000)

class V26RestoreRequest(BaseModel):
    version_id: str = Field(min_length=1,max_length=160)

class V27BuildRequest(BaseModel):
    prompt: str = Field(min_length=3,max_length=12000)
    target_markets: list[str] = Field(default_factory=lambda:['US','EU','IL'])

class V27RightsEvidenceRequest(BaseModel):
    right_kind: str
    subject: str = Field(min_length=1,max_length=160)
    evidence_type: str = Field(min_length=1,max_length=120)
    scope: str = Field(min_length=1,max_length=500)
    source_reference: str = Field(default='',max_length=1000)

class V27RightsReviewRequest(BaseModel):
    evidence_id: str = Field(min_length=1,max_length=120)
    reviewer_note: str = Field(default='',max_length=1000)

class V27OriginalizeRequest(BaseModel):
    prompt: str | None = Field(default=None,max_length=12000)

class V27CompanySignal(BaseModel):
    kind: str = Field(min_length=1,max_length=80)
    title: str = Field(min_length=1,max_length=300)
    severity: str = Field(default='medium',max_length=20)
    detail: str = Field(default='',max_length=4000)
    source: str = Field(default='system',max_length=120)

class V27CompanyTriageRequest(BaseModel):
    signals: list[V27CompanySignal] = Field(default_factory=list,max_length=200)

class V27CEOBriefRequest(BaseModel):
    signals: list[V27CompanySignal] = Field(default_factory=list,max_length=200)
    metrics: dict = Field(default_factory=dict)
    max_priorities: int = Field(default=7,ge=1,le=20)

class V27ReleaseCouncilRequest(BaseModel):
    gates: dict
    founder_public_launch_approved: bool = False

class V28BrandingRequest(BaseModel):
    visible: bool | None = None
    white_label_name: str | None = Field(default=None,max_length=80)

class V28UsageQuoteRequest(BaseModel):
    cost_class: str = Field(default='standard')
    credits: int = Field(default=1,ge=0,le=100000)
    category: str = Field(default='new_build',max_length=80)
    estimated_provider_cost_usd: str | None = None

class V28PlanAdminRequest(BaseModel):
    user_id: str = Field(min_length=1,max_length=160)
    plan: str = Field(min_length=1,max_length=40)

class V28CheckoutRequest(BaseModel):
    plan: str = Field(min_length=1,max_length=40)


def _repo_summary(repo: dict[str,str]) -> dict:
    return {'file_count':len(repo),'total_chars':sum(len(v) for v in repo.values()),
            'files':[{'path':k,'chars':len(v),'preview':v[:400]} for k,v in sorted(repo.items())]}

@app.get('/',response_class=HTMLResponse)
def home()->str: return _HTML

@app.get('/api/status')
def status()->dict:
    # version is retained for V23 API-client compatibility; product_release is canonical.
    return {
        'product':'148AI','brand_domain':'148ailabs.com','tagline':'Build Anything.','version':'V23 Investor-Grade Prelaunch','product_release':'V24 International Readiness','current_release':'V25 Unified Core','universal_release':'V26 Universal Pro Reviewer Release','rights_release':'V27 Rights & Company OS','launch_candidate':'V28 148AI Launch Candidate',
        'default_cost_mode':'zero-cost/local-first','benchmark_catalog_cases':len(CASES),
        'supported_locales':list(SUPPORTED_LOCALES),
        'capabilities':['prompt-to-spec','autonomous repository generation','acceptance traceability','repair loop',
            'quality/security release gate','local-first multi-model routing','project memory/versioning','teams/RBAC',
            'credits/free-repair policy','integration registry','Android/iOS build contracts','Godot/Unity/Unreal build contracts',
            'PostgreSQL/Redis/S3 production adapters','release integrity/observability/recovery',
            'V10 behavior parity gate','V26 creator accounts/tenant isolation','multimodal creative asset planning','V27 rights/IP provenance and publish gate','one-founder company operating system','148AI plan economics/branding/provenance','generated-app auth/RBAC','hosted deployment isolation','authenticated realtime runtime'],
        'readiness':readiness_payload(),'international':international_payload(),'brand_readiness':brand_readiness(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists()).to_dict(),'launch_readiness':launch_readiness_payload(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists()),
    }

@app.get('/api/international/readiness')
def international_readiness()->dict: return international_payload()

@app.get('/api/integrations')
def integrations()->dict: return {'providers':integration_catalog()}

@app.get('/api/benchmark/catalog')
def benchmark_catalog(limit:int=20)->dict:
    n=max(1,min(limit,200))
    return {'total':len(CASES),'cases':[{'id':x.id,'category':x.category,'difficulty':x.difficulty,'prompt':x.prompt} for x in CASES[:n]]}

@app.get('/api/targets/mobile/{platform}')
def mobile_target(platform:str)->dict:
    try:return mobile_build_plan(platform).to_dict()
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/targets/game/{engine}')
def game_target(engine:str)->dict:
    try:return engine_plan(engine).to_dict()
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/source/mobile/{platform}')
def mobile_source(platform:str, app_name:str='Omni App')->dict:
    if platform.lower()=='android': repo=android_project(app_name=app_name)
    elif platform.lower()=='ios': repo=ios_project(app_name=app_name)
    else: raise HTTPException(400,'platform must be android or ios')
    return {'platform':platform.lower(),'repository':_repo_summary(repo)}

@app.get('/api/source/game/{engine}')
def game_source(engine:str, title:str='Omni Game')->dict:
    try: repo=game_project(engine,title=title)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'engine':engine.lower(),'repository':_repo_summary(repo)}

@app.get('/api/agent-team')
def agent_team(target:str='web',mobile:bool=False,game:bool=False)->dict:
    return plan_team(target=target,has_ui=True,has_mobile=mobile,has_game=game).to_dict()

@app.post('/api/billing/classify')
def billing_classify(req:ChangeRequest)->dict:
    d=classify_charge(category=req.category,estimated_compute_units=req.estimated_compute_units)
    return {'billable':d.billable,'credits':d.credits,'reason':d.reason.value}

@app.post('/api/demo/build')
def demo_build(req:PromptRequest)->dict:
    spec=demo_spec(req.prompt); repo=create_demo_repository(req.prompt,spec)
    report=StaticDemoVerifier().execute(repository=repo,spec=spec)
    quality=assess_repository(spec=spec,repository=repo,minimum_score=75)
    security=hostile_repository_scan(repo)
    tokens=derive_tokens(req.prompt)
    version=_workspace.commit(project_id=req.project_id,repository=repo,message='offline verified demo build')
    _memory.append(project_id=req.project_id,kind='user_intent',text=req.prompt,source_version=version.id)
    _memory.append(project_id=req.project_id,kind='quality',text=f'quality={quality.score} security_pass={security.passed}',source_version=version.id)
    return {
        'mode':'offline-deterministic-demo','status':'ready' if report.passed else 'failed',
        'truth_note':'This route proves product flow, quality/security gating and repository traceability without claiming arbitrary AI generation. /api/live/build requires a configured local model + Docker.',
        'spec':spec.to_dict(),'repository':_repo_summary(repo),
        'verification':{'passed':report.passed,'failures':[f.__dict__ for f in report.failures],'log':report.build_log},
        'quality':quality.to_dict(),'security':security.to_dict(),'design_system':tokens.to_dict(),
        'design_fingerprint':anti_template_fingerprint(tokens),'agent_team':plan_team(target='web').to_dict(),
        'version':{'id':version.id,'checksum':version.checksum},
    }

@app.get('/api/projects/{project_id}/history')
def project_history(project_id:str)->dict:
    return {'project_id':project_id,'versions':[{'id':v.id,'parent_id':v.parent_id,'created_at':v.created_at,'message':v.message,'checksum':v.checksum,'file_count':len(v.files)} for v in _workspace.history(project_id)]}

@app.get('/api/projects/{project_id}/versions/{version_id}/download')
def download_version(project_id:str,version_id:str):
    try: version=_workspace.get(project_id=project_id,version_id=version_id)
    except KeyError as exc: raise HTTPException(404,'version not found') from exc
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        for path,content in version.files: z.writestr(path,content)
    buf.seek(0)
    headers={'Content-Disposition':f'attachment; filename="{project_id}-{version_id}.zip"','X-Omni-Repository-SHA256':version.checksum}
    return StreamingResponse(buf,media_type='application/zip',headers=headers)

@app.get('/api/projects/{project_id}/memory')
def project_memory(project_id:str)->dict:
    return {'project_id':project_id,'context':_memory.context(project_id),'entries':[x.__dict__ for x in _memory.list(project_id)]}


def _live_components():
    if os.getenv('OMNI_ENABLE_LIVE_BUILD')!='1': raise RuntimeError('OMNI_ENABLE_LIVE_BUILD=1 is required')
    cfg=ModelRuntimeConfig.from_env(); fallback_cost=Decimal(os.getenv('OMNI_EXTERNAL_MAX_ESTIMATED_COST_USD_PER_CALL','0.25'))
    gateway=RoutedModelGateway(primary=ProviderRoute(cfg.primary),fallback=tuple(ProviderRoute(ep,fallback_cost) for ep in cfg.fallback),policy=cfg.policy)
    remote_url=os.getenv('OMNI_SANDBOX_RUNNER_URL','').strip()
    if remote_url:
        secret=os.getenv('OMNI_SANDBOX_SHARED_SECRET','')
        executor=RemoteSandboxRepositoryExecutor(RemoteSandboxConfig(remote_url,secret))
    else:
        if not shutil.which('docker'): raise RuntimeError('docker or OMNI_SANDBOX_RUNNER_URL is required for live generated-code execution')
        executor=SandboxRepositoryExecutor(limits=SandboxLimits())
    engine=AutonomousProductEngine(architect=ArchitectAgent(gateway),generator=GeneratorAgent(gateway),repairer=RepairAgent(gateway),
        executor=executor,max_repair_rounds=int(os.getenv('OMNI_MAX_REPAIR_ROUNDS','5')))
    return engine,gateway

def _live_engine()->AutonomousProductEngine:
    return _live_components()[0]

@app.post('/api/live/build')
def live_build(req:PromptRequest)->dict:
    try:
        engine,gateway=_live_components()
        context=_memory.context(req.project_id,max_chars=4000) if _memory.list(req.project_id) else ''
        effective=req.prompt if not context else req.prompt+'\n\nExisting project memory (preserve unless the new request conflicts):\n'+context
        result=engine.build(effective)
    except Exception as exc: raise HTTPException(status_code=503,detail=str(exc)[:1000]) from exc
    quality=assess_repository(spec=result.spec,repository=result.repository,minimum_score=int(os.getenv('OMNI_MIN_QUALITY_SCORE','80')))
    security=hostile_repository_scan(result.repository)
    reviews=[]
    if os.getenv('OMNI_ENABLE_SPECIALIST_REVIEW','1')=='1' and result.status=='ready':
        try:
            reviews=list(MultiAgentReviewTeam(gateway).review(spec=result.spec.to_dict(),repository_summary=_repo_summary(result.repository)))
        except Exception as exc:
            reviews=[]
            _memory.append(project_id=req.project_id,kind='review_warning',text='specialist review unavailable: '+str(exc)[:500])
    review_blocked=any(x.severity in {'blocker','high'} for x in reviews)
    version=_workspace.commit(project_id=req.project_id,repository=result.repository,message='live autonomous build')
    _memory.append(project_id=req.project_id,kind='user_intent',text=req.prompt,source_version=version.id)
    _memory.append(project_id=req.project_id,kind='build_result',text=f'status={result.status} quality={quality.score} security={security.passed} reviews={len(reviews)}',source_version=version.id)
    return {'mode':'live-autonomous','status':result.status,'release_ready':result.status=='ready' and quality.passed and security.passed and not review_blocked,
        'repair_rounds':result.repair_rounds,'spec':result.spec.to_dict(),'repository':_repo_summary(result.repository),
        'verification':{'passed':result.report.passed,'failures':[f.__dict__ for f in result.report.failures],'log':result.report.build_log[-4000:]},
        'quality':quality.to_dict(),'security':security.to_dict(),'specialist_reviews':[x.__dict__ for x in reviews],
        'model_route_events':[x.__dict__ for x in gateway.events],
        'version':{'id':version.id,'checksum':version.checksum}}




def _v26_bearer(request:Request)->str:
    raw=request.headers.get('authorization','')
    if not raw.startswith('Bearer '): raise HTTPException(401,'authentication required')
    return raw[7:]

@app.post('/api/v26/auth/register')
def v26_register(req:V26AuthRequest)->dict:
    try: return _v26.register(email=req.email,password=req.password)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v26/auth/login')
def v26_login(req:V26AuthRequest)->dict:
    try: return _v26.login(email=req.email,password=req.password)
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.get('/api/v26/me')
def v26_me(request:Request)->dict:
    try: a=_v26.account(_v26_bearer(request))
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'id':a.id,'email':a.email,'created_at':a.created_at}

@app.post('/api/v26/projects')
def v26_create_project(req:V26ProjectCreateRequest,request:Request)->dict:
    try:return _v26.create_project(token=_v26_bearer(request),title=req.title)
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/v26/projects')
def v26_projects(request:Request)->dict:
    try:return {'projects':_v26.list_projects(token=_v26_bearer(request))}
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.post('/api/v26/projects/{project_id}/build')
def v26_build(project_id:str,req:V26BuildRequest,request:Request)->dict:
    try:return _v26.build(token=_v26_bearer(request),project_id=project_id,prompt=req.prompt)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/v26/projects/{project_id}/history')
def v26_history(project_id:str,request:Request)->dict:
    try:return {'project_id':project_id,'versions':_v26.history(token=_v26_bearer(request),project_id=project_id)}
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc

@app.post('/api/v26/projects/{project_id}/patch')
def v26_patch(project_id:str,req:V25PatchRequest,request:Request)->dict:
    try:return _v26.patch(token=_v26_bearer(request),project_id=project_id,payload={'files':req.files},message=req.message)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except (KeyError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v26/projects/{project_id}/restore')
def v26_restore(project_id:str,req:V26RestoreRequest,request:Request)->dict:
    try:return _v26.restore(token=_v26_bearer(request),project_id=project_id,version_id=req.version_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'version not found') from exc

@app.get('/api/v26/projects/{project_id}/export')
def v26_export(project_id:str,request:Request,version_id:str|None=None):
    try:payload=_v26.export(token=_v26_bearer(request),project_id=project_id,version_id=version_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc
    return Response(payload,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{project_id}.zip"'})

@app.post('/api/v26/projects/{project_id}/promote')
def v26_promote(project_id:str,request:Request,version_id:str|None=None)->dict:
    try:return _v26.promote(token=_v26_bearer(request),project_id=project_id,version_id=version_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc

@app.post('/api/v26/brain/plan')
def v26_brain_plan(req:V26BuildRequest,request:Request)->dict:
    try:_v26.account(_v26_bearer(request))
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return OmniUniversalBrain().decide(req.prompt).to_dict()


@app.post('/api/v26/projects/{project_id}/live-build')
def v26_live_build(project_id:str,req:V26BuildRequest,request:Request)->dict:
    token=_v26_bearer(request)
    try:
        account,key=_v26.resolve_project_key(token=token,project_id=project_id)
        decision=_v26.brain.decide(req.prompt)
        engine,gateway=_live_components()
        result=engine.build(req.prompt)
        quality=assess_repository(spec=result.spec,repository=result.repository,minimum_score=int(os.getenv('OMNI_MIN_QUALITY_SCORE','80')))
        security=hostile_repository_scan(result.repository)
        repo=dict(result.repository); repo.update(_v26.brain.creative.repository_files(decision.creative))
        version=_v26.engine.workspace.commit(project_id=key,repository=repo,message='V26 live autonomous build')
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
    return {'mode':'v26-live-autonomous','status':result.status,'release_ready':result.status=='ready' and quality.passed and security.passed,
            'project_id':project_id,'owner_id':account.id,'version_id':version.id,'checksum':version.checksum,'file_count':len(repo),
            'repair_rounds':result.repair_rounds,'brain':decision.to_dict(),'quality':quality.to_dict(),'security':security.to_dict(),
            'model_route_events':[x.__dict__ for x in gateway.events],
            'truth':'This route uses a configured local/self-hosted model and sandbox. If those services are absent it fails closed with 503.'}

@app.get('/api/v26/capabilities')
def v26_capabilities()->dict:
    return {'release':'V26 Universal Pro','creator_security':['signup/login','PBKDF2 password hashing','signed session tokens','owner-scoped project IDs','cross-user denial'],
            'creation':['web','android-source','ios-source','godot','unity','unreal','repository versioning','patch/restore/export/deploy'],
            'creative':['image','icon','audio','music','voice','video','3D model','PBR texture'],
            'brain':['local-first model router','specialist agents','deterministic coverage planner','acceptance/quality/security gates'],
            'truth':'Media kinds are planned contracts until a real configured provider materializes files.'}

@app.get('/hosted/v26/{deployment_id}',response_class=HTMLResponse)
def v26_hosted_page(deployment_id:str)->str:
    try:
        snap=_v26.engine.deployment(deployment_id); repo=_v26.engine.deployed_repository(deployment_id)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    return repo.get('index.html',f'<h1>{snap.project_id}</h1>')

@app.post('/runtime/v26/{deployment_id}/register')
def v26_runtime_register(deployment_id:str,req:RuntimeRegisterRequest)->dict:
    try: role,issued=_v26.engine.runtime(deployment_id).register(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'role':role,'token':issued}

@app.post('/runtime/v26/{deployment_id}/login')
def v26_runtime_login(deployment_id:str,req:RuntimeLoginRequest)->dict:
    try: role,issued=_v26.engine.runtime(deployment_id).login(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'role':role,'token':issued}

@app.get('/runtime/v26/{deployment_id}/data/{collection}')
def v26_runtime_list(deployment_id:str,collection:str,request:Request)->dict:
    token=_runtime_bearer(request)
    try:return {'items':_v26.engine.runtime(deployment_id).list(token=token,collection=collection)}
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.post('/runtime/v26/{deployment_id}/data/{collection}')
def v26_runtime_create(deployment_id:str,collection:str,req:RuntimeDataRequest,request:Request)->dict:
    token=_runtime_bearer(request)
    try:return _v26.engine.runtime(deployment_id).create(token=token,collection=collection,payload=req.payload)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.websocket('/runtime/v26/{deployment_id}/ws')
async def v26_runtime_ws(websocket:WebSocket,deployment_id:str,token:str=''):
    try:claims=_v26.engine.runtime(deployment_id).websocket_authorize(token)
    except Exception:
        await websocket.close(code=4401); return
    await websocket.accept(); await websocket.send_json({'authenticated':True,'role':claims.role,'deployment_id':deployment_id})
    try:
        while True:
            payload=await websocket.receive_json(); await websocket.send_json({'echo':payload,'deployment_id':deployment_id})
    except WebSocketDisconnect:return


@app.get('/api/v25/parity')
def v25_parity()->dict:
    return {
        'baseline':'Omni Creator V10 validation behavior',
        'release':'V25 Unified Core',
        'gates':['generated-app-auth-rbac','hosted-deployment-isolation','authenticated-websocket',
                 'maps-realtime-payments-planning','android-studio-source','godot-4-3d-source',
                 'safe-repository-patching','omni-android-aab-ci','version-isolation'],
    }

@app.post('/api/v25/build')
def v25_build(req:PromptRequest)->dict:
    result=_unified.build(project_id=req.project_id,prompt=req.prompt)
    return result.to_dict()

@app.get('/api/v25/projects/{project_id}/export')
def v25_export(project_id:str,version_id:str|None=None):
    try: payload=_unified.export_zip(project_id=project_id,version_id=version_id)
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc
    return Response(payload,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{project_id}.zip"'})

@app.post('/api/v25/projects/{project_id}/patch')
def v25_patch(project_id:str,req:V25PatchRequest)->dict:
    try: version=_unified.patch(project_id=project_id,payload={'files':req.files},message=req.message)
    except KeyError as exc: raise HTTPException(404,'project not found') from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'project_id':project_id,'version_id':version.id,'parent_id':version.parent_id,'checksum':version.checksum}

@app.post('/api/v25/projects/{project_id}/promote')
def v25_promote(project_id:str,version_id:str|None=None)->dict:
    try: snap=_unified.promote(project_id=project_id,version_id=version_id)
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc
    return snap.__dict__

@app.get('/api/v25/source/omni-android')
def v25_omni_android()->dict:
    repo=omni_android_release_project()
    return {'status':'SOURCE_READY','repository':_repo_summary(repo)}

@app.get('/hosted/v25/{deployment_id}',response_class=HTMLResponse)
def v25_hosted_page(deployment_id:str)->str:
    try:
        snap=_unified.deployment(deployment_id)
        repo=_unified.deployed_repository(deployment_id)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    return repo.get('index.html',f'<h1>{snap.project_id}</h1>')


def _runtime_bearer(request:Request)->str:
    raw=request.headers.get('authorization','')
    if not raw.startswith('Bearer '): raise HTTPException(401,'authentication required')
    return raw[7:]

@app.post('/runtime/v25/{deployment_id}/register')
def v25_runtime_register(deployment_id:str,req:RuntimeRegisterRequest)->dict:
    try: role,issued=_unified.runtime(deployment_id).register(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'role':role,'token':issued}

@app.post('/runtime/v25/{deployment_id}/login')
def v25_runtime_login(deployment_id:str,req:RuntimeLoginRequest)->dict:
    try: role,issued=_unified.runtime(deployment_id).login(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'role':role,'token':issued}

@app.get('/runtime/v25/{deployment_id}/data/{collection}')
def v25_runtime_list(deployment_id:str,collection:str,request:Request)->dict:
    token=_runtime_bearer(request)
    try: items=_unified.runtime(deployment_id).list(token=token,collection=collection)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'items':items}

@app.post('/runtime/v25/{deployment_id}/data/{collection}')
def v25_runtime_create(deployment_id:str,collection:str,req:RuntimeDataRequest,request:Request)->dict:
    token=_runtime_bearer(request)
    try: return _unified.runtime(deployment_id).create(token=token,collection=collection,payload=req.payload)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.websocket('/runtime/v25/{deployment_id}/ws')
async def v25_runtime_ws(websocket:WebSocket,deployment_id:str,token:str=''):
    try: claims=_unified.runtime(deployment_id).websocket_authorize(token)
    except Exception:
        await websocket.close(code=4401); return
    await websocket.accept()
    await websocket.send_json({'authenticated':True,'role':claims.role,'deployment_id':deployment_id})
    try:
        while True:
            payload=await websocket.receive_json()
            await websocket.send_json({'echo':payload,'deployment_id':deployment_id})
    except WebSocketDisconnect:
        return

_ASSET_DIR=Path(__file__).resolve().parent/'assets'
_HTML=(_ASSET_DIR/'index.html').read_text(encoding='utf-8')

@app.get('/assets/app.css')
def asset_css(): return Response((_ASSET_DIR/'app.css').read_text(encoding='utf-8'),media_type='text/css')

@app.get('/assets/app.js')
def asset_js(): return Response((_ASSET_DIR/'app.js').read_text(encoding='utf-8'),media_type='application/javascript')

@app.get('/manifest.webmanifest')
def pwa_manifest(): return Response((_ASSET_DIR/'manifest.webmanifest').read_text(encoding='utf-8'),media_type='application/manifest+json',headers={'Cache-Control':'public,max-age=3600'})

@app.get('/sw.js')
def service_worker(): return Response((_ASSET_DIR/'sw.js').read_text(encoding='utf-8'),media_type='application/javascript',headers={'Cache-Control':'no-cache','Service-Worker-Allowed':'/'})

# ---- V27 Rights/IP + one-founder Company OS ---------------------------------
def _v27_bearer(request:Request)->str:
    return _v26_bearer(request)

@app.post('/api/v27/auth/register')
def v27_register(req:V26AuthRequest)->dict:
    try: return _v27.register(email=req.email,password=req.password)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v27/auth/login')
def v27_login(req:V26AuthRequest)->dict:
    try: return _v27.login(email=req.email,password=req.password)
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.get('/api/v27/me')
def v27_me(request:Request)->dict:
    try: a=_v27.account(_v27_bearer(request))
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'id':a.id,'email':a.email,'created_at':a.created_at}

@app.post('/api/v27/projects')
def v27_create_project(req:V26ProjectCreateRequest,request:Request)->dict:
    try:return _v27.create_project(token=_v27_bearer(request),title=req.title)
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/v27/projects')
def v27_projects(request:Request)->dict:
    try:return {'projects':_v27.list_projects(token=_v27_bearer(request))}
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/build')
def v27_build(project_id:str,req:V27BuildRequest,request:Request)->dict:
    try:return _v27.build(token=_v27_bearer(request),project_id=project_id,prompt=req.prompt,target_markets=tuple(req.target_markets))
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.get('/api/v27/projects/{project_id}/history')
def v27_history(project_id:str,request:Request)->dict:
    try:return {'project_id':project_id,'versions':_v27.history(token=_v27_bearer(request),project_id=project_id)}
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/patch')
def v27_patch(project_id:str,req:V25PatchRequest,request:Request)->dict:
    try:return _v27.patch(token=_v27_bearer(request),project_id=project_id,payload={'files':req.files},message=req.message)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except (KeyError,ValueError) as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/restore')
def v27_restore(project_id:str,req:V26RestoreRequest,request:Request)->dict:
    try:return _v27.restore(token=_v27_bearer(request),project_id=project_id,version_id=req.version_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'version not found') from exc

@app.get('/api/v27/projects/{project_id}/export')
def v27_export(project_id:str,request:Request,version_id:str|None=None):
    try:payload=_v27.export(token=_v27_bearer(request),project_id=project_id,version_id=version_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc
    return Response(payload,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{project_id}.zip"'})

@app.get('/api/v27/projects/{project_id}/rights')
def v27_rights(project_id:str,request:Request)->dict:
    try:return _v27.rights_status(token=_v27_bearer(request),project_id=project_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/rights/evidence')
def v27_rights_evidence(project_id:str,req:V27RightsEvidenceRequest,request:Request)->dict:
    try:
        return _v27.add_rights_evidence(
            token=_v27_bearer(request),project_id=project_id,right_kind=req.right_kind,
            subject=req.subject,evidence_type=req.evidence_type,scope=req.scope,
            source_reference=req.source_reference,verified=False,
        )
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/rights/review')
def v27_rights_review(project_id:str,req:V27RightsReviewRequest,request:Request)->dict:
    expected=os.getenv('OMNI_RIGHTS_REVIEW_KEY','')
    provided=request.headers.get('x-omni-rights-review-key','')
    if not expected or not provided or not hmac.compare_digest(expected,provided):
        raise HTTPException(403,'rights reviewer authorization required')
    try:return _v27.verify_rights_evidence(token=_v27_bearer(request),project_id=project_id,evidence_id=req.evidence_id)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'rights evidence not found') from exc

@app.post('/api/v27/projects/{project_id}/rights/original-alternative')
def v27_original_alternative(project_id:str,req:V27OriginalizeRequest,request:Request)->dict:
    try:return _v27.original_alternative(token=_v27_bearer(request),project_id=project_id,prompt=req.prompt)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc

@app.post('/api/v27/projects/{project_id}/promote')
def v27_promote(project_id:str,request:Request,version_id:str|None=None)->dict:
    try:return _v27.promote(token=_v27_bearer(request),project_id=project_id,version_id=version_id)
    except PermissionError as exc: raise HTTPException(409,str(exc)) from exc
    except KeyError as exc: raise HTTPException(404,'project/version not found') from exc

@app.post('/api/v27/brain/plan')
def v27_brain_plan(req:V27BuildRequest,request:Request)->dict:
    try:_v27.account(_v27_bearer(request))
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return _v27.brain.decide(req.prompt,target_markets=tuple(req.target_markets)).to_dict()

@app.get('/api/v27/rights/jurisdictions')
def v27_jurisdictions()->dict:
    return {'profiles':{k:v.to_dict() for k,v in JURISDICTIONS.items()},'truth':'Profiles are a maintained risk-policy baseline, not exhaustive legal advice.'}

@app.get('/api/v27/company-os')
def v27_company_os()->dict:
    return _v27.company_operating_system()

@app.get('/api/v27/company-os/departments/{department_id}')
def v27_company_department(department_id:str)->dict:
    try:return _v27.company_os.department(department_id)
    except KeyError as exc: raise HTTPException(404,'department not found') from exc

@app.post('/api/v27/company-os/triage')
def v27_company_triage(req:V27CompanyTriageRequest)->dict:
    return {'tasks':_v27.company_os.triage([x.model_dump() for x in req.signals])}

@app.post('/api/v27/company-os/ceo-brief')
def v27_company_ceo_brief(req:V27CEOBriefRequest)->dict:
    return _v27.company_os.ceo_brief(signals=[x.model_dump() for x in req.signals],metrics=req.metrics,max_priorities=req.max_priorities)

@app.post('/api/v27/company-os/release-council/evaluate')
def v27_release_council_evaluate(req:V27ReleaseCouncilRequest)->dict:
    return _v27.company_os.evaluate_release(req.gates,founder_public_launch_approved=req.founder_public_launch_approved)

@app.post('/api/v27/projects/{project_id}/live-build')
def v27_live_build(project_id:str,req:V27BuildRequest,request:Request)->dict:
    token=_v27_bearer(request)
    try:
        account,key=_v27.resolve_project_key(token=token,project_id=project_id)
        decision=_v27.brain.decide(req.prompt,target_markets=tuple(req.target_markets))
        evidence=_v27._evidence_for(key)
        assessment=_v27.rights.assess(req.prompt,target_markets=tuple(req.target_markets),evidence=evidence,
            synthetic_person_media=bool(decision.rights.required_disclosures))
        engine,gateway=_live_components()
        result=engine.build(req.prompt)
        quality=assess_repository(spec=result.spec,repository=result.repository,minimum_score=int(os.getenv('OMNI_MIN_QUALITY_SCORE','80')))
        security=hostile_repository_scan(result.repository)
        repo=dict(result.repository)
        repo.update(_v27.brain.creative.repository_files(decision.creative))
        repo.update(_v27.rights.repository_files(assessment,original_prompt=req.prompt))
        version=_v27.engine.workspace.commit(project_id=key,repository=repo,message='V27 live autonomous build + rights manifest')
        _v27._rights_assessment[key]=assessment; _v27._rights_prompt[key]=req.prompt; _v27._rights_markets[key]=tuple(req.target_markets)
    except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
    except Exception as exc: raise HTTPException(503,str(exc)[:1000]) from exc
    return {'mode':'v27-live-autonomous','status':result.status,
            'release_ready':result.status=='ready' and quality.passed and security.passed and assessment.publish_allowed,
            'project_id':project_id,'owner_id':account.id,'version_id':version.id,'checksum':version.checksum,'file_count':len(repo),
            'repair_rounds':result.repair_rounds,'brain':decision.to_dict(),'rights':assessment.to_dict(),
            'quality':quality.to_dict(),'security':security.to_dict(),'model_route_events':[x.__dict__ for x in gateway.events],
            'truth':'Live generation requires configured local/self-hosted model + sandbox and fails closed when absent. Rights gate remains independent of model output.'}

@app.get('/hosted/v27/{deployment_id}',response_class=HTMLResponse)
def v27_hosted_page(deployment_id:str)->str:
    try:
        snap=_v27.engine.deployment(deployment_id); repo=_v27.engine.deployed_repository(deployment_id)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    return repo.get('index.html',f'<h1>{snap.project_id}</h1>')

@app.post('/runtime/v27/{deployment_id}/register')
def v27_runtime_register(deployment_id:str,req:RuntimeRegisterRequest)->dict:
    try: role,issued=_v27.engine.runtime(deployment_id).register(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    return {'role':role,'token':issued}

@app.post('/runtime/v27/{deployment_id}/login')
def v27_runtime_login(deployment_id:str,req:RuntimeLoginRequest)->dict:
    try: role,issued=_v27.engine.runtime(deployment_id).login(email=req.email,credential=req.password)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc
    return {'role':role,'token':issued}

@app.get('/runtime/v27/{deployment_id}/data/{collection}')
def v27_runtime_list(deployment_id:str,collection:str,request:Request)->dict:
    token=_runtime_bearer(request)
    try:return {'items':_v27.engine.runtime(deployment_id).list(token=token,collection=collection)}
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.post('/runtime/v27/{deployment_id}/data/{collection}')
def v27_runtime_create(deployment_id:str,collection:str,req:RuntimeDataRequest,request:Request)->dict:
    token=_runtime_bearer(request)
    try:return _v27.engine.runtime(deployment_id).create(token=token,collection=collection,payload=req.payload)
    except KeyError as exc: raise HTTPException(404,'deployment not found') from exc
    except PermissionError as exc: raise HTTPException(401,str(exc)) from exc

@app.websocket('/runtime/v27/{deployment_id}/ws')
async def v27_runtime_ws(websocket:WebSocket,deployment_id:str,token:str=''):
    try:claims=_v27.engine.runtime(deployment_id).websocket_authorize(token)
    except Exception:
        await websocket.close(code=4401); return
    await websocket.accept(); await websocket.send_json({'authenticated':True,'role':claims.role,'deployment_id':deployment_id})
    try:
        while True:
            payload=await websocket.receive_json(); await websocket.send_json({'echo':payload,'deployment_id':deployment_id})
    except WebSocketDisconnect:return

# ---- V28 148AI brand, plan economics, integrations -------------------------
@app.get('/api/v28/brand/readiness')
def v28_brand_readiness() -> dict:
    return brand_readiness(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists()).to_dict()

@app.get('/api/v28/launch/readiness')
def v28_launch_readiness() -> dict:
    return launch_readiness_payload(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists())

@app.get('/api/v28/source/client/{platform}')
def v28_brand_client_source(platform: str) -> dict:
    p=platform.lower()
    if p=='android': repo=android_client()
    elif p=='ios': repo=ios_client()
    else: raise HTTPException(400,'platform must be android or ios')
    return {'brand':'148AI','platform':p,'repository':_repo_summary(repo),'truth':'Source-ready only. Signed store binaries require external signing credentials.'}

@app.get('/api/v28/ui/translations')
def v28_ui_translations() -> dict:
    return ui_translation_payload()

def _v28_bearer(request: Request) -> str:
    return _v26_bearer(request)

@app.get('/api/v28/pricing')
def v28_pricing() -> dict:
    return _v28.pricing()

@app.post('/api/v28/billing/checkout')
def v28_billing_checkout(req: V28CheckoutRequest, request: Request) -> dict:
    try:
        token = _v28_bearer(request)
        account = _v28.account(token)
        session = StripeCheckoutClient().create_subscription(user_id=account.id, email=account.email, plan=req.plan)
        return {'checkout_session_id': session.id, 'url': session.url, 'plan': session.plan, 'provider': 'stripe'}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except (PermissionError, StripeBillingError) as exc:
        code = 401 if isinstance(exc, PermissionError) else 503
        raise HTTPException(code, str(exc)) from exc

@app.post('/api/v28/billing/stripe/webhook')
async def v28_stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get('stripe-signature', '')
    secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
    try:
        event = verify_stripe_signature(payload, signature, secret)
        return _stripe_webhooks_v28.process(event)
    except StripeBillingError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/auth/register')
def v28_register(req: V26AuthRequest) -> dict:
    try:
        return _v28.register(email=req.email, password=req.password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/auth/login')
def v28_login(req: V26AuthRequest) -> dict:
    try:
        payload = _v28.login(email=req.email, password=req.password)
        payload['subscription'] = _v28.subscription(token=payload['token'])
        return payload
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.get('/api/v28/me')
def v28_me(request: Request) -> dict:
    try:
        token = _v28_bearer(request)
        a = _v28.account(token)
        return {'id': a.id, 'email': a.email, 'created_at': a.created_at, 'subscription': _v28.subscription(token=token)}
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.get('/api/v28/me/subscription')
def v28_subscription(request: Request) -> dict:
    try:
        return _v28.subscription(token=_v28_bearer(request))
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.post('/api/v28/admin/subscription')
def v28_admin_subscription(req: V28PlanAdminRequest, request: Request) -> dict:
    expected = os.getenv('OMNI_BILLING_ADMIN_KEY', '')
    provided = request.headers.get('x-148ai-billing-admin-key', '')
    if not expected or not provided or not hmac.compare_digest(expected, provided):
        raise HTTPException(403, 'billing admin authorization required')
    try:
        return _v28.assign_plan_admin(user_id=req.user_id, plan=req.plan)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/projects')
def v28_create_project(req: V26ProjectCreateRequest, request: Request) -> dict:
    try:
        token = _v28_bearer(request)
        account = _v28.account(token)
        plan = _v28.subscriptions.plan_for(account.id)
        current = _v28.list_projects(token=token)
        if plan.max_projects is not None and len(current) >= plan.max_projects:
            raise HTTPException(402, f'{plan.name} project limit reached')
        return _v28.create_project(token=token, title=req.title)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.get('/api/v28/projects')
def v28_projects(request: Request) -> dict:
    try:
        return {'projects': _v28.list_projects(token=_v28_bearer(request))}
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/build')
def v28_build(project_id: str, req: V27BuildRequest, request: Request) -> dict:
    try:
        return _v28.build(token=_v28_bearer(request), project_id=project_id, prompt=req.prompt, target_markets=tuple(req.target_markets))
    except PermissionError as exc:
        raise HTTPException(402, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.get('/api/v28/projects/{project_id}/history')
def v28_history(project_id: str, request: Request) -> dict:
    try:
        return {'project_id': project_id, 'versions': _v28.history(token=_v28_bearer(request), project_id=project_id)}
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/patch')
def v28_patch(project_id: str, req: V25PatchRequest, request: Request) -> dict:
    try:
        return _v28.patch(token=_v28_bearer(request), project_id=project_id, payload={'files': req.files}, message=req.message)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/restore')
def v28_restore(project_id: str, req: V26RestoreRequest, request: Request) -> dict:
    try:
        return _v28.restore(token=_v28_bearer(request), project_id=project_id, version_id=req.version_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'version not found') from exc

@app.get('/api/v28/projects/{project_id}/export')
def v28_export(project_id: str, request: Request, version_id: str | None = None):
    try:
        payload = _v28.export(token=_v28_bearer(request), project_id=project_id, version_id=version_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'project/version not found') from exc
    return Response(payload, media_type='application/zip', headers={'Content-Disposition': f'attachment; filename="{project_id}-148ai.zip"'})

@app.get('/api/v28/projects/{project_id}/rights')
def v28_rights(project_id: str, request: Request) -> dict:
    try:
        return _v28.rights_status(token=_v28_bearer(request), project_id=project_id)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/rights/original-alternative')
def v28_original_alternative(project_id: str, req: V27OriginalizeRequest, request: Request) -> dict:
    try:
        return _v28.original_alternative(token=_v28_bearer(request), project_id=project_id, prompt=req.prompt)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/branding')
def v28_branding(project_id: str, req: V28BrandingRequest, request: Request) -> dict:
    try:
        return _v28.set_project_branding(token=_v28_bearer(request), project_id=project_id, visible=req.visible, white_label_name=req.white_label_name)
    except PermissionError as exc:
        raise HTTPException(402, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/usage/quote')
def v28_usage_quote(project_id: str, req: V28UsageQuoteRequest, request: Request) -> dict:
    try:
        d = _v28.authorize_live_usage(token=_v28_bearer(request), project_id=project_id, cost_class=req.cost_class, credits=req.credits,
            category=req.category, estimated_cost_usd=req.estimated_provider_cost_usd)
        return d.__dict__
    except (ValueError, PermissionError) as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/api/v28/projects/{project_id}/promote')
def v28_promote(project_id: str, request: Request, version_id: str | None = None) -> dict:
    try:
        return _v28.promote(token=_v28_bearer(request), project_id=project_id, version_id=version_id)
    except PermissionError as exc:
        raise HTTPException(409, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, 'project/version not found') from exc

@app.get('/api/v28/integrations')
def v28_integrations(request: Request) -> dict:
    try:
        _v28.account(_v28_bearer(request))
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    return {'integrations': _integrations_v28.catalog(), 'public_launch_blockers': _integrations_v28.blockers(),
            'truth': 'configured means secret/config presence only; live_verified remains false until a harmless provider check succeeds'}

@app.get('/api/v28/company-os')
def v28_company_os(request: Request) -> dict:
    try:
        _v28.account(_v28_bearer(request))
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    payload = _v28.company_operating_system()
    payload['brand'] = {'name': '148AI', 'domain': '148ailabs.com', 'tagline': 'Build Anything.'}
    payload['pricing'] = _v28.pricing()
    payload['brand_readiness'] = brand_readiness(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists()).to_dict()
    payload['launch_readiness'] = launch_readiness_payload(logo_pack_present=(_ASSET_DIR/'brand'/'148ai-logo-128.png').exists())
    return payload

@app.post('/api/v28/projects/{project_id}/live-build')
def v28_live_build(project_id: str, req: V27BuildRequest, request: Request) -> dict:
    token = _v28_bearer(request)
    usage_decision = None
    try:
        account, key = _v28.resolve_project_key(token=token, project_id=project_id)
        brain = _v28.brain.decide(req.prompt, target_markets=tuple(req.target_markets))
        kinds = {x.kind.value for x in brain.creative.requests}
        if {'video', 'model3d', 'music'} & kinds:
            cost_class, credits = CostClass.HEAVY, 400
        elif {'image', 'audio', 'voice', 'texture'} & kinds:
            cost_class, credits = CostClass.ADVANCED, 140
        else:
            cost_class, credits = CostClass.STANDARD, 60
        usage_decision = _v28.authorize_live_usage(token=token, project_id=project_id, cost_class=cost_class.value, credits=credits)
        if not usage_decision.allowed:
            raise HTTPException(402, usage_decision.reason)
        evidence = _v28._evidence_for(key)
        rights = _v28.rights.assess(req.prompt, target_markets=tuple(req.target_markets), evidence=evidence,
            synthetic_person_media=bool(brain.rights.required_disclosures))
        engine, gateway = _live_components()
        result = engine.build(req.prompt)
        quality = assess_repository(spec=result.spec, repository=result.repository, minimum_score=int(os.getenv('OMNI_MIN_QUALITY_SCORE', '80')))
        security = hostile_repository_scan(result.repository)
        repo = dict(result.repository)
        repo.update(_v28.brain.creative.repository_files(brain.creative))
        repo.update(_v28.rights.repository_files(rights, original_prompt=req.prompt))
        plan = _v28.subscriptions.plan_for(account.id)
        repo = _v28.branding.decorate_repository(repo, plan=plan.code, project_id=project_id,
            requested_visible=_v28._project_brand_visible.get(key), white_label_name=_v28._project_white_label.get(key))
        version = _v28.engine.workspace.commit(project_id=key, repository=repo, message='V28 148AI live autonomous build')
        _v28._rights_assessment[key] = rights; _v28._rights_prompt[key] = req.prompt; _v28._rights_markets[key] = tuple(req.target_markets)
        usage = _v28.consume_live_usage(token=token, project_id=project_id, decision=usage_decision)
    except HTTPException:
        raise
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, str(exc)[:1000]) from exc
    return {
        'mode': '148ai-v28-live-autonomous', 'status': result.status,
        'release_ready': result.status == 'ready' and quality.passed and security.passed and rights.publish_allowed,
        'project_id': project_id, 'owner_id': account.id, 'version_id': version.id, 'checksum': version.checksum, 'file_count': len(repo),
        'repair_rounds': result.repair_rounds, 'brain': brain.to_dict(), 'rights': rights.to_dict(), 'quality': quality.to_dict(),
        'security': security.to_dict(), 'usage': usage, 'model_route_events': [x.__dict__ for x in gateway.events],
        'truth': 'Requires configured model + sandbox and fails closed if absent. Provider usage is pre-authorized by plan budget.'
    }

@app.get('/hosted/v28/{deployment_id}', response_class=HTMLResponse)
def v28_hosted_page(deployment_id: str) -> str:
    try:
        snap = _v28.engine.deployment(deployment_id); repo = _v28.engine.deployed_repository(deployment_id)
    except KeyError as exc:
        raise HTTPException(404, 'deployment not found') from exc
    return repo.get('index.html', f'<h1>{snap.project_id}</h1>')

@app.post('/runtime/v28/{deployment_id}/register')
def v28_runtime_register(deployment_id: str, req: RuntimeRegisterRequest) -> dict:
    try:
        role, issued = _v28.engine.runtime(deployment_id).register(email=req.email, credential=req.password)
    except KeyError as exc:
        raise HTTPException(404, 'deployment not found') from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {'role': role, 'token': issued}

@app.post('/runtime/v28/{deployment_id}/login')
def v28_runtime_login(deployment_id: str, req: RuntimeLoginRequest) -> dict:
    try:
        role, issued = _v28.engine.runtime(deployment_id).login(email=req.email, credential=req.password)
    except KeyError as exc:
        raise HTTPException(404, 'deployment not found') from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    return {'role': role, 'token': issued}

@app.get('/runtime/v28/{deployment_id}/data/{collection}')
def v28_runtime_list(deployment_id: str, collection: str, request: Request) -> dict:
    token = _runtime_bearer(request)
    try:
        return {'items': _v28.engine.runtime(deployment_id).list(token=token, collection=collection)}
    except KeyError as exc:
        raise HTTPException(404, 'deployment not found') from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.post('/runtime/v28/{deployment_id}/data/{collection}')
def v28_runtime_create(deployment_id: str, collection: str, req: RuntimeDataRequest, request: Request) -> dict:
    token = _runtime_bearer(request)
    try:
        return _v28.engine.runtime(deployment_id).create(token=token, collection=collection, payload=req.payload)
    except KeyError as exc:
        raise HTTPException(404, 'deployment not found') from exc
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc

@app.websocket('/runtime/v28/{deployment_id}/ws')
async def v28_runtime_ws(websocket: WebSocket, deployment_id: str, token: str = ''):
    try:
        claims = _v28.engine.runtime(deployment_id).websocket_authorize(token)
    except Exception:
        await websocket.close(code=4401); return
    await websocket.accept(); await websocket.send_json({'authenticated': True, 'role': claims.role, 'deployment_id': deployment_id, 'brand': '148AI'})
    try:
        while True:
            payload = await websocket.receive_json(); await websocket.send_json({'echo': payload, 'deployment_id': deployment_id})
    except WebSocketDisconnect:
        return

# Public brand assets, safe whitelist only.
_BRAND_DIR = Path(__file__).resolve().parent / 'assets' / 'brand'
@app.get('/brand/{asset_name}')
def v28_brand_asset(asset_name: str):
    allowed = {'148ai-logo-1024.png','148ai-logo-512.png','148ai-logo-256.png','148ai-logo-128.png','148ai-logo-64.png','148ai-watermark-256.png','148ai-app-icon-512.png','148ai-favicon-64.png'}
    if asset_name not in allowed:
        raise HTTPException(404, 'brand asset not found')
    return Response((_BRAND_DIR / asset_name).read_bytes(), media_type='image/png', headers={'Cache-Control': 'public,max-age=86400'})

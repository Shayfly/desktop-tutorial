#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import io,json,os,socket,subprocess,sys,time,urllib.request,urllib.error,zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'LIVE_HTTP_V28.json'

def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0)); return s.getsockname()[1]

def req(base,path,method='GET',body=None,headers=None):
    data=None
    h=dict(headers or {})
    if body is not None:
        data=json.dumps(body).encode(); h['Content-Type']='application/json'
    r=urllib.request.Request(base+path,data=data,headers=h,method=method)
    try:
        with urllib.request.urlopen(r,timeout=15) as resp:
            raw=resp.read(); ctype=resp.headers.get('content-type','')
            return resp.status, (json.loads(raw.decode()) if 'json' in ctype else raw), dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw=e.read()
        try: payload=json.loads(raw.decode())
        except Exception: payload=raw.decode('utf-8','ignore')
        return e.code,payload,dict(e.headers)

port=free_port(); base=f'http://127.0.0.1:{port}'
env=os.environ.copy(); env.update({
    'OMNI_ENV':'production','OMNI_SECRET_KEY':'http-v28-'+'s'*48,
    'OMNI_GENERATED_APP_TOKEN_SECRET':'runtime-v28-'+'r'*48,
    'OMNI_CREATOR_PERSISTENCE':'memory','OMNI_ALLOWED_ORIGINS':'https://148ailabs.com',
})
for k in ('STRIPE_SECRET_KEY','STRIPE_WEBHOOK_SECRET','STRIPE_PRICE_BASIC','STRIPE_PRICE_PRO','STRIPE_PRICE_BUSINESS','OMNI_PUBLIC_BASE_URL','RUNPOD_API_KEY'):
    env.pop(k,None)
p=subprocess.Popen([sys.executable,'-m','uvicorn','omni_prod.investor_app:app','--host','127.0.0.1','--port',str(port),'--log-level','warning'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    deadline=time.time()+15
    while time.time()<deadline:
        try:
            st,_,_=req(base,'/api/status')
            if st==200: break
        except Exception: pass
        time.sleep(.15)
    else: raise RuntimeError('server did not start')
    out={}
    st,status,_=req(base,'/api/status'); out['status_code']=st; out['product']=status.get('product'); out['launch_candidate']=status.get('launch_candidate'); out['brand_public_ready']=status.get('brand_readiness',{}).get('public_brand_ready')
    st,pricing,_=req(base,'/api/v28/pricing'); out['pricing_status']=st; out['plans']=[x['code'] for x in pricing.get('plans',[])]; out['annual_prices']={x['code']:x.get('annual_price_usd') for x in pricing.get('plans',[])}
    st,tr,_=req(base,'/api/v28/ui/translations'); out['translation_status']=st; out['launch_locales']=tr.get('locale_count')
    out['pwa_manifest_status']=req(base,'/manifest.webmanifest')[0]; out['service_worker_status']=req(base,'/sw.js')[0]
    out['android_client_status']=req(base,'/api/v28/source/client/android')[0]; out['ios_client_status']=req(base,'/api/v28/source/client/ios')[0]

    def register(email):
        st,d,_=req(base,'/api/v28/auth/register','POST',{'email':email,'password':'StrongPass123!'})
        if st!=200: raise RuntimeError(f'register {st}: {d}')
        return d
    u1=register('owner@148ai.test'); u2=register('intruder@148ai.test'); h1={'Authorization':'Bearer '+u1['token']}; h2={'Authorization':'Bearer '+u2['token']}
    out['register_status']=200; out['default_plan']=u1['subscription']['plan']['code']
    st,p1,_=req(base,'/api/v28/projects','POST',{'title':'Safe product'},h1); out['project1_status']=st; pid1=p1['id']
    st,p2,_=req(base,'/api/v28/projects','POST',{'title':'Rights test'},h1); out['project2_status']=st; pid2=p2['id']
    out['free_third_project_status']=req(base,'/api/v28/projects','POST',{'title':'Over limit'},h1)[0]

    st,b1,_=req(base,f'/api/v28/projects/{pid1}/build','POST',{'prompt':'Build an original multilingual booking app with payments and mobile support','target_markets':['US','EU','IL']},h1)
    out['safe_build_status']=st; out['safe_files']=b1.get('file_count'); out['safe_brand']=b1.get('brand',{}).get('name'); out['safe_rights']=b1.get('rights',{}).get('status')
    st,prom,_=req(base,f'/api/v28/projects/{pid1}/promote','POST',None,h1); out['safe_promote_status']=st; dep=prom.get('deployment_id') if isinstance(prom,dict) else None
    st,zraw,_=req(base,f'/api/v28/projects/{pid1}/export','GET',None,h1); out['export_status']=st
    if st==200:
        with zipfile.ZipFile(io.BytesIO(zraw)) as z:
            names=set(z.namelist()); out['brand_manifest_in_export']='.148ai/brand-manifest.json' in names; out['provenance_in_export']='.148ai/provenance.json' in names

    st,b2,_=req(base,f'/api/v28/projects/{pid2}/build','POST',{'prompt':'Build a football game using Lionel Messi and Cristiano Ronaldo with their real likenesses and team logos','target_markets':['US','EU']},h1)
    out['risky_build_status']=st; out['risky_rights']=b2.get('rights',{}).get('status'); out['risky_promote_status']=req(base,f'/api/v28/projects/{pid2}/promote','POST',None,h1)[0]
    out['cross_user_rights_status']=req(base,f'/api/v28/projects/{pid1}/rights','GET',None,h2)[0]
    out['free_live_build_status']=req(base,f'/api/v28/projects/{pid1}/live-build','POST',{'prompt':'Build an advanced AI SaaS with image generation','target_markets':['US']},h1)[0]

    st,ints,_=req(base,'/api/v28/integrations','GET',None,h1); out['integrations_status']=st; txt=json.dumps(ints); out['integration_payload_contains_secret_values']='super-sensitive' in txt; out['integration_blockers']=ints.get('public_launch_blockers',[])
    out['company_os_status']=req(base,'/api/v28/company-os','GET',None,h1)[0]
    out['creator_without_billing_admin_key_status']=req(base,'/api/v28/admin/subscription','POST',{'user_id':u1['user']['id'],'plan':'pro'},h1)[0]
    out['checkout_without_stripe_status']=req(base,'/api/v28/billing/checkout','POST',{'plan':'pro'},h1)[0]

    if dep:
        st,rr,_=req(base,f'/runtime/v28/{dep}/register','POST',{'email':'appadmin@example.com','password':'RuntimePass123!'}); out['generated_app_register_status']=st; out['generated_app_first_role']=rr.get('role') if isinstance(rr,dict) else None
        out['generated_app_unauth_crud_status']=req(base,f'/runtime/v28/{dep}/data/items','GET')[0]
        rh={'Authorization':'Bearer '+rr['token']}; out['generated_app_auth_create_status']=req(base,f'/runtime/v28/{dep}/data/items','POST',{'payload':{'name':'record'}},rh)[0]
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(out,indent=2,sort_keys=True))
finally:
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill()

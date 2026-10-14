from __future__ import annotations

import io
import json
import os
import unittest
import uuid
import zipfile
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from omni_prod.branding import BrandingEngine
from omni_prod.integration_center import IntegrationCenter
from omni_prod.investor_app import app
from omni_prod.pricing import PLAN_CATALOG, PlanCode, SubscriptionService
from omni_prod.v28_platform import V28Platform
from omni_prod.i18n import SUPPORTED_LOCALES

SECRET='v28-test-'+'s'*48


class PricingAndBrandingTests(unittest.TestCase):
    def test_plan_catalog_has_free_basic_pro_business(self):
        self.assertEqual(PLAN_CATALOG[PlanCode.FREE].monthly_price_usd, Decimal('0'))
        self.assertEqual(PLAN_CATALOG[PlanCode.BASIC].monthly_price_usd, Decimal('12'))
        self.assertEqual(PLAN_CATALOG[PlanCode.PRO].monthly_price_usd, Decimal('39'))
        self.assertEqual(PLAN_CATALOG[PlanCode.BUSINESS].monthly_price_usd, Decimal('99'))
        self.assertGreaterEqual(PLAN_CATALOG[PlanCode.BASIC].variable_margin_floor(), Decimal('.75'))
        self.assertGreaterEqual(PLAN_CATALOG[PlanCode.PRO].variable_margin_floor(), Decimal('.70'))
        self.assertGreaterEqual(PLAN_CATALOG[PlanCode.BUSINESS].variable_margin_floor(), Decimal('.70'))

    def test_free_blocks_paid_provider_and_bug_repair_is_credit_free(self):
        s=SubscriptionService(); uid='u1'
        denied=s.authorize(user_id=uid,cost_class='standard',credits=10)
        self.assertFalse(denied.allowed)
        s.assign_plan(uid,'basic')
        repair=s.authorize(user_id=uid,cost_class='standard',credits=100,category='system_bug')
        self.assertTrue(repair.allowed); self.assertEqual(repair.credits,0); self.assertFalse(repair.user_billable)
        snap=s.consume(user_id=uid,decision=repair)
        self.assertEqual(snap['credits_used'],0)
        self.assertGreater(Decimal(snap['provider_spend_usd']),Decimal('0'))

    def test_hard_provider_budget(self):
        s=SubscriptionService(); uid='u2'; s.assign_plan(uid,'basic')
        d=s.authorize(user_id=uid,cost_class='standard',credits=1,estimated_provider_cost_usd=Decimal('2.40'))
        self.assertTrue(d.allowed); s.consume(user_id=uid,decision=d)
        d2=s.authorize(user_id=uid,cost_class='light',credits=1,estimated_provider_cost_usd=Decimal('.20'))
        self.assertFalse(d2.allowed); self.assertIn('budget',d2.reason)

    def test_branding_policy_and_repository_badge(self):
        b=BrandingEngine(); repo={'index.html':'<html><body><h1>Hello</h1></body></html>'}
        free=b.decorate_repository(repo,plan='free',project_id='p1')
        self.assertIn('Built with 148AI',free['index.html'])
        self.assertIn('.148ai/provenance.json',free)
        pro=b.decorate_repository(repo,plan='pro',project_id='p1',requested_visible=False)
        self.assertNotIn('Built with 148AI',pro['index.html'])
        with self.assertRaises(PermissionError):
            b.decorate_repository(repo,plan='basic',project_id='p1',requested_visible=False)

    def test_business_white_label_only(self):
        b=BrandingEngine(); repo={'index.html':'<body></body>'}
        with self.assertRaises(PermissionError):
            b.decorate_repository(repo,plan='pro',project_id='p',white_label_name='Acme')
        x=b.decorate_repository(repo,plan='business',project_id='p',white_label_name='Acme',requested_visible=False)
        manifest=json.loads(x['.148ai/brand-manifest.json'])
        self.assertEqual(manifest['white_label_name'],'Acme')

    def test_actual_raster_watermark(self):
        src=io.BytesIO(); Image.new('RGBA',(640,360),(250,250,250,255)).save(src,format='PNG')
        out=BrandingEngine().watermark_image_bytes(src.getvalue())
        im=Image.open(io.BytesIO(out)).convert('RGBA')
        self.assertEqual(im.size,(640,360))
        # At least one pixel in the watermark quadrant must differ from the flat source.
        region=im.crop((450,220,640,360))
        self.assertTrue(any(px!=(250,250,250,255) for px in region.get_flattened_data()))

    def test_global_locale_contract_expanded(self):
        self.assertGreaterEqual(len(SUPPORTED_LOCALES),20)
        self.assertIn('ar',SUPPORTED_LOCALES); self.assertIn('hi',SUPPORTED_LOCALES); self.assertIn('zh',SUPPORTED_LOCALES)


class V28PlatformTests(unittest.TestCase):
    def test_default_free_build_has_148ai_provenance(self):
        p=V28Platform(token_secret=SECRET,generated_app_token_secret='runtime-'+'r'*48)
        r=p.register(email='x@example.com',password='StrongPass123!'); t=r['token']
        self.assertEqual(r['subscription']['plan']['code'],'free')
        project=p.create_project(token=t,title='148AI Test')
        built=p.build(token=t,project_id=project['id'],prompt='Build an original CRM',target_markets=('US',))
        repo=p.repository(token=t,project_id=project['id'])
        self.assertIn('.148ai/brand-manifest.json',repo)
        self.assertIn('.148ai/provenance.json',repo)
        self.assertEqual(built['brand']['name'],'148AI')

    def test_pro_can_remove_branding_business_can_white_label(self):
        p=V28Platform(token_secret=SECRET,generated_app_token_secret='runtime-'+'r'*48)
        r=p.register(email='pro@example.com',password='StrongPass123!'); t=r['token']; uid=r['user']['id']
        pr=p.create_project(token=t,title='Pro')
        p.assign_plan_admin(user_id=uid,plan='pro')
        p.build(token=t,project_id=pr['id'],prompt='Build original dashboard',target_markets=('US',))
        b=p.set_project_branding(token=t,project_id=pr['id'],visible=False)
        self.assertFalse(b['visible_branding'])
        p.assign_plan_admin(user_id=uid,plan='business')
        w=p.set_project_branding(token=t,project_id=pr['id'],visible=False,white_label_name='Customer Brand')
        self.assertEqual(w['white_label_name'],'Customer Brand')


class V28HTTPTests(unittest.TestCase):
    def setUp(self): self.c=TestClient(app)
    def _email(self): return f'v28-{uuid.uuid4().hex[:12]}@example.com'
    def test_status_brand_pricing_brand_asset_and_flow(self):
        s=self.c.get('/api/status'); self.assertEqual(s.status_code,200); self.assertEqual(s.json()['product'],'148AI'); self.assertIn('V28',s.json()['launch_candidate'])
        pricing=self.c.get('/api/v28/pricing'); self.assertEqual(pricing.status_code,200); self.assertEqual(len([p for p in pricing.json()['plans'] if p['code']!='enterprise']),4)
        logo=self.c.get('/brand/148ai-logo-128.png'); self.assertEqual(logo.status_code,200); self.assertGreater(len(logo.content),1000)
        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'})
        self.assertEqual(reg.status_code,200,reg.text); tok=reg.json()['token']; h={'Authorization':'Bearer '+tok}
        self.assertEqual(reg.json()['subscription']['plan']['code'],'free')
        pr=self.c.post('/api/v28/projects',headers=h,json={'title':'Launch test'}); self.assertEqual(pr.status_code,200,pr.text); pid=pr.json()['id']
        b=self.c.post(f'/api/v28/projects/{pid}/build',headers=h,json={'prompt':'Build an original booking app','target_markets':['US','EU']})
        self.assertEqual(b.status_code,200,b.text); self.assertEqual(b.json()['brand']['name'],'148AI')
        ex=self.c.get(f'/api/v28/projects/{pid}/export',headers=h); self.assertEqual(ex.status_code,200)
        with zipfile.ZipFile(io.BytesIO(ex.content)) as z:
            self.assertIn('.148ai/brand-manifest.json',z.namelist()); self.assertIn('.148ai/provenance.json',z.namelist())

    def test_free_live_paid_compute_fails_before_provider_call(self):
        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json(); h={'Authorization':'Bearer '+reg['token']}
        pid=self.c.post('/api/v28/projects',headers=h,json={'title':'Free compute'}).json()['id']
        r=self.c.post(f'/api/v28/projects/{pid}/live-build',headers=h,json={'prompt':'Build an AI SaaS with image generation','target_markets':['US']})
        self.assertEqual(r.status_code,402,r.text)

    def test_integration_center_never_returns_secret_values(self):
        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json(); h={'Authorization':'Bearer '+reg['token']}
        with patch.dict(os.environ,{'RUNPOD_API_KEY':'super-sensitive-value-xyz'},clear=False):
            d=self.c.get('/api/v28/integrations',headers=h); self.assertEqual(d.status_code,200,d.text)
            text=json.dumps(d.json())
            self.assertNotIn('super-sensitive-value-xyz',text)

    def test_plan_upgrade_requires_admin_key(self):
        email=self._email(); reg=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json(); uid=reg['user']['id']
        denied=self.c.post('/api/v28/admin/subscription',json={'user_id':uid,'plan':'pro'})
        self.assertEqual(denied.status_code,403)
        with patch.dict(os.environ,{'OMNI_BILLING_ADMIN_KEY':'billing-admin-test'},clear=False):
            ok=self.c.post('/api/v28/admin/subscription',headers={'X-148AI-Billing-Admin-Key':'billing-admin-test'},json={'user_id':uid,'plan':'pro'})
            self.assertEqual(ok.status_code,200,ok.text); self.assertEqual(ok.json()['plan']['code'],'pro')

if __name__=='__main__': unittest.main()

class V28LaunchHardeningTests(unittest.TestCase):
    def test_brand_readiness_fails_closed_until_external_steps_complete(self):
        from omni_prod.brand_clearance import brand_readiness
        with patch.dict(os.environ, {
            'OMNI_BRAND_TRADEMARK_CLEARED':'0','OMNI_BRAND_TRADEMARK_FILED':'0',
            'OMNI_BRAND_DOMAIN_OWNED':'0','OMNI_BRAND_DNS_TLS_READY':'0'
        }, clear=False):
            r=brand_readiness(logo_pack_present=True)
            self.assertFalse(r.public_brand_ready); self.assertGreaterEqual(len(r.blockers),3)
        with patch.dict(os.environ, {
            'OMNI_BRAND_TRADEMARK_CLEARED':'1','OMNI_BRAND_TRADEMARK_FILED':'1',
            'OMNI_BRAND_DOMAIN_OWNED':'1','OMNI_BRAND_DNS_TLS_READY':'1'
        }, clear=False):
            r=brand_readiness(logo_pack_present=True)
            self.assertTrue(r.public_brand_ready); self.assertFalse(r.blockers)

    def test_all_20_launch_locales_have_complete_core_copy(self):
        from omni_prod.ui_translations import UI_LANGUAGES, UI_COPY
        required={'hero','lead','account','project','request','build','history','rights','original','company','integration','refresh','ready','output','markets','register','login','new_project'}
        self.assertEqual(len(UI_LANGUAGES),20)
        self.assertEqual(set(UI_LANGUAGES),set(UI_COPY))
        for locale, copy in UI_COPY.items():
            self.assertTrue(required.issubset(copy), locale)
            self.assertTrue(all(str(copy[k]).strip() for k in required), locale)

    def test_annual_pricing_defaults_to_ten_months_for_paid_launch_plans(self):
        for code in (PlanCode.BASIC,PlanCode.PRO,PlanCode.BUSINESS):
            p=PLAN_CATALOG[code]
            self.assertEqual(p.annual_price_usd,p.monthly_price_usd*10)

    def test_media_branding_raster_and_nondestructive_audio_provenance(self):
        from omni_prod.media_branding import MediaBrandingEngine
        from omni_prod.media_gateway import GeneratedAsset
        src=io.BytesIO(); Image.new('RGBA',(640,360),(250,250,250,255)).save(src,format='PNG')
        branded=MediaBrandingEngine().apply(GeneratedAsset('a','image/png',src.getvalue(),'test',{}),plan='free')
        self.assertNotEqual(branded.data,src.getvalue()); self.assertEqual(branded.metadata['branding_applied'],'raster-watermark')
        audio=MediaBrandingEngine().apply(GeneratedAsset('b','audio/mpeg',b'fake-audio','test',{}),plan='free')
        self.assertEqual(audio.data,b'fake-audio'); self.assertTrue(audio.metadata['brand_provenance'])

    def test_ui_translation_brand_and_pwa_endpoints(self):
        c=TestClient(app)
        tr=c.get('/api/v28/ui/translations'); self.assertEqual(tr.status_code,200); self.assertEqual(tr.json()['locale_count'],20)
        br=c.get('/api/v28/brand/readiness'); self.assertEqual(br.status_code,200); self.assertEqual(br.json()['brand_name'],'148AI')
        mf=c.get('/manifest.webmanifest'); self.assertEqual(mf.status_code,200); self.assertIn('148AI',mf.text)
        sw=c.get('/sw.js'); self.assertEqual(sw.status_code,200); self.assertIn("148ai-v28-static",sw.text)

    def test_stripe_signature_and_idempotent_plan_assignment(self):
        import hashlib,hmac,time
        from omni_prod.stripe_billing import verify_stripe_signature, StripeSubscriptionWebhookProcessor
        from omni_prod.pricing import SubscriptionService
        now=int(time.time())
        payload=json.dumps({'id':'evt_148ai_1','created':now,'type':'checkout.session.completed','data':{'object':{'id':'cs_test_retention','subscription':'sub_test_retention','payment_status':'paid','mode':'subscription','metadata':{'user_id':'u-stripe','plan_code':'pro'}}}},separators=(',',':')).encode()
        secret='whsec_test_148ai'
        sig=hmac.new(secret.encode(),str(now).encode()+b'.'+payload,hashlib.sha256).hexdigest()
        event=verify_stripe_signature(payload,f't={now},v1={sig}',secret,now=now)
        svc=SubscriptionService(); svc.assign_plan('u-stripe', PlanCode.PRO)
        proc=StripeSubscriptionWebhookProcessor(svc)
        first=proc.process(event); second=proc.process(event)
        self.assertTrue(first['processed']); self.assertEqual(svc.plan_for('u-stripe').code,PlanCode.PRO)
        self.assertTrue(second['duplicate']); self.assertFalse(second['processed'])

class V28BillingSafetyTests(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(app)

    def _register(self):
        email=f'billing-{uuid.uuid4().hex[:12]}@example.com'
        r=self.c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()

    def test_checkout_fails_closed_without_stripe_and_plan_stays_free(self):
        reg=self._register(); h={'Authorization':'Bearer '+reg['token']}
        with patch.dict(os.environ,{'STRIPE_SECRET_KEY':'','OMNI_PUBLIC_BASE_URL':''},clear=False):
            r=self.c.post('/api/v28/billing/checkout',headers=h,json={'plan':'pro'})
        self.assertEqual(r.status_code,503,r.text)
        snap=self.c.get('/api/v28/me/subscription',headers=h)
        self.assertEqual(snap.status_code,200,snap.text)
        self.assertEqual(snap.json()['plan']['code'],'free')

    def test_webhook_without_verified_signature_cannot_upgrade(self):
        reg=self._register(); h={'Authorization':'Bearer '+reg['token']}
        event={'id':'evt_'+uuid.uuid4().hex,'type':'checkout.session.completed','data':{'object':{'client_reference_id':reg['user']['id'],'metadata':{'plan_code':'pro'}}}}
        with patch.dict(os.environ,{'STRIPE_WEBHOOK_SECRET':'webhook-test-secret'},clear=False):
            r=self.c.post('/api/v28/billing/stripe/webhook',content=json.dumps(event).encode(),headers={'stripe-signature':'t=1,v1=bad'})
        self.assertEqual(r.status_code,400,r.text)
        snap=self.c.get('/api/v28/me/subscription',headers=h)
        self.assertEqual(snap.json()['plan']['code'],'free')

class V28VerifiedWebhookTests(unittest.TestCase):
    def test_valid_signed_stripe_webhook_can_assign_paid_plan(self):
        import hashlib, hmac, time
        c=TestClient(app)
        email=f'verified-billing-{uuid.uuid4().hex[:10]}@example.com'
        reg=c.post('/api/v28/auth/register',json={'email':email,'password':'StrongPass123!'}).json()
        uid=reg['user']['id']; token=reg['token']
        event={'id':'evt_'+uuid.uuid4().hex,'created':int(time.time()),'type':'checkout.session.completed','data':{'object':{'id':'cs_test_paid','subscription':'sub_test_paid','payment_status':'paid','mode':'subscription','client_reference_id':uid,'metadata':{'user_id':uid,'plan_code':'pro'}}}}
        body=json.dumps(event,separators=(',',':')).encode(); ts=int(time.time()); secret='verified-webhook-secret'
        sig=hmac.new(secret.encode(),str(ts).encode()+b'.'+body,hashlib.sha256).hexdigest()
        with patch.dict(os.environ,{'STRIPE_WEBHOOK_SECRET':secret},clear=False):
            r=c.post('/api/v28/billing/stripe/webhook',content=body,headers={'stripe-signature':f't={ts},v1={sig}','content-type':'application/json'})
        self.assertEqual(r.status_code,200,r.text); self.assertEqual(r.json()['plan'],'pro')
        snap=c.get('/api/v28/me/subscription',headers={'Authorization':'Bearer '+token})
        self.assertEqual(snap.json()['plan']['code'],'pro')

import io
import json
import unittest
import zipfile

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from omni_prod.investor_app import app
from omni_prod.native_source import omni_android_release_project, game_project
from omni_prod.repository_patch import apply_patch, parse_patch, PatchValidationError
from omni_prod.unified_engine import UnifiedOmniEngine, UnifiedPromptPlanner

UBER_PROMPT='תבנה לי אפליקציה בסגנון Uber עם לקוחות, נהגים, נסיעות, תשלומים, GPS, מפה, מעקב חי, התראות והרשאות'


class V10PlanningParityTests(unittest.TestCase):
    def test_uber_modules_exact(self):
        p=UnifiedPromptPlanner().plan(UBER_PROMPT)
        self.assertEqual(p.modules,('customers','drivers','rides','payments'))

    def test_uber_capabilities_cover_v10(self):
        p=UnifiedPromptPlanner().plan(UBER_PROMPT)
        self.assertTrue({'analytics','auth','export','maps','notifications','payments','realtime','roles','search'}.issubset(set(p.capabilities)))

    def test_mobile_target_is_planned(self):
        self.assertIn('android',UnifiedPromptPlanner().plan(UBER_PROMPT).targets)


class UnifiedEngineParityTests(unittest.TestCase):
    def setUp(self):
        self.e=UnifiedOmniEngine(token_secret='t'*64)

    def test_v10_style_build_is_ready_and_structured(self):
        r=self.e.build(project_id='uber',prompt=UBER_PROMPT)
        self.assertEqual(r.status,'READY')
        self.assertGreaterEqual(r.file_count,42)
        self.assertTrue(r.preview_ready)
        self.assertTrue(r.web_package_ready)
        self.assertEqual(r.android_status,'SOURCE_READY')
        self.assertEqual(r.launch_score,100)
        self.assertTrue(r.launch_ready)

    def test_source_export_is_valid_zip(self):
        r=self.e.build(project_id='export',prompt=UBER_PROMPT)
        z=zipfile.ZipFile(io.BytesIO(self.e.export_zip(project_id='export',version_id=r.version_id)))
        self.assertIsNone(z.testzip())
        self.assertIn('backend/modules/rides.py',z.namelist())
        self.assertIn('.omni/unified.json',z.namelist())

    def test_chat_patch_creates_new_version(self):
        r=self.e.build(project_id='patch',prompt=UBER_PROMPT)
        v2=self.e.patch(project_id='patch',payload={'files':[{'path':'backend/modules/rides.py','content':'# patched\n'}]})
        self.assertNotEqual(r.version_id,v2.id)
        self.assertEqual(v2.parent_id,r.version_id)
        self.assertEqual(self.e.repository(project_id='patch')['backend/modules/rides.py'],'# patched\n')

    def test_deployed_version_is_immutable_after_project_patch(self):
        r=self.e.build(project_id='isolation',prompt=UBER_PROMPT)
        d=self.e.promote(project_id='isolation',version_id=r.version_id)
        before=self.e.deployed_repository(d.deployment_id)
        self.e.patch(project_id='isolation',payload={'files':[{'path':'new-feature.txt','content':'later'}]})
        after=self.e.deployed_repository(d.deployment_id)
        self.assertEqual(before,after)
        self.assertNotIn('new-feature.txt',after)

    def test_generated_app_first_user_admin_and_authenticated_crud(self):
        self.e.build(project_id='runtime',prompt=UBER_PROMPT)
        d=self.e.promote(project_id='runtime')
        runtime=self.e.runtime(d.deployment_id)
        role,token=runtime.register(email='owner@example.com',credential='correct-horse')
        self.assertEqual(role,'admin')
        created=runtime.create(token=token,collection='rides',payload={'from':'A','to':'B'})
        self.assertEqual(created['from'],'A')
        self.assertEqual(len(runtime.list(token=token,collection='rides')),1)

    def test_deployment_data_isolated(self):
        self.e.build(project_id='p1',prompt=UBER_PROMPT); d1=self.e.promote(project_id='p1')
        self.e.build(project_id='p2',prompt=UBER_PROMPT); d2=self.e.promote(project_id='p2')
        _,t1=self.e.runtime(d1.deployment_id).register(email='a@x.com',credential='password1')
        _,t2=self.e.runtime(d2.deployment_id).register(email='b@x.com',credential='password2')
        self.e.runtime(d1.deployment_id).create(token=t1,collection='rides',payload={'secret':'one'})
        self.assertEqual(self.e.runtime(d2.deployment_id).list(token=t2,collection='rides'),[])

    def test_cross_deployment_token_rejected(self):
        self.e.build(project_id='x1',prompt=UBER_PROMPT); d1=self.e.promote(project_id='x1')
        self.e.build(project_id='x2',prompt=UBER_PROMPT); d2=self.e.promote(project_id='x2')
        _,token=self.e.runtime(d1.deployment_id).register(email='a@x.com',credential='password1')
        with self.assertRaises(PermissionError):
            self.e.runtime(d2.deployment_id).list(token=token,collection='rides')


class NativeParityTests(unittest.TestCase):
    def test_omni_android_v10_release_contract(self):
        r=omni_android_release_project()
        gradle=r['omni-android/app/build.gradle.kts']
        manifest=r['omni-android/app/src/main/AndroidManifest.xml']
        main=[v for k,v in r.items() if k.endswith('MainActivity.java')][0]
        workflow=r['.github/workflows/omni-android-aab.yml']
        self.assertIn('ai.omnicreator.mobile',gradle)
        self.assertIn('compileSdk=35',gradle); self.assertIn('targetSdk=35',gradle)
        self.assertIn('ACCESS_FINE_LOCATION',manifest)
        self.assertIn('onShowFileChooser',main); self.assertIn('onGeolocationPermissionsShowPrompt',main)
        self.assertIn('OMNI_ANDROID_KEYSTORE',gradle)
        self.assertIn('java-version: "17"',workflow); self.assertIn('gradle-version: "8.9"',workflow); self.assertIn('bundleRelease',workflow)

    def test_godot_is_explicitly_v4_source(self):
        r=game_project('godot',title='Football')
        self.assertIn('PackedStringArray("4.3")',r['project.godot'])
        self.assertIn('CharacterBody3D',r['Main.tscn'])


class PatchSafetyParityTests(unittest.TestCase):
    def test_safe_external_patch_adds_file(self):
        p=parse_patch({'files':[{'path':'features/new.py','content':'VALUE=1\n'}]})
        self.assertIn('features/new.py',apply_patch({},p))

    def test_unsafe_external_patch_rejected(self):
        with self.assertRaises(PatchValidationError):
            parse_patch({'files':[{'path':'../escape.py','content':'bad'}]})


class V25HttpAcceptanceTests(unittest.TestCase):
    def setUp(self): self.c=TestClient(app)

    def _build_promote_register(self,project):
        b=self.c.post('/api/v25/build',json={'prompt':UBER_PROMPT,'project_id':project})
        self.assertEqual(b.status_code,200,b.text)
        data=b.json(); self.assertEqual(data['status'],'READY'); self.assertGreaterEqual(data['file_count'],42)
        p=self.c.post(f'/api/v25/projects/{project}/promote')
        self.assertEqual(p.status_code,200,p.text); dep=p.json()['deployment_id']
        reg=self.c.post(f'/runtime/v25/{dep}/register',json={'email':f'{project}@example.com','password':'strong-pass-1'})
        self.assertEqual(reg.status_code,200,reg.text)
        return data,dep,reg.json()['token'],reg.json()['role']

    def test_status_exposes_v25_without_breaking_v24_field(self):
        d=self.c.get('/api/status').json()
        self.assertEqual(d['product_release'],'V24 International Readiness')
        self.assertEqual(d['current_release'],'V25 Unified Core')

    def test_full_http_acceptance_auth_crud_hosted_export(self):
        b,dep,token,role=self._build_promote_register('http-uber')
        self.assertEqual(role,'admin')
        hosted=self.c.get(f'/hosted/v25/{dep}'); self.assertEqual(hosted.status_code,200); self.assertIn('OMNI GENERATED PREVIEW',hosted.text)
        unauth=self.c.post(f'/runtime/v25/{dep}/data/rides',json={'payload':{'x':1}}); self.assertEqual(unauth.status_code,401)
        auth=self.c.post(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'},json={'payload':{'from':'A','to':'B'}})
        self.assertEqual(auth.status_code,200,auth.text)
        listed=self.c.get(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'}).json()['items']
        self.assertEqual(len(listed),1)
        export=self.c.get('/api/v25/projects/http-uber/export'); self.assertEqual(export.status_code,200)
        self.assertIsNone(zipfile.ZipFile(io.BytesIO(export.content)).testzip())

    def test_authenticated_websocket(self):
        _,dep,token,_=self._build_promote_register('http-ws')
        with self.c.websocket_connect(f'/runtime/v25/{dep}/ws?token={token}') as ws:
            hello=ws.receive_json(); self.assertTrue(hello['authenticated']); self.assertEqual(hello['deployment_id'],dep)
            ws.send_json({'type':'ping'}); self.assertEqual(ws.receive_json()['echo']['type'],'ping')

    def test_unauthenticated_websocket_rejected(self):
        self.c.post('/api/v25/build',json={'prompt':UBER_PROMPT,'project_id':'bad-ws'})
        dep=self.c.post('/api/v25/projects/bad-ws/promote').json()['deployment_id']
        with self.assertRaises(WebSocketDisconnect) as ctx:
            with self.c.websocket_connect(f'/runtime/v25/{dep}/ws') as ws:
                ws.receive_json()
        self.assertEqual(ctx.exception.code,4401)

    def test_deployment_data_survives_project_patch(self):
        b,dep,token,_=self._build_promote_register('persist-http')
        self.c.post(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'},json={'payload':{'ride':'kept'}})
        patch=self.c.post('/api/v25/projects/persist-http/patch',json={'files':[{'path':'feature.txt','content':'new'}],'message':'new version'})
        self.assertEqual(patch.status_code,200); self.assertNotEqual(patch.json()['version_id'],b['version_id'])
        items=self.c.get(f'/runtime/v25/{dep}/data/rides',headers={'Authorization':f'Bearer {token}'}).json()['items']
        self.assertEqual(items[0]['ride'],'kept')


if __name__=='__main__': unittest.main()

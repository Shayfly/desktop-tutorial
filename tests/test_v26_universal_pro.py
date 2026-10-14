from __future__ import annotations
import io, json, zipfile
import unittest
from fastapi.testclient import TestClient
from omni_prod.account_tenant import AccountService
from omni_prod.media_pipeline import CreativeDirector, AssetKind
from omni_prod.universal_brain import OmniUniversalBrain
from omni_prod.investor_app import app

SECRET='v26-test-'+'z'*48

class AccountTenantTests(unittest.TestCase):
    def test_two_users_are_isolated(self):
        s=AccountService(token_secret=SECRET)
        a,ta=s.register(email='a@example.com',password='StrongPass123!')
        b,tb=s.register(email='b@example.com',password='StrongPass123!')
        p=s.create_project(owner_id=a.id,title='Private')
        self.assertEqual(s.require_project(owner_id=a.id,project_id=p.id).id,p.id)
        with self.assertRaises(PermissionError): s.require_project(owner_id=b.id,project_id=p.id)
        self.assertEqual(len(s.list_projects(owner_id=b.id)),0)
        self.assertEqual(s.authenticate(ta).id,a.id)
        self.assertEqual(s.authenticate(tb).id,b.id)

    def test_duplicate_email_and_bad_password(self):
        s=AccountService(token_secret=SECRET)
        s.register(email='a@example.com',password='StrongPass123!')
        with self.assertRaises(ValueError): s.register(email='a@example.com',password='StrongPass123!')
        with self.assertRaises(PermissionError): s.login(email='a@example.com',password='wrong-password')

class CreativeBrainTests(unittest.TestCase):
    def test_game_prompt_plans_3d_audio_music(self):
        plan=CreativeDirector().plan('Build a 3D football game in Unreal with crowd sound and music',targets=('web','game3d'))
        kinds={x.kind for x in plan.requests}
        self.assertIn(AssetKind.MODEL3D,kinds); self.assertIn(AssetKind.AUDIO,kinds); self.assertIn(AssetKind.MUSIC,kinds)
        self.assertTrue(plan.rights_policy['original_or_licensed_only'])

    def test_universal_brain_keeps_security_principles(self):
        d=OmniUniversalBrain().decide('Build an iOS and Android booking app with payments')
        self.assertIn('user-owns-project',d.principles)
        self.assertIn('android',d.plan.targets)
        self.assertIn('ios',d.plan.targets)
        self.assertIn('payments',d.plan.capabilities)

class V26HttpTests(unittest.TestCase):
    def setUp(self): self.c=TestClient(app)
    def _register(self,email):
        r=self.c.post('/api/v26/auth/register',json={'email':email,'password':'StrongPass123!'})
        self.assertEqual(r.status_code,200,r.text); return r.json()['token']
    def _auth(self,t): return {'Authorization':'Bearer '+t}

    def test_status_exposes_v26_without_breaking_v25(self):
        d=self.c.get('/api/status').json()
        self.assertEqual(d['current_release'],'V25 Unified Core')
        self.assertEqual(d['universal_release'],'V26 Universal Pro Reviewer Release')

    def test_full_creator_flow_and_cross_user_denial(self):
        t1=self._register('v26-one@example.com'); t2=self._register('v26-two@example.com')
        p=self.c.post('/api/v26/projects',headers=self._auth(t1),json={'title':'World App'}).json(); pid=p['id']
        build=self.c.post(f'/api/v26/projects/{pid}/build',headers=self._auth(t1),json={'prompt':'Build a multilingual 3D football game with Android app, realtime scores, music and voice'} )
        self.assertEqual(build.status_code,200,build.text); data=build.json()
        self.assertEqual(data['status'],'READY'); self.assertGreaterEqual(data['creative_assets']['planned'],5)
        self.assertEqual(data['creative_assets']['materialized'],0)
        denied=self.c.get(f'/api/v26/projects/{pid}/history',headers=self._auth(t2))
        self.assertEqual(denied.status_code,403)
        hist=self.c.get(f'/api/v26/projects/{pid}/history',headers=self._auth(t1)).json()['versions']
        self.assertGreaterEqual(len(hist),2)
        patch=self.c.post(f'/api/v26/projects/{pid}/patch',headers=self._auth(t1),json={'files':[{'path':'README_USER.md','content':'edited'}],'message':'user edit'})
        self.assertEqual(patch.status_code,200,patch.text)
        restore=self.c.post(f'/api/v26/projects/{pid}/restore',headers=self._auth(t1),json={'version_id':hist[0]['id']})
        self.assertEqual(restore.status_code,200,restore.text)
        exp=self.c.get(f'/api/v26/projects/{pid}/export',headers=self._auth(t1))
        self.assertEqual(exp.status_code,200); self.assertTrue(zipfile.is_zipfile(io.BytesIO(exp.content)))
        promoted=self.c.post(f'/api/v26/projects/{pid}/promote',headers=self._auth(t1))
        self.assertEqual(promoted.status_code,200,promoted.text)
        dep=promoted.json()['deployment_id']
        unauth=self.c.get(f'/runtime/v26/{dep}/data/items')
        self.assertEqual(unauth.status_code,401)
        reg=self.c.post(f'/runtime/v26/{dep}/register',json={'email':'appadmin@example.com','password':'StrongPass123!'})
        self.assertEqual(reg.status_code,200); self.assertEqual(reg.json()['role'],'admin')
        rt=reg.json()['token']
        created=self.c.post(f'/runtime/v26/{dep}/data/items',headers=self._auth(rt),json={'payload':{'name':'x'}})
        self.assertEqual(created.status_code,200,created.text)

    def test_brain_requires_auth(self):
        r=self.c.post('/api/v26/brain/plan',json={'prompt':'Build a CRM'})
        self.assertEqual(r.status_code,401)

if __name__=='__main__': unittest.main()

class V26LiveGateTests(unittest.TestCase):
    def test_live_build_fails_closed_without_enable_flag(self):
        c=TestClient(app)
        r=c.post('/api/v26/auth/register',json={'email':'live-gate@example.com','password':'StrongPass123!'})
        t=r.json()['token']; h={'Authorization':'Bearer '+t}
        p=c.post('/api/v26/projects',headers=h,json={'title':'Live Gate'}).json()['id']
        r=c.post(f'/api/v26/projects/{p}/live-build',headers=h,json={'prompt':'Build a CRM'})
        self.assertEqual(r.status_code,503)

class MediaGatewayTests(unittest.TestCase):
    def test_self_hosted_media_contract(self):
        import base64, threading
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from omni_prod.media_gateway import MediaEndpoint, HTTPMediaGateway
        from omni_prod.media_pipeline import AssetRequest, AssetKind
        class H(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_POST(self):
                n=int(self.headers.get('content-length','0')); body=json.loads(self.rfile.read(n))
                self.send_response(200); self.send_header('content-type','application/json'); self.end_headers()
                self.wfile.write(json.dumps({'content_base64':base64.b64encode(b'asset-bytes').decode(),'mime_type':'audio/wav','metadata':{'kind':body['kind']}}).encode())
        srv=HTTPServer(('127.0.0.1',0),H); th=threading.Thread(target=srv.serve_forever,daemon=True); th.start()
        try:
            ep=MediaEndpoint('local-media',f'http://127.0.0.1:{srv.server_port}')
            out=HTTPMediaGateway(ep).generate(AssetRequest('a1',AssetKind.AUDIO,'sfx','make sfx'))
            self.assertEqual(out.data,b'asset-bytes'); self.assertEqual(out.provider,'local-media'); self.assertEqual(out.mime_type,'audio/wav')
        finally: srv.shutdown(); srv.server_close()

class WorkspaceConcurrencyTests(unittest.TestCase):
    def test_concurrent_commits_have_unique_linear_versions(self):
        import concurrent.futures
        from omni_prod.workspace import ProjectWorkspace
        w=ProjectWorkspace()
        def one(i): return w.commit(project_id='p',repository={f'f{i}.txt':str(i)},message='m').id
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex: ids=list(ex.map(one,range(40)))
        self.assertEqual(len(set(ids)),40)
        self.assertEqual(len(w.history('p')),40)
        self.assertEqual(w.current('p').id,'p-v00040')

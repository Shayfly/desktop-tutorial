from __future__ import annotations

import io
import json
import zipfile
import unittest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient

from omni_prod.company_os import OnePersonCompanyOS
from omni_prod.investor_app import app
from omni_prod.rights_ip import RightsEngine, RightKind, RightsEvidence, GateStatus, JURISDICTIONS


class RightsEngineUnitTests(unittest.TestCase):
    def test_real_people_in_game_require_review(self):
        a=RightsEngine().assess('Build a football game with Messi and Ronaldo',target_markets=('US','EU','IL'))
        self.assertEqual(a.status,GateStatus.LEGAL_REVIEW_REQUIRED)
        self.assertFalse(a.publish_allowed)
        self.assertGreaterEqual(len(a.findings),2)
        self.assertTrue(a.original_alternative_recommended)

    def test_voice_request_needs_authorization_and_eu_disclosure(self):
        a=RightsEngine().assess('Create a song in the voice of Taylor Swift',target_markets=('EU',),synthetic_person_media=True)
        kinds={x.right_kind for x in a.findings}
        self.assertIn(RightKind.VOICE,kinds)
        self.assertFalse(a.publish_allowed)
        self.assertTrue(any('Article 50' in x for x in a.required_disclosures))

    def test_verified_evidence_can_clear_matching_findings(self):
        e=RightsEvidence('e1',RightKind.VOICE,'Taylor Swift','license','commercial synthetic voice use','ref',True)
        a=RightsEngine().assess('Create a song in the voice of Taylor Swift',target_markets=('US',),evidence=(e,))
        self.assertEqual(a.status,GateStatus.CLEAR)
        self.assertTrue(a.publish_allowed)

    def test_unverified_evidence_does_not_clear(self):
        e=RightsEvidence('e1',RightKind.VOICE,'Taylor Swift','user claim','commercial use','ref',False)
        a=RightsEngine().assess('Create a song in the voice of Taylor Swift',evidence=(e,))
        self.assertFalse(a.publish_allowed)

    def test_original_alternative_removes_detected_identity(self):
        d=RightsEngine().originalize('Build a football game with Messi and Ronaldo like Mario')
        self.assertNotIn('Messi',d['original_brief'])
        self.assertNotIn('Ronaldo',d['original_brief'])
        self.assertNotIn('Mario',d['original_brief'])
        self.assertIn('[ORIGINAL_ELEMENT]',d['original_brief'])
        self.assertIn('not a legal safe-harbor',d['truth_note'])

    def test_jurisdiction_profiles_have_official_sources(self):
        self.assertTrue({'US','EU','IL'}.issubset(JURISDICTIONS))
        for p in JURISDICTIONS.values():
            self.assertTrue(p.source_urls)
            self.assertTrue(all(x.startswith('https://') for x in p.source_urls))


class CompanyOSTests(unittest.TestCase):
    def test_one_person_company_has_core_departments(self):
        os=OnePersonCompanyOS(); deps={d['id'] for d in os.departments()}
        self.assertTrue({'ceo','product','ai','engineering','design','qa','security','legal','infra','data','finance','support','growth'}.issubset(deps))
        council=os.release_council()
        self.assertIn('rights/IP publish gate clear',council['required_gates'])
        self.assertIn('public launch',council['founder_must_approve'])


    def test_operating_company_triage_and_release_council(self):
        os=OnePersonCompanyOS()
        tasks=os.triage([
            {'kind':'security_alert','title':'Cross-tenant access suspicion','severity':'critical'},
            {'kind':'customer_feedback','title':'Users want project folders','severity':'medium'},
            {'kind':'cost_alert','title':'GPU cost spike','severity':'high'},
        ])
        self.assertEqual(tasks[0]['department_id'],'security')
        self.assertEqual(tasks[0]['priority'],'P0')
        self.assertTrue(tasks[0]['founder_approval_required'])
        self.assertEqual({x['department_id'] for x in tasks},{'security','product','finance'})
        blocked=os.evaluate_release({
            'product_acceptance':True,'engineering_regression':True,'qa_evals':True,
            'security_tenant_isolation':False,'rights_ip':True,
            'infrastructure_readiness':True,'backup_restore':True,
        },founder_public_launch_approved=True)
        self.assertFalse(blocked['technical_green'])
        self.assertFalse(blocked['public_launch_ready'])
        green=os.evaluate_release({k:True for k in (
            'product_acceptance','engineering_regression','qa_evals','security_tenant_isolation',
            'rights_ip','infrastructure_readiness','backup_restore')},founder_public_launch_approved=False)
        self.assertTrue(green['technical_green'])
        self.assertFalse(green['public_launch_ready'])


class V27HTTPTests(unittest.TestCase):
    def setUp(self): self.c=TestClient(app)
    def _register(self,email):
        r=self.c.post('/api/v27/auth/register',json={'email':email,'password':'StrongPass123!'})
        self.assertEqual(r.status_code,200,r.text); return r.json()['token']
    def _auth(self,t): return {'Authorization':'Bearer '+t}

    def test_status_reports_v27(self):
        d=self.c.get('/api/status').json()
        self.assertEqual(d['rights_release'],'V27 Rights & Company OS')
        self.assertIn('V27 rights/IP provenance and publish gate',d['capabilities'])

    def test_safe_project_can_promote_and_contains_rights_manifest(self):
        t=self._register('v27-safe@example.com'); h=self._auth(t)
        pid=self.c.post('/api/v27/projects',headers=h,json={'title':'Original CRM'}).json()['id']
        b=self.c.post(f'/api/v27/projects/{pid}/build',headers=h,json={'prompt':'Build an original CRM for technicians with bookings and payments','target_markets':['US','EU','IL']})
        self.assertEqual(b.status_code,200,b.text); data=b.json()
        self.assertEqual(data['rights']['status'],'CLEAR')
        self.assertTrue(data['rights']['publish_allowed'])
        z=self.c.get(f'/api/v27/projects/{pid}/export',headers=h)
        self.assertEqual(z.status_code,200)
        with zipfile.ZipFile(io.BytesIO(z.content)) as f:
            self.assertIn('rights/rights-manifest.json',f.namelist())
            m=json.loads(f.read('rights/rights-manifest.json'))
            self.assertEqual(m['status'],'CLEAR')
        p=self.c.post(f'/api/v27/projects/{pid}/promote',headers=h)
        self.assertEqual(p.status_code,200,p.text)
        self.assertEqual(p.json()['rights_gate'],'CLEAR')

    def test_high_risk_project_is_blocked_until_verified_rights(self):
        t=self._register('v27-rights@example.com'); h=self._auth(t)
        pid=self.c.post('/api/v27/projects',headers=h,json={'title':'Football'}).json()['id']
        b=self.c.post(f'/api/v27/projects/{pid}/build',headers=h,json={'prompt':'Build a football game with Messi and Ronaldo','target_markets':['US','EU']})
        self.assertEqual(b.status_code,200,b.text)
        self.assertEqual(b.json()['rights']['status'],'LEGAL_REVIEW_REQUIRED')
        blocked=self.c.post(f'/api/v27/projects/{pid}/promote',headers=h)
        self.assertEqual(blocked.status_code,409,blocked.text)
        # Both person findings need verified evidence; a mere claim is not sufficient.
        evidence_ids=[]
        for subject in ('messi','ronaldo'):
            e=self.c.post(f'/api/v27/projects/{pid}/rights/evidence',headers=h,json={
                'right_kind':'persona_likeness','subject':subject,'evidence_type':'signed commercial consent',
                'scope':'game worldwide commercial use','source_reference':'vault://rights/'+subject,
            })
            self.assertEqual(e.status_code,200,e.text)
            self.assertFalse(e.json()['record']['verified'])
            evidence_ids.append(e.json()['record']['id'])
        still_blocked=self.c.post(f'/api/v27/projects/{pid}/promote',headers=h)
        self.assertEqual(still_blocked.status_code,409)
        denied_review=self.c.post(f'/api/v27/projects/{pid}/rights/review',headers=h,json={'evidence_id':evidence_ids[0]})
        self.assertEqual(denied_review.status_code,403)
        with patch.dict(os.environ,{'OMNI_RIGHTS_REVIEW_KEY':'review-secret-123'},clear=False):
            for evidence_id in evidence_ids:
                reviewed=self.c.post(f'/api/v27/projects/{pid}/rights/review',headers={**h,'X-Omni-Rights-Review-Key':'review-secret-123'},json={'evidence_id':evidence_id,'reviewer_note':'verified against signed source'})
                self.assertEqual(reviewed.status_code,200,reviewed.text)
                self.assertTrue(reviewed.json()['record']['verified'])
        status=self.c.get(f'/api/v27/projects/{pid}/rights',headers=h).json()
        self.assertEqual(status['status'],'CLEAR')
        promoted=self.c.post(f'/api/v27/projects/{pid}/promote',headers=h)
        self.assertEqual(promoted.status_code,200,promoted.text)

    def test_original_alternative_and_cross_user_rights_isolation(self):
        t1=self._register('v27-owner@example.com'); t2=self._register('v27-other@example.com')
        h1=self._auth(t1); h2=self._auth(t2)
        pid=self.c.post('/api/v27/projects',headers=h1,json={'title':'IP Project'}).json()['id']
        self.c.post(f'/api/v27/projects/{pid}/build',headers=h1,json={'prompt':'Create a game like Mario','target_markets':['US']})
        alt=self.c.post(f'/api/v27/projects/{pid}/rights/original-alternative',headers=h1,json={})
        self.assertEqual(alt.status_code,200,alt.text)
        self.assertNotIn('Mario',alt.json()['original_brief'])
        denied=self.c.get(f'/api/v27/projects/{pid}/rights',headers=h2)
        self.assertEqual(denied.status_code,403)

    def test_company_os_endpoint(self):
        d=self.c.get('/api/v27/company-os').json()
        self.assertGreaterEqual(len(d['departments']),13)
        self.assertIn('release_council',d)


    def test_company_os_operating_endpoints(self):
        triage=self.c.post('/api/v27/company-os/triage',json={'signals':[
            {'kind':'rights_alert','title':'Unlicensed celebrity voice','severity':'critical'},
            {'kind':'build_failure','title':'Android build failed','severity':'high'},
        ]})
        self.assertEqual(triage.status_code,200,triage.text)
        tasks=triage.json()['tasks']
        self.assertEqual(tasks[0]['department_id'],'legal')
        self.assertEqual(tasks[0]['priority'],'P0')
        brief=self.c.post('/api/v27/company-os/ceo-brief',json={
            'signals':[{'kind':'cost_alert','title':'GPU cost increased','severity':'high'}],
            'metrics':{'accepted_build_rate':0.82,'runway_months':12}
        })
        self.assertEqual(brief.status_code,200,brief.text)
        self.assertTrue(brief.json()['founder_approval_queue'])
        gates={k:True for k in (
            'product_acceptance','engineering_regression','qa_evals','security_tenant_isolation',
            'rights_ip','infrastructure_readiness','backup_restore')}
        council=self.c.post('/api/v27/company-os/release-council/evaluate',json={'gates':gates,'founder_public_launch_approved':True})
        self.assertEqual(council.status_code,200,council.text)
        self.assertTrue(council.json()['public_launch_ready'])

if __name__=='__main__': unittest.main()

class V27SecretSeparationTests(unittest.TestCase):
    def test_control_plane_and_generated_app_secrets_can_be_distinct(self):
        from omni_prod.v27_platform import V27UniversalPlatform
        p=V27UniversalPlatform(token_secret='control-'+'c'*48,generated_app_token_secret='runtime-'+'r'*48)
        r=p.register(email='separate@example.com',password='StrongPass123!'); token=r['token']
        project=p.create_project(token=token,title='Separate secrets')
        p.build(token=token,project_id=project['id'],prompt='Build an original CRM',target_markets=('US',))
        promoted=p.promote(token=token,project_id=project['id']); dep=promoted['deployment_id']
        role,rt=p.engine.runtime(dep).register(email='runtime@example.com',credential='StrongPass123!')
        self.assertEqual(role,'admin')
        self.assertEqual(p.account(token).email,'separate@example.com')
        with self.assertRaises(PermissionError):
            p.engine.runtime(dep).list(token=token,collection='items')
        self.assertEqual(p.engine.runtime(dep).list(token=rt,collection='items'),[])

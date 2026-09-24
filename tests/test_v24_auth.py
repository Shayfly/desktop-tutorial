import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from omni_prod.auth import issue_token, verify_token, AuthError
from omni_prod.investor_app import app

SECRET='x'*64
class AuthUnitTests(unittest.TestCase):
    def test_round_trip(self):
        t=issue_token(secret=SECRET,user_id='u',org_id='o',role='owner',ttl_seconds=100,now=1000)
        c=verify_token(t,secret=SECRET,now=1050); self.assertEqual(c.user_id,'u'); self.assertEqual(c.role,'owner')
    def test_expiry(self):
        t=issue_token(secret=SECRET,user_id='u',org_id='o',role='owner',ttl_seconds=10,now=1000)
        with self.assertRaises(AuthError): verify_token(t,secret=SECRET,now=1010)
    def test_tamper(self):
        t=issue_token(secret=SECRET,user_id='u',org_id='o',role='owner',ttl_seconds=10,now=1000)
        with self.assertRaises(AuthError): verify_token(t+'x',secret=SECRET,now=1001)

class AuthApiTests(unittest.TestCase):
    def test_production_protected_route_requires_auth(self):
        with patch.dict(os.environ,{'OMNI_ENV':'production','OMNI_SECRET_KEY':SECRET},clear=False):
            c=TestClient(app); r=c.post('/api/demo/build',json={'prompt':'Build CRM','project_id':'p'})
            self.assertEqual(r.status_code,401)
    def test_production_token_allows_route(self):
        t=issue_token(secret=SECRET,user_id='u',org_id='o',role='owner',ttl_seconds=3600)
        with patch.dict(os.environ,{'OMNI_ENV':'production','OMNI_SECRET_KEY':SECRET},clear=False):
            c=TestClient(app); r=c.post('/api/demo/build',headers={'Authorization':'Bearer '+t},json={'prompt':'Build CRM','project_id':'auth-p'})
            self.assertEqual(r.status_code,200)

import io
import json
import os
import unittest
import zipfile
from unittest.mock import patch
from fastapi.testclient import TestClient
from omni_prod.investor_app import app
from omni_prod.native_source import android_project, ios_project, game_project
from omni_prod.rate_limit import InMemoryFixedWindowLimiter
from omni_prod.remote_sandbox import RemoteSandboxConfig, RemoteSandboxRepositoryExecutor, sign_body
from omni_prod.demo_project import demo_spec, create_demo_repository
from omni_prod.secrets_manager import EnvSecretResolver, SecretResolutionError

class FakeResponse:
    def __init__(self,payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.payload).encode()

class NativeSourceTests(unittest.TestCase):
    def test_android_source_contains_gradle_manifest_and_kotlin(self):
        r=android_project(app_name='Field CRM',application_id='com.example.fieldcrm')
        self.assertIn('app/build.gradle.kts',r); self.assertIn('app/src/main/AndroidManifest.xml',r)
        self.assertTrue(any(x.endswith('MainActivity.kt') for x in r))
    def test_ios_source_has_xcodegen_and_swiftui(self):
        r=ios_project(app_name='Field CRM'); self.assertIn('project.yml',r); self.assertIn('Sources/OmniApp.swift',r)
    def test_game_sources_have_real_engine_markers(self):
        self.assertIn('project.godot',game_project('godot'))
        self.assertIn('ProjectSettings/ProjectVersion.txt',game_project('unity'))
        self.assertTrue(any(x.endswith('.uproject') for x in game_project('unreal')))

class RemoteSandboxTests(unittest.TestCase):
    def test_signature_deterministic(self):
        self.assertEqual(sign_body('x'*32,b'a'),sign_body('x'*32,b'a'))
        self.assertNotEqual(sign_body('x'*32,b'a'),sign_body('x'*32,b'b'))
    def test_secret_minimum(self):
        with self.assertRaises(ValueError): RemoteSandboxConfig('https://runner','short')
    def test_remote_executor_maps_success(self):
        def fake(req,timeout): return FakeResponse({'returncode':0,'stdout':'ok','stderr':''})
        cfg=RemoteSandboxConfig('https://runner','x'*32); ex=RemoteSandboxRepositoryExecutor(cfg,urlopen=fake)
        spec=demo_spec('Build CRM'); repo=create_demo_repository('Build CRM',spec)
        self.assertTrue(ex.execute(repository=repo,spec=spec).passed)
    def test_remote_executor_maps_verification_failure(self):
        calls={'n':0}
        def fake(req,timeout):
            calls['n']+=1
            return FakeResponse({'returncode':1 if calls['n']==1 else 0,'stdout':'','stderr':'bad'})
        cfg=RemoteSandboxConfig('https://runner','x'*32); ex=RemoteSandboxRepositoryExecutor(cfg,urlopen=fake)
        spec=demo_spec('Build CRM'); repo=create_demo_repository('Build CRM',spec)
        report=ex.execute(repository=repo,spec=spec); self.assertFalse(report.passed); self.assertTrue(report.failures)

class RateSecretTests(unittest.TestCase):
    def test_rate_limit(self):
        now=[60]
        l=InMemoryFixedWindowLimiter(limit=2,window_seconds=60,clock=lambda:now[0])
        self.assertTrue(l.check('u').allowed); self.assertTrue(l.check('u').allowed); self.assertFalse(l.check('u').allowed)
        now[0]=120; self.assertTrue(l.check('u').allowed)
    def test_env_secret_reference(self):
        with patch.dict(os.environ,{'PAYMENT_SECRET':'abc123'},clear=False): self.assertEqual(EnvSecretResolver().resolve('env:PAYMENT_SECRET'),'abc123')
    def test_bad_secret_ref(self):
        with self.assertRaises(SecretResolutionError): EnvSecretResolver().resolve('raw:abc')

class DownloadTests(unittest.TestCase):
    def test_download_version_zip(self):
        c=TestClient(app); d=c.post('/api/demo/build',json={'prompt':'Build CRM','project_id':'download-p'}).json(); vid=d['version']['id']
        r=c.get(f'/api/projects/download-p/versions/{vid}/download'); self.assertEqual(r.status_code,200)
        z=zipfile.ZipFile(io.BytesIO(r.content)); self.assertIn('index.html',z.namelist()); self.assertIn('X-Omni-Repository-SHA256',r.headers)
    def test_source_endpoints(self):
        c=TestClient(app); self.assertGreater(c.get('/api/source/mobile/android').json()['repository']['file_count'],4)
        self.assertGreater(c.get('/api/source/game/godot').json()['repository']['file_count'],2)

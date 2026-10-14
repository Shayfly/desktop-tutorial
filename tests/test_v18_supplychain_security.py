import unittest
from omni_prod.attestation import build_attestation
from omni_prod.cors_policy import parse_and_validate_origins
from omni_prod.dependency_inventory import parse_requirements,lock_status
from omni_prod.sbom import build_cyclonedx_bom
class DependencyInventoryTests(unittest.TestCase):
    def test_exact_pin_is_locked(self):
        self.assertTrue(lock_status(parse_requirements('fastapi==1.2.3\nhttpx==4.5.6\n'))['locked'])
    def test_range_is_not_locked(self):
        s=lock_status(parse_requirements('fastapi>=1,<2\n')); self.assertFalse(s['locked']); self.assertEqual(s['unpinned'],['fastapi'])
    def test_direct_url_is_rejected(self):
        with self.assertRaises(ValueError): parse_requirements('thing @ https://example.com/x.whl')
class SBOMTests(unittest.TestCase):
    def test_bom_contains_unresolved_constraint(self):
        b=build_cyclonedx_bom(parse_requirements('fastapi==1.2.3\nredis>=5,<6\n'),component_name='Omni',version='V18')
        self.assertEqual(b['bomFormat'],'CycloneDX'); self.assertEqual(len(b['components']),2)
        r=[c for c in b['components'] if c['name']=='redis'][0]; self.assertEqual(r['properties'][1]['value'],'false')
class CORSPolicyTests(unittest.TestCase):
    def test_production_requires_https(self):
        with self.assertRaises(ValueError): parse_and_validate_origins('http://app.example.com',production=True)
    def test_wildcard_rejected(self):
        with self.assertRaises(ValueError): parse_and_validate_origins('*',production=True)
    def test_valid_https_origin(self):
        self.assertEqual(parse_and_validate_origins('https://app.example.com',production=True),['https://app.example.com'])
class AttestationTests(unittest.TestCase):
    def test_unsigned_is_explicit(self):
        a=build_attestation(subject_name='release.zip',subject_sha256='a'*64,builder='local',metadata={})
        self.assertFalse(a['predicate']['signed']); self.assertEqual(a['predicate']['signature_status'],'UNSIGNED_LOCAL_ATTESTATION')
if __name__=='__main__': unittest.main()

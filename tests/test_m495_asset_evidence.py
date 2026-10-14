from __future__ import annotations

import json
import unittest
from decimal import Decimal

from omni_prod.media_pipeline import CreativeDirector


class AssetEvidenceManifestTests(unittest.TestCase):
    def setUp(self):
        self.director=CreativeDirector()
        self.plan=self.director.plan('Build a 3D game', targets=('web','game3d'))

    def test_legacy_manifest_shape_remains_readable_without_materialization_evidence(self):
        files=self.director.repository_files(self.plan)
        payload=json.loads(files['assets/148ai-asset-manifest.json'])
        self.assertIn('requests', payload)
        self.assertIn('accessibility', payload)
        self.assertIn('rights_policy', payload)
        self.assertNotIn('capability_materializations', payload)
        self.assertGreaterEqual(payload['schema_version'], 2)
        self.assertEqual(files['assets/148ai-asset-manifest.json'], files['assets/omni-asset-manifest.json'])

    def test_verified_capability_evidence_is_additive_and_preserves_unknown_actual(self):
        evidence={
            'requirements':[{
                'requirement_id':'cap-media-3d-mesh-generate',
                'capability_key':'media.3d.mesh.generate', 'required':True,
                'status':'VERIFIED', 'selected_provider':'fake-3d',
                'pricing_version':'price-v1', 'artifact_key':'projects/p/b/cap/mesh.glb',
                'verification':{'sha256':'a'*64,'size_bytes':123,'authorization':'secret-value'},
            }],
            'usage':[{
                'requirement_id':'cap-media-3d-mesh-generate','provider':'fake-3d',
                'estimated_cost_usd':Decimal('0.40'),'maximum_cost_usd':Decimal('0.60'),
                'actual_cost_usd':None,'pricing_version':'price-v1',
                'evidence':{'provenance':{'provider_task_id':'task-1'}},
            }],
        }
        files=self.director.repository_files(self.plan, capability_evidence=evidence)
        payload=json.loads(files['assets/148ai-asset-manifest.json'])
        item=payload['capability_materializations'][0]
        self.assertEqual(item['capability_key'],'media.3d.mesh.generate')
        self.assertEqual(item['artifact_key'],'projects/p/b/cap/mesh.glb')
        self.assertEqual(item['actual_cost_usd'], None)
        self.assertEqual(item['estimated_cost_usd'],'0.40')
        self.assertEqual(item['maximum_cost_usd'],'0.60')
        self.assertEqual(item['cost_truth'],'ESTIMATE_ONLY')
        self.assertEqual(item['provenance']['provider_task_id'],'task-1')
        serialized=json.dumps(payload)
        self.assertNotIn('secret-value', serialized)
        self.assertEqual(item['verification']['authorization'],'[REDACTED]')


if __name__=='__main__': unittest.main()

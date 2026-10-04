from __future__ import annotations

import hashlib
import json
import struct
import unittest
from decimal import Decimal

from omni_prod.capability_executor import CapabilityExecutionAssignment, CapabilityExecutor
from omni_prod.capability_planner import CapabilityPlanner
from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.capability_worker import DurableCapabilityBuildStage, DEFAULT_NATIVE_BUILD_CAPABILITIES
from omni_prod.media_pipeline import CreativeDirector
from omni_prod.provider_contracts import (
    ProviderArtifactPayload, ProviderCapability, ProviderExecutionResult,
    ProviderQuote, ProviderTaskHandle, ProviderTaskState,
)
from omni_prod.provider_pricing import ProviderPriceCatalog, ProviderPriceEntry, PriceStatus
from omni_prod.provider_registry import ProviderRegistry
from omni_prod.storage import StoredObject
from omni_prod.unified_engine import UnifiedPromptPlanner


def _glb() -> bytes:
    body = b'{}  '
    total = 12 + 8 + len(body)
    return struct.pack('<4sII', b'glTF', 2, total) + struct.pack('<I4s', len(body), b'JSON') + body


PNG = b'\x89PNG\r\n\x1a\n' + b'golden-png-bytes'
WAV = b'RIFF' + (8).to_bytes(4, 'little') + b'WAVE' + b'golden-wav'
GLB = _glb()


class GoldenStore:
    def __init__(self): self.objects = {}
    def put_bytes(self, key, data):
        data = bytes(data); self.objects[key] = data
        return StoredObject(key=key, sha256=hashlib.sha256(data).hexdigest(), size=len(data))
    def get_bytes(self, key, *, verify=True): return self.objects[key]
    def iter_bytes(self, key, **kwargs):
        data = self.objects[key]
        for start in range(0, len(data), 7):
            yield data[start:start+7]


class GoldenMultimodalProvider:
    name = 'fake-multimodal'
    durable_idempotency = True
    durable_result_retrieval = True
    paid_external = True

    FORMATS = {
        'media.image.generate': ('image/png', PNG, 'image.png'),
        'media.3d.mesh.generate': ('model/gltf-binary', GLB, 'mesh.glb'),
        'media.3d.texture': ('image/png', PNG, 'texture.png'),
        'media.audio.sfx': ('audio/wav', WAV, 'sfx.wav'),
        'media.audio.music': ('audio/wav', WAV, 'music.wav'),
    }

    def __init__(self):
        self.requests = {}
        self.submit_count = 0

    def capabilities(self):
        return tuple(ProviderCapability(key, (mime,), True) for key, (mime, _, _) in self.FORMATS.items())

    def health(self): return 'HEALTHY'

    def quote(self, requirement):
        return ProviderQuote(self.name, requirement.key, Decimal('0.05'), Decimal('0.10'), 'golden-prices-v1', 'asset', Decimal('1'))

    def submit(self, requirement, *, idempotency_key):
        self.submit_count += 1
        task_id = 'golden-' + hashlib.sha256(idempotency_key.encode()).hexdigest()[:20]
        self.requests[task_id] = requirement
        return ProviderTaskHandle(self.name, task_id, requirement.id, idempotency_key)

    def poll(self, handle): return ProviderTaskState('SUCCEEDED', 1.0)

    def collect(self, handle):
        requirement = self.requests[handle.provider_task_id]
        mime, data, filename = self.FORMATS[requirement.key]
        return ProviderExecutionResult(
            artifacts=(), actual_cost_usd=Decimal('0.04'),
            usage={'assets': 1},
            evidence={'provenance': {'provider_task_id': handle.provider_task_id, 'test_provider': True}},
            payloads=(ProviderArtifactPayload(mime, data, filename=filename),),
        )

    def cancel(self, handle): pass


def _catalog() -> ProviderPriceCatalog:
    entries = [
        ProviderPriceEntry(
            provider='fake-multimodal', capability_key=key, operation='generate', unit_name='asset',
            estimated_unit_cost_usd=Decimal('0.05'), maximum_unit_cost_usd=Decimal('0.10'),
            status=PriceStatus.PUBLIC_LIST_PRICE, effective_from='2026-10-04',
            source_reference='golden-test-only',
        )
        for key in GoldenMultimodalProvider.FORMATS
    ]
    return ProviderPriceCatalog(version='golden-prices-v1', entries=entries)


class M495GoldenAcceptanceTests(unittest.TestCase):
    def test_3d_game_prompt_executes_verified_multimodal_vertical_slice_without_fake_commercial_claim(self):
        prompt = 'Build a 3D delivery racing game in Unreal with original environment, textures, sound effects and adaptive music'
        unified = UnifiedPromptPlanner().plan(prompt)
        creative = CreativeDirector().plan(prompt, targets=unified.targets)
        plan = CapabilityPlanner(CapabilityRegistry()).plan(prompt=prompt, unified_plan=unified, creative_plan=creative)
        keys = {requirement.key for requirement in plan.requirements}
        required = {
            'software.code.generate', 'software.build', 'software.test', 'target.game.3d',
            'media.image.generate', 'media.3d.mesh.generate', 'media.3d.texture', 'media.audio.sfx', 'media.audio.music',
        }
        self.assertTrue(required.issubset(keys))

        provider = GoldenMultimodalProvider()
        provider_registry = ProviderRegistry((provider,))
        repository = MemoryCapabilityRepository()
        store = GoldenStore()
        executor = CapabilityExecutor(
            provider_registry=provider_registry, repository=repository, artifact_store=store,
            worker_id='golden-worker', lease_seconds=30, max_polls=3,
        )
        catalog = _catalog()

        def assignments_resolver(capability_plan):
            assignments = {}
            for requirement in capability_plan.requirements:
                if requirement.key in GoldenMultimodalProvider.FORMATS:
                    assignments[requirement.id] = CapabilityExecutionAssignment(
                        'fake-multimodal', catalog.quote(provider='fake-multimodal', requirement=requirement)
                    )
            return assignments

        native = set(DEFAULT_NATIVE_BUILD_CAPABILITIES) | {'target.game.3d'}
        stage = DurableCapabilityBuildStage(
            repository=repository, native_capability_keys=native,
            executor=executor, assignments_resolver=assignments_resolver,
        )
        prepared = stage.prepare(
            build_id='golden-build', project_id='tenant-golden', plan=plan,
            authorized_maximum_usd=Decimal('1.00'), now=100,
        )
        self.assertTrue(prepared['required_ready'])
        final = stage.finalize_native(
            build_id='golden-build', plan=plan, core_ready=True,
            evidence={'verification': True, 'quality': True, 'security': True, 'rights': True},
        )
        self.assertTrue(final['required_ready'])
        self.assertEqual(final['status'], 'VERIFIED')

        external_rows = [r for r in repository.requirements(build_id='golden-build') if r['capability_key'] in GoldenMultimodalProvider.FORMATS]
        self.assertTrue(external_rows)
        self.assertTrue(all(row['status'] == 'VERIFIED' for row in external_rows))
        usage = repository.usage_for_build(build_id='golden-build')
        self.assertEqual(len(usage), len(external_rows))
        actual_total = sum((event['actual_cost_usd'] for event in usage), Decimal('0'))
        maximum_total = sum((event['maximum_cost_usd'] for event in usage), Decimal('0'))
        self.assertEqual(actual_total, Decimal('0.04') * len(usage))
        self.assertLessEqual(actual_total, maximum_total)
        self.assertEqual(provider.submit_count, len(external_rows))
        self.assertEqual(len(store.objects), len(external_rows))

        manifest = json.loads(CreativeDirector().repository_files(creative, capability_evidence=final)['assets/148ai-asset-manifest.json'])
        materialized = manifest['capability_materializations']
        self.assertEqual(len(materialized), len(external_rows))
        self.assertTrue(all(item['cost_truth'] == 'ACTUAL' for item in materialized))
        self.assertTrue(all(item['provider'] == 'fake-multimodal' for item in materialized))
        self.assertNotIn('tripo', json.dumps(manifest).lower())
        self.assertNotIn('meshy', json.dumps(manifest).lower())


if __name__ == '__main__': unittest.main()

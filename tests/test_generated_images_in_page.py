"""#324 (Michael 2026-11-13): the plan's verified generated images go INTO the page.

Production bld_cf406df6 (2026-11-12): media.image.generate was VERIFIED and stored, but the page showed an
illustration the code model drew itself -- the stage's evidence never reached code generation. Michael's conditions:
(1) inserted only when the plan asked for an image; (2) dimensions and purpose go to the model; (3) alt is mandatory
and comes from the brief; (4) the blocking check stays, with a non-empty alt on top. Several images, not one hero."""
import hashlib
import struct
import unittest
import zlib
from types import SimpleNamespace

from omni_prod import generated_images as G
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_executor import CapabilityExecutionAssignment, CapabilityExecutor
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.capability_worker import DurableCapabilityBuildStage
from omni_prod.provider_contracts import ProviderArtifactPayload, ProviderExecutionResult
from omni_prod.provider_registry import ProviderRegistry
from tests.test_m495_capability_executor import FakeProvider, MemoryStore, quote

# the production request, word for word
CAFE = ('דף נחיתה לבית קפה קטן, עם תמונה ראשית גדולה של כוס קפה על שולחן עץ ליד חלון, כותרת, שעות פתיחה וכפתור '
        '"הזמנת שולחן". --- Approved project brief (binding; fingerprint 6fc5a369d80268fc) --- Sign-in: NONE.')
CUP = 'תמונה ראשית גדולה של כוס קפה על שולחן עץ ליד חלון'


def png(width, height, seed=0):
    raw = b''.join(b'\x00' + bytes([seed % 256]) * (width * 3) for _ in range(height))
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def image_req(rid='cap-media-image-generate', purpose='hero/brand visual'):
    return CapabilityRequirement(rid, G.IMAGE_CAPABILITY, purpose, True)


def evidence_for(store, rows):
    """A capability-stage snapshot: rows of (requirement_id, status, [image bytes])."""
    out = []
    for rid, status, blobs in rows:
        arts = []
        for i, data in enumerate(blobs, start=1):
            key = f'projects/t/builds/b/capabilities/{rid}/{rid}-{i}.png'
            store.objects[key] = data
            arts.append({'verified': True, 'sha256': hashlib.sha256(data).hexdigest(), 'size_bytes': len(data),
                         'artifact_key': key, 'mime_type': 'image/png'})
        out.append({'requirement_id': rid, 'capability_key': G.IMAGE_CAPABILITY, 'required': True, 'status': status,
                    'artifact_key': arts[0]['artifact_key'] if arts else None, 'verification': {'artifacts': arts}})
    return {'requirements': out}


class Passing:
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'ok')


def engine():
    return SimpleNamespace(core=SimpleNamespace(executor=Passing(), repository_transform=None))


class AltFromTheBrief(unittest.TestCase):                                        # condition 3
    def test_the_clause_that_describes_the_image(self):
        self.assertEqual(G.describe(CAFE, 'hero/brand visual'), CUP)
        self.assertEqual(G.alt_text(CAFE, 'hero/brand visual'), CUP)

    def test_only_the_request_not_the_brief_block(self):
        self.assertIsNone(G.describe('דף נחיתה לבית קפה. --- Approved project brief --- hero image of x', 'hero'))

    def test_without_a_clause_the_product_line_of_the_request(self):
        alt = G.alt_text('דף נחיתה לבית קפה קטן, עם שעות פתיחה', 'hero/brand visual')
        self.assertEqual(alt, 'תמונה ראשית — דף נחיתה לבית קפה קטן')
        self.assertEqual(G.alt_text('A landing page for a bakery. Hours.', 'hero/brand visual'),
                         'Main image — A landing page for a bakery')

    def test_an_icon_uses_the_logo_clause(self):
        self.assertEqual(G.describe('אתר לחנות, עם לוגו של עלה ירוק, וטופס', 'product icon'), 'לוגו של עלה ירוק')

    def test_several_images_of_one_requirement_are_numbered(self):
        self.assertEqual(G.alt_text(CAFE, 'hero/brand visual', number=2, of=3), CUP + ' (2/3)')

    def test_never_empty(self):
        with self.assertRaises(ValueError):
            G.alt_text('', 'hero/brand visual')


class OnlyWhatThePlanAskedFor(unittest.TestCase):                                # condition 1
    def setUp(self):
        self.store = MemoryStore()

    def test_a_verified_requested_image_is_collected_with_its_dimensions(self):
        ev = evidence_for(self.store, [('cap-media-image-generate', 'VERIFIED', [png(64, 36)])])
        [img] = G.collect(plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=self.store, prompt=CAFE)
        self.assertEqual((img.marker, img.mime, img.width, img.height, img.alt),
                         ('148ai-asset://image/1', 'image/png', 64, 36, CUP))

    def test_no_image_in_the_plan_nothing_is_inserted(self):
        ev = evidence_for(self.store, [('cap-media-image-generate', 'VERIFIED', [png(8, 8)])])
        plan = CapabilityPlan((CapabilityRequirement('cap-target-web', 'target.web', 'web', True),), ('target.web',))
        self.assertEqual(G.collect(plan=plan, evidence=ev, store=self.store, prompt=CAFE), [])

    def test_an_image_that_is_not_verified_is_never_inserted(self):
        for status in ('PLANNED', 'FAILED', 'NOT_CONFIGURED', 'SKIPPED'):
            ev = evidence_for(self.store, [('cap-media-image-generate', status, [png(8, 8)])])
            self.assertEqual(G.collect(plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=self.store,
                                       prompt=CAFE), [], status)

    def test_bytes_that_changed_since_verification_are_refused(self):
        ev = evidence_for(self.store, [('cap-media-image-generate', 'VERIFIED', [png(8, 8)])])
        key = ev['requirements'][0]['artifact_key']
        self.store.objects[key] = png(9, 9)
        with self.assertRaises(ValueError):
            G.collect(plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=self.store, prompt=CAFE)

    def test_several_images_each_get_a_marker(self):
        plan = CapabilityPlan((image_req('cap-a', 'hero/brand visual'), image_req('cap-b', 'product icon')), ())
        ev = evidence_for(self.store, [('cap-a', 'VERIFIED', [png(16, 9, 1), png(16, 9, 2)]),
                                       ('cap-b', 'VERIFIED', [png(8, 8, 3)])])
        imgs = G.collect(plan=plan, evidence=ev, store=self.store,
                         prompt='דף לבית קפה, עם תמונה ראשית של כוס קפה, ועם לוגו של פול קפה, וכפתור')
        self.assertEqual([i.marker for i in imgs], [G.MARKER_PREFIX + n for n in '123'])
        self.assertEqual([i.alt for i in imgs], ['תמונה ראשית של כוס קפה (1/2)', 'תמונה ראשית של כוס קפה (2/2)',
                                                 'לוגו של פול קפה'])
        self.assertEqual(len({i.sha256 for i in imgs}), 3)


class WhatTheModelIsTold(unittest.TestCase):                                     # condition 2
    def test_purpose_dimensions_marker_and_alt(self):
        store = MemoryStore()
        ev = evidence_for(store, [('cap-media-image-generate', 'VERIFIED', [png(1024, 576)])])
        block = G.prompt_block(G.collect(plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=store,
                                         prompt=CAFE))
        for part in ('src="148ai-asset://image/1"', 'purpose: hero/brand visual', '1024x576 px', 'image/png',
                     f'alt="{CUP}"', 'Do NOT draw a replacement'):
            self.assertIn(part, block)


class TheBlockingCheck(unittest.TestCase):                                       # condition 4
    def setUp(self):
        store = MemoryStore()
        ev = evidence_for(store, [('cap-media-image-generate', 'VERIFIED', [png(8, 8)])])
        self.e = engine()
        self.prompt = G.install(self.e, prompt=CAFE, plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=store)
        [self.img] = self.e.core.generated_images

    def run_page(self, html, path='index.html'):
        repo = self.e.core.repository_transform({path: html})
        return self.e.core.executor.execute(repository=repo, spec=None)

    def failures(self, html, path='index.html'):
        return [f for f in self.run_page(html, path).failures if f.acceptance_id == G.ACCEPTANCE_ID]

    def test_used_with_the_alt_passes(self):
        self.assertTrue(self.run_page(f'<img src="{self.img.marker}" alt="{CUP}">').passed)

    def test_not_on_the_page_fails(self):
        [f] = self.failures('<svg><rect/></svg>')
        self.assertIn('is not on the page', f.message)

    def test_missing_alt_fails(self):
        [f] = self.failures(f'<img src="{self.img.marker}">')
        self.assertIn('empty or missing alt', f.message)

    def test_empty_or_blank_alt_fails(self):
        for alt in ('""', '"   "', "''"):
            self.assertTrue(self.failures(f'<img alt={alt} src="{self.img.marker}">'), alt)

    def test_a_reference_in_a_comment_does_not_count(self):
        self.assertTrue(self.failures(f'<!-- <img src="{self.img.marker}" alt="x"> --><p>hi</p>'))

    def test_jsx_literal_alt_passes(self):
        self.assertTrue(self.run_page(f'export default () => <img src="{self.img.marker}" alt={{"{CUP}"}} />',
                                      'src/App.jsx').passed)

    def test_the_failure_tells_the_repair_the_marker_and_alt(self):
        [f] = self.failures('<p>no image</p>')
        self.assertIn(self.img.marker, f.message)
        self.assertIn(CUP, f.message)


class MarkerAndBytes(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        ev = evidence_for(self.store, [('cap-media-image-generate', 'VERIFIED', [png(8, 8)])])
        self.ev = ev

    def test_the_marker_becomes_the_verified_bytes_and_back(self):
        e = engine()
        G.install(e, prompt=CAFE, plan=CapabilityPlan((image_req(),), ()), evidence=self.ev, store=self.store)
        [img] = e.core.generated_images
        repo = e.core.repository_transform({'index.html': f'<img src="{img.marker}" alt="a">'})
        self.assertIn('data:image/png;base64,', repo['index.html'])
        self.assertNotIn(img.marker, repo['index.html'])
        self.assertEqual(e.core.repository_transform.redact(repo), {'index.html': f'<img src="{img.marker}" alt="a">'})
        cut = img.uri[:len(img.uri) // 2]
        self.assertNotIn(img.uri.split(',', 1)[1][:40], e.core.repository_transform.redact_text('log ' + cut))

    def test_it_chains_onto_the_uploaded_logo_and_keeps_its_redaction(self):
        from omni_prod.uploaded_assets import logo_transform
        data = png(4, 4, 7)
        logo = logo_transform(data, 'image/png', hashlib.sha256(data).hexdigest())
        e = SimpleNamespace(core=SimpleNamespace(executor=Passing(), repository_transform=logo))
        G.install(e, prompt=CAFE, plan=CapabilityPlan((image_req(),), ()), evidence=self.ev, store=self.store)
        [img] = e.core.generated_images
        page = f'<img src="148ai-asset://logo" alt="logo"><img src="{img.marker}" alt="a">'
        repo = e.core.repository_transform({'index.html': page})
        self.assertNotIn('148ai-asset://', repo['index.html'])                  # both replaced
        self.assertEqual(e.core.repository_transform.redact(repo), {'index.html': page})   # both redacted

    def test_no_image_requested_the_build_is_untouched(self):
        e = engine()
        executor = e.core.executor
        self.assertEqual(G.install(e, prompt=CAFE, plan=CapabilityPlan((), ()), evidence=self.ev, store=self.store),
                         CAFE)
        self.assertIs(e.core.executor, executor)
        self.assertIsNone(e.core.repository_transform)


class FromTheRealCapabilityStage(unittest.TestCase):
    """The stage's own evidence (CapabilityExecutor -> DurableCapabilityBuildStage snapshot) names every
    artifact's key, so a requirement that produced several images hands all of them over."""

    def test_end_to_end_two_images_of_one_requirement(self):
        a, b = png(32, 18, 1), png(32, 18, 2)
        provider = FakeProvider(result_factory=lambda h: ProviderExecutionResult(
            artifacts=(), actual_cost_usd=None, usage={'images': 2}, evidence={},
            payloads=(ProviderArtifactPayload('image/png', a, filename='hero-1.png'),
                      ProviderArtifactPayload('image/png', b, filename='hero-2.png'))))
        repo, store = MemoryCapabilityRepository(), MemoryStore()
        executor = CapabilityExecutor(provider_registry=ProviderRegistry((provider,)), repository=repo,
                                      artifact_store=store, worker_id='w', lease_seconds=5, max_polls=5)
        req = CapabilityRequirement('cap-media-image-generate', G.IMAGE_CAPABILITY, 'hero/brand visual', True,
                                    quantity=2)
        plan = CapabilityPlan((req,), ())
        stage = DurableCapabilityBuildStage(
            repository=repo, executor=executor,
            assignments_resolver=lambda p: {req.id: CapabilityExecutionAssignment('media', quote())})
        ev = stage.prepare(build_id='b1', project_id='p1', plan=plan, authorized_maximum_usd='1', now=100)
        arts = ev['requirements'][0]['verification']['artifacts']
        self.assertEqual(len({x['artifact_key'] for x in arts}), 2)              # each artifact names its own key
        e = engine()
        prompt = G.install(e, prompt=CAFE, plan=plan, evidence=ev, store=store)
        imgs = e.core.generated_images
        self.assertEqual([i.data for i in imgs], [a, b])
        self.assertIn('148ai-asset://image/2', prompt)
        page = ''.join(f'<img src="{i.marker}" alt="{i.alt}">' for i in imgs)
        self.assertTrue(e.core.executor.execute(repository=e.core.repository_transform({'index.html': page}),
                                                spec=None).passed)
        only_one = f'<img src="{imgs[0].marker}" alt="x">'
        self.assertFalse(e.core.executor.execute(repository=e.core.repository_transform({'index.html': only_one}),
                                                 spec=None).passed)


if __name__ == '__main__':
    unittest.main()


class TheWorkerWiresItIn(unittest.TestCase):
    """_run_live_build_job hands the stage's verified images to code generation, before engine.build."""

    def run_build(self, plan, evidence, store):
        from decimal import Decimal
        from unittest.mock import MagicMock
        from omni_prod import worker_tasks
        from tests.test_m495_worker_capabilities import FakeJobs, passing_engine, platform_for
        seen = {}
        engine = passing_engine()
        build = engine.build
        engine.build = lambda prompt: (seen.setdefault('prompt', prompt), build(prompt))[1]
        stage = SimpleNamespace(executor=SimpleNamespace(artifact_store=store),
                                prepare=lambda **kw: evidence,
                                finalize_native=lambda **kw: {'required_ready': True, 'status': 'VERIFIED',
                                                              'requirements': evidence['requirements']})
        jobs = FakeJobs(plan)
        jobs.request['prompt'] = CAFE
        workspace = MagicMock()
        workspace.commit.return_value = SimpleNamespace(id='v1', artifact_key='a.zip')
        gateway = SimpleNamespace(state=SimpleNamespace(external_spend_usd=Decimal('0'), external_calls=0),
                                  events=[], bind_budget=lambda ceiling: {'effective_budget_usd': str(ceiling)})
        worker_tasks._run_live_build_job(
            'b1', jobs=jobs, platform=platform_for(plan), workspace=workspace,
            components_factory=lambda: (engine, gateway),
            quality_fn=lambda **kw: SimpleNamespace(passed=True, score=100, minimum_score=80, blockers=(),
                                                    to_dict=lambda: {}),
            security_fn=lambda repo: SimpleNamespace(passed=True, findings=(), to_dict=lambda: {}),
            capability_stage=stage)
        return engine, seen['prompt']

    def test_a_requested_verified_image_reaches_code_generation(self):
        store = MemoryStore()
        plan = CapabilityPlan((image_req(),), ())
        ev = evidence_for(store, [('cap-media-image-generate', 'VERIFIED', [png(40, 30)])])
        engine, prompt = self.run_build(plan, ev, store)
        self.assertIn('src="148ai-asset://image/1"', prompt)
        self.assertIn('40x30 px', prompt)
        self.assertEqual(len(engine.generated_images), 1)
        self.assertIsInstance(engine.executor, G.GeneratedImagesExecutor)

    def test_no_image_in_the_plan_the_prompt_is_unchanged(self):
        store = MemoryStore()
        plan = CapabilityPlan((CapabilityRequirement('cap-plan', 'software.plan', 'plan', True),), ())
        ev = {'required_ready': True, 'status': 'VERIFIED', 'requirements': []}
        engine, prompt = self.run_build(plan, ev, store)
        self.assertNotIn(G.MARKER_PREFIX, prompt)
        self.assertNotIsInstance(engine.executor, G.GeneratedImagesExecutor)

"""Lens 11 / rule I-01 (Michael 2026-11-14: "בדיקת ראייה לתמונה — כן, עדשה 11, חוסם").

Production: the butcher (bld_83529c13, 2026-11-14) asked for "נתחי בקר טריים על נייר קצבים על דלפק שיש, אור קר של
בוקר"; the prompt sent to the image model was right ("Fresh cuts of beef on butcher paper atop a marble counter, lit
by cool morning light. ...", from build_capability_requirements.constraints_json); the provider returned eggs, and the
page carried exactly that image (decoded sha256 b2b81b8e... = the stored artifact). Nothing looked at the picture.

Path tested: the worker's own _run_live_build_job with the capability stage's evidence for the butcher's requirement
(its subject and prompt, as stored), the stored image bytes, and the build gateway -- whose vision answer is the one
boundary here (no model runs in CI). The check runs before engine.build; a mismatch fails the build as image_mismatch
and keeps the image's evidence. What this does NOT prove: that a vision model judges correctly (calibration, spec §8)."""
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from omni_prod import generated_images as G
from omni_prod import image_match as M
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.model_gateway import _image_mime
from tests.test_generated_images_in_page import evidence_for, png
from tests.test_m495_capability_executor import MemoryStore

# build_capability_requirements, bld_83529c132a864075945080e9390484cb, cap-media-image-generate (production row)
SUBJECT = 'נתחי בקר טריים על נייר קצבים על דלפק שיש, אור קר של בוקר'
PROMPT = ('Fresh cuts of beef on butcher paper atop a marble counter, lit by cool morning light. Original hero/brand '
          'visual for a web page; realistic, high quality. No text, no letters, no logos, no watermark, no user '
          'interface elements.')
REQUEST = ('אטליז בשר כשר, "האטליז של סבא שמעון", רחוב נתיב המזלות 22, ירושלים. טלפון 0504000162. כפתור להתקשרות. '
           'תמונה ראשית גדולה: נתחי בקר טריים על נייר קצבים על דלפק שיש, אור קר של בוקר.')


def butcher_plan():
    return CapabilityPlan((CapabilityRequirement(
        'cap-media-image-generate', G.IMAGE_CAPABILITY, 'hero/brand visual', True,
        constraints={'prompt': PROMPT, 'subject': SUBJECT, 'aspect_ratio': '16:9'}),), ())


class Vision:
    """The build gateway's vision answer -- the only stand-in here."""
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete_json(self, **kw):
        self.calls.append(kw)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


EGGS = {'matches': False, 'shows': 'ביצים בקערה', 'reason': 'the main subject is eggs, not cuts of beef'}
BEEF = {'matches': True, 'shows': 'נתחי בקר על נייר קצבים', 'reason': 'matches'}


def run(answer):
    from omni_prod import worker_tasks
    from tests.test_m495_worker_capabilities import FakeJobs, passing_engine, platform_for
    plan, store = butcher_plan(), MemoryStore()
    image = png(64, 36, 7)
    ev = evidence_for(store, [('cap-media-image-generate', 'VERIFIED', [image])])
    engine = passing_engine()
    built = []
    build = engine.build
    engine.build = lambda prompt: (built.append(prompt), build(prompt))[1]
    vision = Vision(answer)
    gateway = SimpleNamespace(state=SimpleNamespace(external_spend_usd=Decimal('0'), external_calls=0), events=[],
                              bind_budget=lambda ceiling: {'effective_budget_usd': str(ceiling)},
                              complete_json=vision.complete_json)
    stage = SimpleNamespace(executor=SimpleNamespace(artifact_store=store), prepare=lambda **kw: ev,
                            finalize_native=lambda **kw: {'required_ready': True, 'status': 'VERIFIED',
                                                          'requirements': ev['requirements']})
    jobs = FakeJobs(plan)
    jobs.request['prompt'] = REQUEST
    workspace = MagicMock()
    workspace.commit.return_value = SimpleNamespace(id='v1', artifact_key='a.zip')
    error = None
    try:
        worker_tasks._run_live_build_job(
            'b1', jobs=jobs, platform=platform_for(plan), workspace=workspace,
            components_factory=lambda: (engine, gateway),
            quality_fn=lambda **kw: SimpleNamespace(passed=True, score=100, minimum_score=80, blockers=(),
                                                    to_dict=lambda: {}),
            security_fn=lambda repo: SimpleNamespace(passed=True, findings=(), to_dict=lambda: {}),
            capability_stage=stage)
    except Exception as exc:                          # the worker re-raises after recording the failure
        error = exc
    return SimpleNamespace(jobs=jobs, final=jobs.transitions[-1], built=built, vision=vision, image=image, error=error)


class TheWrongPictureStopsTheBuild(unittest.TestCase):
    def test_eggs_for_beef_fails_before_any_code_is_written(self):
        r = run(EGGS)
        self.assertIsInstance(r.error, M.ImageDoesNotMatch)
        self.assertEqual(r.built, [])                                         # engine.build never ran
        self.assertEqual(r.final['error_code'], 'image_mismatch')
        self.assertIn(SUBJECT, r.final['error_message'])
        self.assertIn('ביצים בקערה', r.final['error_message'])
        caps = r.final['evidence_json']['capabilities']
        self.assertEqual(caps['image_match'][0]['status'], 'MISMATCH')
        self.assertEqual(caps['requirements'][0]['status'], 'VERIFIED')       # the paid image's evidence is kept
        from tests.evidence_notice import notice
        notice('lens 11', f"butcher subject vs eggs: {r.final['error_code']}: {r.final['error_message'][:160]}")

    def test_the_vision_model_sees_the_stored_image_and_the_customers_words(self):
        r = run(EGGS)
        self.assertEqual(len(r.vision.calls), 1)
        call = r.vision.calls[0]
        self.assertEqual(call['images'], (r.image,))
        self.assertIn(SUBJECT, call['user'])
        self.assertEqual(call.get('task'), 'review')

    def test_the_right_picture_goes_on_to_code_generation(self):
        r = run(BEEF)
        self.assertIsNone(r.error)
        self.assertEqual(len(r.built), 1)
        self.assertIn('148ai-asset://image/1', r.built[0])
        self.assertEqual(r.final['evidence_json']['capabilities']['image_match'][0]['status'], 'MATCH')

    def test_a_check_that_cannot_run_does_not_pass(self):
        for answer in (RuntimeError('no vision route'), {'shows': 'x'}, ['not', 'an', 'object']):
            with self.subTest(answer=str(answer)[:30]):
                r = run(answer)
                self.assertIsInstance(r.error, M.ImageDoesNotMatch)
                self.assertEqual(r.built, [])
                self.assertEqual(r.final['error_code'], 'image_mismatch')
                self.assertEqual(r.final['evidence_json']['capabilities']['image_match'][-1]['status'], 'NOT_RUN')

    def test_an_image_without_its_subject_is_not_waved_through(self):
        img = SimpleNamespace(requirement_id='cap-x', sha256='0', data=png(8, 8))
        with self.assertRaisesRegex(M.ImageDoesNotMatch, 'without the subject'):
            M.verify(Vision(BEEF), [img], {'cap-x': '  '})

    def test_bounded(self):
        imgs = [SimpleNamespace(requirement_id='r', sha256=str(i), data=png(8, 8)) for i in range(M.MAX_IMAGES + 1)]
        vision = Vision(BEEF)
        with self.assertRaisesRegex(M.ImageDoesNotMatch, 'bounded'):
            M.verify(vision, imgs, {'r': SUBJECT})
        self.assertEqual(vision.calls, [])


class TheImageIsSentUnderItsRealType(unittest.TestCase):
    """Every image was labelled image/jpeg; the generated hero is a PNG."""
    def test_types(self):
        self.assertEqual(_image_mime(png(4, 4)), 'image/png')
        self.assertEqual(_image_mime(b'\xff\xd8\xff\xe0' + b'0' * 8), 'image/jpeg')
        self.assertEqual(_image_mime(b'RIFF\x00\x00\x00\x00WEBPVP8 '), 'image/webp')
        with self.assertRaises(ValueError):
            _image_mime(b'not an image')

    def test_both_request_dialects_carry_it(self):
        from omni_prod.model_gateway import ModelEndpoint, OpenAICompatibleGateway as ModelGateway
        import json
        for style in ('anthropic', 'openai'):
            sent = []

            class Resp:
                def __enter__(self): return self
                def __exit__(self, *a): return False
                def read(self):
                    return json.dumps({'content': [{'type': 'text', 'text': '{}'}], 'usage': {}} if style == 'anthropic'
                                      else {'choices': [{'message': {'content': '{}'}}], 'usage': {}}).encode()
            gw = ModelGateway(ModelEndpoint('m', 'https://example.invalid/v1', 'model', api_style=style),
                              urlopen=lambda req, timeout=None: sent.append(json.loads(req.data)) or Resp())
            gw.complete(system='s', user='u', images=(png(4, 4),))
            body = json.dumps(sent[0])
            self.assertIn('image/png', body, style)
            self.assertNotIn('image/jpeg', body, style)


if __name__ == '__main__':
    unittest.main()

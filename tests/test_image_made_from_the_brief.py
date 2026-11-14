"""#324 (Michael 2026-11-13): a generated image is made FROM THE BRIEF.

Before, the capability planner kept only the purpose ("hero/brand visual") and FLUX got "Original hero/brand
visual for a modern web product" whatever the customer asked for -- while #336 gives the image an alt from the
brief. Now the clause of the approved request that describes the image is BOTH the generation subject and the alt
(one source), and the image is generated in the proportions of its purpose."""
import io
from types import SimpleNamespace
import json
import unittest

from omni_prod import generated_images as G
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_provider
from tests.test_generated_images_in_page import CAFE, CUP, MemoryStore, evidence_for, png
from tests.test_m495_capability_planner import build_plan

OPEN = {'REPLICATE_API_TOKEN': 'test-only-synthetic', 'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}


def image_requirement(plan):
    return next(r for r in plan.requirements if r.key == G.IMAGE_CAPABILITY)


class Transport:
    def __init__(self):
        self.bodies = []

    def __call__(self, req, timeout=None):
        self.bodies.append(json.loads(req.data.decode()))
        return io.BytesIO(b'{"id":"synthetic-prediction","status":"starting"}')


def submitted(req, env=OPEN):
    t = Transport()
    build_image_provider(env, journal=MemorySubmissionJournal(), urlopen=t).submit(req, idempotency_key='k')
    return t.bodies[0]['input']


class ThePlanCarriesTheSubject(unittest.TestCase):
    def test_the_production_request(self):
        req = image_requirement(build_plan(CAFE))
        self.assertEqual(dict(req.constraints), {'subject': CUP, 'aspect_ratio': '16:9'})

    def test_no_image_requested_no_constraints_anywhere(self):
        plan = build_plan('דף נחיתה לבית קפה קטן עם שעות פתיחה וכפתור הזמנה')
        self.assertFalse(any(r.key == G.IMAGE_CAPABILITY for r in plan.requirements))
        self.assertTrue(all(not r.constraints for r in plan.requirements))

    def test_an_icon_is_square(self):
        req = image_requirement(build_plan('אתר לחנות פרחים, עם לוגו של עלה ירוק, וטופס יצירת קשר'))
        self.assertEqual(req.constraints['aspect_ratio'], '1:1')


class TheProviderGeneratesTheSubject(unittest.TestCase):
    def test_the_prompt_is_the_brief_clause_and_the_ratio_is_sent(self):
        sent = submitted(image_requirement(build_plan(CAFE)))
        self.assertTrue(sent['prompt'].startswith(CUP + '. '))
        self.assertIn('No text, no letters, no logos, no watermark, no user interface elements.', sent['prompt'])
        self.assertEqual(sent['aspect_ratio'], '16:9')

    def test_an_explicit_prompt_still_wins(self):
        req = CapabilityRequirement('x', G.IMAGE_CAPABILITY, 'hero', True, constraints={'prompt': 'exact', 'subject': 's'})
        self.assertEqual(submitted(req)['prompt'], 'exact')

    def test_without_a_subject_the_old_prompt_and_no_ratio(self):
        sent = submitted(CapabilityRequirement('x', G.IMAGE_CAPABILITY, 'hero/brand visual', True))
        self.assertTrue(sent['prompt'].startswith('Original hero/brand visual for a modern web product'))
        self.assertNotIn('aspect_ratio', sent)


class OneSourceForWhatItShowsAndWhatItSays(unittest.TestCase):
    def test_the_alt_is_exactly_the_generation_subject(self):
        plan = build_plan(CAFE)
        req = image_requirement(plan)
        store = MemoryStore()
        ev = evidence_for(store, [(req.id, 'VERIFIED', [png(16, 9)])])
        [img] = G.collect(plan=plan, evidence=ev, store=store, prompt=CAFE)
        self.assertEqual(img.alt, req.constraints['subject'])
        self.assertTrue(submitted(req)['prompt'].startswith(img.alt))

    def test_the_subject_wins_over_re_reading_the_prompt(self):
        plan = CapabilityPlan((CapabilityRequirement('cap-i', G.IMAGE_CAPABILITY, 'hero/brand visual', True,
                                                     constraints={'subject': 'כוס תה על אדן חלון'}),), ())
        store = MemoryStore()
        ev = evidence_for(store, [('cap-i', 'VERIFIED', [png(8, 8)])])
        [img] = G.collect(plan=plan, evidence=ev, store=store, prompt=CAFE)
        self.assertEqual(img.alt, 'כוס תה על אדן חלון')


if __name__ == '__main__':
    unittest.main()


# ---- Michael 2026-11-13 03:43: English prompt translated once and saved; negative list; style from the plan ----
from omni_prod import image_prompt as P   # noqa: E402

DESIGNED = CAFE + (" Design: style warm; requested colour description 'חום, שמנת, ירוק'; font Heebo. "
                   "Use a responsive layout.")
ENGLISH = 'A large cup of coffee on a wooden table by a window, warm style, brown, cream and green colours'


class Translator:
    def __init__(self, answer=ENGLISH):
        self.calls, self.answer = [], answer

    def __call__(self, text):
        self.calls.append(text)
        return self.answer


def prepared(plan, translate, store, only=None):
    return P.prepare_image_prompts(plan, translate=translate, store=store, build_id='b1', project_id='p1', only=only)


class StyleDirectionFromThePlan(unittest.TestCase):
    def test_the_design_line_reaches_the_requirement(self):
        c = image_requirement(build_plan(DESIGNED)).constraints
        self.assertEqual((c['subject'], c['style'], c['colours']), (CUP, 'warm', 'חום, שמנת, ירוק'))

    def test_subject_style_and_colours_are_what_is_translated(self):
        t = Translator()
        prepared(build_plan(DESIGNED), t, MemoryStore())
        self.assertEqual(t.calls, [f'{CUP}. Style: warm. Colours: חום, שמנת, ירוק'])


class EnglishPromptWithTheNegativeList(unittest.TestCase):
    def test_the_provider_sends_the_english_prompt_and_the_negative_list(self):
        plan = prepared(build_plan(DESIGNED), Translator(), MemoryStore())
        req = image_requirement(plan)
        sent = submitted(req)['prompt']
        self.assertTrue(sent.startswith(ENGLISH))
        self.assertTrue(sent.endswith(P.NEGATIVE))
        for word in ('No text', 'no letters', 'no logos', 'no watermark', 'no user interface'):
            self.assertIn(word, sent)
        self.assertFalse(P._NON_LATIN.search(sent))                       # English only

    def test_the_alt_stays_hebrew_from_the_brief(self):
        plan = prepared(build_plan(DESIGNED), Translator(), MemoryStore())
        req = image_requirement(plan)
        store = MemoryStore()
        ev = evidence_for(store, [(req.id, 'VERIFIED', [png(16, 9)])])
        [img] = G.collect(plan=plan, evidence=ev, store=store, prompt=DESIGNED)
        self.assertEqual(img.alt, CUP)


class TranslatedOnceAndSaved(unittest.TestCase):
    def test_saved_next_to_the_image_and_never_translated_again(self):
        store, t = MemoryStore(), Translator()
        first = image_requirement(prepared(build_plan(DESIGNED), t, store)).constraints['prompt']
        key = 'projects/p1/builds/b1/capabilities/cap-media-image-generate/prompt-en.txt'
        self.assertEqual(store.objects[key].decode(), ENGLISH)
        again = Translator('something else entirely')                     # a retry / a recovered worker
        second = image_requirement(prepared(build_plan(DESIGNED), again, store)).constraints['prompt']
        self.assertEqual(again.calls, [])
        self.assertEqual(second, first)

    def test_an_english_request_is_not_translated(self):
        t = Translator()
        plan = prepared(build_plan('A landing page with a hero image of a red bicycle by the sea, opening hours.'),
                        t, MemoryStore())
        self.assertEqual(t.calls, [])
        self.assertTrue(image_requirement(plan).constraints['prompt'].startswith('hero image of a red bicycle'))


class FailClosed(unittest.TestCase):
    def test_a_bad_translation_stops_the_image(self):
        for answer in ('', 'כוס קפה', 'x' * (P.MAX_CHARS + 1)):
            with self.subTest(answer=answer[:10]), self.assertRaises(P.ImagePromptError):
                prepared(build_plan(DESIGNED), Translator(answer), MemoryStore())

    def test_a_failing_model_call_is_an_image_prompt_error(self):
        boom = SimpleNamespace(complete=lambda **kw: (_ for _ in ()).throw(RuntimeError('provider down')))
        with self.assertRaises(P.ImagePromptError):
            P.gateway_translator(boom)('כוס קפה')

    def test_an_image_without_a_provider_is_not_translated(self):
        t = Translator()
        plan = prepared(build_plan(DESIGNED), t, MemoryStore(), only=set())
        self.assertEqual(t.calls, [])
        self.assertNotIn('prompt', image_requirement(plan).constraints)


class TheBuildGatewayTranslates(unittest.TestCase):
    def test_one_call_through_the_gateway_with_the_system_prompt(self):
        calls = []
        gw = SimpleNamespace(complete=lambda **kw: calls.append(kw) or ENGLISH)
        self.assertEqual(P.gateway_translator(gw)('כוס קפה'), ENGLISH)
        self.assertEqual(len(calls), 1)
        self.assertEqual((calls[0]['system'], calls[0]['user'], calls[0]['task']), (P.SYSTEM, 'כוס קפה', 'general'))


class TheWorkerTranslatesThroughTheBoundGateway(unittest.TestCase):
    def test_translated_once_before_the_image_stage_and_the_stage_gets_the_english_prompt(self):
        from decimal import Decimal
        from unittest.mock import MagicMock
        from omni_prod import worker_tasks
        from tests.test_m495_worker_capabilities import FakeJobs, passing_engine, platform_for
        plan = build_plan(DESIGNED)
        req = image_requirement(plan)
        store, order, calls, staged = MemoryStore(), [], [], {}
        gateway = SimpleNamespace(
            state=SimpleNamespace(external_spend_usd=Decimal('0'), external_calls=0), events=[],
            bind_budget=lambda ceiling: order.append('budget') or {'effective_budget_usd': str(ceiling)},
            complete=lambda **kw: order.append('translate') or calls.append(kw) or ENGLISH)
        ev = evidence_for(store, [(req.id, 'VERIFIED', [png(16, 9)])])

        def prepare(**kw):
            order.append('images')
            staged['plan'] = kw['plan']
            return ev
        stage = SimpleNamespace(executor=SimpleNamespace(artifact_store=store), prepare=prepare,
                                assignments_resolver=lambda p: {req.id: object()},
                                finalize_native=lambda **kw: {'required_ready': True, 'status': 'VERIFIED',
                                                              'requirements': ev['requirements']})
        jobs = FakeJobs(plan)
        jobs.request['prompt'] = DESIGNED
        workspace = MagicMock()
        workspace.commit.return_value = SimpleNamespace(id='v1', artifact_key='a.zip')
        worker_tasks._run_live_build_job(
            'b1', jobs=jobs, platform=platform_for(plan), workspace=workspace,
            components_factory=lambda: (passing_engine(), gateway),
            quality_fn=lambda **kw: SimpleNamespace(passed=True, score=100, minimum_score=80, blockers=(),
                                                    to_dict=lambda: {}),
            security_fn=lambda repo: SimpleNamespace(passed=True, findings=(), to_dict=lambda: {}),
            capability_stage=stage)
        self.assertEqual(order[:3], ['budget', 'translate', 'images'])      # metered, then the image
        self.assertEqual(len(calls), 1)
        sent = image_requirement(staged['plan']).constraints['prompt']
        self.assertTrue(sent.startswith(ENGLISH) and sent.endswith(P.NEGATIVE))

    def test_an_image_without_a_provider_blocks_without_a_translation_call(self):
        from decimal import Decimal
        from unittest.mock import MagicMock
        from omni_prod import worker_tasks
        from omni_prod.capability_worker import CapabilityStageBlocked
        from tests.test_m495_worker_capabilities import FakeJobs, passing_engine, platform_for
        plan = build_plan(DESIGNED)
        gateway = SimpleNamespace(
            state=SimpleNamespace(external_spend_usd=Decimal('0'), external_calls=0), events=[],
            bind_budget=lambda ceiling: {'effective_budget_usd': str(ceiling)},
            complete=lambda **kw: self.fail('no translation for an image that will not be generated'))

        def prepare(**kw):
            raise CapabilityStageBlocked('required capability NOT_CONFIGURED: media.image.generate',
                                         evidence={'required_ready': False, 'requirements': []})
        stage = SimpleNamespace(executor=SimpleNamespace(artifact_store=MemoryStore()), prepare=prepare,
                                assignments_resolver=lambda p: {})
        jobs = FakeJobs(plan)
        jobs.request['prompt'] = DESIGNED
        with self.assertRaisesRegex(Exception, 'NOT_CONFIGURED'):
            worker_tasks._run_live_build_job(
                'b1', jobs=jobs, platform=platform_for(plan), workspace=MagicMock(),
                components_factory=lambda: (passing_engine(), gateway),
                quality_fn=lambda **kw: None, security_fn=lambda repo: None, capability_stage=stage)

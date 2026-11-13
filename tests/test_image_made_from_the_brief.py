"""#324 (Michael 2026-11-13): a generated image is made FROM THE BRIEF.

Before, the capability planner kept only the purpose ("hero/brand visual") and FLUX got "Original hero/brand
visual for a modern web product" whatever the customer asked for -- while #336 gives the image an alt from the
brief. Now the clause of the approved request that describes the image is BOTH the generation subject and the alt
(one source), and the image is generated in the proportions of its purpose."""
import io
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
        self.assertIn('no text', sent['prompt'])
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

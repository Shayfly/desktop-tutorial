"""The default hero is optional, so it never fails a build (the owner, DECISIONS 5, 2026-11-17; fixed 2026-11-23).

Production, 2026-11-23 -- three builds in a row died, and none of them had asked for a picture at all:

    bld_7b541f93 (ShayFly)  15:10  image_mismatch: generated image(s) without the subject they were made from
    bld_4bb6207f (GOA)      17:14  the same
    bld_6c8c2d3a (GOA)      17:15  the same

DECISIONS 5 says a content site gets one main image by DEFAULT -- `media_pipeline` adds it with required=False and
the comment "Optional: a failed generation never fails the build". That picture carries no subject of the customer's
own, and `image_match.verify` blocks on any image it cannot judge. So the optional picture killed the build.

Here: a picture the customer ASKED for still blocks when it is wrong or cannot be checked (the butcher's rule,
lens 11 / I-01, unchanged), and the default one is dropped instead -- never shown unverified, never fatal.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from omni_prod import generated_images as G
from omni_prod import image_match as M
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from tests.test_generated_images_in_page import evidence_for, png
from tests.test_m495_capability_executor import MemoryStore

RID = 'cap-media-image-generate'


def plan_for(*, required: bool, subject: str | None):
    constraints = {'aspect_ratio': '16:9'}
    if subject:
        constraints.update(subject=subject, prompt='a prompt')
    return CapabilityPlan((CapabilityRequirement(RID, G.IMAGE_CAPABILITY, 'hero/brand visual', required,
                                                 constraints=constraints),), ())


class Vision:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete_json(self, **kw):
        self.calls.append(kw)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def install(plan, vision):
    store = MemoryStore()
    ev = evidence_for(store, [(RID, 'VERIFIED', [png(64, 36, 7)])])
    core = SimpleNamespace(executor=None, repository_transform=None)
    engine = SimpleNamespace(core=core)
    prompt = G.install(engine, prompt='אתר לעסק', plan=plan, evidence=ev, store=store, vision=vision)
    return prompt, core


class TheDefaultHeroIsNeverFatal(unittest.TestCase):
    def test_the_three_production_builds_would_have_been_built(self):
        """No subject, optional: the build goes on, and the picture is not in it."""
        vision = Vision({'matches': True, 'shows': 'x', 'reason': 'x'})
        prompt, core = install(plan_for(required=False, subject=None), vision)
        self.assertNotIn('Generated images', prompt)              # nothing unverified reaches the page
        self.assertEqual(vision.calls, [])                        # and nothing was paid to judge it
        self.assertEqual([v['status'] for v in core.image_match], ['DROPPED'])
        self.assertIn('did not ask', core.image_match[0]['reason'])

    def test_a_default_hero_that_matches_is_kept(self):
        vision = Vision({'matches': True, 'shows': 'חנות', 'reason': 'matches'})
        prompt, core = install(plan_for(required=False, subject='חנות מוצרי עישון'), vision)
        self.assertIn('Generated images', prompt)
        self.assertEqual([v['status'] for v in core.image_match], ['MATCH'])

    def test_a_default_hero_that_shows_the_wrong_thing_is_dropped_not_fatal(self):
        vision = Vision({'matches': False, 'shows': 'ביצים', 'reason': 'eggs'})
        prompt, core = install(plan_for(required=False, subject='חנות מוצרי עישון'), vision)
        self.assertNotIn('Generated images', prompt)
        self.assertEqual([v['status'] for v in core.image_match], ['DROPPED'])

    def test_a_vision_failure_on_the_default_hero_is_dropped_not_fatal(self):
        vision = Vision(RuntimeError('no vision route'))
        prompt, core = install(plan_for(required=False, subject='חנות מוצרי עישון'), vision)
        self.assertNotIn('Generated images', prompt)
        self.assertEqual([v['status'] for v in core.image_match], ['DROPPED'])


class APictureTheCustomerAskedForStillBlocks(unittest.TestCase):
    """The butcher's rule (bld_83529c13) is untouched: what the customer asked to see is judged, and a wrong or
    unjudgeable picture stops the build before any code is generated."""

    def test_a_wrong_picture_still_fails_the_build(self):
        vision = Vision({'matches': False, 'shows': 'ביצים', 'reason': 'eggs, not beef'})
        with self.assertRaises(M.ImageDoesNotMatch):
            install(plan_for(required=True, subject='נתחי בקר טריים'), vision)

    def test_a_check_that_cannot_run_still_fails_the_build(self):
        vision = Vision(RuntimeError('no vision route'))
        with self.assertRaises(M.ImageDoesNotMatch):
            install(plan_for(required=True, subject='נתחי בקר טריים'), vision)

    def test_a_requested_picture_with_no_subject_still_fails_the_build(self):
        vision = Vision({'matches': True, 'shows': 'x', 'reason': 'x'})
        with self.assertRaises(M.ImageDoesNotMatch):
            install(plan_for(required=True, subject=None), vision)


if __name__ == '__main__':
    unittest.main()

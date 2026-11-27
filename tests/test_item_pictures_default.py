"""A picture of EACH listed item is the default, drawn by a stronger model (the owner, 2026-11-27, inbox/005).

Decision 2 ("ב"): every service or product the customer lists gets a picture, unless the customer says none ("בלי
תמונות", "without pictures", "بدون صور"). It used to need the customer's words ("תמונה של כל נושא").
Decision 3 ("ג"): FLUX 1.1 pro on Replicate ($0.04 per image, commercial use) replaces FLUX schnell ($0.003), without a
side-by-side test. One image per request, no num_outputs input.

The real path: ProductArchitect.compile on the owner's law-firm brief with a services list, the real image provider
(build_image_provider, its journal, quote, submit and collect) and site_content.decide. Doubled: the HTTP transport only,
which records every request it is sent (the provider network), plus the SafeFetcher's resolver.
"""
from __future__ import annotations

import io
import json
import unittest
from decimal import Decimal

from omni_prod import a4
from omni_prod import capability_planner as CP
from omni_prod import site_content as SC
from omni_prod.capabilities import CapabilityRequirement
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_provider
from tests.test_m5_media_provider_adapters import _fetcher, _png
from tests.test_site_content_route import PROMPT, on, with_request

SERVICES = ('פיטורים שלא כדין', 'הטרדה במקום העבודה', 'זכויות סוציאליות')
CONTENT = 'Initial content: כתובת: דרך מנחם בגין 132, תל אביב; טלפון 03-5551234; office@cohen-law.co.il; א׳–ה׳ 09:00–18:00; ייעוץ ראשון 250 ₪'
ENV = {'REPLICATE_API_TOKEN': 'test-only-token', 'OMNI_ZERO_COST_MODE': '0', 'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'}
BUILD_CAP = Decimal('2.00')      # the build's cost cap (CLAUDE.md; pricing.FOUNDER_BUILD_LLM_USD default)
OWNER = {'user_id': 'usr_owner_test'}


def listing(items):
    base = PROMPT.replace(CONTENT, CONTENT + '; שירותים: ' + ', '.join(items))
    assert base != PROMPT
    return base


LISTED = listing(SERVICES)


def item_requirements(prompt):
    contract = ProductArchitect().compile(prompt, project_id='prj_items_default', contract_version=1)
    return [r for r in contract.capability_plan.requirements if r.key == CP.IMAGE_KEY and r.purpose == a4.ITEM_PURPOSE]


class _Response(io.BytesIO):
    status = 200
    headers = {'Content-Type': 'image/png'}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class Transport:
    """The Replicate HTTP boundary, recording every request: official-model predictions, one output URL each."""

    def __init__(self):
        self.requests = []

    def __call__(self, req, timeout):
        self.requests.append(req)
        url = req.full_url
        if req.get_method() == 'POST' and url.endswith('/predictions'):
            n = len(self.posts())
            return _Response(json.dumps({
                'id': f'pred_{n}', 'status': 'succeeded', 'model': 'black-forest-labs/flux-1.1-pro',
                'output': f'https://replicate.delivery/pbxt/{n}/out.png', 'metrics': {'predict_time': 3.0}}).encode())
        if url.startswith('https://replicate.delivery/'):
            return _Response(_png())
        raise AssertionError(f'unexpected request {req.get_method()} {url}')

    def posts(self):
        return [r for r in self.requests if r.get_method() == 'POST']


def provider(transport, journal=None, env=None):
    return build_image_provider(env or ENV, journal=journal or MemorySubmissionJournal(), urlopen=transport,
                                fetcher=_fetcher(transport))


def picture(rid, quantity=1):
    return CapabilityRequirement(id=rid, key=CP.IMAGE_KEY, purpose='hero', required=True, quantity=quantity,
                                 constraints={'prompt': 'x'})


class ThePictureIsTheDefault(unittest.TestCase):
    def test_each_listed_item_gets_a_picture_with_no_word_from_the_customer(self):
        reqs = item_requirements(LISTED)
        self.assertEqual([r.constraints['subject'] for r in reqs], list(SERVICES))
        self.assertTrue(all(r.quantity == 1 and r.required for r in reqs))

    def test_a_customer_who_says_no_pictures_gets_none_in_three_languages(self):
        for words in ('בלי תמונות באתר.', 'ללא תמונות', 'I want it without pictures.', 'no images please',
                      'بدون صور من فضلكم', 'من غير صور'):
            with self.subTest(words):
                said = with_request(words, LISTED)
                self.assertFalse(CP.item_pictures_wanted(said))
                self.assertEqual(item_requirements(said), [])

    def test_no_stock_photos_is_not_no_pictures(self):
        # the owner's law-firm brief says "בלי תמונות מלאי של פטישים": no STOCK photos, the pictures are still wanted
        self.assertIn('בלי תמונות מלאי של פטישים', LISTED)
        self.assertTrue(CP.item_pictures_wanted(LISTED))

    def test_a_brief_that_lists_no_item_plans_nothing_and_asks_nothing(self):
        self.assertFalse(CP.item_pictures_wanted(PROMPT))
        contract = ProductArchitect().compile(PROMPT, project_id='prj_items_default', contract_version=1)
        self.assertEqual([r for r in contract.capability_plan.requirements if r.purpose == a4.ITEM_PURPOSE], [])
        self.assertNotIn(CP.IMAGE_ITEMS_UNREAD, contract.capability_plan.notes)
        self.assertEqual([q.id for q in contract.unresolved_questions if q.id == 'image_items'], [])

    def test_only_a_content_site_has_the_default(self):
        other = LISTED.replace('Product kind: CONTENT-ONLY website', 'Product kind: web app')
        self.assertNotEqual(other, LISTED)
        self.assertFalse(CP.item_pictures_wanted(other))

    def test_the_customers_own_words_still_ask_for_it(self):
        self.assertTrue(CP.item_pictures_wanted(with_request('ליד כל שירות תשימו תמונה.', PROMPT)))


class TheRoute(unittest.TestCase):
    def test_a_defaulted_item_picture_stays_on_the_library_route_which_places_it(self):
        # visual plan S3: the services cards carry the pictures and the gallery holds the rest, so a picture per item
        # never sends a build to the legacy path (it was 'item_pictures_default' while the library had no card for one)
        with on():
            route = SC.decide(LISTED, OWNER, year='2026')
            self.assertEqual((route.route, route.reason), ('section_library', 'all preconditions hold'))
            self.assertTrue(CP.item_pictures_wanted(LISTED))       # and the picture is still planned, paid for and placed
            self.assertFalse(CP.item_pictures_wanted(with_request('בלי תמונות', LISTED)))
            self.assertEqual(SC.decide(with_request('בלי תמונות', LISTED), OWNER, year='2026').route, 'section_library')
            self.assertEqual(SC.decide(PROMPT, OWNER, year='2026').route, 'section_library')


class TheStrongerModel(unittest.TestCase):
    def test_the_default_is_flux_1_1_pro_priced_and_licensed_from_its_profile(self):
        c = provider(Transport()).config
        self.assertEqual((c.model, c.maximum_usd_per_image, c.estimated_usd_per_image, c.billing_unit),
                         ('black-forest-labs/flux-1.1-pro', Decimal('0.04'), Decimal('0.04'), 'output'))
        self.assertTrue(c.commercial_use)
        self.assertIn('flux-1.1-pro', c.price_source)
        self.assertIn('FLUX 1.1 pro', c.license)

    def test_every_item_picture_is_one_request_to_the_model_with_its_proportions_and_a_computed_cost(self):
        reqs = item_requirements(LISTED)
        transport = Transport()
        p = provider(transport)
        total = Decimal('0')
        for r in reqs:
            result = p.collect(p.submit(r, idempotency_key='k-' + r.id))
            (payload,) = result.payloads
            self.assertTrue(payload.metadata['commercial_use'])
            self.assertEqual(result.usage['cost_basis'], 'computed_from_usage')
            self.assertEqual(result.usage['unit_price_usd'], '0.04')
            self.assertIsNone(result.actual_cost_usd)                      # computed, never written as actual
            total += Decimal(result.usage['computed_cost_usd'])
        posts = transport.posts()
        self.assertEqual(len(posts), len(SERVICES))
        for req, r in zip(posts, reqs):
            self.assertEqual(req.full_url, 'https://api.replicate.com/v1/models/black-forest-labs/flux-1.1-pro/predictions')
            body = json.loads(req.data)
            self.assertNotIn('num_outputs', body['input'])                  # the model takes none
            self.assertEqual(body['input']['aspect_ratio'], r.constraints['aspect_ratio'])
            self.assertEqual(body['input']['output_format'], 'png')
        self.assertEqual(total, Decimal('0.04') * len(SERVICES))

    def test_ten_item_pictures_and_the_main_one_stay_far_under_the_build_cap(self):
        reqs = item_requirements(listing(tuple(f'שירות {n}' for n in range(1, 11))))
        self.assertEqual(len(reqs), 10)
        p = provider(Transport())
        worst = sum((p.quote(r).maximum_cost_usd for r in [picture('hero'), *reqs]), Decimal('0'))
        self.assertEqual(worst, Decimal('0.44'))
        self.assertLess(worst, BUILD_CAP / 4)                                # a quarter of the cap, worst case

    def test_a_model_that_makes_one_image_refuses_a_larger_quantity_before_anything_is_sent(self):
        transport, journal = Transport(), MemorySubmissionJournal()
        p = provider(transport, journal)
        with self.assertRaisesRegex(ValueError, 'one image per request'):
            p.submit(picture('two', quantity=2), idempotency_key='k-two')
        self.assertEqual(transport.requests, [])
        self.assertFalse(journal.begin('k-two', provider=p.name).preexisting)   # no INTENT was left behind

    def test_schnell_keeps_its_own_request_shape_by_configuration(self):
        transport = Transport()
        p = provider(transport, env={**ENV, 'OMNI_IMAGE_PROVIDER_MODEL': 'black-forest-labs/flux-schnell'})
        p.submit(picture('r'), idempotency_key='k')
        (req,) = transport.posts()
        self.assertTrue(req.full_url.endswith('/models/black-forest-labs/flux-schnell/predictions'))
        self.assertEqual(json.loads(req.data)['input']['num_outputs'], 1)

    def test_the_owners_paid_connection_test_stays_on_the_cheap_model_it_confirms(self):
        from omni_prod.providers.replicate_image_test import ReplicateImageTest
        transport = Transport()
        service = ReplicateImageTest(env={'REPLICATE_API_TOKEN': 'test-only', 'OMNI_ZERO_COST_MODE': '0',
                                          'OMNI_ALLOW_EXTERNAL_FALLBACK': '1'},
                                     journal=MemorySubmissionJournal(), store=None, urlopen=transport)
        self.assertEqual(service.start('acct', confirmed=True)['maximum_usd'], '0.003')
        (req,) = transport.posts()
        self.assertTrue(req.full_url.endswith('/models/black-forest-labs/flux-schnell/predictions'))


if __name__ == '__main__':
    unittest.main()

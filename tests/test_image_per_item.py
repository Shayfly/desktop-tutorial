"""A picture of EACH item the customer named, each made from its own item (the owner, 2026-11-26: "אין דבר כזה תקרת
תמונות לבטל מיד").

Production, 2026-11-25 (tests/fixtures/site_content_bld_3938e570.json: route-honesty's read-only row, redacted, sha256
checked below). The owner's GOA build asked "ליד כל נושא ממה שאנחנו מוכרים תשים תמונה של הנושא" for nine product
categories. A4 counted ONE picture (it counts only a number written next to the picture word), and a number of
pictures was one requirement with one subject anyway: N takes of the same picture, cut to 3.

Now the customer's words are read by one_page.beyond (picture_per_item, the reader the content route uses -- law 9),
the items are the list the approved brief's "Initial content:" line labels ("קטגוריות: ..."), and each item is one
requirement with that item as its subject. Each is generated, checked against its own item and placed next to it.

The real path: ProductArchitect.compile, image_prompt.prepare_image_prompts, the image capability stage, the real
generated_images.install with the lens-11 check, and a4.plan. Doubled: the provider network only -- the image HTTP
API, the translation model and the vision model.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from omni_prod import a4
from omni_prod import generated_images as G
from omni_prod import image_match as M
from omni_prod.build_contract import BuildContractStatus
from omni_prod.capability_planner import IMAGE_ITEMS_UNREAD
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.image_prompt import final_prompt, gateway_translator, prepare_image_prompts
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_capability_stage
from tests.test_image_subject import Store
from tests.test_m5_media_provider_adapters import ENV, FakePredictionAPI, _fetcher

FX = json.loads((Path(__file__).parent / 'fixtures' / 'site_content_bld_3938e570.json').read_text(encoding='utf-8'))
PROMPT = FX['prompt']
ITEMS = ('נרגילות', 'סיגריות', 'טבק לנרגילה', 'מוצרים נלווים לנרגילות', 'באנגים', 'ניירות גילגול', 'גרינדרים',
         'קופסאות אחסון', 'מצתים')
BUSINESS_LINE = 'הצגת קטגוריות ומוצרים בעסק למוצרי עישון, עם אפשרות להרחיב כל קטגוריה בעמוד משלה'
ASKED = ('ליד כל נושא ממה שאנחנו מוכרים תשים תמונה של הנושא',
         'כאילו שיהיה תפריט הנושאים למכירה עם תמונה של כל נושא .')


def compile_contract(prompt=PROMPT):
    return ProductArchitect().compile(prompt, project_id='prj_per_item', contract_version=1)


def images(contract):
    return [r for r in contract.capability_plan.requirements if r.key == G.IMAGE_CAPABILITY]


def english(text):
    """The translation double: one plain English line per source text (no Hebrew, as image_prompt requires)."""
    return 'A picture ' + hashlib.md5(text.encode('utf-8')).hexdigest()[:10]


class Translator:
    def __init__(self):
        self.calls = []

    def complete(self, **kw):
        self.calls.append(kw['user'])
        return english(kw['user'])


class Vision:
    """The lens-11 vision model: MATCH, except for the subjects in `wrong`."""

    def __init__(self, wrong=()):
        self.wrong, self.calls = set(wrong), []

    def complete_json(self, **kw):
        subject = json.loads(kw['user'])['customer_asked_to_see']
        self.calls.append(subject)
        if subject in self.wrong:
            return {'matches': False, 'shows': 'הרים', 'reason': 'mountains'}
        return {'matches': True, 'shows': subject, 'reason': 'matches'}


def build_images(vision):
    """The worker's order (prepare_image_prompts -> capability_stage.prepare -> install) on the compiled contract."""
    contract = compile_contract()
    api, store, translator = FakePredictionAPI(), Store(), Translator()
    stage = build_image_capability_stage(env=ENV, repository=MemoryCapabilityRepository(), artifact_store=store,
                                         journal=MemorySubmissionJournal(), worker_id='w1', urlopen=api,
                                         fetcher=_fetcher(api))
    stage.executor.provider_registry.get('image-predictions').sleep = lambda s: None
    plan = contract.capability_plan
    plan = prepare_image_prompts(plan, translate=gateway_translator(translator), store=store, build_id='bld_items',
                                 project_id='prj_items', only=set(stage.assignments_resolver(plan) or {}))
    evidence = stage.prepare(build_id='bld_items', project_id='prj_items', plan=plan,
                             authorized_maximum_usd=Decimal('1.00'), now=1000.0)
    core = SimpleNamespace(executor=None, repository_transform=None)
    run = SimpleNamespace(plan=plan, api=api, translator=translator, core=core, error=None,
                          sent=[c['body']['input'].get('prompt') for c in api.created])
    try:
        run.prompt = G.install(SimpleNamespace(core=core), prompt=contract.prompt, plan=plan, evidence=evidence,
                               store=store, vision=vision)
    except M.ImageDoesNotMatch as exc:
        run.error = exc
    return run


class TheFixtureIsTheProductionRow(unittest.TestCase):
    def test_the_redacted_prompt_hashes_to_its_recorded_digest(self):
        self.assertEqual(hashlib.sha256(PROMPT.encode('utf-8')).hexdigest(), FX['prompt_sha256'])
        for words in ASKED:
            self.assertIn(words, PROMPT)


class EachNamedItemGetsItsOwnPicture(unittest.TestCase):
    def test_nine_named_items_are_nine_pictures_each_its_own_subject(self):
        contract = compile_contract()
        items = [r for r in images(contract) if r.purpose == a4.ITEM_PURPOSE]
        self.assertEqual(tuple(r.constraints['subject'] for r in items), ITEMS)
        self.assertEqual([r.id for r in items], [f'cap-media-image-generate-item-{n}' for n in range(1, 10)])
        self.assertTrue(all(r.required and r.quantity == 1 for r in items))
        # the field read: the approved brief's "Initial content:" line, the list after its "קטגוריות:" label
        content = next(line for line in PROMPT.split('\n') if line.startswith('Initial content: '))
        self.assertIn('קטגוריות: ' + ', '.join(ITEMS[:-2]) + ', ' + ITEMS[-2] + ' ו' + ITEMS[-1], content)
        # the default hero of the content site stays, made from the brief's business line
        (main,) = [r for r in images(contract) if r.purpose != a4.ITEM_PURPOSE]
        self.assertEqual((main.required, main.constraints['subject']), (False, BUSINESS_LINE))
        self.assertEqual(contract.status, BuildContractStatus.READY)

    def test_each_picture_is_made_and_judged_from_its_own_item_and_placed_next_to_it(self):
        vision = Vision()
        run = build_images(vision)
        self.assertIsNone(run.error)
        subjects = (BUSINESS_LINE,) + ITEMS
        self.assertEqual(sorted(run.translator.calls), sorted(subjects))          # one translation per picture
        self.assertEqual(sorted(run.sent), sorted(final_prompt(english(s), p) for s, p in
                                                  [(BUSINESS_LINE, 'hero/brand visual')]
                                                  + [(i, a4.ITEM_PURPOSE) for i in ITEMS]))
        self.assertEqual(sorted(vision.calls), sorted(subjects))                  # each judged against its own item
        self.assertEqual(sorted(img.alt for img in run.core.generated_images), sorted(subjects))
        slots = a4.plan([], run.core.generated_images)
        self.assertEqual(sorted(s['place'] for s in slots), ['hero'] + ['products'] * 9)
        rules = a4.rules(slots)
        for item in ITEMS:
            self.assertIn(f'It shows "{item}": put it next to that item.', rules)

    def test_a_wrong_picture_of_one_item_stops_the_build(self):
        run = build_images(Vision(wrong={'מצתים'}))
        self.assertIsInstance(run.error, M.ImageDoesNotMatch)
        self.assertIn('asked "מצתים"', str(run.error))


class WhenNoItemsAreNamedOrAsked(unittest.TestCase):
    def test_a_picture_per_item_with_no_list_in_the_brief_is_the_contracts_question(self):
        content = next(line for line in PROMPT.split('\n') if line.startswith('Initial content: '))
        unlisted = content.split('; קטגוריות:')[0]
        contract = compile_contract(PROMPT.replace(content, unlisted))
        self.assertEqual([r for r in images(contract) if r.purpose == a4.ITEM_PURPOSE], [])
        self.assertIn(IMAGE_ITEMS_UNREAD, contract.capability_plan.notes)
        self.assertEqual(contract.status, BuildContractStatus.NEEDS_CLARIFICATION)
        (question,) = [q for q in contract.unresolved_questions if q.id == 'image_items']
        self.assertEqual(question.question, 'לאילו פריטים לשים תמונה? כתבו את רשימת הפריטים, מופרדת בפסיקים.')

    def test_a_list_alone_without_the_customers_ask_makes_no_item_pictures(self):
        prompt = PROMPT
        for words in ASKED:
            prompt = prompt.replace(words + '\n', '')
        contract = compile_contract(prompt)
        self.assertEqual([r for r in images(contract) if r.purpose == a4.ITEM_PURPOSE], [])
        self.assertNotIn(IMAGE_ITEMS_UNREAD, contract.capability_plan.notes)


class TheCustomersOwnPhotos(unittest.TestCase):
    """S3 (release review of 550320c): a picture was generated for each item although the customer uploaded their own
    photos -- the per-item path had no upload check, while a4.pictures and media_pipeline.default_hero have one
    (founder decision #28). The clothes shop of the review: three uploads, "מוצרים: חולצות, מכנסיים ושמלות"."""
    BRIEF = ('--- Approved project brief (binding; fingerprint 0123456789abcdef) ---\n'
             'Sign-in: NONE. Do not add login, sessions, users or roles.\n'
             'Product kind: CONTENT-ONLY website. Visitors only read the page and nothing from visitors is saved; no '
             'accounts, no record-saving forms and no record APIs. Show the content, prices and links exactly as given.\n'
             'Product decisions v1: {"version":1,"persistence":"none","source":"customer"}\n'
             'Main action: הצגת החנות והמוצרים\n'
             'Initial content: בגדי נועה; מוצרים: חולצות, מכנסיים ושמלות\n'
             'Language: Hebrew, right-to-left; dates shown as DD/MM/YYYY.')
    REQUEST = 'אתר לחנות הבגדים שלי "בגדי נועה" עם תמונות של המוצרים.'
    UPLOADS = (' צירפתי את התמונות שלי: src 148ai-asset://upload/1 , 148ai-asset://upload/2 , '
               '148ai-asset://upload/3')

    def test_uploaded_photos_mean_no_generated_item_pictures_and_the_contract_says_so(self):
        from omni_prod.capability_planner import IMAGE_ITEMS_UPLOADED
        contract = compile_contract(self.REQUEST + self.UPLOADS + '\n' + self.BRIEF)
        self.assertEqual(images(contract), [])
        self.assertIn(IMAGE_ITEMS_UPLOADED, contract.capability_plan.notes)
        self.assertEqual([q.id for q in contract.unresolved_questions if q.id.startswith('image')], [])

    def test_without_uploads_each_item_gets_its_picture(self):
        contract = compile_contract(self.REQUEST + '\n' + self.BRIEF)
        self.assertEqual([r.constraints['subject'] for r in images(contract) if r.purpose == a4.ITEM_PURPOSE],
                         ['חולצות', 'מכנסיים', 'שמלות'])


if __name__ == '__main__':
    unittest.main()

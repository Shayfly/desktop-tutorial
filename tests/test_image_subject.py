"""Every image requirement says what it shows (the owner's decision, 2026-11-26).

Production, 2026-11-23 (tests/fixtures/image_subject_owner_builds_2026_11_23.json: read-only rows, redacted in the
database, md5 checked below). Three owner builds failed about 25 seconds in, before any code, with image_mismatch
"generated image(s) without the subject they were made from":

    bld_7b541f93 (ShayFly)  required=true   the approved semantic decision "required" for media.image.generate
    bld_4bb6207f (GOA)      required=false  the default hero of a content site (DECISIONS 5)
    bld_6c8c2d3a (GOA)      required=false  the same prompt and contract

The planner recorded a subject only when the customer's own words held one of the fixed phrases of
generated_images.describe. Every other trigger made an image requirement with no subject: the provider drew a picture
from a generic sentence ("Original hero/brand visual for a modern web product. ...") and the image check had nothing to
judge it by. The 2026-11-23 fix only let the optional picture be dropped; ShayFly's required one still failed.

Now the subject comes from the trigger that made the requirement, in this order: the customer's own clause; else the
customer's words quoted by the approved semantic decision; else, for the default hero, the approved brief's business
line ("Main action:"). With none of them an optional image is not planned and a required one is the contract's question
-- never a paid generic picture -- and CapabilityRegistry.validate_plan refuses any image requirement without a subject
when the contract is compiled.

The real path: ProductArchitect.compile, image_prompt.prepare_image_prompts, the image capability stage
(build_image_capability_stage: router, executor, adapter, artifact verification) and generated_images.install.
Doubled: the provider network only -- the image HTTP API (FakePredictionAPI), the translation model and the vision model.
"""
from __future__ import annotations

import hashlib
import json
import unittest
from unittest import mock
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from omni_prod import generated_images as G
from omni_prod import image_match as M
from omni_prod.build_contract import BuildContractStatus
from omni_prod.capabilities import CapabilityPlan, CapabilityRequirement
from omni_prod.capability_planner import IMAGE_NOT_PLANNED, IMAGE_SUBJECT_UNRESOLVED, _picture_per_item
from omni_prod.capability_registry import CapabilityRegistry
from omni_prod.capability_repository import MemoryCapabilityRepository
from omni_prod.image_prompt import final_prompt, gateway_translator, prepare_image_prompts
from omni_prod.product_architect import ProductArchitect
from omni_prod.providers.image_provider import MemorySubmissionJournal, build_image_capability_stage
from omni_prod.rehearsal import approved_prompt
from tests.test_m5_media_provider_adapters import ENV, FakePredictionAPI, _fetcher

FX = json.loads((Path(__file__).parent / 'fixtures' / 'image_subject_owner_builds_2026_11_23.json')
                .read_text(encoding='utf-8'))
SHAYFLY, GOA = FX['rows']['shayfly'], FX['rows']['goa']
MARKER = '\n--- Approved project brief'
QUOTED = 'תעשה תמונות של כולם לפי המקום'           # the customer's words in ShayFly's approved semantic decision
BUSINESS_LINE = 'הצגת קטלוג מוצרים של עסק באתר'    # GOA's approved brief, "Main action:"
GENERIC = 'Original hero/brand visual for a modern web product'   # image_provider's sentence when nothing is given
ENGLISH = 'A picture made from the customer words'               # what the translation double answers


def compile_contract(prompt):
    """These tests are about the MAIN picture's subject. A picture per listed item is the default since 2026-11-27
    (capability_planner.item_pictures_wanted: tests/test_item_pictures_default.py); here it is read as before, only
    when the customer asks for it in words, so that the GOA row (which lists its items) plans the one hero it did."""
    with mock.patch('omni_prod.capability_planner.item_pictures_wanted', side_effect=_picture_per_item):
        return ProductArchitect().compile(prompt, project_id='prj_image_subject', contract_version=1)


def images(contract):
    return [r for r in contract.capability_plan.requirements if r.key == G.IMAGE_CAPABILITY]


def with_customer_line(row, line):
    """The production row as it is, with one more line of the customer's own words before the approved brief."""
    head, brief = row['prompt'].split(MARKER, 1)
    return f'{head}\n{line}{MARKER}{brief}'


class Store:
    """Artifact store double (memory): the executor writes and reads the generated image through it."""

    def __init__(self):
        self.objects = {}

    def put_bytes(self, key, data):
        if key in self.objects:
            raise KeyError(key)
        self.objects[key] = bytes(data)
        return SimpleNamespace(sha256=hashlib.sha256(data).hexdigest(), size=len(data))

    def get_bytes(self, key, *, verify=True):
        return self.objects[key]


class Translator:
    """The translation model (image_prompt.gateway_translator calls gateway.complete)."""

    def __init__(self):
        self.calls = []

    def complete(self, **kw):
        self.calls.append(kw['user'])
        return ENGLISH


class Vision:
    """The vision model of lens 11 (image_match._ask calls gateway.complete_json)."""

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def complete_json(self, **kw):
        self.calls.append(json.loads(kw['user'])['customer_asked_to_see'])
        return self.answer


MATCH = {'matches': True, 'shows': 'התמונה שהתבקשה', 'reason': 'matches'}
MISMATCH = {'matches': False, 'shows': 'הרים', 'reason': 'mountains'}


def build_images(prompt, vision_answer):
    """The worker's order (worker_tasks: prepare_image_prompts -> capability_stage.prepare -> install) on the contract
    compiled from `prompt`. Returns what each double saw and what install did."""
    contract = compile_contract(prompt)
    api, store, translator, vision = FakePredictionAPI(), Store(), Translator(), Vision(vision_answer)
    stage = build_image_capability_stage(env=ENV, repository=MemoryCapabilityRepository(), artifact_store=store,
                                         journal=MemorySubmissionJournal(), worker_id='w1', urlopen=api,
                                         fetcher=_fetcher(api))
    stage.executor.provider_registry.get('image-predictions').sleep = lambda s: None
    plan = contract.capability_plan
    plan = prepare_image_prompts(plan, translate=gateway_translator(translator), store=store, build_id='bld_subject',
                                 project_id='prj_subject', only=set(stage.assignments_resolver(plan) or {}))
    evidence = stage.prepare(build_id='bld_subject', project_id='prj_subject', plan=plan,
                             authorized_maximum_usd=Decimal('0.05'), now=1000.0)
    core = SimpleNamespace(executor=None, repository_transform=None)
    out = SimpleNamespace(contract=contract, api=api, translator=translator, vision=vision, core=core, error=None,
                          sent=[c['body']['input'].get('prompt') for c in api.created])
    try:
        out.prompt = G.install(SimpleNamespace(core=core), prompt=contract.prompt, plan=plan, evidence=evidence,
                               store=store, vision=vision)
    except M.ImageDoesNotMatch as exc:
        out.error = exc
    return out


class TheFixtureIsTheProductionRow(unittest.TestCase):
    def test_the_redacted_prompts_hash_to_what_the_database_computed(self):
        for name, row in FX['rows'].items():
            with self.subTest(name):
                self.assertEqual(hashlib.md5(row['prompt'].encode('utf-8')).hexdigest(), row['redacted_md5'])


class EachTriggerGivesItsSubject(unittest.TestCase):
    """At planning time, from the trigger that made the requirement (ProductArchitect.compile -> the brain -> the
    capability planner)."""

    def test_shayfly_required_by_the_semantic_decision_plans_the_customers_quoted_words(self):
        contract = compile_contract(SHAYFLY['prompt'])
        (image,) = images(contract)
        self.assertEqual((image.id, image.purpose, image.required, image.quantity),
                         ('cap-media-image-generate', 'hero/brand visual', True, 1))     # the stored row's shape
        self.assertEqual(image.constraints['subject'], QUOTED)
        self.assertNotEqual(image.constraints['subject'], 'להציג ולמכור שלוש חבילות חופשה משפחתיות כשרות ולאפשר '
                                                          'בדיקת זמינות ומחיר דרך וואטסאפ')   # the quote comes first
        decisions = json.loads(SHAYFLY['prompt'].split('Semantic capability decisions v1: ', 1)[1].split('\n')[0])
        (decided,) = [d for d in decisions['decisions'] if d['key'] == G.IMAGE_CAPABILITY]
        self.assertEqual((decided['decision'], decided['evidence']), ('required', QUOTED))
        self.assertEqual(contract.status, BuildContractStatus.READY)
        self.assertEqual(contract.unresolved_questions, ())

    def test_goa_default_hero_plans_the_briefs_business_line(self):
        contract = compile_contract(GOA['prompt'])
        (image,) = images(contract)
        self.assertEqual((image.purpose, image.required), ('hero/brand visual', False))
        self.assertEqual(image.constraints['subject'], BUSINESS_LINE)
        self.assertIn(f'\nMain action: {BUSINESS_LINE}\n', GOA['prompt'])
        self.assertEqual(contract.status, BuildContractStatus.READY)

    def test_the_customers_own_clause_comes_first(self):
        contract = compile_contract(with_customer_line(GOA, 'תמונה ראשית: נרגילות צבעוניות על מדף בחנות'))
        (image,) = images(contract)
        self.assertTrue(image.required)                      # the customer asked for it
        self.assertEqual(image.constraints['subject'], 'נרגילות צבעוניות על מדף בחנות')


class NothingDescribesThePicture(unittest.TestCase):
    def test_an_optional_default_hero_with_no_business_line_is_not_planned(self):
        # GOA's row without its brief's "Main action:" line. A line the CUSTOMER wrote in that form is not the brief
        # and is never read as its business line.
        lines = [line for line in GOA['prompt'].split('\n') if not line.startswith('Main action: ')]
        prompt = with_customer_line({'prompt': '\n'.join(lines)}, 'Main action: dragons over a castle')
        contract = compile_contract(prompt)
        self.assertEqual(images(contract), [])
        self.assertIn(IMAGE_NOT_PLANNED, contract.capability_plan.notes)
        self.assertNotIn('image_subject', [q.id for q in contract.unresolved_questions])

    def test_a_required_picture_nothing_describes_is_the_contracts_question(self):
        # media_pipeline's own wider hero list holds "imagery"; generated_images.describe does not read it
        contract = compile_contract(with_customer_line(GOA, 'עם AI imagery'))
        self.assertEqual(images(contract), [])              # no image requirement, so no provider is ever asked
        self.assertIn(IMAGE_SUBJECT_UNRESOLVED, contract.capability_plan.notes)
        self.assertEqual(contract.status, BuildContractStatus.NEEDS_CLARIFICATION)
        (question,) = [q for q in contract.unresolved_questions if q.id == 'image_subject']
        self.assertTrue(question.material)
        self.assertEqual(question.question, 'מה התמונה באתר צריכה להראות? כתבו במשפט אחד מה רואים בה.')

    def test_the_question_is_in_the_customers_language(self):
        prompt = approved_prompt('A landing page for my bakery "Crumbs" in Leeds with AI imagery.',
                                 {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'})
        contract = compile_contract(prompt)
        (question,) = [q for q in contract.unresolved_questions if q.id == 'image_subject']
        self.assertEqual(question.question, 'What should the picture on the site show? Describe it in one sentence.')


class TheContractRefusesAnImageWithoutASubject(unittest.TestCase):
    def test_the_stored_production_requirements_are_refused(self):
        for name, row in FX['rows'].items():
            stored = row['stored_image_requirement']
            plan = CapabilityPlan((CapabilityRequirement(
                stored['id'], stored['key'], stored['purpose'], stored['required'], stored['quantity'],
                stored['constraints'], tuple(stored['dependency_ids'])),), ())
            with self.subTest(name), self.assertRaisesRegex(ValueError, 'cap-media-image-generate has no subject'):
                CapabilityRegistry().validate_plan(plan)

    def test_the_same_requirement_with_a_subject_is_accepted(self):
        stored = SHAYFLY['stored_image_requirement']
        plan = CapabilityPlan((CapabilityRequirement(
            stored['id'], stored['key'], stored['purpose'], stored['required'], stored['quantity'],
            {**stored['constraints'], 'subject': QUOTED}),), ())
        CapabilityRegistry().validate_plan(plan)


class ThePictureIsMadeFromTheSubject(unittest.TestCase):
    """The production rows through the real image path: the provider gets the subject's English line, never the
    generic sentence, and the image check judges the picture against the subject."""

    def test_shayfly_builds_with_the_picture_the_customer_asked_for(self):
        run = build_images(SHAYFLY['prompt'], MATCH)
        self.assertIsNone(run.error)                                      # was: image_mismatch, 25 s in
        self.assertEqual(run.translator.calls, [QUOTED])
        self.assertEqual(run.sent, [final_prompt(ENGLISH, 'hero/brand visual')])
        self.assertNotIn(GENERIC, run.sent[0])
        self.assertEqual(run.vision.calls, [QUOTED])
        self.assertEqual([(v['status'], v['subject']) for v in run.core.image_match], [('MATCH', QUOTED)])
        self.assertEqual(len(run.core.generated_images), 1)
        self.assertIn(f'alt="{QUOTED}"', run.prompt)

    def test_shayfly_still_stops_on_a_wrong_picture(self):
        run = build_images(SHAYFLY['prompt'], MISMATCH)                   # the butcher's rule (lens 11) is unchanged
        self.assertIsInstance(run.error, M.ImageDoesNotMatch)
        self.assertIn(f'asked "{QUOTED}"', str(run.error))

    def test_goa_keeps_a_matching_default_hero(self):
        run = build_images(GOA['prompt'], MATCH)
        self.assertIsNone(run.error)
        self.assertEqual(run.translator.calls, [BUSINESS_LINE])
        self.assertEqual(run.sent, [final_prompt(ENGLISH, 'hero/brand visual')])
        self.assertEqual(run.vision.calls, [BUSINESS_LINE])
        self.assertEqual([v['status'] for v in run.core.image_match], ['MATCH'])
        self.assertEqual(len(run.core.generated_images), 1)

    def test_goa_drops_a_wrong_default_hero_and_still_builds(self):
        run = build_images(GOA['prompt'], MISMATCH)
        self.assertIsNone(run.error)
        self.assertEqual([v['status'] for v in run.core.image_match], ['DROPPED'])
        self.assertNotIn('Generated images', run.prompt)


if __name__ == '__main__':
    unittest.main()

"""Every build carries a per-part provenance ledger (a vision slice, not a warehouse item): `.148ai/parts.json`, safe for the customer, inside
what provenance.json signs; the owner's view adds each generated image's spend.

The main case is the production row of the owner's law-firm brief (bld_b0eb47a5, prompt sha256 asserted), through the
worker's own order (worker_tasks.py:1220-1235) on real code only: the generated image installed by the real
generated_images.install (collect -> GeneratedImage -> _Transform), the content route's real fact sheet, render and
repository, the transform the engine applies, CreativeDirector.repository_files(capability_evidence=...),
RightsEngine.repository_files(original_prompt=PROMPT) and BrandingEngine.decorate_repository. The capability snapshot
has the shape capability_worker._snapshot returns (rows + usage events); its provider names and costs are planted so
the leak checks have something to find."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from omni_prod import generated_images as G
from omni_prod import part_ledger as PL
from omni_prod import vertical_palettes as VP
from omni_prod.branding import BrandingEngine
from omni_prod.capabilities import CapabilityPlan
from omni_prod.customer_views import is_internal_key
from omni_prod.fact_canon import decode_entities
from omni_prod.media_pipeline import CreativeDirector
from omni_prod.rehearsal import approved_prompt
from omni_prod.repository_assets import envelope, file_bytes, zip_bytes
from omni_prod.rights_ip import RightsEngine
from omni_prod.site_content import facts as Fx
from omni_prod.site_content import render as R
from omni_prod.uploaded_assets import _MainImage, logo_transform
from tests.test_generated_images_in_page import evidence_for, image_req
from tests.test_m495_capability_executor import MemoryStore

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
BUTCHER = json.loads((ROOT / 'tests' / 'fixtures' / 'butcher_served_page_2026_11_14.json').read_text(encoding='utf-8'))
TITLES = {'services': 'תחומי התמחות', 'about': 'על המשרד', 'process': 'איך זה עובד', 'faq': 'שאלות נפוצות',
          'contact': 'צור קשר'}
ORDER = ['hero', 'services', 'about', 'process', 'faq', 'contact']
SMALL_PNG = (ROOT / 'BRAND_PACK' / '148AI-logo-64.png').read_bytes()        # a logo: carried byte for byte
GEN_FILE = 'assets/148ai-image-1.webp'   # image weight (2026-11-26): a generated image is carried as its conversion
OTHER_PNG = (ROOT / 'BRAND_PACK' / '148AI-logo-128.png').read_bytes()
LARGE_PNG = (ROOT / 'BRAND_PACK' / '148AI-logo-master-transparent.png').read_bytes()   # over the budget: a rendition
RID = 'cap-media-image-generate'
LEAK = ('replicate', 'flux', 'gemini', 'openai', 'venice', 'anthropic', 'claude')
CUSTOMER_FACTS = ('03-5551234', '050-5551234', 'office@cohen-law.co.il', 'דרך מנחם בגין 132, תל אביב',
                  'א׳–ה׳ 09:00–18:00', '250 ₪')
BUTCHER_ANSWERS = {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'}
PROJECT, VERSION = 'prj_law', 'v_1'


def snapshot(store, blobs):
    """The capability stage's snapshot (capability_worker._snapshot): VERIFIED rows with their artifacts, and the
    provider usage events (capability_repository.usage_for_build: Decimal costs). Provider and model names planted."""
    ev = evidence_for(store, [(RID, 'VERIFIED', blobs)])
    ev['requirements'][0].update(selected_provider='replicate', pricing_version='replicate-flux-schnell-2026-11')
    ev['usage'] = [{'event_key': 'u1', 'requirement_id': RID, 'provider': 'replicate',
                    'pricing_version': 'replicate-flux-schnell-2026-11', 'estimated_cost_usd': Decimal('0.003'),
                    'maximum_cost_usd': Decimal('0.01'), 'actual_cost_usd': Decimal('0.003'), 'usage': {},
                    'evidence': {'provenance': {'model': 'black-forest-labs/flux-schnell', 'routed_by': 'venice',
                                                'fallbacks': ['gemini-2.5-flash-image', 'openai/gpt-image-1'],
                                                'prompt_writer': 'anthropic/claude-haiku-4-5'}}}]
    return ev


def install_image(prompt, blob):
    """generated_images.install, as the worker calls it: the engine gets the image and its transform."""
    store = MemoryStore()
    ev = snapshot(store, [blob])
    engine = SimpleNamespace(core=SimpleNamespace(executor=None, repository_transform=None))
    G.install(engine, prompt=prompt, plan=CapabilityPlan((image_req(),), ()), evidence=ev, store=store)
    return engine.core.generated_images[0], engine.core.repository_transform, ev


def records(repo, prompt, ev):
    """worker_tasks.py:1220-1224: the creative manifest, then the rights manifest with the approved prompt."""
    creative = CreativeDirector()
    repo.update(creative.repository_files(creative.plan(prompt), capability_evidence=ev))
    rights = RightsEngine()
    repo.update(rights.repository_files(rights.assess(prompt), original_prompt=prompt))
    return repo


def law_firm(prompt=PROMPT):
    """The repository the worker hands to decorate_repository on the content route (before decoration)."""
    image, transform, ev = install_image(prompt, SMALL_PNG)
    contract = R.render_contract(prompt, VP.palette_for('lawyers')[1])[0]
    sheet = Fx.fact_sheet(prompt, asset_plan=[{'place': 'hero', 'marker': image.marker, 'alt': image.alt,
                                               'source': 'generated', 'index': 1}], images=[image])
    html, _ = R.render(FIXTURE['scripted_content'], sheet, contract, expect_fp=contract['fingerprint'],
                       direction='formal', year='2026', outline_titles=TITLES, order=ORDER, windows=())   # the route serves none here
    spec = SimpleNamespace(acceptance=[SimpleNamespace(id='accept-site-content'), SimpleNamespace(id='CUSTOMER-FACTS')])
    files = R.repository(FIXTURE['scripted_content'], sheet, html, spec=spec, contract=contract,
                         bound=R.binds(sheet, contract, '2026'), order_names=[TITLES[k] for k in ORDER[1:]])
    return records(transform(files), prompt, ev)          # the engine's transform: marker -> the image file


def butcher():
    """A legacy-route build: the butcher's production request through rehearsal.approved_prompt, its production page
    (served by the model's app.py) with the D5 hero carried as a file, the model's project.json (no site_route)."""
    prompt = approved_prompt(BUTCHER['brief']['prompt'], BUTCHER_ANSWERS)
    image, transform, ev = install_image(prompt, LARGE_PNG)
    page = BUTCHER['page'].replace('data:image/gif;base64,R0lGODlhAQABAAAAACw=', image.marker, 1)
    app = f'HTML_CONTENT = {page!r}\n# the model serves HTML_CONTENT and /assets/<name>\n'
    project = json.dumps({'schema_version': 2, 'runtime': 'python:3.11-slim', 'start': ['python', 'app.py'],
                          'port': 8000, 'health_path': '/'})
    return records(transform({'app.py': app, '.omni/project.json': project}), prompt, ev), prompt


def decorate(repo, **kw):
    return BrandingEngine().decorate_repository(copy.deepcopy(repo), plan='pro', project_id=PROJECT,
                                                version_hint=VERSION, **kw)


def parts(decorated) -> dict:
    return json.loads(decorated[PL.PARTS_PATH])


def by_path(led, part) -> dict:
    return {i['path']: i for i in led['parts'][part]['items'] if 'path' in i}


def facts(led) -> dict:
    return {i['value']: i for i in led['parts']['facts']['items']}


def norm(text):
    return ' '.join(decode_entities(text).split())


def keys(value):
    if isinstance(value, dict):
        return [k for k in value] + [x for v in value.values() for x in keys(v)]
    if isinstance(value, list):
        return [x for v in value for x in keys(v)]
    return []


class TheProductionRowThroughTheWorkersChain(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        assert hashlib.sha256(PROMPT.encode('utf-8')).hexdigest() == FIXTURE['prompt_sha256']
        cls.before = law_firm()
        cls.decorated = decorate(cls.before)
        cls.parts = parts(cls.decorated)
        cls.full = PL.ledger(cls.decorated)

    def test_the_fixture_is_the_production_prompt(self):
        self.assertEqual(FIXTURE['prompt_sha256'], '41d10d6333900cf116de9da2e3ed38cffb58398fad8143132b4cab1d1eb5db61')
        self.assertEqual(FIXTURE['build_id'], 'bld_b0eb47a553c8442abdbc8ada7f2439dc')
        self.assertEqual(self.parts['brief_sha256'], FIXTURE['prompt_sha256'])

    def test_the_ledger_is_complete_and_every_file_is_claimed_once(self):
        self.assertEqual((self.parts['schema'], self.parts['route']), ('148ai.parts/1', 'section_library/1'))
        self.assertEqual(self.parts['unresolved'], [])
        self.assertTrue(self.parts['complete'])
        claimed = [f['path'] for f in self.parts['files']]
        self.assertEqual(len(claimed), len(set(claimed)))
        self.assertEqual(set(claimed) | set(PL.SIGNING_FILES), set(self.decorated))
        for part in self.parts['parts'].values():
            for item in part['items']:
                self.assertIn(item['origin'], PL.ORIGINS)

    def test_each_fact_the_customer_said_is_customer_words(self):
        got = facts(self.parts)
        self.assertEqual(sorted(got), sorted(CUSTOMER_FACTS))
        for value in CUSTOMER_FACTS:
            self.assertEqual(got[value]['origin'], 'customer_words', value)
        self.assertEqual(got['050-5551234']['basis'], 'customer_facts_line')     # said in the conversation, not the request
        self.assertEqual(got['03-5551234']['basis'], 'request')

    def test_no_value_is_customer_words_unless_it_is_in_customer_text(self):
        said = norm(Fx.customer_text(PROMPT))
        for value, item in facts(self.parts).items():
            if item['origin'] == 'customer_words':
                self.assertIn(norm(value), said)
        design = self.parts['parts']['design']['items'][0]
        for word in design['customer_said'].replace(',', ' ').split():
            self.assertIn(word, said)

    def test_the_design_is_the_customers_colour(self):
        design = self.parts['parts']['design']['items']
        self.assertEqual(len(design), 1)
        self.assertEqual((design[0]['origin'], design[0]['basis'], design[0]['customer_said']),
                         ('customer_words', 'requested colour description', 'כחול כהה, לבן'))
        self.assertIn({'property': '--color-primary', 'value': '#1e3a5f'}, design[0]['values'])
        self.assertEqual(design[0]['values_from'], ['public/index.html'])
        self.assertTrue(design[0]['brief_primary_on_page'])

    def test_the_generated_image_is_linked_to_its_verified_requirement(self):
        image = by_path(self.full, 'images')[GEN_FILE]
        self.assertEqual((image['origin'], image['requirement_id'], image['index'], image['bytes']),
                         ('ai_generated', RID, 1, 'web_rendition'))
        self.assertEqual(image['sha256'], hashlib.sha256(file_bytes(GEN_FILE, self.before[GEN_FILE])).hexdigest())
        self.assertEqual(image['artifact_sha256'], hashlib.sha256(SMALL_PNG).hexdigest())
        self.assertNotEqual(image['artifact_sha256'], image['sha256'])       # the page's file is the conversion

    def test_the_route_files_have_the_routes_origins(self):
        code, page, copy_ = (by_path(self.parts, p) for p in ('code', 'page', 'copy'))
        for path in ('app.py', 'tests/test_site.py', '.omni/project.json'):
            self.assertEqual(code[path]['origin'], 'platform_fixed', path)
        self.assertEqual(page['public/index.html']['origin'], 'platform_rendered')
        self.assertEqual(copy_['content/site.json']['origin'], 'ai_written')
        self.assertEqual(by_path(self.parts, 'platform_records')['rights/rights-manifest.json']['origin'],
                         'platform_record')

    def test_the_provenance_signature_covers_parts_json(self):
        signed = {**self.before, PL.PARTS_PATH: self.decorated[PL.PARTS_PATH]}
        source = '\n'.join(f'{k}\0{signed[k]}' for k in sorted(signed)) + f'\0{PROJECT}\0{VERSION}'
        provenance = json.loads(self.decorated['.148ai/provenance.json'])
        self.assertEqual(provenance['repository_signature_sha256'], hashlib.sha256(source.encode('utf-8')).hexdigest())
        tampered = {**signed, PL.PARTS_PATH: signed[PL.PARTS_PATH].replace('customer_words', 'customer_approved', 1)}
        other = '\n'.join(f'{k}\0{tampered[k]}' for k in sorted(tampered)) + f'\0{PROJECT}\0{VERSION}'
        self.assertNotEqual(provenance['repository_signature_sha256'], hashlib.sha256(other.encode('utf-8')).hexdigest())

    def test_decorating_twice_gives_byte_identical_parts_and_signature(self):
        again = decorate(law_firm())
        self.assertEqual(again[PL.PARTS_PATH], self.decorated[PL.PARTS_PATH])
        self.assertEqual(again['.148ai/provenance.json'], self.decorated['.148ai/provenance.json'])
        self.assertEqual(decorate(self.before)[PL.PARTS_PATH], self.decorated[PL.PARTS_PATH])

    def test_the_ledger_written_is_the_ledger_of_the_decorated_repository(self):
        self.assertEqual(PL.customer_view(PL.ledger(self.decorated)), self.parts)
        self.assertEqual(PL.ledger(self.decorated), PL.ledger(self.before))


class TheCustomerViewLeaksNothing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decorated = decorate(law_firm())

    def test_the_input_manifest_carries_providers_and_cost(self):
        manifest = self.decorated[PL.ASSET_MANIFEST].lower()
        for word in LEAK:
            self.assertIn(word, manifest)
        self.assertIn('estimated_cost_usd', manifest)

    def test_parts_json_has_no_internal_key_and_no_provider_name(self):
        for view in (parts(self.decorated), PL.customer_view(PL.owner_view(self.decorated))):
            found = [k for k in keys(view) if is_internal_key(k) or k in PL.CUSTOMER_HIDDEN]
            self.assertEqual(found, [])
            text = json.dumps(view, ensure_ascii=False).lower()
            self.assertEqual([w for w in LEAK if w in text], [])

    def test_the_owner_view_carries_each_images_cost(self):
        owner = PL.owner_view(self.decorated)
        image = by_path(owner, 'images')[GEN_FILE]
        self.assertEqual((image['provider'], image['pricing_version'], image['estimated_cost_usd'],
                          image['maximum_cost_usd'], image['actual_cost_usd'], image['cost_truth']),
                         ('replicate', 'replicate-flux-schnell-2026-11', '0.003', '0.01', '0.003', 'ACTUAL'))
        for name in ('facts', 'copy', 'page', 'code', 'design', 'platform_records'):
            self.assertIsNone(owner['parts'][name]['cost'])
            self.assertEqual(owner['parts'][name]['cost_basis'], 'not attributed per part (build-level spend only)')


class TheRuleAgainstCreditingTheCustomer(unittest.TestCase):
    def test_a_value_only_in_the_approved_brief_is_customer_approved(self):
        """A price planted in the brief's 'Initial content' line -- intake's summary, not the customer's sentence. The
        content route's fact sheet takes it (site_content.facts.customer_text includes that line), so it reaches
        content/facts.json; the ledger never credits it to the customer."""
        line = '; ייעוץ ראשון 250 ₪\n'
        self.assertEqual(PROMPT.count(line), 1)
        planted = PROMPT.replace(line, '; ייעוץ ראשון 250 ₪; ייעוץ המשך 180 ₪\n', 1)
        self.assertNotIn('180', PROMPT)
        self.assertIn('180 ₪', Fx.customer_text(planted))       # the truth gate's text has it; the customer never said it
        led = parts(decorate(law_firm(planted)))
        got = facts(led)
        self.assertEqual((got['180 ₪']['origin'], got['180 ₪']['basis']), ('customer_approved', 'approved_brief'))
        self.assertEqual(got['250 ₪']['origin'], 'customer_words')
        self.assertTrue(led['complete'])


class TheLegacyRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before, cls.prompt = butcher()
        cls.led = parts(decorate(cls.before))

    def test_the_brief_is_composed_by_the_conversations_own_functions(self):
        design = [ln for ln in self.prompt.splitlines() if ln.startswith('Design:')]
        self.assertEqual(len(design), 1)
        self.assertIn('the customer stated no colour', design[0])
        self.assertNotIn('requested colour description', design[0])

    def test_design_is_the_platform_default_and_page_and_code_are_ai_written(self):
        self.assertEqual(self.led['route'], 'legacy')
        design = self.led['parts']['design']['items']
        self.assertEqual([d['origin'] for d in design], ['platform_default'])
        self.assertEqual(design[0]['brief_primary'], '#991b1b')
        self.assertFalse(design[0]['brief_primary_on_page'])     # the 2026-11-14 page chose its own blue: said, not hidden
        self.assertEqual(self.led['parts']['page']['items'], [{'origin': 'ai_written', 'inside': ['app.py']}])
        self.assertEqual({p: i['origin'] for p, i in by_path(self.led, 'code').items()},
                         {'app.py': 'ai_written', '.omni/project.json': 'ai_written'})

    def test_the_generated_hero_is_a_web_rendition_of_its_artifact(self):
        image = by_path(self.led, 'images')
        self.assertEqual(list(image), ['assets/148ai-image-1.webp'])
        item = image['assets/148ai-image-1.webp']
        self.assertEqual((item['origin'], item['bytes'], item['artifact_sha256']),
                         ('ai_generated', 'web_rendition', hashlib.sha256(LARGE_PNG).hexdigest()))
        self.assertTrue(self.led['complete'], self.led['unresolved'])


class NothingDefaultsSilently(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = law_firm()

    def test_an_unclaimed_file_is_unresolved(self):
        led = parts(decorate({**self.before, 'notes/todo.txt': 'x'}))
        self.assertFalse(led['complete'])
        self.assertEqual(led['unresolved'], [{'path': 'notes/todo.txt',
                                              'reason': 'no producer the ledger knows writes this file'}])
        self.assertNotIn('notes/todo.txt', [f['path'] for f in led['files']])

    def test_an_unattested_generated_image_is_unresolved(self):
        led = parts(decorate({**self.before, 'assets/148ai-image-2.png': envelope(OTHER_PNG, 'image/png')}))
        self.assertFalse(led['complete'])
        self.assertEqual(led['unresolved'], [{'path': 'assets/148ai-image-2.png',
                                              'reason': 'a generated image with no verified artifact in the asset '
                                                        'manifest'}])
        self.assertEqual(list(by_path(led, 'images')), [GEN_FILE])

    def test_a_verified_artifact_without_its_file_and_a_file_that_is_not_its_artifact(self):
        missing = {k: v for k, v in self.before.items() if k != GEN_FILE}
        led = parts(decorate(missing))
        self.assertEqual(led['unresolved'], [{'path': 'assets/148ai-image-1.*', 'reason': 'verified generated image 1 '
                                              'of the asset manifest has no file in the repository'}])
        # in its place, a PNG that is not its artifact: a converted image is WebP or JPEG, never a PNG (2026-11-26)
        swapped = parts(decorate({**missing, 'assets/148ai-image-1.png': envelope(OTHER_PNG, 'image/png')}))
        self.assertEqual([u['path'] for u in swapped['unresolved']], ['assets/148ai-image-1.png'])
        self.assertIn('not its verified artifact', swapped['unresolved'][0]['reason'])
        self.assertFalse(led['complete'] or swapped['complete'])

    def test_an_unknown_origin_or_route_raises(self):
        with self.assertRaises(ValueError):
            PL.check_origin('customer_said')
        project = json.loads(self.before['.omni/project.json'])
        odd = {**self.before, '.omni/project.json': json.dumps({**project, 'site_route': 'section_library/2'})}
        with self.assertRaises(ValueError):
            PL.ledger(odd)
        with self.assertLogs('omni_prod.branding', 'ERROR') as logged:
            led = parts(decorate(odd))
        self.assertEqual(led, {'schema': '148ai.parts/1', 'complete': False,
                               'error': "LedgerError: unknown site_route 'section_library/2' in .omni/project.json "
                                        "(known: 'section_library/1')"})
        self.assertIn('PART_LEDGER complete=False', logged.output[0])

    def test_a_bare_repository_still_gets_a_ledger_that_says_what_is_missing(self):
        led = parts(BrandingEngine().decorate_repository({'index.html': '<html><body></body></html>'}, plan='free',
                                                         project_id='p'))
        self.assertEqual((led['schema'], led['complete']), ('148ai.parts/1', False))
        self.assertIn({'path': 'rights/rights-manifest.json',
                       'reason': 'missing: there is no approved brief to read origins from'}, led['unresolved'])


class TheCustomersOwnFiles(unittest.TestCase):
    """The logo and a photo the customer uploaded, carried by the real transforms (uploaded_assets.logo_transform and
    _MainImage through generated_images._Transform) and bound by the brief's own lines (discovery.requirements_text)."""

    @classmethod
    def setUpClass(cls):
        logo_sha, photo_sha = hashlib.sha256(SMALL_PNG).hexdigest(), hashlib.sha256(LARGE_PNG).hexdigest()
        cls.prompt = (PROMPT + f'\nUploaded logo attachment: att_{"a" * 32}; sha256={logo_sha}. Use the original '
                      'uploaded logo in a visible img element with src="148ai-asset://logo".\n'
                      f'Uploaded image 1 attachment: att_{"b" * 32}; sha256={photo_sha}; src="148ai-asset://upload/1"; '
                      'placement: hero; role place: "המשרד מבפנים". The customer\'s own photo: use it AS IS.\n')
        repo = law_firm()
        repo = logo_transform(SMALL_PNG, 'image/png', logo_sha)(repo)
        cls.photo = _MainImage(LARGE_PNG, 'image/png', photo_sha, 'המשרד מבפנים', index=1, place='hero')
        repo = G._Transform(None, [cls.photo])(repo)
        rights = RightsEngine()
        repo.update(rights.repository_files(rights.assess(cls.prompt), original_prompt=cls.prompt))
        cls.before = repo

    def test_the_logo_and_the_photo_are_the_customers_uploads(self):
        led = parts(decorate(self.before))
        self.assertTrue(led['complete'], led['unresolved'])
        images = by_path(led, 'images')
        self.assertEqual(images['assets/148ai-logo.png']['origin'], 'customer_upload')
        self.assertEqual(images['assets/148ai-logo.png']['bytes'], 'identical')
        photo = images[self.photo.uri]
        self.assertEqual((photo['origin'], photo['bound_to'], photo['place'], photo['bytes'], photo['original_sha256']),
                         ('customer_upload', 'uploaded_image_1', 'hero', 'web_rendition',
                          hashlib.sha256(LARGE_PNG).hexdigest()))
        self.assertTrue(self.photo.rendition['changed'])

    def test_a_logo_the_brief_did_not_bind_and_a_second_file_are_unresolved(self):
        swapped = parts(decorate({**self.before, 'assets/148ai-logo.png': envelope(OTHER_PNG, 'image/png')}))
        self.assertEqual(swapped['unresolved'], [{'path': 'assets/148ai-logo.png',
                                                  'reason': "the logo file's sha256 is not the one the approved brief "
                                                            'bound'}])
        # a valid PNG file next to the generated image's WebP (its conversion since 2026-11-26): two files for
        # generated image 1, and neither is taken for it
        twice = parts(decorate({**self.before, 'assets/148ai-image-1.png': envelope(OTHER_PNG, 'image/png')}))
        self.assertEqual([u['path'] for u in twice['unresolved']],
                         ['assets/148ai-image-1.png', 'assets/148ai-image-1.webp'])
        self.assertIn('not its verified artifact', twice['unresolved'][0]['reason'])
        self.assertIn('a second file for the same image', twice['unresolved'][1]['reason'])
        self.assertFalse(swapped['complete'] or twice['complete'])


class TheExportedVersion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decorated = decorate(law_firm())
        cls.zip = zip_bytes(cls.decorated)

    def cli(self, *args, data=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'version.zip'
            path.write_bytes(data or self.zip)
            return subprocess.run([sys.executable, '-m', 'omni_prod.part_ledger', str(path), *args], cwd=ROOT,
                                  capture_output=True, text=True, timeout=120)

    def test_the_cli_on_the_zip_gives_the_same_ledger(self):
        self.assertEqual(PL.read_zip(self.zip), self.decorated)
        self.assertEqual(PL.ledger(PL.read_zip(self.zip)), PL.ledger(self.decorated))
        run = self.cli()
        self.assertEqual(run.returncode, 0, run.stderr[-2000:])
        self.assertEqual(json.loads(run.stdout), parts(self.decorated))
        owner = self.cli('--owner')
        self.assertEqual(owner.returncode, 0, owner.stderr[-2000:])
        self.assertEqual(json.loads(owner.stdout), PL.owner_view(self.decorated))

    def test_an_incomplete_version_exits_non_zero(self):
        run = self.cli(data=zip_bytes({**self.decorated, 'notes/todo.txt': 'x'}))
        self.assertEqual(run.returncode, 1)
        self.assertFalse(json.loads(run.stdout)['complete'])


class TheRouteFilesAreRendersOwn(unittest.TestCase):
    def test_the_constants_equal_the_renderers(self):
        self.assertEqual((PL.PAGE, PL.SITE_JSON, PL.FACTS_JSON, PL.PLATFORM_FILES),
                         (R.PAGE, R.SITE_JSON, R.FACTS_JSON, R.PLATFORM_FILES))
        self.assertEqual(PL.IMAGE_CAPABILITY, G.IMAGE_CAPABILITY)
        self.assertEqual(PL.VERBATIM_LINE, Fx.CUSTOMER_LINES[0])
        self.assertEqual(PL.BRIEF_MARKER, Fx.BRIEF_MARKER)


if __name__ == '__main__':
    unittest.main()

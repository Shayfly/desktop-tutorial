"""The content route is chosen only when every precondition holds, and every other build says why it stays on the
legacy path (site_content.decide). OMNI_SITE_LIBRARY = off | accounts | on: an unknown value raises, 'accounts' with no
account listed raises. With the flag off nothing changes: the engine's parts are the same objects and a whole engine
build sends the model the same calls and returns the same repository as a build without the route
(the CTO's decision 1). Every palette the library knows carries the voice and the sections the route reads.

The base prompt is the owner's law-firm brief, a production row read read-only (tests/fixtures/
site_content_bld_b0eb47a5.json; its fingerprint is asserted in test_site_content_render.py)."""
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import site_content as SC
from omni_prod.section_library import DIRECTIONS

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
OWNER = {'user_id': 'usr_owner_test'}
REQUEST_END = PROMPT.index('--- Approved project brief')


def on(**extra):
    return mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'on', **extra})


def with_request(text: str, prompt: str = PROMPT) -> str:
    """The prompt with `text` added to the customer's request (before the approved brief)."""
    end = prompt.index('--- Approved project brief')
    return prompt[:end] + text + '\n' + prompt[end:]


def with_brief_line(line: str) -> str:
    return PROMPT + '\n' + line


def decide(prompt=PROMPT, request=OWNER, **kw):
    return SC.decide(prompt, request, year='2026', **kw)


class TheFlag(unittest.TestCase):
    def test_it_is_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('OMNI_SITE_LIBRARY', None)
            self.assertEqual(SC.mode(), 'off')
            self.assertEqual((decide().route, decide().reason), ('legacy', 'flag_off'))

    def test_an_unknown_value_raises(self):
        for value in ('yes', '1', 'true', 'founder'):
            with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': value}):
                with self.assertRaises(ValueError, msg=value):
                    SC.mode()
                with self.assertRaises(ValueError, msg=value):
                    SC.install(SimpleNamespace(), prompt=PROMPT, gateway=None, request=OWNER)

    def test_accounts_reads_the_list_and_an_empty_list_raises(self):
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'accounts', 'OMNI_SITE_LIBRARY_ACCOUNTS': ''}):
            with self.assertRaises(ValueError):
                decide()
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'accounts',
                                          'OMNI_SITE_LIBRARY_ACCOUNTS': 'usr_a, usr_owner_test'}):
            self.assertEqual(decide().route, 'section_library')
            self.assertEqual(decide(request={'user_id': 'usr_someone_else'}).reason, 'account_not_listed')
            self.assertEqual(decide(request=None).reason, 'account_not_listed')


class TheDecisionTable(unittest.TestCase):
    maxDiff = None

    def test_the_owners_brief_takes_the_route_with_its_outline(self):
        with on():
            route = decide()
        self.assertEqual((route.route, route.palette, route.direction), ('section_library', 'counsel', 'formal'))
        self.assertEqual(route.order, ['hero', 'services', 'about', 'process', 'faq', 'contact'])
        self.assertEqual(route.outline_titles['contact'], 'צור קשר')
        self.assertEqual(route.contract_source, 'brief-primary+category')   # the brief states two colours, not four
        self.assertEqual(route.contract['tokens']['--color-primary'], '#1e3a5f')
        # warehouse 126: a pair from the font-pair library, no longer the Design line's one font for body and headings
        self.assertEqual((route.script, route.font_pair), ('hebrew', 'he-frank-heebo'))
        self.assertEqual((route.contract['tokens']['--font-family'], route.contract['tokens']['--font-display']),
                         ("'Heebo', system-ui, sans-serif", "'Frank Ruhl Libre', serif"))

    def test_every_legacy_reason(self):
        logo = 'Uploaded logo attachment: att_' + 'a' * 32 + '; sha256=' + 'b' * 64 + '.'
        gallery = ('Uploaded image 1 attachment: att_' + 'c' * 32 + '; sha256=' + 'd' * 64
                   + '; src="148ai-asset://upload/1"; placement: gallery; role place: "המשרד".')
        from omni_prod.window_catalog import prompt_lines
        cases = {
            'not_content_only': PROMPT.replace('Product kind: CONTENT-ONLY website', 'Product kind: web app'),
            'not_hebrew': ('A website for my law firm Cohen and Co. Phone 03-5551234.\n--- Approved project brief '
                           '(binding; fingerprint 0123456789abcdef) ---\nSign-in: NONE. Do not add login.\n'
                           'Do not store personal or contact details of people.\nProduct kind: CONTENT-ONLY website.'),
            'uploaded_logo': with_brief_line(logo),
            'approved_windows: mega_menu': with_brief_line('\n'.join(prompt_lines(['mega_menu']))),
            'image_place_gallery': with_brief_line(gallery),
            'icon_image': with_request('אני רוצה גם לוגו למשרד.'),
            'several_pictures': with_request('אני רוצה 3 תמונות של המשרד.'),
            'no_design_contract: ': PROMPT.replace("primary colour #1e3a5f; palette #1e3a5f, #ffffff; ", ''),
            'phone_not_one': with_request('טלפון נוסף: 04-8123456.'),
            'whatsapp_number_unknown': with_request('נייד: 054-6612345.').replace('וואטסאפ: 050-5551234', 'נייד'),
            'address_not_one': with_request('סניף נוסף: רחוב הרצל 12, חיפה.'),
            'email_not_one': with_request('מייל נוסף: info@cohen-law.co.il'),
            'outline_unmapped: ': PROMPT.replace('4. איך זה עובד:', '4. הצוות שלנו:', 1),
            'outline_repeated: ': PROMPT.replace('4. איך זה עובד:', '4. שירותים:', 1),
            'outline_hero_not_first': PROMPT.replace('1. פתיח:', '1. תחומי עיסוק:', 1).replace(
                '2. תחומי התמחות:', '2. פתיח:', 1),
            'outline_without_basis: ': PROMPT.replace('4. איך זה עובד:', '4. המלצות:', 1),
            # no declared name and no name the customer quoted: the model never chooses one
            'name_not_declared': PROMPT.replace('"כהן ושות׳ – דיני עבודה"', 'כהן ושות׳ – דיני עבודה'),
        }
        got = {}
        with on():
            for reason, prompt in cases.items():
                got[reason] = decide(prompt).reason
            got['plan_governed'] = decide(plan_governed=True).reason
            with mock.patch.dict(DIRECTIONS['palettes'], {}, clear=True):
                got['palette_not_in_library: '] = decide().reason
        for reason, said in got.items():
            with self.subTest(reason=reason):
                self.assertTrue(said == reason or (reason.endswith(': ') and said.startswith(reason)), said)

    def test_a_named_whatsapp_goes_to_the_labelled_number_or_the_only_mobile_never_a_landline(self):
        from omni_prod.site_content import facts as Fx
        sheet = Fx.fact_sheet(PROMPT)
        self.assertEqual((sheet.phone, sheet.whatsapp, sheet.whatsapp_basis), ('03-5551234', '050-5551234', 'labelled'))
        only_mobile = PROMPT.replace('וואטסאפ: 050-5551234', 'נייד')
        sheet = Fx.fact_sheet(only_mobile)
        self.assertEqual((sheet.whatsapp, sheet.whatsapp_basis), ('050-5551234', 'only_mobile'))
        landline = PROMPT.replace('וואטסאפ: 050-5551234', 'נייד').replace('| 050-5551234', '')
        sheet = Fx.fact_sheet(landline)
        self.assertEqual((sheet.whatsapp, sheet.whatsapp_basis), (None, 'unknown'))
        self.assertIn('whatsapp_number_unknown', sheet.problems)
        unnamed = PROMPT.replace('וכפתור וואטסאפ', 'וכפתור חיוג').replace('וואטסאפ: 050-5551234', 'נייד')
        sheet = Fx.fact_sheet(unnamed)
        self.assertEqual((sheet.whatsapp, sheet.whatsapp_basis), (None, None))

    def test_a_whatsapp_the_customer_says_no_to_takes_the_legacy_path(self):
        from omni_prod.site_content import facts as Fx
        no_button = PROMPT.replace('וכפתור וואטסאפ', 'וכפתור חיוג')
        negated = {
            # the brief's own evidence line still labels 050-5551234 WhatsApp: the customer's "no" wins
            'no whatsapp': with_request('אין לנו וואטסאפ.', no_button),
            'an affirmative and a negated mention': with_request('בלי כפתור וואטסאפ בראש העמוד.'),
        }
        with on():
            for label, prompt in negated.items():
                with self.subTest(label):
                    self.assertEqual(decide(prompt).reason, 'whatsapp_negated')
                    sheet = Fx.fact_sheet(prompt)
                    self.assertEqual((sheet.whatsapp, sheet.whatsapp_basis), (None, 'negated'))
        only_mobile = Fx.fact_sheet('בלי וואטסאפ, רק שיחות טלפון. נייד: 050-7654321.')
        self.assertEqual((only_mobile.whatsapp, only_mobile.problems[:1]), (None, ['whatsapp_negated']))
        english = Fx.fact_sheet('A site for my shop. We have no WhatsApp. Mobile 050-7654321.')
        self.assertEqual(english.whatsapp_basis, 'negated')

    def test_a_landline_labelled_whatsapp_is_never_sent_to_wa_me(self):
        from omni_prod.site_content import facts as Fx
        landline = PROMPT.replace('וואטסאפ: 050-5551234', 'נייד').replace('| 050-5551234', '')
        prompt = with_request('וואטסאפ: 03-5551234.', landline)
        with on():
            self.assertEqual(decide(prompt).reason, 'whatsapp_landline')
        sheet = Fx.fact_sheet(prompt)
        self.assertEqual((sheet.whatsapp, sheet.whatsapp_basis), (None, 'landline'))

    def test_a_whatsapp_label_never_crosses_a_sentence_or_another_label(self):
        from omni_prod import fact_canon as F
        from omni_prod.site_content import facts as Fx

        def whatsapp(text):
            return Fx._whatsapp(text, F.build_canon(text), Fx.customer_text(text))[:2]
        # the landline after the full stop is not labelled; the only mobile is WhatsApp's
        self.assertEqual(whatsapp('אפשר גם בוואטסאפ. 03-5551234 במשרד, 050-7654321 בנייד.'),
                         ('050-7654321', 'only_mobile'))
        # another fact's label inside the gap: the phone is that fact's
        self.assertEqual(whatsapp('כפתור וואטסאפ טלפון 03-5551234, נייד 050-7654321'), ('050-7654321', 'only_mobile'))
        self.assertEqual(whatsapp('וואטסאפ: 050-7654321. טלפון: 03-5551234.'), ('050-7654321', 'labelled'))

    def test_every_decision_is_logged_and_kept_for_the_evidence(self):
        engine = SimpleNamespace()
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'off'}), self.assertLogs('omni_prod.site_content') as logs:
            SC.install(engine, prompt=PROMPT, gateway=None, request=OWNER)
        self.assertIn('SITE_ROUTE route=legacy reason=flag_off', logs.output[0])
        self.assertEqual(SC.report(engine)['reason'], 'flag_off')


class EveryPaletteHasAVoiceAndSections(unittest.TestCase):
    def test_every_library_palette_and_every_catalogue_palette(self):
        catalogue = json.loads((ROOT / 'omni_prod' / 'vertical_palettes.json').read_text(encoding='utf-8'))['palettes']
        self.assertEqual(set(catalogue) - set(DIRECTIONS['palettes']), set())
        for name, entry in DIRECTIONS['palettes'].items():
            with self.subTest(palette=name):
                self.assertRegex(entry['voice'], '[א-ת]')
                self.assertEqual(entry['sections'][0], 'hero')
                self.assertIn('contact', entry['sections'])
                self.assertEqual(len(set(entry['sections'])), len(entry['sections']))
                from omni_prod.site_content.schema import SECTIONS
                self.assertEqual(set(entry['sections']) - set(SECTIONS), set())


# ---- flag off: byte-identical --------------------------------------------------------------------------------------
SPEC = {'title': 'משרד', 'summary': 's', 'stack': {'runtime': 'python'},
        'requirements': [{'id': 'R1', 'text': 'the page', 'kind': 'functional'}],
        'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'GET / returns the page'}]}
FILES = {'files': [{'path': 'app.py', 'content': 'print("legacy")\n'}, {'path': 'public/index.html', 'content': '<p>x</p>'}]}


class ScriptedGateway:
    """The model gateway, scripted (the only double): the architect gets a spec, the generator files."""
    accepts_task_tag = False

    def __init__(self):
        self.calls = []

    def complete_json(self, **kwargs):
        self.calls.append(json.dumps(kwargs, ensure_ascii=False, sort_keys=True, default=str))
        return SPEC if kwargs['system'].startswith('You are Omni Architect') else FILES


class Passing:
    def execute(self, *, repository, spec):
        from omni_prod.autonomous_core import ExecutionReport
        return ExecutionReport(True, (), 'ok')


def legacy_engine(gateway):
    from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
    from omni_prod.autonomous_core import AutonomousProductEngine
    return AutonomousProductEngine(architect=ArchitectAgent(gateway), generator=GeneratorAgent(gateway),
                                   repairer=RepairAgent(gateway), executor=Passing())


class WithTheFlagOffNothingChanges(unittest.TestCase):
    def test_the_engine_parts_are_the_same_objects_and_the_build_is_byte_identical(self):
        from omni_prod.site_content import facts as Fx
        plain_gw, routed_gw = ScriptedGateway(), ScriptedGateway()
        plain, routed = legacy_engine(plain_gw), legacy_engine(routed_gw)
        before = (routed.architect, routed.generator, routed.repairer, routed.executor)
        with mock.patch.dict(os.environ, {'OMNI_SITE_LIBRARY': 'off'}), \
                mock.patch.object(Fx, 'fact_sheet', side_effect=AssertionError('the flag is off: nothing is read')):
            SC.install(routed, prompt=PROMPT, gateway=routed_gw, request=OWNER)
        self.assertEqual((routed.architect, routed.generator, routed.repairer, routed.executor), before)
        a, b = plain.build(PROMPT), routed.build(PROMPT)
        self.assertEqual(plain_gw.calls, routed_gw.calls)
        self.assertEqual((a.status, a.repository, a.spec.to_dict()), (b.status, b.repository, b.spec.to_dict()))
        self.assertGreater(len(plain_gw.calls), 1)

    def test_the_worker_installs_it_before_anything_wraps_the_architect(self):
        source = (ROOT / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        at = source.index('site_content.install(')
        self.assertLess(source.index('engine, gateway = components_factory()'), at)
        for later in ('install_uploaded_assets(engine', 'install_facts(engine, prompt)', 'install_page_outline(engine',
                      'agentic_repair = _install_agentic_repair(engine, request)', 'install_apple_gate(engine'):
            self.assertLess(at, source.index(later), later)


if __name__ == '__main__':
    unittest.main()

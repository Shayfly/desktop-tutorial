"""Production 2026-11-16, "148 דלתות" (bld_426addd3): the customer's photo never reached the page.

The page carried src="148ai-asset://upload/1"; the browser does not know the scheme, and img#hero-image was a broken
image. Root cause: the worker builds from the BUILD CONTRACT's prompt, and ProductArchitect.compile stores that prompt
with its whitespace collapsed (product_architect.py: `clean = " ".join(prompt.split())`), so it has no line breaks.
The uploaded-image binding was anchored to a line start (`^`, re.M). On the contract it matched nothing, and
install_main_image returned without a word. No transform replaced the marker, and the raw address reached the browser.
A bug of Claude's (845051a).

Both discarded repair rounds came from that same cause: round 1 swapped in an http URL ("Unexpected identifier
'http'"), round 2 still had no visible image -- the platform never gave the page the bytes.

The same class of bug, also Claude's (3db7d57), broke the approved-windows reader. The window gate checked nothing on a
contract build, and the fact canon lost the windows. The MISSING-facts line reader had the same flaw.

Real path: the production contract row as stored, with its fingerprint and prompt digest checked. It goes
BuildContract.from_dict -> .prompt -> uploaded_assets.install_main_image -> asset_markers.install ->
AutonomousProductEngine.build, with a sandbox that records the repository it receives. The stand-ins are:
- the attachment store: the customer's photo is in R2 and is not copied here, so the photo's digest in the prompt is
  swapped for the test bytes' digest, and that is the only change to the row;
- the generator and the repairer: fixed pages.
"""
from __future__ import annotations

import base64
import hashlib
import json
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import asset_markers as A
from omni_prod import discovery as d
from omni_prod import fact_canon as F
from omni_prod import uploaded_assets as U
from omni_prod import window_catalog as W
from omni_prod.repository_assets import file_bytes
from omni_prod.autonomous_core import AutonomousProductEngine, ExecutionReport
from omni_prod.build_contract import BuildContract
from omni_prod.product_architect import ProductArchitect
from omni_prod.skill_units import gate as G
from tests.test_window_catalog import AGE, COOKIES, _Arch, _Gen, _Rep, page

ROW = json.loads((Path(__file__).parent / 'fixtures' / 'doors_contract_bc_8ffe6070.json').read_text(encoding='utf-8'))
PROD_SHA = 'f1684ad30e8fbf976efc13145857740b50be2d3bd4cdea2722ef99656fd4126e'
ATTACHMENT = 'att_6d5b3e6de6274a44829dd038da5c4539'
PHOTO = b'\xff\xd8\xff' + b'doors' * 400
PHOTO_SHA = hashlib.sha256(PHOTO).hexdigest()
PHOTO_URI = 'data:image/jpeg;base64,' + base64.b64encode(PHOTO).decode('ascii')
PHOTO_FILE = 'assets/148ai-upload-1.jpg'          # warehouse 118: the page references the photo as this file
MARKER = '148ai-asset://upload/1'
ALT = 'דלתות'


def contract() -> BuildContract:
    return BuildContract.from_dict(ROW['contract'])


def hero(src: str, alt: str = ALT) -> str:
    return page(extra=f'<img id="hero-image" src="{src}" alt="{alt}" width="1080" height="720">')


class _Recording:
    """The sandbox: records every repository it is given and passes it."""

    def __init__(self):
        self.seen: list[dict] = []

    def execute(self, *, repository, spec):
        self.seen.append(dict(repository))
        return ExecutionReport(True, (), 'sandbox ok', tests_executed=1)


def worker_install(engine, prompt):
    """What the worker does before engine.build (worker_tasks._run_live_build_job): the photo, then the marker gate."""
    row = {'sha256': PHOTO_SHA, 'mime': 'image/jpeg', 'width': 1080, 'height': 720}
    with mock.patch.object(U, 'AttachmentRepository') as Repo:
        Repo.return_value.get.return_value = row
        Repo.return_value.read.return_value = PHOTO
        out = U.install_main_image(engine, prompt=prompt, pool=object(), store=object(),
                                   project_id=ROW['contract']['project_id'], account_id='a')
    A.install(engine)
    return out, Repo


def engine_for(first: str, repaired: str | None = None, sandbox=None, rounds: int = 1):
    return AutonomousProductEngine(architect=_Arch(), generator=_Gen(first), repairer=_Rep(repaired or first),
                                   executor=sandbox or _Recording(), max_repair_rounds=rounds)


class TheProductionContract(unittest.TestCase):
    def test_the_fixture_is_the_production_row_and_it_has_no_line_breaks(self):
        c = contract()
        self.assertTrue(c.verify_fingerprint())
        self.assertEqual(c.contract_fingerprint, ROW['contract_fingerprint'])
        self.assertEqual(hashlib.sha256(c.prompt.encode('utf-8')).hexdigest(), ROW['prompt_sha256'])
        self.assertNotIn('\n', c.prompt)                 # the premise: the worker reads one long line

    def test_the_photo_binding_is_read_from_the_contract(self):
        [m] = list(U._IMAGE_BINDING.finditer(contract().prompt))
        self.assertEqual((m[1], m[2], m[3], m[4], m[5], m[6], m[7]),
                         ('1', ATTACHMENT, PROD_SHA, MARKER, 'hero', 'product', ALT))

    def test_the_sandbox_gets_the_photo_bytes_never_the_raw_address(self):
        prompt = contract().prompt.replace(PROD_SHA, PHOTO_SHA)     # the only change to the production row
        self.assertEqual(prompt.count(PHOTO_SHA), 1)
        engine = engine_for(hero(MARKER))
        build_prompt, Repo = worker_install(engine, prompt)
        result = engine.build(build_prompt)
        sandbox = engine.executor
        while not isinstance(sandbox, _Recording):                  # the recording sandbox under the wrappers
            sandbox = vars(sandbox)['_inner']
        seen = sandbox.seen[0]['index.html']                        # what the browser gets, first
        self.assertNotIn('148ai-asset://', seen)
        self.assertIn(f'src="{PHOTO_FILE}"', seen)                  # warehouse 118: a file, not a data URI
        self.assertNotIn('data:image', seen)
        self.assertEqual(file_bytes(PHOTO_FILE, sandbox.seen[0][PHOTO_FILE]), PHOTO)   # the file holds the bytes
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        Repo.return_value.get.assert_called_once_with(project_id='prj_-K3B8ZLIJawPEA', account_id='a',
                                                      attachment_id=ATTACHMENT)
        self.assertIn(f'- image 1: src="{MARKER}"; place: hero; 1080x720 px; image/jpeg; alt="{ALT}"; file: {PHOTO_FILE}',
                      build_prompt)


class TheOwnersMutation(unittest.TestCase):
    """The owner (2026-11-16): a page with a raw 148ai-asset:// address fails; a page with a real URL passes."""

    def _run(self, repository):
        return A.AssetMarkerExecutor(_Recording()).execute(repository=repository, spec='s')

    def test_a_page_with_a_raw_asset_address_fails(self):
        report = self._run({'index.html': hero(MARKER)})
        self.assertFalse(report.passed)
        [f] = report.failures
        self.assertEqual(f.acceptance_id, A.ACCEPTANCE_ID)
        self.assertIn(f'{A.CODE}: index.html: src "{MARKER}"', f.message)
        self.assertEqual(report.tests_executed, 1)                  # the sandbox's own count is kept

    def test_a_page_with_a_real_url_passes(self):
        for src in ('https://cdn.example.com/doors.jpg', PHOTO_URI, '/static/doors.jpg'):
            with self.subTest(src=src[:40]):
                self.assertTrue(self._run({'index.html': hero(src)}).passed)

    def test_a_page_served_from_app_py_is_read_too_and_documentation_is_not(self):
        app = 'HTML = """' + hero(MARKER) + '"""\n'
        self.assertFalse(self._run({'app.py': app}).passed)
        self.assertFalse(self._run({'static/site.css': f'.hero{{background:url("{MARKER}")}}'}).passed)
        self.assertTrue(self._run({'README.md': f'The hero is {MARKER}.', 'index.html': hero(PHOTO_URI)}).passed)
        self.assertTrue(self._run({'index.html': hero(PHOTO_URI) + f'<!-- was {MARKER} -->'}).passed)

    def test_an_address_the_model_invented_fails_the_round_and_the_repair_removes_it(self):
        invented = '148ai-asset://upload/7'                         # the prompt never gave image 7
        engine = engine_for(hero(invented), hero('https://cdn.example.com/doors.jpg'), rounds=1)
        A.install(engine)
        result = engine.build('אתר לחנות דלתות פנים')
        first = engine.repairer.failures[0]
        self.assertEqual([f['acceptance_id'] for f in first], [A.ACCEPTANCE_ID])
        self.assertIn(f'index.html: src "{invented}"', first[0]['message'])
        self.assertIn('never replace a given one with an http URL', first[0]['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_the_gate_is_installed_once(self):
        engine = engine_for(hero(PHOTO_URI))
        a = A.install(engine)
        self.assertIs(A.install(engine), a)
        self.assertIs(engine.executor, a)


class NothingIsSkippedSilently(unittest.TestCase):
    def test_a_placed_address_without_a_binding_stops_the_build_before_generation(self):
        broken = contract().prompt.replace(f'role product: "{ALT}".', f'role product: {ALT}.')   # unreadable binding
        engine = engine_for(hero(MARKER))
        inner = engine.executor
        with self.assertRaisesRegex(ValueError, rf'{U.UNBOUND_CODE}: .*148ai-asset://upload/1 '):
            U.install_main_image(engine, prompt=broken, pool=object(), store=object(), project_id='p', account_id='a')
        self.assertIs(engine.executor, inner)

    def test_an_address_without_its_own_binding_is_named(self):
        prompt = contract().prompt.replace(PROD_SHA, PHOTO_SHA) + ' Also src="148ai-asset://upload/2" in the gallery.'
        with self.assertRaisesRegex(ValueError, r'148ai-asset://upload/2 but no binding'):
            worker_install(engine_for(hero(MARKER)), prompt)

    def test_a_request_without_a_photo_is_unchanged(self):
        engine = engine_for(hero(PHOTO_URI))
        prompt = 'אתר לחנות דלתות פנים, טלפון 050-3456723'
        self.assertEqual(U.install_main_image(engine, prompt=prompt, pool=None, store=None, project_id='p',
                                              account_id='a'), prompt)


def doors_brief():
    """A request like the production one, approved with its photo, two windows (one rejected) and no phone."""
    b = d.start('אתר לחנות דלתות פנים עם כפתור להתקשרות. מבצע: דלת לממ״ד ב-1390 ש״ח כולל התקנה.')
    b.assets['image'] = {'id': ATTACHMENT, 'sha256': PHOTO_SHA, 'mime': 'image/jpeg', 'size_bytes': len(PHOTO),
                         'width': 1080, 'height': 720}
    for a in ({'image_kind': 'product'}, {'image_who_product': ALT}, {'image_use': 'as_is'},
              {'image_place_product': 'hero'}):
        b = d.answer(b, a)
    d.decide_windows(b, {'age_gate': True, 'cookie_banner': True, 'entry_popup': False})
    return b


class TheSameReadersOnBothForms(unittest.TestCase):
    """What the customer approved and what the worker reads from the contract must give the same answers -- for a
    contract compiled today (it keeps the approved lines) and for one stored before 2026-11-16 (one long line, like
    the production row bc_8ffe6070), which can still be built."""

    @classmethod
    def setUpClass(cls):
        b = doors_brief()
        cls.approved = b.prompt + '\n' + d.requirements_text(b)
        cls.contract = ProductArchitect().compile(cls.approved, project_id='p', contract_version=1).prompt
        cls.one_line = ' '.join(cls.approved.split())                 # how contracts were stored until 2026-11-16
        cls.forms = {'approved': cls.approved, 'contract': cls.contract, 'one line (old contracts)': cls.one_line}

    def test_the_contract_keeps_the_approved_lines(self):
        self.assertIn('\n', self.approved)
        self.assertEqual(self.contract.splitlines(), [' '.join(x.split()) for x in self.approved.splitlines() if x.strip()])
        self.assertEqual(' '.join(self.contract.split()), self.one_line)        # the same words, nothing added or lost
        self.assertNotIn('\n', self.one_line)
        self.assertNotIn('\n', contract().prompt)                               # the production row: the old form

    def test_the_rest_of_the_contract_still_reads_the_one_line_text(self):
        c = ProductArchitect().compile(self.approved, project_id='p', contract_version=1)
        self.assertTrue(c.verify_fingerprint())
        self.assertNotIn('\n', c.product_spec.title + c.product_spec.summary)   # detection and the spec read `clean`
        self.assertEqual(ProductArchitect().compile(self.one_line, project_id='p', contract_version=1).prompt,
                         self.one_line)                                # a one-line request is stored as it always was

    def test_the_photo_binding(self):
        read = {name: [m.groups() for m in U._IMAGE_BINDING.finditer(p)] for name, p in self.forms.items()}
        self.assertEqual(read['approved'], read['contract'])
        self.assertEqual(read['approved'], read['one line (old contracts)'])
        self.assertEqual([g[0] for g in read['contract']], ['1'])

    def test_the_approved_and_rejected_windows_and_the_canon(self):
        for name, p in self.forms.items():
            with self.subTest(form=name):
                self.assertEqual(W.approved_in_prompt(p), ['age_gate', 'cookie_banner'])
                self.assertEqual(W.rejected_in_prompt(p), ['entry_popup'])
                self.assertEqual(F.build_canon(p).values('window'), {'age_gate', 'cookie_banner'})

    def test_the_missing_phone_stops_the_repairs_on_every_form(self):
        invented = [F._INVENTED['phone'] + '972501234567']
        for name, p in self.forms.items():
            with self.subTest(form=name):
                self.assertEqual(F.needs_customer_input(invented, p), ['phone'])

    def test_the_window_gate_holds_a_contract_build(self):
        for name in ('contract', 'one line (old contracts)'):
            with self.subTest(form=name):
                prompt = self.forms[name]
                engine = engine_for(page(COOKIES), page(COOKIES))
                self.assertEqual(W.install(engine, prompt=prompt), ['age_gate', 'cookie_banner'])
                result = engine.build(prompt)
                self.assertEqual(result.status, 'failed')
                self.assertIn('WINDOW_MISSING', engine.repairer.failures[0][0]['message'])
                passing = engine_for(page(AGE, COOKIES))
                W.install(passing, prompt=prompt)
                self.assertEqual(passing.build(prompt).status, 'ready')


REVIEWS = ('בית קפה "הפינה" ברחוב הרצל 10, חיפה. טלפון 04-8123456. ביקורות של לקוחות:\n'
           '"הקפה הכי טוב בחיפה, באמת" – דנה\n"שירות מעולה ומהיר מאוד" – יוסי כהן\n'
           'תמונה ראשית: כוס קפה על שולחן עץ ליד חלון\nתודה רבה')


class WhatOnlyTheLinesCarry(unittest.TestCase):
    """Two readers cannot recover a line that was joined to the next one. They read the contract correctly only
    because the contract keeps the approved lines."""

    @classmethod
    def setUpClass(cls):
        b = d.start(REVIEWS)
        cls.approved = b.prompt + '\n' + d.requirements_text(b)
        cls.contract = ProductArchitect().compile(cls.approved, project_id='p', contract_version=1).prompt

    def test_a_review_at_the_end_of_its_line_keeps_its_author(self):
        want = {'הקפה הכי טוב בחיפה באמת|דנה', 'שירות מעולה ומהיר מאוד|יוסי כהנ'}
        self.assertEqual(F.build_canon(self.approved).values('review'), want)
        self.assertEqual(F.build_canon(self.contract).values('review'), want)
        # the old one-line form reads the second author together with the next line's words: the reason for the change
        self.assertNotEqual(F.build_canon(' '.join(self.approved.split())).values('review'), want)

    def test_an_image_description_ends_with_its_line(self):
        from omni_prod import generated_images as G
        want = 'כוס קפה על שולחן עץ ליד חלון'
        self.assertEqual(G.describe(self.approved, 'hero image'), want)
        self.assertEqual(G.describe(self.contract, 'hero image'), want)
        self.assertNotEqual(G.describe(' '.join(self.approved.split()), 'hero image'), want)


class TheEvidenceKeepsTheGates(unittest.TestCase):
    def test_the_gate_report_walks_through_the_photo_check_and_the_marker_gate(self):
        engine = engine_for(hero(MARKER))
        with mock.patch.dict('os.environ', {'OMNI_GATE_G6': 'block'}):
            G.install(engine, 'G6')                                  # inside, as the worker installs it
        worker_install(engine, contract().prompt.replace(PROD_SHA, PHOTO_SHA))
        self.assertIsInstance(engine.executor, A.AssetMarkerExecutor)     # the outermost wrapper is not a gate
        engine.build('x')
        self.assertEqual(G.report(engine)['G6']['status'], 'pass')


if __name__ == '__main__':
    unittest.main()

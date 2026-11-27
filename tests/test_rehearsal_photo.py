"""The golden rehearsal can carry a customer's photo, run as a non-founder account and report the build's time budget
(warehouse 117, 71, 115 and 118; the owner's order of 2026-11-27).

Everything after the fixture's own row and bytes is the customer's real path: the discovery questions of the image's
role, `ProductArchitect.compile`, `AttachmentRepository.get` and `read` (with the checksum), `install_main_image`, the
real transform and gate, `BuildControl`, `failure_code` and `ready`. The rehearsal's engine and the model are the only
doubles, as in the other rehearsal tests."""
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omni_prod import rehearsal as R
from omni_prod import rehearsal_photo as P
from omni_prod.product_architect import ProductArchitect

ROOT = Path(__file__).resolve().parent.parent
CAFE = ('אתר לבית קפה שכונתי בתל אביב בשם קפה נחמה: תפריט עם מחירים, הסיפור שלנו, שעות פתיחה 07:00-19:00, '
        'טלפון 03-5551234, כתובת אבן גבירול 100 תל אביב')
ANSWERS = {'content_only': 'yes', 'personal_data': 'no', 'login': 'none'}
PAGE = ('<html><body><header><h1>קפה נחמה</h1></header><section class="hero"><img src="148ai-asset://upload/1" '
        'alt="חזית העסק"><h2>ברוכים הבאים</h2></section></body></html>')


class _Inner:
    def execute(self, *, repository, spec):
        raise AssertionError('not reached')


def with_options(**kw):
    token = R._OPTIONS.set(R.Options(**kw))
    return token


class _Base(unittest.TestCase):
    def setUp(self):
        self.photo = P.load('customer_photo')
        self.addCleanup(R._OPTIONS.reset, R._OPTIONS.set(R.Options(photo=self.photo)))

    def installed(self, account='rehearsal-account'):
        """The engine of a rehearsal after the photo is installed by the real install_main_image."""
        from omni_prod.uploaded_assets import install_main_image
        prompt = R.approved_prompt(CAFE, ANSWERS)
        engine = SimpleNamespace(executor=_Inner(), architect=None)
        prompt = install_main_image(engine, prompt=prompt, pool=P.FixturePool(self.photo, account),
                                    store=P.FixtureStore(self.photo), project_id=P.PROJECT_ID, account_id=account)
        return engine, prompt


class ThePhotoIsInTheApprovedRequest(_Base):
    def test_the_brief_places_the_fixture_photo_in_the_hero_with_the_customers_words(self):
        prompt = R.approved_prompt(CAFE, ANSWERS)
        line = [l for l in prompt.splitlines() if l.startswith('Uploaded image 1 attachment:')]
        self.assertEqual(len(line), 1)
        self.assertIn(f'attachment: {self.photo.attachment_id}; sha256={self.photo.sha256}', line[0])
        self.assertIn('placement: hero', line[0])
        self.assertIn('"חזית העסק"', line[0])

    def test_without_the_option_the_approved_request_is_unchanged(self):
        R._OPTIONS.set(R.Options())
        self.assertNotIn('Uploaded image', R.approved_prompt(CAFE, ANSWERS))

    def test_the_contract_the_worker_builds_from_keeps_the_binding(self):
        contract = ProductArchitect().compile(R.approved_prompt(CAFE, ANSWERS), project_id='t', contract_version=1)
        self.assertIn('Uploaded image 1 attachment:', contract.to_dict().get('prompt', json.dumps(contract.to_dict())))

    def test_a_customer_question_is_still_never_guessed(self):
        with self.assertRaises(ValueError):
            R.approved_prompt(CAFE, {})


class TheRealInstallCarriesThePhotoAsAFile(_Base):
    def test_the_page_names_a_file_and_the_report_says_file_and_hero_kept(self):
        engine, _ = self.installed()
        repo = engine.repository_transform({'index.html': PAGE})
        photo = P.photo_report(repo, engine.uploaded_images)
        self.assertTrue(photo['as_file'], photo)
        self.assertTrue(photo['hero_kept'], photo)
        self.assertTrue(photo['ok'])
        row = photo['images'][0]
        self.assertTrue(row['path'].startswith('assets/148ai-upload-1.'))
        self.assertIn(row['path'], repo)
        self.assertNotIn('data:image', repo['index.html'])
        self.assertEqual(photo['inline_data_uri_in'], [])

    def test_the_attachment_store_checks_the_bytes_like_the_real_one(self):
        from omni_prod.attachments import AttachmentError
        bad = P.Fixture(**{**self.photo.__dict__, 'data': self.photo.data + b'x'})
        with self.assertRaises(AttachmentError):
            from omni_prod.attachments import AttachmentRepository
            repo = AttachmentRepository(P.FixturePool(bad, 'a'), P.FixtureStore(bad))
            repo.read(repo.get(project_id=P.PROJECT_ID, account_id='a', attachment_id=bad.attachment_id))

    def test_another_account_does_not_see_the_fixture_row(self):
        from omni_prod.attachments import AttachmentRepository
        repo = AttachmentRepository(P.FixturePool(self.photo, 'a'), P.FixtureStore(self.photo))
        with self.assertRaises(KeyError):
            repo.get(project_id=P.PROJECT_ID, account_id='b', attachment_id=self.photo.attachment_id)


class TheReportSaysNoWhenThePhotoIsNotThere(_Base):
    def setUp(self):
        super().setUp()
        self.engine, _ = self.installed()
        self.good = self.engine.repository_transform({'index.html': PAGE})

    def test_base64_in_the_page_is_not_a_file(self):
        bad = dict(self.good)          # the file and its reference stay: the page carries the picture a second time inline
        bad['index.html'] = bad['index.html'].replace('</body>', '<img src="data:image/webp;base64,AAAA" alt="x"></body>')
        photo = P.photo_report(bad, self.engine.uploaded_images)
        self.assertFalse(photo['as_file'])
        self.assertEqual(photo['inline_data_uri_in'], ['index.html'])
        self.assertFalse(photo['ok'])

    def test_a_dropped_hero_is_not_kept(self):
        bad = dict(self.good)
        bad['index.html'] = '<html><body><h1>קפה נחמה</h1></body></html>'
        photo = P.photo_report(bad, self.engine.uploaded_images)
        self.assertFalse(photo['hero_kept'])
        self.assertEqual(photo['images'][0]['placement'], 'missing')
        self.assertFalse(photo['ok'])

    def test_a_missing_file_is_not_carried(self):
        path = self.engine.uploaded_images[0].uri
        bad = {k: v for k, v in self.good.items() if k != path}
        photo = P.photo_report(bad, self.engine.uploaded_images)
        self.assertFalse(photo['images'][0]['file_carried'])
        self.assertFalse(photo['as_file'])
        self.assertIn('no file at', photo['images'][0]['reason'])

    def test_the_file_as_text_is_not_the_image(self):
        path = self.engine.uploaded_images[0].uri
        photo = P.photo_report({**self.good, path: 'not an image'}, self.engine.uploaded_images)
        self.assertFalse(photo['images'][0]['file_carried'])
        self.assertFalse(photo['as_file'])
        self.assertFalse(photo['ok'])

    def test_a_marker_left_in_the_page_is_not_a_file(self):
        photo = P.photo_report({**self.good, 'extra.html': '<img src="148ai-asset://upload/1" alt="x">'},
                               self.engine.uploaded_images)
        self.assertTrue(photo['images'][0]['marker_left'])
        self.assertFalse(photo['as_file'])

    def test_an_svg_icon_inline_is_not_a_photo(self):
        photo = P.photo_report({**self.good, 'i.html': '<img src="data:image/svg+xml;utf8,<svg/>" alt="i">'},
                               self.engine.uploaded_images)
        self.assertTrue(photo['as_file'])


def run_with_engine(build, *, prompt=CAFE):
    engine = SimpleNamespace(executor=_Inner(), architect=None, build=build)
    with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
        return engine, R.run(prompt)


class TheRehearsalRunReportsIt(_Base):
    def test_a_build_that_keeps_the_photo_reports_file_and_hero(self):
        seen = {}

        def build(given):
            seen['prompt'] = given
            repo = engine.repository_transform({'index.html': PAGE})
            return SimpleNamespace(status='ready', repository=repo, spec=SimpleNamespace(acceptance=[]), repair_rounds=0,
                                   report=SimpleNamespace(failures=[], passed=True), stop_reason=None)
        prompt = R.approved_prompt(CAFE, ANSWERS)
        engine = SimpleNamespace(executor=_Inner(), architect=None, build=build)
        with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
            report = R.run(prompt)
        self.assertEqual(report['photo_installed']['placed'], 1)
        self.assertIn('Uploaded images (verified by 148AI)', seen['prompt'])
        self.assertTrue(report['photo']['as_file'], report.get('photo'))
        self.assertTrue(report['photo']['hero_kept'])
        notes = R.annotations(report)
        self.assertTrue(any('title=customer photo' in n and 'photo_as_file=True' in n and 'hero_kept=True' in n
                            for n in notes), notes)
        self.assertTrue(R.extras_ok(report))

    def test_a_build_that_drops_the_hero_fails_the_rehearsal_even_if_everything_else_is_ready(self):
        prompt = R.approved_prompt(CAFE, ANSWERS)

        def build(given):
            return SimpleNamespace(status='ready', repository={'index.html': '<html><body>x</body></html>'},
                                   spec=SimpleNamespace(acceptance=[]), repair_rounds=0,
                                   report=SimpleNamespace(failures=[], passed=True), stop_reason=None)
        engine = SimpleNamespace(executor=_Inner(), architect=None, build=build)
        with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
            report = R.run(prompt)
        self.assertFalse(report['photo']['hero_kept'])
        self.assertFalse(R.extras_ok(report))
        report.update(outcome='ready', quality={'passed': True}, release_policy={'decision': 'READY'})
        self.assertFalse(R.ready(report))
        self.assertTrue(any(n.startswith('::error title=customer photo::') for n in R.annotations(report)))

    def test_a_request_with_no_photo_in_it_does_not_build(self):
        built = []
        engine = SimpleNamespace(executor=_Inner(), architect=None, build=lambda p: built.append(p))
        with mock.patch('omni_prod.investor_app._live_components', return_value=(engine, SimpleNamespace())):
            report = R.run(CAFE)                       # a raw request: no binding line, so no photo can be placed
        self.assertEqual(built, [])
        self.assertIn('photo_install_error', report)
        self.assertFalse(R.extras_ok(report))

    def test_without_the_option_nothing_of_it_is_in_the_report(self):
        R._OPTIONS.set(R.Options())
        engine, report = run_with_engine(mock.Mock(side_effect=RuntimeError('stop')))
        for key in ('photo', 'photo_installed', 'account'):
            self.assertNotIn(key, report)
        self.assertTrue(R.extras_ok(report))


class TheNonFounderAccount(unittest.TestCase):
    def test_the_account_is_not_in_the_founder_list(self):
        self.assertEqual(P.check_account('non_founder'), P.NON_FOUNDER_ID)
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': f'usr_x,{P.NON_FOUNDER_ID}'}):
            with self.assertRaises(ValueError) as ctx:
                P.check_account('non_founder')
        self.assertIn('would not be a non-founder run', str(ctx.exception))

    def test_an_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            P.check_account('founder')

    def test_the_workers_own_decisions_are_read_for_that_account(self):
        token = R._OPTIONS.set(R.Options(account_id=P.NON_FOUNDER_ID))
        self.addCleanup(R._OPTIONS.reset, token)
        with mock.patch.dict(os.environ, {'OMNI_AGENTIC_REPAIR': 'founder', 'OMNI_DESIGN_REVIEW': 'founder',
                                          'OMNI_IMAGE_MATCH': 'founder'}):
            engine, report = run_with_engine(mock.Mock(side_effect=RuntimeError('stop')))
        self.assertEqual(report['account']['mode'], 'non_founder')
        self.assertIs(report['account']['founder'], False)
        self.assertIs(report['account']['agentic_repair'], False)
        self.assertIs(report['account']['design_critic'], False)
        self.assertIs(report['account']['image_match'], False)
        self.assertIn('plan limits', report['account']['not_covered'])
        # the same decisions for the founder, to show the account is what changes them
        with mock.patch.dict(os.environ, {'OMNI_IMAGE_MATCH': 'founder'}):
            from omni_prod.image_match import enabled_for
            from omni_prod.pricing import _FOUNDER_DEFAULT
            self.assertTrue(enabled_for({'user_id': _FOUNDER_DEFAULT}))

    def test_a_non_founder_run_that_turns_out_founder_fails(self):
        report = {'account': {'founder': True}}
        self.assertFalse(R.extras_ok(report))


class TheTimeBudget(unittest.TestCase):
    def setUp(self):
        self.addCleanup(R._OPTIONS.reset, R._OPTIONS.set(R.Options()))      # the defaults, whatever ran before

    def test_parse(self):
        self.assertIsNone(R.parse_time_budget(''))
        self.assertEqual(R.parse_time_budget('120, 600'), (120, 600))
        for bad in ('120', '120,abc', '0,10', '600,120', '120,5000', '900,1000', '1,2,3', '-1,10'):
            with self.assertRaises(ValueError, msg=bad):
                R.parse_time_budget(bad)

    def test_the_rehearsal_has_the_workers_budget_and_reports_a_build_that_stays_inside_it(self):
        from omni_prod import queueing
        engine, report = run_with_engine(mock.Mock(side_effect=RuntimeError('stop')))
        tb = report['time_budget']
        self.assertEqual((tb['repair_until_seconds'], tb['stop_at_seconds'], tb['job_timeout_seconds']),
                         (queueing.BUILD_REPAIR_UNTIL_SECONDS, queueing.BUILD_STOP_AT_SECONDS,
                          queueing.BUILD_JOB_TIMEOUT_SECONDS))
        self.assertFalse(tb['shortened'])
        self.assertEqual(tb['ended_by'], 'within_budget')
        self.assertFalse(tb['queue_limit_reached'])
        self.assertEqual(engine.out_of_time.__self__.stop_at_seconds, queueing.BUILD_STOP_AT_SECONDS)

    def _late_control(self, now):
        """The real BuildControl, with the clock this test sets (its default clock is bound at import)."""
        from omni_prod.build_control import BuildControl

        class Late(BuildControl):
            def __init__(self, jobs, build_id, **kw):
                self.t = 0
                super().__init__(jobs, build_id, clock=lambda: self.t, **kw)
                self.t = now
        return mock.patch('omni_prod.build_control.BuildControl', Late)

    def test_a_build_that_passes_its_stop_time_ends_itself_and_is_named_build_timeout(self):
        token = R._OPTIONS.set(R.Options(time_budget=(1, 2)))
        self.addCleanup(R._OPTIONS.reset, token)
        engine = SimpleNamespace(executor=_Inner(), architect=None,
                                 build=lambda prompt: engine.executor.execute(repository={}, spec=None))
        with self._late_control(5), mock.patch('omni_prod.investor_app._live_components',
                                               return_value=(engine, SimpleNamespace())):
            report = R.run(CAFE)
        self.assertEqual(report['error_code'], 'build_timeout')
        self.assertEqual(report['time_budget']['ended_by'], 'build_deadline')
        self.assertTrue(report['time_budget']['shortened'])
        self.assertEqual(report['time_budget']['stop_at_seconds'], 2)
        self.assertEqual(report['time_budget']['checks'], 0)

    def test_a_repair_loop_that_is_out_of_time_is_named(self):
        engine = SimpleNamespace(executor=_Inner(), architect=None)
        engine.build = lambda p: SimpleNamespace(status='failed', repository={}, spec=SimpleNamespace(acceptance=[]),
                                                 repair_rounds=2, report=SimpleNamespace(failures=[], passed=False),
                                                 stop_reason='time_budget')
        with self._late_control(1), mock.patch('omni_prod.investor_app._live_components',
                                               return_value=(engine, SimpleNamespace())):
            report = R.run(CAFE)
        self.assertEqual(report['time_budget']['ended_by'], 'repair_cut_off_by_time')

    def test_the_queues_own_limit_ending_a_build_fails_the_rehearsal(self):
        report = {'time_budget': {'queue_limit_reached': True}}
        self.assertFalse(R.extras_ok(report))


class MainReadsTheOptions(unittest.TestCase):
    def run_main(self, argv):
        seen = {}

        def fake_run(prompt):
            seen['options'] = R.options()
            seen['prompt'] = prompt
            return {'outcome': 'exception', 'build_id': 'x'}
        out = io.StringIO()
        before = R._OPTIONS.get()
        try:
            with mock.patch.object(R, 'run', fake_run), redirect_stdout(out):
                rc = R.main(argv)
        finally:
            # main() sets the options for the rest of its process and never resets them (it is the process's last
            # call); a test must not leave them to the next test (unittest runs MainReadsTheOptions before TheTimeBudget)
            R._OPTIONS.set(before)
        return rc, seen

    def test_the_defaults_are_the_old_behaviour(self):
        rc, seen = self.run_main([CAFE])
        self.assertEqual(seen['options'], R.Options())
        self.assertEqual(seen['prompt'], CAFE)

    def test_all_three_are_read(self):
        rc, seen = self.run_main([CAFE, json.dumps(ANSWERS), 'customer_photo', 'non_founder', '120,600'])
        opts = seen['options']
        self.assertEqual(opts.photo.name, 'customer_photo')
        self.assertEqual(opts.account_id, P.NON_FOUNDER_ID)
        self.assertEqual(opts.time_budget, (120, 600))
        self.assertIn('Uploaded image 1 attachment:', seen['prompt'])
        self.assertTrue(seen['prompt'].startswith(CAFE))

    def test_empty_extras_from_the_workflow_mean_off(self):
        rc, seen = self.run_main([CAFE, json.dumps(ANSWERS), '', '', ''])
        self.assertEqual(seen['options'], R.Options())

    def test_the_workflows_variables_are_read_when_no_argument_says_otherwise(self):
        env = {'REHEARSAL_IMAGE': 'customer_photo', 'REHEARSAL_ACCOUNT': 'non_founder', 'REHEARSAL_TIME_BUDGET': '60,300'}
        with mock.patch.dict(os.environ, env):
            rc, seen = self.run_main([CAFE, json.dumps(ANSWERS)])
        self.assertEqual((seen['options'].photo.name, seen['options'].account_id, seen['options'].time_budget),
                         ('customer_photo', P.NON_FOUNDER_ID, (60, 300)))

    def test_an_unknown_value_stops_before_any_run(self):
        for argv in ([CAFE, '{}', 'nope'], [CAFE, '{}', '', 'founder'], [CAFE, '{}', '', '', 'x']):
            with self.assertRaises(ValueError, msg=argv):
                self.run_main(argv)

    def test_an_image_without_the_brief_is_refused(self):
        for argv in ([CAFE, '', 'customer_photo'], [CAFE, '  ', 'customer_photo']):
            with self.assertRaises(ValueError) as ctx:
                self.run_main(argv)
            self.assertIn('approved brief', str(ctx.exception))


class TheWorkflowPassesThemOn(unittest.TestCase):
    def test_inputs_and_the_command(self):
        text = (ROOT / '.github' / 'workflows' / 'golden-rehearsal.yml').read_text(encoding='utf-8')
        for name in ('image:', 'account:', 'time_budget:'):
            self.assertIn('      ' + name, text)
        for env in ('IMAGE: ${{ inputs.image }}', 'ACCOUNT: ${{ inputs.account }}', 'TIME_BUDGET: ${{ inputs.time_budget }}'):
            self.assertIn(env, text)
        for var in ('REHEARSAL_IMAGE=${IMAGE:-}', 'REHEARSAL_ACCOUNT=${ACCOUNT:-}',
                    'REHEARSAL_TIME_BUDGET=${TIME_BUDGET:-}'):
            self.assertIn(var, text)

    def test_an_image_with_empty_answers_gets_an_empty_brief_not_a_raw_request(self):
        text = (ROOT / '.github' / 'workflows' / 'golden-rehearsal.yml').read_text(encoding='utf-8')
        self.assertIn('if [ -n "${IMAGE:-}" ] && [ -z "${ANSWERS:-}" ]; then ANSWERS="{}"; fi', text)

    def test_the_fixture_is_committed_and_is_a_real_image(self):
        from omni_prod.attachments import validate_image
        data = (ROOT / 'tests' / 'fixtures' / 'rehearsal' / 'customer_photo.jpg').read_bytes()
        self.assertEqual(validate_image(data)[0], 'image/jpeg')


if __name__ == '__main__':
    unittest.main()

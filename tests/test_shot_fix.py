"""Warehouse 124 (the owner, 2026-11-21; released 2026-11-27): the customer takes a screenshot of the build and the model fixes
the exact component. What can be proved without a database and without a paid call, on the real functions:

  * the image is brought down to 1,400 px on its long side before any model reads it, and both copies are stored (rules 4, 5);
  * the window width and the build id travel with the image to the model (rule 2);
  * the answer is exact edit blocks on files of THIS build, applied once each, all or none; a rebuild is refused, and the files
    nobody touched are byte-identical (rule 1; acceptance 3);
  * every round writes five evidence lines -- receipt, reduction, model call, edit, result -- in every outcome (acceptance 5, 6);
  * the customer is told in Hebrew, Arabic or English, with the next action, and with no platform word;
  * the stored fix becomes a modification candidate by the SAME gates as any change (modification_engine, exact edits).

The turn counter and the model's own path (reservation, worker, images) are on real PostgreSQL: tests/test_shot_fix_pg.py.
The card and the upload, in real Chromium: tests/shot_fix_browser.cjs."""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import attachments as A
from omni_prod import customer_words as CW
from omni_prod import shot_fix as SF
from omni_prod.conversation.store import MemoryConversationStore
from tests.shot_fix_support import CSS, FIX_ANSWER, WORK, MemoryAttachments, Reader, jpeg, png
from tests.test_plain_words_failure_and_approval import offences

ROOT = Path(__file__).resolve().parents[1]
HEBREW, ARABIC, LATIN = (re.compile(p) for p in ('[֐-׿]', '[؀-ۿ]', '[A-Za-z]'))

BIG = png(3000, 1800)                                              # made once: 12 rounds read it


def run_round(reader, *, data=None, width=390, lang='he', note='', work=None, store=None, attachments=None):
    store = store or MemoryConversationStore()
    attachments = attachments or MemoryAttachments()
    record = SF.round_of(project_id='prj_1', account_id='usr_1', build_id='bld_abc123', version_id='ver_1',
                         work=dict(WORK if work is None else work), data=data or BIG, width=width, note=note,
                         lang=lang, repo=attachments, reader=reader, store=store, request_key='k1')
    return record, store, attachments


class TheImageIsReducedBeforeTheModelReadsIt(unittest.TestCase):
    def test_a_large_screenshot_has_its_long_side_at_1400_and_keeps_its_shape(self):
        data = png(3000, 1800)
        s = SF.shrink(data)
        self.assertTrue(s.scaled)
        self.assertEqual((s.width, s.height), (1400, 840))
        self.assertEqual((s.original_width, s.original_height), (3000, 1800))
        self.assertEqual(A.validate_image(s.data), ('image/png', 1400, 840))
        self.assertEqual(s.original_sha256, hashlib.sha256(data).hexdigest())
        self.assertNotEqual(s.sha256, s.original_sha256)

    def test_a_tall_phone_screenshot_is_reduced_on_its_height(self):
        s = SF.shrink(jpeg(1170, 2532))
        self.assertEqual(max(s.width, s.height), 1400)
        self.assertEqual(s.mime, 'image/jpeg')
        self.assertAlmostEqual(s.width / s.height, 1170 / 2532, places=2)

    def test_an_image_already_within_the_bound_is_the_original_and_is_not_enlarged(self):
        data = png(800, 600)
        s = SF.shrink(data)
        self.assertFalse(s.scaled)
        self.assertEqual(s.data, data)
        self.assertEqual(SF.shrink(png(1400, 700)).data, png(1400, 700))

    def test_what_is_not_a_readable_image_is_refused_by_its_bytes(self):
        for bad in (b'', b'GIF89a....', b'<svg xmlns="http://www.w3.org/2000/svg"/>', b'not an image'):
            with self.subTest(bad=bad[:12]), self.assertRaises(A.AttachmentError):
                SF.shrink(bad)

    def test_the_window_width_is_a_whole_number_of_pixels_in_range(self):
        self.assertEqual(SF.check_width(390), 390)
        for bad in (0, 239, 3841, -1, 390.5, '390', None, True):
            with self.subTest(bad=bad), self.assertRaises(SF.ShotError):
                SF.check_width(bad)


class TheAnswerIsExactEdits(unittest.TestCase):
    def fix(self, answer, work=None):
        return SF.answer_edits(answer, dict(WORK if work is None else work), build_id='bld_abc123', version_id='ver_1')

    def refused(self, answer, code, work=None):
        with self.assertRaises(SF.ShotReadFailed) as ctx:
            self.fix(answer, work)
        self.assertEqual(ctx.exception.code, code, ctx.exception.detail)

    def test_an_exact_block_changes_that_component_and_nothing_else(self):
        fix = self.fix(FIX_ANSWER)
        self.assertEqual(fix.paths, ['style.css'])
        self.assertIn('.cta{position:absolute;bottom:8px;right:24px;', fix.new_work['style.css'])
        self.assertNotIn('bottom:-40px', fix.new_work['style.css'])
        for path in WORK:                                              # the files nobody touched are byte-identical
            if path != 'style.css':
                self.assertIs(fix.new_work[path], WORK[path], path)
        self.assertEqual(set(fix.new_work), set(WORK))                 # no file appeared, none was dropped
        self.assertEqual(len(fix.fingerprint), 64)
        self.assertEqual(fix.finding['what'], 'הכפתור יורד מתחת לקצה המסך בטלפון')

    def test_the_diff_is_only_the_lines_of_the_block(self):
        fix = self.fix(FIX_ANSWER)
        before, after = WORK['style.css'].splitlines(), fix.new_work['style.css'].splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual([i for i, (a, b) in enumerate(zip(before, after)) if a != b], [4])

    def test_an_answer_that_brings_whole_files_is_a_rebuild_and_is_refused(self):
        for key in ('files', 'repository', 'page', 'html'):
            with self.subTest(key=key):
                self.refused({**FIX_ANSWER, key: {'index.html': '<html>a brand new page</html>'}}, 'rebuild_refused')

    def test_an_edit_that_replaces_most_of_a_file_is_a_rebuild_in_disguise(self):
        css = CSS[:1200]                                               # a file of 1,200 characters; a block of 800 is two thirds of it
        work = {**WORK, 'style.css': css}
        self.refused({'edits': [{'path': 'style.css', 'old': css[:800], 'new': 'body{}'}]}, 'rebuild_refused', work)
        self.fix({'edits': [{'path': 'style.css', 'old': css[:400], 'new': css[:400].replace('#fff', '#eee')}]}, work)   # a third is fine
        self.refused({'edits': [{'path': 'style.css', 'old': CSS[:1600], 'new': 'x'}]}, 'rebuild_refused')    # a block is one component

    def test_more_than_six_blocks_is_not_one_component(self):
        edits = [{'path': 'style.css', 'old': f'.pad{i}{{margin:{i}px;', 'new': f'.pad{i}{{margin:0;'} for i in range(7)]
        self.refused({'edits': edits}, 'rebuild_refused')

    def test_a_block_that_does_not_apply_exactly_once_applies_nothing(self):
        self.refused({'edits': [FIX_ANSWER['edits'][0], {'path': 'style.css', 'old': 'no such text', 'new': 'x'}]}, 'edit_not_applicable')
        self.refused({'edits': [{'path': 'style.css', 'old': 'margin:', 'new': 'padding:'}]}, 'edit_not_applicable')      # many times
        self.refused({'edits': [{'path': 'new-page.html', 'old': 'a', 'new': 'b'}]}, 'edit_not_applicable')              # a new file
        self.refused({'edits': [{'path': '../etc/passwd', 'old': 'a', 'new': 'b'}]}, 'edit_not_applicable')              # unsafe path

    def test_nothing_to_change_or_no_blocks_or_a_wrong_shape_is_refused_in_words(self):
        self.refused({'edits': []}, 'no_edit')
        self.refused({'finding': {}}, 'no_edit')
        self.refused({'edits': [{'path': 'style.css', 'old': 'body{', 'new': 'body{'}]}, 'no_edit')
        self.refused({'edits': [{'path': 'style.css', 'old': 1, 'new': 2}]}, 'invalid_answer')
        self.refused('a sentence', 'invalid_answer')
        self.refused(['edits'], 'invalid_answer')

    def test_a_model_that_cannot_tell_says_so_and_changes_nothing(self):
        self.refused({'cannot_tell': 'איזה כפתור?'}, 'cannot_tell')

    def test_only_the_files_shown_to_the_model_can_be_edited(self):
        shown = SF.source_files(WORK)
        self.assertEqual(sorted(shown), ['app.js', 'index.html', 'style.css'])      # no README, no binary
        big = {'index.html': 'x' * 30_000, 'style.css': 'y' * 30_000, 'app.js': 'z' * 100}
        self.assertEqual(sorted(SF.source_files(big)), ['app.js', 'index.html'])    # a file that does not fit is not shown


class TheFollowupCarriesTheExactEdits(unittest.TestCase):
    def test_the_followup_names_the_edits_and_reads_back_exactly(self):
        record, _, _ = run_round(Reader(FIX_ANSWER))
        followup = SF.followup_for(record)
        self.assertTrue(followup.startswith(SF.MARK))
        self.assertEqual(SF.edits_of(followup), FIX_ANSWER['edits'])
        self.assertIsNone(SF.edits_of('make the button green'))
        with self.assertRaises(ValueError):
            SF.edits_of(SF.MARK + '[]')
        with self.assertRaises(ValueError):
            SF.edits_of(SF.MARK + 'not json')

    def test_the_engine_applies_exactly_those_edits_through_its_own_gates(self):
        from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
        from omni_prod.modification_engine import CandidateModificationEngine
        from omni_prod.product_spec import ProductSpec
        from tests.test_m4_modification_engine import SPEC

        class Executor:
            calls = []

            def execute(self, *, repository, spec):
                self.calls.append(repository)
                return ExecutionReport(True)

        class Boom:
            def __getattr__(self, name):
                def refuse(*a, **k):
                    raise AssertionError(f'no model is asked on the exact path: {name}')
                return refuse

        class Gate:
            passed, score, minimum_score, blockers = True, 99, 80, ()

            def to_dict(self):
                return {'passed': True}

        class Rights:
            def assess(self, *_, **__):
                return mock.Mock(publish_allowed=True, status='CLEAR', to_dict=lambda: {})

        record, _, _ = run_round(Reader(FIX_ANSWER))
        engine = CandidateModificationEngine(classifier=Boom(), repairer=Boom(), executor=Executor(), evolver=Boom(),
                                             quality_fn=lambda **k: Gate(), security_fn=lambda repo: Gate(), rights_engine=Rights())
        spec = ProductSpec.from_dict(SPEC)
        out = engine.propose(spec=spec, repository=dict(WORK), followup=SF.followup_for(record))
        self.assertEqual(out.status, 'ready_for_review')
        self.assertEqual(out.repair_rounds, 0)
        changed = sorted(p for p in out.candidate_repository if out.candidate_repository[p] != WORK[p])
        self.assertEqual(changed, ['style.css'])
        self.assertEqual(len(Executor.calls), 1)                         # the sandbox verification ran, on the candidate
        # the gates are the same ones: a candidate that does not verify is failed, and says which gate stopped it
        class Failing(Executor):
            def execute(self, *, repository, spec):
                return ExecutionReport(False, (AcceptanceFailure('A1', 'not working', 'style.css'),), 'failed')
        stopped = CandidateModificationEngine(classifier=Boom(), repairer=Boom(), executor=Failing(), evolver=Boom(),
                                              quality_fn=lambda **k: Gate(), security_fn=lambda repo: Gate(),
                                              rights_engine=Rights()).propose(spec=spec, repository=dict(WORK),
                                                                              followup=SF.followup_for(record))
        self.assertEqual((stopped.status, stopped.gates.blocking_gate), ('failed', 'verification'))
        # a version that moved on since: the block no longer applies, and the candidate says so instead of guessing
        moved = {**WORK, 'style.css': CSS.replace('bottom:-40px', 'bottom:0px')}
        failed = engine.propose(spec=spec, repository=moved, followup=SF.followup_for(record))
        self.assertEqual(failed.status, 'failed')
        self.assertEqual(failed.candidate_repository, moved)
        self.assertEqual(failed.gates.blocking_gate, 'verification')


class TheRoundWritesFiveLines(unittest.TestCase):
    def test_a_fix_reaches_the_model_reduced_with_the_width_and_the_build_id_and_both_images_are_kept(self):
        data = BIG
        reader = Reader(FIX_ANSWER)
        record, store, attachments = run_round(reader, data=data, width=390, note='הכפתור נעלם')
        call = reader.calls[0]
        self.assertEqual(A.validate_image(call['image'])[1:], (1400, 840))              # what the model read: reduced
        self.assertEqual(call['user']['viewport_width'], 390)                             # rule 2: the width travels with it
        self.assertEqual(call['user']['build_id'], 'bld_abc123')
        self.assertEqual(call['user']['version_id'], 'ver_1')
        self.assertEqual(call['user']['customer_note'], 'הכפתור נעלם')
        self.assertEqual(sorted(call['user']['files']), ['app.js', 'index.html', 'style.css'])
        self.assertIn('POINTER', call['system'])                                         # the model is told: a pointer, never a brief
        # rule 4: both images are stored, with their digests, on the build's record
        ids = {record['original']['attachment_id'], record['reduced']['attachment_id']}
        self.assertEqual(len(ids), 2)
        self.assertEqual(attachments.blobs[record['original']['attachment_id']], data)
        self.assertEqual(hashlib.sha256(attachments.blobs[record['reduced']['attachment_id']]).hexdigest(), record['reduced']['sha256'])
        self.assertEqual(attachments.blobs[record['reduced']['attachment_id']], call['image'])
        self.assertEqual(record['viewport_width'], 390)
        self.assertEqual(record['build_id'], 'bld_abc123')
        self.assertEqual(record['outcome'], 'fix_ready')
        self.assertEqual(record['fix']['paths'], ['style.css'])

    def test_each_stage_writes_one_line_in_order(self):
        record, _, _ = run_round(Reader(FIX_ANSWER))
        self.assertEqual([line['stage'] for line in record['evidence']], list(SF.STAGES))
        by = {line['stage']: line for line in record['evidence']}
        self.assertTrue(all(line['ok'] for line in record['evidence']))
        self.assertEqual((by['receipt']['viewport_width'], by['receipt']['build_id']), (390, 'bld_abc123'))
        self.assertEqual((by['reduction']['original']['width'], by['reduction']['reduced']['width']), (3000, 1400))
        self.assertTrue(by['reduction']['scaled'])
        self.assertEqual((by['model_call']['model'], by['model_call']['viewport_width'], by['model_call']['image_long_side']),
                         ('test-vision-model', 390, 1400))
        self.assertEqual(by['edit']['paths'], ['style.css'])
        self.assertEqual(by['result']['outcome'], 'fix_ready')

    def test_the_record_is_in_the_conversation_and_the_build_reads_it_back(self):
        record, store, _ = run_round(Reader(FIX_ANSWER))
        messages = store.messages_for('prj_1', limit=10)
        self.assertEqual([m['role'] for m in messages], ['customer', 'assistant'])
        self.assertTrue((messages[0]['interpretation'] or {}).get('label'))               # the customer's line is a label, not a request
        self.assertEqual(messages[0]['interpretation']['attachments'][0]['id'], record['original']['attachment_id'])
        action = messages[1]['interpretation']['actions'][0]
        self.assertEqual((action['type'], action['fingerprint']), ('apply_shot_fix', record['fix']['fingerprint']))
        self.assertEqual(SF.records_for_build(messages, 'bld_abc123'), [record])
        self.assertEqual(SF.records_for_build(messages, 'bld_other'), [])
        self.assertEqual(SF.record_for_fix(messages, record['fix']['fingerprint']), record)
        self.assertIsNone(SF.record_for_fix(messages, 'f' * 64))

    def test_a_screenshot_within_the_bound_is_the_one_image_and_says_so(self):
        record, _, attachments = run_round(Reader(FIX_ANSWER), data=png(390, 800))
        self.assertEqual(record['original']['attachment_id'], record['reduced']['attachment_id'])
        self.assertFalse(record['evidence'][1]['scaled'])
        self.assertEqual(len(attachments.rows), 1)

    def test_a_round_that_fails_keeps_both_images_and_all_five_lines(self):
        failures = {'not_connected': SF.NotConnectedReader(),
                    'late': Reader(error=SF.ShotReadFailed('late', 'not settled in 25 s')),
                    'unreadable': Reader(error=SF.ShotReadFailed('unreadable', 'provider error')),
                    'cannot_tell': Reader({'cannot_tell': 'איזה כפתור?'}),
                    'rebuild_refused': Reader({'files': {'index.html': '<html></html>'}}),
                    'edit_not_applicable': Reader({'edits': [{'path': 'style.css', 'old': 'nowhere', 'new': 'x'}]}),
                    'version_unavailable': SF.FailedReader('version_unavailable', 'no version')}
        for code, reader in failures.items():
            with self.subTest(code=code):
                record, store, attachments = run_round(reader)
                self.assertEqual(record['outcome'], code)
                self.assertEqual(len(attachments.rows), 2)                                # original and reduced, kept
                self.assertEqual([line['stage'] for line in record['evidence']], list(SF.STAGES))
                self.assertFalse(record['evidence'][-1]['ok'])
                self.assertIsNone(record['fix'])
                last = store.messages_for('prj_1', limit=10)[-1]
                self.assertEqual(last['interpretation']['actions'], [])                   # nothing to apply
                self.assertEqual(SF.records_for_build(store.messages_for('prj_1', limit=10), 'bld_abc123'), [record])

    def test_a_request_refused_up_front_stores_nothing(self):
        for kwargs in ({'data': b'not an image'}, {'width': 100}):
            with self.subTest(kwargs=kwargs):
                store, attachments = MemoryConversationStore(), MemoryAttachments()
                with self.assertRaises((A.AttachmentError, SF.ShotError)):
                    run_round(Reader(FIX_ANSWER), store=store, attachments=attachments, **kwargs)
                self.assertEqual((store.messages_for('prj_1', limit=5), attachments.rows), ([], {}))

    def test_a_stage_is_written_once(self):
        ev = SF.Evidence('bld_x')
        ev.add('receipt', True)
        with self.assertRaises(ValueError):
            ev.add('receipt', True)
        with self.assertRaises(ValueError):
            ev.add('somewhere', True)


class TheCustomerReadsIt(unittest.TestCase):
    CODES = ('fix_ready',) + SF.FAILURES

    def test_every_result_is_said_in_each_language_with_the_next_action(self):
        for lang, script in (('he', HEBREW), ('ar', ARABIC), ('en', None)):
            for code in self.CODES:
                text = SF.sentence(code, lang, what='x y')
                with self.subTest(lang=lang, code=code):
                    self.assertGreater(len(text.split()), 6)
                    if script:
                        self.assertRegex(text, script)
                        self.assertNotRegex(text.replace('x y', ''), LATIN)
                    else:
                        self.assertNotRegex(text, '[֐-ۿ]')
                    self.assertEqual(CW.machine_terms(text), [])
                    if lang != 'ar':
                        self.assertEqual(offences(text, lang), [])

    def test_a_screenshot_that_could_not_be_read_says_it_is_saved_and_what_to_do_next(self):
        for lang in SF.LANGS:
            for code in ('not_connected', 'cannot_tell', 'unreadable', 'edit_not_applicable'):
                record, store, _ = run_round(SF.NotConnectedReader() if code == 'not_connected' else Reader({'edits': []}),
                                             lang=lang)
                said = store.messages_for('prj_1', limit=5)[-1]['content']
                self.assertIn(SF.sentence('not_connected' if code == 'not_connected' else 'no_edit', lang), said)

    def test_an_unknown_result_or_language_raises(self):
        with self.assertRaises(ValueError):
            SF.sentence('a_code_nobody_worded', 'he')
        with self.assertRaises(ValueError):
            SF.sentence('late', 'fr')
        with self.assertRaises(ValueError):
            SF.sentence('uploaded', 'he')                                                 # a label, not a result

    def test_the_words_file_is_customer_text_with_no_platform_word(self):
        self.assertEqual([t for t, _ in [(w, 0) for lang in SF.TEXT.values() for w in CW.machine_terms(' '.join(lang.values()))]], [])
        self.assertEqual(CW.machine_terms(' '.join(SF.BUTTON.values())), [])


class TheModeIsLoud(unittest.TestCase):
    def test_off_is_the_default_and_a_wrong_value_raises(self):
        with mock.patch.dict('os.environ', {}, clear=False):
            import os
            os.environ.pop('OMNI_SHOT_FIX', None)
            self.assertEqual(SF.mode(), 'off')
            self.assertIsInstance(SF.reader_for(mock.Mock(reservations=object(), enqueue=object()), account_id='a', project_id='p',
                                                request_key=None), SF.NotConnectedReader)
        with mock.patch.dict('os.environ', {'OMNI_SHOT_FIX': 'maybe'}), self.assertRaises(ValueError):
            SF.mode()

    def test_on_needs_the_queue_and_a_cap_the_owner_set(self):
        sup = mock.Mock(reservations=object(), enqueue=object())
        with mock.patch.dict('os.environ', {'OMNI_SHOT_FIX': 'on'}):
            import os
            os.environ.pop('OMNI_SHOT_FIX_PROJECT_USD', None)
            self.assertIsInstance(SF.reader_for(sup, account_id='a', project_id='p', request_key=None), SF.NotConnectedReader)
        with mock.patch.dict('os.environ', {'OMNI_SHOT_FIX': 'on', 'OMNI_SHOT_FIX_PROJECT_USD': '0.50'}):
            self.assertIsInstance(SF.reader_for(sup, account_id='a', project_id='p', request_key=None), SF.ReservedShotReader)
        with mock.patch.dict('os.environ', {'OMNI_SHOT_FIX': 'on', 'OMNI_SHOT_FIX_PROJECT_USD': 'a lot'}), self.assertRaises(ValueError):
            SF.reader_for(sup, account_id='a', project_id='p', request_key=None)


class TheWiring(unittest.TestCase):
    def test_an_image_round_has_its_own_budget_scope_task_and_worker_support(self):
        from omni_prod.intake import budget as B
        from omni_prod.intake import reservation_worker as RW
        from omni_prod.intelligence.task_policy import TASK_CLASSES
        self.assertIn(SF.PURPOSE, B.PURPOSES)
        self.assertEqual((SF.PURPOSE, SF.TASK), ('shot-fix', 'screenshot_fix'))
        self.assertIn(SF.TASK, RW.RESERVED_TASKS)
        self.assertIn(SF.TASK, TASK_CLASSES)
        with self.assertRaises(ValueError):
            B.scopes_for('usr_1', 'prj_1', B.PRODUCTION, None, B.Caps(project_usd=__import__('decimal').Decimal('1'),
                                                                     daily_usd=__import__('decimal').Decimal('1')), 'nowhere')

    def test_the_screenshot_fix_never_reads_the_conversation_agents_model_profile(self):
        source = (ROOT / 'omni_prod' / 'shot_fix.py').read_text(encoding='utf-8')
        self.assertNotIn('venice_profile', source)
        self.assertNotIn('conversation_agent', source)
        self.assertIn('routed_only=True', source)

    def test_the_fixtures_messages_are_the_servers_messages(self):
        from omni_prod import investor_app as IA
        record, store, _ = run_round(Reader(FIX_ANSWER))
        out = json.loads(__import__('subprocess').run(['python3', str(ROOT / 'tests' / 'shot_fix_fixture.py')], cwd=ROOT,
                                                      capture_output=True, text=True, check=True).stdout)
        mine = [IA._conversation_message(m) for m in store.messages_for('prj_1', limit=10)]
        theirs = out['views']['he']['after']['messages'][-2:]
        for a, b in zip(mine, theirs):
            for key in ('role', 'intent', 'attachments', 'notices', 'brief_revision'):
                self.assertEqual(a[key], b[key], key)
        self.assertEqual(sorted(mine[-1]), sorted(theirs[-1]))
        self.assertEqual(mine[-1]['actions'][0]['type'], theirs[-1]['actions'][0]['type'])

    def test_the_tests_run_in_ci_and_the_browser_test_names_its_mutations_and_bounds_every_wait(self):
        ci = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
        self.assertIn('node --check tests/shot_fix_browser.cjs', ci)
        self.assertIn('      - run: node tests/shot_fix_browser.cjs\n        timeout-minutes: 4\n', ci)
        pg = (ROOT / '.github' / 'workflows' / 'intake-budget-pg.yml').read_text(encoding='utf-8')
        self.assertIn('tests/test_shot_fix_pg.py', pg)
        self.assertIn('tests/test_shot_fix_routes_pg.py', pg)
        text = (ROOT / 'tests' / 'shot_fix_browser.cjs').read_text(encoding='utf-8')
        for what in ('the width is not sent as the frame has it', 'the build id is not on the card', 'the build card is a second card of its own',
                     'the switch changes nothing', 'the click sends no stored fix', 'the upload goes to another build',
                     'the file is changed on the way'):
            self.assertIn(what, text)
        self.assertIn('assert.equal(APP.split(from).length, 2', text)
        self.assertIn('WATCHDOG_MS', text)
        self.assertIn('setDefaultTimeout', text)
        self.assertNotIn('waitForTimeout', text)


class TheWordsFileIsScanned(unittest.TestCase):
    def test_the_customer_words_scan_reads_shot_fix_and_finds_nothing(self):
        self.assertIn('omni_prod/shot_fix.py', CW.CUSTOMER_TEXT)
        self.assertEqual(CW.scan('omni_prod/shot_fix.py', root=ROOT), [])


if __name__ == '__main__':
    unittest.main()

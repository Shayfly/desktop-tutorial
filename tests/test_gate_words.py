"""Warehouse 132 (the owner, 2026-11-22): every blocking finding in the customer's words, with the next action.

Acceptance (WAREHOUSE.md 132):
  1. every blocking check has customer words and a next action; a test walks the list of checks and a check with no
     words fails -- the list is READ from the code (tests/test_site_content_owners.produced_ids: every unit of every
     gate the worker installs, every failure-id constant, the post-build layers and their suffixes; plus each check's
     own closed list of kinds), never typed here;
  2. the words are in the customer's language (Hebrew and Arabic, and English);
  3. technical terms are counted per route (customer_words.scan over CUSTOMER_TEXT, which now holds gate_words.py).

Real path: the gates run as the worker runs them (skill_units.gate.SkillGateExecutor on a real broken fixture,
consistency_gate.scan on a broken file), their failures go through the production worker job (_run_live_build_job via
the BuildHarness, as tests/test_build_failed_announced.py) into announce_if_failed and a MemoryConversationStore (it
stands in for SQL only). No model call, no network.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import build_announcement as BA
from omni_prod import customer_words as CW
from omni_prod import gate_words as G
from omni_prod.autonomous_core import AcceptanceFailure, ExecutionReport
from omni_prod.build_announcement import FailureWitness, announce_if_failed, message_for
from omni_prod.conversation.store import MemoryConversationStore
from tests.test_m3_preview_logic import BuildHarness
from tests.test_plain_words_failure_and_approval import offences
from tests.test_site_content_owners import produced_ids

ROOT = Path(__file__).resolve().parents[1]
HEBREW, ARABIC, LATIN = re.compile('[א-ת]'), re.compile('[؀-ۿ]'), re.compile('[A-Za-z]')
REQUEST = {'public_project_id': 'prj_words', 'user_id': 'usr_customer'}


def every_id() -> dict[str, str]:
    """{acceptance id: where it is produced}: the owners test's list, plus the approved-criteria prefix it misses."""
    from omni_prod.worker_tasks import APPROVED_PREFIX
    return {**produced_ids(), APPROVED_PREFIX + 'AC1': 'worker_tasks.merge_approved_criteria'}


def kind_messages() -> dict[str, tuple[str, str]]:
    """{expected key: (acceptance id, message)} for every kind a check's own code lists, each message made the way
    the check makes it."""
    from omni_prod import browser_probe, consistency_gate as C, game_runtime, runtime_load, window_catalog
    from omni_prod.site_content.owners import REVIEW_RULES
    out = {}
    for check in C.CHECKS:
        [f] = C.failures(C.ConsistencyReport(findings=[C.Finding(check, 'app.py', 3, 'it is broken', 'fix it')]))
        out[f'CONSISTENCY:{check}'] = (f.acceptance_id, f.message)
    for kind, marker in G.BROWSER_KINDS:
        out[f'BROWSER:{kind}'] = (browser_probe.BROWSER_FAILURE_ID, 'the product misbehaves in a real browser: ' + marker)
    assert len(G.REVIEW_KINDS) == len(REVIEW_RULES) - 1, 'a static REVIEW rule with no kind here'
    for kind, marker in G.REVIEW_KINDS:
        out[f'REVIEW:{kind}'] = ('REVIEW', f'QA review (skill.copy_quality): {marker}: x')
    for code in window_catalog.CODES:
        out[f'window-:{code}'] = (window_catalog.ACCEPTANCE_PREFIX + 'age_gate', f'{code}: the window is wrong')
    for code in runtime_load.CODES:
        out[f'{runtime_load.ACCEPTANCE_ID}:{code}'] = (runtime_load.ACCEPTANCE_ID,
                                                       f'{code}: why. {runtime_load._FIX.get(code, "")}')
    from omni_prod import app_states
    for code in app_states.CODES:                       # warehouse 130: the failure id is the prefix + its code
        out[app_states.ACCEPTANCE_PREFIX + code] = (app_states.ACCEPTANCE_PREFIX + code,
                                                    f'{code}: why. {app_states._FIX[code]}')
    for code in game_runtime.CODES:
        out[f'{game_runtime.ACCEPTANCE_ID}:{code}'] = (game_runtime.ACCEPTANCE_ID,
                                                       f'{code} (phone): why. {game_runtime._FIX.get(code, "")}')
    from omni_prod.fact_canon import _NEEDS
    for kind in _NEEDS:
        out[f'needs:{kind}'] = ('', f'missing from the customer: {kind}')
    return out


def sandbox_messages() -> list[str]:
    """The messages the sandbox puts on the spec's own acceptance ids, from the functions that make them."""
    from omni_prod import project_manifest as PM, sandbox_executor as SE
    from tests.policy_fixtures import ACCEPTED_SPEC
    for literal, rel in (('build command failed', 'omni_prod/sandbox_executor.py'),
                         ('remote build failed', 'omni_prod/remote_sandbox.py')):
        assert f"'{literal}'" in (ROOT / rel).read_text(encoding='utf-8'), f'{literal!r} is no longer made in {rel}'
    msgs = ['build command failed', 'build command failed: at app.py', 'remote build failed: at app.py',
            SE.verify_failure_message('unit tests', ['pytest'], 1), SE.verify_failure_message('unit tests', ['pytest'], 5),
            SE.verify_failure_message('unit tests', ['pytest'], 1, 'remote verification failed'),
            f'verification failed: unit tests — {SE.NO_TEST_EXECUTED_MESSAGE}']
    msgs += [f.message for f in PM.invalid_manifest_report(ValueError('bad json'), ACCEPTED_SPEC).failures]
    msgs += [f.message for f in PM.uncovered_acceptance_failures(PM.ProjectManifest(build=(), verify=()), ACCEPTED_SPEC)]
    return msgs


def the_key(aid: str, msg: str = '') -> str:
    if aid == '':
        [key] = G.findings((), error_code='needs_customer_input', error_message=msg)
        return key
    return G.key_of(aid, msg)


class EveryBlockingCheckHasWords(unittest.TestCase):
    maxDiff = None

    def test_every_id_the_chain_can_produce_has_words_in_every_language(self):
        ids = every_id()
        self.assertGreaterEqual(len(ids), 90)
        unworded = {}
        for aid, where in sorted(ids.items()):
            if aid in G.NOT_A_FINDING:
                continue
            try:
                key = G.key_of(aid, '')
                for lang in G.LANGS:
                    G.words(key, lang)
            except G.NoWords:
                unworded[aid] = where
        self.assertEqual(unworded, {})

    def test_every_kind_a_check_lists_in_its_own_code_has_words(self):
        unworded = {}
        for expected, (aid, msg) in sorted(kind_messages().items()):
            try:
                self.assertEqual(the_key(aid, msg), expected)
            except G.NoWords:
                unworded[expected] = msg[:60]
        self.assertEqual(unworded, {})

    def test_the_kind_markers_are_the_producers_own_words(self):
        from omni_prod import browser_probe
        from omni_prod.site_content.owners import REVIEW_RULES
        self.assertEqual({k for k, _ in G.BROWSER_KINDS}, set(browser_probe.BLOCKING))
        for kind, marker in G.BROWSER_KINDS:
            self.assertIn(marker, browser_probe.PROBE, kind)
        runtime = (ROOT / 'omni_prod' / 'skills_runtime.py').read_text(encoding='utf-8')
        matched = []
        for kind, marker in G.REVIEW_KINDS:
            self.assertIn(marker, runtime, kind)                          # skills_runtime still says it
            rules = [i for i, (p, _) in enumerate(REVIEW_RULES[:-1]) if p.search(marker)]
            self.assertEqual(len(rules), 1, kind)                         # one static REVIEW rule, not the catch-all
            matched += rules
        self.assertEqual(sorted(matched), list(range(len(REVIEW_RULES) - 1)))   # every static rule has its kind

    def test_the_products_own_criteria_are_said_by_what_the_sandbox_saw(self):
        for msg in sandbox_messages():
            with self.subTest(msg=msg[:50]):
                key = G.key_of('AC-7', msg)                     # a spec id the architect model chose: any text
                self.assertTrue(key.startswith('SANDBOX:'), key)
                self.assertEqual(G.key_of('accept-R1', msg), key)
        self.assertEqual({G.key_of('AC-7', m) for m in sandbox_messages()},
                         {k for k in G.WORDS if k.startswith('SANDBOX:')})

    def test_no_words_for_a_check_nobody_can_fail(self):
        reachable = set(kind_messages()) | {G.key_of('AC-7', m) for m in sandbox_messages()}
        for aid in every_id():
            try:
                reachable.add(G.key_of(aid, ''))
            except G.NoWords:
                pass                         # an id with no words is the first test's failure, not this one's
        self.assertEqual(set(G.WORDS) - reachable, set())

    def test_a_check_with_no_words_raises_and_is_never_guessed(self):
        for aid, msg in (('gate-NEWGATE-unit', 'NEW_CODE (skill.new) on index.html: x'), ('SOMETHING_NEW', 'x'),
                         ('CONSISTENCY', 'consistency (newcheck): app.py x'), ('gate-G8-runtime-load', 'LOAD_NEW: x'),
                         ('gate-GAME-runtime', 'GAME_NEW (phone): x'), ('window-age_gate', 'WINDOW_NEW: x'),
                         ('AC-7', 'tests failed')):
            with self.subTest(aid=aid), self.assertRaises(G.NoWords):
                G.key_of(aid, msg)
        with self.assertRaises(G.NoWords):
            G.findings((), error_code='needs_customer_input', error_message='missing from the customer: fax')
        with self.assertRaises(G.NoWords):
            G.words('gate-NEWGATE-unit', 'he')

    def test_the_engines_notes_are_not_findings_and_the_owners_table_agrees(self):
        from omni_prod.site_content.owners import owner_of
        for aid in G.NOT_A_FINDING:
            self.assertEqual(owner_of(aid), 'advisory', aid)
            self.assertIsNone(G.key_of(aid, 'anything'))
            self.assertIn(aid, every_id())


class EveryWordingHasTheNextAction(unittest.TestCase):
    def test_every_entry_says_what_why_and_one_next_action_named_as_its_button(self):
        buttons = {'retry': BA.RETRY_BUTTON, 'edit': BA.EDIT_BUTTON}
        for key in G.WORDS:
            for lang in G.LANGS:
                with self.subTest(key=key, lang=lang):
                    w = G.words(key, lang)
                    self.assertIn(w['action'], G.ACTIONS)
                    for part in ('what', 'why', 'next'):
                        self.assertIsInstance(w[part], str)
                        self.assertGreaterEqual(len(w[part].split()), 2, part)
                    self.assertFalse(w['what'].endswith('.') or w['why'].endswith('.'))
                    self.assertNotEqual(w['next'], w['why'])
                    if lang in ('he', 'en'):
                        self.assertIn(f'"{buttons[w["action"]][lang]}"', w['next'])
                    else:
                        self.assertIn('الزر', w['next'])                 # the button under the message

    def test_an_entry_with_no_action_or_no_next_step_is_refused(self):
        broken = G.Entry('', ('א ב', 'ג ד'), ('ا ب', 'ج د'), ('a b', 'c d'))
        with mock.patch.dict(G.WORDS, {'gate-X-y': broken}), self.assertRaises(ValueError):
            G.words('gate-X-y', 'he')
        with self.assertRaises(ValueError):
            G.words('gate-G11-links_tel', 'fr')                          # a language with no words: raised


class TheCustomersLanguage(unittest.TestCase):
    def test_hebrew_and_arabic_carry_no_english_and_english_no_hebrew(self):
        for key in G.WORDS:
            he, ar, en = (' '.join(G.words(key, lang)[p] for p in ('what', 'why', 'next')) for lang in G.LANGS)
            with self.subTest(key=key):
                self.assertTrue(HEBREW.search(he) and not LATIN.search(he), he)
                self.assertTrue(ARABIC.search(ar) and not LATIN.search(ar) and not HEBREW.search(ar), ar)
                self.assertFalse(HEBREW.search(en) or ARABIC.search(en), en)

    def test_no_machinery_word_reaches_the_customer(self):
        for key in G.WORDS:
            for lang in G.LANGS:
                text = ' '.join(G.words(key, lang)[p] for p in ('what', 'why', 'next'))
                with self.subTest(key=key, lang=lang):
                    self.assertEqual(CW.machine_terms(text), [])
                    if lang != 'ar':
                        self.assertEqual(offences(text, lang), [])

    def test_the_words_file_is_customer_text_and_holds_no_platform_word(self):
        self.assertIn('omni_prod/gate_words.py', CW.CUSTOMER_TEXT)
        self.assertEqual(CW.scan('omni_prod/gate_words.py', root=ROOT), [])


def run_build(h, store=None):
    """The production worker job, its jobs wrapped and announced exactly as _run_live_build_job_with_components does."""
    witness = FailureWitness(h.jobs)
    h.jobs.request = {**(h.jobs.request or {}), **REQUEST}
    store = store if store is not None else MemoryConversationStore()
    real_jobs, h.jobs = h.jobs, witness
    try:
        outcome = h.run()
    finally:
        h.jobs = real_jobs
        announce_if_failed(witness, conversation=store, request=real_jobs.get_request('bld_1'), build_id='bld_1')
    return outcome, store.messages_for('prj_words', limit=10)


class _Passing:
    last_pages = None

    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'log', 1)


def real_tel_failure():
    """A real G11 failure: the gate the worker installs, blocking, on the butcher page whose call button dials a
    digit short (skill_units/links_tel/fixtures/broken)."""
    from omni_prod.skill_units.gate import SkillGateExecutor
    from tests.policy_fixtures import ACCEPTED_SPEC
    page = (ROOT / 'omni_prod/skill_units/links_tel/fixtures/broken/butcher_tel_digit.html').read_text(encoding='utf-8')
    report = SkillGateExecutor(_Passing(), 'G11', 'block').execute(repository={'index.html': page}, spec=ACCEPTED_SPEC)
    assert not report.passed
    return report


class TheCustomerReadsIt(unittest.TestCase):
    def failed_with(self, report, **attrs):
        h = BuildHarness(verified=False)
        h.result.report, h.result.status = report, 'failed'
        for k, v in attrs.items():
            setattr(h.result, k, v)
        return h

    def test_a_real_gate_failure_reaches_the_conversation_in_the_customers_words(self):
        outcome, [m] = run_build(self.failed_with(real_tel_failure()))
        self.assertEqual(outcome, 'failed')
        tel = G.words('gate-G11-links_tel', 'he')
        self.assertEqual(m['content'], 'לא הצלחנו לבנות את האתר הפעם. ' + f"{tel['what']} — {tel['why']}. "
                         + 'לא חויבתם. ' + tel['next'])
        self.assertEqual(m['interpretation']['findings'], ['gate-G11-links_tel'])
        self.assertEqual([a['type'] for a in m['interpretation']['actions']], ['retry_build'])
        self.assertFalse(LATIN.search(m['content']))
        self.assertEqual(CW.machine_terms(m['content']), [])
        self.assertEqual(offences(m['content'], 'he'), [])

    def test_a_missing_phone_is_said_as_the_owner_wrote_it_and_asks_for_the_number(self):
        h = self.failed_with(ExecutionReport(False, (AcceptanceFailure(
            'REVIEW', 'QA review (skill.copy_quality): contact details not in the approved request (invented): +97231'),),
            'log'), stop_reason='needs_customer_input')
        h.engine.core.needs_input = ['phone']
        _, [m] = run_build(h)
        self.assertEqual(m['interpretation']['error_code'], 'needs_customer_input')
        self.assertIn('חסר מספר טלפון — בלי זה אנשים לא יכולים להתקשר אליכם.', m['content'])
        self.assertTrue(m['content'].endswith('כתבו את המספר בבקשה: לחצו על "עריכת הבקשה".'), m['content'])
        self.assertEqual([a['type'] for a in m['interpretation']['actions']], ['edit_requirements'])
        self.assertNotIn(BA.RETRY_BUTTON['he'], m['content'])

    def test_a_real_consistency_failure_is_said_by_its_kind(self):
        from omni_prod import consistency_gate as C
        failures = C.failures(C.scan({'app.py': 'def broken(:\n    pass\n'}))
        keys = G.findings([f.__dict__ for f in failures])
        self.assertEqual(keys, ['CONSISTENCY:syntax'])
        content = message_for(build_id='bld_1', error_code='verification_failed', billing=None, findings=keys)['content']
        self.assertIn(G.words('CONSISTENCY:syntax', 'he')['what'], content)

    def test_each_language_reads_its_own_words(self):
        keys = G.findings(G.verification_failures({'gates': {'verification': {'failures': [
            f.__dict__ for f in real_tel_failure().failures]}}}))
        en = message_for(build_id='b', error_code='verification_failed', billing='released', lang='en', findings=keys)
        ar = message_for(build_id='b', error_code='verification_failed', billing='released', lang='ar', findings=keys)
        he = message_for(build_id='b', error_code='verification_failed', billing='released', lang='he', findings=keys)
        self.assertIn(G.words('gate-G11-links_tel', 'en')['what'], en['content'])
        self.assertFalse(HEBREW.search(en['content']) or ARABIC.search(en['content']))
        self.assertTrue(ARABIC.search(ar['content']) and not LATIN.search(ar['content']) and not HEBREW.search(ar['content']))
        self.assertFalse(LATIN.search(he['content']))

    def test_one_action_when_the_findings_need_different_ones(self):
        keys = G.findings([{'acceptance_id': 'gate-G11-links_tel', 'message': 'TEL_BROKEN x'},
                           {'acceptance_id': 'UNSUPPORTED_DEPENDENCY', 'message': 'needs y'}])
        self.assertEqual(keys, ['UNSUPPORTED_DEPENDENCY', 'gate-G11-links_tel'])     # what only the customer can change first
        msg = message_for(build_id='b', error_code='unsupported_dependency', billing=None, findings=keys)
        self.assertTrue(msg['content'].endswith(G.NEXT['he']['edit']))
        self.assertNotIn(BA.RETRY_BUTTON['he'], msg['content'])
        self.assertEqual([a['type'] for a in msg['interpretation']['actions']], ['edit_requirements'])

    def test_at_most_three_findings_are_listed_and_the_rest_counted(self):
        keys = ['gate-G11-links_tel', 'gate-G11-links_anchor', 'gate-G1-blocks_empty', 'gate-BRAND-brand_name',
                'gate-SHARE-share_meta']
        content = message_for(build_id='b', error_code='verification_failed', billing=None, findings=keys)['content']
        self.assertEqual(content.count(' — '), 3)
        self.assertIn(BA.MORE['he'].format(n=2), content)
        self.assertEqual(content.count(G.NEXT['he']['retry']), 1)                   # the shared step, said once

    def test_a_finding_with_no_words_is_logged_and_the_general_sentence_said(self):
        witness = FailureWitness(BuildHarness().jobs)
        witness.failed = {'error_code': 'verification_failed', 'evidence_json': {'gates': {'verification': {
            'failures': [{'acceptance_id': 'gate-NEWGATE-unit', 'message': 'NEW_CODE (skill.new) on index.html: x'}]}}}}
        store = MemoryConversationStore()
        with self.assertLogs('omni_prod.build_announcement', 'ERROR') as logs:
            self.assertTrue(announce_if_failed(witness, conversation=store, request=REQUEST, build_id='bld_9'))
        self.assertIn('BUILD_FINDING_UNWORDED build=bld_9', '\n'.join(logs.output))
        [m] = store.messages_for('prj_words')
        self.assertEqual(m['content'], 'לא הצלחנו לבנות את האתר הפעם. אפשר לנסות שוב: לחצו על "לנסות לבנות שוב".')
        self.assertNotIn('findings', m['interpretation'])


class TheReviewFindings(unittest.TestCase):
    """The independent review of 132 (2026-11-22): D1, D2 and D3, each reproduced before it was fixed."""

    def test_d1_a_finding_with_no_words_does_not_take_the_worded_ones_down(self):
        failures = [{'acceptance_id': 'gate-G11-links_tel', 'message': 'TEL_BROKEN x'},
                    {'acceptance_id': 'AC-1', 'message': 'tests failed'}]          # AC-1: no words (see above)
        keys, unworded = G.collect(failures)
        self.assertEqual(keys, ['gate-G11-links_tel'])
        self.assertEqual(len(unworded), 1)
        self.assertIn("'AC-1'", unworded[0])
        with self.assertRaises(G.NoWords):                                         # the strict form still raises
            G.findings(failures)
        witness = FailureWitness(BuildHarness().jobs)
        witness.failed = {'error_code': 'verification_failed',
                          'evidence_json': {'gates': {'verification': {'failures': failures}}}}
        store = MemoryConversationStore()
        with self.assertLogs('omni_prod.build_announcement', 'ERROR') as logs:
            self.assertTrue(announce_if_failed(witness, conversation=store, request=REQUEST, build_id='bld_d1'))
        self.assertIn("BUILD_FINDING_UNWORDED build=bld_d1: no customer words for the check 'AC-1'", '\n'.join(logs.output))
        [m] = store.messages_for('prj_words')
        self.assertIn(G.words('gate-G11-links_tel', 'he')['what'], m['content'])
        self.assertEqual(m['interpretation']['findings'], ['gate-G11-links_tel'])

    def test_d1_an_unknown_fact_does_not_hide_the_known_one(self):
        keys, unworded = G.collect((), error_code='needs_customer_input',
                                   error_message='missing from the customer: fax, phone')
        self.assertEqual(keys, ['needs:phone'])
        self.assertEqual(len(unworded), 1)
        self.assertIn("'fax'", unworded[0])

    def test_d2_two_missing_facts_name_the_button_once_at_the_end(self):
        keys = G.findings((), error_code='needs_customer_input', error_message='missing from the customer: phone, hours')
        self.assertEqual(keys, ['needs:phone', 'needs:hours'])
        for lang, button in (('he', BA.EDIT_BUTTON['he']), ('en', BA.EDIT_BUTTON['en'])):
            with self.subTest(lang):
                content = message_for(build_id='b', error_code='needs_customer_input', billing='released', lang=lang,
                                      findings=keys)['content']
                self.assertEqual(content.count(button), 1, content)
                self.assertTrue(content.endswith(BA.TEXT[lang]['refunded'] + ' ' + G.NEXT[lang]['edit']), content)
                for k in keys:
                    self.assertIn(G.words(k, lang)['what'], content)
                    self.assertNotIn(G.words(k, lang)['next'], content)     # each fact's own step is not said too
        ar = message_for(build_id='b', error_code='needs_customer_input', billing=None, lang='ar', findings=keys)
        self.assertTrue(ar['content'].endswith(G.NEXT['ar']['edit']), ar['content'])

    def test_d2_one_missing_fact_keeps_its_own_step(self):
        content = message_for(build_id='b', error_code='needs_customer_input', billing='released',
                              findings=['needs:phone'])['content']
        self.assertTrue(content.endswith('לא חויבתם. כתבו את המספר בבקשה: לחצו על "עריכת הבקשה".'), content)
        self.assertEqual(content.count(BA.EDIT_BUTTON['he']), 1)

    def test_d3_a_step_missing_in_one_language_is_loud_and_never_a_crash(self):
        entry = G.Entry('edit', ('חסר פקס', 'כך'), ('ينقص الفاكس', 'هكذا'), ('The fax is missing', 'so'),
                        next={'he': 'כתבו את הפקס בבקשה.'})
        with mock.patch.dict(G.WORDS, {'needs:fax': entry}):
            with self.assertRaises(G.NoWords):
                G.words('needs:fax', 'ar')
            with self.assertLogs('omni_prod.build_announcement', 'ERROR') as logs:
                msg = message_for(build_id='bld_d3', error_code='needs_customer_input', billing=None, lang='ar',
                                  findings=['needs:fax'])
        self.assertIn("BUILD_FINDING_UNWORDED build=bld_d3: no next action in 'ar' for 'needs:fax'", '\n'.join(logs.output))
        self.assertEqual(msg['content'], BA.TEXT['ar']['failed'] + ' ' + BA.TEXT['ar']['needs_input'])
        self.assertNotIn('findings', msg['interpretation'])


class TheCountPerRoute(unittest.TestCase):
    def test_the_failure_route_holds_no_platform_word(self):
        for path in ('omni_prod/build_announcement.py', 'omni_prod/gate_words.py', 'omni_prod/build_readiness.py'):
            with self.subTest(path):
                self.assertEqual(CW.scan(path, root=ROOT), [])


if __name__ == '__main__':
    unittest.main()

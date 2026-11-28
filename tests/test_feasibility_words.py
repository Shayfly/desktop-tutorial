"""Warehouse 132 (the owner, 2026-11-22): the findings of the feasibility gate, in the customer's language, with the next action.

Root cause (2026-11-27): a finding of `planning.feasibility.assess` is the platform's own English ("product family mobile_app",
"verification step status BLOCKED"). The conversation printed the raw item for every customer but a Hebrew one asking about
sign-in or an integration, the "cannot be approved yet" reply joined the raw items, the answer to "can you add X?" printed the
raw reason, and the plan tab printed `item: reason` to Arabic and English customers. Now one table says each finding once
(omni_prod/planning/feasibility_words.py), in Hebrew, Arabic and English, with its next action.

Acceptance (WAREHOUSE.md 132), on the real path:
  1. every finding the gate can produce has words and a next action: the list is READ from the code (every `Finding(` of
     omni_prod, every check of CORE_CHECKS, every integration kind), never typed here; a new finding with no words fails;
  2. the words are in the customer's language (Hebrew, Arabic, English), each in its own script;
  3. platform words are counted per route (customer_words.scan) and the count is zero.
The reply is the real ConversationSupervisor's, from the real gate's findings. No model call, no network."""
from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import customer_words as CW
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import contract as C
from omni_prod.planning import feasibility as F
from omni_prod.planning import feasibility_words as FW
from tests.test_conversation_os import MemoryBriefs
from tests.test_plain_words_failure_and_approval import offences

ROOT = Path(__file__).resolve().parents[1]
HEBREW = re.compile('[֐-׿]')
ARABIC = re.compile('[؀-ۿ]')
LATIN = re.compile('[A-Za-z]')
# words an Arabic customer must not read (the dictionary of customer_words holds Hebrew and English only)
ARABIC_PLATFORM = ('خادم', 'سيرفر', 'مزود', 'واجهة برمجة', 'قاعدة بيانات', 'مواصفات')

# What an f-string item stands for, per prefix of the code: the values the code itself can put there.
FSTRING_VALUES = {
    'integration: ': sorted(F.INTEGRATION_AGENT),
    'sign-in (': ['simple)', 'roles)'],
    'product family ': ['mobile_app', 'game', 'desktop'],
    'assignment: ': ['T01', 'T12'],
}


def finding_items() -> list[str]:
    """The `item` (first argument) of every Finding( construction in omni_prod, expanded by the values of its f-string."""
    found = []
    for path in sorted((ROOT / 'omni_prod').rglob('*.py')):
        text = path.read_text(encoding='utf-8')
        if 'feasibility' not in text and 'Finding(' not in text:
            continue
        for node in ast.walk(ast.parse(text)):
            if not (isinstance(node, ast.Call) and getattr(node.func, 'attr', getattr(node.func, 'id', '')) == 'Finding'):
                continue
            first = node.args[0] if node.args else None
            # only the feasibility gate's own: a Finding of (item, outcome, reason) whose outcome is F.<NAME> or a constant of F
            second = node.args[1] if len(node.args) > 1 else None
            is_ours = isinstance(second, ast.Attribute) and getattr(second.value, 'id', '') == 'F' or \
                isinstance(second, ast.Name) and second.id in {'BLOCKED', 'WITH_CONSTRAINTS', 'UNKNOWN', 'UNSUPPORTED'}
            if not is_ours:
                continue
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                found.append((str(path.relative_to(ROOT)), first.value))
            elif isinstance(first, ast.JoinedStr):
                prefix = ''.join(v.value for v in first.values[:1] if isinstance(v, ast.Constant))
                if prefix not in FSTRING_VALUES:
                    found.append((str(path.relative_to(ROOT)), f'<f-string with prefix {prefix!r}: add its values to FSTRING_VALUES>'))
                else:
                    found.extend((str(path.relative_to(ROOT)), prefix + v) for v in FSTRING_VALUES[prefix])
            else:
                found.append((str(path.relative_to(ROOT)), '<an item that is not a string literal>'))
    return found


class EveryFindingHasWords(unittest.TestCase):
    def test_the_walk_found_the_findings_of_the_code(self):
        items = {i for _, i in finding_items()}
        self.assertIn('publishing', items)                                  # a constant item of feasibility.py
        self.assertIn('integration: payments', items)                       # an f-string of it, expanded
        self.assertIn('images', items)                                      # the supervisor's own probe
        self.assertTrue(any(i.startswith('assignment: ') for i in items))   # architect.plan's
        self.assertGreaterEqual(len(items), 20)

    def test_every_item_the_code_can_produce_has_words_in_every_language(self):
        for path, item in finding_items():
            for lang in FW.LANGS:
                with self.subTest(path=path, item=item, lang=lang):
                    self.assertTrue(FW.words(item, lang)['what'])

    def test_every_check_of_the_gate_and_every_integration_kind_has_words(self):
        for item in F.CORE_CHECKS:
            with self.subTest(check=item):
                FW.key_of(item)
        for kind in F.INTEGRATION_AGENT:
            with self.subTest(kind=kind):
                FW.key_of(f'integration: {kind}')
        from omni_prod.intake.contract import _INTEGRATION_WORDS
        for kind, _ in _INTEGRATION_WORDS:                                  # a kind the contract can name
            with self.subTest(contract_kind=kind):
                FW.key_of(f'integration: {kind}')

    def test_the_real_gate_on_real_contracts_finds_nothing_it_cannot_word(self):
        import dataclasses
        from omni_prod import discovery as D
        brief = D.start('אתר לעסק שלי, קוראים לו קפה נועה, בחיפה')
        base = C.from_brief(brief)
        probes = [base, dataclasses.replace(base, product_family='mobile_app'),
                  dataclasses.replace(base, authentication_requirements={'mode': 'roles', 'source': 'probe'}),
                  dataclasses.replace(base, integrations=[{'kind': k, 'detected_from': 'q', 'status': 'probe'} for k in F.INTEGRATION_AGENT])]
        seen = set()
        with mock.patch.object(F.R, 'agent_status', return_value='NOT_IMPLEMENTED'):
            for probe in probes:
                for f in F.assess(probe).findings:
                    seen.add(f.item)
                    for lang in FW.LANGS:
                        with self.subTest(item=f.item, lang=lang):
                            FW.words(f.item, lang)
        self.assertTrue(any(i.startswith('product family') for i in seen) and any(i.startswith('integration: ') for i in seen), seen)

    def test_a_finding_with_no_words_raises_and_is_never_guessed(self):
        with self.assertRaises(FW.NoWords):
            FW.key_of('a new check nobody worded')
        with self.assertLogs('omni_prod.planning.feasibility_words', level='ERROR'):
            said = FW.say({'item': 'a new check nobody worded'}, 'he')
        self.assertFalse(said['worded'])                                    # the general sentence, flagged, and logged as an error
        self.assertNotIn('nobody', ' '.join(str(v) for v in said.values()))


class EveryWordingHasTheNextAction(unittest.TestCase):
    def test_every_entry_says_what_why_and_one_next_action(self):
        for key, entry in FW.WORDS.items():
            for lang in FW.LANGS:
                with self.subTest(key=key, lang=lang):
                    what, why, nxt = getattr(entry, lang)
                    for part in (what, why, nxt):
                        self.assertGreaterEqual(len(part.split()), 2, part)
                        self.assertFalse(part.rstrip().endswith(('.', ':')), part)
                    self.assertNotEqual(nxt, why)
                    self.assertNotEqual(nxt, what)

    def test_an_entry_with_no_next_step_is_refused(self):
        broken = FW.Entry(('א ב', 'ג ד', ''), ('ا ب', 'ج د', 'هـ و'), ('a b', 'c d', 'e f'))
        with mock.patch.dict(FW.WORDS, {'publishing': broken}), self.assertRaises(ValueError):
            FW.words('publishing', 'he')
        with self.assertRaises(ValueError):
            FW.words('publishing', 'fr')                                   # a language with no words: raised, not guessed

    def test_the_general_sentence_also_has_a_next_action(self):
        for lang in FW.LANGS:
            what, why, nxt = getattr(FW.GENERAL, lang)
            self.assertTrue(what and why and nxt)
            self.assertIn(nxt, FW.reply([], lang))


class TheCustomersLanguage(unittest.TestCase):
    def texts(self, key):
        return {lang: ' '.join(getattr(FW.WORDS[key], lang)) for lang in FW.LANGS}

    def test_hebrew_and_arabic_carry_no_english_and_english_no_hebrew(self):
        for key in FW.WORDS:
            t = self.texts(key)
            with self.subTest(key=key):
                self.assertTrue(HEBREW.search(t['he']) and not LATIN.search(t['he']) and not ARABIC.search(t['he']), t['he'])
                self.assertTrue(ARABIC.search(t['ar']) and not LATIN.search(t['ar']) and not HEBREW.search(t['ar']), t['ar'])
                self.assertFalse(HEBREW.search(t['en']) or ARABIC.search(t['en']), t['en'])

    def test_no_platform_word_reaches_the_customer(self):
        for key in FW.WORDS:
            for lang, text in self.texts(key).items():
                with self.subTest(key=key, lang=lang):
                    self.assertEqual(CW.machine_terms(text), [])
                    if lang != 'ar':
                        self.assertEqual(offences(text, lang), [])
                    for word in ARABIC_PLATFORM:
                        self.assertNotIn(word, text)

    def test_the_words_file_is_customer_text_and_holds_no_platform_word(self):
        self.assertIn('omni_prod/planning/feasibility_words.py', CW.CUSTOMER_TEXT)
        self.assertIn('omni_prod/planning/feasibility_words.py', CW.CONVERSATION)
        self.assertEqual(CW.scan('omni_prod/planning/feasibility_words.py', root=ROOT), [])

    def test_the_platforms_item_names_are_never_in_a_sentence(self):
        for _, item in finding_items():
            for lang in FW.LANGS:
                said = FW.sentence({'item': item}, lang)
                with self.subTest(item=item, lang=lang):
                    self.assertNotIn(item, said)
                    self.assertNotRegex(said, r'mobile_app|BLOCKED|UNSUPPORTED|status|registry') if lang != 'en' else None


class TheCustomerReadsIt(unittest.TestCase):
    """The real ConversationSupervisor, on the real gate's findings."""

    def supervisor(self):
        return ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())

    def real_findings(self):
        import dataclasses
        from omni_prod import discovery as D
        base = C.from_brief(D.start('אתר לעסק שלי, קוראים לו קפה נועה, בחיפה'))
        probe = dataclasses.replace(base, product_family='mobile_app',
                                    authentication_requirements={'mode': 'simple', 'source': 'probe'},
                                    integrations=[{'kind': 'payments', 'detected_from': 'q', 'status': 'probe'}])
        with mock.patch.object(F.R, 'agent_status', return_value='NOT_IMPLEMENTED'):
            return [f for f in F.assess(probe).to_dict()['findings'] if f['outcome'] in (F.BLOCKED, F.UNSUPPORTED, F.UNKNOWN)]

    def test_a_blocked_build_is_said_in_each_language_with_its_next_action(self):
        blocked = self.real_findings()
        self.assertGreaterEqual(len(blocked), 3)
        sup = self.supervisor()
        for lang, script in (('he', HEBREW), ('ar', ARABIC), ('en', re.compile('[A-Za-z]'))):
            reply = sup._blocked_reply(blocked, lang)
            with self.subTest(lang=lang):
                self.assertRegex(reply, script)
                for f in blocked:
                    self.assertNotIn(f['item'], reply)                      # never the platform's name for it
                    self.assertNotIn(f['reason'], reply)
                shown = FW.unique(blocked)[:FW.MAX_SHOWN]
                for f in shown:
                    self.assertIn(FW.words(f['item'], lang)['next'], reply)  # each finding carries its next action
                if lang != 'en':
                    self.assertNotRegex(reply, '[A-Za-z]{3,}')

    def test_more_findings_than_three_are_counted_not_listed(self):
        many = [{'item': i} for i in ('publishing', 'registries', 'code-writing model', 'images')]
        self.assertIn('1', FW.reply(many, 'en').splitlines()[-1][-40:])
        self.assertEqual(FW.reply(many, 'en').count('Something you asked'), 1)

    def test_several_open_questions_are_one_sentence(self):
        qs = [{'item': 'unresolved requirement', 'reason': 'Does it need sign-in?'},
              {'item': 'unresolved requirement', 'reason': 'Will it store personal details?'}]
        self.assertEqual(FW.reply(qs, 'en').count('still unclear'), 1)

    def test_the_answer_to_can_you_add_x_is_in_the_customers_language_in_all_three(self):
        sup = self.supervisor()
        for lang, message, script in (('he', 'אפשר להוסיף תשלומים?', HEBREW), ('ar', 'can you add payments?', ARABIC),
                                      ('en', 'can you add payments?', None)):
            sup.turn(project_id=f'p_{lang}', account_id='a', message='אתר לעסק שלי, קוראים לו קפה נועה, בחיפה', lang=lang)
            reply = sup.turn(project_id=f'p_{lang}', account_id='a', message=message, lang=lang).reply
            with self.subTest(lang=lang):
                self.assertIn(FW.words('integration: payments', lang)['next'], reply)
                self.assertNotIn('integration', reply)
                self.assertNotIn('is NOT_IMPLEMENTED', reply)
                if script:
                    self.assertRegex(reply, script)
                    self.assertNotRegex(reply, '[A-Za-z]{3,}')

    def test_the_reply_to_approve_before_it_is_ready_names_no_item(self):
        sup = self.supervisor()
        sup.turn(project_id='p_ar', account_id='a', message='אתר לעסק שלי, קוראים לו קפה נועה, בחיפה', lang='ar')
        reply = sup.turn(project_id='p_ar', account_id='a', message='approve, start building', lang='ar').reply
        self.assertNotIn('unresolved requirement', reply)
        self.assertIn(FW.words('unresolved requirement', 'ar')['next'], reply)
        self.assertEqual(reply.count(FW.words('unresolved requirement', 'ar')['what']), 1)


class TheScreenGetsTheWords(unittest.TestCase):
    def test_the_plan_view_carries_the_words_of_every_finding_in_three_languages(self):
        import dataclasses
        from omni_prod import discovery as D
        from omni_prod.conversation.supervisor import _plan_view
        from omni_prod.planning.architect import ChiefArchitect
        base = C.from_brief(D.start('אתר לעסק שלי, קוראים לו קפה נועה, בחיפה'))
        plan = ChiefArchitect().plan(dataclasses.replace(base, product_family='mobile_app'))
        findings = _plan_view(plan)['feasibility']['findings']
        self.assertTrue(findings)
        for f in findings:
            self.assertEqual(sorted(f['words']), sorted(FW.LANGS))
            for lang in FW.LANGS:
                self.assertTrue(all(f['words'][lang][k] for k in ('what', 'why', 'next')))
        self.assertNotIn('words', plan['feasibility']['findings'][0])      # the stored plan (and its fingerprint) is untouched

    def test_the_blocker_the_workspace_reads_carries_the_words_too(self):
        src = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        self.assertIn("'findings': FW.attach(findings)", src)

    def test_the_screen_shows_the_words_and_never_the_item_or_the_reason(self):
        app = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        block = app[app.index('function capabilityBlockMessage'):app.index('const TT = {')]
        self.assertNotIn('x.item', block)
        self.assertNotIn('x.reason', block)
        self.assertNotIn("'Edit the requirement or contact support", app)
        arch = app[app.index('function renderArch()'):app.index('// 2026-11-14 (Michael b2)')]
        self.assertIn('ownerView() ? h(', arch)                             # the technical lines are the owner's alone
        self.assertNotIn("S.lang==='he'?'פרטים טכניים':'Technical details'", app)

    def test_the_three_languages_have_the_same_screen_keys(self):
        app = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        for key in ('findingGeneralWhat', 'findingGeneralWhy', 'findingGeneralNext', 'buildNotStarted', 'requirementsInvalid'):
            self.assertEqual(len(re.findall(rf'\b{key}:', app)), 3, key)

    def test_the_screens_general_sentence_is_the_servers_general_sentence(self):
        app = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        for lang in FW.LANGS:
            what, why, nxt = getattr(FW.GENERAL, lang)
            for part in (what, why, nxt):
                self.assertIn(part, app, (lang, part))


class TheRealAdmissionAnswerCarriesTheWords(unittest.TestCase):
    """2026-11-27: tests/customer_flow_browser.cjs failed in CI on a 409 it had hand-written ({item: 'sign-in (roles)'}, no
    `words`) -- a body the real server never sends. The producer-side walk above (every `Finding(` has an entry) cannot see
    that: it proves the table is complete, not that every answer which carries findings to a customer went through
    FW.attach, nor that a test of the screen feeds it what the server really sends. These two do."""

    def test_the_real_gate_refuses_a_request_with_words_on_every_finding_in_the_409_and_in_the_blocker(self):
        import json
        import subprocess
        import sys
        try:
            import fastapi  # noqa: F401
        except ModuleNotFoundError:
            self.skipTest('needs fastapi (CI)')
        out = subprocess.run([sys.executable, str(ROOT / 'tests' / 'customer_flow_409_fixture.py')], cwd=ROOT,
                             capture_output=True, text=True, check=True, timeout=120).stdout
        got = json.loads(out)
        for where, findings in (('409 detail', got['detail']['findings']), ('blocker', got['blocker']['findings'])):
            self.assertTrue(findings, where)
            for f in findings:
                self.assertEqual(sorted(f.get('words') or {}), sorted(FW.LANGS), (where, f['item']))
                for lang in FW.LANGS:
                    self.assertTrue(all(f['words'][lang][k] for k in ('what', 'why', 'next')), (where, f['item'], lang))
        by_item = {f['item']: f for f in got['detail']['findings']}
        # the finding of the failing flow: sign-in with roles is worded in Hebrew as the sign-in entry, by the table's own key
        self.assertIn('התחברות והרשאות', by_item['sign-in (roles)']['words']['he']['what'])
        self.assertIn('יומן', by_item['integration: calendar']['words']['he']['what'])

    def test_a_browser_test_never_hand_writes_a_finding_the_server_would_send(self):
        hand_written = re.compile(r"findings\s*:\s*\[\s*\{[^}]*\bitem\s*:")
        offenders = [p.name for p in sorted((ROOT / 'tests').glob('*.cjs'))
                     if hand_written.search(p.read_text(encoding='utf-8'))]
        self.assertEqual(offenders, [], 'a finding in a mocked answer must come from the real functions '
                                        '(tests/customer_flow_409_fixture.py, tests/feasibility_words_fixture.py)')

    def test_the_customer_flow_browser_test_takes_its_409_from_the_real_gate(self):
        text = (ROOT / 'tests' / 'customer_flow_browser.cjs').read_text(encoding='utf-8')
        self.assertIn('customer_flow_409_fixture.py', text)
        self.assertIn('body:JSON.stringify({detail:GATE.detail})', text)
        self.assertIn('blockers:blockedBuild?[GATE.blocker]:[]', text)


class TheBrowserTestIsRunInCi(unittest.TestCase):
    def test_it_is_syntax_checked_and_run_beside_the_other_browser_suites(self):
        ci = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
        self.assertIn('node --check tests/feasibility_words_browser.cjs', ci)
        self.assertIn('      - run: node tests/feasibility_words_browser.cjs\n        timeout-minutes: 3\n', ci)

    def test_it_names_the_mutations_it_must_fail_under_and_bounds_every_wait(self):
        text = (ROOT / 'tests' / 'feasibility_words_browser.cjs').read_text(encoding='utf-8')
        for what in ('the finding is printed as the gate wrote it', 'the words ignore the customer',
                     'a customer sees the technical lines', 'a finding several checks share is listed each time',
                     'a finding with no words says its item', 'the blocker sentence is the server'):
            self.assertIn(what, text)
        self.assertIn('assert.equal(APP.split(from).length, 2', text)
        self.assertIn('WATCHDOG_MS', text)
        self.assertIn('setDefaultTimeout', text)
        self.assertNotIn('waitForTimeout', text)                           # no unbounded or fixed sleep: every wait is a bounded condition


class TheCountPerRoute(unittest.TestCase):
    def test_the_platform_words_in_every_customer_route_are_counted_and_the_count_is_zero(self):
        counts = {path: len(CW.scan(path, root=ROOT)) for path in CW.CUSTOMER_TEXT}
        for path, n in sorted(counts.items()):
            print(f'::notice title=customer words::{path}: {n} platform word(s)')
        self.assertEqual({p: n for p, n in counts.items() if n}, {})
        self.assertEqual(CW.route_counts(root=ROOT)['total'], 0)


if __name__ == '__main__':
    unittest.main()

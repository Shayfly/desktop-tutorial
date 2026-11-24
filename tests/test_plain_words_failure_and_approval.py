"""Plain words on two routes (owner 2026-11-21): a build that fails (audit route 4) and the approval texts (route 2).

The owner's first metric is how many technical terms a customer must know to start and finish; the target is zero. The
audit of origin/main a77c1b85 found the failure screen and the approval texts naming the machinery (spec, verifier,
credits, repair rounds, providers, check names) and printing raw error text, with no next step.

What is checked here, on the real path:
  * app.js is read as shipped; its own string tables and its own functions (friendlyError, failureView, ownerTech,
    ownerView, explain, notRunLine, stopReasonLine) are executed in node -- no browser.
  * the Python message builders are called (approval_flow.range_line / budget_lines / text, build_announcement.message_for,
    build_readiness.primary_blocker, the supervisor's own text table).
  * /api/v28/me is asked through the real FastAPI app.

For every customer-facing text in scope: none of FORBIDDEN (defined once, below) appears; each failure message names its
one next action by the name of a button that exists; an unknown failure code gives the default line and never the raw
text; "you were not charged" is said only when the build's record says so; the approve button has one name and the
sentences that refer to it use it; the technical block is the owner account's only.

NOT covered here, said in the open: image_mismatch still quotes what was asked and what the image shows (Michael
2026-11-15) -- that quoted text is model output and is not checked against FORBIDDEN. Nothing here renders a page.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path
from unittest import mock

from omni_prod import build_announcement as BA
from omni_prod import build_readiness as BR
from omni_prod.conversation import supervisor as SUP
from omni_prod.intake import approval_flow as AF

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'omni_prod' / 'assets' / 'app.js'
LANGS = ('he', 'en')

# ---------------------------------------------------------------- the forbidden list, defined once
_HE = r'(?<![א-ת])'          # a Hebrew word boundary: "קודם" is not "קוד", "מספיק" is not "ספק"
FORBIDDEN = [re.compile(p, re.I) for p in (
    r'סבב(י)? (ה)?תיקון', r'מפרט', r'מאמת', r'קרדיט', r'מסלול', r'תקציב', r'אפיון', r'תמחור', r'מכסה', r'פלטפורמה',
    r'ספריי?ה', r'לשונית', r'תשתית', _HE + r'[בלמה]?ספק(י|ים)?(?![א-ת])', _HE + r'[בלמה]?מודל(ים)?(?![א-ת])',
    _HE + r'[בלמה]?שרת(?![א-ת])', _HE + r'[בלמה]?קוד(?![א-ת])', r'בדיקת (דפדפן|התנהגות)', r'סקירת איכות', r'רף האיכות',
    r'הפעלת ניסיון',
    r'\bcredits?\b', r'\bspec\b', r'\bspecification\b', r'\bverifier\b', r'\bproviders?\b', r'\bmodels?\b',
    r'\brepair rounds?\b', r'\bquota\b', r'\bserver\b', r'\bbudget\b', r'\bgates?\b', r'\bidempotency\b', r'\bAI\b',
    r'\bbld_\w+',                                   # a raw build id
    r'\b[45]\d\d\b',                                # an HTTP status code
    r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b',           # a snake_case code
    r'Traceback|Exception|Error\b',                 # raw exception text
)]
LATIN_WORD = re.compile(r'[A-Za-z]{3,}')            # in a Hebrew text every Latin word is a leak, except the product's name
RAW = 'KeyError: boom_sentinel Traceback route openai-gpt-6-luna HTTP 502 for bld_9f8e7d6c'
RAWS = (RAW,
        'AI provider quota/credits unavailable: openai-gpt-6-luna; ' + RAW,
        'missing from the customer: phone, fax_number ' + RAW,
        'generated interface is empty; missing: form,button ' + RAW,
        'all model routes failed: route does not fit the remaining budget ' + RAW)
# #486 gives the four former unknown failure codes their own messages; setUpClass covers all table keys.
# Keep genuinely unknown codes and the missing-code case on the default-line and raw-text checks.
UNKNOWN_CODES = ('gate_escalation', 'a_code_nobody_wrote_words_for', None)


def offences(text: str, lang: str) -> list[str]:
    found = [p.pattern for p in FORBIDDEN if p.search(text)]
    if lang == 'he':
        found += [w for w in LATIN_WORD.findall(text.replace('148AI', ''))]
    return found


# ---------------------------------------------------------------- app.js, executed as shipped
def _source() -> str:
    return APP.read_text(encoding='utf-8')


def _fn(source: str, name: str) -> str:
    found = re.search(r'^(?:async )?function ' + name + r'\(.*?\n\}', source, re.S | re.M)
    assert found, f'app.js has no function {name}'
    return found.group()


def _const(source: str, name: str) -> str:
    found = re.search(r'^const ' + name + r' = .*;$', source, re.M)
    assert found, f'app.js has no const {name}'
    return found.group()


def run_js(expression: str, *, lang: str = 'he', me=None):
    """Evaluate `expression` against app.js's own tables and functions. `me` is what /api/v28/me returned."""
    source = _source()
    tables = source[source.index('const T ='):source.index('const S =')]
    assigns = '\n'.join(re.findall(r'^Object\.assign\(T\.(?:he|en), \{.*?\}\);$', source, re.S | re.M))
    parts = [tables, f'const S = {{lang: {json.dumps(lang)}, me: {json.dumps(me)}, signedIn: true}};', assigns,
             'function t(k) { return T[S.lang][k]; }',
             re.search(r'^class ApiError extends Error \{.*?\n\}', source, re.S | re.M).group(),
             *(_const(source, c) for c in ('NOT_CHARGED_BILLING', 'NOT_CHARGED_CODES', 'CHARGE_UNKNOWN_CODES', 'FAIL_ACTION')),
             *(_fn(source, f) for f in ('notRunLine', 'stopReasonLine', 'friendlyError', 'ownerView', 'failureView',
                                        'ownerTech', 'requestEditLabel', 'explain')),
             f'console.log(JSON.stringify({expression}));']
    # the code goes in on stdin: with the Arabic dictionary app.js's tables passed 128 KB, the limit of one argv string
    done = subprocess.run(['node', '-'], input='\n'.join(parts), capture_output=True, text=True, timeout=50)
    assert done.returncode == 0, done.stderr[-1500:]
    return json.loads(done.stdout)


def failed(code, raw=RAW, **evidence):
    return {'status': 'failed', 'error_code': code, 'error_message': raw, 'repair_rounds': 2,
            'evidence': {'repair_stop_reason': 'no_progress_same_failure',
                         'quality_report': {'not_run': [{'check': 'browser_flow'}, {'check': 'a_new_check'}]}, **evidence}}


CUSTOMER = {'id': 'usr_customer', 'email': 'c@example.com', 'is_founder': False}
OWNER = {'id': 'usr_owner', 'email': 'o@example.com', 'is_founder': True}
needs_node = unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js')


@needs_node
class AFailedBuildInTheCustomersWords(unittest.TestCase):
    """Rows 4.1-4.16, 4.21: what happened, in one plain sentence; then the money; then the one action."""

    @classmethod
    def setUpClass(cls):
        cls.codes = {lang: run_js('Object.keys(T[S.lang].errCodes)', lang=lang) for lang in LANGS}
        cls.labels = {lang: run_js('({retry: t("actRetryBuild"), edit: t("editAll")})', lang=lang) for lang in LANGS}
        builds = [failed(c, raw, billing='released') for c in [*cls.codes['he'], *UNKNOWN_CODES] for raw in RAWS]
        cls.builds = builds
        cls.views = {lang: run_js(f'{json.dumps(builds, ensure_ascii=False)}.map(failureView)', lang=lang, me=CUSTOMER)
                     for lang in LANGS}

    def test_both_languages_have_words_for_the_same_codes(self):
        self.assertEqual(sorted(self.codes['he']), sorted(self.codes['en']))
        self.assertGreaterEqual(len(self.codes['he']), 20, self.codes['he'])

    def test_no_technical_term_and_no_raw_text_reaches_the_customer(self):
        for lang in LANGS:
            for build, view in zip(self.builds, self.views[lang]):
                if build['error_code'] == 'image_mismatch':
                    continue                       # quotes the request and the image by an earlier decision; see the docstring
                with self.subTest(lang=lang, code=build['error_code'], raw=build['error_message'][:30]):
                    self.assertEqual(offences(view['text'], lang), [], view['text'])
                    for leak in ('boom_sentinel', 'openai', 'fax_number', str(build['error_code'])):
                        self.assertNotIn(leak, view['text'])

    def test_every_failure_message_names_one_next_action_that_has_a_button(self):
        for lang in LANGS:
            for build, view in zip(self.builds, self.views[lang]):
                with self.subTest(lang=lang, code=build['error_code']):
                    self.assertIn(view['action'], ('retry', 'edit', 'input'))
                    self.assertEqual(view['label'], self.labels[lang]['retry' if view['action'] == 'retry' else 'edit'])
                    self.assertTrue(view['text'].rstrip().endswith(f'"{view["label"]}".'), view['text'])
                    self.assertEqual(view['text'].count('"' + view['label'] + '"'), 1, view['text'])

    def test_a_missing_detail_is_named_in_words_and_sends_the_customer_to_the_request(self):
        view = run_js(f'failureView({json.dumps(failed("needs_customer_input", RAWS[2]))})', me=CUSTOMER)
        self.assertEqual(view['action'], 'input')
        self.assertIn('(מספר הטלפון)', view['text'])           # the detail the table knows; the unknown key is not printed
        self.assertTrue(view['text'].endswith('לחצו על "עריכת הבקשה".'), view['text'])

    def test_an_unknown_failure_code_gets_the_default_line_and_never_the_raw_text(self):
        for lang, default, action in (('he', 'הבנייה לא הצליחה בגלל תקלה אצלנו.', 'אפשר לנסות שוב: לחצו על "לנסות לבנות שוב".'),
                                      ('en', 'The build did not succeed because of a problem on our side.',
                                       'You can try again: press "Try building again".')):
            for code in UNKNOWN_CODES:
                with self.subTest(lang=lang, code=code):
                    build = failed(code)
                    self.assertEqual(run_js(f'friendlyError({json.dumps(build)})', lang=lang, me=CUSTOMER), default)
                    self.assertEqual(run_js(f'failureView({json.dumps(build)}).text', lang=lang, me=CUSTOMER),
                                     f'{default} {action}')

    def test_not_charged_is_said_only_when_the_builds_record_says_so(self):
        said = {'he': 'לא חויבתם.', 'en': 'You were not charged.'}
        cases = [(failed('verification_failed', billing='released'), True),
                 (failed('worker_lost', billing='exposure_checked_release'), True),      # maintenance.reap_build
                 (failed('worker_lost'), True),                                          # maintenance.run_once: released, no evidence
                 (failed('build_not_found'), True), (failed('preview_no_build_queue'), True),
                 (failed('verification_failed'), False),                                 # no record: nothing is promised
                 (failed('verification_failed', billing='settled'), False),
                 (failed('worker_lost', billing='held'), False),
                 (failed('provider_liability_unknown'), False),
                 (failed('provider_liability_unknown', billing='released'), False),   # "not known yet" is never followed by "not charged"
                 (failed('a_code_nobody_wrote_words_for'), False)]
        for lang in LANGS:
            views = run_js(f'{json.dumps([b for b, _ in cases])}.map(failureView)', lang=lang, me=CUSTOMER)
            for (build, expected), view in zip(cases, views):
                with self.subTest(lang=lang, code=build['error_code'], billing=build['evidence'].get('billing')):
                    self.assertIs(view['notCharged'], expected)
                    self.assertEqual(said[lang] in view['text'], expected, view['text'])

    def test_the_failure_tables_themselves_carry_no_technical_term(self):
        for lang in LANGS:
            texts = run_js('[...Object.values(T[S.lang].errCodes), t("failUnknown"), t("failNotCharged"), t("uiEmpty"), '
                           't("uiMissingLead"), t("uiEmptyTail"), ...Object.values(t("uiMissing")), '
                           '...Object.values(t("failMissing")), ...Object.values(t("failNext")).map(f => f("X"))]', lang=lang)
            for text in texts:
                with self.subTest(lang=lang, text=text[:40]):
                    self.assertEqual(offences(text.replace('"X"', ''), lang), [], text)


@needs_node
class TheTechnicalBlockIsTheOwnersOnly(unittest.TestCase):
    """Rows 4.17-4.20: the checks that did not run, why the repair stopped and the raw message -- owner account only."""

    def test_a_customer_gets_no_technical_block(self):
        build = json.dumps(failed('verification_failed'))
        for me in (CUSTOMER, None, {}, {'id': 'u', 'is_founder': 'true'}, {'id': 'u', 'is_founder': 1},
                   {'id': 'u', 'is_founder': None}):
            with self.subTest(me=me):
                self.assertIs(run_js('ownerView()', me=me), False)
                self.assertIsNone(run_js(f'ownerTech({build})', me=me))

    def test_the_owner_still_reads_every_technical_detail(self):
        tech = run_js(f'ownerTech({json.dumps(failed("verification_failed"))})', me=OWNER)
        self.assertEqual(tech['raw'], 'verification_failed: ' + RAW)
        self.assertEqual(len(tech['lines']), 2, tech)
        self.assertIn('בדיקת דפדפן', tech['lines'][0])           # warehouse 104: the checks that did not run, by name
        self.assertIn('a_new_check', tech['lines'][0])
        self.assertIn('התיקון האוטומטי נעצר', tech['lines'][1])  # warehouse 102: why the repair stopped

    def test_the_failed_branch_of_the_build_screen_prints_technical_text_only_through_the_owner_gate(self):
        source = _source()
        start = source.index("else if (status === 'failed') {\n    // Plain words")
        branch = source[start:source.index("  else msg.textContent = '';", start)]
        self.assertIn('const tech = ownerTech(b);', branch)
        self.assertIn('msg.replaceChildren(fv.text);', branch)
        for raw in ('error_message', 'error_code', 'notRunLine', 'stopReasonLine', 'repair_stop_reason', 'techDetails'):
            self.assertNotIn(raw, branch, raw)
        self.assertEqual(branch.count('if (tech)'), 1)

    def test_the_chat_status_line_says_the_plain_sentence(self):
        self.assertIn("st === 'failed' ? friendlyError(S.build) :", _source())


class TheServerSaysWhoTheOwnerIs(unittest.TestCase):
    """The flag the gate reads: /api/v28/me carries is_founder, from the one existing founder check."""

    def test_me_says_is_founder_only_for_the_founder_account(self):
        from fastapi.testclient import TestClient
        from omni_prod import investor_app
        client = TestClient(investor_app.app)
        registered = client.post('/api/v28/auth/register',
                                 json={'email': f'plain-{uuid.uuid4().hex[:10]}@example.com', 'password': 'correct-horse-battery'})
        self.assertEqual(registered.status_code, 200, registered.text)
        auth = {'Authorization': 'Bearer ' + registered.json()['token']}
        me = client.get('/api/v28/me', headers=auth)
        self.assertEqual(me.status_code, 200, me.text)
        self.assertIs(me.json()['is_founder'], False)             # an ordinary customer
        with mock.patch.dict(os.environ, {'OMNI_FOUNDER_ACCOUNT_IDS': f"usr_other, {me.json()['id']}"}):
            self.assertIs(client.get('/api/v28/me', headers=auth).json()['is_founder'], True)
        self.assertIs(client.get('/api/v28/me', headers=auth).json()['is_founder'], False)


class OneNameForEveryButtonTheTextsReferTo(unittest.TestCase):
    """Row 2.11: three names for the approve button became one, and the sentences use the button's own words."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('node'):
            raise unittest.SkipTest('node is required to read app.js tables')
        keys = ('approveBuild', 'propApprove', 'confirm', 'actApprove', 'actApproveSpec', 'editAll', 'actRetryBuild',
                'b_spec_not_approved', 'b_plan_not_verified', 'b_brief_stale')
        cls.ui = {lang: run_js(f'Object.fromEntries({json.dumps(keys)}.map(k => [k, t(k)]))', lang=lang) for lang in LANGS}

    def test_the_approve_button_has_one_name_everywhere(self):
        for lang in LANGS:
            names = {self.ui[lang][k] for k in ('approveBuild', 'propApprove', 'confirm', 'actApprove')}
            self.assertEqual(names, {AF.APPROVE_BUTTON[lang]}, lang)

    def test_the_sentences_that_send_the_customer_to_approve_use_that_name(self):
        for lang in LANGS:
            quoted = f'"{AF.APPROVE_BUTTON[lang]}"'
            for text in (AF.text(lang)['gate2'], SUP._TXT[lang]['approve'], SUP._TXT[lang]['ready_again']):
                self.assertIn(quoted, text)
        for old in ('אשרו את התקציב', 'אישור והתחלת בנייה', 'אשר והתחל בנייה', 'אשר ובנה', 'approve the budget'):
            for lang in LANGS:
                self.assertNotIn(old, json.dumps([AF.TEXT[lang], {k: v for k, v in SUP._TXT[lang].items() if isinstance(v, str)},
                                                  self.ui[lang]], ensure_ascii=False))

    def test_the_confirm_edit_and_retry_buttons_are_named_the_same_in_the_text_and_on_the_screen(self):
        for lang in LANGS:
            self.assertEqual(self.ui[lang]['actApproveSpec'], AF.CONFIRM_BUTTON[lang])
            self.assertEqual(self.ui[lang]['editAll'], AF.EDIT_BUTTON[lang])
            self.assertEqual(self.ui[lang]['editAll'], BA.EDIT_BUTTON[lang])
            self.assertEqual(self.ui[lang]['actRetryBuild'], BA.RETRY_BUTTON[lang])
            confirm = f'"{AF.CONFIRM_BUTTON[lang]}"'
            for text in (AF.text(lang)['gate1'], self.ui[lang]['b_spec_not_approved'], self.ui[lang]['b_plan_not_verified'],
                         self.ui[lang]['b_brief_stale'],
                         *(BR.primary_blocker({'blockers': [{'code': c}]}, lang)['next']
                           for c in ('spec_not_approved', 'plan_not_verified', 'brief_stale'))):
                self.assertIn(confirm, text)
            edit = f'"{AF.EDIT_BUTTON[lang]}"'
            self.assertIn(edit, AF.text(lang)['refused'])
            self.assertIn(edit, SUP._TXT[lang]['limit_incomplete_any'])


class TheApprovalTextsInPlainWords(unittest.TestCase):
    """Rows 2.6-2.10, 2.21, 2.28, 2.30: the server's own builders, called."""

    VERIFIER_RAW = 'requirements_fingerprint differs; field:auth_mode not carried by agent.plan_verifier'

    def _clean(self, text, lang):
        self.assertEqual(offences(text, lang), [], text)

    def test_every_approval_sentence_is_free_of_the_machinerys_names(self):
        sample = dict(summary='אתר לקפה שכונתי', c=3, lo=2, hi=5, exact=7, d=2, cx='HIGH_COMPLEXITY', what=self.VERIFIER_RAW)
        for lang in LANGS:
            for key, template in AF.TEXT[lang].items():
                with self.subTest(lang=lang, key=key):
                    said = template.format(**{**sample, 'summary': sample['summary'] if lang == 'he' else 'a site for a cafe'})
                    self._clean(said, lang)
                    self.assertNotIn('HIGH_COMPLEXITY', said)          # row 2.10: the raw complexity value
                    self.assertNotIn('plan_verifier', said)            # rows 2.7, 2.8: the verifier's raw problem list

    def test_the_price_lines_the_customer_reads(self):
        for lang in LANGS:
            lines = [AF.range_line(lang, 3, 3), AF.range_line(lang, 2, 5),
                     *AF.budget_lines(AF.compare((2, 5), None), lang, 'HIGH_COMPLEXITY'),
                     *AF.budget_lines(AF.compare((3, 3), 3), lang, 'HIGH_COMPLEXITY'),
                     *AF.budget_lines(AF.compare((2, 5), 7), lang, 'HIGH_COMPLEXITY'),
                     *AF.budget_lines(AF.compare((2, 5), 1), lang, 'HIGH_COMPLEXITY'),
                     SUP._TXT[lang]['cost'].format(credits=3, cap='2.00'), SUP._TXT[lang]['cost_unknown']]
            self.assertEqual(len(lines), 10)
            for line in lines:
                with self.subTest(lang=lang, line=line[:40]):
                    self._clean(line, lang)
                    self.assertNotIn('HIGH_COMPLEXITY', line)
                    self.assertNotIn('$', line)                        # row 2.30: no model spending cap in dollars
                    self.assertNotIn('2.00', line)

    def test_a_refused_plan_says_what_happened_the_money_and_what_to_do(self):
        he = AF.text('he')['refused'].format(what=self.VERIFIER_RAW)
        self.assertEqual(he, 'לא הצלחתי להכין תוכנית שמתאימה למה שביקשתם. לא חויבתם. כתבו שוב במשפט אחד מה הכי חשוב '
                             'לכם, או לחצו על "עריכת הבקשה".')
        self.assertIn('You were not charged.', AF.text('en')['refused'].format(what=self.VERIFIER_RAW))

    def test_the_supervisors_sentences_in_scope(self):
        for lang in LANGS:
            for key in ('ready_again', 'limit_incomplete_any', 'approve', 'cost_unknown'):
                with self.subTest(lang=lang, key=key):
                    self._clean(SUP._TXT[lang][key], lang)

    def test_a_blocked_build_says_whose_side_it_is_on_and_what_to_do(self):
        codes = ('spec_not_approved', 'plan_not_verified', 'brief_stale', 'approval_state_unavailable',
                 'durable_backend_not_configured', 'infrastructure_database_NOT_CONFIGURED', 'image_provider_NOT_CONFIGURED')
        for lang in LANGS:
            for code in codes:
                with self.subTest(lang=lang, code=code):
                    reason = BR.primary_blocker({'blockers': [{'code': code}]}, lang)
                    self._clean(reason['message'], lang)
                    self._clean(reason['next'], lang)
                    self.assertTrue(reason['next'].strip())              # a stop without an action is a wall
        for code in codes[4:]:                                           # row 2.21: no "server operator" to turn to
            self.assertEqual(BR.primary_blocker({'blockers': [{'code': code}]}, 'he')['next'], 'נסו שוב מאוחר יותר.')
            self.assertNotIn('operator', BR.primary_blocker({'blockers': [{'code': code}]}, 'en')['next'])

    def test_the_failure_said_in_the_conversation(self):
        for lang in LANGS:
            for code, action, label in (('verification_failed', 'retry_build', BA.RETRY_BUTTON[lang]),
                                        ('a_code_nobody_wrote_words_for', 'retry_build', BA.RETRY_BUTTON[lang]),
                                        ('needs_customer_input', 'edit_requirements', BA.EDIT_BUTTON[lang])):
                for billing in ('released', 'settled', None):
                    with self.subTest(lang=lang, code=code, billing=billing):
                        msg = BA.message_for(build_id='bld_1', error_code=code, billing=billing, lang=lang)
                        self._clean(msg['content'], lang)
                        self.assertTrue(msg['content'].endswith(f'"{label}".'), msg['content'])
                        self.assertEqual([a['type'] for a in msg['interpretation']['actions']], [action])
                        said = BA.TEXT[lang]['refunded'] in msg['content']
                        self.assertEqual(said, billing == 'released')
        self.assertEqual(BA.message_for(build_id='bld_1', error_code='verification_failed', billing='released')['content'],
                         'לא הצלחנו לבנות את האתר הפעם. לא חויבתם. אפשר לנסות שוב: לחצו על "לנסות לבנות שוב".')


@needs_node
class TheApprovalScreenInPlainWords(unittest.TestCase):
    """Rows 2.16, 2.18, 2.19, 2.31: app.js's own strings and its own explain()."""

    def test_the_price_block_and_the_blocked_texts(self):
        for lang in LANGS:
            texts = run_js('[t("creditsRequired"), t("creditsRemaining"), t("quoteStatus"), t("st_UNKNOWN"), t("quoteMissingTitle"), '
                           't("quoteUnverified"), t("b_cost_quote_unknown"), t("b_spec_not_approved"), t("b_plan_not_verified"), '
                           't("b_approval_state_unavailable"), t("b_brief_stale"), t("actApproveSpec"), t("approveBuild"), '
                           't("readinessBlockedHelp")(requestEditLabel({brief_revision: 3})), '
                           't("quoteMissingHelp")(requestEditLabel({})), ...Object.values(t("serverSaid"))]', lang=lang)
            self.assertEqual(len(texts), 19)
            for text in texts:
                with self.subTest(lang=lang, text=text[:40]):
                    self.assertEqual(offences(text, lang), [], text)

    def test_the_blocked_help_names_the_button_that_is_on_the_screen(self):
        got = run_js('[t("readinessBlockedHelp")(requestEditLabel({brief_revision: 3})), t("updateRequest"), '
                     't("quoteMissingHelp")(requestEditLabel({})), t("editRequest")]')
        self.assertIn(f'"{got[1]}"', got[0])
        self.assertIn(f'"{got[3]}"', got[2])
        source = _source()
        self.assertIn("p.blocked_reason.next : t('readinessBlockedHelp')(requestEditLabel(p))", source)
        self.assertIn("else $('chatInput').focus(); } }, requestEditLabel(p))));", source)   # the button itself

    def test_the_servers_english_sentences_are_answered_in_the_customers_language(self):
        server = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        sentences = {'build_contract_invalid': 'This plan can no longer be used. Request the plan again.',
                     'empty_message': 'The message is empty: write something, choose an answer or attach an image.',
                     'idempotency_conflict': 'This idempotency key was already used for a different build request or quote.',
                     'approval_required': 'Approve the summary and plan first.',
                     'brief_stale': 'The request was changed elsewhere. Reload to continue.'}
        for code, sentence in sentences.items():                       # the server still says exactly this, under this code
            self.assertRegex(server, r"'error': '" + code + r"',[^}]*?'message':\s*'" + re.escape(sentence) + "'")
        for lang in LANGS:
            for code, sentence in sentences.items():
                status = 422 if code == 'empty_message' else 409
                shown = run_js(f'explain(new ApiError({status}, {json.dumps({"error": code, "message": sentence})}))', lang=lang)
                with self.subTest(lang=lang, code=code):
                    self.assertTrue(shown and shown != sentence, shown)
                    self.assertEqual(offences(shown, lang), [], shown)
                    table = 't("b_brief_stale")' if code == 'brief_stale' else f't("serverSaid")[{json.dumps(code)}]'
                    self.assertEqual(shown, run_js(table, lang=lang))


if __name__ == '__main__':
    unittest.main()

"""S6.3 slice 4: the direction sketch's card (omni_prod/assets/app.js and app.css), what can be checked without a browser,
and the browser test's place in CI. tests/direction_sketch_browser.cjs is the behaviour proof in real Chromium; this file keeps
the static facts it relies on: the bounds, the sandbox, no approval of its own, the three languages, the CI lines.

The card is warehouse item 124's card (a card in the conversation with a phone / desktop switch, not a separate screen): one
card component, here for the sketch, which a build can feed later."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
CSS = (ROOT / 'omni_prod' / 'assets' / 'app.css').read_text(encoding='utf-8')
CI = (ROOT / '.github' / 'workflows' / 'v24-ci.yml').read_text(encoding='utf-8')
KEYS = ('sketchTitle', 'sketchDraft', 'sketchFrameTitle', 'sketchColours', 'sketchFonts', 'sketchSections', 'sketchLoading',
        'sketchWordsPending', 'sketchWordsWritten', 'sketchWordsPlaceholders', 'sketchWordsLate', 'sketchError', 'sketchOld',
        'sketchNote', 'sketchPay', 'sketchNoCredits', 'sketchPriceChanged')


def block(name: str) -> str:
    """The source of one top-level function of app.js."""
    start = APP.index(f'function {name}(') if f'function {name}(' in APP else APP.index(f'async function {name}(')
    return APP[start:APP.index('\n}\n', start) + 3]


class TheCardIsBounded(unittest.TestCase):
    def test_the_poll_has_a_bound_and_a_period(self):
        self.assertIn('const SKETCH_POLL_MS = 2000, SKETCH_POLL_MAX = 60;', APP)
        self.assertIn('st.polls < SKETCH_POLL_MAX', block('scheduleSketchPoll'))
        self.assertIn('st.polls += 1', block('pollSketch'))

    def test_the_sketch_is_asked_for_once_per_offer(self):
        self.assertIn('if (st.id || st.creating || st.error) return;', block('ensureSketch'))
        self.assertEqual(APP.count("method: 'POST', body: { brief_revision: a.brief_revision }"), 1)

    def test_only_the_current_sketch_asks_and_earlier_ones_hold_no_frame(self):
        chat = block('renderChat')
        self.assertIn('const currentSketch = sketchFps[sketchFps.length - 1];', chat)
        self.assertIn('if (current) ensureSketch(a);', chat)
        card = block('sketchCard')
        self.assertLess(card.index('if (!current)'), card.index('iframe'))


class ThePriceOfNewWords(unittest.TestCase):
    def test_the_button_sends_the_price_it_shows_and_nothing_else_is_charged_by_the_card(self):
        pay = block('payForSketchWords')
        self.assertIn("body: { brief_revision: a.brief_revision, price_ack: st.view.price.credits }", pay)
        self.assertIn('if (st.paying || !st.view || !st.view.price) return;', pay)
        self.assertEqual(APP.count('price_ack:'), 1)

    def test_a_refusal_is_said_in_words(self):
        pay = block('payForSketchWords')
        self.assertIn("e.status === 402 ? t('sketchNoCredits')", pay)
        self.assertIn("'price_changed'", pay)

    def test_the_button_shows_only_while_the_words_are_missing_and_priced(self):
        update = block('updateSketchDom')
        self.assertIn("['structure', 'failed'].includes(st.view.state)", update)
        self.assertIn('n.pay.hidden = !priced;', update)

    def test_the_hebrew_text_says_the_customers_word_for_a_credit_never_the_platforms(self):
        # the owner's dictionary (omni_prod/customer_words.py, warehouse 132): a customer hears "an amount from your balance"
        start = APP.index('sketchTitle:')
        he = APP[start:APP.index('\n', APP.index('sketchNote:', start))]        # the Hebrew lines of the card
        self.assertNotIn('קרדיט', he)

    def test_the_note_says_what_is_free_and_what_costs_a_credit(self):
        self.assertIn('שינוי צבע, גופן או סדר חינם; ניסוח חדש עולה יחידה אחת מהיתרה שלכם', APP)


class TheFrameIsSandboxed(unittest.TestCase):
    def test_the_frame_has_an_empty_sandbox_a_title_and_the_sketch_page_as_its_source(self):
        card = block('sketchCard')
        self.assertIn("sandbox: ''", card)
        self.assertNotIn('allow-', card)
        self.assertIn("title: t('sketchFrameTitle')", card)
        self.assertRegex(card, r"src: `/api/v28/projects/\$\{pid\(\)\}/sketches/\$\{encodeURIComponent\(st\.id\)\}/page\?v=")
        self.assertNotIn('srcdoc', card)

    def test_the_card_has_no_approval_of_its_own(self):
        source = block('sketchCard') + block('updateSketchDom') + block('ensureSketch') + block('pollSketch')
        for forbidden in ('sendChat', 'approve', 'confirmBtn', 'spec-approval', '/builds', '/approvals'):
            self.assertNotIn(forbidden, source, forbidden)

    def test_a_swatch_is_coloured_through_the_cssom_never_an_inline_style_attribute(self):
        rows = block('sketchSummaryRows')
        self.assertIn("sw.style.setProperty('background', c);", rows)
        self.assertNotIn("style:", rows)
        self.assertNotIn("'style'", rows)


class TheTexts(unittest.TestCase):
    def test_every_key_is_in_hebrew_english_and_arabic(self):
        # tests/test_i18n_contract.py holds the three tables to the same keys; here each sketch key is in all three, once each
        for key in KEYS:
            self.assertEqual(len(re.findall(rf"(?m)^  {key}:|, {key}:", APP)), 3, key)
        heads = [m.start() for m in re.finditer(r"  sketchTitle:", APP)]
        self.assertEqual(len(heads), 3)
        self.assertIn('סקיצת כיוון', APP[heads[0]:heads[0] + 40])
        self.assertIn('Direction sketch', APP[heads[1]:heads[1] + 40])
        self.assertIn('رسم الاتجاه', APP[heads[2]:heads[2] + 40])

    def test_the_state_of_the_words_is_said_in_words_and_the_draft_is_named(self):
        he = APP[APP.index('sketchTitle:'):APP.index('sketchNote:')]
        for fragment in ('טיוטה', 'מקום שמור', 'נכתבו', 'בדרך', 'הניסוח הסופי נכתב בבנייה'):
            self.assertIn(fragment, he, fragment)

    def test_the_note_says_nothing_is_built_or_charged(self):
        self.assertRegex(APP, r"sketchNote: '[^']*שום דבר לא נבנה ושום חיוב לא קורה")


class TheLayout(unittest.TestCase):
    def test_the_switch_buttons_are_44_pixels_and_the_frame_does_not_scroll_the_page(self):
        self.assertRegex(CSS, r'\.sketchTools button\{min-height:44px;min-width:44px;')
        self.assertIn('.sketchFrame.phone{width:390px;max-width:100%}', CSS)
        self.assertIn('.sketchFrame{border:0;', CSS)

    def test_no_inline_style_is_needed_by_the_app_csp(self):
        # the app's CSP is style-src 'self' with no inline styles; the card's own styles are in app.css
        self.assertNotRegex(block('sketchCard'), r"style\s*:")


class TheBrowserTestIsRunInCi(unittest.TestCase):
    def test_it_is_syntax_checked_and_run_beside_the_other_browser_suites(self):
        self.assertIn('node --check tests/direction_sketch_browser.cjs', CI)
        self.assertIn('      - run: node tests/direction_sketch_browser.cjs\n', CI)

    def test_it_names_the_mutations_it_must_fail_under(self):
        text = (ROOT / 'tests' / 'direction_sketch_browser.cjs').read_text(encoding='utf-8')
        for what in ('the draft pill is taken out', 'the frame is not sandboxed',
                     'the card waits for the words before it shows the frame', 'the create call is made on every render',
                     'the state says nothing in text'):
            self.assertIn(what, text)
        self.assertIn('assert.equal(APP.split(from).length, 2', text)


class TheFixtureIsTheServersOwn(unittest.TestCase):
    def test_the_fixture_is_built_by_the_real_service_functions(self):
        out = subprocess.run(['python3', str(ROOT / 'tests' / 'direction_sketch_fixture.py')], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout
        data = json.loads(out)
        self.assertEqual({k for k in data if isinstance(data[k], dict)}, {'pending', 'written', 'failed'})
        self.assertEqual([data[k]['view']['state'] for k in ('pending', 'written', 'failed')], ['pending', 'written', 'failed'])
        for name in ('pending', 'written'):
            self.assertIn('draft-ribbon', data[name]['page'])
        self.assertIn('כאן תופיע', data['pending']['page'])
        self.assertNotIn('כאן תופיע', data['written']['page'])
        self.assertIn('תספורת שמתאימה לכם', data['written']['page'])
        self.assertIsNotNone(re.fullmatch(r'[0-9a-f]{64}', data['direction_fp']))


if __name__ == '__main__':
    unittest.main()

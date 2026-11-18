"""The proposal card in the app (app.js): the price line is an estimate, always; one button approves THIS spec and
starts the build; edits and undo go through the proposal API. Run in node where it computes; source checks where the
wiring is the point."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'
SRC = APP.read_text()


def js(expr, lang='he'):
    fn = re.search(r'function proposalPrice\(.*?\n\}', SRC, re.S).group()
    code = (SRC[SRC.index('const T ='):SRC.index('const S =')] + f'\nconst S={{lang:{json.dumps(lang)}}};\n'
            'function t(k){return T[S.lang][k];}\n' + fn + f'\nconsole.log(JSON.stringify({expr}));')
    return json.loads(subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True).stdout)


@unittest.skipUnless(shutil.which('node'), 'node runs app.js')
class ThePriceLine(unittest.TestCase):
    def test_the_butcher_price_is_an_estimate(self):
        out = js("proposalPrice({amount_ils: 189, basis: '6 × 25₪ + 39₪ מדיה'})")
        self.assertEqual(out, {'amount': '189 ₪', 'label': 'הערכה', 'basis': '6 × 25₪ + 39₪ מדיה'})
        self.assertEqual(js("proposalPrice({amount_ils: 399})", 'en')['label'], 'estimate')

    def test_no_number_no_line(self):
        self.assertIsNone(js('proposalPrice(null)'))
        self.assertIsNone(js("proposalPrice({amount_ils: '189'})"))


class TheWiring(unittest.TestCase):
    def test_one_button_approves_the_spec_by_fingerprint_and_starts_the_build(self):
        fn = re.search(r'async function approveAndBuild\(.*?\n\}', SRC, re.S).group()
        self.assertIn('approveFromChat(', fn)
        self.assertIn('brief_fingerprint: pr.brief_fingerprint', fn)
        shared = re.search(r'async function approveFromChat\(.*?\n\}', SRC, re.S).group()
        self.assertLess(shared.index('/spec-approval'), shared.index('await startBuild('))
        self.assertIn('plan.brief_revision !== brief.revision', shared)

    def test_edits_and_undo_go_through_the_proposal_api_and_refresh_the_plan(self):
        for name, path in (('proposalEdit', '/edit'), ('proposalUndo', '/undo')):
            fn = re.search(r'async function %s\(.*?\n\}' % name, SRC, re.S).group()
            self.assertIn(f'`${{proposalPath()}}{path}`', fn)
            self.assertIn('S.plan = null; await requestBriefPlan(true);', fn)   # a new fingerprint means a new plan

    def test_the_card_is_first_in_the_plan_tab_and_withheld_when_the_editor_blocks(self):
        self.assertIn("    ...proposalCard(),\n    h('h2', {}, t('planTitle')),", SRC)
        card = re.search(r'function proposalCard\(.*?\n\}', SRC, re.S).group()
        self.assertIn("if (!pr.ok || !pr.cards) return [h('section', { class: 'proposal pending' }", card)


if __name__ == '__main__':
    unittest.main()

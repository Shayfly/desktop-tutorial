"""Owner 2026-11-16: the customer approval screen for windows. Each window is offered with a one-sentence benefit; the
customer approves or rejects it.

Acceptance: a rejected window is not built; an approved one enters the fact canon; the gate fails a build missing an
approved window.

Real path: the ConversationSupervisor with the deterministic interpreter (the in-memory stores stand in for SQL only)
up to gate 1, its approve_spec action, approve_spec with the customer's decisions, the saved brief's
requirements_text -> fact_canon.build_canon, window_catalog.install on the real AutonomousProductEngine, and app.js's
own windowsChoice() in a real Chromium page.
"""
from __future__ import annotations

import json
import os
import re
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import discovery as d
from omni_prod import window_catalog as W
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.conversation.store import MemoryConversationStore
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.fact_canon import build_canon
from tests.test_conversation_os import MemoryBriefs
from tests.test_missing_needed_facts import WITH_FACTS
from tests.test_window_catalog import AGE, COOKIES, POPUP, _Arch, _Gen, _Rep, _Sandbox, page

APP = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'
WINE_SHOP = 'חנות יין אונליין עם מבצעים, קטגוריות ומשלוחים'
DECISIONS = {'age_gate': True, 'cookie_banner': True, 'entry_popup': False, 'promo_bar': False}


def at_gate_1():
    s = ConversationSupervisor(briefs=MemoryBriefs(), store=MemoryConversationStore())
    say = lambda **kw: s.turn(project_id='p', account_id='a', lang='he', **kw)
    with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
        t = say(message=WITH_FACTS)
        for _ in range(8):
            if not t.questions:
                break
            q = t.questions[0]
            t = say(answers={q.id: {'content_only': 'yes', 'personal_data': 'no'}.get(
                q.id, q.recommended or q.options[0].value)})
    [action] = [a for a in t.actions if a['type'] == 'approve_spec']
    return s, action


def approve(s, action, windows):
    with mock.patch.dict(os.environ, {'OMNI_INTAKE_MODEL': '0'}):
        return s.approve_spec(project_id='p', account_id='a', brief_fingerprint=action['brief_fingerprint'], lang='he',
                              windows=windows)


class TheOffer(unittest.TestCase):
    def test_every_window_has_one_sentence_of_benefit_in_both_languages(self):
        self.assertEqual(set(W.BENEFITS), set(W.CATALOG))
        for wid, (he, en) in W.BENEFITS.items():
            with self.subTest(wid):
                for text in (he, en):
                    self.assertTrue(text.endswith('.'))
                    self.assertEqual(text.count('.'), 1)          # one sentence
                    self.assertLessEqual(len(text), 120)

    def test_gate_1_offers_the_windows_that_fit_with_their_benefit_and_no_decision_yet(self):
        # the owner 2026-11-19: a cafe is not offered a cart, an age gate or filter chips -- only what fits it
        _, action = at_gate_1()
        offer = action['windows']
        self.assertEqual([w['id'] for w in offer], ['cookie_banner', 'question_widget'])
        cookies = offer[0]
        self.assertEqual((cookies['label'], cookies['benefit'], cookies['state']),
                         ('הודעת עוגיות', W.BENEFITS['cookie_banner'][0], None))

    def test_a_product_that_is_not_a_website_is_offered_no_windows(self):
        self.assertEqual(d.window_offer(d.start('אפליקציה לניהול תורים למספרה עם התחברות')), [])


class TheCustomersDecision(unittest.TestCase):
    def setUp(self):
        self.s, action = at_gate_1()
        self.turn = approve(self.s, action, DECISIONS)
        self.row = self.s.briefs.latest('p')
        self.prompt = self.row.brief.prompt + '\n' + d.requirements_text(self.row.brief)

    def test_the_approval_binds_to_the_spec_with_the_windows(self):
        last = [m for m in self.s.store.messages_for('p') if m['role'] == 'customer'][-1]
        self.assertEqual(last['interpretation'].get('spec_approved'), self.row.fingerprint)
        self.assertEqual((d.approved_windows(self.row.brief), d.rejected_windows(self.row.brief)),
                         (['age_gate', 'cookie_banner'], ['entry_popup', 'promo_bar']))

    def test_an_approved_window_enters_the_fact_canon_and_a_rejected_one_does_not(self):
        self.assertEqual(build_canon(self.prompt).values('window'), {'age_gate', 'cookie_banner'})

    def test_a_rejected_window_is_not_built(self):
        self.assertEqual(W.approved_in_prompt(self.prompt), ['age_gate', 'cookie_banner'])
        self.assertEqual(W.rejected_in_prompt(self.prompt), ['entry_popup', 'promo_bar'])
        self.assertNotIn('- entry_popup (', self.prompt)                    # no spec for it reaches the generator
        engine = AutonomousProductEngine(architect=_Arch(), generator=_Gen(page(AGE, COOKIES, POPUP.replace(
            ' role="dialog" aria-modal="true"', ' hidden role="dialog" aria-modal="true"'))),
            repairer=_Rep(page(AGE, COOKIES)), executor=_Sandbox(), max_repair_rounds=2)
        W.install(engine, prompt=self.prompt)
        result = engine.build(self.prompt)
        first = engine.repairer.failures[0]
        self.assertEqual([f['acceptance_id'] for f in first], ['window-entry_popup'])
        self.assertIn('WINDOW_REJECTED', first[0]['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))   # the repair removes it

    def test_the_gate_fails_a_build_missing_an_approved_window(self):
        engine = AutonomousProductEngine(architect=_Arch(), generator=_Gen(page(COOKIES)), repairer=_Rep(page(COOKIES)),
                                         executor=_Sandbox(), max_repair_rounds=1)
        W.install(engine, prompt=self.prompt)
        result = engine.build(self.prompt)
        self.assertEqual(result.status, 'failed')
        self.assertIn('WINDOW_MISSING', engine.repairer.failures[0][0]['message'])

    def test_the_next_offer_shows_the_decisions(self):
        states = {w['id']: w['state'] for w in d.window_offer(self.row.brief)}
        self.assertEqual({k: v for k, v in states.items() if v}, {'age_gate': 'approved', 'cookie_banner': 'approved',
                                                                  'entry_popup': 'rejected', 'promo_bar': 'rejected'})

    def test_changing_a_decision_moves_the_window(self):
        brief = d.Brief.from_dict(json.loads(json.dumps(self.row.brief.to_dict())))
        self.assertTrue(d.decide_windows(brief, {'entry_popup': True, 'age_gate': False}))
        self.assertEqual(d.approved_windows(brief), ['cookie_banner', 'entry_popup'])
        self.assertEqual(d.rejected_windows(brief), ['age_gate', 'promo_bar'])
        self.assertFalse(d.decide_windows(brief, {'entry_popup': True}))     # no change, no new revision


class NothingIsGuessed(unittest.TestCase):
    def test_an_unknown_window_or_a_non_boolean_decision_raises(self):
        brief = d.start(WITH_FACTS)
        with self.assertRaises(KeyError):
            d.decide_windows(brief, {'popunder': True})
        with self.assertRaises(ValueError):
            d.decide_windows(brief, {'age_gate': 'yes'})

    def test_the_api_refuses_an_unknown_window_out_loud(self):
        src = (Path(__file__).resolve().parents[1] / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        fn = src[src.index('class V28SpecApproval'):src.index('class V28AttachmentUpload')]
        self.assertIn('windows: dict[str, bool] | None', fn)
        self.assertIn("'error': 'unknown_window'", src)
        self.assertIn('windows=req.windows', src)


def _ui_page():
    src = APP.read_text(encoding='utf-8')
    translations = src[src.index('const T ='):src.index('const S =')]
    h = re.search(r'function h\(.*?\n\}', src, re.S).group()
    choice = re.search(r'function windowsChoice\(.*?\n\}', src, re.S).group()
    return translations, h, choice


class TheScreen(unittest.TestCase):
    """app.js's own windowsChoice() and h() in a real Chromium page."""

    def test_the_screen_shows_every_window_with_its_benefit_and_a_row_click_ticks_it(self):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:  # pragma: no cover
            self.skipTest('playwright is required to run app.js in a browser')
        translations, h, choice = _ui_page()
        offer = W.offer('he', text=WINE_SHOP)                    # a shop that sells wine: every window fits
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.set_content('<html lang="he" dir="rtl"><body><div id="root"></div></body></html>')
            pg.add_style_tag(content=APP.with_name('app.css').read_text(encoding='utf-8'))   # the real stylesheet
            pg.add_script_tag(content=translations + "\nconst S={lang:'he'};\nfunction t(k){return T[S.lang][k];}\n" + h
                              + '\n' + choice + f'\nwindow.W = windowsChoice({json.dumps(offer, ensure_ascii=False)});'
                              '\ndocument.getElementById("root").append(W.node);')
            self.assertEqual(pg.locator('.windowOpt').count(), len(W.CATALOG))
            self.assertIn(W.BENEFITS['age_gate'][0], pg.locator('.windowOpt[data-window="age_gate"]').inner_text())
            self.assertIn('חלון שלא מסומן לא ייבנה', pg.locator('.windowsChoice').inner_text())
            self.assertGreaterEqual(pg.locator('.windowOpt').first.bounding_box()['height'], 44)
            pg.locator('.windowOpt[data-window="age_gate"]').click()          # the whole row is the target
            ticked = pg.evaluate("[...document.querySelectorAll('.windowOpt input')].map(i => i.checked)")
            b.close()
        # the click on the row ticks its box (read()'s content is checked in node, where CI can run it)
        self.assertEqual(ticked, [w == 'age_gate' for w in W.CATALOG])

    def test_read_sends_every_window_ticked_or_not_in_node(self):
        """The same app.js windowsChoice() and h() in node with a minimal DOM (CI has node but no browser): an offer
        with one approved window, one more ticked, the rest left as they are -- read() sends all 8, true or false."""
        import shutil
        import subprocess
        if not shutil.which('node'):  # pragma: no cover
            self.skipTest('node runs app.js')
        translations, h, choice = _ui_page()
        offer = W.offer('he', approved=['age_gate'])
        dom = ("class El{constructor(t){this.nodeType=1;this.tagName=t;this.attrs={};this.children=[];this.checked=false}"
               "setAttribute(k,v){this.attrs[k]=v;if(k==='checked')this.checked=true}append(...k){this.children.push(...k)}"
               "addEventListener(){}set className(v){this.attrs.class=v}}\n"
               "const document={createElement:t=>new El(t)};\n"
               "function inputs(n,out=[]){if(n&&n.tagName==='input')out.push(n);for(const c of (n&&n.children)||[])inputs(c,out);return out;}\n")
        js = (dom + translations + "\nconst S={lang:'he'};\nfunction t(k){return T[S.lang][k];}\n" + h + '\n' + choice +
              f'\nconst W = windowsChoice({json.dumps(offer, ensure_ascii=False)});'
              "\nfor (const i of inputs(W.node)) if (i.attrs['data-window'] === 'cookie_banner') i.checked = true;"
              '\nconsole.log(JSON.stringify({sent: W.read(), rows: inputs(W.node).length}));')
        out = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
        self.assertEqual(out['rows'], len(W.CATALOG))
        self.assertEqual(out['sent'], {w: w in ('age_gate', 'cookie_banner') for w in W.CATALOG})

    def test_both_approval_screens_send_the_decisions(self):
        src = APP.read_text(encoding='utf-8')
        self.assertIn('windows: wins.read() }', src)                                    # the chat's approve card
        self.assertIn('windows: S.proposalWindows ? S.proposalWindows.read() : undefined', src)   # the proposal card
        self.assertIn('S.proposalWindows = windowsChoice(pr.windows);', src)


if __name__ == '__main__':
    unittest.main()

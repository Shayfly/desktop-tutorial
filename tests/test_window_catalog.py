"""A2 steps 8 and 9 (owner 2026-11-15/16): the catalogue of in-page windows and the gate that holds a build to the
windows the customer approved.

Real path: the approved windows go from the brief (discovery.requirements_text) into the build prompt, from the prompt
into the fact canon (fact_canon.build_canon) and into the gate (window_catalog.install wraps the engine's executor), and
the real AutonomousProductEngine fails a build whose page lacks an approved window, then passes once a repair adds it.
The generator, the repairer and the sandbox are fakes (no model, no Docker); the gate and the engine are not.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from omni_prod import discovery as d
from omni_prod import window_catalog as W
from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.fact_canon import build_canon
from omni_prod.repository_patch import parse_patch

OWNER_LIST = ('mega_menu', 'age_gate', 'cookie_banner', 'entry_popup', 'cart_drawer', 'promo_bar', 'chips',
              'question_widget')
JS = "document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); if (e.key === 'Tab') trap(e); });"


def page(*windows, rtl=True, extra=''):
    body = ''.join(windows)
    return (f'<!doctype html><html lang="he"{" dir=\"rtl\"" if rtl else ""}><body>{body}<main>האטליז</main>{extra}'
            f'<script>{JS}</script></body></html>')


AGE = ('<div data-148-window="age_gate" role="dialog" aria-modal="true" aria-label="אישור גיל">'
       '<button>אני מעל 18</button><button>יציאה</button></div>')
COOKIES = ('<div data-148-window="cookie_banner" hidden>עוגיות <button data-148-close>סגירה</button></div>')
POPUP = ('<div data-148-window="entry_popup" role="dialog" aria-modal="true" aria-label="מבצע">10% הנחה '
         '<button data-148-close>סגירה</button></div>')


def brief_with(windows, source='answer'):
    b = d.start('אתר לאטליז, טלפון 0504000162')
    b.fields['windows'] = {'value': list(windows), 'source': source, 'question_id': 'windows', 'confidence': 'confirmed'}
    return b


class TheCatalogue(unittest.TestCase):
    def test_the_owners_windows_each_with_its_spec(self):
        self.assertEqual(set(W.CATALOG), set(OWNER_LIST))
        for w in W.CATALOG.values():
            with self.subTest(w.id):
                text = ' '.join(w.spec)
                self.assertIn('44', text)                       # a finger-size button
                self.assertIn('rtl', text)
                if w.modal:
                    self.assertIn('aria-modal', text)
                    self.assertIn('Focus', text)
        self.assertIn('Escape does NOT dismiss', ' '.join(W.CATALOG['age_gate'].spec))
        self.assertIn('BEFORE the cookie banner', ' '.join(W.CATALOG['age_gate'].spec))

    def test_an_unknown_window_raises(self):
        with self.assertRaises(KeyError):
            W.prompt_lines(['popunder'])
        with self.assertRaises(KeyError):
            d.approved_windows(brief_with(['popunder']))


class FromTheBriefToThePromptAndTheCanon(unittest.TestCase):
    def test_the_customers_approved_windows_are_written_into_the_prompt(self):
        text = d.requirements_text(brief_with(['age_gate', 'cookie_banner']))
        self.assertIn(W.APPROVED_PREFIX, text)
        self.assertIn('Escape does NOT dismiss it', text)
        self.assertIn('the age gate comes first', text)
        self.assertEqual(W.approved_in_prompt(text), ['age_gate', 'cookie_banner'])

    def test_only_the_customer_approves_a_window(self):
        for source in ('delegated', 'default', 'model'):
            with self.subTest(source):
                self.assertEqual(d.approved_windows(brief_with(['age_gate'], source)), [])
                self.assertNotIn(W.APPROVED_PREFIX, d.requirements_text(brief_with(['age_gate'], source)))

    def test_an_approved_window_is_a_fact_of_the_canon(self):
        canon = build_canon(d.requirements_text(brief_with(['age_gate', 'promo_bar'])))
        self.assertEqual(canon.values('window'), {'age_gate', 'promo_bar'})
        self.assertEqual(build_canon(d.requirements_text(brief_with([]))).values('window'), set())


class TheProbe(unittest.TestCase):
    def codes(self, html, approved, **kw):
        return [(f['code'], f['window']) for f in W.probe(html, approved, **kw)['failures']]

    def test_a_page_that_keeps_the_rules_passes(self):
        self.assertEqual(self.codes(page(AGE, COOKIES), ['age_gate', 'cookie_banner']), [])

    def test_an_approved_window_missing_from_the_page_fails(self):
        self.assertEqual(self.codes(page(COOKIES), ['age_gate', 'cookie_banner']), [('WINDOW_MISSING', 'age_gate')])

    def test_a_modal_without_dialog_semantics_fails(self):
        bad = AGE.replace(' role="dialog" aria-modal="true"', '')
        self.assertIn(('WINDOW_RULE', 'age_gate'), self.codes(page(bad), ['age_gate']))

    def test_cookies_before_the_age_gate_fail(self):
        self.assertIn(('WINDOW_ORDER', 'age_gate'), self.codes(page(COOKIES, AGE), ['age_gate', 'cookie_banner']))

    def test_two_windows_open_at_once_fail(self):
        self.assertIn('WINDOW_TWO_OPEN', [c for c, _ in self.codes(page(AGE, POPUP), ['age_gate', 'entry_popup'])])

    def test_no_escape_handling_fails_a_closable_modal_but_not_the_age_gate(self):
        no_esc = page(POPUP).replace("if (e.key === 'Escape') close(); ", '')
        self.assertIn(('WINDOW_RULE', 'entry_popup'), self.codes(no_esc, ['entry_popup']))
        self.assertEqual(self.codes(page(AGE).replace("if (e.key === 'Escape') close(); ", ''), ['age_gate']), [])

    def test_a_hebrew_page_without_rtl_fails(self):
        self.assertIn(('WINDOW_RULE', '*'), self.codes(page(AGE, rtl=False), ['age_gate']))

    def test_a_closable_window_without_a_close_button_fails(self):
        self.assertIn(('WINDOW_RULE', 'cookie_banner'),
                      self.codes(page(AGE, COOKIES.replace(' data-148-close', '')), ['age_gate', 'cookie_banner']))

    def test_the_probe_says_what_it_checked(self):
        checked = W.probe(page(AGE, COOKIES), ['age_gate', 'cookie_banner'])['checked']
        self.assertIn('order: age gate before cookies', checked)
        self.assertIn('at most one modal window open on load', checked)


class _Arch:
    def create_spec(self, prompt):
        return SimpleNamespace(acceptance=(SimpleNamespace(id='A1', text='the shop page'),), requirements=())


class _Gen:
    def __init__(self, html):
        self.html = html

    def generate(self, spec):
        return parse_patch({'files': [{'path': 'index.html', 'content': self.html}]})


class _Rep:
    def __init__(self, html):
        self.html, self.failures = html, []

    def repair(self, *, spec, repo_summary, failures):
        self.failures.append(failures)
        return parse_patch({'files': [{'path': 'index.html', 'content': self.html}]})


class _Sandbox:
    def execute(self, *, repository, spec):
        return ExecutionReport(True, (), 'sandbox ok', tests_executed=1)


class TheGateHoldsTheBuild(unittest.TestCase):
    def test_a_build_without_the_approved_age_gate_fails_and_a_repair_that_adds_it_passes(self):
        prompt = 'אתר לאטליז' + d.requirements_text(brief_with(['age_gate', 'cookie_banner']))
        rep = _Rep(page(AGE, COOKIES))
        engine = AutonomousProductEngine(architect=_Arch(), generator=_Gen(page(COOKIES)), repairer=rep,
                                         executor=_Sandbox(), max_repair_rounds=2)
        self.assertEqual(W.install(engine, prompt=prompt), ['age_gate', 'cookie_banner'])
        result = engine.build(prompt)
        first = rep.failures[0]
        self.assertEqual([f['acceptance_id'] for f in first], ['window-age_gate'])
        self.assertIn('WINDOW_MISSING', first[0]['message'])
        self.assertEqual((result.status, result.repair_rounds), ('ready', 1))

    def test_a_build_with_no_approved_window_is_not_gated(self):
        engine = SimpleNamespace(executor=_Sandbox())
        self.assertEqual(W.install(engine, prompt='אתר לאטליז' + d.requirements_text(brief_with([]))), [])
        self.assertIsInstance(engine.executor, _Sandbox)

    def test_the_worker_installs_the_gate(self):
        import inspect
        from omni_prod import worker_tasks
        src = inspect.getsource(worker_tasks._run_live_build_job)
        self.assertIn('install_window_gate(engine, prompt=build_prompt)', src)


if __name__ == '__main__':
    unittest.main()

"""An element parked off-screen on the side a page scrolls to (bld_cb2d1b90a90f430c98603d14f8afa1a8, 2026-11-24).

Every round of the owner's build failed the layout check with "page width 11439px > viewport 1440px" -- the width of
one element at left:-9999px on a right-to-left page (tests/test_visual_qa.py reproduces the three production numbers
in a real browser). Now (omni_prod/offscreen.py):
  * the consistency gate blocks it, with file:line and the platform's visually-hidden rule as the fix;
  * the worker's repository transform rewrites the hiding idiom itself to that rule after generation and every repair,
    so a generated page with it is verified -- and stored -- without it;
  * the generator is given the rule.
Real path for the worker: the worker job (BuildHarness) with the real engine on the production chain, its generator
writing a right-to-left page with the idiom.
"""
from __future__ import annotations

import json
import unittest

from omni_prod import consistency_gate, offscreen
from omni_prod.repository_patch import FilePatch
from tests.test_kept_version_report import BuildHarness
from tests.test_repair_converge import production_engine, production_env
from tests.test_verification_group import MANIFEST


def page(direction: str, css: str, body: str = '<a class="skip-link" href="#main">דלג לתוכן</a>') -> str:
    return (f'<!DOCTYPE html><html lang="he" dir="{direction}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{margin:0}}{css}</style>'
            f'</head><body>{body}<main id="main"><h1>כותרת</h1></main></body></html>')


IDIOM = '.skip-link{position:absolute;left:-9999px;top:0}'
PAGE_PY = ('def render_page():\n'
           '    return f"""' + page('rtl', IDIOM.replace('{', '{{').replace('}', '}}')).replace('{margin:0}', '{{margin:0}}')
           + '"""\n')


def blocking(repo):
    return [f for f in consistency_gate.scan(repo).blocking if f.check == 'offscreen']


class TheGateBlocksIt(unittest.TestCase):
    def test_left_off_screen_on_a_right_to_left_page_blocks_with_its_line_and_the_fix(self):
        found = blocking({'index.html': page('rtl', '\n' + IDIOM + '\n')})
        self.assertEqual([(f.path, f.line) for f in found], [('index.html', 2)])
        self.assertIn('"left: -9999px"', found[0].message)
        self.assertIn(offscreen.VISUALLY_HIDDEN, found[0].fix)
        failure = consistency_gate.failures(consistency_gate.scan({'index.html': page('rtl', IDIOM)}))[0]
        self.assertTrue(failure.message.startswith('consistency (offscreen): index.html:1 on a right-to-left page'))

    def test_the_same_rule_on_a_left_to_right_page_is_harmless(self):
        self.assertEqual(blocking({'index.html': page('ltr', IDIOM)}), [])
        self.assertEqual(len(blocking({'index.html': page('ltr', '.skip-link{position:absolute;right:-9999px}')})), 1)

    def test_margin_and_text_indent_count_and_a_fixed_box_does_not(self):
        self.assertEqual(len(blocking({'index.html': page('rtl', '.band{margin-left:-9999px}')})), 1)
        self.assertEqual(len(blocking({'index.html': page('rtl', '.logo{text-indent:-9999px}')})), 1)
        self.assertEqual(blocking({'index.html': page('rtl', '.skip-link{position:fixed;left:-9999px}')}), [])
        self.assertEqual(blocking({'index.html': page('rtl', '.nudge{position:relative;left:-20px}')}), [])

    def test_a_stylesheet_is_read_with_the_direction_of_the_pages(self):
        repo = {'index.html': page('rtl', ''), 'static/site.css': '/* hidden */\n.sr-only{position:absolute;left:-9999px}\n'}
        self.assertEqual([(f.path, f.line) for f in blocking(repo)], [('static/site.css', 2)])


class ThePlatformRewritesTheIdiom(unittest.TestCase):
    def test_the_idiom_becomes_the_visually_hidden_rule_scoped_to_not_focused(self):
        repo, done = offscreen.rewrite({'index.html': page('rtl', IDIOM)})
        self.assertEqual(done, ['index.html:1 left -9999px'])
        self.assertNotIn('-9999px', repo['index.html'])
        self.assertIn('.skip-link:not(:focus):not(:focus-within){' + offscreen.HIDE + '}', repo['index.html'])
        self.assertEqual(blocking(repo), [])
        self.assertEqual(offscreen.rewrite(repo), (repo, []))                   # idempotent

    def test_a_python_template_keeps_compiling(self):
        repo, done = offscreen.rewrite({'page.py': PAGE_PY})
        self.assertEqual(len(done), 1)
        compile(repo['page.py'], 'page.py', 'exec')
        self.assertIn('.skip-link:not(:focus):not(:focus-within){{', repo['page.py'])
        rendered = {}
        exec(repo['page.py'], rendered)                                          # noqa: S102 -- the generated template
        self.assertIn('.skip-link:not(:focus):not(:focus-within){position:absolute!important', rendered['render_page']())

    def test_what_may_be_visible_is_left_to_the_gate(self):
        for css, body in (('.band{margin-left:-9999px;padding-left:9999px}', ''),
                          ('.logo{text-indent:-9999px;background:url(l.png)}', ''),
                          ('', '<a style="position:absolute;left:-9999px" href="#main">x</a>')):
            original = {'index.html': page('rtl', css, body or '<a class="skip-link" href="#main">x</a>')}
            self.assertEqual(offscreen.rewrite(original), (original, []), css or body)
            self.assertEqual(len(blocking(original)), 1, css or body)

    def test_the_generator_is_given_the_rule(self):
        from omni_prod.skills_runtime import ROLE_GENERATOR, guidance_for
        text = guidance_for(ROLE_GENERATOR)
        self.assertIn(offscreen.VISUALLY_HIDDEN, text)
        self.assertIn('-999px', text)


class TheWorkerRewritesBeforeVerifying(unittest.TestCase):
    """The worker job, the real engine and the production chain; the generator writes a right-to-left page with the
    idiom. The consistency gate (enabled, as in production) runs on the transformed repository."""

    @classmethod
    def setUpClass(cls):
        class Generator:
            def generate(self, spec):
                return (FilePatch('app.py', 'print("v0")\n'), FilePatch('page.py', PAGE_PY),
                        FilePatch('.omni/project.json', json.dumps(MANIFEST)))
        calls = []
        with production_env(calls):
            engine, repairer = production_engine(max_rounds=0)
            engine.generator = Generator()
            cls.harness = h = BuildHarness(verified=False)
            h.engine = engine
            h.run()
        cls.engine, cls.ev = engine, h.final['evidence_json']
        # the version round 0 verified, as the round snapshot stored it (a failed build commits no version)
        cls.stored = h.workspace._zip_repo.call_args_list[0].args[0]

    def test_the_rewrite_is_in_the_evidence_and_the_stored_page(self):
        self.assertEqual(self.ev['offscreen_rewrites'], ['page.py:2 left -9999px'])
        self.assertNotIn('left:-9999px', self.stored['page.py'])
        self.assertIn(':not(:focus):not(:focus-within){{', self.stored['page.py'])

    def test_the_consistency_gate_judged_the_rewritten_page(self):
        last = self.ev['consistency_gate']['last']
        self.assertIn('offscreen', last['checks_run'])
        self.assertTrue(last['passed'], last['blocking'])


if __name__ == '__main__':
    unittest.main()

"""SHARE failed on every production build with the rule in the spec (2026-11-19): the platform writes og:title and
og:description from the page's own title and description, like the RTL rule. Nothing is invented."""
import inspect
import os
import re
import unittest
from unittest import mock

from omni_prod import skill_units as U
from omni_prod.autonomous_core import AutonomousProductEngine
from omni_prod.share_preview import ensure_share, install, share_tags
from omni_prod.skill_units import gate as G
from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py

NO_OG = re.sub(r'<meta property="og:[^>]*>', '', BUTCHER['page'])


class ShareByConstruction(unittest.TestCase):
    def test_the_butcher_page_without_og_tags_gets_them_from_its_own_title_and_description(self):
        self.assertEqual(U.run('share_meta', NO_OG)['code'], 'SHARE_META_MISSING')
        out = ensure_share({'static/index.html': NO_OG})['static/index.html']
        self.assertEqual(U.run('share_meta', out), {'status': 'pass'})
        self.assertIn('<meta property="og:title" content="האטליז של סבא שמעון | בשר כשר וטרי בירושלים">', out)
        self.assertIn('content="האטליז של סבא שמעון - בשר בקר טרי', out)          # the meta description, as written

    def test_a_page_that_has_them_is_left_exactly_as_written(self):
        self.assertEqual(ensure_share({'index.html': BUTCHER['page']}), {'index.html': BUTCHER['page']})

    def test_no_meta_description_takes_the_first_paragraph_shortened(self):
        page = '<html><head><title>כהן ושות׳</title></head><body><p>' + 'מילה ' * 60 + '</p></body></html>'
        tag = re.search(r'og:description" content="([^"]*)"', share_tags(page)).group(1)
        self.assertLessEqual(len(tag), 160)
        self.assertTrue(tag.endswith('…'))

    def test_nothing_true_to_write_writes_nothing(self):
        self.assertEqual(share_tags('<html><head></head><body><p>x</p></body></html>'), '')    # no title
        self.assertNotIn('og:description', share_tags('<html><head><title>t</title></head><body></body></html>'))

    def test_a_python_template_is_changed_only_if_it_still_compiles(self):
        good = as_app_py(NO_OG)
        self.assertIn('og:title', ensure_share({'app.py': good})['app.py'])
        bad = 'PAGE = "<html><head><title>x</title></head><body><p>y</p></body></html>"\n'   # double-quoted string
        self.assertEqual(ensure_share({'app.py': bad}), {'app.py': bad})

    def test_tests_are_never_touched(self):
        repo = {'tests/test_site.py': as_app_py(NO_OG), 'test_page.py': as_app_py(NO_OG)}
        self.assertEqual(ensure_share(repo), repo)

    def test_a_build_whose_generator_forgot_them_passes_the_share_gate_with_no_repair(self):
        rep = _Files({'app.py': as_app_py(BUTCHER['page'])})
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(NO_OG)}), repairer=rep,
                                    executor=_Sandbox(), max_repair_rounds=2)
        with mock.patch.dict(os.environ, {'OMNI_GATE_SHARE': 'block'}):
            G.install(e, 'SHARE')
            install(e)
            result = e.build('a page')
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(rep.failures, [])

    def test_the_worker_and_the_rehearsal_install_it(self):
        from omni_prod import rehearsal, worker_tasks
        for src in (inspect.getsource(worker_tasks._run_live_build_job), inspect.getsource(rehearsal)):
            self.assertIn('install_share_preview(engine)', src)
            self.assertLess(src.index('install_page_locale(engine, prompt)'), src.index('install_share_preview(engine)'))


if __name__ == '__main__':
    unittest.main()

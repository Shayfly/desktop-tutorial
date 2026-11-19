"""A test file is never judged as a served file (production 2026-11-19, bld_59236dc6: G5 blocked the build on
tests/test_cohen_law.py, a test the builder wrote; three repair rounds could not clear it). The real gate runs."""
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod.skill_units import gate as G

IMG_TEST = 'def test_hero():\n    assert \'<img src="https://images.example.com/hero.jpg"\' in page()\n'
BROKEN = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'skill_units' / 'rights_image_source' / 'fixtures'
          / 'broken' / 'butcher_hotlinked_photo.html').read_text(encoding='utf-8')
def as_py(html):
    return 'PAGE = ' + repr(html) + '\n'


PAGE = ('<!doctype html><html dir="rtl" lang="he"><head><title>כהן ושות׳</title></head>'
        '<body><h1>כהן ושות׳</h1><p>משרד עורכי דין</p></body></html>')


class TestsAreNotServed(unittest.TestCase):
    def test_served_of_leaves_out_test_files(self):
        repo = {'app.py': 'x = 1\n', 'tests/test_cohen_law.py': IMG_TEST, 'test_app.py': IMG_TEST,
                'static/app.js': 'let a = 1;', 'static/app.test.js': 'x'}
        self.assertEqual([p for p, _ in G.served_of(repo)], ['app.py', 'static/app.js'])

    def test_g5_passes_a_page_whose_only_unknown_image_is_in_a_test(self):
        repo = {'app.py': as_py(PAGE), 'tests/test_cohen_law.py': as_py(BROKEN)}
        with mock.patch.dict(os.environ, {'OMNI_GATE_G5': 'block'}):
            self.assertEqual(G.check('G5', repo)['status'], 'pass')

    def test_g5_still_fails_the_same_image_on_a_served_file(self):
        repo = {'app.py': as_py(BROKEN)}
        with mock.patch.dict(os.environ, {'OMNI_GATE_G5': 'block'}):
            self.assertEqual(G.check('G5', repo)['status'], 'fail')


if __name__ == '__main__':
    unittest.main()

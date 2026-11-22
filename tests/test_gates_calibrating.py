"""A new gate warns until it is calibrated (the owner, 2026-11-16, rule 4), and the rehearsal runs the worker's gates.
Kept apart from tests/test_skill_gates.py so that file's negative controls keep their exact expected failures."""
import unittest

from tests.test_skill_gates import BUTCHER, _Arch, _Files, _Sandbox, as_app_py


class ANewGateWarnsUntilItIsCalibrated(unittest.TestCase):
    """The owner, 2026-11-16, rule 4: a new gate enters at warn; three builds, calibration, a proven fall on a broken
    page, and only then block."""
    def test_every_calibrating_gate_warns_by_default_and_the_proven_ones_block(self):
        import os
        from unittest import mock
        from omni_prod.skill_units import gate as G
        self.assertEqual(set(G.CALIBRATING), {'HE', 'G11', 'BRAND', 'SHARE', 'A4', 'G8', 'GAME', 'APPLE', 'PRO',
                                              'SITE_CLAIMS', 'SITE_PARITY', 'APP_STATES'})
        self.assertEqual(set(G.CALIBRATED), {'G1', 'G10', 'G5'})                  # calibrated 2026-11-19: they block
        with mock.patch.dict(os.environ, {}, clear=False):
            for gate in (*G.CALIBRATING, *G.CALIBRATED, 'G3', 'G4', 'G6'):
                os.environ.pop(f'OMNI_GATE_{gate}', None)
            for gate in G.CALIBRATING:
                self.assertEqual(G.mode(gate), 'warn', gate)
            self.assertEqual((G.mode('G3'), G.mode('G6'), G.mode('G4')), ('block', 'block', 'warn'))
            for gate in G.CALIBRATED:
                self.assertEqual(G.mode(gate), 'block', gate)

    def test_every_gate_the_worker_installs_has_a_stated_default(self):
        import re
        from pathlib import Path
        from omni_prod.skill_units import gate as G
        src = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'worker_tasks.py').read_text(encoding='utf-8')
        named = set(re.findall(r"install_skill_gate\(engine, '(\w+)'\)", src))
        loop = re.search(r"for g in \(([^)]*)\):\s*#[^\n]*\n\s*install_skill_gate\(engine, g\)", src)
        named |= set(re.findall(r"'(\w+)'", loop.group(1))) if loop else set()
        self.assertGreaterEqual(len(named), 9)
        self.assertEqual(named - set(G.DEFAULT_MODE), set())      # a gate with no stated default would block in silence
        self.assertEqual(named, set(G.WORKER_GATES))              # the rehearsal installs this list: the same gates

    def test_the_rehearsal_runs_the_gates_a_customers_build_runs(self):
        from pathlib import Path
        from types import SimpleNamespace
        from omni_prod.skill_units import gate as G
        engine = SimpleNamespace(executor=SimpleNamespace(execute=lambda **k: None))
        installed = G.install_all(engine)
        self.assertEqual(tuple(installed), G.WORKER_GATES)
        self.assertEqual(set(engine.gate_modes), set(G.WORKER_GATES))
        src = (Path(__file__).resolve().parent.parent / 'omni_prod' / 'rehearsal.py').read_text(encoding='utf-8')
        self.assertLess(src.index('install_all(engine)'), src.index('result = engine.build(prompt)'))
        self.assertIn("report['skill_gates'] = skill_gate_report(engine)", src)

    def test_a_calibrating_gate_keeps_its_findings_and_a_blocking_one_keeps_codes_only(self):
        import os
        from unittest import mock
        from omni_prod.autonomous_core import AutonomousProductEngine
        from omni_prod.skill_units import gate as G
        page = BUTCHER['page'].replace('</body>', '<p>מנה טעים</p><img src="x.png"></body>')
        e = AutonomousProductEngine(architect=_Arch(), generator=_Files({'app.py': as_app_py(page)}),
                                    repairer=_Files({'app.py': as_app_py(page)}), executor=_Sandbox(), max_repair_rounds=0)
        with mock.patch.dict(os.environ, {'OMNI_GATE_G3': 'warn'}):
            os.environ.pop('OMNI_GATE_HE', None)
            G.install(e, 'G3')
            G.install(e, 'HE')
        e.build('a page')
        rep = G.report(e)
        he = rep['HE']
        self.assertEqual((he['mode'], he['status']), ('warn', 'fail'))
        finding = he['failures'][0]['findings'][0]
        self.assertIn('מנה טעים', finding['where'] + finding['why'])
        self.assertLessEqual(len(he['failures'][0]['findings']), G.MAX_CALIBRATION_FINDINGS)
        self.assertEqual(rep['G3']['status'], 'fail')
        self.assertTrue(all('findings' not in f for f in rep['G3']['failures']))     # proven gate: codes only
        self.assertNotIn('G6', G.CALIBRATING)                                        # a secret is never copied

    def test_a_calibrating_gate_can_still_be_set_to_block(self):
        import os
        from unittest import mock
        from omni_prod.skill_units import gate as G
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'block'}):
            self.assertEqual(G.mode('HE'), 'block')


class ThePageAsServed(unittest.TestCase):
    """Calibration finding of 2026-11-17 (rehearsals 44025252867, 44025259144): a page kept as a Python template was
    read from its source, and its template fields were called placeholders and a missing business name."""
    TEMPLATE = ('<!doctype html><html lang="he" dir="rtl"><head><title>{SITE_TITLE}</title></head><body>'
                '<h1>{SITE_TITLE}</h1><main>{packages_html}</main></body></html>')
    SERVED = ('<!doctype html><html lang="he" dir="rtl"><head><title>קפה נחמה</title></head><body>'
              '<h1>קפה נחמה</h1><main><p>קפה ומאפה 28 ש"ח</p></main></body></html>')

    def repo(self):
        return {'app.py': f'PAGE = """{self.TEMPLATE}"""\n'}

    def test_from_the_source_the_template_fields_are_findings_and_from_the_served_page_they_are_not(self):
        from omni_prod.skill_units import gate as G
        self.assertEqual(G.check('G10', self.repo())['status'], 'fail')                 # what the rehearsals showed
        served = G.check('G10', self.repo(), {'/': self.SERVED})
        self.assertEqual((served['status'], served['failures']), ('pass', []))
        self.assertTrue(all('(as served)' in line for line in served['checked']))
        self.assertEqual(G.check('BRAND', self.repo(), {'/': self.SERVED})['status'], 'pass')

    def test_a_real_placeholder_on_the_served_page_is_still_found(self):
        from omni_prod.skill_units import gate as G
        bad = self.SERVED.replace('קפה ומאפה 28 ש"ח', 'Lorem ipsum dolor sit amet')
        self.assertEqual(G.check('G10', self.repo(), {'/': bad})['status'], 'fail')

    def test_the_source_is_read_when_the_served_copy_cannot_be_trusted(self):
        from omni_prod.skill_units import gate as G
        cut = self.SERVED[:-20]                                                          # no closing </html>: cut
        long = self.SERVED.replace('</main>', '<p>' + 'א' * G.SERVED_PAGE_LIMIT + '</p></main>')
        two = {**self.repo(), 'about.html': self.SERVED}
        plain = {'index.html': self.SERVED.replace('קפה ומאפה', 'Lorem ipsum dolor sit amet')}
        for repo, rendered in ((self.repo(), {'/': cut}), (self.repo(), {'/': long}), (self.repo(), None),
                               (self.repo(), {'assets': 'x'}), (two, {'/': self.SERVED})):
            self.assertFalse(any('(as served)' in line for line in G.check('G10', repo, rendered)['checked']))
        # a page that is not a template is read as written even when a served copy exists
        self.assertEqual(G.check('G10', plain, {'/': self.SERVED})['status'], 'fail')

    def test_the_gate_uses_the_served_page_of_this_round_only(self):
        from omni_prod.autonomous_core import ExecutionReport
        from omni_prod.skill_units import gate as G

        class Inner:
            last_pages = {'/': ThePageAsServed.SERVED}

            def __init__(self, passed):
                self.passed = passed

            def execute(self, *, repository, spec):
                return ExecutionReport(self.passed, (), '')
        ok = G.SkillGateExecutor(Inner(True), 'G10', 'warn')
        ok.execute(repository=self.repo(), spec=None)
        self.assertEqual(ok.last_gate['status'], 'pass')
        stale = G.SkillGateExecutor(Inner(False), 'G10', 'warn')                         # the smoke did not run this round
        stale.execute(repository=self.repo(), spec=None)
        self.assertEqual(stale.last_gate['status'], 'fail')


if __name__ == '__main__':
    unittest.main()

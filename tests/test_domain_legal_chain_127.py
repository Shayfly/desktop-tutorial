"""Warehouse 127, acceptance 6, through the REAL engine and the REAL production verification chain (the seam rule; the
harness of tests/test_site_content_engine.py: real chain, scripted model, local sandbox transport, local Chromium).

On the owner's law-firm brief (bld_b0eb47a5, read-only): the business reads the domain `lawyer`, so the build writes a
legal page and its data, the home page's footer links to it, the fixed tests the repository ships serve it, every skill
gate passes on it, and the evidence says which domain it came from. A repository that loses the page fails the chain.
"""
import json
import os
import unittest
from unittest import mock

from tests.test_site_content_engine import CHROMIUM, ENV, ScriptedGateway, build_engine, why


@unittest.skipUnless(CHROMIUM, 'the browser stages need a local Chromium (playwright)')
class TheLegalPageThroughTheRealChain(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ('OMNI_GATE_HE', 'OMNI_VISUAL_QA_ENFORCE', 'OMNI_GATE_SITE_PARITY'):
            os.environ.pop(key, None)

    def build(self):
        from omni_prod.autonomous_core import AutonomousProductEngine  # noqa: F401  (the engine is built by the harness)
        gw = ScriptedGateway()
        engine, prompt = build_engine(gw)
        result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds, result.stop_reason), ('ready', 0, 'passed'), why(result))
        return engine, result

    def test_the_build_writes_the_legal_page_links_it_and_says_where_it_came_from(self):
        from omni_prod import site_content
        from omni_prod.site_content import legal as LG
        from omni_prod.skill_units.gate import report as gate_report
        engine, result = self.build()
        repo = result.repository
        self.assertIn(LG.LEGAL_PAGE, repo)
        self.assertIn(LG.LEGAL_JSON, repo)
        self.assertIn(f'href="{LG.HREF}"', repo['public/index.html'])
        self.assertNotIn('legal.html', repo[LG.LEGAL_PAGE].replace('<a href="index.html">', ''))     # it does not link to itself
        self.assertIn('זה לא ייעוץ משפטי', repo[LG.LEGAL_PAGE])
        self.assertEqual(json.loads(repo[LG.LEGAL_JSON])['domain'], 'lawyer')
        evidence = site_content.report(engine)
        self.assertEqual(evidence['domain'], 'lawyer')                                  # slice 2: the domain it read
        self.assertEqual(evidence['legal']['page'], LG.LEGAL_PAGE)
        self.assertEqual(evidence['legal']['domain'], 'lawyer')
        self.assertEqual(evidence['legal']['groups'], ['Applies almost everywhere', 'Israel'])
        self.assertGreater(evidence['legal']['questions'], 10)
        self.assertEqual(evidence['parity']['status'], 'pass')
        self.assertNotIn('legal_findings', evidence)
        gates = gate_report(engine)
        self.assertEqual({g: v.get('status') for g, v in gates.items() if g in ('G3', 'G10', 'HE', 'PRO', 'G1', 'G5')},
                         {g: 'pass' for g in ('G3', 'G10', 'HE', 'PRO', 'G1', 'G5')})

    def test_a_repository_that_loses_the_legal_page_fails_the_chain(self):
        from omni_prod.site_content import legal as LG
        engine, result = self.build()
        # the page alone gone: the repository's own fixed test (a link and a page go together) catches it ...
        no_page = {k: v for k, v in result.repository.items() if k != LG.LEGAL_PAGE}
        report = engine.executor.execute(repository=no_page, spec=result.spec)
        self.assertFalse(report.passed)
        self.assertIn('accept-site-content', [f.acceptance_id for f in report.failures])
        # ... and the page, its data and the link all gone (the fixed test is then satisfied): the platform's own gate
        footer_link = f' · <a href="{LG.HREF}">'
        index = result.repository['public/index.html']
        start = index.index(footer_link)
        cut = index[:start] + index[index.index('</a>', start) + len('</a>'):]
        stripped = {k: v for k, v in result.repository.items() if k not in (LG.LEGAL_PAGE, LG.LEGAL_JSON)}
        stripped['public/index.html'] = cut
        report = engine.executor.execute(repository=stripped, spec=result.spec)
        self.assertFalse(report.passed)
        self.assertIn('gate-SITE_LEGAL', [f.acceptance_id for f in report.failures])


if __name__ == '__main__':
    unittest.main()

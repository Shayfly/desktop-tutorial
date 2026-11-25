"""Warehouse 126 on the real chain: a brief whose own four colours lock the design contract (source 'brief') -- so the
G-APPLE gate holds a contract too, and the content route's generator refuses to render when the gate's contract is not
the one the page is rendered with -- is built ready in round 0 with its font pair on the page, by the engine of
tests/test_site_content_engine.py: the worker's installs in the worker's order, the production verification chain, a
local sandbox transport and a scripted model (the only double). The brief is the owner's law-firm brief (a production
row read read-only, tests/fixtures/site_content_bld_b0eb47a5.json) with a four-colour palette on its Design line."""
import importlib.util
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from omni_prod import typography as T
from omni_prod.site_content import render as R

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
FOUR_COLOURS = PROMPT.replace('palette #1e3a5f, #ffffff;', 'palette #1e3a5f, #b45309, #f8fafc, #0f172a;')


class TheRealChain(unittest.TestCase):
    def test_a_brief_that_locks_its_own_contract_is_built_ready_through_the_real_chain(self):
        spec = importlib.util.spec_from_file_location('site_content_engine_harness',
                                                      ROOT / 'tests' / 'test_site_content_engine.py')
        E = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(E)
        if not E.CHROMIUM:  # pragma: no cover
            self.skipTest('the browser stages need a local Chromium (playwright)')
        from omni_prod.g_apple import report as apple_report
        with mock.patch.dict(os.environ, E.ENV), mock.patch.object(E, 'PROMPT', FOUR_COLOURS):
            for key in ('OMNI_GATE_HE', 'OMNI_VISUAL_QA_ENFORCE', 'OMNI_GATE_SITE_PARITY'):
                os.environ.pop(key, None)
            gw = E.ScriptedGateway()
            engine, prompt = E.build_engine(gw)
            result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0),
                         [f'{f.acceptance_id}: {f.message[:200]}' for f in result.report.failures])
        route = engine.core.site_route if hasattr(engine, 'core') else engine.site_route
        held = getattr(engine, 'core', engine).design_contract
        self.assertEqual((route.contract_source, held['fingerprint']), ('brief', route.contract_fp))
        self.assertIn(T.font_link(T.pair(route.font_pair)), result.repository[R.PAGE])
        # the gate judged the page statically against the route's contract and found nothing (its render test's long-
        # string findings are not about fonts; they are the same at the base commit, without this change)
        last = apple_report(engine)['last']
        self.assertEqual((last['contract'], last['static']), (route.contract_fp, []), last)


if __name__ == '__main__':
    unittest.main()

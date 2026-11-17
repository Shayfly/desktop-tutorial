"""The owner's butcher builds, 2026-11-17 (bld_6323468a, bld_c0b2b43b): rounds were verified, then no model route
answered the repair with valid JSON. The exception ended the whole build -- the verified work was thrown away and the
customer read "no check ran". Now the repair stops ('repair_model_unavailable') and the build ends on its best version
with its real checks. Real loop (AutonomousProductEngine) and the real release-gate verdict; the model and the sandbox
are fakes."""
import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.model_gateway import ModelGatewayError
from omni_prod.repository_patch import parse_patch
from omni_prod.worker_tasks import evaluate_release_gates

ROOT = Path(__file__).resolve().parents[1]
NO_ROUTE = ModelGatewayError("all model routes failed: gemini-3.8-flash: model did not return valid JSON (content "
                             "before the JSON value ...); gpt-6.1-sol: skipped (CREDIT_EXHAUSTED ...)")


def engine(repair_errors):
    class Architect:
        def create_spec(self, prompt): return 'spec'

    class Generator:
        def generate(self, spec): return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})

    class Repairer:
        def __init__(self): self.calls = 0
        def repair(self, **kw):
            self.calls += 1
            err = repair_errors.pop(0) if repair_errors else None
            if err is not None:
                raise err
            return parse_patch({'files': [{'path': 'app.py', 'content': f'v{self.calls}'}]})

    class Executor:
        def execute(self, *, repository, spec):
            return ExecutionReport(False, (AcceptanceFailure('BROWSER', f"uncaught JavaScript error in {repository['app.py']}"),))

    rep = Repairer()
    return AutonomousProductEngine(architect=Architect(), generator=Generator(), repairer=rep, executor=Executor(),
                                   max_repair_rounds=3), rep


class NoRouteAnsweredTheRepair(unittest.TestCase):
    def test_the_build_ends_on_its_verified_version_with_its_checks(self):
        eng, rep = engine([None, NO_ROUTE])                  # round 1 repaired, round 2: no route answered
        result = eng.build('p')
        self.assertEqual((result.status, result.stop_reason), ('failed', 'repair_model_unavailable'))
        self.assertEqual(result.repository['app.py'], 'v1')                     # the work of round 1 is kept
        self.assertEqual([f.acceptance_id for f in result.report.failures], ['BROWSER'])   # the real check
        self.assertIn('all model routes failed', eng.repair_model_error)

    def test_the_customer_reads_a_verification_failure_not_no_check_ran(self):
        eng, _ = engine([NO_ROUTE])
        result = eng.build('p')
        ok, code, message = evaluate_release_gates(result=result, quality=None, security=None, rights=None)
        self.assertEqual((ok, code), (False, 'verification_failed'))
        self.assertIn('stopped repairing: no model returned a valid repair', message)
        self.assertIn('BROWSER', message)

    def test_any_other_error_still_ends_the_build(self):
        eng, _ = engine([RuntimeError('a bug')])
        with self.assertRaises(RuntimeError):
            eng.build('p')
        eng, _ = engine([ModelGatewayError('budget exceeded for this build')])
        with self.assertRaises(ModelGatewayError):
            eng.build('p')

    def test_the_screen_says_why_the_repair_stopped(self):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
        self.assertEqual(len(re.findall(r"repair_model_unavailable:'", js)), 2)             # Hebrew and English


if __name__ == '__main__':
    unittest.main()

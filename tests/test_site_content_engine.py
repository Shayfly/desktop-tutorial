"""The content route through the REAL engine and the REAL production verification chain (AGENTS.md rule 2, the seam
rule; the CTO's decision 10): investor_app._verification_executor -- consistency and dependency gates, the remote
sandbox executor's own manifest handling and request policy, preview smoke, behavioural acceptance, browser probe,
visual QA, the QA review with its static truth gate, the quality gate -- then the worker's installs in the worker's
order (the request installs, every WORKER_GATES skill gate, the window, main-image, G8, A4, asset-marker and G-APPLE
gates). Two things are not production: the model gateway is scripted, and the sandbox TRANSPORT is local -- each
command really runs, in a fresh directory, in its own process group that is killed afterwards (the container ending);
the browser stages use the local Chromium. Nothing judges by a double.

  ready in round 0 on the owner's brief (bld_b0eb47a5, read-only), one content call
  a copy finding (HE, switched to block) is rewritten at that path only -- before the sandbox, and by the repairer
  a platform failure stops the build with RepairDeclined('platform_render_defect') and zero repair calls
  an advisory finding (the model reviewer, the design critic's must_fix) is recorded and never declines a build
"""
import io
import json
import os
import signal
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = json.loads((ROOT / 'tests' / 'fixtures' / 'site_content_bld_b0eb47a5.json').read_text(encoding='utf-8'))
PROMPT = FIXTURE['prompt']
CONTENT = FIXTURE['scripted_content']
BAD_PATH = 'sections.services.items[1].desc'
BAD_TEXT = 'שירות מקצועית בתלונה ובהליך המשפטי.'           # he_gender: "שירות" is masculine
GOOD_TEXT = 'ליווי מקצועי בתלונה ובהליך המשפטי.'


def chromium() -> str | None:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            path = p.chromium.executable_path
        return path if path and os.path.exists(path) else None
    except Exception:  # pragma: no cover
        return None


CHROMIUM = chromium()


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _kill_inside(tmp: str) -> None:
    for pid in os.listdir('/proc'):
        if pid.isdigit():
            try:
                if os.readlink(f'/proc/{pid}/cwd').startswith(tmp):
                    os.kill(int(pid), signal.SIGKILL)
            except OSError:
                continue


def local_urlopen(req, timeout=None):
    """The sandbox runner's /run, locally: the repository written to a fresh directory, argv run there."""
    body = json.loads(req.data.decode())
    with tempfile.TemporaryDirectory() as tmp:
        for path, text in body['repository'].items():
            target = Path(tmp) / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        env = dict(os.environ, HOME=tmp, PYTHONDONTWRITEBYTECODE='1', OMNI_CHROMIUM=CHROMIUM or '')
        proc = subprocess.Popen(body['argv'], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                env=env, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=150)
            result = {'returncode': proc.returncode, 'stdout': out, 'stderr': err}
        except subprocess.TimeoutExpired:
            result = {'returncode': 124, 'stdout': '', 'stderr': 'local sandbox: timeout'}
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            _kill_inside(tmp)
    return _Response(json.dumps(result).encode())


class ScriptedGateway:
    """The model, scripted by role (the only double). Records every call."""
    accepts_task_tag = False

    def __init__(self, *, content=None, rewrites=None, review=None):
        self.content = content if content is not None else CONTENT
        self.rewrites = list(rewrites or [])
        self.review = review if review is not None else {'findings': []}
        self.calls = []

    def complete_json(self, *, system, user, max_tokens=4096, images=(), **_):
        from omni_prod.design_review import _SYSTEM as DESIGN
        from omni_prod.product_review import _REVIEW_SYSTEM
        from omni_prod.site_content.agents import _CONTENT_REPAIR_SYSTEM, _CONTENT_SYSTEM
        role = {_CONTENT_SYSTEM: 'content', _CONTENT_REPAIR_SYSTEM: 'rewrite', _REVIEW_SYSTEM: 'review',
                DESIGN: 'design'}.get(system, 'other')
        self.calls.append((role, user))
        if role == 'content':
            return json.loads(json.dumps(self.content))
        if role == 'rewrite':
            return {'set': self.rewrites.pop(0)}
        if role == 'review':
            return self.review
        if role == 'design':
            return {'score': 60, 'summary': 'x', 'findings': [{'severity': 'must_fix', 'area': 'hierarchy',
                                                               'viewport': 'mobile', 'problem': 'The hero feels plain',
                                                               'fix': 'make the title larger'}]}
        raise AssertionError(f'an unexpected model call: {system[:80]!r}')

    def roles(self):
        return [r for r, _ in self.calls]


def build_engine(gateway, *, design_critic=False):
    """The engine a customer's build gets, in the worker's install order (worker_tasks._run_live_build_job), minus the
    installs that need the database (uploaded logo, attachments) -- none applies to this brief."""
    from omni_prod import investor_app, site_content
    from omni_prod.autonomous_agents import ArchitectAgent, GeneratorAgent, RepairAgent
    from omni_prod.autonomous_core import AutonomousProductEngine
    from omni_prod.remote_sandbox import RemoteSandboxRepositoryExecutor

    class LocalSandbox(RemoteSandboxRepositoryExecutor):
        def __init__(self, config, **_):
            super().__init__(config, urlopen=local_urlopen)

    with mock.patch.object(investor_app, 'RemoteSandboxRepositoryExecutor', LocalSandbox):
        executor = investor_app._verification_executor(gateway)
    engine = AutonomousProductEngine(architect=ArchitectAgent(gateway), generator=GeneratorAgent(gateway),
                                     repairer=RepairAgent(gateway), executor=executor, max_repair_rounds=6,
                                     repair_ceiling=6)
    engine.no_progress_retries = 1
    request = {'user_id': 'usr_owner_test'}
    site_content.install(engine, prompt=PROMPT, gateway=gateway, request=request, year='2026')
    from omni_prod.page_locale import install as install_page_locale
    install_page_locale(engine, PROMPT)
    from omni_prod.share_preview import install as install_share_preview
    install_share_preview(engine)
    from omni_prod.product_review import install_review_request
    install_review_request(engine, PROMPT)
    from omni_prod.fact_canon import install_facts
    install_facts(engine, PROMPT)
    from omni_prod.page_outline import install as install_page_outline
    install_page_outline(engine, PROMPT)
    from omni_prod.worker_tasks import _install_agentic_repair, set_acceptance_scope
    with mock.patch.dict(os.environ, {'OMNI_AGENTIC_REPAIR': 'all'}):
        assert _install_agentic_repair(engine, request) is False          # never on this route
    if design_critic:
        from omni_prod.behavior_acceptance import find_in_chain
        from omni_prod.design_review import DesignCritic
        from omni_prod.visual_qa import VisualQAExecutor
        find_in_chain(engine.executor, VisualQAExecutor).design_critic = DesignCritic(gateway, request_text=PROMPT)
    from omni_prod.product_architect import ProductArchitect
    set_acceptance_scope(engine, ProductArchitect().compile(PROMPT, project_id='t', contract_version=1).to_dict())
    from omni_prod.window_catalog import install as install_window_gate
    install_window_gate(engine, prompt=PROMPT)
    from omni_prod.skill_units.gate import WORKER_GATES, carry_rules
    from omni_prod.skill_units.gate import install as install_skill_gate
    for g in WORKER_GATES:
        install_skill_gate(engine, g)
    carry_rules(engine, WORKER_GATES)
    from omni_prod.uploaded_assets import install_main_image
    build_prompt = install_main_image(engine, prompt=PROMPT, pool=None, store=None, project_id=None, account_id='x')
    from omni_prod.runtime_load import install as install_runtime_load
    install_runtime_load(engine)
    from omni_prod.a4 import install as install_asset_plan
    build_prompt = install_asset_plan(engine, prompt=build_prompt)
    from omni_prod.asset_markers import install as install_asset_marker_gate
    install_asset_marker_gate(engine)
    from omni_prod.g_apple import install as install_apple_gate
    build_prompt = install_apple_gate(engine, prompt=build_prompt, gateway=None)
    from omni_prod.fact_canon import needs_customer_input
    engine.missing_input = lambda messages: needs_customer_input(messages, build_prompt)
    return engine, build_prompt


ENV = {'OMNI_SANDBOX_RUNNER_URL': 'http://local-sandbox.invalid', 'OMNI_SANDBOX_SHARED_SECRET': 'l' * 40,
       'OMNI_SITE_LIBRARY': 'on'}


@unittest.skipUnless(CHROMIUM, 'the browser stages need a local Chromium (playwright)')
class TheRouteThroughTheRealChain(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ('OMNI_GATE_HE', 'OMNI_VISUAL_QA_ENFORCE', 'OMNI_GATE_SITE_PARITY'):
            os.environ.pop(key, None)

    def test_ready_in_round_0_with_one_content_call(self):
        from omni_prod import site_content
        from omni_prod.site_content import render as R
        from omni_prod.skill_units.gate import report as gate_report
        gw = ScriptedGateway()
        engine, prompt = build_engine(gw)
        result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds, result.stop_reason), ('ready', 0, 'passed'),
                         [f'{f.acceptance_id}: {f.message[:200]}' for f in result.report.failures])
        self.assertEqual(gw.roles().count('content'), 1)
        self.assertNotIn('rewrite', gw.roles())
        self.assertEqual(result.repository['app.py'], R.APP_PY)
        self.assertEqual(result.repository['tests/test_site.py'], R.TEST_SITE)
        evidence = site_content.report(engine)
        self.assertEqual((evidence['route'], evidence['content_calls']), ('section_library', 1))
        self.assertEqual(evidence['parity']['status'], 'pass')
        gates = gate_report(engine)
        self.assertEqual({g: v.get('status') for g, v in gates.items() if g in ('G3', 'G10', 'HE', 'PRO', 'G1')},
                         {'G3': 'pass', 'G10': 'pass', 'HE': 'pass', 'PRO': 'pass', 'G1': 'pass'})
        self.assertEqual(engine.first_pass, True)

    def test_a_copy_finding_is_rewritten_at_that_path_only(self):
        from omni_prod.site_content import agents as A
        from omni_prod.site_content import render as R
        from omni_prod.skill_units.gate import SkillGateExecutor
        content = json.loads(json.dumps(CONTENT))
        content['sections']['services']['items'][1]['desc'] = BAD_TEXT
        gw = ScriptedGateway(content=content, rewrites=[{BAD_PATH: GOOD_TEXT}, {BAD_PATH: GOOD_TEXT}])
        with mock.patch.dict(os.environ, {'OMNI_GATE_HE': 'block'}):
            engine, prompt = build_engine(gw)
            result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertEqual(gw.roles().count('content'), 1)
        self.assertEqual(gw.roles().count('rewrite'), 1)                   # the pre-sandbox correction, one path
        rewrite_request = json.loads(gw.calls[gw.roles().index('rewrite')][1])
        self.assertEqual(list(rewrite_request['paths']), [BAD_PATH])
        final = json.loads(result.repository[R.SITE_JSON])['document']
        self.assertEqual(final, A.set_path(content, BAD_PATH, GOOD_TEXT))
        # after a round, through the repairer: the real HE gate's failure on a repository carrying the bad copy
        bad_doc = A.set_path(final, BAD_PATH, BAD_TEXT)
        core, sheet = engine, engine.site_sheet
        route = engine.site_route
        html, _ = R.render(bad_doc, sheet, route.contract, expect_fp=route.contract_fp, direction=route.direction,
                           year=route.year, outline_titles=route.outline_titles, order=route.order)
        repo = dict(result.repository, **{R.PAGE: html, R.SITE_JSON: R.site_json(
            bad_doc, json.loads(result.repository[R.SITE_JSON])['binds'])})

        class Passing:
            def execute(self, *, repository, spec):
                from omni_prod.autonomous_core import ExecutionReport
                return ExecutionReport(True, (), '')
        report = SkillGateExecutor(Passing(), 'HE', 'block').execute(repository=repo, spec=result.spec)
        self.assertEqual([f.acceptance_id for f in report.failures], ['gate-HE-he_gender'])
        patch = core.repairer.repair(spec=result.spec, repo_summary={'_repository': repo},
                                     failures=[f.__dict__ for f in report.failures])
        self.assertEqual(sorted(p.path for p in patch), [R.SITE_JSON, R.PAGE])
        repaired = json.loads(dict((p.path, p.content) for p in patch)[R.SITE_JSON])['document']
        self.assertEqual(repaired, final)                                   # only that path changed back
        self.assertEqual(json.loads(gw.calls[-1][1])['paths'], {BAD_PATH: BAD_TEXT})

    def test_a_platform_failure_stops_the_build_with_zero_repair_calls(self):
        from omni_prod.autonomous_core import RepairDeclined
        from omni_prod.site_content import agents as A
        gw = ScriptedGateway()
        # a real production switch: visual QA enforces its contrast rule too -- the real audit then fails the page
        with mock.patch.dict(os.environ, {'OMNI_VISUAL_QA_ENFORCE': 'offscreen_control,overlap,low_contrast'}):
            engine, prompt = build_engine(gw)
            with mock.patch.object(A.ContentSiteRepairer, 'repair', autospec=True,
                                   side_effect=A.ContentSiteRepairer.repair) as repair:
                result = engine.build(prompt)
        self.assertEqual((result.status, result.stop_reason), ('failed', 'platform_render_defect'))
        self.assertEqual(repair.call_count, 1)
        self.assertNotIn('rewrite', gw.roles())                            # zero repair model calls
        self.assertEqual(gw.roles().count('content'), 1)
        self.assertTrue(any(f.acceptance_id == 'VISUAL' for f in result.report.failures))
        declined = [t for t in engine.trace if t.get('repair_declined')]
        self.assertEqual(declined[0]['repair_declined'], 'platform_render_defect')
        self.assertTrue(issubclass(RepairDeclined, Exception))

    def test_advisory_findings_are_recorded_and_never_decline(self):
        from omni_prod import site_content
        review = {'findings': [{'skill': 'spec', 'severity': 'blocking', 'file': 'public/index.html',
                                'problem': 'The hero does not name the city in its title',
                                'fix': 'add the city to the title'}]}
        gw = ScriptedGateway(review=review)
        engine, prompt = build_engine(gw, design_critic=True)
        result = engine.build(prompt)
        self.assertEqual((result.status, result.repair_rounds), ('ready', 0))
        self.assertNotIn('rewrite', gw.roles())
        self.assertIn('design', gw.roles())
        feedback = site_content.report(engine)['library_feedback']
        self.assertTrue(any(f['acceptance_id'] == 'REVIEW' and 'city' in f['message'] for f in feedback), feedback)
        self.assertTrue(any(f['acceptance_id'] == 'DESIGN' for f in feedback), feedback)


if __name__ == '__main__':
    unittest.main()

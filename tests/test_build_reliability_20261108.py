"""Founder build bld_ca727ba7 (2026-11-08): what failed, pinned.

1. The acceptance runner could not capture '[0].id' from a JSON array, so a correct app failed A2-A4.
2. Sonnet 5.5 ran adaptive thinking by default and returned no text; its repair answer opened with prose.
3. The repair loop stopped after 2 of 6 rounds on one unchanged patch.
4. The founder had nothing to open after a failed build.
"""
import json
import unittest
from unittest import mock

from omni_prod.autonomous_core import AcceptanceFailure, AutonomousProductEngine, ExecutionReport
from omni_prod.model_gateway import ANTHROPIC_JSON_ONLY_RULE, ModelEndpoint, OpenAICompatibleGateway
from omni_prod.repository_patch import parse_patch
from omni_prod.web_saas_acceptance import _capture


class _Json:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class CapturePathTests(unittest.TestCase):
    def cap(self, path, data):
        out = {}
        _capture({'v': path}, _Json(data), out)
        return out['v']

    def test_root_array_index(self):
        self.assertEqual(self.cap('[0].id', [{'id': 1}, {'id': 3}]), 1)

    def test_nested_index_forms(self):
        data = {'items': [{'id': 7}]}
        for path in ('items[0].id', 'items.0.id', '$.items[0].id'):
            with self.subTest(path=path):
                self.assertEqual(self.cap(path, data), 7)

    def test_plain_keys_and_digit_object_key_still_work(self):
        self.assertEqual(self.cap('data.id', {'data': {'id': 'x'}}), 'x')
        self.assertEqual(self.cap('0', {'0': 'zero'}), 'zero')

    def test_missing_index_is_a_failure(self):
        with self.assertRaises(AssertionError):
            self.cap('[2].id', [{'id': 1}])
        with self.assertRaises(AssertionError):
            self.cap('[0].id', {'id': 1})


class _Resp:
    def __init__(self, payload):
        self.body, self.headers = json.dumps(payload).encode(), {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class AnthropicRequestTests(unittest.TestCase):
    def gateway(self, model, extra=()):
        gw = OpenAICompatibleGateway(ModelEndpoint(name='a', base_url='https://x.invalid', model=model, api_key='k',
                                                   external=True, api_style='anthropic', extra_body=extra))
        sent = {}

        def urlopen(req, timeout=None):
            sent.update(json.loads(req.data))
            return _Resp({'content': [{'type': 'text', 'text': '{"ok": true}'}], 'stop_reason': 'end_turn'})
        gw._urlopen = urlopen
        return gw, sent

    def test_sonnet_5_5_turns_off_up_front_thinking_and_states_the_json_rule(self):
        gw, sent = self.gateway('claude-sonnet-5-5')
        self.assertEqual(gw.complete_json(system='S', user='U'), {'ok': True})
        self.assertEqual(sent['thinking'], {'type': 'between_tools'})
        self.assertTrue(sent['system'].startswith('S') and sent['system'].endswith(ANTHROPIC_JSON_ONLY_RULE))

    def test_catalog_value_wins_and_other_models_are_untouched(self):
        gw, sent = self.gateway('claude-sonnet-5-5', extra=(('thinking', json.dumps({'type': 'adaptive'})),))
        gw.complete_json(system='S', user='U')
        self.assertEqual(sent['thinking'], {'type': 'adaptive'})
        gw, sent = self.gateway('claude-other')
        gw.complete(system='S', user='U')
        self.assertNotIn('thinking', sent)
        self.assertEqual(sent['system'], 'S')        # plain complete() is not a JSON call

    def test_catalog_entry_sets_between_tools(self):
        import pathlib
        catalog = json.loads(pathlib.Path('infra/worker-host/model-catalog.json').read_text())
        items = catalog if isinstance(catalog, list) else catalog['models']
        sonnet = next(m for m in items if m['name'] == 'anthropic-claude-sonnet-5-5')
        self.assertEqual(sonnet['extra_body']['thinking'], {'type': 'between_tools'})


class _Arch:
    def create_spec(self, prompt):
        return 'spec'


class _Gen:
    def generate(self, spec):
        return parse_patch({'files': [{'path': 'app.py', 'content': 'v0'}]})


class _Rep:
    def __init__(self, contents):
        self.contents, self.calls, self.failures = list(contents), 0, []

    def repair(self, **kw):
        self.calls += 1
        self.failures.append(kw['failures'])
        return parse_patch({'files': [{'path': 'app.py', 'content': self.contents.pop(0)}]})


class _Exec:
    def __init__(self, passing=()):
        self.passing = set(passing)

    def execute(self, *, repository, spec):
        if repository['app.py'] in self.passing:
            return ExecutionReport(True)
        return ExecutionReport(False, (AcceptanceFailure('A1', f"boom at {repository['app.py']}"),))


class SecondChanceTests(unittest.TestCase):
    def engine(self, rep, ex, chances):
        e = AutonomousProductEngine(architect=_Arch(), generator=_Gen(), repairer=rep, executor=ex,
                                    max_repair_rounds=6, repair_ceiling=6)
        e.no_progress_retries = chances
        return e

    def test_default_keeps_the_stop_loss(self):
        rep = _Rep(['v0', 'v1'])
        result = self.engine(rep, _Exec(), 0).build('p')
        self.assertEqual((result.stop_reason, rep.calls), ('no_progress_repository_unchanged', 1))

    def test_one_second_chance_is_told_and_can_pass(self):
        rep = _Rep(['v0', 'v1'])
        result = self.engine(rep, _Exec(passing={'v1'}), 1).build('p')
        self.assertEqual((result.status, result.stop_reason, rep.calls), ('ready', 'passed', 2))
        self.assertIn('NO_PROGRESS', [f['acceptance_id'] for f in rep.failures[1]])

    def test_chances_are_bounded(self):
        rep = _Rep(['v0', 'v0', 'v0'])
        result = self.engine(rep, _Exec(), 1).build('p')
        self.assertEqual((result.stop_reason, rep.calls), ('no_progress_repository_unchanged', 2))

    def test_running_out_of_rounds_is_labelled_as_such(self):
        rep = _Rep(['v0', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6'])
        result = self.engine(rep, _Exec(), 1).build('p')
        self.assertEqual(result.stop_reason, 'max_repair_rounds')
        self.assertEqual(result.repair_rounds, 6)


class FounderDraftTests(unittest.TestCase):
    def test_only_founder_and_only_check_failures(self):
        from omni_prod.worker_tasks import _founder_draft_allowed, _version_message
        with mock.patch.dict('os.environ', {'OMNI_FOUNDER_ACCOUNT_IDS': 'usr_f'}):
            self.assertTrue(_founder_draft_allowed({'user_id': 'usr_f'}, 'verification_failed'))
            self.assertFalse(_founder_draft_allowed({'user_id': 'usr_c'}, 'verification_failed'))
            self.assertFalse(_founder_draft_allowed({'user_id': 'usr_f'}, 'security_gate_failed'))
            with mock.patch.dict('os.environ', {'OMNI_FOUNDER_DRAFT_VERSIONS': '0'}):
                self.assertFalse(_founder_draft_allowed({'user_id': 'usr_f'}, 'verification_failed'))
        self.assertIn('DRAFT', _version_message('b1', True))
        self.assertEqual(_version_message('b1', False), '148AI async live build b1')


if __name__ == '__main__':
    unittest.main()


class StationSkillPackTests(unittest.TestCase):
    """CEO 2026-11-08 23:04: 10-20 world-class skills, each tied to the stations that use it."""

    def test_pack_size_and_every_station_has_a_method(self):
        from omni_prod.skills_runtime import WEB_SKILLS, skills_for
        self.assertTrue(10 <= len(WEB_SKILLS) <= 20)
        keys = {role: {s.key for s in skills_for(role)} for role in ('architect', 'generator', 'repair', 'reviewer')}
        self.assertIn('skill.spec_precision', keys['architect'])
        self.assertIn('skill.acceptance_plan', keys['generator'])
        self.assertIn('skill.repair_method', keys['repair'])
        self.assertIn('skill.security_basics', keys['reviewer'])

    def test_family_specific_skills_say_when_they_apply(self):
        from omni_prod.skills_runtime import DATA_INTEGRITY, GAME_2D, LANDING_CONVERSION
        self.assertTrue(GAME_2D.guidance.startswith('ONLY for a game'))
        self.assertTrue(LANDING_CONVERSION.guidance.startswith('ONLY for a website or landing page'))
        self.assertIn('ONLY when the product books a resource', DATA_INTEGRITY.guidance)

    def test_prompts_carry_the_skills(self):
        import omni_prod.autonomous_agents as agents
        self.assertIn('skill.repair_method@1', agents._REPAIR_SYSTEM)
        self.assertIn('skill.acceptance_plan@1', agents._GENERATOR_SYSTEM)
        self.assertIn('skill.spec_precision@1', agents._ARCHITECT_SYSTEM)


class SkillStaticCheckTests(unittest.TestCase):
    def test_new_checks_report_advisory_findings(self):
        from omni_prod.skills_runtime import static_findings
        repo = {'app.py': 'cur.execute(f"SELECT * FROM t WHERE id={x}")\ncur.execute("SELECT 1 WHERE a=?", (a,))',
                'index.html': '<html><label for="n">n</label><input id="n"><input id="p"><p>Lorem ipsum</p></html>'}
        got = {(f.skill, f.severity) for f in static_findings(repo)}
        for skill in ('skill.security_basics', 'skill.accessibility', 'skill.copy_quality'):
            self.assertIn((skill, 'advisory'), got)
        clean = {'app.py': 'cur.execute("SELECT 1 WHERE a=?", (a,))'}
        self.assertFalse([f for f in static_findings(clean) if f.skill == 'skill.security_basics'])


class RepairVisibilityTests(unittest.TestCase):
    """bld_624610bc (2026-11-09): a 51K-char app.py was hidden from every repair round."""

    def test_large_entry_file_is_shown_to_the_repairer(self):
        from omni_prod.modifier_engine import repo_summary
        repo = {'app.py': 'x = 1\n' * 9000, '.omni/project.json': '{}'}      # 54K chars
        files = {f['path']: f for f in repo_summary(repo, [])['files']}
        self.assertIn('content', files['app.py'])

    def test_sonnet_output_cap_and_code_structure_skill(self):
        import pathlib
        from omni_prod.skills_runtime import WEB_SKILLS
        catalog = json.loads(pathlib.Path('infra/worker-host/model-catalog.json').read_text())
        items = catalog if isinstance(catalog, list) else catalog['models']
        sonnet = next(m for m in items if m['name'] == 'anthropic-claude-sonnet-5-5')
        self.assertGreaterEqual(sonnet['max_output_tokens'], 40000)
        self.assertIn('skill.code_structure', {s.key for s in WEB_SKILLS})


class IndentationGuardTests(unittest.TestCase):
    """bld_3f5dc453 / bld_5b2e8f58 (2026-11-09): flattened Python from Sonnet was adopted and burned every round."""

    FLAT = {'files': [{'path': 'app.py', 'content': 'def f():\nreturn 1\n'}]}
    GOOD = {'files': [{'path': 'app.py', 'content': 'def f():\n    return 1\n'}]}

    def test_guard_rejects_only_lost_indentation(self):
        from omni_prod.autonomous_agents import _code_shape_guard
        from omni_prod.model_gateway import ModelJSONRejected
        with self.assertRaises(ModelJSONRejected):
            _code_shape_guard(self.FLAT)
        _code_shape_guard(self.GOOD)
        _code_shape_guard({'files': [{'path': 'a.py', 'content': 'x = (\n'}]})   # other syntax: repair's job
        _code_shape_guard({'files': [{'path': 'index.html', 'content': '<p>\n</p>'}]})

    def test_router_escalates_to_the_next_model(self):
        from decimal import Decimal
        from omni_prod.autonomous_agents import _code_shape_guard
        from omni_prod.model_catalog import CatalogModel
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.model_router import ModelOption, RoutingPolicy
        from omni_prod.routed_gateway import RoutedModelGateway

        def m(name, price):
            return CatalogModel(endpoint=ModelEndpoint(name=name, base_url='https://x.invalid', model=name, api_key='k',
                                                       external=True),
                                option=ModelOption('p', name, 90, 1000, Decimal(price), Decimal(price)),
                                max_output_tokens=4000, api_key_env='K')
        gw = RoutedModelGateway(ranked=(m('first', '1'), m('second', '5')),
                                routing_policy=RoutingPolicy(minimum_quality=0, prefer_cost=True),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('10'),
                                                      max_external_calls_per_build=10))
        used = []

        def attempt(route, method, kwargs, why, **kw):
            used.append(route.endpoint.name)
            return self.FLAT if route.endpoint.name == 'first' else self.GOOD
        with mock.patch.object(gw, '_attempt', side_effect=attempt):
            out = gw.complete_json(system='s', user='u', max_tokens=100, task='codegen', validate=_code_shape_guard)
        self.assertEqual(out, self.GOOD)
        self.assertEqual(used, ['first', 'second'])


class MissingKindHintTests(unittest.TestCase):
    def test_missing_delete_says_what_a_passing_step_is(self):
        from omni_prod.behavior_acceptance import _failure_text
        msg, evidence = _failure_text({'checks': [], 'missing_kinds': ['data_delete']})
        self.assertIn('SUCCESSFULLY removes or cancels', msg + evidence)

    def test_reviewer_treats_timing_edge_cases_as_advisory(self):
        from omni_prod.product_review import _REVIEW_SYSTEM
        self.assertIn('rapid repeated clicks', _REVIEW_SYSTEM)
class BuildRestoreUiTests(unittest.TestCase):
    """2026-11-09: a queued/running build vanished after a reload; a finished build's result was not shown again."""

    def setUp(self):
        import pathlib
        self.js = pathlib.Path('omni_prod/assets/app.js').read_text(encoding='utf-8')

    def test_background_quote_never_clears_an_active_build(self):
        self.assertIn("if (open === true && (!S.build || isTerminal(S.build.status))) S.build = null;", self.js)
        self.assertNotIn("    S.build = null; renderDiscovery(); renderPlan(); renderTrack();", self.js)

    def test_finished_build_is_restored_without_preview_start(self):
        start = self.js.index('async function restoreBuild()')
        body = self.js[start:self.js.index('\n}\n', start)]
        self.assertIn('if (isTerminal(b.status))', body)
        self.assertNotIn('startPreview', body)

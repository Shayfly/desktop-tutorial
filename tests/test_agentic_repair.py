"""Agentic repair v1 (CEO order 2026-11-09): the repair model reads, searches, edits and checks in a working copy."""
import json
import unittest
from unittest import mock

from omni_prod.agentic_repair import AgenticRepairAgent


class _Spec:
    def to_dict(self):
        return {'title': 't'}


class _Fallback:
    def __init__(self):
        self.calls = 0

    def repair(self, **kw):
        self.calls += 1
        return ('fallback',)


class _Gw:
    def __init__(self, answers):
        self.answers, self.prompts = list(answers), []

    def complete_json(self, **kw):
        self.prompts.append(json.loads(kw['user']))
        return self.answers.pop(0)


BASE = {'app.py': 'from api import handle\n\ndef main():\n    return handle()\n',
        'api.py': 'def handle():\n    return 1\n'}


class AgenticRepairTests(unittest.TestCase):
    def run_agent(self, answers, repo=BASE, steps=6):
        gw, fb = _Gw(answers), _Fallback()
        agent = AgenticRepairAgent(gw, fallback=fb, max_steps=steps)
        out = agent.repair(spec=_Spec(), repo_summary={'_repository': dict(repo), 'candidate_files': []},
                           failures=[{'acceptance_id': 'A1', 'message': 'boom', 'evidence': ''}])
        return out, gw, fb, agent

    def test_read_edit_submit_returns_only_changed_files(self):
        out, gw, fb, agent = self.run_agent([
            {'action': 'read', 'paths': ['api.py']},
            {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 2\n'}]},
            {'action': 'submit', 'note': 'returned the wrong value'}])
        self.assertEqual([p.path for p in out], ['api.py'])
        self.assertEqual(fb.calls, 0)
        self.assertIn('return 1', gw.prompts[1]['history'][0]['result']['files']['api.py'])
        self.assertTrue(gw.prompts[2]['history'][1]['result']['clean'])
        self.assertEqual(gw.prompts[2]['edited'], ['api.py'])

    def test_edit_reports_broken_code_back_to_the_model(self):
        out, gw, _, _ = self.run_agent([
            {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle(:\n'}]},
            {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 3\n'}]},
            {'action': 'submit'}])
        first = gw.prompts[1]['history'][0]['result']
        self.assertFalse(first['clean'])
        self.assertTrue(any('syntax' in p for p in first['problems']))
        self.assertEqual(out[0].content, 'def handle():\n    return 3\n')

    def test_search_finds_definitions(self):
        _, gw, _, _ = self.run_agent([{'action': 'search', 'pattern': r'def handle'},
                                      {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 4\n'}]},
                                      {'action': 'submit'}])
        self.assertEqual(gw.prompts[1]['history'][0]['result']['matches'], ['api.py:1: def handle():'])

    def test_no_change_or_no_repository_falls_back_to_classic_repair(self):
        out, _, fb, _ = self.run_agent([{'action': 'read', 'paths': ['x']}, {'action': 'submit'}])
        self.assertEqual((out, fb.calls), (('fallback',), 1))
        fb2 = _Fallback()
        out = AgenticRepairAgent(_Gw([]), fallback=fb2).repair(spec=_Spec(), repo_summary={}, failures=[])
        self.assertEqual((out, fb2.calls), (('fallback',), 1))

    def test_steps_are_bounded_and_edits_kept_when_steps_run_out(self):
        answers = [{'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 5\n'}]}] + \
                  [{'action': 'read', 'paths': ['api.py']}] * 10
        out, gw, _, agent = self.run_agent(answers, steps=3)
        self.assertEqual(len(gw.prompts), 3)
        self.assertEqual(out[0].content, 'def handle():\n    return 5\n')
        self.assertEqual(agent.trace[-1]['result'], 'steps_exhausted')

    def test_founder_only_by_default(self):
        from omni_prod.worker_tasks import _install_agentic_repair

        class E:
            def __init__(self):
                self.repairer = mock.Mock(gateway=object())
        with mock.patch.dict('os.environ', {'OMNI_FOUNDER_ACCOUNT_IDS': 'usr_f'}, clear=False):
            e = E(); self.assertTrue(_install_agentic_repair(e, {'user_id': 'usr_f'}))
            self.assertEqual(type(e.repairer).__name__, 'AgenticRepairAgent')
            e = E(); self.assertFalse(_install_agentic_repair(e, {'user_id': 'usr_c'}))
            with mock.patch.dict('os.environ', {'OMNI_AGENTIC_REPAIR': '0'}):
                e = E(); self.assertFalse(_install_agentic_repair(e, {'user_id': 'usr_f'}))
            with mock.patch.dict('os.environ', {'OMNI_AGENTIC_REPAIR': 'all'}):
                e = E(); self.assertTrue(_install_agentic_repair(e, {'user_id': 'usr_c'}))

    def test_repository_never_reaches_the_classic_prompt(self):
        from omni_prod.autonomous_agents import _filter_repo_summary
        self.assertNotIn('_repository', _filter_repo_summary({'files': [], '_repository': {'a': 'b'}}))


if __name__ == '__main__':
    unittest.main()

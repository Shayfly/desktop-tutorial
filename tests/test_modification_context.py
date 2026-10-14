"""Modification and repair agents see the code they must change.

Golden E2E #1 (2026-10-07): the evolution/repair prompts carried only
{path, chars}, so "add deleting a team" would have rewritten app.py blind.
"""
import json
import unittest

from omni_prod.autonomous_agents import RepairAgent, _filter_repo_summary
from omni_prod.modifier_engine import repo_summary
from omni_prod.product_evolution import ProductEvolutionAgent, _EVOLUTION_SYSTEM
from omni_prod.product_spec import ProductSpec


def _repo():
    return {
        '.omni/project.json': '{"build": [], "verify": []}',
        'app.py': 'TEAMS = []\ndef add(name):\n    TEAMS.append(name)\n',
        'tests/test_app.py': 'def test_add():\n    pass\n',
        'package-lock.json': '{}',
        'big.py': 'x' * 20_000,
        'logo.png': 'binary',
    }


class _Gateway:
    def __init__(self, reply):
        self.reply, self.calls = reply, []

    def complete_json(self, *, system, user, max_tokens):
        self.calls.append((system, json.loads(user)))
        return self.reply


def _spec():
    return ProductSpec.from_dict({'title': 'L', 'summary': 's', 'stack': ['python'],
                                  'requirements': [{'id': 'R1', 'text': 'teams'}],
                                  'acceptance': [{'id': 'A1', 'requirement_id': 'R1', 'text': 'add'}]})


class ContextTests(unittest.TestCase):
    def test_source_files_carry_content_and_noise_does_not(self):
        entries = {e['path']: e for e in repo_summary(_repo())['files']}
        self.assertIn('TEAMS.append', entries['app.py']['content'])
        self.assertIn('content', entries['.omni/project.json'])
        self.assertIn('content', entries['tests/test_app.py'])
        for noisy in ('package-lock.json', 'big.py', 'logo.png'):
            self.assertNotIn('content', entries[noisy], noisy)
            self.assertIn('chars', entries[noisy])

    def test_total_content_is_bounded(self):
        repo = {f'm{i}.py': 'y' * 15_000 for i in range(10)}
        total = sum(len(e.get('content', '')) for e in repo_summary(repo)['files'])
        self.assertLessEqual(total, 64_000)

    def test_repair_agent_receives_content(self):
        gw = _Gateway({'files': [{'path': 'app.py', 'content': 'x = 1'}]})
        RepairAgent(gw).repair(spec=_spec(), repo_summary=repo_summary(_repo()), failures=[])
        sent = {e['path']: e for e in gw.calls[0][1]['repository']['files']}
        self.assertIn('content', sent['app.py'])

    def test_evolution_agent_receives_content_and_coverage_rule(self):
        gw = _Gateway({'spec': _spec().to_dict(), 'files': [{'path': 'app.py', 'content': 'x = 1'}]})
        ProductEvolutionAgent(gw).evolve(spec=_spec(), repo_summary=repo_summary(_repo()), followup='add delete')
        sent = {e['path']: e for e in gw.calls[0][1]['repository']['files']}
        self.assertIn('content', sent['app.py'])
        self.assertIn('acceptance_ids', _EVOLUTION_SYSTEM)
        self.assertNotIn('Only touch', _EVOLUTION_SYSTEM)


if __name__ == '__main__':
    unittest.main()

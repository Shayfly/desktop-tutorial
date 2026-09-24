import json
import unittest

from omni_prod.product_evolution import ProductEvolutionAgent, SpecRegressionError
from omni_prod.product_spec import ProductSpec

SPEC = {
    'title': 'Todo',
    'summary': 'Todo app',
    'stack': ['python'],
    'requirements': [
        {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
    ],
    'acceptance': [
        {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
    ],
}


def _spec():
    return ProductSpec.from_dict(SPEC)


class FakeGateway:
    """Mirrors OpenAICompatibleGateway.complete_json's contract (system, user,
    max_tokens) -> dict, without any HTTP -- the same substitution
    test_v22_autonomous_core.py's non-HTTP tests make for ArchitectAgent/
    GeneratorAgent/RepairAgent's own gateway dependency."""
    def __init__(self, response: dict):
        self.response = response
        self.calls = []

    def complete_json(self, *, system, user, max_tokens):
        self.calls.append({'system': system, 'user': user, 'max_tokens': max_tokens})
        return self.response


def _response_with_new_requirement():
    return {
        'spec': {
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [
                {'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True},
                {'id': 'R2', 'text': 'calendar view', 'kind': 'functional', 'mandatory': True},
            ],
            'acceptance': [
                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
                {'id': 'A2', 'requirement_id': 'R2', 'text': 'calendar view renders'},
            ],
        },
        'files': [{'path': 'calendar.py', 'content': 'def render(): pass'}],
    }


class EvolutionTests(unittest.TestCase):
    def test_valid_evolution_adds_capability_and_preserves_existing_ids(self):
        gateway = FakeGateway(_response_with_new_requirement())
        agent = ProductEvolutionAgent(gateway)
        new_spec, patch = agent.evolve(spec=_spec(), repo_summary={'files': [], 'file_count': 0, 'total_chars': 0},
                                        followup='add a calendar view')
        self.assertEqual({r.id for r in new_spec.requirements}, {'R1', 'R2'})
        self.assertEqual({a.id for a in new_spec.acceptance}, {'A1', 'A2'})
        self.assertEqual(len(patch), 1)
        self.assertEqual(patch[0].path, 'calendar.py')
        # The request sent to the model carries the real spec and followup.
        sent = json.loads(gateway.calls[0]['user'])
        self.assertEqual(sent['change_request'], 'add a calendar view')
        self.assertEqual(sent['spec']['title'], 'Todo')

    def test_dropped_requirement_id_is_rejected(self):
        response = _response_with_new_requirement()
        response['spec']['requirements'] = [r for r in response['spec']['requirements'] if r['id'] != 'R1']
        response['spec']['acceptance'] = [a for a in response['spec']['acceptance'] if a['requirement_id'] != 'R1']
        agent = ProductEvolutionAgent(FakeGateway(response))
        with self.assertRaises(SpecRegressionError):
            agent.evolve(spec=_spec(), repo_summary={}, followup='add a calendar view')

    def test_dropped_acceptance_id_is_rejected_even_if_requirement_still_has_other_coverage(self):
        # R1 starts with two acceptance criteria (A1, A1b) so dropping just A1
        # still leaves R1 covered -- ProductSpec.from_dict's own "mandatory
        # requirement needs at least one acceptance criterion" check would
        # otherwise catch this first (a different, earlier failure reason)
        # and this test wants to isolate _assert_no_dropped_ids's own check.
        spec = ProductSpec.from_dict({
            'title': 'Todo', 'summary': 'Todo app', 'stack': ['python'],
            'requirements': [{'id': 'R1', 'text': 'show todos', 'kind': 'functional', 'mandatory': True}],
            'acceptance': [
                {'id': 'A1', 'requirement_id': 'R1', 'text': 'home shows todo list'},
                {'id': 'A1b', 'requirement_id': 'R1', 'text': 'todo list updates live'},
            ],
        })
        response = _response_with_new_requirement()
        response['spec']['acceptance'] = [
            {'id': 'A1b', 'requirement_id': 'R1', 'text': 'todo list updates live'},
            {'id': 'A2', 'requirement_id': 'R2', 'text': 'calendar view renders'},
        ]
        agent = ProductEvolutionAgent(FakeGateway(response))
        with self.assertRaises(SpecRegressionError):
            agent.evolve(spec=spec, repo_summary={}, followup='add a calendar view')

    def test_empty_followup_rejected_without_calling_the_model(self):
        gateway = FakeGateway(_response_with_new_requirement())
        agent = ProductEvolutionAgent(gateway)
        with self.assertRaises(ValueError):
            agent.evolve(spec=_spec(), repo_summary={}, followup='   ')
        self.assertEqual(gateway.calls, [])

    def test_patch_path_traversal_is_rejected_by_the_shared_patch_parser(self):
        response = _response_with_new_requirement()
        response['files'] = [{'path': '../../etc/passwd', 'content': 'x'}]
        agent = ProductEvolutionAgent(FakeGateway(response))
        with self.assertRaises(Exception):
            agent.evolve(spec=_spec(), repo_summary={}, followup='add a calendar view')


if __name__ == '__main__':
    unittest.main()

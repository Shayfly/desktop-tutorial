"""Repair JSON (owner 2026-11-22, item 5): production, 14 days to 2026-11-22 -- 99 of 310 Sonnet repair answers were
rejected, every one for prose before the JSON ("I need to see the project config..."), and each rejection ended the
agentic round. Two fixes, both crossing the real code: the native Anthropic request carries the action schema
(structured outputs), and a refused answer is told back to the model instead of ending the round."""
import io
import json
import unittest

from omni_prod.agentic_repair import ACTION_SCHEMA, MAX_CONSECUTIVE_REJECTED, AgenticRepairAgent
from omni_prod.model_gateway import ModelEndpoint, ModelJSONRejected, OpenAICompatibleGateway


class _Resp(io.BytesIO):
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _gateway(style, answer_text):
    sent = []

    def urlopen(req, timeout=None):
        sent.append(json.loads(req.data.decode('utf-8')))
        if style == 'anthropic':
            body = {'content': [{'type': 'text', 'text': answer_text}], 'stop_reason': 'end_turn',
                    'usage': {'input_tokens': 1, 'output_tokens': 1}}
        else:
            body = {'choices': [{'message': {'content': answer_text}, 'finish_reason': 'stop'}],
                    'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
        return _Resp(json.dumps(body).encode())
    ep = ModelEndpoint(name='m', base_url='https://example.invalid/v1', model='claude-sonnet-5-5', api_style=style)
    return OpenAICompatibleGateway(ep, urlopen=urlopen), sent


class SchemaReachesTheProvider(unittest.TestCase):
    def test_anthropic_request_carries_the_schema_as_structured_output(self):
        gw, sent = _gateway('anthropic', '{"action": "read", "paths": ["app.py"]}')
        self.assertEqual(gw.complete_json(system='s', user='u', schema=ACTION_SCHEMA), {'action': 'read', 'paths': ['app.py']})
        self.assertEqual(sent[0]['output_config'], {'format': {'type': 'json_schema', 'schema': ACTION_SCHEMA}})

    def test_no_schema_no_output_config(self):
        gw, sent = _gateway('anthropic', '{"a": 1}')
        gw.complete_json(system='s', user='u')
        self.assertNotIn('output_config', sent[0])

    def test_openai_style_is_unchanged(self):
        gw, sent = _gateway('openai', '{"action": "submit"}')
        gw.complete_json(system='s', user='u', schema=ACTION_SCHEMA)
        self.assertNotIn('output_config', sent[0])
        self.assertNotIn('response_format', sent[0])

    def test_routed_gateway_passes_the_schema_through(self):
        from decimal import Decimal
        from omni_prod.model_catalog import parse_model_catalog
        from omni_prod.model_policy import ModelUsePolicy
        from omni_prod.model_router import RoutingPolicy
        from omni_prod.routed_gateway import RoutedModelGateway
        seen = []

        class Fake:
            def __init__(self, endpoint):
                self.endpoint, self.last_usage = endpoint, None

            def complete_json(self, **kw):
                seen.append(kw)
                return {'action': 'submit'}
        catalog = [{'name': 'cheap', 'provider': 'p1', 'base_url': 'https://a.example/v1', 'model': 'm-cheap', 'api_key_env': 'KEY_ONE',
                    'quality': 90, 'input_per_million': '1', 'output_per_million': '2'}]
        gw = RoutedModelGateway(ranked=parse_model_catalog(json.dumps(catalog), {'KEY_ONE': 'x'}),
                                routing_policy=RoutingPolicy(minimum_quality=0),
                                policy=ModelUsePolicy(zero_cost_mode=False, allow_external_fallback=True,
                                                      external_budget_usd=Decimal('5'), max_external_calls_per_build=5),
                                gateway_factory=Fake)
        gw.complete_json(system='s', user='u', schema=ACTION_SCHEMA)
        gw.complete_json(system='s', user='u')
        self.assertIs(seen[0]['schema'], ACTION_SCHEMA)
        self.assertNotIn('schema', seen[1])                 # gateways without the option see no new keyword


class SchemaShape(unittest.TestCase):
    """The documented structured-output limits: every object closed, anyOf at the root only, no length keywords."""

    def _objects(self, node):
        if isinstance(node, dict):
            if node.get('type') == 'object':
                yield node
            for v in node.values():
                yield from self._objects(v)
        elif isinstance(node, list):
            for v in node:
                yield from self._objects(v)

    def test_every_object_is_closed_and_requires_only_known_properties(self):
        objs = list(self._objects(ACTION_SCHEMA))
        self.assertGreaterEqual(len(objs), 6)
        for o in objs:
            self.assertIs(o['additionalProperties'], False)
            self.assertTrue(set(o['required']) <= set(o['properties']))
        text = json.dumps(ACTION_SCHEMA)
        for banned in ('oneOf', 'minLength', 'maxLength', 'minimum', 'maximum'):
            self.assertNotIn(banned, text)

    def test_the_four_actions_of_the_prompt(self):
        actions = [b['properties']['action']['enum'] for b in ACTION_SCHEMA['anyOf']]
        self.assertEqual(actions, [['read'], ['search'], ['edit'], ['submit']])


class _Spec:
    def to_dict(self):
        return {'title': 't'}


class _Fallback:
    calls = 0

    def repair(self, **kw):
        self.calls += 1
        return ('fallback',)


class _Gw:
    """Answers in order; an Exception instance is raised. Records the schema it was given."""

    def __init__(self, answers):
        self.answers, self.prompts, self.schemas = list(answers), [], []

    def complete_json(self, **kw):
        self.prompts.append(json.loads(kw['user']))
        self.schemas.append(kw.get('schema'))
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a


def _rejected(reason='content before the JSON value (not a known envelope) at char 0 of 120'):
    return ModelJSONRejected('model did not return valid JSON', raw='I need to see app.py first. {"action":"read"}',
                             diagnostic={'reason': reason})


BASE = {'api.py': 'def handle():\n    return 1\n'}


class RefusedAnswerDoesNotEndTheRound(unittest.TestCase):
    def run_agent(self, answers):
        gw, fb = _Gw(answers), _Fallback()
        agent = AgenticRepairAgent(gw, fallback=fb, max_steps=6)
        out = agent.repair(spec=_Spec(), repo_summary={'_repository': dict(BASE), 'candidate_files': []},
                           failures=[{'acceptance_id': 'A1', 'message': 'boom', 'evidence': ''}])
        return out, gw, fb, agent

    def test_the_repair_loop_sends_the_action_schema(self):
        _, gw, _, _ = self.run_agent([{'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 2\n'}]},
                                      {'action': 'submit'}])
        self.assertTrue(all(s is ACTION_SCHEMA for s in gw.schemas))

    def test_one_refused_answer_is_told_back_and_the_round_goes_on(self):
        out, gw, fb, agent = self.run_agent([
            _rejected(),
            {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 2\n'}]},
            {'action': 'submit', 'note': 'wrong value'}])
        self.assertEqual(fb.calls, 0)                                  # the agentic round answered, not the fallback
        self.assertEqual([p.path for p in out], ['api.py'])
        told = gw.prompts[1]['history'][-1]['result']['error']
        self.assertIn('refused', told)
        self.assertIn('content before the JSON value', told)
        self.assertTrue(any('rejected' in t for t in agent.trace))

    def test_two_refused_in_a_row_end_the_round_loudly(self):
        self.assertEqual(MAX_CONSECUTIVE_REJECTED, 2)
        out, gw, fb, agent = self.run_agent([_rejected(), _rejected(), {'action': 'submit'}])
        self.assertEqual(len(gw.prompts), 2)                            # bounded: no third call
        self.assertEqual(fb.calls, 1)
        self.assertTrue(any('in a row' in str(t.get('error', '')) for t in agent.trace))

    def test_a_good_answer_resets_the_count(self):
        out, gw, fb, _ = self.run_agent([
            _rejected(), {'action': 'read', 'paths': ['api.py']},
            _rejected(), {'action': 'edit', 'files': [{'path': 'api.py', 'content': 'def handle():\n    return 3\n'}]},
            {'action': 'submit'}])
        self.assertEqual(fb.calls, 0)
        self.assertEqual(out[0].content, 'def handle():\n    return 3\n')

    def test_other_errors_still_end_the_round(self):
        out, gw, fb, _ = self.run_agent([RuntimeError('provider down'), {'action': 'submit'}])
        self.assertEqual((len(gw.prompts), fb.calls), (1, 1))


if __name__ == '__main__':
    unittest.main()

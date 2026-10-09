"""Model JSON answers (paid builds 2026-10-09: every strong-model repair answer
was refused as 'not valid JSON' with no reason given)."""
import json
import unittest

from omni_prod.model_gateway import ModelEndpoint, ModelGatewayError, OpenAICompatibleGateway, _parse_json_object
from omni_prod.web_saas_acceptance import _text_contains


class _Resp:
    def __init__(self, payload):
        self.body, self.headers = json.dumps(payload).encode(), {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _gateway(content, finish='stop'):
    gw = OpenAICompatibleGateway(ModelEndpoint(name='m', base_url='https://x.invalid', model='m', api_key='k', external=True))
    gw._urlopen = lambda req, timeout=None: _Resp({'choices': [{'message': {'content': content}, 'finish_reason': finish}]})
    return gw


class JsonAnswerTests(unittest.TestCase):
    def test_plain_and_fenced_objects(self):
        self.assertEqual(_gateway('{"a": 1}').complete_json(system='s', user='u'), {'a': 1})
        self.assertEqual(_gateway('```json\n{"a": 1}\n```').complete_json(system='s', user='u'), {'a': 1})

    def test_raw_newline_inside_a_code_string_is_accepted(self):
        self.assertEqual(_parse_json_object('{"code": "line1\nline2"}')[0], {'code': 'line1\nline2'})

    def test_object_wrapped_in_prose_is_extracted(self):
        out = _gateway('Here is the fix:\n{"files": []}\nGood luck').complete_json(system='s', user='u')
        self.assertEqual(out, {'files': []})

    def test_truncated_answer_names_the_reason(self):
        with self.assertRaises(ModelGatewayError) as ctx:
            _gateway('{"files": [{"path": "a.py", "content": "x', finish='length').complete_json(system='s', user='u')
        msg = str(ctx.exception)
        self.assertIn('finish_reason=length', msg)
        self.assertIn('valid JSON', msg)

    def test_regex_backslash_in_code_is_kept_literally(self):
        self.assertEqual(_parse_json_object(r'{"re": "\d+", "ok": "a\\b\n"}')[0], {'re': '\\d+', 'ok': 'a\\b\n'})

    def test_garbage_is_still_refused(self):
        self.assertIsNotNone(_parse_json_object('not json at all')[1])
        self.assertIsNotNone(_parse_json_object('{"a": }')[1])


class AcceptanceTextTests(unittest.TestCase):
    def test_escaped_hebrew_in_a_json_body_matches(self):
        body = json.dumps({'error': 'השעה הזו כבר תפוסה'})            # ensure_ascii -> ה...
        self.assertTrue(_text_contains(body, 'השעה הזו כבר תפוסה'))

    def test_absent_text_still_fails(self):
        self.assertFalse(_text_contains(json.dumps({'error': 'אחר'}), 'תפוסה'))
        self.assertFalse(_text_contains('<html>nothing</html>', 'תפוסה'))



class AcceptanceDateVariableTests(unittest.TestCase):
    """Paid build bld_2be07937: a fixed date in the plan went stale."""

    def test_relative_dates_resolve_from_today(self):
        import datetime
        from omni_prod.web_saas_acceptance import _resolve
        today = datetime.date.today()
        out = _resolve({'date': '${date_plus_7}', 'since': '${date_minus_1}', 'on': '${today}', 'id': '${id}'}, {'id': 3})
        self.assertEqual(out, {'date': (today + datetime.timedelta(days=7)).isoformat(),
                               'since': (today - datetime.timedelta(days=1)).isoformat(),
                               'on': today.isoformat(), 'id': '3'})

    def test_captured_values_win_and_unknown_names_still_fail(self):
        from omni_prod.web_saas_acceptance import _resolve
        self.assertEqual(_resolve('${today}', {'today': 'captured'}), 'captured')
        with self.assertRaises(ValueError):
            _resolve('${nope}', {})


if __name__ == '__main__':
    unittest.main()

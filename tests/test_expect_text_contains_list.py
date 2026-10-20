"""expect_text_contains accepts a list: every item must appear (paid run 39377332673, 2026-10-20).

The plan said ["viewport", "width=device-width"]; the old check searched for str(list) -- "['viewport', ...]" -- which
no page contains, so a page with both strings failed three repair rounds (BEHAVIOR / A5, kind responsive).
"""
import unittest

from omni_prod.web_saas_acceptance import HttpResponse, _assert_response

PAGE = ('<!DOCTYPE html><html lang="he" dir="rtl"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>תורים למספרה</title>')


def resp(body=PAGE, status=200):
    return HttpResponse(status=status, headers={}, body=body.encode())


class ExpectTextContainsListTests(unittest.TestCase):
    def test_the_failing_step_of_run_39377332673_now_passes(self):
        _assert_response({'expect_status': 200, 'expect_text_contains': ['viewport', 'width=device-width']}, resp())

    def test_every_item_must_appear(self):
        with self.assertRaises(AssertionError) as cm:
            _assert_response({'expect_text_contains': ['viewport', 'max-width: 600px']}, resp())
        self.assertIn('max-width: 600px', str(cm.exception))
        self.assertNotIn("'viewport'", str(cm.exception).split('(all of')[0])   # only the missing one is named

    def test_tuple_is_a_list_too(self):
        _assert_response({'expect_text_contains': ('תורים', 'viewport')}, resp())

    def test_a_plain_string_behaves_as_before(self):
        _assert_response({'expect_text_contains': 'תורים למספרה'}, resp())
        with self.assertRaises(AssertionError) as cm:
            _assert_response({'expect_text_contains': 'not on the page'}, resp())
        self.assertEqual(str(cm.exception), "response text missing 'not on the page'")

    def test_items_match_escaped_json_like_a_string(self):
        _assert_response({'expect_text_contains': ['תור', 'נקבע']}, resp('{"message": "\\u05ea\\u05d5\\u05e8 \\u05e0\\u05e7\\u05d1\\u05e2"}'))

    def test_an_empty_list_or_empty_item_fails_instead_of_passing_vacuously(self):
        for empty in ([], ['viewport', ''], ''):
            with self.assertRaises(AssertionError) as cm:
                _assert_response({'expect_text_contains': empty}, resp())
            self.assertIn('empty', str(cm.exception))


if __name__ == '__main__':
    unittest.main()

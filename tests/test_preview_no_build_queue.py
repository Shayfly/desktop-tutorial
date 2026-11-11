"""72 part 2 (Michael 2026-11-11): on a Preview a build is closed at once as an ENVIRONMENT outcome, never a product
failure; `environment` is recorded on the job; the credits go back."""
import ast
import os
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / 'omni_prod' / 'investor_app.py').read_text()
TREE = ast.parse(APP)
FUNCS = {n.name: n for n in TREE.body if isinstance(n, ast.FunctionDef)}


def load(*names):
    ns = {'os': os, 'PREVIEW_NO_BUILD_QUEUE': 'preview_no_build_queue'}
    for n in names:
        exec(ast.unparse(FUNCS[n]).replace('from .models import', 'from omni_prod.models import'), ns)
    return ns


class Environment(unittest.TestCase):
    def test_only_a_preview_without_a_queue(self):
        f = load('_preview_without_build_queue')['_preview_without_build_queue']
        cases = [({'VERCEL_ENV': 'preview'}, True), ({'VERCEL_ENV': 'preview', 'OMNI_REDIS_URL': 'redis://x'}, False),
                 ({'VERCEL_ENV': 'production'}, False), ({}, False)]
        for env, want in cases:
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertIs(f(), want, env)

    def test_the_job_carries_its_environment(self):
        src = ast.unparse(FUNCS['v28_build_async'])
        self.assertIn("'environment': _build_environment()", src)

    def test_closed_after_the_outbox_and_before_any_enqueue(self):
        src = ast.unparse(FUNCS['v28_build_async'])
        self.assertLess(src.index('jobs.create_outbox('), src.index('_preview_without_build_queue()'))
        self.assertLess(src.index('_preview_without_build_queue()'), src.index('enqueue_build('))


class Close(unittest.TestCase):
    def test_environment_code_words_and_credits_back(self):
        ns = load('_close_preview_build')
        jobs, subs = mock.Mock(), mock.Mock()
        ns['_v28'] = mock.Mock(subscriptions=subs)
        ns['logging'] = __import__('logging')
        ns['_close_preview_build'](jobs, 'bld_1')
        kw = jobs.transition.call_args.kwargs
        self.assertEqual(kw['error_code'], 'preview_no_build_queue')
        self.assertIn('not a product failure', kw['error_message'])
        self.assertEqual(kw['target'].value.lower(), 'failed')
        subs.release.assert_called_once_with(build_id='bld_1')

    def test_a_failed_close_never_raises(self):
        ns = load('_close_preview_build')
        jobs = mock.Mock(); jobs.transition.side_effect = RuntimeError('db')
        ns['_v28'] = mock.Mock(); ns['_v28'].subscriptions.release.side_effect = RuntimeError('db')
        ns['logging'] = __import__('logging')
        ns['_close_preview_build'](jobs, 'bld_1')


class CustomerWords(unittest.TestCase):
    def test_both_languages_say_environment_not_failure(self):
        js = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text()
        # Michael 2026-11-11: no internal term ("Preview") in what the customer reads.
        self.assertIn("preview_no_build_queue:'הבנייה לא רצה בגרסה הזאת — זו גרסת בדיקה בלי תור בנייה. הקרדיטים הוחזרו.'", js)
        self.assertIn("preview_no_build_queue:'The build did not run in this version: it is a test version", js)
        for line in js.splitlines():
            if 'preview_no_build_queue:' in line:
                said = line.split("preview_no_build_queue:'", 1)[1].split("'", 1)[0]
                self.assertNotIn('Preview', said)
        self.assertNotIn("preview_no_build_queue:'הבנייה נכשלה", js)

    def test_the_gap_is_written_down(self):
        doc = (ROOT / 'docs' / 'ops' / 'preview-isolation.md').read_text()
        self.assertIn('The Preview smoke does NOT cover the builder', doc)
        self.assertIn('**82**', doc)


if __name__ == '__main__':
    unittest.main()

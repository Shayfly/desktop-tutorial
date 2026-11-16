"""Michael 2026-11-15: the $10.53 is Vercel build minutes -- no preview builds for docs-only changes, no previews of
ci/v24-report. The real entry point (scripts/vercel_ignore_build.mjs, vercel.json ignoreCommand) runs in node with the
Vercel variables set; only `fetch` is replaced, and it answers with GitHub's real compare responses for three open PRs
of 2026-11-15 (tests/fixtures/vercel_compare_2026_11_15.json): #364 CLAUDE.md, #351 docs/spec, #363 workflow+script.
Exit 0 = Vercel skips, exit 1 = Vercel builds."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'vercel_ignore_build.mjs'
CASES = json.loads((ROOT / 'tests' / 'fixtures' / 'vercel_compare_2026_11_15.json').read_text())['cases']
SKIP, BUILD = 0, 1


def run(env, ref, sha='abc1234', answer=None, status=200, throw=False, message='', release=None):
    """Runs the script as Vercel does. `answer` is the compare body fetch returns; the URL it asked for is printed."""
    with tempfile.TemporaryDirectory() as tmp:
        stub = Path(tmp) / 'stub.mjs'
        stub.write_text(
            'globalThis.fetch = async (url) => { console.log("FETCH " + url);'
            f' if ({json.dumps(throw)}) throw new Error("network down");'
            f' return {{ ok: {json.dumps(status == 200)}, status: {status}, json: async () => ({json.dumps(answer)}) }}; }};\n')
        vars_ = {k: v for k, v in os.environ.items() if not k.startswith('VERCEL_')}
        vars_.update({'VERCEL_ENV': env, 'VERCEL_GIT_COMMIT_REF': ref, 'VERCEL_GIT_COMMIT_SHA': sha,
                      'VERCEL_GIT_REPO_OWNER': 'Shayfly', 'VERCEL_GIT_REPO_SLUG': 'desktop-tutorial',
                      'VERCEL_GIT_COMMIT_MESSAGE': message})
        vars_.pop('OMNI_RELEASE', None)
        if release is not None:
            vars_['OMNI_RELEASE'] = release
        p = subprocess.run(['node', '--import', stub.as_uri(), str(SCRIPT)], capture_output=True, text=True, env=vars_,
                           timeout=30)
    return p.returncode, p.stdout + p.stderr


@unittest.skipUnless(shutil.which('node'), 'node runs the Vercel ignore step')
class VercelIgnoredBuildStep(unittest.TestCase):
    def test_vercel_json_runs_the_script(self):
        self.assertEqual(json.loads((ROOT / 'vercel.json').read_text())['ignoreCommand'],
                         'node scripts/vercel_ignore_build.mjs')

    def test_docs_only_previews_are_skipped(self):
        for name, ref in (('docs', 'docs/claude-md'), ('spec', 'docs/delivery-gate-v2')):
            code, out = run('preview', ref, CASES[name]['head'], CASES[name])
            self.assertEqual(code, SKIP, out)
            self.assertIn(f"compare/main...{CASES[name]['head']}", out)      # the diff is read against main
            self.assertIn('SKIP', out)

    def test_a_code_change_builds_its_preview(self):
        code, out = run('preview', 'fix/refresh-no-push-to-main', CASES['code']['head'], CASES['code'])
        self.assertEqual(code, BUILD, out)
        self.assertIn('non-docs', out)

    def test_ci_v24_report_gets_no_preview_and_no_compare_call(self):
        code, out = run('preview', 'ci/v24-report', answer=CASES['code'])
        self.assertEqual(code, SKIP, out)
        self.assertNotIn('FETCH', out)

    def test_production_builds_only_a_release(self):
        # warehouse 111 (owner 2026-11-16): no automatic production deploy of every push to main. This test asserted the
        # opposite ("production always builds") -- it encoded the behaviour the owner stopped, and changes in the open.
        code, out = run('production', 'main', answer=CASES['code'], message='Merge pull request #406 from x/y')
        self.assertEqual(code, SKIP, out)
        self.assertIn('not a release', out)
        self.assertNotIn('FETCH', out)
        for kwargs, why in (({'message': 'Merge pull request #406 [release]'}, 'release commit'),

                            ({'release': '1'}, 'manual release')):
            code, out = run('production', 'main', answer=CASES['docs'], **kwargs)
            self.assertEqual(code, BUILD, (kwargs, out))
            self.assertIn(why, out)
        self.assertEqual(run('production', 'main', release='0', message='x')[0], SKIP)      # only "1" releases

    def test_the_mark_counts_only_at_the_end_of_the_title_line(self):
        # 2026-11-16: #413's merge (c38fbb4) went to production because its body quoted a title mentioning the mark
        for message in ("Merge pull request #413: warehouse 111 completed, the worker deploys only on a release\n\nwarehouse 111 completed: the build worker deploys only on a release ([release] or a manual run)", 'title\n\nbody [release]', 'about the [release] rule', '[release] at the start'):
            with self.subTest(message[:30]):
                self.assertEqual(run('production', 'main', message=message)[0], SKIP)
        self.assertEqual(run('production', 'main', message='Merge pull request #412 from x/y [release]  ')[0], BUILD)

    def test_previews_still_build_automatically(self):
        code, out = run('preview', 'fix/x', CASES['code']['head'], CASES['code'], message='no marker')
        self.assertEqual(code, BUILD, out)

    def test_a_rename_out_of_docs_is_code(self):
        answer = {'files': [{'filename': 'omni_prod/x.py', 'previous_filename': 'docs/x.py', 'status': 'renamed'}]}
        self.assertEqual(run('preview', 'b', answer=answer)[0], BUILD)
        answer = {'files': [{'filename': 'docs/x.md', 'previous_filename': 'omni_prod/x.md', 'status': 'renamed'}]}
        self.assertEqual(run('preview', 'b', answer=answer)[0], BUILD)

    def test_anything_unknown_builds_and_says_why(self):
        for kwargs, why in (({'status': 403}, 'compare HTTP 403'), ({'throw': True}, 'network down'),
                            ({'answer': {}}, 'without a file list'), ({'answer': {'files': []}}, 'empty diff'),
                            ({'answer': {'files': [{'filename': 'docs/a.md'}] * 300}}, 'truncated')):
            code, out = run('preview', 'docs/x', **kwargs)
            self.assertEqual(code, BUILD, (kwargs, out))
            self.assertIn(why, out)
        self.assertEqual(run('development', 'docs/x', answer=CASES['docs'])[0], BUILD)
        self.assertEqual(run('preview', 'docs/x', sha='', answer=CASES['docs'])[0], BUILD)


if __name__ == '__main__':
    unittest.main()

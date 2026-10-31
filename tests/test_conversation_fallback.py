"""2026-10-30: restoreConversation switched to the guided questionnaire on ANY error -- a network blip included --
and stayed there for the session. Only 503 conversation_not_ready (the conversation is not installed on this
server) may switch; anything else shows the error with a retry. Executes the real functions from app.js under node."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APP_JS = Path(__file__).resolve().parents[1] / 'omni_prod' / 'assets' / 'app.js'


def grab(src, pattern):
    m = re.search(pattern, src, re.S | re.M)
    assert m, pattern
    return m.group(0)


@unittest.skipUnless(shutil.which('node'), 'node is required to execute app.js restoreConversation()')
class RestoringTheConversation(unittest.TestCase):
    def run_js(self, failures):
        """`failures`: what each successive conversation GET throws (None = it succeeds)."""
        src = APP_JS.read_text(encoding='utf-8')
        code = '\n'.join([
            grab(src, r'^class ApiError extends Error \{.*?^\}'),
            grab(src, r'^function conversationNotInstalled\(e\) \{.*?^\}'),
            grab(src, r'^async function restoreConversation\(\) \{.*?^\}'),
        ])
        harness = f"""
const S = {{ lang: 'en' }}; const calls = []; const failures = {json.dumps(failures)};
const explain = e => 'EXPLAINED:' + (e.status || e.message); const t = k => k;
const convPath = () => '/conv'; const discPath = () => '/disc';
async function api(path) {{
  calls.push(path);
  if (path.startsWith('/disc')) return {{ questions: [] }};
  const f = failures.shift();
  if (f === null || f === undefined) return {{ messages: [{{ role: 'assistant', content: 'hi' }}] }};
  if (f.network) throw new TypeError('Failed to fetch');
  throw new ApiError(f.status, f.detail);
}}
const applyConversation = v => {{ S.chat = {{ messages: v.messages }}; }};
const renderChat = () => {{}}, renderDiscovery = () => {{}}, renderTabs = () => {{}};
{code}
(async () => {{
  const states = [];
  for (let i = 0; i < {len(failures)}; i++) {{ await restoreConversation(); states.push({{ ...S.chat }}); }}
  process.stdout.write(JSON.stringify({{ states, calls }}));
}})();
"""
        out = subprocess.run(['node', '-e', harness], capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_network_blip_shows_a_retry_and_does_not_switch_to_the_questionnaire(self):
        r = self.run_js([{'network': True}, None])
        first, second = r['states']
        self.assertTrue(first.get('retry'))
        self.assertFalse(first.get('fallback'))
        self.assertNotIn('/disc', r['calls'])
        self.assertEqual(second['messages'][0]['content'], 'hi')            # the retry restores the conversation

    def test_a_server_error_is_not_a_reason_to_switch(self):
        for status, detail in ((500, 'boom'), (503, {'error': 'durable_backend_required'}), (502, None)):
            with self.subTest(status=status):
                state = self.run_js([{'status': status, 'detail': detail}])['states'][0]
                self.assertFalse(state.get('fallback'))
                self.assertTrue(state.get('retry'))

    def test_only_conversation_not_ready_switches_to_the_questionnaire(self):
        r = self.run_js([{'status': 503, 'detail': {'error': 'conversation_not_ready'}}])
        self.assertTrue(r['states'][0].get('fallback'))
        self.assertIn('/disc?lang=en', r['calls'])


if __name__ == '__main__':
    unittest.main()

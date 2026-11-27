"""The customer's screen says what #542 changed (the owner, 2026-11-27): a character counter that reads the server's own
limit, "load earlier messages" on the paging route, and the tokens the content writing used.

Real paths: the real investor_app request model and conversation view (TestClient), the real MemoryConversationStore
and history_page, the real usage_summary and strip_internal_economics (the customer's view of the evidence), and the
real functions of omni_prod/assets/app.js executed under node (only the browser seams are stubbed)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
APP_JS = (ROOT / 'omni_prod' / 'assets' / 'app.js').read_text(encoding='utf-8')
INDEX = (ROOT / 'omni_prod' / 'assets' / 'index.html').read_text(encoding='utf-8')
NODE = shutil.which('node')
NEW_KEYS = ('charsLeft', 'charsAtLimit', 'loadEarlier', 'loadingEarlier', 'tokensNotMeasured')


def _fn(name: str) -> str:
    m = re.search(rf'^(?:async )?function {name}\(.*?^\}}', APP_JS, re.S | re.M)
    assert m, f'{name} not found in app.js'
    return m.group(0)


def run_js(body: str, *, extract=()) -> object:
    prelude = '''
const S = { projectId: 'p1', lang: 'he', chat: null };
const calls = []; let rendered = 0; const fields = { composerMsg: { textContent: '' } };
const $ = id => fields[id] || { textContent: '', getAttribute: () => '7777', value: '' };
const t = k => k; const explain = e => String(e && e.message || e);
const convPath = () => '/api/v28/projects/p1/conversation'; const stillOn = p => S.projectId === p;
const renderChat = () => { rendered++; };
const h = (tag, attrs, ...kids) => ({ tag, attrs, kids: kids.flat() });
let PAGES = [];
const api = async url => { calls.push(url); const p = PAGES.shift(); if (p instanceof Error) throw p; return p; };
let olderBusy = false;
'''
    warn = re.search(r'^const CHAT_COUNT_WARN_FROM = .*;$', APP_JS, re.M).group(0)      # the app's own number
    src = prelude + warn + '\n' + '\n'.join(_fn(n) for n in extract) + '\n(async () => {\n' + body + '\n})().catch(e => { console.error(e); process.exit(1); });'
    assert NODE, 'node is required to execute app.js (a missing node fails this test)'
    out = subprocess.run([NODE, '-e', src], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


class TheServerLimit(unittest.TestCase):
    """The counter's number is the one the server refuses at, read from the model that refuses."""

    def setUp(self):
        from fastapi.testclient import TestClient
        import omni_prod.investor_app as ia
        from omni_prod.conversation.store import MemoryConversationStore
        self.ia = ia
        s = MemoryConversationStore()
        for i in range(130):
            s.add_message(project_id='pA', account_id='A', role='customer', content=f'A{i}')
        brief = type('Repo', (), {'latest': lambda self, project_id: None})()

        def resolve(*, token, project_id):
            if (token, project_id) != ('tokA', 'pA'):
                raise PermissionError('project not owned')
            return type('Acc', (), {'id': 'A'})(), None
        for p in (mock.patch.object(ia, '_conversation_store', lambda: s), mock.patch.object(ia, '_brief_repo', lambda: brief),
                  mock.patch.object(ia._v28, 'resolve_project_key', resolve, create=True)):
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(ia.app)
        self.h = {'Authorization': 'Bearer tokA'}

    def view(self):
        r = self.client.get('/api/v28/projects/pA/conversation', headers=self.h)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_the_view_carries_the_limit_the_model_refuses_at(self):
        limit = self.view()['limits']['message_chars']
        self.assertEqual(limit, self.ia.CONVERSATION_MESSAGE_MAX_CHARS)
        over = self.client.post('/api/v28/projects/pA/conversation', headers=self.h, json={'message': 'x' * (limit + 1)})
        self.assertEqual(over.status_code, 422)                       # one character over the number is refused
        self.assertIn('at most', json.dumps(over.json()))
        self.assertEqual(self.ia.V28ConversationMessage(message='x' * limit).message, 'x' * limit)   # the number itself fits

    def test_the_box_in_the_page_has_the_same_number(self):
        m = re.search(r'<textarea id="chatInput"[^>]*maxlength="(\d+)"', INDEX)
        self.assertIsNotNone(m)
        self.assertEqual(int(m.group(1)), self.ia.CONVERSATION_MESSAGE_MAX_CHARS)

    def test_the_view_gives_the_cursor_the_button_uses(self):
        v = self.view()
        self.assertTrue(v['history']['has_older'])
        r = self.client.get(f"/api/v28/projects/pA/conversation/messages?before={v['history']['before']}&limit=100", headers=self.h)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(v['messages']) + len(r.json()['messages']), 130)    # nothing lost, nothing twice

    def test_a_field_without_exactly_one_bound_is_refused_out_loud(self):
        from pydantic import BaseModel, Field
        class M(BaseModel):
            a: str = Field(max_length=5)
            b: str = ''
        self.assertEqual(self.ia._field_max_chars(M, 'a'), 5)
        with self.assertRaises(RuntimeError):
            self.ia._field_max_chars(M, 'b')


class TheCounter(unittest.TestCase):
    def states(self, cases):
        return run_js(f'process.stdout.write(JSON.stringify({json.dumps(cases)}.map(([n, m]) => chatCountState(n, m))));',
                      extract=('chatCountState',))

    def test_silent_until_the_last_tenth_then_counts_down_then_stops(self):
        r = self.states([[0, 8000], [7199, 8000], [7200, 8000], [7999, 8000], [8000, 8000], [9000, 8000]])
        self.assertEqual([x['state'] for x in r], ['ok', 'ok', 'near', 'near', 'limit', 'limit'])
        self.assertEqual([x['left'] for x in r], [8000, 801, 800, 1, 0, 0])

    def test_no_known_limit_means_no_counter_never_a_guess(self):
        r = self.states([[10, None], [10, 0], [10, 'x'], [-1, 8000], [1.5, 8000]])
        self.assertEqual({x['state'] for x in r}, {'hidden'})

    def test_the_limit_comes_from_the_view_then_from_the_box_never_a_constant(self):
        body = '''
S.chat = { limits: { message_chars: 9000 } }; const a = chatLimit();
S.chat = {}; const b = chatLimit();
S.chat = { limits: { message_chars: 'abc' } }; const c = chatLimit();
process.stdout.write(JSON.stringify([a, b, c]));'''
        self.assertEqual(run_js(body, extract=('chatLimit',)), [9000, 7777, 7777])

    def test_the_text_is_in_all_three_languages_and_never_says_server(self):
        body = '''
const fs = require('fs'); const s = fs.readFileSync(%s, 'utf8');
globalThis.localStorage = { getItem: () => null }; globalThis.window = globalThis; globalThis.document = {};
const T = new Function(s.slice(s.indexOf('const T = {'), s.indexOf('const $ = id =>')) + ';return T;')();
const out = {};
for (const lang of ['he', 'en', 'ar']) {
  out[lang] = {};
  for (const k of %s) { const v = T[lang][k]; out[lang][k] = typeof v === 'function' ? v('1,234') : v; }
}
process.stdout.write(JSON.stringify(out));''' % (json.dumps(str(ROOT / 'omni_prod/assets/app.js')), json.dumps(list(NEW_KEYS)))
        out = run_js(body)
        for lang, texts in out.items():
            for k, v in texts.items():
                with self.subTest(lang=lang, key=k):
                    self.assertTrue(isinstance(v, str) and v.strip(), f'{lang}.{k} is missing')
                    self.assertNotIn('שרת', v)
                    self.assertNotIn('server', v.lower())
                    self.assertNotIn('خادم', v)
        self.assertIn('1,234', out['he']['charsLeft'])
        self.assertNotEqual(out['he']['charsLeft'], out['en']['charsLeft'])
        self.assertNotEqual(out['ar']['loadEarlier'], out['en']['loadEarlier'])

    def test_the_counter_is_driven_by_every_write_to_the_box(self):
        self.assertRegex(APP_JS, r'function autoGrow\(\).*updateChatCount\(\); \}')     # every write to the box calls autoGrow
        self.assertIn('S.chat = keepLoadedOlder(view);\n  updateChatCount();', APP_JS)
        self.assertIn('input.maxLength = max', _fn('updateChatCount'))
        self.assertIn('[...input.value].length', _fn('updateChatCount'))      # characters, as the server counts them
        self.assertIn('id="chatCount"', INDEX)


class TheEarlierMessages(unittest.TestCase):
    def pages(self, n_latest=3):
        """The real history_page over a real store, shaped as the route shapes it."""
        from omni_prod.conversation.store import MemoryConversationStore, history_page
        s = MemoryConversationStore()
        for i in range(250):
            s.add_message(project_id='p1', account_id='a', role='customer', content=f'm{i}')
        shape = lambda m: {'id': m['id'], 'role': m['role'], 'content': m['content']}   # noqa: E731
        return s, shape, history_page

    def test_following_the_button_reaches_every_message_once(self):
        s, shape, history_page = self.pages()
        first = history_page(s, 'p1', shape=shape)
        second = history_page(s, 'p1', before=first['before'], shape=shape)
        third = history_page(s, 'p1', before=second['before'], shape=shape)
        body = f'''
PAGES = {json.dumps([second, third])};
S.chat = {{ messages: {json.dumps(first['messages'])}, history: {{ has_older: true, before: {first['before']} }} }};
await loadEarlier(); const afterOne = S.chat.messages.length; const urlOne = calls[0];
await loadEarlier();
process.stdout.write(JSON.stringify({{ afterOne, total: S.chat.messages.length,
  ids: S.chat.messages.map(m => m.id), history: S.chat.history, calls, busy: olderBusy, keep: S.keepScroll }}));'''
        r = run_js(body, extract=('loadEarlier',))
        self.assertEqual(r['afterOne'], 200)
        self.assertEqual(r['total'], 250)
        self.assertEqual(r['ids'], sorted(set(r['ids'])))                # in order, no message twice
        self.assertEqual(r['history'], {'has_older': False, 'before': None})
        self.assertEqual(r['calls'][0], f"/api/v28/projects/p1/conversation/messages?before={first['before']}&limit=100&lang=he")
        self.assertIn(f"before={second['before']}", r['calls'][1])
        self.assertFalse(r['busy'])

    def test_a_failed_read_is_said_and_changes_nothing(self):
        body = '''
PAGES = [Object.assign(new Error('network'), { status: 0 })];
S.chat = { messages: [{ id: 5, content: 'a' }], history: { has_older: true, before: 5 } };
await loadEarlier();
process.stdout.write(JSON.stringify({ n: S.chat.messages.length, msg: fields.composerMsg.textContent, busy: olderBusy, more: S.chat.history.has_older }));'''
        r = run_js(body, extract=('loadEarlier',))
        self.assertEqual((r['n'], r['msg'], r['busy'], r['more']), (1, 'network', False, True))

    def test_a_page_that_is_not_a_page_is_refused_not_shown(self):
        body = '''
PAGES = [{ messages: 'x', has_older: true }];
S.chat = { messages: [{ id: 5, content: 'a' }], history: { has_older: true, before: 5 } };
await loadEarlier();
process.stdout.write(JSON.stringify({ n: S.chat.messages.length, msg: fields.composerMsg.textContent }));'''
        r = run_js(body, extract=('loadEarlier',))
        self.assertEqual(r['n'], 1)
        self.assertTrue(r['msg'])

    def test_a_page_that_brings_nothing_new_ends_the_walk(self):
        body = '''
PAGES = [{ messages: [{ id: 5, content: 'a' }], has_older: true, before: 5 }];
S.chat = { messages: [{ id: 5, content: 'a' }], history: { has_older: true, before: 5 } };
await loadEarlier();
process.stdout.write(JSON.stringify(S.chat.history));'''
        self.assertEqual(run_js(body, extract=('loadEarlier',)), {'has_older': False, 'before': None})

    def test_a_second_click_while_reading_does_nothing(self):
        body = '''
PAGES = [{ messages: [{ id: 1, content: 'z' }], has_older: false, before: null }];
S.chat = { messages: [{ id: 5, content: 'a' }], history: { has_older: true, before: 5 } };
await Promise.all([loadEarlier(), loadEarlier()]);
process.stdout.write(JSON.stringify({ calls: calls.length }));'''
        self.assertEqual(run_js(body, extract=('loadEarlier',)), {'calls': 1})

    def test_older_messages_survive_the_next_answer_when_the_pages_touch(self):
        body = '''
S.olderLoaded = [{ id: 1 }, { id: 2 }]; S.olderHistory = { has_older: false, before: null }; S.olderBound = 3;
const touching = keepLoadedOlder({ messages: [{ id: 3 }, { id: 4 }], history: { has_older: true, before: 3 } });
S.olderLoaded = [{ id: 1 }, { id: 2 }]; S.olderHistory = { has_older: false, before: null }; S.olderBound = 3;
const gap = keepLoadedOlder({ messages: [{ id: 300 }], history: { has_older: true, before: 300 } });
process.stdout.write(JSON.stringify({ touching: touching.messages.map(m => m.id), touchingHist: touching.history,
  gap: gap.messages.map(m => m.id), gapHist: gap.history, cleared: S.olderLoaded }));'''
        r = run_js(body, extract=('keepLoadedOlder',))
        self.assertEqual(r['touching'], [1, 2, 3, 4])
        self.assertEqual(r['touchingHist'], {'has_older': False, 'before': None})
        self.assertEqual(r['gap'], [300])                                # a gap is never bridged with a guess
        self.assertEqual(r['gapHist'], {'has_older': True, 'before': 300})
        self.assertEqual(r['cleared'], [])

    def test_the_button_is_drawn_only_with_an_older_page_and_is_wired(self):
        chat = _fn('renderChat')
        self.assertIn('S.chat.history.has_older', chat)
        self.assertIn('onclick: loadEarlier', chat)
        self.assertIn("t('loadEarlier')", chat)
        self.assertIn('/messages?before=', _fn('loadEarlier'))


class TheUsageLine(unittest.TestCase):
    def evidence(self, calls):
        from omni_prod.customer_views import strip_internal_economics
        from omni_prod.site_content.agents import usage_summary
        return strip_internal_economics({'site_route': {'content_usage': usage_summary(calls)}})   # the customer's view

    def line(self, ev):
        r = run_js(f'process.stdout.write(JSON.stringify(contentUsageRows({json.dumps(ev)})));', extract=('contentUsageRows',))
        return r

    @staticmethod
    def call(tin, tout):
        return {'role': 'writer', 'max_tokens': 1, 'measured': True, 'attempts': [{
            'model': 'm', 'outcome': 'ok', 'input_tokens': tin, 'output_tokens': tout, 'metered_cost_usd': '0.01',
            'max_tokens_sent': 1, 'model_maximum': 2, 'finish_reason': 'stop',
            'truncated_at_model_maximum': False, 'truncated_at_budget_allowance': False}]}

    def test_the_measured_tokens_are_shown_in_the_customers_evidence(self):
        ev = self.evidence([self.call(1200, 3400), self.call(300, 100)])
        self.assertEqual(ev['site_route']['content_usage']['input_tokens'], 1500)   # survives the customer's view
        self.assertNotIn('metered_cost_usd', json.dumps(ev))                        # the cost does not
        rows = self.line(ev)
        self.assertEqual([r['kids'] for r in rows], [['tokens'], ['1,500 / 3,500']])

    def test_a_total_the_platform_could_not_measure_is_said_not_shown_as_zero(self):
        ev = self.evidence([self.call(1200, None)])
        self.assertIsNone(ev['site_route']['content_usage']['output_tokens'])
        self.assertEqual(self.line(ev)[1]['kids'], ['tokensNotMeasured'])

    def test_no_content_usage_no_line(self):
        for ev in ({}, {'site_route': None}, {'site_route': {}}, {'site_route': {'content_usage': 'x'}}):
            with self.subTest(ev=ev):
                self.assertEqual(self.line(ev), [])

    def test_the_evidence_panel_shows_the_line(self):
        self.assertIn('...contentUsageRows(ev)', _fn('renderEvidence'))


if __name__ == '__main__':
    unittest.main()

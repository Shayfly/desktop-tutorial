"""The whole conversation can be read, a page at a time (the owner, 2026-11-26, WAREHOUSE 136 option a: the screen got
only the last 100 messages and nothing reached the ones before).

The real store.history_page on the real MemoryConversationStore, and the real PostgresConversationStore.messages_before
on a recording pool (its SQL); the route and the view call the same function (read from investor_app's source here,
because importing the app needs its whole web stack)."""
import re
import unittest
from pathlib import Path

from omni_prod.conversation.store import (HISTORY_PAGE, MemoryConversationStore, PostgresConversationStore,
                                          history_page)

ROOT = Path(__file__).resolve().parent.parent


def store_with(n: int, project='p1'):
    s = MemoryConversationStore()
    s.add_message(project_id=project, account_id='a', role='assistant', content='', interpretation={'system': 'flow'})
    for i in range(n):
        s.add_message(project_id=project, account_id='a', role='customer' if i % 2 == 0 else 'assistant',
                      content=f'הודעה {i}')
    s.add_message(project_id='other', account_id='b', role='customer', content='לא שלכם')
    return s


class TheHistoryIsPaged(unittest.TestCase):
    def test_every_message_is_reached_by_following_the_cursor(self):
        store = store_with(250)
        seen, before, pages = [], None, 0
        for _ in range(10):                                     # bounded: 251 rows need three pages of 100
            page = history_page(store, 'p1', before=before)
            seen = [m['content'] for m in page['messages']] + seen
            pages += 1
            if not page['has_older']:
                self.assertIsNone(page['before'])
                break
            before = page['before']
        self.assertEqual(pages, 3)
        self.assertEqual(seen, [f'הודעה {i}' for i in range(250)])      # all 250, in order, the flow mark not shown

    def test_the_first_page_is_the_latest_hundred(self):
        page = history_page(store_with(250), 'p1')
        self.assertEqual(len(page['messages']), HISTORY_PAGE)
        self.assertEqual(page['messages'][-1]['content'], 'הודעה 249')
        self.assertTrue(page['has_older'])
        self.assertEqual(page['before'], page['messages'][0]['id'])

    def test_a_short_conversation_has_nothing_older(self):
        page = history_page(store_with(5), 'p1')
        self.assertEqual((len(page['messages']), page['has_older'], page['before']), (5, False, None))

    def test_another_projects_messages_never_appear(self):
        page = history_page(store_with(3), 'p1', limit=50)
        self.assertNotIn('לא שלכם', [m['content'] for m in page['messages']])

    def test_a_bad_page_request_is_refused_out_loud(self):
        for kw in ({'limit': 0}, {'limit': HISTORY_PAGE + 1}, {'before': 0}, {'before': 'x'}):
            with self.subTest(kw), self.assertRaises(ValueError):
                history_page(store_with(3), 'p1', **kw)

    def test_the_postgres_store_reads_the_page_before_the_cursor(self):
        seen = []

        class Conn:
            def execute(self, sql, params):
                seen.append((' '.join(sql.split()), params))
                return type('R', (), {'fetchall': lambda self: []})()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        pool = type('P', (), {'connection': lambda self: Conn()})()
        PostgresConversationStore(pool).messages_before('p1', 151, 101)
        self.assertIn('FROM intake_messages WHERE project_id = %s AND id < %s ORDER BY id DESC LIMIT %s', seen[0][0])
        self.assertEqual(seen[0][1], ('p1', 151, 101))

    def test_the_view_and_the_route_use_it(self):
        source = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        self.assertIn("@app.get('/api/v28/projects/{project_id}/conversation/messages')", source)
        view = source.split('def _conversation_view(', 1)[1].split('\ndef ', 1)[0]
        self.assertIn('history_page(store, project_id, shape=_conversation_message)', view)
        self.assertIn("'history': {'has_older': page['has_older'], 'before': page['before']}", view)
        self.assertIsNone(re.search(r'messages_for\(project_id, limit=100\)', view))
        route = source.split('def v28_conversation_history(', 1)[1].split('\n@app.', 1)[0]
        self.assertIn('_discovery_account(request, project_id)', route)       # the owner of the project only


class TheRoute(unittest.TestCase):
    """Review S2 (2026-11-26): the real route through the app (TestClient); only the account resolution and the store
    are the seams. Another account's project is a 403, never its messages; a bad cursor or size is
    invalid_history_page."""

    def setUp(self):
        from unittest import mock
        from fastapi.testclient import TestClient
        import omni_prod.investor_app as ia
        s = MemoryConversationStore()
        for i in range(5):
            s.add_message(project_id='pA', account_id='A', role='customer', content=f'A{i}')
        for i in range(5):
            s.add_message(project_id='pB', account_id='B', role='customer', content=f'SECRET-B{i}')
        own = {('tokA', 'pA'): 'A', ('tokB', 'pB'): 'B'}

        def resolve(*, token, project_id):
            if (token, project_id) not in own:
                raise PermissionError('project not owned')
            return type('Acc', (), {'id': own[(token, project_id)]})(), None
        for p in (mock.patch.object(ia, '_conversation_store', lambda: s),
                  mock.patch.object(ia._v28, 'resolve_project_key', resolve, create=True)):
            p.start()
            self.addCleanup(p.stop)
        self.client = TestClient(ia.app)

    def get(self, token, query=''):
        return self.client.get(f'/api/v28/projects/{"pB" if token == "tokA-on-B" else "pA"}/conversation/messages{query}',
                               headers={'Authorization': f'Bearer {"tokA" if token == "tokA-on-B" else token}'})

    def test_the_owner_reads_the_pages(self):
        r = self.get('tokA', '?limit=2')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([m['content'] for m in r.json()['messages']], ['A3', 'A4'])
        older = self.get('tokA', f"?before={r.json()['before']}&limit=2").json()
        self.assertEqual([m['content'] for m in older['messages']], ['A1', 'A2'])

    def test_another_accounts_project_is_refused(self):
        r = self.get('tokA-on-B')
        self.assertEqual(r.status_code, 403)
        self.assertNotIn('SECRET', r.text)

    def test_a_cursor_never_reaches_another_projects_messages(self):
        r = self.get('tokA', '?before=10')                                # 10 is one of B's ids
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('SECRET', r.text)

    def test_a_bad_cursor_or_size_is_invalid_history_page(self):
        for q in ('?before=abc', '?before=0', '?before=-5', '?limit=0', '?limit=1000', '?limit=x'):
            with self.subTest(q):
                r = self.get('tokA', q)
                self.assertEqual((r.status_code, r.json()['detail']['error']), (422, 'invalid_history_page'))


if __name__ == '__main__':
    unittest.main()

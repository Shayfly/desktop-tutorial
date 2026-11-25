"""Warehouse 128.4 on the real stores: the customer's original file is the evidence a reading draft is bound to, and a
draft whose file is gone cannot be approved.

A REAL PostgreSQL (M4D2_DATABASE_URL): a fresh database per run with every repository migration applied (as
tests/test_first_agent_brief_slice_pg.py does). The attachment rows (migration 038), the brief revisions
(PostgresBriefRepository) and the conversation (PostgresConversationStore) are the production stores; the bytes are in
an in-process object store with the same put/get/delete contract as the project bucket (tests/test_visual_edit.py).
The conversation runs on the real ConversationSupervisor; no model is called (a fixed answer stands for the reader).
Skipped -- not faked -- without PostgreSQL; the intake-budget-pg job runs it, in its own process.
"""
import pathlib
import os
import unittest
import uuid

from omni_prod import attachments as A
from omni_prod.conversation.supervisor import ConversationSupervisor
from omni_prod.intake import media_reading as MR
from tests.test_media_reading_128 import NOTE, Fixed, png
from tests.test_visual_edit import MemoryStore, _pg_skip, DATABASE_URL


@unittest.skipIf(_pg_skip(), _pg_skip())
class TheStoredFileIsTheEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        from omni_prod.db import DatabasePool
        from omni_prod.migration_runner import apply_migrations
        from omni_prod.migrations import discover_migrations
        root = pathlib.Path(__file__).resolve().parents[1]
        cls.admin = psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=5)
        cls.dbname = f'mr128_{uuid.uuid4().hex[:10]}'
        cls.admin.execute(f'CREATE DATABASE {cls.dbname}')
        cls.url = DATABASE_URL.rsplit('/', 1)[0] + '/' + cls.dbname
        with psycopg.connect(cls.url) as conn:
            apply_migrations(conn, discover_migrations(root / 'infra' / 'postgres'))
        cls.pool = DatabasePool(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.pool.close()
        cls.admin.execute(f'DROP DATABASE IF EXISTS {cls.dbname} WITH (FORCE)')
        cls.admin.close()

    def setUp(self):
        from omni_prod.brief_repository import PostgresBriefRepository
        from omni_prod.conversation.store import PostgresConversationStore
        self.p, self.a = f'prj_{uuid.uuid4().hex[:8]}', f'usr_{uuid.uuid4().hex[:8]}'
        with self.pool.connection() as conn:
            conn.execute('INSERT INTO creator_accounts (id, email, password_hash, salt_b64) VALUES (%s,%s,%s,%s)',
                         (self.a, f'{self.a}@example.com', 'x', 'x'))
            conn.execute("INSERT INTO creator_projects (id, owner_id, title) VALUES (%s, %s, 't')", (self.p, self.a))
            conn.commit()
        self.objects = MemoryStore()
        self.repo = A.AttachmentRepository(self.pool, self.objects)
        self.briefs, self.store = PostgresBriefRepository(self.pool), PostgresConversationStore(self.pool)
        self.sup = ConversationSupervisor(briefs=self.briefs, store=self.store)

    def evidence(self, account=None):
        return lambda att_id: A.public(self.repo.get(project_id=self.p, account_id=account or self.a,
                                                     attachment_id=att_id))

    def upload_and_read(self, data):
        row = self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=data)
        stored = self.repo.read(row)                          # integrity-checked against the row's digest
        turn = self.sup.read_attachment(project_id=self.p, account_id=self.a, attachment=A.public(row), data=stored,
                                        purpose=MR.NOTE, reader=Fixed({'language': 'he', 'text': NOTE}), lang='he')
        return row, turn

    def approve(self, turn, evidence):
        return self.sup.approve_reading(project_id=self.p, account_id=self.a, evidence=evidence,
                                        draft_fingerprint=turn.actions[0]['draft_fingerprint'])

    def test_the_draft_is_bound_to_the_stored_row_and_its_bytes(self):
        row, t = self.upload_and_read(png(9, 7))
        src = t.interpretation['reading_draft']['source']
        self.assertEqual((src['attachment_id'], src['sha256']), (row['id'], row['sha256']))
        self.assertEqual(self.objects.objects[row['storage_key']], png(9, 7))      # the original bytes, kept
        r = self.approve(t, self.evidence())
        self.assertNotEqual(r.intent, 'reading_failed', r.reply)
        self.assertIn('מאפיית לחם הבית', self.briefs.latest(self.p).brief.prompt)

    def test_a_deleted_file_cannot_be_approved_and_still_holds_the_build(self):
        row, t = self.upload_and_read(png(8, 8))
        self.repo.delete(project_id=self.p, account_id=self.a, attachment_id=row['id'])
        r = self.approve(t, self.evidence())
        self.assertEqual(r.intent, 'reading_failed')
        self.assertEqual(r.interpretation['reading_failed']['code'], 'evidence_missing')
        self.assertIsNone(self.briefs.latest(self.p))
        self.assertEqual(len(MR.pending_drafts(self.store.messages_for(self.p))), 1)

    @unittest.skipUnless(__import__('importlib').util.find_spec('fastapi'), 'fastapi is required to import the app')
    def test_the_route_reads_the_stored_file_and_answers_in_a_sentence(self):
        """POST .../attachments/{id}/reading as production runs it today (OMNI_MEDIA_READER unset = off): the route
        reads the row and its bytes from the real store, the customer gets one sentence with the next action, and
        the conversation keeps which file it was. Only the sign-in, the object bucket and the two conversation
        stores are stand-ins; the route, the attachment repository on PostgreSQL and the supervisor are real."""
        from types import SimpleNamespace
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from omni_prod import investor_app as IA
        row = self.repo.create(project_id=self.p, account_id=self.a, kind='image', data=png(5, 4))
        env = {k: v for k, v in os.environ.items() if k != 'OMNI_MEDIA_READER'}
        with patch.object(IA, '_owner', return_value=(SimpleNamespace(id=self.a), 'k')), \
                patch.object(IA, '_attachments', return_value=self.repo), \
                patch.object(IA, '_conversation_store', return_value=self.store), \
                patch.object(IA, '_brief_repo', return_value=self.briefs), \
                patch.object(IA, '_supervisor', return_value=self.sup), \
                patch.dict(os.environ, env, clear=True):
            client = TestClient(IA.app)
            r = client.post(f'/api/v28/projects/{self.p}/attachments/{row["id"]}/reading',
                            json={'purpose': MR.NOTE})
            missing = client.post(f'/api/v28/projects/{self.p}/attachments/att_{"0" * 32}/reading',
                                  json={'purpose': MR.NOTE})
        self.assertEqual(r.status_code, 200, r.text)
        view = r.json()
        self.assertEqual(view['turn']['intent'], 'reading_failed')
        self.assertEqual(view['turn']['reply'], MR.failure_sentence('not_connected', MR.NOTE, 'he'))
        self.assertEqual([(m['role'], m['attachments']) for m in view['messages']],
                         [('customer', [{'id': row['id'], 'kind': 'image'}]), ('assistant', [])])
        stored = self.store.messages_for(self.p)[-1]['interpretation']['reading_failed']
        self.assertEqual((stored['code'], stored['attachment_id'], stored['sha256']),
                         ('not_connected', row['id'], row['sha256']))
        self.assertEqual(missing.status_code, 404)

    @unittest.skipUnless(__import__('importlib').util.find_spec('fastapi'), 'fastapi is required to import the app')
    def test_the_approve_route_checks_the_stored_file(self):
        """POST .../readings/{fingerprint}/approve: the route's own evidence lookup on the real store. A deleted file
        cannot be approved; the draft of a file still saved enters the request."""
        from types import SimpleNamespace
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from omni_prod import investor_app as IA
        gone_row, gone = self.upload_and_read(png(6, 6))
        kept_row, kept = self.upload_and_read(png(6, 7))
        self.repo.delete(project_id=self.p, account_id=self.a, attachment_id=gone_row['id'])
        with patch.object(IA, '_owner', return_value=(SimpleNamespace(id=self.a), 'k')), \
                patch.object(IA, '_attachments', return_value=self.repo), \
                patch.object(IA, '_conversation_store', return_value=self.store), \
                patch.object(IA, '_brief_repo', return_value=self.briefs), \
                patch.object(IA, '_supervisor', return_value=self.sup):
            client = TestClient(IA.app)
            url = f'/api/v28/projects/{self.p}/readings/{{}}/approve'
            r_gone = client.post(url.format(gone.actions[0]['draft_fingerprint']), json={})
            self.assertIsNone(self.briefs.latest(self.p))
            # the earlier draft still waits: discard it, then approve the one whose file is saved
            client.post(url.replace('approve', 'discard').format(gone.actions[0]['draft_fingerprint']), json={})
            r_kept = client.post(url.format(kept.actions[0]['draft_fingerprint']), json={})
        self.assertEqual(r_gone.status_code, 200, r_gone.text)
        self.assertEqual(r_gone.json()['turn']['reply'], MR.failure_sentence('evidence_missing', MR.NOTE, 'he'))
        self.assertEqual(r_kept.status_code, 200, r_kept.text)
        self.assertNotEqual(r_kept.json()['turn']['intent'], 'reading_failed', r_kept.json()['turn']['reply'])
        self.assertIn('מאפיית לחם הבית', self.briefs.latest(self.p).brief.prompt)
        self.assertEqual(MR.pending_drafts(self.store.messages_for(self.p)), [])

    def test_another_accounts_store_is_not_evidence(self):
        _, t = self.upload_and_read(png(7, 9))
        r = self.approve(t, self.evidence(account=f'acc_{uuid.uuid4().hex[:8]}'))
        self.assertEqual(r.interpretation['reading_failed']['code'], 'evidence_missing')
        self.assertIsNone(self.briefs.latest(self.p))


if __name__ == '__main__':
    unittest.main()

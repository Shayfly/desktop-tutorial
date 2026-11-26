"""More images per message and per project (the owner, 2026-11-26, WAREHOUSE 136 option a: a count is not money).

The real AttachmentRepository on a recording pool and store (no database or bucket here): 20 images in one message
and 200 live in a project; one more is the same loud 422/409 as before, at the new bound. The size checks that
protect the request path stay: 3 MiB per image, 8000 px a side (one image per upload request, under the 4.5 MB
body a Vercel function accepts). The browser's own cap is in omni_prod/assets/visual-edit.js (the shell's file):
its MAX_IMAGES must follow (the report says so)."""
import hashlib
import re
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace

from omni_prod import attachments as A

ROOT = Path(__file__).resolve().parent.parent


def png(w=4, h=3) -> bytes:
    return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', w, h) + b'\x08\x02\x00\x00\x00'


class Pool:
    """Answers the live-count query with `live`; returns a row for the insert."""

    def __init__(self, live):
        self.live, self.sql = live, []
        outer = self

        class Conn:
            def execute(self, sql, params=()):
                outer.sql.append(' '.join(sql.split()))
                if 'count(*)' in sql:
                    return SimpleNamespace(fetchone=lambda: (outer.live,))
                return SimpleNamespace(fetchone=lambda: params[:10] + ('{}', 'NOT_ANALYZED', 'now'))

            def transaction(self):
                return self

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        self.conn = Conn()

    def connection(self):
        return self.conn


class Store:
    def put_bytes(self, key, data):
        return SimpleNamespace(key=key, sha256=hashlib.sha256(data).hexdigest())


class TheCounts(unittest.TestCase):
    def test_the_bounds(self):
        self.assertEqual((A.MAX_PER_MESSAGE, A.MAX_LIVE_PER_PROJECT), (20, 200))
        self.assertEqual((A.MAX_BYTES, A.MAX_SIDE), (3 * 1024 * 1024, 8000))          # unchanged

    def test_twenty_images_in_one_message_and_one_more_is_refused(self):
        repo = A.AttachmentRepository(Pool(0), Store())
        repo.get = lambda **kw: {'id': kw['attachment_id']}
        ids = [f'att_{i:032x}' for i in range(20)]
        self.assertEqual(len(repo.many(project_id='p', account_id='a', ids=ids)), 20)
        with self.assertRaises(A.AttachmentError) as caught:
            repo.many(project_id='p', account_id='a', ids=ids + ['att_' + 'f' * 32])
        self.assertEqual((caught.exception.code, str(caught.exception)), ('too_many', 'at most 20 images per message'))

    def test_the_two_hundredth_image_is_kept_and_the_next_one_is_refused(self):
        row = A.AttachmentRepository(Pool(199), Store()).create(project_id='p', account_id='a', kind='image',
                                                                 data=png())
        self.assertTrue(row['id'].startswith('att_'))
        with self.assertRaises(A.AttachmentError) as caught:
            A.AttachmentRepository(Pool(200), Store()).create(project_id='p', account_id='a', kind='image', data=png())
        self.assertEqual((caught.exception.code, caught.exception.status), ('too_many', 409))

    def test_an_image_over_three_mib_is_still_refused(self):
        with self.assertRaises(A.AttachmentError):
            A.validate_image(png() + b'\x00' * A.MAX_BYTES)

    def test_the_message_routes_take_twenty_ids(self):
        source = (ROOT / 'omni_prod' / 'investor_app.py').read_text(encoding='utf-8')
        found = re.findall(r'attachment_ids: list\[str\] = Field\(default_factory=list, max_length=(\d+)\)', source)
        self.assertEqual(found, [str(A.MAX_PER_MESSAGE)] * 2)                    # a message and a change request


if __name__ == '__main__':
    unittest.main()

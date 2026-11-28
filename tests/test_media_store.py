"""S13.1/S13.2: the tenant media store on the REAL omni_prod.storage.S3ArtifactStore (boto3 client, R2 options), with only
the network call replaced by a bucket in memory. No provider, no network, no database (the rights gate is tested on
PostgreSQL in tests/test_media_infra_pg.py).

Fixtures are real files made by the repository's own code (a PNG from the image encoder the tests already use is not
needed: the bytes below are minimal valid headers, which is what the sniffer reads)."""
from __future__ import annotations

import hashlib
import io
import struct
import unittest
import zlib
from urllib.parse import parse_qs, urlsplit

from omni_prod.artifact_keys import build_media_key, media_key_prefix
from omni_prod.media_store import MAX_LINK_SECONDS, MediaError, MediaNotFound, MediaRef, TenantMediaStore, sniff
from omni_prod.storage import S3ArtifactStore


def png(width=2, height=2) -> bytes:
    def chunk(tag, body):
        return struct.pack('>I', len(body)) + tag + body + struct.pack('>I', zlib.crc32(tag + body))
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * width for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


MP4 = b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2' + b'\x00' * 64
WAV = b'RIFF' + struct.pack('<I', 36) + b'WAVEfmt ' + b'\x00' * 40
GLB = b'glTF' + struct.pack('<II', 2, 12) + b'\x00' * 8


class Bucket:
    """The network call only: put_object / get_object of the boto3 client the real store holds."""
    def __init__(self):
        self.objects: dict[str, tuple[bytes, dict]] = {}
        self.reads: list[str] = []

    def put_object(self, *, Bucket, Key, Body, Metadata):
        self.objects[Key] = (bytes(Body.read() if hasattr(Body, 'read') else Body), dict(Metadata))

    def get_object(self, *, Bucket, Key):
        self.reads.append(Key)
        if Key not in self.objects:
            class NoSuchKey(Exception):
                response = {'Error': {'Code': 'NoSuchKey'}}
            raise NoSuchKey(Key)
        data, meta = self.objects[Key]
        return {'Body': io.BytesIO(data), 'Metadata': meta}


def real_store() -> tuple[S3ArtifactStore, Bucket]:
    store = S3ArtifactStore(endpoint='https://acct.r2.cloudflarestorage.com', bucket='media',
                            access_key='AKIAEXAMPLEEXAMPLE0', secret_key='x' * 40)
    bucket = Bucket()
    store.client.put_object, store.client.get_object = bucket.put_object, bucket.get_object
    return store, bucket


class Allow:
    def require(self, **_):
        return None


class Keys(unittest.TestCase):
    def test_the_key_is_under_the_account_and_project_and_named_by_the_digest(self):
        digest = hashlib.sha256(b'x').hexdigest()
        self.assertEqual(build_media_key(account_id='usr_A1', project_id='prj_1', sha256=digest, ext='mp4'),
                         f'tenants/usr_A1/projects/prj_1/media/{digest}.mp4')
        self.assertEqual(media_key_prefix('usr_A1'), 'tenants/usr_A1/')

    def test_an_unsafe_segment_a_short_digest_and_an_unknown_type_are_refused(self):
        digest = 'a' * 64
        for kwargs in ({'account_id': '../x'}, {'project_id': 'a/b'}, {'sha256': 'abc'}, {'ext': 'exe'}):
            args = {'account_id': 'usr_A1', 'project_id': 'prj_1', 'sha256': digest, 'ext': 'png', **kwargs}
            with self.assertRaises(ValueError):
                build_media_key(**args)


class Sniff(unittest.TestCase):
    def test_each_type_is_read_from_its_bytes(self):
        self.assertEqual(sniff(png()), 'image/png')
        self.assertEqual(sniff(MP4), 'video/mp4')
        self.assertEqual(sniff(WAV), 'audio/wav')
        self.assertEqual(sniff(GLB), 'model/gltf-binary')
        self.assertEqual(sniff(b'ID3\x04' + b'\x00' * 20), 'audio/mpeg')
        self.assertEqual(sniff(b'\x1aE\xdf\xa3' + b'\x00' * 20), 'video/webm')

    def test_a_jpeg_is_not_taken_for_an_mp3(self):
        self.assertEqual(sniff(b'\xff\xd8\xff\xe0' + b'\x00' * 30 + b'\xff\xc0\x00\x0b\x08\x00\x10\x00\x10\x01\x01\x11\x00'), 'image/jpeg')

    def test_text_is_refused(self):
        with self.assertRaises(MediaError):
            sniff(b'<html>not media</html>')


class Store(unittest.TestCase):
    def setUp(self):
        self.s3, self.bucket = real_store()
        self.alice = TenantMediaStore(self.s3, 'usr_alice', rights=Allow())
        self.bob = TenantMediaStore(self.s3, 'usr_bob', rights=Allow())

    def test_a_file_round_trips_under_its_owners_key(self):
        ref = self.alice.put('prj_1', MP4, 'video/mp4')
        self.assertEqual(ref.key, f'tenants/usr_alice/projects/prj_1/media/{hashlib.sha256(MP4).hexdigest()}.mp4')
        self.assertEqual(self.alice.read(ref), MP4)
        self.assertEqual(self.alice.deliver(ref), MP4)

    def test_another_accounts_reference_is_the_unknown_answer_and_the_bucket_is_never_asked(self):
        ref = self.alice.put('prj_1', png(), 'image/png')
        self.bucket.reads.clear()
        with self.assertRaises(MediaNotFound):
            self.bob.read(ref)
        with self.assertRaises(MediaNotFound):
            self.bob.deliver(ref)
        with self.assertRaises(MediaNotFound):
            self.bob.link(ref)
        self.assertEqual(self.bucket.reads, [], 'a foreign key must not reach the object store: that is the existence oracle')

    def test_a_missing_object_and_a_foreign_one_read_the_same(self):
        ghost = MediaRef(key=build_media_key(account_id='usr_alice', project_id='prj_1', sha256='c' * 64, ext='png'),
                         sha256='c' * 64, size=10, mime='image/png')
        foreign = self.alice.put('prj_1', png(), 'image/png')
        errors = []
        for store, ref in ((self.alice, ghost), (self.bob, foreign)):
            with self.assertRaises(MediaNotFound) as caught:
                store.read(ref)
            errors.append(str(caught.exception))
        self.assertEqual(errors[0], errors[1])

    def test_two_accounts_with_the_same_bytes_hold_two_objects(self):
        a, b = self.alice.put('prj_1', png(), 'image/png'), self.bob.put('prj_1', png(), 'image/png')
        self.assertNotEqual(a.key, b.key)
        self.assertEqual(len(self.bucket.objects), 2)

    def test_a_reference_that_disagrees_with_itself_is_refused(self):
        ref = self.alice.put('prj_1', png(), 'image/png')
        for bad in (MediaRef(ref.key, 'f' * 64, ref.size, ref.mime), MediaRef(ref.key, ref.sha256, ref.size, 'video/mp4'),
                    MediaRef('projects/prj_1/' + ref.sha256 + '.png', ref.sha256, ref.size, ref.mime),
                    MediaRef(ref.key, ref.sha256, 0, ref.mime), MediaRef(ref.key, ref.sha256, 10 ** 12, ref.mime)):
            with self.assertRaises(MediaNotFound):
                self.alice.read(bad)

    def test_bytes_that_changed_in_the_bucket_are_not_delivered(self):
        ref = self.alice.put('prj_1', png(), 'image/png')
        data, meta = self.bucket.objects[ref.key]
        self.bucket.objects[ref.key] = (data[:-1] + b'\x00', {})            # same size, other bytes, no stored digest
        with self.assertRaises(MediaNotFound):
            self.alice.read(ref)

    def test_a_larger_object_than_the_reference_says_stops_at_the_bound(self):
        ref = self.alice.put('prj_1', png(), 'image/png')
        self.bucket.objects[ref.key] = (png(40, 40), {})
        with self.assertRaises(Exception) as caught:
            self.alice.read(ref)
        self.assertIn('exceeds maximum size', str(caught.exception))

    def test_what_is_not_the_claimed_type_is_not_stored(self):
        with self.assertRaises(MediaError):
            self.alice.put('prj_1', b'<html></html>', 'image/png')
        with self.assertRaises(MediaError):
            self.alice.put('prj_1', MP4, 'image/png')
        with self.assertRaises(MediaError):
            self.alice.put('prj_1', b'', 'image/png')
        with self.assertRaises(MediaError):
            self.alice.put('prj_1', MP4, 'application/zip')
        self.assertEqual(self.bucket.objects, {})

    def test_a_file_over_its_kinds_limit_is_not_stored(self):
        from omni_prod import media_store
        with self.assertRaises(MediaError):
            self.alice.put('prj_1', png() + b'\x00' * media_store.TYPES['image/png'][2], 'image/png')
        self.assertEqual(self.bucket.objects, {})

    def test_the_signed_link_is_ours_and_lives_at_most_five_minutes(self):
        ref = self.alice.put('prj_1', MP4, 'video/mp4')
        url = self.alice.link(ref)
        parts = urlsplit(url)
        self.assertEqual(parts.hostname, 'acct.r2.cloudflarestorage.com')
        self.assertIn(ref.key, parts.path)
        self.assertEqual(parse_qs(parts.query)['X-Amz-Expires'], [str(MAX_LINK_SECONDS)])
        self.assertEqual(MAX_LINK_SECONDS, 300)
        for seconds in (MAX_LINK_SECONDS + 1, 0, 3600):
            with self.assertRaises(ValueError):
                self.alice.link(ref, expires_seconds=seconds)

    def test_without_a_rights_gate_nothing_is_delivered_or_linked(self):
        bare = TenantMediaStore(self.s3, 'usr_alice')
        ref = bare.put('prj_1', MP4, 'video/mp4')
        with self.assertRaises(RuntimeError):
            bare.deliver(ref)
        with self.assertRaises(RuntimeError):
            bare.link(ref)


if __name__ == '__main__':
    unittest.main()

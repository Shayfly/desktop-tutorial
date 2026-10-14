import io
import json
from urllib.error import HTTPError

import pytest

from omni_prod.providers.image_provider import MemorySubmissionJournal


def service(transport, journal=None, store=None):
    from omni_prod.providers.replicate_image_test import ReplicateImageTest
    return ReplicateImageTest(env={'REPLICATE_API_TOKEN': 'test-only'},
        journal=journal or MemorySubmissionJournal(), store=store, urlopen=transport)


def test_paid_submit_is_fixed_single_image_and_survives_new_process():
    calls = []
    def transport(req, timeout):
        calls.append(req)
        assert req.full_url.endswith('/models/black-forest-labs/flux-schnell/predictions')
        body = json.loads(req.data)
        assert body['input']['num_outputs'] == 1
        return io.BytesIO(b'{"id":"test-task","status":"starting"}')
    journal = MemorySubmissionJournal()
    first = service(transport, journal).start('account-one', confirmed=True)
    second = service(transport, journal).start('account-one', confirmed=True)
    assert first['task_id'] == second['task_id'] == 'test-task'
    assert first['maximum_usd'] == '0.003'
    assert len(calls) == 1


def test_no_confirmation_or_missing_token_never_calls_provider():
    def forbidden(*args, **kwargs):
        raise AssertionError('must not call')
    with pytest.raises(ValueError):
        service(forbidden).start('account-one', confirmed=False)
    from omni_prod.providers.replicate_image_test import ReplicateImageTest
    with pytest.raises(ValueError):
        ReplicateImageTest(env={}, journal=MemorySubmissionJournal(), store=None,
            urlopen=forbidden).start('account-one', confirmed=True)


def test_unknown_submit_outcome_is_never_replayed():
    calls = []
    def broken(req, timeout):
        calls.append(req)
        raise TimeoutError('private token error')
    journal = MemorySubmissionJournal()
    with pytest.raises(TimeoutError):
        service(broken, journal).start('account-one', confirmed=True)
    from omni_prod.providers.image_provider import AmbiguousSubmission
    with pytest.raises(AmbiguousSubmission):
        service(broken, journal).start('account-one', confirmed=True)
    assert len(calls) == 1


def test_no_task_status_is_read_only_and_account_isolation():
    journal = MemorySubmissionJournal()
    obj = service(lambda req, timeout: io.BytesIO(b'{"id":"one"}'), journal)
    assert obj.status('other')['status'] == 'NOT_STARTED'
    assert not journal._rows
    obj.start('account-one', confirmed=True)
    assert obj.status('other')['status'] == 'NOT_STARTED'


def test_routes_refuse_unauthenticated_paid_calls():
    from fastapi.testclient import TestClient
    from omni_prod.investor_app import app
    client = TestClient(app)
    for method, path in [('post', '/api/v28/providers/replicate/image-test'),
                         ('get', '/api/v28/providers/replicate/image-test'),
                         ('get', '/api/v28/providers/replicate/image-test/image')]:
        assert getattr(client, method)(path, **({'json': {'confirmed': True}} if method == 'post' else {})).status_code == 401


def test_verified_image_is_saved_and_retrievable_without_provider_after_restart():
    from omni_prod.providers.replicate_image_test import ReplicateImageTest
    png = b'\x89PNG\r\n\x1a\n' + b'\0\0\0\rIHDR' + b'\0\0\0\1\0\0\0\1'
    class Store:
        def __init__(self): self.rows = {}
        def get_bytes(self, key): return self.rows[key]
        def put_bytes(self, key, data): self.rows[key] = data
    class Fetcher:
        def get(self, url, headers):
            assert not headers
            return png, 'image/png'
    def transport(req, timeout):
        return io.BytesIO(b'{"id":"one","status":"succeeded","output":["https://replicate.delivery/test.png"]}')
    store, journal = Store(), MemorySubmissionJournal()
    obj = ReplicateImageTest(env={'REPLICATE_API_TOKEN':'test-only'}, journal=journal,
        store=store, urlopen=transport, fetcher=Fetcher())
    obj.provider.sleep = lambda _: None
    obj.start('account-one', confirmed=True)
    assert obj.status('account-one')['generation_verified'] is True
    def forbidden(*args, **kwargs): raise AssertionError('cached result must not require Replicate')
    restored = service(forbidden, journal, store)
    assert restored.status('account-one')['generation_verified'] is True
    assert restored.image('account-one') == (png, 'image/png')
    with pytest.raises(KeyError): restored.image('other-account')


def test_storage_probe_uses_required_object_access_not_bucket_admin():
    class Store:
        def ping(self): raise AssertionError('bucket permission is not required')
        def put_bytes(self, key, data): self.key, self.data = key, data
        def get_bytes(self, key):
            assert key == self.key
            return self.data
    obj = service(lambda *args: None, store=Store())
    assert obj.check_storage('account-one') == {'verified': True}


def test_storage_probe_returns_only_safe_failure_category():
    from botocore.exceptions import ClientError
    class Store:
        def put_bytes(self, key, data):
            raise ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'private credentials'}}, 'PutObject')
    result = service(lambda *args: None, store=Store()).check_storage('account-one')
    assert result == {'verified': False, 'operation': 'write', 'category': 'AccessDenied'}
    assert 'private' not in json.dumps(result)

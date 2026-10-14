import pytest
from omni_prod.storage import S3ArtifactStore


def test_r2_put_is_signed_without_unsupported_chunked_checksum():
    store = S3ArtifactStore(endpoint='https://example.r2.cloudflarestorage.com',
        bucket='test-bucket', access_key='test-only', secret_key='test-only')
    class Captured(Exception): pass
    observed = {}
    def capture(request, **kwargs):
        observed.update({k.lower(): v for k, v in request.headers.items()})
        raise Captured()
    store.client.meta.events.register('before-send.s3.PutObject', capture)
    with pytest.raises(Captured): store.put_bytes('probe', b'148AI signing test')
    assert 'x-amz-sdk-checksum-algorithm' not in observed
    assert b'aws-chunked' not in observed.get('content-encoding', b'')
    assert b'STREAMING-' not in observed.get('x-amz-content-sha256', b'')
    assert observed['authorization'].startswith(b'AWS4-HMAC-SHA256 ')
    assert 'x-amz-meta-sha256' in observed


def test_standard_s3_configuration_is_preserved():
    store = S3ArtifactStore(endpoint='https://s3.example.com', bucket='test-bucket',
        access_key='test-only', secret_key='test-only', region='eu-west-1')
    assert store.client.meta.region_name == 'eu-west-1'
    assert store.client.meta.config.request_checksum_calculation == 'when_supported'

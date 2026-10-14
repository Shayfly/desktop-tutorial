import json
from omni_prod.storage import S3ArtifactStore
from omni_prod.providers.replicate_image_test import r2_config_diagnostic


def test_diagnostic_detects_loaded_secret_mismatch_without_disclosing_credentials():
    store = S3ArtifactStore(endpoint='https://example.r2.cloudflarestorage.com',
        bucket='test-bucket', access_key='test-access', secret_key='old-test-secret')
    result = r2_config_diagnostic({'OMNI_S3_ACCESS_KEY': ' test-access ',
        'OMNI_S3_SECRET_KEY': 'new-test-secret'}, store)
    assert result['environment_matches_client'] is False
    assert result['client']['access_key'] == result['environment']['access_key']
    assert result['client']['secret_key'] != result['environment']['secret_key']
    for credential in ('test-access', 'old-test-secret', 'new-test-secret'):
        assert credential not in json.dumps(result)


def test_diagnostic_reads_only_configuration_without_object_requests():
    store = S3ArtifactStore(endpoint='https://example.r2.cloudflarestorage.com',
        bucket='test-bucket', access_key='test-access', secret_key='test-secret')
    store.client.meta.events.register('before-send', lambda **kw: (_ for _ in ()).throw(AssertionError('Network forbidden')))
    result = r2_config_diagnostic({'OMNI_S3_ACCESS_KEY': 'test-access',
        'OMNI_S3_SECRET_KEY': 'test-secret', 'HTTPS_PROXY': 'private-proxy-password'}, store)
    assert result['environment_matches_client'] is True
    assert result['ambient_variable_names'] == ['HTTPS_PROXY']
    assert 'private-proxy-password' not in json.dumps(result)
    assert result['configuration']['region'] == 'auto'
    assert result['configuration']['signature_version'] == 's3v4'

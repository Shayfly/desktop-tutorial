import io
import json

from omni_prod.model_gateway import (ModelEndpoint, OpenAICompatibleGateway,
                                     idempotency_key_for)

class FakeResponse(io.BytesIO):
    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

def _ok():
    return {'id': 'r1', 'choices': [{'message': {'content': 'ok'}, 'finish_reason': 'stop'}]}

def _endpoint():
    return ModelEndpoint(name='p', base_url='https://x/v1', model='m', api_key='k', external=True)

def _gateway(seen):
    def urlopen(req, timeout=None):
        seen.update({k.lower(): v for k, v in req.headers.items()})
        return FakeResponse(_ok())
    return OpenAICompatibleGateway(_endpoint(), urlopen=urlopen)

def test_key_is_sent_and_kept():
    seen = {}
    gw = _gateway(seen)
    key = idempotency_key_for(build_id='b', task='codegen', attempt=2)
    gw.complete(system='s', user='u', idempotency_key=key)
    assert seen.get('idempotency-key') == key
    assert gw.last_idempotency_key == key

def test_no_key_no_header():
    seen = {}
    gw = _gateway(seen)
    gw.complete(system='s', user='u')
    assert 'idempotency-key' not in seen
    assert gw.last_idempotency_key is None

def test_key_is_deterministic_and_distinct():
    a = idempotency_key_for(build_id='b', task='t', attempt=1)
    assert a == idempotency_key_for(build_id='b', task='t', attempt=1)
    assert a != idempotency_key_for(build_id='b', task='t', attempt=2)

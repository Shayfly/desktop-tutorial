import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['DATA_DIR'] = tempfile.mkdtemp()
import app  # noqa: E402


def post(payload):
    body = json.dumps(payload).encode()
    seen = {}
    environ = {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/api/matches', 'CONTENT_LENGTH': str(len(body)),
               'wsgi.input': io.BytesIO(body)}
    out = app.app(environ, lambda status, headers: seen.setdefault('status', int(status.split()[0])))
    return seen['status'], json.loads(b''.join(out))


def test_fractional_score_rejected():
    status, _ = post({'score': '2.9'})
    assert status == 400


def test_boolean_score_rejected():
    status, _ = post({'score': True})
    assert status == 400


def test_integer_score_accepted():
    status, body = post({'score': 7})
    assert status == 201 and body['score'] == 7

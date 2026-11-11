"""Repair repro fixture (founder 2026-11-01). Built from the QA-review TEXT of rehearsal run 39313029465
("POST /api/matches converts scores with int(), so fractional scores such as 2.9 and boolean values are
accepted"), NOT from that run's files: they were never kept (issue #202). The bug is intentional."""
import json
import os
import sqlite3
from wsgiref.simple_server import make_server

DATA_DIR = os.environ.get('DATA_DIR', '/tmp/repair-repro-data')


def _db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(os.path.join(DATA_DIR, 'league.db'))
    conn.execute('CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, score INTEGER NOT NULL)')
    return conn


def create_match(payload):
    score = int(payload["score"])
    with _db() as conn:
        cur = conn.execute('INSERT INTO matches (score) VALUES (?)', (score,))
        return 201, {'id': cur.lastrowid, 'score': score}


def app(environ, start_response):
    if environ['REQUEST_METHOD'] == 'POST' and environ['PATH_INFO'] == '/api/matches':
        size = int(environ.get('CONTENT_LENGTH') or 0)
        payload = json.loads(environ['wsgi.input'].read(size) or b'{}')
        status, body = create_match(payload)
    else:
        status, body = 404, {'error': 'not found'}
    start_response(f'{status} {"Created" if status == 201 else "Error"}', [('Content-Type', 'application/json')])
    return [json.dumps(body).encode()]


if __name__ == '__main__':
    make_server('0.0.0.0', int(os.environ.get('PORT', '8000')), app).serve_forever()

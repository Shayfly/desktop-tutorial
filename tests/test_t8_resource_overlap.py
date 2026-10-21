"""T8 (founder 2026-10-21): a bookable resource is protected by the SERVER, inside one transaction.

Two real fixture apps (stdlib + SQLite, ThreadingHTTPServer) run as processes:
  * LOCKED  follows the data-integrity skill: BEGIN IMMEDIATE -> SELECT the resource row -> overlap SELECT ->
            INSERT/UPDATE, plus BEFORE INSERT/UPDATE triggers; UTC stored (Z), Asia/Jerusalem shown;
  * NAIVE   checks, then inserts, with no transaction and no trigger (what "the page blocks it" looks like on the
            server); the gap between check and insert is widened so the race is reproducible.
The real acceptance runner fires two identical POSTs released by one barrier (`concurrent: 2`): exactly one must be
accepted. The edit path is checked the same way, and the stored UTC time is checked for a winter and a summer date.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from omni_prod.web_saas_acceptance import WebSaaSAcceptanceRunner, _validate_plan

APP = r'''
import json, os, sqlite3, sys, time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo
NAIVE = os.environ.get("NAIVE") == "1"
TZ = ZoneInfo("Asia/Jerusalem")
DB = os.path.join(os.environ["DATA_DIR"], "app.db")

def conn():
    c = sqlite3.connect(DB, timeout=10, isolation_level=None)
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY, name TEXT NOT NULL, capacity INTEGER NOT NULL);
    INSERT OR IGNORE INTO resources (id, name, capacity) VALUES (1, 'room', 1);
    CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, resource_id INTEGER NOT NULL,
        start_utc TEXT NOT NULL, end_utc TEXT NOT NULL, title TEXT NOT NULL);
    """)
    if not NAIVE:
        c.executescript("""
        CREATE TRIGGER IF NOT EXISTS no_overlap_ins BEFORE INSERT ON bookings
        WHEN EXISTS (SELECT 1 FROM bookings b WHERE b.resource_id = NEW.resource_id
                     AND b.start_utc < NEW.end_utc AND b.end_utc > NEW.start_utc)
        BEGIN SELECT RAISE(ABORT, 'overlap'); END;
        CREATE TRIGGER IF NOT EXISTS no_overlap_upd BEFORE UPDATE ON bookings
        WHEN EXISTS (SELECT 1 FROM bookings b WHERE b.resource_id = NEW.resource_id AND b.id != NEW.id
                     AND b.start_utc < NEW.end_utc AND b.end_utc > NEW.start_utc)
        BEGIN SELECT RAISE(ABORT, 'overlap'); END;
        """)

def utc_range(body):
    local = datetime.fromisoformat(body["date"] + "T" + body["start"]).replace(tzinfo=TZ)
    start = local.astimezone(timezone.utc)
    end = start + timedelta(minutes=60)
    z = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    return z(start), z(end)

def view(row):
    s = datetime.strptime(row["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    e = datetime.strptime(row["end_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return {"id": row["id"], "title": row["title"], "start_utc": row["start_utc"], "end_utc": row["end_utc"],
            "start_local": s.astimezone(TZ).isoformat(), "end_local": e.astimezone(TZ).isoformat()}

def save(body, booking_id=None):
    start, end = utc_range(body)
    c = conn()
    try:
        if not NAIVE:
            c.execute("BEGIN IMMEDIATE")                       # the write lock BEFORE the read (FOR UPDATE)
            c.execute("SELECT id FROM resources WHERE id = 1").fetchone()
        clash = c.execute("SELECT id FROM bookings WHERE resource_id = 1 AND start_utc < ? AND end_utc > ?"
                          " AND id != ?", (end, start, booking_id or -1)).fetchone()
        if clash:
            if not NAIVE: c.execute("ROLLBACK")
            return 409, {"error": "החדר תפוס בשעה הזו"}
        if NAIVE:
            time.sleep(0.4)                                    # the window a real server has under load
        if booking_id is None:
            cur = c.execute("INSERT INTO bookings (resource_id, start_utc, end_utc, title) VALUES (1, ?, ?, ?)",
                            (start, end, body["title"]))
            booking_id = cur.lastrowid
        else:
            c.execute("UPDATE bookings SET start_utc = ?, end_utc = ?, title = ? WHERE id = ?",
                      (start, end, body["title"], booking_id))
        if not NAIVE: c.execute("COMMIT")
        return (201 if body.get("_new", True) else 200), view(c.execute("SELECT * FROM bookings WHERE id = ?",
                                                                         (booking_id,)).fetchone())
    except sqlite3.IntegrityError:
        if not NAIVE: c.execute("ROLLBACK")
        return 409, {"error": "החדר תפוס בשעה הזו"}
    finally:
        c.close()

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(data)
    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
    def do_GET(self):
        self._send(200, {"ok": True})
    def do_POST(self):
        code, obj = save(self._body()); self._send(code, obj)
    def do_PUT(self):
        b = self._body(); b["_new"] = False
        code, obj = save(b, int(self.path.rsplit("/", 1)[1])); self._send(code, obj)
    def log_message(self, *a): pass

init()
ThreadingHTTPServer(("127.0.0.1", int(os.environ["PORT"])), H).serve_forever()
'''

WINTER = {'date': '2026-11-05', 'start': '10:00', 'title': 'ישיבת צוות'}     # Asia/Jerusalem UTC+2 -> 08:00Z
SUMMER = {'date': '2027-07-05', 'start': '10:00', 'title': 'ישיבה בקיץ'}     # UTC+3 -> 07:00Z
AIDS = ['A1', 'A2', 'A3']
CONTRACT = {'acceptance': [{'id': a} for a in AIDS]}
PLAN = [{'id': 'staff', 'steps': [
    {'id': 'parallel_create', 'kind': 'data_create', 'acceptance_ids': ['A1'], 'method': 'POST', 'path': '/api/bookings',
     'json': WINTER, 'concurrent': 2, 'expect_status': 201, 'expect_conflict_status': 409,
     'expect_json_contains': {'start_utc': '2026-11-05T08:00:00Z', 'start_local': '2026-11-05T10:00:00+02:00'},
     'capture': {'first': 'id'}},
    {'id': 'summer_utc', 'kind': 'data_create', 'acceptance_ids': ['A3'], 'method': 'POST', 'path': '/api/bookings',
     'json': SUMMER, 'expect_status': 201,
     'expect_json_contains': {'start_utc': '2027-07-05T07:00:00Z', 'start_local': '2027-07-05T10:00:00+03:00'},
     'capture': {'second': 'id'}},
    {'id': 'edit_onto_other', 'kind': 'data_update', 'acceptance_ids': ['A2'], 'method': 'PUT',
     'path': '/api/bookings/${second}', 'json': {**WINTER, 'start': '10:30'}, 'expect_status': 409},
    {'id': 'parallel_edit', 'kind': 'data_update', 'acceptance_ids': ['A2'], 'method': 'PUT',
     'path': '/api/bookings/${second}', 'json': {**SUMMER, 'start': '12:00'}, 'concurrent': 2, 'expect_status': 200,
     'expect_accepted': 2, 'expect_conflict_status': 409},
]}]


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


def run_app(naive: bool):
    root = tempfile.mkdtemp()
    open(os.path.join(root, 'app.py'), 'w', encoding='utf-8').write(APP)
    port = free_port()
    env = dict(os.environ, PORT=str(port), DATA_DIR=root, NAIVE='1' if naive else '0')
    proc = subprocess.Popen([sys.executable, 'app.py'], cwd=root, env=env, stderr=subprocess.PIPE)
    for _ in range(100):
        try:
            socket.create_connection(('127.0.0.1', port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    return proc, f'http://127.0.0.1:{port}'


def verify(naive: bool):
    proc, url = run_app(naive)
    try:
        report = WebSaaSAcceptanceRunner(required_kinds=('data_create', 'data_update')).verify(
            {'preview_url': url}, CONTRACT, PLAN)
    finally:
        proc.terminate()
        proc.communicate(timeout=5)
    return {c.step_id: c for c in report.checks}


class T8ResourceOverlap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.locked, cls.naive = verify(naive=False), verify(naive=True)

    def test_the_plan_with_concurrent_steps_is_valid(self):
        self.assertIsNone(_validate_plan(PLAN, set(AIDS)))

    def test_two_parallel_creates_one_accepted_on_the_locked_server(self):
        c = self.locked['parallel_create']
        self.assertTrue(c.passed, c.detail)
        self.assertIn('[201, 409]', c.detail.replace('409, 201', '201, 409'))

    def test_the_naive_server_accepts_both_and_is_caught(self):
        c = self.naive['parallel_create']
        self.assertFalse(c.passed)
        self.assertIn('expected exactly 1 x HTTP 201', c.detail)
        self.assertIn('[201, 201]', c.detail)

    def test_an_edit_onto_another_booking_is_refused(self):
        self.assertTrue(self.locked['edit_onto_other'].passed, self.locked['edit_onto_other'].detail)

    def test_utc_is_stored_and_asia_jerusalem_is_shown_winter_and_summer(self):
        self.assertTrue(self.locked['summer_utc'].passed, self.locked['summer_utc'].detail)
        self.assertTrue(self.locked['parallel_create'].passed)     # its expect_json_contains holds the winter values

    def test_a_concurrent_edit_of_the_same_booking_to_a_free_slot_is_not_a_conflict(self):
        self.assertTrue(self.locked['parallel_edit'].passed, self.locked['parallel_edit'].detail)


class ConcurrentStepValidation(unittest.TestCase):
    def step(self, **kw):
        base = {'id': 's', 'kind': 'data_create', 'acceptance_ids': ['A1'], 'method': 'POST', 'path': '/x'}
        return _validate_plan([{'id': 'p', 'steps': [{**base, **kw}]}], {'A1'})

    def test_bounds(self):
        self.assertIsNone(self.step(concurrent=2))
        self.assertIn('2 to 5', self.step(concurrent=1))
        self.assertIn('2 to 5', self.step(concurrent=9))
        self.assertIn('POST, PUT or PATCH', self.step(concurrent=2, method='GET'))
        self.assertIn('expect_accepted', self.step(concurrent=2, expect_accepted=3))


if __name__ == '__main__':
    unittest.main()

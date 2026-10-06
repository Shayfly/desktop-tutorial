from contextlib import contextmanager
from unittest.mock import patch
import pytest
from omni_prod.db import DatabasePool, transaction


def test_pool_checks_connections_before_handing_them_to_requests():
    # Exercise the driver boundary: simulate a stale checkout and require the
    # configured driver health check to run before application work begins.
    events = []
    class DriverPool:
        @staticmethod
        def check_connection(conn):
            events.append('checked')
        def __init__(self, **options):
            self.check = options.get('check')
        @contextmanager
        def connection(self, **options):
            conn = object()
            if self.check:
                self.check(conn)
            yield conn
    with patch('psycopg_pool.ConnectionPool', DriverPool):
        with DatabasePool('postgresql://test').connection():
            assert events == ['checked']


def test_failed_transaction_is_not_replayed():
    events = []
    class Conn:
        @contextmanager
        def transaction(self):
            events.append('begin')
            yield
    pool = DatabasePool('postgresql://test')
    class DriverPool:
        @contextmanager
        def connection(self, **options):
            yield Conn()
    pool._pool = DriverPool()
    with pytest.raises(RuntimeError):
        with transaction(pool):
            events.append('write')
            raise RuntimeError('connection lost after write')
    assert events == ['begin', 'write']

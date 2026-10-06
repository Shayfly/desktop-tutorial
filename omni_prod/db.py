from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import time
from typing import Any

def connect(database_url: str, *, connect_timeout_seconds: int = 5):
    import psycopg
    return psycopg.connect(
        database_url,
        connect_timeout=connect_timeout_seconds,
    )

@dataclass
class DatabasePool:
    database_url: str
    min_size: int = 2
    max_size: int = 10
    timeout_seconds: float = 10.0
    connect_timeout_seconds: int = 5
    _pool: Any = None

    def open(self) -> "DatabasePool":
        if self._pool is not None:
            return self
        from psycopg_pool import ConnectionPool
        self._pool = ConnectionPool(
            conninfo=self.database_url,
            min_size=self.min_size,
            max_size=self.max_size,
            timeout=self.timeout_seconds,
            kwargs={"connect_timeout": self.connect_timeout_seconds},
            # Reject connections closed while the serverless process was idle.
            check=ConnectionPool.check_connection,
            open=True,
        )
        return self

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    @contextmanager
    def connection(self):
        if self._pool is None:
            self.open()
        with self._pool.connection(timeout=self.timeout_seconds) as conn:
            yield conn

    def wait_until_ready(
        self,
        *,
        attempts: int = 5,
        base_delay_seconds: float = 0.25,
    ) -> None:
        if attempts < 1:
            raise ValueError("attempts must be >=1")
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                with self.connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        row = cur.fetchone()
                        if row and row[0] == 1:
                            return
            except Exception as exc:
                last_error = exc
            if attempt < attempts:
                time.sleep(base_delay_seconds * (2 ** (attempt - 1)))
        raise RuntimeError("database pool did not become ready") from last_error

@contextmanager
def transaction(database: str | DatabasePool, *, connect_timeout_seconds: int = 5):
    """
    Transactions are NOT automatically retried: replaying arbitrary writes can
    duplicate side effects. Retry belongs at idempotent command/job boundaries.
    """
    if isinstance(database, DatabasePool):
        with database.connection() as conn:
            with conn.transaction():
                yield conn
        return

    conn = connect(database, connect_timeout_seconds=connect_timeout_seconds)
    try:
        with conn.transaction():
            yield conn
    finally:
        conn.close()

def ping(database: str | DatabasePool) -> bool:
    try:
        with transaction(database) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                return bool(row and row[0] == 1)
    except Exception:
        return False


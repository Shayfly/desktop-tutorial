"""needs_env (the owner, 2026-11-15 22:50): the measured list in tests/needs_env.txt is marked `needs_env`.

A listed MODULE fails at import here (no fastapi/psycopg), so it cannot carry a marker: under -m "not needs_env" it is
not collected at all; without that expression (CI) it is collected as before. A listed TEST gets the marker and is
deselected by the same expression. Nothing else changes: with no -m, every test is collected and run as today.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_LIST = Path(__file__).resolve().parent / 'needs_env.txt'


def _entries() -> tuple[set[str], set[str]]:
    lines = [l.strip() for l in _LIST.read_text(encoding='utf-8').splitlines()
             if l.strip() and not l.lstrip().startswith('#')]
    return {l for l in lines if '::' not in l}, {l for l in lines if '::' in l}


MODULES, NODE_IDS = _entries()


def _excluding(config) -> bool:
    expr = (config.getoption('markexpr', '') or '').replace(' ', '')
    return 'notneeds_env' in expr


def pytest_ignore_collect(collection_path, config):
    if not _excluding(config):
        return None
    try:
        rel = Path(collection_path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return None
    return True if rel in MODULES else None


def pytest_collection_modifyitems(config, items):
    import pytest
    for item in items:
        if item.nodeid in NODE_IDS or item.nodeid.split('::')[0] in MODULES:
            item.add_marker(pytest.mark.needs_env)

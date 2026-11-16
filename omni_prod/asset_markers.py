"""No raw 148ai-asset:// address reaches the browser (production 2026-11-16, "148 דלתות", bld_426addd3).

A `148ai-asset://` address is a placeholder the platform writes into the build prompt: the uploaded logo
(`148ai-asset://logo`), the customer's own photos (`148ai-asset://upload/N`) and the generated images
(`148ai-asset://image/N`). After generation and after every repair, the engine's repository transform replaces each
placeholder it was given with the verified bytes (a data URI), before the sandbox runs (autonomous_core.build).

In production the transform for the customer's photo was never installed (the binding line was not read from the
contract prompt), so the page carried src="148ai-asset://upload/1": the browser does not know the scheme, and the hero
was a broken image. Two repair rounds made it worse -- one tried to swap the address for an http URL ("Unexpected
identifier 'http'"), one left the image invisible -- and both were discarded.

This gate reads the repository exactly as the sandbox receives it. Any placeholder still there was given no bytes:
- one the approved request placed is stopped earlier and louder (uploaded_assets.install_main_image raises
  UPLOAD_MARKER_UNBOUND before generation), so a repair is never asked to fix the platform;
- one the model invented (an image number the prompt never gave) fails the round with the file, the address and the
  rule, and the repair removes it.
A page with a real URL or a data URI passes.
"""
from __future__ import annotations

import re

from .autonomous_core import AcceptanceFailure, ExecutionReport

SCHEME = '148ai-asset://'
CODE = 'ASSET_MARKER_UNRESOLVED'
ACCEPTANCE_ID = 'asset-marker'
# what the browser loads: pages, scripts, styles, data files, a page served from app.py
SERVED = ('.html', '.htm', '.js', '.mjs', '.cjs', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.py', '.css', '.json',
          '.svg', '.webmanifest')
_MARKER = re.compile(r'148ai-asset://[A-Za-z0-9_./-]*')
MAX_LISTED = 10


def _code(path: str, source: str) -> str:
    """The source without comments; when a file cannot be read that way, the whole file (never a silent pass)."""
    from .generated_images import _strip_comments
    stripped = _strip_comments(path, source)
    return stripped if stripped or not source.strip() else source


def unresolved(repository: dict) -> list[tuple[str, str]]:
    """(path, address) of every 148ai-asset:// address left in a file the browser loads, in path order."""
    found: list[tuple[str, str]] = []
    for path in sorted(repository or {}):
        source = repository[path]
        if not isinstance(source, str) or not path.lower().endswith(SERVED) or SCHEME not in source:
            continue
        for address in dict.fromkeys(_MARKER.findall(_code(path, source))):
            found.append((path, address))
    return found


def failure(found: list[tuple[str, str]]) -> AcceptanceFailure:
    listed = '; '.join(f'{path}: src "{address}"' for path, address in found[:MAX_LISTED])
    more = f' (and {len(found) - MAX_LISTED} more)' if len(found) > MAX_LISTED else ''
    return AcceptanceFailure(ACCEPTANCE_ID, (
        f'{CODE}: {listed}{more}. A 148ai-asset:// address is not a real file: the browser cannot load it and shows a '
        'broken image. Use only the image src values the prompt gives, exactly as given; never invent a '
        '148ai-asset:// address, and never replace a given one with an http URL.'))


class AssetMarkerExecutor:
    """Wraps the engine's executor: the round fails while any 148ai-asset:// address is left in a served file."""

    def __init__(self, inner):
        self._inner = inner
        self.last_found: list[tuple[str, str]] = []

    def __getattr__(self, name):
        return getattr(self._inner, name)

    def execute(self, *, repository, spec):
        report = self._inner.execute(repository=repository, spec=spec)
        self.last_found = unresolved(repository)
        if not self.last_found:
            return report
        return ExecutionReport(False, tuple(report.failures) + (failure(self.last_found),), report.build_log,
                               getattr(report, 'tests_executed', None))


def install(engine) -> AssetMarkerExecutor:
    """Wrap the engine's executor once (a second install returns the gate already there)."""
    core = getattr(engine, 'core', engine)
    ex = getattr(core, 'executor', None)
    for _ in range(20):          # bounded walk; `_inner` from the instance's own __dict__ only
        if isinstance(ex, AssetMarkerExecutor):
            return ex
        ex = getattr(ex, '__dict__', {}).get('_inner') if ex is not None else None
    core.executor = AssetMarkerExecutor(core.executor)
    return core.executor

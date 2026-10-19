"""Run a platform-owned Python script in the sandbox as a FILE, never as `python -c <source>`.

The J2 request policy (`sandbox_request_policy.validate_command`, 2026-10-13) rejects any argument that contains a
newline. Every multi-line `python -c` probe was therefore refused with "invalid command arguments" (preview smoke,
browser probe, behavioural acceptance, visual QA; rehearsal 39280924963, deploy browser-probe). The policy stays as it
is. The script travels inside the repository snapshot, which `validate_snapshot` checks like any other file, and the
argv is a single-line `python <path> [args]`.

The product's own repository is not changed: the caller gets a copy with the script added.
"""
from __future__ import annotations

from collections.abc import Mapping

SCRIPT_DIR = '.omni/_sandbox'
# `python -c` puts '' (the working directory, i.e. the product root) first on sys.path; a script file puts its own
# directory there instead. Restore the -c behaviour so a script resolves imports exactly as before.
_PRELUDE = 'import sys as _omni_sys\n_omni_sys.path[0] = ""\ndel _omni_sys\n'


def staged_script(repository: Mapping[str, str], name: str, source: str, *args: str
                  ) -> tuple[dict[str, str], tuple[str, ...]]:
    """(copy of `repository` with the script added, single-line argv that runs it)."""
    if not name.replace('_', '').replace('-', '').isalnum():
        raise ValueError(f'invalid sandbox script name: {name!r}')
    path = f'{SCRIPT_DIR}/{name}.py'
    staged = dict(repository)
    staged[path] = _PRELUDE + source
    return staged, ('python', path, *args)

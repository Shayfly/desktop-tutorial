"""The step that ended vision-probe run 43657047045 red although every model passed (law 2, 2026-11-26).

Run 43657047045 (2026-11-15 00:14Z, main f02404a, job 132637775745): all six catalog models named both pictures
correctly -- 18 notices, the last "PASS (not routed for images)" -- and then "##[error]Process completed with exit code
1." with no "vision probe exit" notice. GitHub runs a step as `bash -e {0}`; the step set `-uo pipefail` and piped the
container's stderr through `grep -v '^[[:space:]]*$'`, which selects nothing and exits 1 when stderr is empty. Under
pipefail that made the pipeline fail, and `-e` ended the step before `exit $rc`. Fixed by 7d79150 (the pipeline is
wrapped in `{ ...; } || true`); the green re-run is 43689691749 (be831c6), the run omni_prod/vision_models.py cites.

Real path: the step's own `run:` text from .github/workflows/vision-probe.yml, under `bash -e` exactly as the runner
shows it ("shell: /usr/bin/bash -e {0}"), and the container's stdout produced by the real omni_prod.vision_probe
(probe_model, report) from the answers the log shows. Only `docker` is replaced: a stub on PATH that prints that stdout
(and an optional stderr) and exits with the probe's code. The old step is the text the log of run 43657047045 shows.
Mutations: tests/negative_controls/vision_probe_step.json.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import yaml

from omni_prod import vision_probe as vp

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'vision-probe.yml'

# The step as the log of run 43657047045 prints it ("##[group]Run set -uo pipefail"), line for line.
OLD_STEP = '\n'.join((
    "set -uo pipefail",
    "rc=0",
    "docker compose run --rm --no-deps -T worker python -m omni_prod.vision_probe > out.txt 2> err.txt || rc=$?",
    "grep '^::' out.txt || true",
    "grep -v '^::' out.txt | grep -v '^VISION_PROBE_JSON ' || true",
    "grep '^VISION_PROBE_JSON ' out.txt | cut -d' ' -f2- > probe.json || true",
    "tr -d '\\r' < err.txt | grep -v '^[[:space:]]*$' | tail -n 5 | while IFS= read -r l; do echo \"::warning "
    "title=vision probe stderr::$l\"; done",
    "echo \"::notice title=vision probe exit::$rc\"",
    "exit $rc",
)) + '\n'

# The catalog order of that run (write-env.sh notice: gemini-3-1-flash-lite ... anthropic-claude-sonnet-5-5) and the
# two models omni_prod/vision_models.py listed at f02404a ("routed for images" in the 3rd and 5th result).
MODELS = ('gemini-3.1-flash-lite', 'gemini-3.5-flash-lite', 'gemini-3.8-flash', 'gpt-6-luna', 'gpt-6.1-sol',
          'claude-sonnet-5-5')
ROUTED_AT_F02404A = {'gemini-3.8-flash', 'gpt-6.1-sol'}
# What every model answered (the log: red circle -> {"shape": "circle", "color": "red"} OK, and the triangle).
ANSWER = {'red circle': '{"shape": "circle", "color": "red"}', 'blue triangle': '{"shape": "triangle", "color": "blue"}'}
# The 18 notices of the log, without their titles (GitHub's log shows an annotation's message only), in order.
LOGGED = [m for model in MODELS for m in (
    'red circle -> {"shape": "circle", "color": "red"} OK',
    'blue triangle -> {"shape": "triangle", "color": "blue"} OK',
    f"PASS ({'routed for images' if model in ROUTED_AT_F02404A else 'not routed for images'})")]


class _LoggedAnswers:
    """A provider that answers what the log shows, by the picture it is really sent."""
    def complete(self, *, images, **kw):
        name = next(n for n in vp.PICTURES if vp.picture(n) == images[0])
        return ANSWER[name]


def container_stdout(listed=ROUTED_AT_F02404A) -> tuple[str, int]:
    """(stdout, exit code) of `python -m omni_prod.vision_probe` for the logged answers: the real probe and report."""
    catalog = [SimpleNamespace(endpoint=SimpleNamespace(model=m, name=m)) for m in MODELS]
    out = io.StringIO()
    with redirect_stdout(out):
        rc = vp.report(vp.run(catalog, lambda ep: _LoggedAnswers()), set(listed))
    return out.getvalue(), rc


def current_step() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    [step] = [s for s in workflow['jobs']['probe']['steps'] if s.get('name') == 'Probe']
    return step['run']


def run_step(tmp_path: Path, script: str, *, stdout: str, stderr: str = '', rc: int = 0):
    """The step under `bash -e` (GitHub's default shell) in an empty working directory, with `docker` stubbed."""
    work, stub = tmp_path / 'work', tmp_path / 'bin'
    work.mkdir()
    stub.mkdir()
    (tmp_path / 'stdout.txt').write_text(stdout, encoding='utf-8')
    (tmp_path / 'stderr.txt').write_text(stderr, encoding='utf-8')
    docker = stub / 'docker'
    docker.write_text('#!/bin/sh\ncat "$STUB_STDOUT"\ncat "$STUB_STDERR" >&2\nexit "$STUB_RC"\n', encoding='utf-8')
    docker.chmod(0o755)
    (tmp_path / 'step.sh').write_text(script, encoding='utf-8')
    env = {'PATH': f"{stub}{os.pathsep}{os.environ.get('PATH', '')}", 'STUB_STDOUT': str(tmp_path / 'stdout.txt'),
           'STUB_STDERR': str(tmp_path / 'stderr.txt'), 'STUB_RC': str(rc)}
    proc = subprocess.run(['bash', '-e', str(tmp_path / 'step.sh')], cwd=work, env=env, capture_output=True,
                          text=True, timeout=30)
    return proc, work


def notices(text: str) -> list[str]:
    return [line.split('::', 2)[2] for line in text.splitlines() if line.startswith('::notice title=vision probe ')
            and not line.startswith('::notice title=vision probe exit::')]


def test_the_fixture_is_the_logged_run():
    stdout, rc = container_stdout()
    assert notices(stdout) == LOGGED                       # the real report() prints the 18 messages of the log
    assert rc == 0                                         # the probe itself passed: no routed model failed
    assert stdout.count('VISION_PROBE_JSON ') == 1


def test_the_old_step_ends_red_with_every_model_passing(tmp_path):
    stdout, rc = container_stdout()
    proc, _ = run_step(tmp_path, OLD_STEP, stdout=stdout, rc=rc)
    # run 43657047045: the 18 notices, then exit code 1 and no "vision probe exit" notice
    assert notices(proc.stdout) == LOGGED
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert 'vision probe exit' not in proc.stdout


def test_the_old_step_passed_whenever_stderr_had_a_line(tmp_path):
    # the root cause, isolated: one non-blank stderr line and the same step ends green
    stdout, rc = container_stdout()
    proc, _ = run_step(tmp_path, OLD_STEP, stdout=stdout, stderr='Container omni-worker-worker-run-1 Creating\n', rc=rc)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '::notice title=vision probe exit::0' in proc.stdout


def test_the_current_step_ends_green_when_every_model_passed(tmp_path):
    stdout, rc = container_stdout()
    proc, work = run_step(tmp_path, current_step(), stdout=stdout, rc=rc)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert notices(proc.stdout) == LOGGED
    assert proc.stdout.splitlines()[-1] == '::notice title=vision probe exit::0'
    kept = json.loads((work / 'probe.json').read_text(encoding='utf-8'))
    assert [r['model'] for r in kept] == list(MODELS) and all(r['passed'] for r in kept)


def test_the_current_step_still_shows_stderr(tmp_path):
    stdout, rc = container_stdout()
    proc, _ = run_step(tmp_path, current_step(), stdout=stdout, stderr='\r\nfirst\n\n  \nsecond\r\n', rc=rc)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert [line for line in proc.stdout.splitlines() if line.startswith('::warning')] == [
        '::warning title=vision probe stderr::first', '::warning title=vision probe stderr::second']


def test_the_current_step_still_ends_red_when_a_routed_model_fails(tmp_path):
    # today every catalog model is routed for images: listed as such, a model that fails is a calibration error
    catalog = [SimpleNamespace(endpoint=SimpleNamespace(model=m, name=m)) for m in MODELS]

    class Blind:
        def complete(self, **kw):
            return ANSWER['red circle']                    # one fixed guess: right once, wrong once
    out = io.StringIO()
    with redirect_stdout(out):
        rc = vp.report(vp.run(catalog, lambda ep: Blind() if ep.model == 'gpt-6-luna' else _LoggedAnswers()),
                       set(MODELS))
    assert rc == 1
    proc, _ = run_step(tmp_path, current_step(), stdout=out.getvalue(), rc=rc)
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert '::error title=vision probe calibration::gpt-6-luna is routed for images but did not pass the probe' \
        in proc.stdout
    assert proc.stdout.splitlines()[-1] == '::notice title=vision probe exit::1'

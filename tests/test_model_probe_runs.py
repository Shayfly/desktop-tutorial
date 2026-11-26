"""Model-probe run 37814803770 was red because three of six models really failed (law 2, 2026-11-26).

Run 37814803770 (2026-10-08 17:12Z, ff6b4f6, job 113440587189): three Gemini models answered OK; gpt-6-luna and
gpt-6.1-sol got HTTP 429 "You have no credits remaining", claude-sonnet-5-5 HTTP 400 "Your credit balance is too low";
then "Process completed with exit code 1". Not a defect of the probe or the step: the provider accounts had no credit
that day and the probe failed closed (model_probe.main: 0 only when every configured model answered). The capability --
every catalog model answers -- was shown by run 42527017456 (f299889; attempt 1 on 2026-11-08 and attempt 2 on
2026-11-18, six of six OK each), the run the evidence records cite now.

Real path: the real omni_prod.model_probe (probe, main) over the real worker catalog file (the six enabled routes of
infra/worker-host/model-catalog.json, parsed by model_catalog.parse_model_catalog with the prices in force on the run's
day), and the workflow step's own run: text under `bash -e`. Only the provider answers are replaced, by what each log
shows, and `docker` by a stub that prints the probe's output and exits with its code.
Mutations: tests/negative_controls/model_probe_runs.json.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import yaml

from omni_prod import model_probe
from omni_prod.model_catalog import parse_model_catalog
from omni_prod.model_gateway import ModelHTTPError

ROOT = Path(__file__).resolve().parents[1]
CATALOG = [row for row in json.loads((ROOT / 'infra' / 'worker-host' / 'model-catalog.json').read_text())
           if row.get('enabled', True)]
ENV = {row['api_key_env']: 'fixture-only' for row in CATALOG}
NO_CREDIT_OPENAI = ('model request failed: HTTP 429: You have no credits remaining. Add credits to continue using the '
                    'API at https://platform.openai.com/settings/organization/billing/.')
NO_CREDIT_ANTHROPIC = ('model request failed: HTTP 400: Your credit balance is too low to access the Anthropic API. '
                       'Please go to Plans & Billing to upgrade or purchase credits.')

# The notices of each run as its log shows them (title omitted: GitHub's log shows the message only).
RED_37814803770 = [
    'model=gemini-3.1-flash-lite provider=gemini status=CONFIGURED result=ok answer=OK seconds=0.8 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000005 served_model=gemini-3.1-flash-lite',
    'model=gemini-3.5-flash-lite provider=gemini status=CONFIGURED result=ok answer=OK seconds=0.8 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000007 served_model=gemini-3.5-flash-lite',
    'model=gemini-3.8-flash provider=gemini status=CONFIGURED result=ok answer=OK seconds=2.3 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000015 served_model=gemini-3.8-flash',
    f'model=gpt-6-luna provider=openai status=CONFIGURED result=error: {NO_CREDIT_OPENAI} seconds=1.8 served_model=None',
    f'model=gpt-6.1-sol provider=openai status=CONFIGURED result=error: {NO_CREDIT_OPENAI} seconds=0.7 served_model=None',
    f'model=claude-sonnet-5-5 provider=anthropic status=CONFIGURED result=error: {NO_CREDIT_ANTHROPIC} seconds=0.9 '
    'served_model=None',
]
GREEN_42527017456 = [   # attempt 2, 2026-11-18 22:43Z (attempt 1, 2026-11-08, the same six OK)
    'model=gemini-3.1-flash-lite provider=gemini status=CONFIGURED result=ok answer=OK seconds=0.8 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000005 served_model=gemini-3.1-flash-lite',
    'model=gemini-3.5-flash-lite provider=gemini status=CONFIGURED result=ok answer=OK seconds=1.1 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000007 served_model=gemini-3.5-flash-lite',
    'model=gemini-3.8-flash provider=gemini status=CONFIGURED result=ok answer=OK seconds=2.1 input_tokens=15 '
    'output_tokens=1 metered_cost_usd=0.000015 served_model=gemini-3.8-flash',
    'model=gpt-6-luna provider=openai status=CONFIGURED result=ok answer=OK seconds=1.9 input_tokens=23 '
    'output_tokens=4 metered_cost_usd=0.000004 served_model=gpt-6-luna',
    'model=gpt-6.1-sol provider=openai status=CONFIGURED result=ok answer=OK seconds=1.3 input_tokens=23 '
    'output_tokens=4 metered_cost_usd=0.000086 served_model=gpt-6.1-sol',
    'model=claude-sonnet-5-5 provider=anthropic status=CONFIGURED result=ok answer=OK seconds=0.9 input_tokens=27 '
    'output_tokens=4 metered_cost_usd=0.000094 served_model=claude-sonnet-5-5',
]
_SECONDS = re.compile(r' seconds=[0-9.]+')


def answers_of(logged: list[str]) -> dict:
    """model -> what the provider did in that run: (input tokens, output tokens) or the error it answered."""
    out = {}
    for line in logged:
        fields = dict(re.findall(r'(\w+)=(\S+)', line))
        if ' result=error: ' in line:
            text = line.split(' result=error: ', 1)[1].rsplit(' seconds=', 1)[0]
            out[fields['model']] = ModelHTTPError(text, status=int(re.search(r'HTTP (\d+)', text).group(1)))
        else:
            out[fields['model']] = (int(fields['input_tokens']), int(fields['output_tokens']))
    return out


def factory(answers: dict):
    def make(endpoint):
        gw = SimpleNamespace(last_usage=None, last_response_model=None)

        def complete(**kw):
            answer = answers[endpoint.model]
            if isinstance(answer, Exception):
                raise answer
            gw.last_usage = SimpleNamespace(input_tokens=answer[0], output_tokens=answer[1])
            gw.last_response_model = endpoint.model
            return 'OK'
        gw.complete = complete
        return gw
    return make


def run_main(logged: list[str], when: date) -> tuple[int, str]:
    """model_probe.main() as the container runs it, with the provider answers of a logged run."""
    catalog = parse_model_catalog(json.dumps(CATALOG), ENV, when=when)
    real = model_probe.probe
    out = io.StringIO()
    with mock.patch.object(model_probe, 'probe', lambda: real(catalog, factory(answers_of(logged)))), \
            redirect_stdout(out):
        rc = model_probe.main()
    return rc, out.getvalue()


def bodies(text: str) -> list[str]:
    return [_SECONDS.sub('', line.split('::', 2)[2]) for line in text.splitlines() if line.startswith('::notice title=')]


def run_step(tmp_path: Path, stdout: str, rc: int):
    workflow = yaml.safe_load((ROOT / '.github' / 'workflows' / 'model-probe.yml').read_text(encoding='utf-8'))
    [step] = [s for s in workflow['jobs']['probe']['steps'] if s.get('name') == 'Probe every configured model']
    stub = tmp_path / 'bin'
    stub.mkdir()
    (tmp_path / 'stdout.txt').write_text(stdout, encoding='utf-8')
    docker = stub / 'docker'
    docker.write_text('#!/bin/sh\ncat "$STUB_STDOUT"\nexit "$STUB_RC"\n', encoding='utf-8')
    docker.chmod(0o755)
    (tmp_path / 'step.sh').write_text(step['run'], encoding='utf-8')
    env = {'PATH': f"{stub}{os.pathsep}{os.environ.get('PATH', '')}", 'STUB_STDOUT': str(tmp_path / 'stdout.txt'),
           'STUB_RC': str(rc)}
    return subprocess.run(['bash', '-e', str(tmp_path / 'step.sh')], cwd=tmp_path, env=env, capture_output=True,
                          text=True, timeout=30)


def test_run_37814803770_is_reproduced_from_its_log_and_fails_closed():
    rc, out = run_main(RED_37814803770, date(2026, 10, 8))
    assert bodies(out) == [_SECONDS.sub('', line) for line in RED_37814803770]
    assert rc == 1                   # three configured models did not answer: the probe is red, as the run was


def test_run_42527017456_is_reproduced_from_its_log_and_passes():
    rc, out = run_main(GREEN_42527017456, date(2026, 11, 18))
    assert bodies(out) == [_SECONDS.sub('', line) for line in GREEN_42527017456]
    assert rc == 0


def test_the_step_ends_with_the_probes_verdict(tmp_path):
    for logged, when, expected in ((RED_37814803770, date(2026, 10, 8), 1), (GREEN_42527017456, date(2026, 11, 18), 0)):
        rc, out = run_main(logged, when)
        work = tmp_path / str(expected)
        work.mkdir()
        proc = run_step(work, out, rc)
        assert proc.returncode == expected, proc.stdout + proc.stderr
        assert bodies(proc.stdout) == [_SECONDS.sub('', line) for line in logged]

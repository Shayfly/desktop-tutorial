"""Law 2 (2026-11-25): every GitHub Actions run cited as evidence is looked up and must be green on its commit.

Real path: the real script (scripts/resolve_evidence_runs.py), the real evidence records it imports from the repository
(21 run ids on 2026-11-25), and the real workflow file. Only the GitHub answer is replaced: `fetch` answers like
GET /repos/{owner}/{repo}/actions/runs/{id}, and one test goes through the real request code (the drill tool's
github_get) with `urlopen` replaced. Mutations: tests/negative_controls/evidence_runs.json.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('resolve_evidence_runs', ROOT / 'scripts' / 'resolve_evidence_runs.py')
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)

WORKFLOW = ROOT / '.github' / 'workflows' / 'evidence-runs.yml'
CITED, UNCITED = R.collect()

# The run ids cited on 2026-11-25, by the record kind that alone cites them (a removed source loses its ids).
ONLY_REQUIREMENT = {'37739774562'}                      # runtime_bindings _MODEL.observed: deploy-worker run
ONLY_PROVIDER = {'39377332673', '39378559811'}          # intelligence/inventory PAID_20261020
SUPPORTING = {'37955419872', '37962090098', '39377332673'}   # a later id in a record's text: green, commit not compared


def green(run_id, head_sha=None):
    commits = [c.commit for c in CITED.get(run_id, []) if c.commit]
    sha = head_sha or ((commits[0] if commits else 'f') + '0' * 40)[:40]
    return {'id': int(run_id), 'status': 'completed', 'conclusion': 'success', 'head_sha': sha,
            'head_branch': 'main', 'path': '.github/workflows/x.yml', 'created_at': '2026-10-10T20:00:00Z'}


def run_main(capsys, answers=None, errors=None):
    """main() over every real cited id; `answers` / `errors` override the green answer of chosen ids."""
    answers, errors = answers or {}, errors or {}
    asked = []

    def fetch(run_id):
        asked.append(run_id)
        if run_id in errors:
            raise errors[run_id]
        return answers.get(run_id) or green(run_id)
    rc = R.main(['--repo', 'Shayfly/desktop-tutorial'], fetch=fetch)
    out = capsys.readouterr().out
    assert sorted(asked) == sorted(CITED)                 # every cited id was asked, once
    return rc, out


def lines(out, prefix):
    return [line for line in out.splitlines() if line.startswith(prefix)]


def error_for(out, run_id):
    found = [line for line in lines(out, '::error ') if line.startswith(f'::error title=evidence run {run_id}::')]
    assert len(found) == 1, out
    return found[0]


# ---- the collector -----------------------------------------------------------------------------------------------

def test_the_collector_finds_the_ids_present_today():
    assert len(CITED) == 21, sorted(CITED)
    kinds = {run_id: {c.kind for c in cs} for run_id, cs in CITED.items()}
    assert {r for r, k in kinds.items() if k == {'Requirement'}} == ONLY_REQUIREMENT
    assert {r for r, k in kinds.items() if k == {'ProviderEvidence'}} == ONLY_PROVIDER
    assert sum(1 for k in kinds.values() if 'Evidence' in k) == 18
    # agent_os/evidence.py: every Evidence there is collected, with its commit
    from omni_prod.agent_os import evidence as E
    for name in ('FREE', 'PAID', 'CRASH', 'BACKUP', 'DEPLOY', 'GATE_REPLAY', 'VERIFY_REPLAY', 'ECONOMICS'):
        ev = getattr(E, name)
        first = R.RUN_ID.findall(ev.ref)[0]
        assert any(c.ref == ev.ref and c.commit == ev.commit and c.primary for c in CITED[first]), name


def test_the_collector_finds_the_same_ids_every_time():
    # Claude's bug, found before the first commit: the walk marked visited objects by id() without keeping them
    # alive, so a later call reused the id of a freed temporary and skipped inventory.py's records (21, then 19).
    assert [sorted(R.collect()[0]) for _ in range(3)] == [sorted(CITED)] * 3


def test_a_later_id_in_a_record_is_a_supporting_run_without_a_commit():
    assert {r for r, cs in CITED.items() if all(not c.primary for c in cs)} == SUPPORTING
    crash = [c for c in CITED['37955419872']]
    assert [(c.primary, c.commit) for c in crash] == [(False, '')]
    assert [(c.primary, c.commit) for c in CITED['37954236866']] == [(True, '2b4bafd')]


def test_live_records_without_a_run_id_are_listed_not_dropped():
    assert len(UNCITED) == 15
    assert 'deploy-worker "janitor started"' in UNCITED


def test_every_file_that_builds_evidence_is_a_source():
    assert R.undeclared_sources() == []
    for module in R.SOURCES:
        rest = tuple(s for s in R.SOURCES if s != module)
        assert R.undeclared_sources(sources=rest) == [
            f"{module.replace('.', '/')}.py builds "
            + ', '.join(n for n in ('Evidence', 'ProviderEvidence', 'Requirement')
                        if n in dict(R._builders(R.ROOT))[module.replace('.', '/') + '.py'])
            + ' records'], module


def test_an_undeclared_evidence_file_stops_the_check(capsys, monkeypatch):
    monkeypatch.setattr(R, 'undeclared_sources', lambda: ['omni_prod/new_place.py builds Evidence records'])
    rc = R.main(['--repo', 'o/r'], fetch=lambda run_id: pytest.fail('nothing may be verified with a source missing'))
    out = capsys.readouterr().out
    assert rc == 2
    assert out.startswith('::error title=evidence runs::omni_prod/new_place.py builds Evidence records, but it is not '
                          'in SOURCES')


def test_nothing_collected_is_never_a_pass(capsys, monkeypatch):
    monkeypatch.setattr(R, 'collect', lambda: ({}, []))
    rc = R.main(['--repo', 'o/r'], fetch=lambda run_id: pytest.fail('there is nothing to ask'))
    assert rc == 2
    assert '::error title=evidence runs::no run id was collected' in capsys.readouterr().out


# ---- the verdict -------------------------------------------------------------------------------------------------

def test_every_green_run_passes(capsys):
    rc, out = run_main(capsys)
    assert rc == 0, out
    assert lines(out, '::error') == []
    assert len(lines(out, '::notice title=evidence run ')) == 21
    assert lines(out, '::notice title=evidence runs::') == ['::notice title=evidence runs::21 of 21 cited run ids resolved green']


@pytest.mark.parametrize('conclusion', ['failure', 'cancelled', 'skipped', None])
def test_a_run_that_is_not_green_fails(capsys, conclusion):
    rc, out = run_main(capsys, answers={'38083312245': dict(green('38083312245'), conclusion=conclusion)})
    assert rc == 1
    assert f'RED: conclusion {conclusion}' in error_for(out, '38083312245')
    assert len(lines(out, '::error')) == 1
    assert '20 of 21 cited run ids resolved green; not green: 38083312245' in out


def test_a_run_in_progress_fails(capsys):
    running = dict(green('39307232830'), status='in_progress', conclusion=None)
    rc, out = run_main(capsys, answers={'39307232830': running})
    assert rc == 1
    assert 'not completed (status in_progress)' in error_for(out, '39307232830')
    # a re-run in progress may still carry the old conclusion: not completed is enough to fail
    rc, out = run_main(capsys, answers={'39307232830': dict(running, conclusion='success')})
    assert rc == 1
    assert 'RED: not completed (status in_progress) |' in error_for(out, '39307232830')


def test_a_missing_run_fails(capsys):
    gone = urllib.error.HTTPError('https://api.github.com/x', 404, 'Not Found', {}, None)
    rc, out = run_main(capsys, errors={'37962179844': gone})
    assert rc == 1
    assert 'RED: missing: GitHub has no such run (HTTP 404)' in error_for(out, '37962179844')


def test_a_run_on_another_commit_fails(capsys):
    rc, out = run_main(capsys, answers={'37962179844': green('37962179844', head_sha='a' * 40)})
    assert rc == 1
    assert 'head_sha aaaaaaaaaaaa does not start with the cited commit 039574f' in error_for(out, '37962179844')


def test_every_citing_record_is_checked_against_its_commit(capsys):
    # 38083162363 is cited by DEPLOY (Evidence) and DEPLOY_NOTICE (ProviderEvidence), both @67a0765
    rc, out = run_main(capsys, answers={'38083162363': green('38083162363', head_sha='b' * 40)})
    assert rc == 1
    assert error_for(out, '38083162363').count('does not start with the cited commit 67a0765') == 2


def test_a_supporting_run_must_be_green_but_its_commit_is_not_compared(capsys):
    rc, out = run_main(capsys, answers={'37955419872': green('37955419872', head_sha='54620a4' + '0' * 33)})
    assert rc == 0, out
    rc, out = run_main(capsys, answers={'37955419872': dict(green('37955419872'), conclusion='failure')})
    assert rc == 1
    assert 'supporting run' in error_for(out, '37955419872')


@pytest.mark.parametrize('error', [
    urllib.error.URLError('connection refused'),
    urllib.error.HTTPError('https://api.github.com/x', 500, 'Server Error', {}, None),
    urllib.error.HTTPError('https://api.github.com/x', 403, 'rate limit exceeded', {}, None),
    TimeoutError('timed out'),
    json.JSONDecodeError('Expecting value', '<html>', 0),
], ids=['network', 'http500', 'http403', 'timeout', 'not-json'])
def test_an_api_error_is_unverified_never_a_pass(capsys, error):
    rc, out = run_main(capsys, errors={'38083647077': error})
    assert rc == 2
    assert error_for(out, '38083647077').startswith('::error title=evidence run 38083647077::UNVERIFIED: API error')
    assert 'unverified: 38083647077' in out


def test_an_answer_for_another_run_is_unverified(capsys):
    rc, out = run_main(capsys, answers={'38083647077': green('38083312245')})
    assert rc == 2
    assert 'the answer is not run 38083647077' in error_for(out, '38083647077')


def test_the_summary_comes_first_and_names_every_failure(capsys):
    rc, out = run_main(capsys, answers={'37814803770': dict(green('37814803770'), conclusion='failure')},
                       errors={'38083647077': urllib.error.URLError('down')})
    assert rc == 2
    first = out.splitlines()[0]
    assert first == ('::notice title=evidence runs::19 of 21 cited run ids resolved green; not green: 37814803770; '
                     'unverified: 38083647077')


# ---- the real entry point and the real request ------------------------------------------------------------------

def test_without_a_token_nothing_is_verified_and_the_exit_is_2():
    env = {k: v for k, v in os.environ.items() if k not in ('GITHUB_TOKEN', 'GITHUB_REPOSITORY')}
    p = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'resolve_evidence_runs.py'), '--repo', 'o/r'],
                       env=env, capture_output=True, text=True, timeout=60)
    assert p.returncode == 2, p.stdout + p.stderr
    assert p.stdout.strip() == ('::error title=evidence runs::GITHUB_TOKEN and --repo (or GITHUB_REPOSITORY) are needed; '
                                '21 cited run ids were not verified')


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_the_real_request_carries_the_token_in_the_header_only(capsys, monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'tok-never-printed')
    sent = []

    def urlopen(req, timeout):
        sent.append(req)
        run_id = req.full_url.rsplit('/', 1)[1]
        return Answer(json.dumps(green(run_id)).encode())
    rc = R.main(['--repo', 'Shayfly/desktop-tutorial'], urlopen=urlopen)
    out = capsys.readouterr().out
    assert rc == 0, out
    assert sorted(r.full_url for r in sent) == sorted(
        f'https://api.github.com/repos/Shayfly/desktop-tutorial/actions/runs/{i}' for i in CITED)
    assert {r.get_header('Authorization') for r in sent} == {'Bearer tok-never-printed'}
    assert 'tok-never-printed' not in out
    assert R.github_get.__code__.co_filename == str(ROOT / 'tools' / 'drill_runs_from_github.py')


# ---- the workflow ------------------------------------------------------------------------------------------------

def _workflow():
    doc = yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))
    return doc, doc.get('on') or doc.get(True)


def test_the_workflow_runs_on_evidence_changes_daily_and_by_hand():
    _, on = _workflow()
    assert set(on) == {'pull_request', 'schedule', 'workflow_dispatch'}
    assert sorted(on['pull_request']['paths']) == R.source_files()
    assert set(on['pull_request']) == {'paths'}
    [cron] = on['schedule']
    assert len(cron['cron'].split()) == 5 and cron['cron'].split()[2:] == ['*', '*', '*']   # daily


def test_the_workflow_reads_only_and_passes_the_token_through_env():
    doc, _ = _workflow()
    assert doc['permissions'] == {'actions': 'read', 'contents': 'read'}
    [job] = doc['jobs'].values()
    assert 'permissions' not in job
    [step] = [s for s in job['steps'] if 'resolve_evidence_runs.py' in str(s.get('run', ''))]
    assert step['env'] == {'GITHUB_TOKEN': '${{ github.token }}'}
    for s in job['steps']:
        for field in ('run', 'with'):
            assert 'token' not in str(s.get(field, '')).lower().replace('persist-credentials', ''), s
    checkout = next(s for s in job['steps'] if str(s.get('uses', '')).startswith('actions/checkout@'))
    assert checkout['with']['persist-credentials'] is False


def test_nothing_lets_a_failure_through():
    doc, _ = _workflow()
    [job] = doc['jobs'].values()
    assert 'continue-on-error' not in job and 'if' not in job
    for s in job['steps']:
        assert 'continue-on-error' not in s and 'if' not in s, s
    [step] = [s for s in job['steps'] if 'resolve_evidence_runs.py' in str(s.get('run', ''))]
    assert step['run'] == 'python scripts/resolve_evidence_runs.py --repo "$GITHUB_REPOSITORY"'   # its exit decides
    assert 'shell' not in step

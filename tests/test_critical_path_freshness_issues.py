"""Law 6 -- no hiding of failures (2026-11-25): a critical path's state is an issue, not only a red run.

.github/workflows/critical-path-freshness.yml went red daily on a broken path and told nobody. Now every scheduled run
on main keeps ONE issue per path (label critical-path-broken) true to the check's own lines: a BROKEN path opens
'Critical path broken: <path>', a path the check could not verify opens 'Critical path not verified: <path>' (it was not
found broken, it was not checked), an open issue of the path gets a comment and its title follows the status, and a
path whose ::notice says PASS closes its open issue with a comment. scripts/check_critical_path_freshness.py decides;
it now also prints that PASS line (tests/test_critical_path_freshness.py covers the verdict itself).

Real path: both steps are run as written with bash; only the commands they call are replaced at the command line
(python3 for the check, gh for GitHub), like tests/test_drills_run_by_themselves.py does for the drills. The fake gh
keeps the repository's issues as JSON, answers the list call by its query (state, labels, per_page with GitHub's default
of 30) and runs the step's own --jq program with jq (review 2026-11-25: a fake that ignored --jq let three broken
lookups pass). Mutations: tests/negative_controls/critical_path_freshness_issues.json.
"""
import json
import os
import shutil
import stat
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'critical-path-freshness.yml'
CHECK = 'Check successful production evidence'
ISSUE = 'Each critical path keeps one issue true to the check'
LABEL = 'critical-path-broken'
RUN_URL = 'https://github.com/o/r/actions/runs/77'

pytestmark = pytest.mark.skipif(not all(shutil.which(c) for c in ('bash', 'awk', 'jq')),
                                reason='BLOCKED: bash, awk and jq are needed to run the steps as written')


@pytest.fixture(autouse=True)
def _own_job_summary(tmp_path, monkeypatch):
    """Nothing here may write to the job summary of the CI run that runs these tests."""
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(tmp_path / 'summary.md'))


def doc():
    return yaml.safe_load(WORKFLOW.read_text(encoding='utf-8'))


def steps():
    [job] = doc()['jobs'].values()
    return job['steps']


def step(name):
    [s] = [s for s in steps() if s.get('name') == name]
    return s


def fake(directory, name, body):
    path = Path(directory) / name
    path.write_text(body, encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


FAKE_GH = textwrap.dedent('''\
    #!/usr/bin/env python3
    """gh api against a JSON list of issues ($FAKE_STATE); every call is recorded in $FAKE_LOG."""
    import json, os, subprocess, sys, urllib.parse
    state = json.load(open(os.environ['FAKE_STATE']))
    args = sys.argv[1:]
    with open(os.environ['FAKE_LOG'], 'a') as log:
        log.write(json.dumps(args) + '\\n')
    if args[:1] != ['api']:
        sys.exit('fake gh: not an api call ' + ' '.join(args))
    rest, method = args[1:], 'GET'
    if rest[:1] == ['-X']:
        method, rest = rest[1], rest[2:]
    endpoint, rest = rest[0], rest[1:]
    fields, jq = {}, None
    while rest:
        if rest[0] == '-f':
            key, value = rest[1].split('=', 1)
            fields.setdefault(key, []).append(value)
        elif rest[0] == '--jq':
            jq = rest[1]
        else:
            sys.exit('fake gh: unknown argument ' + rest[0])
        rest = rest[2:]
    path, _, query = endpoint.partition('?')
    q = dict(urllib.parse.parse_qsl(query))
    issues = 'repos/o/r/issues'

    def one(key):
        [value] = fields[key]
        return value

    def find(number):
        found = [i for i in state['issues'] if i['number'] == number]
        if not found:
            sys.exit(f'fake gh: no issue {number}')
        return found[0]

    def shown(i):
        return dict(i, labels=[{'name': name} for name in i['labels']])
    if method == 'GET' and path == issues:
        if set(q) - {'state', 'labels', 'per_page', 'page'}:
            sys.exit('fake gh: unknown query ' + query)
        size, page = int(q.get('per_page', 30)), int(q.get('page', 1))     # GitHub's default page is 30
        hits = [i for i in state['issues'] if i['state'] == q.get('state', 'open')
                and all(name in i['labels'] for name in filter(None, q.get('labels', '').split(',')))]
        answer = [shown(i) for i in hits[(page - 1) * size:page * size]]
    elif method == 'POST' and path == issues:
        state['next'] += 1
        new = {'number': state['next'], 'title': one('title'), 'labels': fields.get('labels[]', []),
               'body': one('body'), 'state': 'open', 'comments': []}
        state['issues'].append(new)
        answer = shown(new)
    elif method == 'POST' and path.startswith(issues + '/') and path.endswith('/comments'):
        find(int(path.split('/')[4]))['comments'].append(one('body'))
        answer = {'id': 1}
    elif method == 'PATCH' and path.startswith(issues + '/') and path.count('/') == 4:
        issue = find(int(path.split('/')[4]))
        for key in fields:
            if key not in ('title', 'state', 'state_reason'):
                sys.exit('fake gh: unexpected field ' + key)
            issue[key] = one(key)
        answer = shown(issue)
    else:
        sys.exit('fake gh: unexpected call ' + ' '.join(args))
    json.dump(state, open(os.environ['FAKE_STATE'], 'w'))
    text = json.dumps(answer)
    if jq is not None:                      # gh api --jq prints raw strings, like jq -r
        p = subprocess.run(['jq', '-r', jq], input=text, capture_output=True, text=True)
        if p.returncode:
            sys.exit('fake gh: jq failed: ' + p.stderr)
        sys.stdout.write(p.stdout)
    else:
        print(text)
''')


def issue(number, title, labels=(LABEL,), state='open'):
    return {'number': number, 'title': title, 'labels': list(labels), 'state': state, 'body': '', 'comments': []}


def run_issue_step(tmp_path, log_text, issues=(), outcome='failure'):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake(bin_dir, 'gh', FAKE_GH)
    if log_text is not None:                         # None: the check step never ran, there is no log
        (tmp_path / 'freshness.log').write_text(log_text, encoding='utf-8')
    state, calls = tmp_path / 'state.json', tmp_path / 'calls.log'
    state.write_text(json.dumps({'issues': list(issues), 'next': 500}))
    calls.write_text('')
    env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}', RUNNER_TEMP=str(tmp_path),
               GITHUB_REPOSITORY='o/r', RUN_URL=RUN_URL, GH_TOKEN='t', CHECK_OUTCOME=outcome,
               FAKE_STATE=str(state), FAKE_LOG=str(calls))
    p = subprocess.run(['bash', '-e', '-c', step(ISSUE)['run']], cwd=tmp_path, env=env, capture_output=True,
                       text=True, timeout=60)
    made = [json.loads(line) for line in calls.read_text().splitlines()]
    return p, made, {i['number']: i for i in json.loads(state.read_text())['issues']}


def created(made):
    return [c for c in made if c[1:4] == ['-X', 'POST', 'repos/o/r/issues']]


TODAY = datetime.now(timezone.utc).strftime('%Y-%m-%d')
GOLDEN = '::error title=Golden E2E::BROKEN — No qualifying successful step'
BACKUP = '::error title=Backup restore::UNVERIFIED — OSError'
BACKUP_PASS = ('::notice title=Backup restore::PASS — 2026-11-24T10:00:00+00:00 '
               'https://github.com/o/r/actions/runs/42 (abcdef012345)')
PATHS = ('Worker deployment', 'Golden rehearsal', 'Post-deploy verify-replay', 'Backup restore', 'Golden E2E')


def ok(name):
    return f'::notice title={name}::PASS — 2026-11-24T10:00:00+00:00 https://github.com/o/r/actions/runs/42 (abc)'


# ---- the pins ----------------------------------------------------------------------------------------------------

def test_the_workflow_may_open_issues():
    d = doc()
    assert d['permissions'] == {'actions': 'read', 'contents': 'read', 'issues': 'write'}
    [job] = d['jobs'].values()
    assert 'permissions' not in job


def test_the_issue_step_runs_after_every_scheduled_run_on_main():
    s = step(ISSUE)
    assert s['if'] == "(success() || failure()) && github.event_name == 'schedule' && github.ref == 'refs/heads/main'"
    names = [x.get('name') for x in steps()]
    assert names.index(ISSUE) == names.index(CHECK) + 1 == len(names) - 1
    assert step(CHECK)['id'] == 'check'
    assert s['env'] == {'GH_TOKEN': '${{ github.token }}', 'CHECK_OUTCOME': '${{ steps.check.outcome }}',
                        'RUN_URL': '${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}'}
    assert '/issues' in s['run'] and LABEL in s['run']


def test_nothing_lets_the_check_fail_quietly():
    d = doc()
    [job] = d['jobs'].values()
    assert 'continue-on-error' not in job and 'if' not in job
    for s in job['steps']:
        assert 'continue-on-error' not in s, s
    check = step(CHECK)
    assert 'if' not in check
    assert check['run'].splitlines() == [
        'set -o pipefail',
        'python3 scripts/check_critical_path_freshness.py | tee "$RUNNER_TEMP/freshness.log"']
    assert '"$RUNNER_TEMP/freshness.log"' in step(ISSUE)['run']


@pytest.mark.parametrize('code', [0, 1, 3])
def test_the_check_step_ends_with_the_scripts_own_exit_code(tmp_path, code):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake(bin_dir, 'python3', f'#!/bin/sh\necho "{GOLDEN}"\necho "{BACKUP}"\nexit {code}\n')
    env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}', RUNNER_TEMP=str(tmp_path))
    p = subprocess.run(['bash', '-e', '-c', step(CHECK)['run']], cwd=tmp_path, env=env, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == code, p.stdout + p.stderr
    assert p.stdout.splitlines() == [GOLDEN, BACKUP]                     # the annotations still reach the log
    assert (tmp_path / 'freshness.log').read_text().splitlines() == [GOLDEN, BACKUP]


def test_the_check_prints_a_pass_line_the_issue_step_reads(tmp_path, monkeypatch, capsys):
    import scripts.check_critical_path_freshness as C
    when = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)
    rows = [('Worker deployment', 'PASS', (when, 42, 'abcdef0123456789')), ('Golden E2E', 'BROKEN', None),
            ('Backup restore', 'UNVERIFIED', 'OSError')]
    monkeypatch.setattr(C, 'report', lambda api, now: iter(rows))
    monkeypatch.setattr(C, 'Actions', lambda repo, token: None)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'o/r')
    monkeypatch.setenv('GH_TOKEN', 't')
    assert C.main() == 1
    out = capsys.readouterr().out
    assert out.splitlines() == [
        '::notice title=Worker deployment::PASS — 2026-11-24T10:00:00+00:00 https://github.com/o/r/actions/runs/42 '
        '(abcdef012345)', GOLDEN, BACKUP]
    # that output, as the check step keeps it, drives the issue step: the recovered path's issue closes
    p, _, state = run_issue_step(tmp_path, out, [issue(41, 'Critical path broken: Worker deployment')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert state[41]['state'] == 'closed'
    assert [i['title'] for i in state.values() if i['state'] == 'open'] == [
        'Critical path broken: Golden E2E', 'Critical path not verified: Backup restore']


# ---- opening and updating ----------------------------------------------------------------------------------------

def test_each_broken_path_opens_its_own_issue(tmp_path):
    p, made, state = run_issue_step(tmp_path, f'| table |\n{GOLDEN}\n{BACKUP}\n')
    assert p.returncode == 0, p.stdout + p.stderr
    assert [(n, i['title'], i['labels'], i['state']) for n, i in state.items()] == [
        (501, 'Critical path broken: Golden E2E', [LABEL], 'open'),
        (502, 'Critical path not verified: Backup restore', [LABEL], 'open')]
    assert state[501]['body'] == (f'The daily critical-path freshness check found this path broken on {TODAY}.'
                                  f'\n\n{GOLDEN}\n\n{RUN_URL}')
    assert state[502]['body'] == (f'The daily critical-path freshness check could not verify this path on {TODAY}.'
                                  f'\n\n{BACKUP}\n\n{RUN_URL}')
    assert '::notice title=Golden E2E::issue #501 opened' in p.stdout


@pytest.mark.parametrize('line', [BACKUP, '::error title=Backup restore::SOMETHING NEW — x'], ids=['unverified', 'unknown'])
def test_a_path_the_check_could_not_verify_is_never_called_broken(tmp_path, line):
    # Review 2026-11-25: 'UNVERIFIED — HTTPError' opened 'Critical path broken: ...', 'found this path broken'
    p, _, state = run_issue_step(tmp_path, f'{line}\n')
    assert p.returncode == 0, p.stdout + p.stderr
    [new] = state.values()
    assert new['title'] == 'Critical path not verified: Backup restore'
    assert 'broken' not in new['body'].split('\n')[0]


def test_an_open_issue_is_updated_never_duplicated(tmp_path):
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\n{BACKUP}\n', [
        issue(41, 'Critical path broken: Golden E2E'), issue(42, 'Critical path broken: Other')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert state[41]['comments'] == [f'Still broken on {TODAY}: BROKEN — No qualifying successful step\n\n{RUN_URL}']
    assert state[42]['comments'] == []
    assert [i['title'] for n, i in state.items() if n > 42] == ['Critical path not verified: Backup restore']


def test_the_lookup_reads_past_githubs_default_page(tmp_path):
    # Review 2026-11-25: dropping &per_page=100 left every test green; GitHub returns 30 issues by default
    others = [issue(n, f'Critical path broken: Other {n}') for n in range(1, 36)]
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\n', others + [issue(36, 'Critical path broken: Golden E2E')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert created(made) == [] and len(state[36]['comments']) == 1


def test_the_lookup_counts_only_open_labelled_issues_with_the_exact_title(tmp_path):
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\n', [
        issue(7, 'Critical path broken: Golden E2E', state='closed'),
        issue(8, 'Critical path broken: Golden E2E', labels=()),
        issue(9, 'Critical path broken: Golden E2E (old)'),
        issue(10, 'Critical path broken: Golden')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert [i['comments'] for n, i in state.items() if n < 500] == [[], [], [], []]
    assert [i['title'] for n, i in state.items() if n > 500] == ['Critical path broken: Golden E2E']


@pytest.mark.parametrize('line, before, after, said', [
    (GOLDEN, 'Critical path not verified: Golden E2E', 'Critical path broken: Golden E2E', 'Still broken on'),
    (BACKUP, 'Critical path broken: Backup restore', 'Critical path not verified: Backup restore', 'Not verified on'),
], ids=['now-broken', 'now-unverified'])
def test_a_status_change_retitles_the_one_issue_of_the_path(tmp_path, line, before, after, said):
    p, made, state = run_issue_step(tmp_path, f'{line}\n{line}\n', [issue(9, before)])
    assert p.returncode == 0, p.stdout + p.stderr
    assert list(state) == [9]                                            # never a second issue
    assert state[9]['title'] == after and state[9]['state'] == 'open'
    assert [c.split(':')[0] for c in state[9]['comments']] == [f'{said} {TODAY}'] * 2
    assert all(RUN_URL in c for c in state[9]['comments'])


def test_the_same_path_twice_in_one_run_is_one_issue(tmp_path):
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\n{GOLDEN}\n')
    assert p.returncode == 0, p.stdout + p.stderr
    assert list(state) == [501] and len(state[501]['comments']) == 1


def test_a_failure_that_names_no_path_opens_an_issue_that_says_so(tmp_path):
    p, _, state = run_issue_step(tmp_path, 'Traceback (most recent call last):\nKeyError: GITHUB_REPOSITORY\n')
    assert p.returncode == 0, p.stdout + p.stderr
    [new] = state.values()
    assert new['title'] == 'Critical path not verified: Critical path freshness check'
    assert 'UNVERIFIED — the check did not pass (outcome failure) and named no path' in new['body']


def test_a_missing_log_still_opens_an_issue(tmp_path):
    # the check step never ran (checkout failed): there is no log at all
    p, _, state = run_issue_step(tmp_path, None, outcome='skipped')
    assert p.returncode == 0, p.stdout + p.stderr
    assert [(i['title'], 'outcome skipped' in i['body']) for i in state.values()] == [
        ('Critical path not verified: Critical path freshness check', True)]


# ---- closing on recovery -----------------------------------------------------------------------------------------

def test_a_passing_path_closes_its_open_issue_with_a_comment(tmp_path):
    # Review 2026-11-25: nothing ever marked recovery, so an issue from one bad day stayed open
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\n{BACKUP_PASS}\n', [
        issue(41, 'Critical path broken: Golden E2E'), issue(43, 'Critical path not verified: Backup restore')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert (state[43]['state'], state[43].get('state_reason')) == ('closed', 'completed')
    assert state[43]['comments'] == [f'Recovered on {TODAY}: PASS — 2026-11-24T10:00:00+00:00 '
                                     f'https://github.com/o/r/actions/runs/42 (abcdef012345)\n\n{RUN_URL}']
    assert state[41]['state'] == 'open' and state[41]['comments'][0].startswith(f'Still broken on {TODAY}')
    assert created(made) == []
    assert '::notice title=Backup restore::issue #43 closed (recovered)' in p.stdout


def test_a_green_run_closes_every_recovered_path_and_opens_nothing(tmp_path):
    log = '\n'.join(ok(name) for name in PATHS) + '\n'
    p, made, state = run_issue_step(tmp_path, log, [
        issue(41, 'Critical path broken: Golden E2E'), issue(43, 'Critical path not verified: Backup restore'),
        issue(44, 'Critical path not verified: Critical path freshness check'),
        issue(45, 'Critical path broken: A path the check no longer has')], outcome='success')
    assert p.returncode == 0, p.stdout + p.stderr
    assert {n: i['state'] for n, i in state.items()} == {41: 'closed', 43: 'closed', 44: 'closed', 45: 'open'}
    assert state[44]['comments'] == [f'Recovered on {TODAY}: PASS — the check ran and named every path\n\n{RUN_URL}']
    assert created(made) == []


def test_a_green_run_without_open_issues_only_lists_them(tmp_path):
    log = '\n'.join(ok(name) for name in PATHS) + '\n'
    p, made, state = run_issue_step(tmp_path, log, outcome='success')
    assert p.returncode == 0, p.stdout + p.stderr
    assert made == [['api', f'repos/o/r/issues?state=open&labels={LABEL}&per_page=100', '--jq',
                     '.[] | "\\(.number)\\t\\(.title)"']]
    assert state == {}


def test_a_red_run_never_closes_an_issue_without_a_pass_line(tmp_path):
    # the check crashed after naming one path: the others are not known to pass
    p, made, state = run_issue_step(tmp_path, f'{GOLDEN}\nTraceback (most recent call last):\n', [
        issue(43, 'Critical path not verified: Backup restore')])
    assert p.returncode == 0, p.stdout + p.stderr
    assert state[43]['state'] == 'open' and state[43]['comments'] == []

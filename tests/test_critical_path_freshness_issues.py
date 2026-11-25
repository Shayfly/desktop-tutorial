"""Law 6 -- no hiding of failures (2026-11-25): a broken critical path opens an issue, not only a red run.

.github/workflows/critical-path-freshness.yml went red daily on a broken path and told nobody. Now, on a failed scheduled
run on main, it opens ONE issue per broken path (label critical-path-broken) with the check's own ::error line, or
comments on the open one -- never a second issue for the same path. The verdict stays the script's
(scripts/check_critical_path_freshness.py is not changed; tests/test_critical_path_freshness.py covers it).

Real path: both steps are run as written with bash; only the commands they call are replaced at the command line
(python3 for the check, gh for GitHub), like tests/test_drills_run_by_themselves.py does for the drills.
Mutations: tests/negative_controls/critical_path_freshness_issues.json.
"""
import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github' / 'workflows' / 'critical-path-freshness.yml'
CHECK = 'Check successful production evidence'
ISSUE = 'A broken critical path opens or updates its issue'
LABEL = 'critical-path-broken'

pytestmark = pytest.mark.skipif(not shutil.which('bash') or not shutil.which('awk'),
                                reason='BLOCKED: bash and awk are needed to run the steps as written')


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
    """gh api, as the issue step calls it: records every call; open issues come from $FAKE_STATE."""
    import json, os, sys
    state = json.load(open(os.environ['FAKE_STATE']))
    args = sys.argv[1:]
    with open(os.environ['FAKE_LOG'], 'a') as log:
        log.write(json.dumps(args) + '\\n')
    a = ' '.join(args)
    if args[:1] != ['api']:
        sys.exit('fake gh: not an api call ' + a)
    if '-X' not in args and 'issues?state=open&labels=critical-path-broken' in a and '--jq' in args:
        for number, title in state['open']:
            print(f'{number}\\t{title}')
        sys.exit(0)
    if args[1:3] == ['-X', 'POST'] and args[3].endswith('/comments'):
        print('{}')
        sys.exit(0)
    if args[1:3] == ['-X', 'POST'] and args[3] == 'repos/o/r/issues' and args[-2:] == ['--jq', '.number']:
        state['next'] += 1
        json.dump(state, open(os.environ['FAKE_STATE'], 'w'))
        print(state['next'])
        sys.exit(0)
    sys.exit('fake gh: unexpected call ' + a)
''')


def run_issue_step(tmp_path, log_text, open_issues=()):
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake(bin_dir, 'gh', FAKE_GH)
    if log_text is not None:                         # None: the check step never ran, there is no log
        (tmp_path / 'freshness.log').write_text(log_text, encoding='utf-8')
    state, calls = tmp_path / 'state.json', tmp_path / 'calls.log'
    state.write_text(json.dumps({'open': [list(i) for i in open_issues], 'next': 500}))
    calls.write_text('')
    env = dict(os.environ, PATH=f'{bin_dir}{os.pathsep}{os.environ["PATH"]}', RUNNER_TEMP=str(tmp_path),
               GITHUB_REPOSITORY='o/r', RUN_URL='https://github.com/o/r/actions/runs/77', GH_TOKEN='t',
               FAKE_STATE=str(state), FAKE_LOG=str(calls))
    p = subprocess.run(['bash', '-e', '-c', step(ISSUE)['run']], cwd=tmp_path, env=env, capture_output=True,
                       text=True, timeout=60)
    made = [json.loads(line) for line in calls.read_text().splitlines()]
    return p, made


def field(call, name):
    return [call[i + 1].split('=', 1)[1] for i, a in enumerate(call) if a == '-f' and call[i + 1].startswith(name + '=')]


def created(made):
    return [c for c in made if c[1:4] == ['-X', 'POST', 'repos/o/r/issues']]


def commented(made):
    return [c for c in made if c[1:3] == ['-X', 'POST'] and c[3].endswith('/comments')]


GOLDEN = '::error title=Golden E2E::BROKEN — No qualifying successful step'
BACKUP = '::error title=Backup restore::UNVERIFIED — OSError'


# ---- the pins ----------------------------------------------------------------------------------------------------

def test_the_workflow_may_open_issues():
    d = doc()
    assert d['permissions'] == {'actions': 'read', 'contents': 'read', 'issues': 'write'}
    [job] = d['jobs'].values()
    assert 'permissions' not in job


def test_the_issue_step_runs_only_when_the_scheduled_run_on_main_failed():
    s = step(ISSUE)
    assert s['if'] == "failure() && github.event_name == 'schedule' && github.ref == 'refs/heads/main'"
    names = [x.get('name') for x in steps()]
    assert names.index(ISSUE) == names.index(CHECK) + 1 == len(names) - 1
    assert s['env']['GH_TOKEN'] == '${{ github.token }}'
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


# ---- the issue step, as written ----------------------------------------------------------------------------------

def test_each_broken_path_opens_its_own_issue(tmp_path):
    p, made = run_issue_step(tmp_path, f'| table |\n{GOLDEN}\n{BACKUP}\n')
    assert p.returncode == 0, p.stdout + p.stderr
    issues = created(made)
    assert [field(c, 'title') for c in issues] == [['Critical path broken: Golden E2E'],
                                                   ['Critical path broken: Backup restore']]
    assert all(field(c, 'labels[]') == [LABEL] for c in issues)
    assert GOLDEN in field(issues[0], 'body')[0] and BACKUP in field(issues[1], 'body')[0]
    assert all('https://github.com/o/r/actions/runs/77' in field(c, 'body')[0] for c in issues)
    assert commented(made) == []
    assert '::notice title=Golden E2E::issue #501 opened' in p.stdout


def test_an_open_issue_is_updated_never_duplicated(tmp_path):
    p, made = run_issue_step(tmp_path, f'{GOLDEN}\n{BACKUP}\n',
                             open_issues=[(41, 'Critical path broken: Golden E2E'), (42, 'Critical path broken: Other')])
    assert p.returncode == 0, p.stdout + p.stderr
    [comment] = commented(made)
    assert comment[3] == 'repos/o/r/issues/41/comments'
    assert 'BROKEN — No qualifying successful step' in field(comment, 'body')[0]
    assert [field(c, 'title') for c in created(made)] == [['Critical path broken: Backup restore']]


def test_the_same_path_twice_in_one_run_is_one_issue(tmp_path):
    p, made = run_issue_step(tmp_path, f'{GOLDEN}\n{GOLDEN}\n')
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(created(made)) == 1
    assert [c[3] for c in commented(made)] == ['repos/o/r/issues/501/comments']


def test_a_failure_that_names_no_path_still_opens_an_issue(tmp_path):
    p, made = run_issue_step(tmp_path, 'Traceback (most recent call last):\nKeyError: GITHUB_REPOSITORY\n')
    assert p.returncode == 0, p.stdout + p.stderr
    [issue] = created(made)
    assert field(issue, 'title') == ['Critical path broken: Critical path freshness']
    assert 'failed without naming a broken path' in field(issue, 'body')[0]


def test_a_missing_log_still_opens_an_issue(tmp_path):
    # the check step never ran (checkout failed): there is no log at all
    p, made = run_issue_step(tmp_path, None)
    assert p.returncode == 0, p.stdout + p.stderr
    assert [field(c, 'title') for c in created(made)] == [['Critical path broken: Critical path freshness']]

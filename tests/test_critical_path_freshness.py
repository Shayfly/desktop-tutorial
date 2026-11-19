from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts.check_critical_path_freshness import latest_proof, report, STEPS


NOW = datetime(2026, 11, 19, tzinfo=timezone.utc)
CUTOFF = NOW - timedelta(days=7)


def test_successful_workflow_does_not_count_a_skipped_critical_step():
    run = {'id': 42, 'conclusion': 'success', 'head_branch': 'main', 'event': 'push', 'head_sha': 'abc'}
    step = {'name': 'Required', 'conclusion': 'skipped', 'completed_at': NOW.isoformat()}
    jobs = [{'conclusion': 'success', 'steps': [step]}]
    assert latest_proof([run], lambda _: jobs, 'Required', CUTOFF, NOW) is None
    step.update(conclusion='success', completed_at=(CUTOFF - timedelta(seconds=1)).isoformat())
    assert latest_proof([run], lambda _: jobs, 'Required', CUTOFF, NOW) is None
    step['completed_at'] = CUTOFF.isoformat()
    assert latest_proof([run], lambda _: jobs, 'Required', CUTOFF, NOW) == (CUTOFF, 42, 'abc')
    run['event'] = 'pull_request'
    assert latest_proof([run], lambda _: jobs, 'Required', CUTOFF, NOW) is None


def test_distinguishes_no_evidence_from_api_failure_for_every_path():
    class API:
        def workflow_runs(self, filename, lookback):
            if filename == 'backup-restore.yml':
                raise OSError('Actions unavailable')
            return []

        def golden_runs(self, cutoff):
            return []

        def jobs(self, run_id):
            raise AssertionError('no runs to inspect')

    outcomes = {name: status for name, status, _ in report(API(), NOW)}
    assert outcomes == {**dict.fromkeys(STEPS, 'BROKEN'), 'Golden E2E': 'BROKEN',
                        'Backup restore': 'UNVERIFIED'}


def test_rerun_of_older_workflow_counts_by_step_completion():
    filename, step_name = STEPS['Post-deploy verify-replay']
    created = NOW - timedelta(days=12)

    class API:
        def workflow_runs(self, name, lookback):
            if name == filename and lookback <= created:
                return [{'id': 42, 'conclusion': 'success', 'head_branch': 'main',
                         'event': 'workflow_dispatch', 'head_sha': 'original', 'updated_at': NOW.isoformat()}]
            return []

        def golden_runs(self, cutoff):
            return []

        def jobs(self, run_id):
            return [{'conclusion': 'success', 'steps': [
                {'name': step_name, 'conclusion': 'success', 'completed_at': NOW.isoformat()}
            ]}]

    _, status, proof = next(row for row in report(API(), NOW) if row[0] == 'Post-deploy verify-replay')
    assert (status, proof) == ('PASS', (NOW, 42, 'original'))


@pytest.mark.parametrize('statuses,allowed', [
    ([], False),
    (['ERROR'], False),
    (['PASS', 'NOT_RUN'], False),
    (['FAIL'], False),
    (['PASS', 'FAIL'], True),
])
def test_verify_replay_evidence_step_requires_positive_completed_versions(tmp_path, statuses, allowed):
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / '.github/workflows/postdeploy-checks.yml').read_text())
    _, name = STEPS['Post-deploy verify-replay']
    step = next(s for s in workflow['jobs']['checks']['steps'] if s.get('name') == name)
    assert step['if'] == "inputs.stage == 'verify-replay'"
    (tmp_path / 'verify.txt').write_text('VERIFY_REPLAY ' + json.dumps({
        'results': [{'version': f'v{i}', 'status': status} for i, status in enumerate(statuses)]
    }) + '\n')
    proc = subprocess.run(['bash', '-c', step['run']], cwd=tmp_path, env={'RUNNER_TEMP': str(tmp_path)},
                          text=True, capture_output=True, timeout=10)
    assert (proc.returncode == 0) is allowed, proc.stdout + proc.stderr

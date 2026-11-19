from datetime import datetime, timedelta, timezone

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

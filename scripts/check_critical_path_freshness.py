"""Report whether critical production checks completed in the last seven days."""
from datetime import datetime, timedelta, timezone
import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STEPS = {
    'Worker deployment': ('deploy-worker.yml', 'Prove the worker executes a job from the build queue'),
    'Golden rehearsal': ('golden-rehearsal.yml', 'Rehearse one build'),
    'Post-deploy verify-replay': ('postdeploy-checks.yml', 'Confirm replay completed with successful version evidence'),
    'Backup restore': ('backup-restore.yml', 'Restore the stored copy and verify'),
}
GOLDEN_STEP = 'Enforce all four Golden E2E requirements'
TRUSTED_EVENTS = {'push', 'schedule', 'workflow_dispatch'}


def timestamp(value):
    return datetime.fromisoformat(value)


def latest_proof(runs, jobs_for_run, step_name, cutoff, now):
    proofs = []
    for run in runs:
        if (run['conclusion'] != 'success' or run['head_branch'] != 'main'
                or run['event'] not in TRUSTED_EVENTS):
            continue
        if run.get('updated_at') and timestamp(run['updated_at']) < cutoff:
            continue
        for job in jobs_for_run(run['id']):
            if job['conclusion'] != 'success':
                continue
            for step in job.get('steps') or []:
                if step['name'] == step_name and step['conclusion'] == 'success' and step.get('completed_at'):
                    completed = timestamp(step['completed_at'])
                    if cutoff <= completed <= now:
                        proofs.append((completed, run['id'], run['head_sha']))
    return max(proofs, default=None)


class Actions:
    def __init__(self, repo, token):
        self.root = f'https://api.github.com/repos/{repo}/actions/'
        self.headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28'}

    def get(self, path, **params):
        query = '?' + urlencode(params) if params else ''
        req = Request(self.root + path + query, headers=self.headers)
        with urlopen(req, timeout=20) as response:
            return json.load(response)

    def rows(self, path, key, **params):
        for page in range(1, 11):
            rows = self.get(path, per_page=100, page=page, **params)[key]
            yield from rows
            if len(rows) < 100:
                return
        raise ValueError('Actions result exceeded the bounded search window')

    def workflow_runs(self, filename, lookback):
        return self.rows(f'workflows/{filename}/runs', 'workflow_runs',
                         branch='main', status='success', created=f'>={lookback.isoformat()}')

    def golden_runs(self, cutoff):
        seen = set()
        for artifact in self.rows('artifacts', 'artifacts', name='golden-evidence-verdict'):
            linked = artifact.get('workflow_run') or {}
            run_id = linked.get('id')
            if (artifact['name'] == 'golden-evidence-verdict' and not artifact['expired']
                    and linked.get('head_branch') == 'main' and run_id and run_id not in seen
                    and timestamp(artifact['created_at']) >= cutoff):
                seen.add(run_id)
                yield self.get(f'runs/{run_id}')

    def jobs(self, run_id):
        return self.rows(f'runs/{run_id}/jobs', 'jobs', filter='latest')


def report(api, now):
    cutoff = now - timedelta(days=7)
    # GitHub allows reruns for 30 days. The API's created filter uses the
    # original run time; eligibility uses when the successful step completed.
    lookback = cutoff - timedelta(days=31)
    paths = [(name, lambda filename=filename: api.workflow_runs(filename, lookback), step)
             for name, (filename, step) in STEPS.items()]
    paths.append(('Golden E2E', lambda: api.golden_runs(cutoff), GOLDEN_STEP))
    for name, runs, step in paths:
        try:
            proof = latest_proof(runs(), api.jobs, step, cutoff, now)
        except (ValueError, OSError, KeyError) as exc:
            yield name, 'UNVERIFIED', type(exc).__name__
        else:
            yield name, 'PASS' if proof else 'BROKEN', proof


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    results = list(report(Actions(repo, os.environ['GH_TOKEN']), datetime.now(timezone.utc)))
    lines = ['| Critical path | Status | Evidence from the past 7 days (UTC; workflow trigger SHA) |', '|---|---|---|']
    for name, status, evidence in results:
        if status == 'PASS':
            when, run_id, sha = evidence
            url = f'https://github.com/{repo}/actions/runs/{run_id}'
            note = f'[{when.isoformat()}]({url}) · `{sha[:12]}`'
            # Law 6 (2026-11-25): a passing path says so in the log, so the issue step can close a recovered path's
            # issue on positive evidence, never on the absence of an error line.
            print(f'::notice title={name}::PASS — {when.isoformat()} {url} ({sha[:12]})')
        else:
            note = evidence or 'No qualifying successful step'
            print(f'::error title={name}::{status} — {note}')
        lines.append(f'| {name} | {status} | {note} |')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
        summary.write('\n'.join(lines) + '\n')
    return int(any(status != 'PASS' for _, status, _ in results))


if __name__ == '__main__':
    raise SystemExit(main())

"""The monthly drills run on main by themselves (2026-11-21: Codex's tasks -- monthly drills automation -- are Claude's).

C16, C19, C11 and C18's alert half were run by hand on 2026-11-21 (CONTROLS.json drills_run). From now on each runs as
a scheduled workflow on main, and registry_lint R3 counts its green runs read from GitHub (drill_workflow,
tools/drill_runs_from_github.py). What is pinned here:
  * every drill_workflow names a real workflow with a schedule and a manual dispatch, and its schedule survives one
    failed run without the monthly record lapsing (R3: overdue when today > last + 31 days);
  * no drill job on the production runner checks out code, and every drill opens an issue when it fails;
  * the PASS decision of the C16 and C18 scripts, run as written with GitHub faked at the command line (gh, curl,
    python): a refusal for another reason, or a merge that went through, is never PASS.
Mutations: tests/negative_controls/drills_by_themselves.json.
"""
import calendar
import datetime as dt
import json
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / '.github' / 'workflows'
CONTROLS = json.loads((ROOT / 'CONTROLS.json').read_text(encoding='utf-8'))
BY_ID = {c['id']: c for c in CONTROLS['controls']}
AUTOMATED = {'C11': 'drill-c11.yml', 'C16': 'drill-c16.yml', 'C18': 'drill-c18-alert.yml', 'C19': 'drill-c19.yml'}
PERIOD = {'weekly': 7, 'monthly': 31, 'quarterly': 92}
REQUIRED_CHECKS = ['test', 'validate']           # main's protection (C16 status: "require status checks = test + validate")


def load(name):
    return yaml.safe_load((WF / name).read_text(encoding='utf-8'))


def events(doc):
    return doc.get('on') or doc.get(True)


def step(doc, startswith):
    for job in doc['jobs'].values():
        for s in job['steps']:
            if str(s.get('name', '')).startswith(startswith):
                return s
    raise AssertionError(f'no step named {startswith!r}')


def frequency(c):
    return str(c['frequency']) if c.get('type') == 'drill' else c['drill'].split(':', 1)[0].strip()


def run_dates(cron, years=(2026, 2027, 2028)):
    """Dates a 5-field cron fires on (day-of-month and month fields only; '*' or a comma list of numbers)."""
    _, _, dom, month, dow = cron.split()
    assert dow == '*', f'{cron}: a day-of-week schedule is not read by this test'
    months = range(1, 13) if month == '*' else [int(m) for m in month.split(',')]
    out = []
    for y in years:
        for m in months:
            last = calendar.monthrange(y, m)[1]
            days = range(1, last + 1) if dom == '*' else [int(d) for d in dom.split(',') if int(d) <= last]
            out += [dt.date(y, m, d) for d in days]
    return sorted(out)


class TheRegistryNamesRealScheduledWorkflows(unittest.TestCase):
    def test_the_four_drills_are_registered(self):
        for cid, wf in AUTOMATED.items():
            self.assertEqual(BY_ID[cid].get('drill_workflow'), wf, cid)

    def test_every_drill_workflow_exists_with_a_schedule_and_a_manual_dispatch(self):
        for c in CONTROLS['controls']:
            if not c.get('drill_workflow'):
                continue
            with self.subTest(control=c['id']):
                doc = load(c['drill_workflow'])
                self.assertIn('schedule', events(doc))
                self.assertIn('workflow_dispatch', events(doc))       # drill_runs_from_github counts both, on main

    def test_one_failed_run_never_lets_the_record_lapse(self):
        # R3: overdue when today > last + period. With one run failing, the next green one is two runs later.
        for cid, wf in AUTOMATED.items():
            period = PERIOD[frequency(BY_ID[cid])]
            for entry in events(load(wf))['schedule']:
                dates = run_dates(entry['cron'])
                worst = max((dates[i + 2] - dates[i]).days for i in range(len(dates) - 2))
                with self.subTest(control=cid, cron=entry['cron']):
                    self.assertLessEqual(worst, period, f'{wf}: a failed run leaves a {worst}-day gap')

    def test_no_drill_job_on_the_production_runner_checks_out_code(self):
        for wf in AUTOMATED.values():
            for name, job in load(wf)['jobs'].items():
                if 'self-hosted' in (job['runs-on'] if isinstance(job['runs-on'], list) else [job['runs-on']]):
                    with self.subTest(workflow=wf, job=name):
                        self.assertFalse([s for s in job['steps'] if 'actions/checkout' in str(s.get('uses', ''))])
                        self.assertLessEqual(job['timeout-minutes'], 10)

    def test_a_failed_drill_opens_an_issue(self):
        for wf in AUTOMATED.values():
            doc = load(wf)
            s = step(doc, 'A failed drill opens an issue')
            with self.subTest(workflow=wf):
                self.assertEqual(s['if'], 'failure()')
                self.assertIn('drill-failed', s['run'])
                self.assertIn('/issues', s['run'])
                perms = dict(doc.get('permissions') or {})
                for job in doc['jobs'].values():
                    perms.update(job.get('permissions') or {})
                self.assertEqual(perms.get('issues'), 'write')

    def test_the_c18_alert_half_never_reads_the_build_queue(self):
        run = step(load(AUTOMATED['C18']), 'C18 alert half')['run']
        self.assertIn('--drill', run)
        self.assertIn('--queue omni-drill-no-consumer', run)
        self.assertNotIn('omni-builds', run)


def fake_bin(d, name, body):
    p = Path(d) / name
    p.write_text(body, encoding='utf-8')
    p.chmod(p.stat().st_mode | stat.S_IEXEC)


FAKE_GH = textwrap.dedent('''\
    #!/usr/bin/env python3
    """gh, as the C16 drill calls it: records every call; answers from $FAKE_STATE."""
    import json, os, sys
    state = json.load(open(os.environ['FAKE_STATE']))
    args = sys.argv[1:]
    open(os.environ['FAKE_LOG'], 'a').write(json.dumps(args) + '\\n')
    a = ' '.join(args)
    def out(v):
        print(v)
        sys.exit(0)
    if 'git/ref/heads/main' in a:
        out(state['main'])
    if '-X POST' in a and 'git/refs' in a:
        sys.exit(0)
    if '-X PUT' in a and '/contents/' in a:
        out('drillhead')
    if '-X POST' in a and a.endswith('--jq .number') and '/pulls' in a:
        out('901')
    if '-X POST' in a and '/check-runs' in a:
        sys.exit(0)
    if '/commits/drillhead/check-runs' in a:
        out(state['red'])
    if 'pulls/901 --jq .mergeable' in a:
        out(state['mergeable'])
    if '-X PATCH' in a or '-X DELETE' in a or '/issues' in a:
        out('ok')
    sys.exit('fake gh: unexpected call ' + a)
''')

FAKE_CURL = textwrap.dedent('''\
    #!/usr/bin/env python3
    """curl, for the merge attempt: writes the answer body to -o, prints the HTTP code; may move main."""
    import json, os, sys
    state = json.load(open(os.environ['FAKE_STATE']))
    args = sys.argv[1:]
    open(os.environ['FAKE_LOG'], 'a').write(json.dumps(['curl'] + args) + '\\n')
    body = args[args.index('-o') + 1]
    open(body, 'w').write(json.dumps({'message': state['merge_message']}))
    if state['merge_code'] == '200':
        state['main'] = 'merged-main'
        json.dump(state, open(os.environ['FAKE_STATE'], 'w'))
    sys.stdout.write(state['merge_code'])
''')


class C16DecidesOnlyOnARealRefusal(unittest.TestCase):
    """The C16 drill script, run as written, with gh and curl answering like GitHub."""

    def setUp(self):
        if not shutil.which('jq') or not shutil.which('bash'):
            self.skipTest('BLOCKED: jq and bash are needed to run the drill script as written')
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.bin = os.path.join(self.dir, 'bin')
        os.mkdir(self.bin)
        fake_bin(self.bin, 'gh', FAKE_GH)
        fake_bin(self.bin, 'curl', FAKE_CURL)
        self.script = step(load(AUTOMATED['C16']), 'C16 -- ')['run']

    def drill(self, **over):
        state = {'main': 'main0', 'red': 'test=failure,validate=failure', 'mergeable': 'true', 'merge_code': '405',
                 'merge_message': '2 of 2 required status checks are failing.'}
        state.update(over)
        st, log, outp = (os.path.join(self.dir, n) for n in ('state.json', 'log', 'out'))
        Path(st).write_text(json.dumps(state))
        Path(log).write_text('')
        Path(outp).write_text('')
        env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ['PATH'], FAKE_STATE=st, FAKE_LOG=log,
                   GITHUB_OUTPUT=outp, GITHUB_REPOSITORY='o/r', GITHUB_RUN_ID='77', GH_TOKEN='t', BR='drill/c16-77',
                   RUNNER_TEMP=self.dir)
        p = subprocess.run(['bash', '-c', self.script], env=env, capture_output=True, text=True, timeout=120)
        calls = [json.loads(line) for line in Path(log).read_text().splitlines()]
        return p.returncode, p.stdout + p.stderr, calls, Path(outp).read_text()

    def test_a_405_naming_the_required_checks_with_main_unmoved_is_pass(self):
        rc, out, calls, outputs = self.drill()
        self.assertEqual(rc, 0, out)
        self.assertIn('C16 PASS', out)
        self.assertIn('pr=901', outputs)                  # the cleanup step closes it
        merge = [c for c in calls if c[0] == 'curl'][0]
        self.assertIn('{"sha":"drillhead","merge_method":"merge"}', merge)

    def test_both_required_checks_are_completed_as_failure_on_the_drill_head(self):
        _, _, calls, _ = self.drill()
        made = [c for c in calls if '/check-runs' in ' '.join(c) and '-X' in c and 'POST' in c]
        names = sorted(next(a.split('=', 1)[1] for a in c if a.startswith('name=')) for c in made)
        self.assertEqual(names, REQUIRED_CHECKS)
        for c in made:
            self.assertIn('head_sha=drillhead', c)
            self.assertIn('conclusion=failure', c)

    def test_a_merge_that_went_through_is_fail(self):
        rc, out, _, _ = self.drill(merge_code='200', merge_message='Pull Request successfully merged')
        self.assertEqual(rc, 1)
        self.assertIn('C16 FAIL', out)

    def test_a_405_for_another_reason_is_not_pass(self):
        rc, out, _, _ = self.drill(merge_message='Pull Request is not mergeable')
        self.assertEqual(rc, 1)
        self.assertNotIn('C16 PASS', out)

    def test_a_head_that_does_not_read_red_is_not_run(self):
        rc, out, calls, _ = self.drill(red='test=failure')
        self.assertEqual(rc, 1)
        self.assertIn('C16 NOT RUN', out)
        self.assertFalse([c for c in calls if c[0] == 'curl'])   # no merge attempt on a head that is not red

    def test_a_pr_github_cannot_merge_for_another_reason_is_not_run(self):
        rc, out, calls, _ = self.drill(mergeable='false')
        self.assertEqual(rc, 1)
        self.assertIn('C16 NOT RUN', out)
        self.assertFalse([c for c in calls if c[0] == 'curl'])

    def test_the_cleanup_always_runs_and_closes_the_pr_and_deletes_the_branch(self):
        s = step(load(AUTOMATED['C16']), 'Close the drill PR')
        self.assertEqual(s['if'], 'always()')
        self.assertIn('-X PATCH "repos/$repo/pulls/$pr" -f state=closed', s['run'])
        self.assertIn('-X DELETE "repos/$repo/git/refs/heads/$br"', s['run'])


class C18AlertHalfDecidesOnTheAlertsOwnVerdict(unittest.TestCase):
    """The C18 alert-half script, run as written, with `python tools/worker_alert.py` answering as given."""

    def setUp(self):
        if not shutil.which('bash'):
            self.skipTest('BLOCKED: bash is needed to run the drill script as written')
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.script = step(load(AUTOMATED['C18']), 'C18 alert half')['run']

    def drill(self, rc, lines):
        b = os.path.join(self.dir, 'bin')
        os.makedirs(b, exist_ok=True)
        fake_bin(b, 'python', '#!/usr/bin/env bash\ncat <<\'EOF\'\n' + '\n'.join(lines) + f'\nEOF\nexit {rc}\n')
        env = dict(os.environ, PATH=b + os.pathsep + os.environ['PATH'], RUNNER_TEMP=self.dir,
                   GITHUB_REPOSITORY='o/r')
        p = subprocess.run(['bash', '-c', self.script], env=env, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr

    DEAD = '::notice title=worker alert dead::omni-drill-no-consumer: no worker is registered on the queue'

    def test_dead_with_the_drill_issue_raised_and_closed_is_pass(self):
        rc, out = self.drill(1, [self.DEAD, '::notice title=worker alert issue::opened and closed drill issue #12'])
        self.assertEqual(rc, 0, out)
        self.assertIn('C18 alert half PASS', out)

    def test_an_unreadable_registry_is_fail(self):
        rc, out = self.drill(2, ['::notice title=worker alert unverified::omni-drill-no-consumer: cannot read'])
        self.assertEqual(rc, 1)
        self.assertIn('FAIL', out)

    def test_dead_without_the_issue_is_fail(self):
        rc, out = self.drill(1, [self.DEAD, '::error title=worker alert::the issue could not be raised'])
        self.assertEqual(rc, 1)

    def test_a_live_worker_on_the_drill_queue_is_fail(self):
        rc, out = self.drill(0, ['::notice title=worker alert alive::omni-drill-no-consumer: 1 live',
                                 '::notice title=worker alert issue::nothing open'])
        self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()

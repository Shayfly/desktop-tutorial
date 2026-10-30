"""deploy-worker mode=drill (2026-10-27): the recovery drill on the live worker. Pins the safety properties: a plain
deploy is unchanged, the drill never checks out / builds / migrates, every result is a PASS|FAIL ::notice, and the
roll-forward always runs."""
import pathlib
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = yaml.safe_load((ROOT / '.github/workflows/deploy-worker.yml').read_text())
JOBS = WF['jobs']
ON = WF.get('on') or WF.get(True)


class DrillMode(unittest.TestCase):
    def test_mode_input_defaults_to_deploy_and_deploy_job_still_runs_on_push(self):
        mode = ON['workflow_dispatch']['inputs']['mode']
        self.assertEqual((mode['default'], mode['options']), ('deploy', ['deploy', 'drill']))
        self.assertEqual(JOBS['deploy']['if'], "github.event_name != 'workflow_dispatch' || inputs.mode != 'drill'")
        self.assertEqual(JOBS['drill']['if'], "github.event_name == 'workflow_dispatch' && inputs.mode == 'drill'")

    def test_drill_never_checks_out_builds_or_migrates(self):
        steps = JOBS['drill']['steps']
        self.assertFalse(any('uses' in s for s in steps), 'no checkout: it would delete the deployed .env')
        text = '\n'.join(s.get('run', '') for s in steps)
        for forbidden in ('docker compose build', 'omni_prod.migrate', 'git checkout', 'docker compose down', 'volume rm',
                          'prune'):
            self.assertNotIn(forbidden, text)
        self.assertIn('--no-build', text)

    def test_drill_runs_the_three_parts_with_pass_fail_notices(self):
        names = [s['name'] for s in JOBS['drill']['steps']]
        for part in ('A. Real build, SIGKILL', 'B. Exactly once', 'C1. recover.sh', 'C2. Roll forward'):
            self.assertTrue(any(n.startswith(part) for n in names), part)
        text = '\n'.join(s.get('run', '') for s in JOBS['drill']['steps'])
        self.assertIn('docker kill', text)
        self.assertIn('bash recover.sh', text)
        for title in ('drill-B exactly-once', 'drill-B zero-duplicates', 'drill-B zero-loss', 'drill-B zero-double-charge'):
            self.assertIn(title.split(' ', 1)[1], text)
        self.assertIn("'PASS' if ok else 'FAIL'", text)

    def test_customer_work_is_checked_first_and_roll_forward_always_runs(self):
        steps = JOBS['drill']['steps']
        names = [s['name'] for s in steps]
        self.assertLess(names.index('Refuse while customer work is running'),
                        next(i for i, n in enumerate(names) if n.startswith('A.')))
        roll = next(s for s in steps if s['name'].startswith('C2.'))
        self.assertEqual(roll['if'], 'always()')
        self.assertEqual(steps[-1], roll)

    def test_rollback_verdict_never_comes_from_recover_sh_exit_code(self):
        """Codex blocker 2026-10-27: recover.sh exits 0 when it restores nothing (list read from a RUNNER_TEMP that a
        new run does not share). The drill writes its own list, proves the snapshots exist, verifies the images."""
        c1 = next(s for s in JOBS['drill']['steps'] if s['name'].startswith('C1.'))
        run = c1['run']
        self.assertIn('${{ runner.temp }}/drill-state', c1['env']['DEPLOY_STATE_DIR'])
        self.assertIn('>> "$list"', run)                                    # its own verified list
        self.assertIn('docker image inspect -f \'{{.Id}}\' "omni-rollback/$s:prev"', run)   # snapshot exists
        self.assertIn('never the verdict', run)
        self.assertNotRegex(run, r'bash recover\.sh; rc=\$\?')            # exit code not captured as the verdict
        self.assertIn('[ "$want" = "$got" ]', run)                            # running image == snapshot image
        self.assertIn('wrote no rollback compose file', run)
        self.assertIn('a rollback to it proves nothing', run)                 # identical snapshot is not a PASS
        self.assertTrue(run.rstrip().endswith('[ "$ok" -eq 1 ]'))

    def test_kill_only_after_the_build_is_proven_mid_flight(self):
        """Auditor gap 1: killing a worker that never picked the job up interrupts nothing (false PASS in B)."""
        a = next(s for s in JOBS['drill']['steps'] if s['name'].startswith('A.'))['run']
        pre, kill = a.index('drill-A pre-kill'), a.index('docker kill')
        self.assertLess(pre, kill)
        self.assertIn("str(status).lower() in ('running'", a)
        self.assertIn("kind = 'provider_call'", a[:kill])
        self.assertIn('NOT killing the worker"; exit 1', a[:kill])

    def test_double_charge_notice_states_its_scope(self):
        b = next(s for s in JOBS['drill']['steps'] if s['name'].startswith('B.'))['run']
        self.assertIn('no provider-side billing reconciliation', b)


if __name__ == '__main__':
    unittest.main()

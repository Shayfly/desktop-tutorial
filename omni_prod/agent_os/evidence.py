"""Real runs that back Agent OS / Skills OS statuses (2026-10-09).

Each is a run on the deployed pre-staging system with an id anyone with repo
access can open (GitHub Actions run). `commit` is the worker code that ran,
so the audit marks the evidence STALE as soon as the implementation changes.
`asserts` is exactly what the run checked: a status is never wider than that.
"""
from ..runtime_bindings import Evidence

FREE = Evidence('live', 'postdeploy-checks run 37962165888', 'free real-server checks, 16/16 PASS', '039574f', 'worker-host',
                ('migrations applied', 'builder health', 'existing versions load + checksum', 'demo/publish refused',
                 'preview creation', 'preview private by default (anonymous 401)', 'owner token access',
                 'share link only while shared', 'data survives preview restart', 'data survives a new version',
                 'queued build cancelled + reservation released', 'running build stops before any model call',
                 'journal resumes after refresh', 'cancel scoped to owner/project',
                 'agent task graph closed for a cancelled build'))
PAID = Evidence('live', 'postdeploy-checks run 37961193099', 'discovery -> approval -> build -> preview, READY, '
                'settled $0.105302 at metered usage incl. thinking tokens', '039574f', 'worker-host',
                ('discovery conversation', 'server-bound approval', 'model-built product READY',
                 'browser check in the build', 'QA model review rounds', 'build journal',
                 'preview of the built version', 'acceptance stored, page responsive',
                 'agent task graph with independent verification', 'settlement at metered usage'))
# Same run: behaviour acceptance failed in round 1 (A5 not covered), the QA
# review then failed (browser alert dialogs); both were repaired; PASS.
REHEARSAL_ACCEPT = Evidence('live', 'postdeploy-checks run 37961193099 (attempt ledger via inspect run 37962090098)',
                            'barber booking app: behaviour acceptance failed, repaired; review failed, repaired; '
                            'preview acceptance PASS (7 checks, 5 acceptance IDs)', '039574f', 'worker-host',
                            ('in-build behavioural acceptance', 'acceptance failure repaired', 'requirements-aware scope',
                             'code generation', 'repair loop', 'browser check', 'quality gate'))
# Worker SIGKILLed at the second model call. READY after recovery; ledger has
# both workers (2 traces) and settled == ledger sum. The run's separate
# agent-graph check read the run before the worker closed it (fixed since);
# inspect run 37955419872 shows the recovered run closed 'ready' and the lost
# worker's run 'superseded'.
CRASH = Evidence('live', 'postdeploy-checks run 37954236866 (+ inspect 37955419872)', 'worker SIGKILLed mid-build, '
                 'recovered, READY; settled $0.070368 = ledger sum of both workers', '2b4bafd', 'worker-host',
                 ('crash recovery (requeue once)', 'build finished after recovery', 'settlement at metered usage',
                  "lost worker's calls settled", 'superseded agent run closed'))
BACKUP = Evidence('live', 'backup-restore run 37962179844', 'stored copy restored into empty PostgreSQL 18; 42/42 versions '
                  'rebuilt; 14/14 data files; 34 migrations equal', '039574f', 'worker-host',
                  ('database backup', 'artifact/project backup', 'restore of the stored copy', 'version rebuild from artifacts',
                   'preview data archive', 'retention prune'))
DEPLOY = Evidence('live', 'deploy-worker run 37960891900', 'drain, migrations, probes', '039574f', 'worker-host',
                  ('drain before replace', 'migrations', 'queue consumed', 'sandbox isolated (no network)',
                   'storage write/read/delete', 'browser probe both fixtures', 'preview data self-test', 'preview edge'))

# When each run happened (UTC) -- shown as last_verified_at.
AT = {
    FREE.ref: '2026-10-09T16:51Z', PAID.ref: '2026-10-09T16:43Z', REHEARSAL_ACCEPT.ref: '2026-10-09T16:43Z',
    CRASH.ref: '2026-10-09T15:46Z', BACKUP.ref: '2026-10-09T16:52Z', DEPLOY.ref: '2026-10-09T16:41Z',
}

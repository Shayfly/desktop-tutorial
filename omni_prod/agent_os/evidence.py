"""Real runs that back Agent OS / Skills OS statuses (2026-10-09).

Each is a run on the deployed pre-staging system with an id anyone with repo
access can open (GitHub Actions run). `commit` is the worker code that ran,
so the audit marks the evidence STALE as soon as the implementation changes.
`asserts` is exactly what the run checked: a status is never wider than that.
"""
from ..runtime_bindings import Evidence

FREE = Evidence('live', 'postdeploy-checks run 37936709830', 'free real-server checks, all PASS', '1c7a9c9', 'worker-host',
                ('migrations applied', 'builder health', 'existing versions load + checksum', 'demo/publish refused',
                 'preview creation', 'preview private by default (anonymous 401)', 'owner token access',
                 'share link only while shared', 'data survives preview restart', 'data survives a new version',
                 'queued build cancelled + reservation released', 'running build stops before any model call',
                 'journal resumes after refresh', 'cancel scoped to owner/project'))
PAID = Evidence('live', 'postdeploy-checks run 37924920646', 'discovery -> approval -> build -> preview, $0.1209', '301d631',
                'worker-host', ('discovery conversation', 'server-bound approval', 'model-built product READY',
                                'browser check in the build', 'QA model review rounds', 'build journal',
                                'preview of the built version', 'acceptance stored, page responsive'))
REHEARSAL_ACCEPT = Evidence('live', 'golden-rehearsal run 37937211420', 'booking app: behaviour acceptance failed, '
                            'repaired, passed (10 checks); ready; $0.0715', '1c7a9c9', 'worker-host',
                            ('in-build behavioural acceptance', 'acceptance failure repaired', 'requirements-aware scope',
                             'code generation', 'repair loop', 'browser check', 'quality gate'))
CRASH = Evidence('live', 'postdeploy-checks run 37940033628', 'worker SIGKILLed mid-build, recovered, READY, '
                 'settled at metered $0.0914', 'd1c7482', 'worker-host',
                 ('crash recovery (requeue once)', 'build finished after recovery', 'settlement at metered usage'))
BACKUP = Evidence('live', 'backup-restore run 37939539147', 'stored copy restored into empty PostgreSQL 18; 31/31 versions '
                  'rebuilt; 9/9 data files', '4dccda8', 'worker-host',
                  ('database backup', 'artifact/project backup', 'restore of the stored copy', 'version rebuild from artifacts',
                   'preview data archive', 'retention prune'))
DEPLOY = Evidence('live', 'deploy-worker run 37939751400', 'drain, migrations, probes', 'd1c7482', 'worker-host',
                  ('drain before replace', 'migrations', 'queue consumed', 'sandbox isolated (no network)',
                   'storage write/read/delete', 'browser probe both fixtures', 'preview data self-test', 'preview edge'))

# When each run happened (UTC) -- shown as last_verified_at.
AT = {
    FREE.ref: '2026-10-09T12:43Z', PAID.ref: '2026-10-09T11:30Z', REHEARSAL_ACCEPT.ref: '2026-10-09T12:55Z',
    CRASH.ref: '2026-10-09T13:58Z', BACKUP.ref: '2026-10-09T13:49Z', DEPLOY.ref: '2026-10-09T13:55Z',
}

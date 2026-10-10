-- Durable per-stage quality evidence (migration 035). Issue #6 P1, Production
-- Assurance v2 §5. Additive; rollback = DROP TABLE build_stage_results (nothing
-- else reads it).
--
-- One row per check of the release policy for one build: the checked artifact
-- digest, the policy version, who verified (platform module or model) and
-- whether that verifier is independent of the generating model. Rows are
-- immutable; a repeated write for the same (build, artifact, policy, check) is
-- a no-op, so a duplicate delivery or a recovered worker cannot change them.
-- A different artifact digest is a different row: evidence never transfers
-- from one repository state to another.

CREATE TABLE IF NOT EXISTS build_stage_results (
    id              BIGSERIAL PRIMARY KEY,
    build_id        TEXT NOT NULL,
    job_kind        TEXT NOT NULL DEFAULT 'build' CHECK (job_kind IN ('build', 'modification', 'replay')),
    tenant_key      TEXT,
    stage           TEXT NOT NULL,
    check_key       TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL', 'NOT_RUN', 'UNKNOWN', 'NOT_APPLICABLE')),
    required        BOOLEAN NOT NULL,
    verifier        TEXT NOT NULL,
    independent     BOOLEAN NOT NULL,
    severity        TEXT NOT NULL,
    detail          TEXT NOT NULL DEFAULT '' CHECK (length(detail) <= 1000),
    artifact_sha256 TEXT NOT NULL,
    policy_version  TEXT NOT NULL,
    report_schema   TEXT NOT NULL,
    decision        TEXT NOT NULL CHECK (decision IN ('READY', 'FAILED')),
    source_commit   TEXT,
    environment     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (build_id, artifact_sha256, policy_version, check_key)
);
CREATE INDEX IF NOT EXISTS idx_build_stage_results_build ON build_stage_results (build_id);
CREATE INDEX IF NOT EXISTS idx_build_stage_results_check ON build_stage_results (check_key, status, created_at DESC);

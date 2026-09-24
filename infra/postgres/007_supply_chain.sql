CREATE TABLE IF NOT EXISTS release_attestations (
    release_id TEXT PRIMARY KEY,
    sbom_sha256 TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    attestation_json JSONB NOT NULL,
    dependency_lock_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

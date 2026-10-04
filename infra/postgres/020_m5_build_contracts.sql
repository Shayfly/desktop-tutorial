-- M5 Task 4: immutable, versioned Build Contracts.
-- A build contract binds one product-intent revision to deterministic capability,
-- infrastructure, security, acceptance and cost-envelope truth.

CREATE TABLE IF NOT EXISTS m5_build_contracts (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES creator_projects(id) ON DELETE RESTRICT,
    contract_version INTEGER NOT NULL CHECK (contract_version > 0),
    status TEXT NOT NULL CHECK (status IN ('READY','NEEDS_CLARIFICATION','BLOCKED')),
    capability_plan_fingerprint TEXT NOT NULL,
    contract_fingerprint TEXT NOT NULL,
    contract_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(project_id, contract_version)
);

CREATE INDEX IF NOT EXISTS idx_m5_build_contracts_project_version
    ON m5_build_contracts(project_id, contract_version DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_m5_build_contracts_project_fingerprint
    ON m5_build_contracts(project_id, contract_fingerprint);

CREATE OR REPLACE FUNCTION reject_m5_build_contract_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'm5 build contracts are immutable; create a new contract revision';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_m5_build_contracts_immutable ON m5_build_contracts;
CREATE TRIGGER trg_m5_build_contracts_immutable
BEFORE UPDATE OR DELETE ON m5_build_contracts
FOR EACH ROW EXECUTE FUNCTION reject_m5_build_contract_mutation();

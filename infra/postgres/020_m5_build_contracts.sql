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

-- M5 Task 5: every new durable build request is bound to one immutable
-- Build Contract revision. Nullable preserves readability of pre-M5 rows.
ALTER TABLE build_requests
    ADD COLUMN IF NOT EXISTS build_contract_id TEXT REFERENCES m5_build_contracts(id) ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_build_requests_build_contract
    ON build_requests(build_contract_id)
    WHERE build_contract_id IS NOT NULL;

CREATE OR REPLACE FUNCTION m5_build_request_contract_project()
RETURNS TRIGGER AS $$
DECLARE
    contract_project TEXT;
BEGIN
    IF NEW.build_contract_id IS NULL THEN
        RETURN NEW;
    END IF;
    IF NEW.public_project_id IS NULL THEN
        RAISE EXCEPTION 'bound build request requires public_project_id';
    END IF;
    SELECT project_id INTO contract_project
      FROM m5_build_contracts
     WHERE id = NEW.build_contract_id;
    IF contract_project IS NULL THEN
        RAISE EXCEPTION 'build contract does not exist';
    END IF;
    IF contract_project IS DISTINCT FROM NEW.public_project_id THEN
        RAISE EXCEPTION 'build contract project mismatch';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_m5_build_request_contract_project ON build_requests;
CREATE TRIGGER trg_m5_build_request_contract_project
BEFORE INSERT OR UPDATE OF build_contract_id, public_project_id ON build_requests
FOR EACH ROW EXECUTE FUNCTION m5_build_request_contract_project();

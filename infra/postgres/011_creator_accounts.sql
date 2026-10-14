CREATE TABLE IF NOT EXISTS creator_accounts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt_b64 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS creator_projects (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES creator_accounts(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS creator_projects_owner_updated_idx ON creator_projects(owner_id, updated_at DESC);

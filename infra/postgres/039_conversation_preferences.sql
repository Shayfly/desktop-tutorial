-- Persist the account's conversation language preference. Additive only.
CREATE TABLE IF NOT EXISTS conversation_preferences (
    account_id  TEXT PRIMARY KEY REFERENCES creator_accounts(id) ON DELETE CASCADE,
    language    TEXT NOT NULL DEFAULT 'he' CHECK (language IN ('he', 'en')),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS creator_subscriptions (
    user_id TEXT PRIMARY KEY REFERENCES creator_accounts(id) ON DELETE CASCADE,
    plan_code TEXT NOT NULL DEFAULT 'free',
    cycle TEXT NOT NULL,
    credits_used INTEGER NOT NULL DEFAULT 0 CHECK (credits_used >= 0),
    provider_spend_usd NUMERIC(14,6) NOT NULL DEFAULT 0 CHECK (provider_spend_usd >= 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

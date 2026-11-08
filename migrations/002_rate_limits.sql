-- AgentPay Nexus - Production Database Migration 002
-- Distributed DB-Backed Rate Limiting & Resource Protection (Supabase / PostgreSQL)

CREATE TABLE IF NOT EXISTS rate_limits (
    key VARCHAR(255) PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Index on expires_at for efficient cleanup and window expiry checks
CREATE INDEX IF NOT EXISTS idx_rate_limits_expires_at ON rate_limits (expires_at);

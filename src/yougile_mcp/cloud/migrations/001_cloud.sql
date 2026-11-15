-- GEN-231 self-hosted cloud storage.
-- Design adapted from Indalo yougile-mcp-cloud 001_init.sql (AGPL-3.0, © Indalo).
-- No subscriptions, trials, payments, or company billing status.
CREATE TABLE cloud_companies (
    id text PRIMARY KEY,
    name text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cloud_users (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id text NOT NULL REFERENCES cloud_companies (id) ON DELETE CASCADE,
    yougile_user_id text NOT NULL,
    email text NOT NULL DEFAULT '',
    name text NOT NULL DEFAULT '',
    is_admin boolean NOT NULL DEFAULT false,
    enabled boolean NOT NULL DEFAULT true,
    api_key_enc bytea NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(company_id, yougile_user_id)
);

CREATE INDEX cloud_users_company_idx ON cloud_users (company_id);

CREATE TABLE cloud_oauth_clients (
    client_id text PRIMARY KEY,
    info jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cloud_refresh_tokens (
    token_hash text PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES cloud_users (id) ON DELETE CASCADE,
    client_id text NOT NULL,
    scopes jsonb NOT NULL DEFAULT '[]'::jsonb,
    resource text,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX cloud_refresh_user_idx ON cloud_refresh_tokens (user_id);
CREATE INDEX cloud_refresh_expiry_idx ON cloud_refresh_tokens (expires_at);

CREATE TABLE cloud_audit_log (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    at timestamptz NOT NULL DEFAULT now(),
    company_id text,
    user_id bigint,
    event text NOT NULL,
    detail jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX cloud_audit_company_idx ON cloud_audit_log (company_id, at DESC);

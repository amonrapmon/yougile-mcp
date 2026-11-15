-- Persist retired YouGile API keys for retryable revocation after OAuth redirects.
-- Encrypted ciphertext from cloud_users is copied in the same transaction.
CREATE TABLE cloud_vendor_key_revocations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id text NOT NULL,
    user_id bigint NOT NULL,
    api_key_enc bytea NOT NULL,
    attempts integer NOT NULL DEFAULT 0,
    ready_at timestamptz NOT NULL DEFAULT now(),
    lease_until timestamptz,
    lease_token text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cloud_vendor_key_revocations_due_idx
    ON cloud_vendor_key_revocations (ready_at, id);

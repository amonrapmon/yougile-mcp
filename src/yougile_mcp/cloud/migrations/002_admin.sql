-- GEN-231 Indalo company-admin controls, © Indalo, AGPL-3.0-only.
-- Allows company admins to block access *before* the user's first login.
-- No roles or project-scopes introduced: MVP is Full Access by vendor key.
CREATE TABLE cloud_member_blocks (
    company_id text NOT NULL REFERENCES cloud_companies(id) ON DELETE CASCADE,
    yougile_user_id text NOT NULL,
    created_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (company_id, yougile_user_id)
);

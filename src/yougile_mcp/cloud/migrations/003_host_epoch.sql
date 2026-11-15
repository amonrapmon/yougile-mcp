-- Host-level access epoch: disabling and re-enabling must not revive OAuth JWTs.
ALTER TABLE cloud_companies
    ADD COLUMN access_epoch bigint NOT NULL DEFAULT 0;

"""Durable, bounded, secret-safe cleanup of retired YouGile API keys.

Cleanup is deliberately independent of the OAuth HTTP response path. Every
replacement key is recorded by the account transaction as an encrypted outbox
entry. Leases allow safe retries after timeouts, crashes and restarts.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from .persistence import PostgresCloudStore
from .yougile_signin import CloudYouGileSignIn

_LOG = logging.getLogger("uvicorn.error")
_REVOKE_TIMEOUT = 8.0
_IDLE_SECONDS = 2.0


async def process_one_key_revocation(
    store: PostgresCloudStore, signin: CloudYouGileSignIn,
) -> bool:
    """Process at most one queued job, returning False when none is due."""
    job = await store.claim_key_revocation()
    if job is None:
        return False
    _LOG.info("vendor_key_revocation stage=old_key_revoke_started job_id=%s attempt=%s",
              job.id, job.attempts)
    try:
        await asyncio.wait_for(signin.revoke_key(job.api_key.reveal()), timeout=_REVOKE_TIMEOUT)
    except Exception:
        # Write operations are not blindly repeated by the API client. A
        # timeout can mean the delete succeeded: a later 404 counts as done.
        delay = min(3600, 15 * (2 ** min(job.attempts - 1, 8)))
        updated = await store.retry_key_revocation(job, delay)
        if updated:
            with suppress(Exception):
                await store.audit(
                    "old_vendor_key_revocation_failed",
                    company_id=job.company_id, user_id=job.user_id,
                    detail={"operation": "vendor_key_delete", "outcome": "retry_scheduled"},
                )
        _LOG.warning("vendor_key_revocation stage=retry_scheduled job_id=%s attempt=%s",
                     job.id, job.attempts)
    else:
        await store.complete_key_revocation(job)
        _LOG.info("vendor_key_revocation stage=old_key_revoke_finished job_id=%s attempt=%s",
                  job.id, job.attempts)
    return True


async def run_key_revocation_worker(
    store: PostgresCloudStore, signin: CloudYouGileSignIn,
) -> None:
    """Keep draining due jobs; storage failures never crash the OAuth server."""
    while True:
        try:
            processed = await process_one_key_revocation(store, signin)
            if not processed:
                await asyncio.sleep(_IDLE_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Exception messages could contain provider or database secrets.
            _LOG.error("vendor_key_revocation stage=worker_error")
            await asyncio.sleep(5)

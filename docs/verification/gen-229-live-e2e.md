# GEN-229 live E2E API v2 report

**Date:** 2026-11-14

**Last full read-only sweep:** 2026-11-14 15:41 UTC (18:41 Moscow).

**Draft PR:** [#13](https://github.com/amonrapmon/yougile-mcp/pull/13). **GitHub Actions:** [run](https://github.com/amonrapmon/yougile-mcp/actions/runs/43612067944) — Python 3.11, Python 3.12 and Docker passed.

**Scope:** all 72 catalog operation IDs; reads only against the owner-confirmed disposable company.

**Credential handling:** loaded from the profile-local `e2e.env` into the Python process; no values, company identifier, account profile, task data or response bodies were recorded.

**SDK:** shared `YouGileClient`; pinned vendor OpenAPI SHA-256 `9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406` remains unchanged.

## Run summary

| Pass | Fail | Blocked | Skipped | Not run | HTTP attempts |
|---:|---:|---:|---:|---:|---:|
| 17 | 4 | 40 | 11 | 0 | 21 initial; final sweep: 23 |

The first complete diagnostic run found four schema mismatches, all `deleted: null` where the pinned schema required `boolean`: `BoardController_get` (`deleted`), `ProjectController_get` (`deleted`), `TaskController_get` (`deleted`), and `GroupChatController_search` (`content.[item].deleted`). The expected type was `boolean`; actual JSON type was `null` in each case.

A full rerun after overlay `2026-11-14.4` passed those four findings and unlocked `GroupChatController_get`, which exposed the same mismatch at `deleted`. Overlay `2026-11-14.5` added only `GroupChatDto`; the next full rerun completed with **23 PASS, 0 FAIL, 40 BLOCKED, 9 SKIPPED, 0 NOT RUN**. The initial and final statuses are shown below.

All final successful HTTP calls returned HTTP 200 and passed strict SDK response validation. Each PASS and initial schema FAIL row represents one request; BLOCKED and SKIPPED rows were not called. The final full sweep used 23/50 allowed HTTP attempts, including two preflight calls. The runner continued independent probes after validation failures and skipped only dependent detail calls without a usable test fixture.

No cleanup ran because no live write operation was performed.

## Operation matrix

| Operation ID | Method | Effect | Initial | Initial evidence | Final | Final evidence | Reason / evidence |
|---|---|---|---|---|---|---|---|
| `AuthKeyController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `AuthKeyController_delete` | `DELETE` | `destructive` | BLOCKED | not called | BLOCKED | not called | BLOCKED: separate destructive-action approval required. |
| `AuthKeyController_search` | `POST` | `read` | SKIPPED | not called | SKIPPED | not called | Credential-bearing read; excluded from the sweep. |
| `BoardController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `BoardController_get` | `GET` | `read` | FAIL | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Schema mismatch: `deleted` expected boolean, actual null. |
| `BoardController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `BoardController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ChatMessageController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `ChatMessageController_search` | `GET` | `read` | SKIPPED | not called | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `ChatMessageController_sendMessage` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ChatMessageController_typing` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ChatMessageController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ColumnController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ColumnController_get` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `ColumnController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `ColumnController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `CompanyController_get` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `CompanyController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `CrmContactPersonsController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `CrmExternalIdController_findContactByExternalId` | `GET` | `read` | BLOCKED | not called | BLOCKED | not called | BLOCKED: no test-only external-ID fixture. |
| `DepartmentController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `DepartmentController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `DepartmentController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `DepartmentController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `FileController_uploadFile` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `GroupChatController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `GroupChatController_get` | `GET` | `read` | SKIPPED | not called | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `GroupChatController_search` | `GET` | `read` | FAIL | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Schema mismatch: `content.[item].deleted` expected boolean, actual null. |
| `GroupChatController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ProjectController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ProjectController_get` | `GET` | `read` | FAIL | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Schema mismatch: `deleted` expected boolean, actual null. |
| `ProjectController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `ProjectController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ProjectRolesController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `ProjectRolesController_delete` | `DELETE` | `destructive` | BLOCKED | not called | BLOCKED | not called | BLOCKED: separate destructive-action approval required. |
| `ProjectRolesController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `ProjectRolesController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `ProjectRolesController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `SprintStickerController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `SprintStickerController_getSticker` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `SprintStickerController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `SprintStickerController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `SprintStickerStateController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `SprintStickerStateController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `SprintStickerStateController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `StringStickerController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `StringStickerController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `StringStickerController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `StringStickerController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `StringStickerStateController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `StringStickerStateController_get` | `GET` | `read` | SKIPPED | not called | SKIPPED | not called | SKIPPED: no related test fixture was returned by the bounded list probe. |
| `StringStickerStateController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `TaskController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `TaskController_get` | `GET` | `read` | FAIL | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Schema mismatch: `deleted` expected boolean, actual null. |
| `TaskController_getChatSubscribers` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `TaskController_getLog` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `TaskController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `TaskController_searchReversed` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `TaskController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `TaskController_updateChatSubscribers` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `UserController_clearCustomStatus` | `DELETE` | `destructive` | BLOCKED | not called | BLOCKED | not called | BLOCKED: separate destructive-action approval required. |
| `UserController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `UserController_delete` | `DELETE` | `destructive` | BLOCKED | not called | BLOCKED | not called | BLOCKED: separate destructive-action approval required. |
| `UserController_get` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `UserController_getMe` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `UserController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `UserController_setCustomStatus` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `UserController_update` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `WebhookController_create` | `POST` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `WebhookController_put` | `PUT` | `write` | BLOCKED | not called | BLOCKED | not called | BLOCKED: writes await an approved plan and test fixtures. |
| `WebhookController_search` | `GET` | `read` | PASS | client live · HTTP 200 · 1 request | PASS | client live · HTTP 200 · 1 request | Live SDK response validated. |
| `getCompanies` | `POST` | `read` | SKIPPED | not called | SKIPPED | not called | Credential-bearing read; excluded from the sweep. |

## Write plan status

No live create, update, delete, message-send, callback, file-upload, auth-key, user, role, company or CRM mutation was performed. The built-in read-only sweep requires `--confirm-disposable-company`; other live plans use an external plan file. Writes additionally require `--allow-writes`, destructive operations require `--allow-destructive`, and sensitive operations require `--allow-sensitive`. Each target must be a listed test fixture or created in the run; create payloads require the `YOUGILE_MCP_E2E_…` marker. Webhook URLs require an exact callback allowlist. The write workflows and dependency requirements still need owner review before any such run.

## Evidence boundaries

- `PASS` means this bounded SDK request variant returned a 2xx response and passed the pinned schema plus approved overlay; it does not prove every page, permission, or payload variant.
- `SKIPPED` reflects empty/missing related test fixtures or credential-bearing reads; it is not a failed API operation.
- `BLOCKED` records methods intentionally withheld by the no-write boundary or missing test-only lookup data.
- Historical raw-curl evidence remains separately labeled in the catalog and is not treated as Python-client coverage.
- No tests or CI run is described as live evidence.

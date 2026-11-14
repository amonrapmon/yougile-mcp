# GEN-229 live E2E API v2 report

**Date:** 2026-11-14
**Draft PR:** [#13](https://github.com/amonrapmon/yougile-mcp/pull/13).
**Scope:** all 72 OpenAPI v2 operation IDs, with live requests against the owner-confirmed disposable test company.
**Credentials:** loaded from the profile-local `e2e.env` into the runner process; no key, company identifier, entity content, response body or fixture ID was written to the repository or report.
**OpenAPI source:** pinned snapshot SHA-256 `9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406` is unchanged. Compatibility overlay: `2026-11-14.6`.

## Final matrix

| Status | Operations |
|---|---:|
| PASS | 55 |
| FAIL | 1 |
| BLOCKED | 5 |
| SKIPPED | 11 |
| NOT RUN | 0 |
| **Total** | **72** |

The final re-run used 23 HTTP attempts for the read-only sweep and 40 for the planned write-side sweep. The earlier diagnostic write batch used 41 attempts. Each runner invocation enforced the 50-request cap and verified the authenticated company matched the disposable test-company scope.

PASS means the SDK response passed strict validation for the tested request; for `CrmExternalIdController_findContactByExternalId`, PASS is the expected 404 for a synthetic absent ID. It does not imply every payload, permission or pagination variant was exercised. BLOCKED and SKIPPED entries are not live coverage.

## Results by operation

| Operation ID | Final | Evidence / reason |
|---|---|---|
| `AuthKeyController_create` | BLOCKED | Credential-bearing key creation is not representable in the external fixture plan; no key was created. |
| `AuthKeyController_delete` | BLOCKED | No test key was created; existing credentials and administrative access were left intact. |
| `AuthKeyController_search` | SKIPPED | Credential-bearing results are excluded from the diagnostic runner. |
| `BoardController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_update` | PASS | Ordinary title update passed. A soft-delete update on a board with children returned HTTP 400; no SDK mismatch was established. |
| `ChatMessageController_get` | SKIPPED | No test chat message fixture was created. |
| `ChatMessageController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ChatMessageController_sendMessage` | SKIPPED | Skipped because the synthetic user creation step failed. |
| `ChatMessageController_typing` | SKIPPED | Skipped because no test chat/user chain was created. |
| `ChatMessageController_update` | SKIPPED | Skipped because no test chat message was created. |
| `ColumnController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `CompanyController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `CompanyController_update` | PASS | No-op PUT returned HTTP 200; the company title was unchanged. |
| `CrmContactPersonsController_create` | BLOCKED | An earlier request using a non-CRM project returned HTTP 400; no valid CRM project fixture was available for a valid-payload test. |
| `CrmExternalIdController_findContactByExternalId` | PASS | Expected HTTP 404 for a synthetic absent external ID; the positive lookup path needs a CRM fixture. |
| `DepartmentController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `FileController_uploadFile` | PASS | Two small synthetic text uploads passed. The API inventory has no upload-delete operation; these files remain as residue. |
| `GroupChatController_create` | SKIPPED | Skipped because synthetic user creation failed. |
| `GroupChatController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `GroupChatController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `GroupChatController_update` | SKIPPED | Skipped because no test group chat was created. |
| `ProjectController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_delete` | PASS | Passed after the compatibility overlay made partial response fields optional while keeping present fields validated. |
| `ProjectRolesController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerController_getSticker` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerStateController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerStateController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `SprintStickerStateController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerStateController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerStateController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `StringStickerStateController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_getChatSubscribers` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_getLog` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_searchReversed` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `TaskController_updateChatSubscribers` | SKIPPED | Skipped because synthetic user creation failed. |
| `UserController_clearCustomStatus` | BLOCKED | The runner blocks account-level custom-status mutations to preserve administrative access. |
| `UserController_create` | FAIL | Two synthetic create attempts returned HTTP 400. The sanitized client does not retain the server reason; dependent user/chat writes were skipped. |
| `UserController_delete` | SKIPPED | Skipped because synthetic user creation failed; no existing user was targeted. |
| `UserController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_getMe` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_setCustomStatus` | BLOCKED | The runner blocks account-level custom-status mutations to preserve administrative access. |
| `UserController_update` | SKIPPED | Skipped because synthetic user creation failed; no existing user was targeted. |
| `WebhookController_create` | PASS | Webhook create passed; lifecycle state was later confirmed disabled and deleted. Delivery confirmation is tracked separately. |
| `WebhookController_put` | PASS | Webhook update passed; lifecycle state was later confirmed disabled and deleted. Delivery confirmation is tracked separately. |
| `WebhookController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `getCompanies` | SKIPPED | Credential-bearing lookup is excluded from the diagnostic runner. |

## Confirmed compatibility findings and fixes

- Live Board, Project, Task and GroupChat responses used `deleted: null` where the pinned OpenAPI required a boolean. Narrow DTO overlay entries now allow null only for those affected fields; strict validation remains enabled for other values.
- `ProjectRolesController_delete` returned a partial role DTO. The operation-specific overlay makes the omitted response fields optional and continues validating fields that are present.
- A synthetic absent CRM external ID returned HTTP 404 while the snapshot documented only 200. Overlay v6 records the not-found response; a positive lookup still needs a valid CRM fixture.
- Webhook filter schemas and file upload multipart/response schemas retain the earlier narrowly scoped compatibility entries. The vendor snapshot itself was not edited.

## Other findings and limits

- Two synthetic user-create requests returned HTTP 400. The SDK sanitizes response bodies, so the server's exact validation reason is unknown. The failed dependency prevented creating a test user and therefore skipped user update/delete, group-chat writes, message writes and task-subscriber mutation.
- CRM contact creation was not validly exercised: an earlier request using a non-CRM project returned HTTP 400, and no safe CRM project fixture was available. The final matrix marks it BLOCKED.
- A board title update passed. A separate soft-delete-shaped update on a board with children returned HTTP 400; this was not attributed to an SDK schema mismatch.
- Webhook create, update, search, disable and delete state checks passed. The owner attested that the callback is a test-only HTTP 200 receiver with no downstream actions. Actual event delivery was **not confirmed**: no independent inbound-request observation or successful delivery receipt was captured, and the runner recorded a delivery-failure signal. Do not treat the callback's 200 response alone as delivery proof.
- The project hierarchy and the department, role, sticker and webhook fixtures were cleaned up or soft-deleted where supported. Two small synthetic text uploads remain because the API inventory provides no upload-delete operation. No user or chat fixture was created.

## Evidence and diagnostics

The runner continues independent operations after a failed probe, enforces a per-run request cap, sanitizes diagnostics, and never retries a write after a timeout. The final read-only sweep confirmed the test-company scope and found no unapproved active callback. Raw response bodies, user content, IDs and credentials were not retained.

The 72-row matrix above is live-client evidence, not mocked coverage. Synthetic MockTransport regressions are tracked separately in the test suite.

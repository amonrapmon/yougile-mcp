# GEN-229 live E2E API v2 report

**Date:** 2026-11-14
**Draft PR:** [#13](https://github.com/amonrapmon/yougile-mcp/pull/13).
**Scope:** all 72 OpenAPI v2 operation IDs, with live requests against the owner-confirmed disposable test company.
**Credentials:** loaded from the profile-local `e2e.env` into the runner process; no key, company identifier, entity content, response body or fixture ID was written to the repository or report.
**OpenAPI source:** pinned snapshot SHA-256 `9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406` is unchanged. Compatibility overlay: `2026-11-14.7`.

## Final matrix

| Status | Operations |
|---|---:|
| PASS | 59 |
| FAIL | 1 |
| BLOCKED | 5 |
| SKIPPED | 7 |
| NOT RUN | 0 |
| **Total** | **72** |

The post-change runs used 23 HTTP attempts for the initial read-only sweep, 42 for the main fixture/write chain, 9 and 8 for two isolated synthetic-user/chat diagnostics, and 23 for the final read-only cleanup check. Each invocation stayed below the 50-request cap and verified the authenticated company matched the disposable test-company scope. The matrix carries forward prior live PASS evidence for unchanged operations when final cleanup left no detail fixture; mocked coverage is not counted as live.

PASS means the SDK response passed strict validation for the tested request; for `CrmExternalIdController_findContactByExternalId`, PASS is the expected 404 for a synthetic absent ID. It does not imply every payload, permission or pagination variant was exercised. BLOCKED and SKIPPED entries are not live coverage.

## Results by operation

| Operation ID | Final | Evidence / reason |
|---|---|---|
| `AuthKeyController_create` | BLOCKED | The profile provides only an API key and company ID; login/password inputs required by this operation are unavailable. No key was created. |
| `AuthKeyController_delete` | BLOCKED | No test key could be created and safely identified; existing credentials and administrative access were left intact. |
| `AuthKeyController_search` | SKIPPED | Credential-bearing results are excluded from the diagnostic runner. |
| `BoardController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_update` | PASS | Ordinary title update passed. A soft-delete update on a board with children returned HTTP 400; no SDK mismatch was established. |
| `ChatMessageController_get` | SKIPPED | Group-chat creation returned HTTP 400, so no test message fixture existed. |
| `ChatMessageController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ChatMessageController_sendMessage` | SKIPPED | Group-chat creation returned HTTP 400; no synthetic chat or recipient existed. |
| `ChatMessageController_typing` | SKIPPED | Group-chat creation returned HTTP 400; no synthetic chat existed. |
| `ChatMessageController_update` | SKIPPED | Group-chat creation returned HTTP 400; no synthetic message existed. |
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
| `FileController_uploadFile` | PASS | Three small synthetic text uploads passed across the live runs. The API inventory has no upload-delete operation; these files remain as residue. |
| `GroupChatController_create` | FAIL | Two synthetic users passed creation; group-chat POST returned HTTP 400 with two role-map variants, including the pinned OpenAPI example. The client does not retain the vendor error body, so the exact server validation reason is unknown. |
| `GroupChatController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `GroupChatController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `GroupChatController_update` | SKIPPED | Group-chat creation returned HTTP 400; there was no test chat to update or soft-delete. |
| `ProjectController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_delete` | PASS | Live DELETE returned a DTO containing `id`; overlay v7 requires `id` and validates other DTO fields if present. |
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
| `TaskController_updateChatSubscribers` | PASS | Applied a subscriber update using a synthetic test-company user; the SDK response passed strict validation. |
| `UserController_clearCustomStatus` | BLOCKED | The runner blocks account-level custom-status mutations to preserve administrative access. |
| `UserController_create` | PASS | Synthetic users with non-routable `example.invalid` addresses and `messengerOnly:false` returned HTTP 201 and passed strict validation. |
| `UserController_delete` | PASS | All five synthetic users created during the updated plans were deleted; no existing user was targeted. |
| `UserController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_getMe` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `UserController_setCustomStatus` | BLOCKED | The runner blocks account-level custom-status mutations to preserve administrative access. |
| `UserController_update` | PASS | Updated a synthetic test user and received HTTP 200; the user was deleted during cleanup. |
| `WebhookController_create` | PASS | Webhook create passed; lifecycle state was later confirmed disabled and deleted. Delivery confirmation is tracked separately. |
| `WebhookController_put` | PASS | Webhook update passed; lifecycle state was later confirmed disabled and deleted. Delivery confirmation is tracked separately. |
| `WebhookController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `getCompanies` | SKIPPED | Credential-bearing lookup is excluded from the diagnostic runner. |

## Confirmed compatibility findings and fixes

- Live Board, Project, Task and GroupChat responses used `deleted: null` where the pinned OpenAPI required a boolean. Narrow DTO overlay entries now allow null only for those affected fields; strict validation remains enabled for other values.
- `ProjectRolesController_delete` returned a partial role DTO containing only `id`. Overlay v7 requires that observed identity and validates present optional fields. The missing-`id` and invalid-`id` regressions remain rejected.
- A synthetic absent CRM external ID returned HTTP 404 while the snapshot documented only 200. Overlay v7 records the not-found response; a positive lookup still needs a valid CRM fixture.
- Webhook filter schemas and file upload multipart/response schemas retain the earlier narrowly scoped compatibility entries. The vendor snapshot itself was not edited.

## Other findings and limits

- `UserController_create` returned HTTP 400 with `messengerOnly:true` in an earlier synthetic attempt and HTTP 201 with `messengerOnly:false`; both used non-routable `example.invalid` addresses. The error body is intentionally discarded, so this confirms a server-side input-dependent behavior but does not establish the reason or justify narrowing the OpenAPI boolean schema. User update and delete passed with synthetic fixtures.
- `GroupChatController_create` returned HTTP 400 twice with two newly created synthetic users. The second request used the pinned OpenAPI example's `owner`/`admin` role mapping and role configuration. The client intentionally discards vendor error bodies; the group-chat validation cause is therefore unknown. Message and group-chat update operations remain SKIPPED because no chat was created.
- CRM contact creation was not validly exercised: an earlier request using a non-CRM project returned HTTP 400, and no safe CRM project fixture was available. The final matrix marks it BLOCKED.
- A board title update passed. A separate soft-delete-shaped update on a board with children returned HTTP 400; this was not attributed to an SDK schema mismatch.
- Webhook create, update, search, disable and delete state checks passed, and the final read-only preflight found no unapproved active callback. The YouGile webhook record reported `failuresSinceLastSuccess > 0`, so event delivery is **FAIL / unconfirmed**. The callback's HTTP 200 behavior was owner-attested, but no independent inbound-request observation was available when this report was written.
- The project hierarchy and the department, role, sticker and webhook fixtures were cleaned up or soft-deleted where supported. Five synthetic users were deleted. No group chat or message was created. Three small synthetic text uploads remain because the API inventory provides no upload-delete operation.

## Evidence and diagnostics

The runner continues independent operations after a failed probe, enforces a per-run request cap, sanitizes diagnostics, and never retries a write after a timeout. Its exit code is nonzero when an operation fails or a side-effect check is not PASS; the webhook delivery check therefore correctly failed the run. The final read-only sweep confirmed the test-company scope and found no unapproved active callback. Raw response bodies, user content, IDs and credentials were not retained.

The 72-row matrix above is live-client evidence, not mocked coverage. Synthetic MockTransport regressions are tracked separately in the test suite.

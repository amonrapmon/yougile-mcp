# GEN-229 live E2E API v2 report

**Date:** 2026-11-14; follow-up 2026-11-15
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

The original 72-operation pass used 23 HTTP attempts for the initial read-only sweep, 42 for the main fixture/write chain, 9 and 8 for two isolated synthetic-user/chat diagnostics, and 23 for the final read-only cleanup check. The Nov 15 follow-up used 9 and 11 attempts for two GroupChat diagnostics and 19 for the webhook lifecycle. Each invocation stayed below the 50-request cap and verified the authenticated company matched the disposable test-company scope. The matrix carries forward prior live PASS evidence for unchanged operations when final cleanup left no detail fixture; mocked coverage is not counted as live.

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
| `GroupChatController_create` | FAIL | Four live POSTs returned HTTP 400. In the second follow-up attempt, both synthetic users passed GET; the request supplied the required OpenAPI fields with consistent `owner`/`admin` role configuration. The SDK classified the response as `validation_message_unclassified`; no machine error code was available. No chat or message was created. |
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
| `WebhookController_create` | PASS | The new filtered task-created subscription passed; its synthetic enabled-event was observed in n8n. |
| `WebhookController_put` | PASS | Disable and soft-delete updates passed; readback confirmed each state. |
| `WebhookController_search` | PASS | Live SDK response passed strict validation. The enabled-event updated `lastSuccess` with zero failures; after disable, the delivery counters stayed unchanged. The owner confirmed no callback requests arrived after the enabled-event at 2026-11-15 00:41:37 MSK. |
| `getCompanies` | SKIPPED | Credential-bearing lookup is excluded from the diagnostic runner. |

## Confirmed compatibility findings and fixes

- Live Board, Project, Task and GroupChat responses used `deleted: null` where the pinned OpenAPI required a boolean. Narrow DTO overlay entries now allow null only for those affected fields; strict validation remains enabled for other values.
- `ProjectRolesController_delete` returned a partial role DTO containing only `id`. Overlay v7 requires that observed identity and validates present optional fields. The missing-`id` and invalid-`id` regressions remain rejected.
- A synthetic absent CRM external ID returned HTTP 404 while the snapshot documented only 200. Overlay v7 records the not-found response; a positive lookup still needs a valid CRM fixture.
- Webhook filter schemas and file upload multipart/response schemas retain the earlier narrowly scoped compatibility entries. The vendor snapshot itself was not edited.

## Other findings and limits

- `UserController_create` returned HTTP 400 with `messengerOnly:true` in an earlier synthetic attempt and HTTP 201 with `messengerOnly:false`; both used non-routable `example.invalid` addresses. The error body is intentionally discarded, so this confirms a server-side input-dependent behavior but does not establish the reason or justify narrowing the OpenAPI boolean schema. User update and delete passed with synthetic fixtures.
- `GroupChatController_create` returned HTTP 400 in four total live attempts. In the two follow-up attempts, both newly created synthetic users returned HTTP 200 from `UserController_get`; the request included all four required fields, and a consistent role map/configuration still failed. The authenticated user is an admin. The safe diagnostic found no machine code and classified the server message as `validation_message_unclassified`; its text is not retained. This is evidence of a server-side rejection after local request validation, but it does not identify a specific rule, so no schema overlay or SDK payload workaround was added. `GroupChatController_get`/search had earlier live PASS coverage; update and all message operations remain SKIPPED because no group chat was created.
- Official [YouGile help](https://ru.yougile.com/news/kak-navesti-poryadok-v-rabochem-obshhenii.html) documents a company setting that can restrict who creates group chats. The authenticated user is an admin, and the API response exposed no discoverable boolean for that setting; this remains an unconfirmed factor and does not explain the HTTP 400.
- CRM contact creation was not validly exercised: an earlier request using a non-CRM project returned HTTP 400, and no safe CRM project fixture was available. The final matrix marks it BLOCKED.
- A board title update passed. A separate soft-delete-shaped update on a board with children returned HTTP 400; this was not attributed to an SDK schema mismatch.
- The follow-up created a new `task-created` hook filtered to the synthetic project column and two synthetic task titles. The enabled task produced a matching n8n execution, and YouGile reported a positive `lastSuccess` with zero delivery failures. After disabling the hook, the second matching task caused no later callback request per the owner's corrected observation; YouGile's counters were unchanged. Disable, soft-delete and readback passed. A final read found zero active webhook subscriptions. The receiver was not called directly.
- The runner no longer treats unchanged YouGile counters alone as proof of no delivery after disable. It returns BLOCKED until receiver confirmation is available; the live result above is PASS only when combined with the owner's n8n observation.
- The project hierarchy and the department, role, sticker and webhook fixtures were cleaned up or soft-deleted where supported. Nine synthetic users were deleted across all runs. No group chat or message was created. Three small synthetic text uploads remain because the API inventory provides no upload-delete operation.

## Evidence and diagnostics

The runner continues independent operations after a failed probe, enforces a per-run request cap, sanitizes diagnostics, and never retries a write after a timeout. Its exit code is nonzero when an operation fails or a side-effect check is not PASS; the webhook delivery check therefore correctly failed the run. The final read-only sweep confirmed the test-company scope and found no unapproved active callback. Raw response bodies, user content, IDs and credentials were not retained.

The 72-row matrix above is live-client evidence, not mocked coverage. Synthetic MockTransport regressions are tracked separately in the test suite.

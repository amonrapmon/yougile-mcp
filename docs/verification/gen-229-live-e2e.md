# GEN-229 live E2E API v2 report

**Date:** 2026-11-14; follow-up 2026-11-15
**PR:** [#13](https://github.com/amonrapmon/yougile-mcp/pull/13).
**Scope:** final status matrix for all 72 OpenAPI v2 operation IDs, based on live requests against the owner-confirmed disposable test company where permitted. The matrix does not claim all 72 operations passed or were exercised.
**Credentials:** loaded from the profile-local `e2e.env` into the runner process; no key, company identifier, entity content, response body or fixture ID was written to the repository or report.
**OpenAPI source:** pinned snapshot SHA-256 `9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406` is unchanged. Compatibility overlay: `2026-11-15.8`.

## Current consolidated matrix

| Status | Operations |
|---|---:|
| PASS | 65 |
| FAIL | 1 |
| BLOCKED | 4 |
| SKIPPED | 2 |
| NOT RUN | 0 |
| **Total** | **72** |

The initial full 72-operation diagnostic run used 23 HTTP attempts for the initial read-only sweep, 42 for the main fixture/write chain, 9 and 8 for two isolated synthetic-user/chat diagnostics, and 23 for the final read-only cleanup check. Nov 15 follow-ups used 9 and 11 attempts for GroupChat diagnostics, 19 for the webhook lifecycle, 14 for CRM/project-chat checks and 11 for post-overlay message verification. Additional SDK discovery/diagnostic sessions were individually bounded below 20 requests. Each invocation stayed below the 50-request cap and verified the authenticated company matched the disposable test-company scope. This update is targeted, not a new full 72-operation run: unchanged rows carry forward prior live evidence, and mocked coverage is not counted as live.

PASS means the SDK response passed strict validation for the tested request; `ChatMessageController_typing` returned live HTTP 201 and passed the compatibility response schema, and `CrmExternalIdController_findContactByExternalId` PASS is the expected 404 for a synthetic absent ID. It does not imply every payload, permission or pagination variant was exercised. BLOCKED and SKIPPED entries are not live coverage.

## Results by operation

| Operation ID | Final | Evidence / reason |
|---|---|---|
| `AuthKeyController_create` | BLOCKED | The profile provides only an API key and company ID; login/password inputs required by this operation are unavailable. No key was created. |
| `AuthKeyController_delete` | BLOCKED | Suitable login/password credentials were unavailable, so no test key could be created and safely identified; existing credentials and administrative access were left intact. |
| `AuthKeyController_search` | SKIPPED | Not tested: suitable login/password credentials were unavailable, and credential-bearing results are excluded by the safe runner. |
| `BoardController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `BoardController_update` | PASS | Ordinary title update passed. A soft-delete update on a board with children returned HTTP 400; no SDK mismatch was established. |
| `ChatMessageController_get` | PASS | Read a synthetic message from the single-member CRM_TEST project chat; strict validation passed after the narrow response overlay. |
| `ChatMessageController_search` | PASS | Live search before and after soft-delete passed strict validation; the server omitted `textHtml` and `editTimestamp`. |
| `ChatMessageController_sendMessage` | PASS | Sent synthetic messages only to the CRM_TEST project chat; both were soft-deleted after checks. |
| `ChatMessageController_typing` | PASS | Live response was HTTP 201 with the documented `ChatTypingDto`; the overlay validates that status. |
| `ChatMessageController_update` | PASS | Soft-deleted only synthetic messages created by this test. |
| `ColumnController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ColumnController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `CompanyController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `CompanyController_update` | PASS | No-op PUT returned HTTP 200; the company title was unchanged. |
| `CrmContactPersonsController_create` | PASS | Found `CRM_TEST`; Project GET exposes no type field, but the CRM endpoint accepted its ID and created one synthetic contact with HTTP 201. No contact-delete operation exists, so the contact remains. |
| `CrmExternalIdController_findContactByExternalId` | PASS | The negative scenario returned the expected HTTP 404 for a synthetic absent ID. The positive lookup was not tested because neither the create schema nor the 72-operation inventory can assign the required `provider/chatId` mapping. |
| `DepartmentController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_get` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_search` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `DepartmentController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `FileController_uploadFile` | PASS | Three small synthetic text uploads passed across the live runs. The API inventory has no upload-delete operation; these files remain as residue. |
| `GroupChatController_create` | FAIL | Four live API POSTs returned HTTP 400. In the second follow-up attempt, both synthetic users passed GET; the request supplied the required OpenAPI fields with consistent `owner`/`admin` role configuration. The SDK classified the response as `validation_message_unclassified`; the cause of the server validation failure is not established. The separate UI-created CRM_TEST chat does not count as API-create evidence. |
| `GroupChatController_get` | PASS | The unique active chat with a title containing `CRM_TEST` returned HTTP 200 and passed strict validation; its only member was the authenticated user. |
| `GroupChatController_search` | PASS | Found the active CRM_TEST-named chat. Project GET exposes no explicit chat link, so association is supported by the unique title match and owner setup. |
| `GroupChatController_update` | PASS | A title-only no-op update on the single-member CRM_TEST chat returned HTTP 200. Changing membership was not tested. |
| `ProjectController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectController_get` | PASS | CRM_TEST detail returned HTTP 200 and passed strict validation; the response has no `type` or ID-prefix field. |
| `ProjectController_search` | PASS | Exact-title search found one active CRM_TEST project; the result fed the CRM contact-create chain. |
| `ProjectController_update` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_create` | PASS | Live SDK response returned HTTP 2xx and passed strict response validation. |
| `ProjectRolesController_delete` | PASS | Live DELETE returned a DTO containing `id`; overlay v8 requires `id` and validates other DTO fields if present. |
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
| `WebhookController_create` | PASS | The filtered test subscription delivered its synthetic event to n8n at 2026-11-15 00:41:37 MSK. |
| `WebhookController_put` | PASS | Disable and delete updates passed; readback confirmed both states. No event arrived after the subscription was disabled. |
| `WebhookController_search` | PASS | Live SDK response passed strict validation. YouGile updated `lastSuccess` for the successful delivery with zero delivery errors. After disable, no new event arrived; the test subscription was deleted and no active test webhooks remained. |
| `getCompanies` | SKIPPED | Not tested: suitable credentials were unavailable, and credential-bearing lookup is excluded by the safe runner. |

## Confirmed compatibility findings and fixes

- Live Board, Project, Task and GroupChat responses used `deleted: null` where the pinned OpenAPI required a boolean. Narrow DTO overlay entries now allow null only for those affected fields; strict validation remains enabled for other values.
- `ProjectRolesController_delete` returned a partial role DTO containing only `id`. Overlay v8 requires that observed identity and validates present optional fields. The missing-`id` and invalid-`id` regressions remain rejected.
- A synthetic absent CRM external ID returned HTTP 404 while the snapshot documented only 200. Overlay v8 records the not-found response; a positive lookup requires a provider/chatId mapping that this API slice cannot assign.
- Live chat-message detail/list responses omit `textHtml` and `editTimestamp`. Overlay v8 makes only those fields optional; their declared types and all other required fields remain strict. Live `ChatMessageController_typing` returns HTTP 201 instead of the snapshot's 200; overlay v8 validates 201 with the same `ChatTypingDto` schema.
- Webhook filter schemas and file upload multipart/response schemas retain the earlier narrowly scoped compatibility entries. The vendor snapshot itself was not edited.

## Other findings and limits

- `UserController_create` returned HTTP 400 with `messengerOnly:true` in an earlier synthetic attempt and HTTP 201 with `messengerOnly:false`; both used non-routable `example.invalid` addresses. The error body is intentionally discarded, so this confirms a server-side input-dependent behavior but does not establish the reason or justify narrowing the OpenAPI boolean schema. User update and delete passed with synthetic fixtures.
- `GroupChatController_create` returned HTTP 400 in four total live API attempts. In the two follow-up attempts, both newly created synthetic users returned HTTP 200 from `UserController_get`; the request included all required fields and a consistent role map/configuration still failed. The authenticated user is an admin. Safe diagnostics found no machine code and classified the server message as `validation_message_unclassified`; its text is not retained. The cause of the server validation failure is not established. A separate project chat created through the UI is accessible through `GroupChatController_search/get`, but does not verify this POST operation. Its title contains CRM_TEST and its only member is the authenticated user; title-only no-op update and message probes passed. Membership changes were not tested.
- Official [YouGile help](https://ru.yougile.com/news/kak-navesti-poryadok-v-rabochem-obshhenii.html) documents a company setting that can restrict who creates group chats. The authenticated user is an admin, and the API response exposed no discoverable boolean for that setting; this remains an unconfirmed factor and does not explain the HTTP 400.
- `ProjectController_get` for CRM_TEST exposes neither project type nor ID prefix. The CRM contact endpoint accepted its ID with HTTP 201, confirming the project is usable as a CRM fixture. One synthetic contact titled `YOUGILE_MCP_E2E_GEN229_CRMCHAT_20261115_CONTACT` remains because the 72-operation inventory has no contact-delete operation. A positive external-ID lookup could not be staged: `CreateContactPersonDto` has no provider/chatId fields and there is no mapping-assignment operation.
- A board title update passed. A separate soft-delete-shaped update on a board with children returned HTTP 400; this was not attributed to an SDK schema mismatch.
- The follow-up created a `task-created` hook filtered to the synthetic project column and two synthetic task titles. The enabled event reached the owner's n8n receiver at 2026-11-15 00:41:37 MSK. YouGile updated `lastSuccess` and reported zero delivery errors. After disabling the subscription, no new events arrived. Disable, delete and readback passed; a final read found no active test webhooks. The receiver was not called directly.
- Final residue: the owner-created `CRM_TEST` project and its UI-created group chat remain intentionally. One synthetic CRM contact and three small synthetic text files remain because the API inventory has no corresponding delete operations. Two synthetic chat messages are soft-deleted; no prior message was changed. Other controlled fixtures were cleaned up, including nine synthetic users across all runs.

## Evidence and diagnostics

The runner continues independent operations after a failed probe, enforces a per-run request cap, sanitizes diagnostics, and never retries a write after a timeout. The initial webhook delivery observation awaited receiver confirmation; the owner later confirmed the n8n execution, matching successful `lastSuccess`, zero delivery errors and no events after disable. This final evidence supports PASS for the webhook lifecycle. No live E2E requests were made for this documentation update. Raw response bodies, user content, IDs and credentials were not retained.

The matrix records live-client outcomes where tested; BLOCKED and SKIPPED rows are not live coverage. Synthetic MockTransport regressions are tracked separately in the test suite.

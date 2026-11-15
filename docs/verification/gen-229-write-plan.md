# GEN-229 write-side plan and results

**Authorization:** the owner confirmed the API key is restricted to a disposable test company and explicitly authorized the full GEN-229 live E2E run, including CRUD and deletion. The owner also confirmed that the configured webhook callback is a test-only HTTP 200 receiver with no downstream actions.

## Executed chains

The external synthetic plans were kept outside the repository. They used dependency references and owner-created CRM_TEST fixtures, a per-invocation request ceiling below 50, and no write retry after timeout. Earlier runs used 42 requests for the main fixture chain and 9 + 8 for two synthetic-user/chat diagnostics; 23-request read-only sweeps ran before writes and after cleanup. Nov 15 follow-ups used 14 requests for CRM/project-chat checks and 11 for post-overlay message verification; additional SDK discovery/diagnostic sessions were individually bounded below 20 requests.

| Area | Result |
|---|---|
| Project, board, column and task | Create/read/update calls passed; the project hierarchy was soft-deleted during cleanup. A board title update passed. A board soft-delete-shaped update with children returned HTTP 400. |
| Departments and project roles | Create/read/update calls passed; created department and role were removed during cleanup. Project-role DELETE passed with overlay v8 requiring the observed `id` field. |
| Sprint/string stickers and states | Create/read/update chains passed; test fixtures were cleaned up. |
| Company | No-op update returned HTTP 200 and left the title unchanged. |
| File upload | Three small synthetic text uploads passed across the live runs. They remain in the disposable company because the API inventory has no delete operation. |
| CRM contact | `CRM_TEST` was found by exact title and its detail returned HTTP 200. Project GET exposes no type field, but `CrmContactPersonsController_create` accepted its ID and created one synthetic contact with HTTP 201. No contact-delete operation exists; the contact remains. A positive external-ID lookup cannot be staged because no API operation or create field assigns `provider/chatId`. |
| User and task subscribers | Synthetic `example.invalid` users created with `messengerOnly:false` passed HTTP 201; update and delete passed. A subscriber update using a synthetic user returned HTTP 200. An earlier `messengerOnly:true` create returned HTTP 400; the vendor reason is unavailable. |
| Group chat and messages | One active group chat with a title containing `CRM_TEST` was found and read; its only member was the authenticated user. A title-only no-op GroupChat update returned HTTP 200; membership changes were not tested. Two synthetic messages were created, read, searched, used for typing checks and soft-deleted. Live message reads omitted `textHtml` and `editTimestamp`; typing returned HTTP 201. The narrow overlay and regression tests now cover these differences. `GroupChatController_create` remains a separate FAIL: its four API POST attempts returned HTTP 400, and the cause of the server validation failure is not established. The UI-created chat does not count as API-create evidence. |
| Auth keys and account custom status | BLOCKED: the local credential set has no login/password for auth-key creation/search, and custom-status methods target `/users/me` outside the disposable company scope. Existing credentials and administrative access were preserved. |
| Webhooks | The task-created subscription successfully delivered its enabled synthetic event to n8n at 2026-11-15 00:41:37 MSK. YouGile updated `lastSuccess` and reported zero delivery errors. After disabling the subscription, no new events arrived. Disable, delete and readback passed; the subscription was removed and no active test webhooks remained. The callback was not called directly. |

## Cleanup and retained data

The runner verified company scope before writes. It used synthetic marked payloads and the owner-created CRM_TEST project/chat only as explicit fixtures; message updates targeted only messages created by this test. It stopped a chain when required fixture creation failed. Timeouts on writes would have stopped the run without retry; no write timeout occurred.

Runner-created project hierarchies, departments, roles, stickers, users and webhook subscriptions were cleaned up or soft-deleted; no active test webhooks remain. The owner-created `CRM_TEST` project and UI-created group chat were intentionally left untouched. No group chat was created through `GroupChatController_create`. Both synthetic chat messages were soft-deleted. One synthetic CRM contact remains because the 72-operation inventory has no contact-delete operation. Nine synthetic users were deleted in total. Three small synthetic text files remain because the API exposes no upload-delete operation in the inventory. Other controlled fixtures were cleaned up according to the execution report.

The exact fixture IDs, uploaded text and API responses are intentionally omitted from this document. The complete per-operation result is in [gen-229-live-e2e.md](gen-229-live-e2e.md).

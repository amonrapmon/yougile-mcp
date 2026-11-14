# GEN-229 write-side plan (approval required)

This is a review plan only. No YouGile writes, deletes, messages, callbacks or uploads were run. The owner confirmed the disposable-company key scope, but that confirmation does not approve mutations.

## Proposed dependency chains

1. **Core hierarchy:** create a uniquely marked project, then board, column and task; read each created object; update only those created IDs; verify via detail/list and task log. Keep exact IDs in the external fixture manifest. Cleanup only reversible, owned fixtures after the run.
2. **Departments and project roles:** create a marked department and role attached to the created project; read and update those IDs; delete only the role created in this run after separate destructive approval.
3. **Stickers:** create sprint and string stickers on the created board, then their states; read and update only those fixtures. Do not delete shared or pre-existing sticker data.
4. **Task subscribers:** use only the synthetic test user created for this run. Changes can notify participants, so this operation needs sensitive-action approval.
5. **Group chat and messages:** create a group chat containing only an explicitly approved synthetic test account; read the chat/messages. Sending, typing and editing messages remain separately gated and require a message body with the run marker.
6. **CRM:** use a dedicated test CRM project and synthetic contact; the external-ID lookup needs an owner-approved synthetic provider/chat ID. No real phone, email or customer text.
7. **Webhooks and upload:** use only an exact callback URL included in the external plan allowlist, with an event filter targeting the marked test project. Upload only a tiny `text/plain` synthetic file. The current API inventory has no confirmed upload-delete operation, so upload residue needs explicit acceptance before running.
8. **Separate restricted group:** auth-key create/delete, user create/update/delete/status, company update, and other permission-changing or identity operations need individual review and approval. Credential-bearing auth-key flows cannot be represented in a plan file and remain blocked by the runner.

## Write operation inventory

| Operation ID | Method | Path template | Effect | Request schema | Gate |
|---|---|---|---|---|---|
| `AuthKeyController_create` | `POST` | `/api-v2/auth/keys` | `write` | `CredentialsWithCompanyDto` | separate sensitive approval |
| `AuthKeyController_delete` | `DELETE` | `/api-v2/auth/keys/{key}` | `destructive` | — | separate sensitive + destructive approval |
| `BoardController_create` | `POST` | `/api-v2/boards` | `write` | `CreateBoardDto` | write approval |
| `BoardController_update` | `PUT` | `/api-v2/boards/{id}` | `write` | `UpdateBoardDto` | write approval |
| `ChatMessageController_sendMessage` | `POST` | `/api-v2/chats/{chatId}/messages` | `write` | `CreateChatMessageDto` | separate sensitive approval |
| `ChatMessageController_typing` | `POST` | `/api-v2/chats/{chatId}/typing` | `write` | — | separate sensitive approval |
| `ChatMessageController_update` | `PUT` | `/api-v2/chats/{chatId}/messages/{id}` | `write` | `UpdateChatMessageDto` | separate sensitive approval |
| `ColumnController_create` | `POST` | `/api-v2/columns` | `write` | `CreateColumnDto` | write approval |
| `ColumnController_update` | `PUT` | `/api-v2/columns/{id}` | `write` | `UpdateColumnDto` | write approval |
| `CompanyController_update` | `PUT` | `/api-v2/companies{*companyId}` | `write` | `UpdateCompanyDto` | separate sensitive approval |
| `CrmContactPersonsController_create` | `POST` | `/api-v2/crm/contact-persons` | `write` | `CreateContactPersonDto` | separate sensitive approval |
| `DepartmentController_create` | `POST` | `/api-v2/departments` | `write` | `CreateDepartmentDto` | write approval |
| `DepartmentController_update` | `PUT` | `/api-v2/departments/{id}` | `write` | `UpdateDepartmentDto` | write approval |
| `FileController_uploadFile` | `POST` | `/api-v2/upload-file` | `write` | `` | separate sensitive approval |
| `GroupChatController_create` | `POST` | `/api-v2/group-chats` | `write` | `CreateGroupChatDto` | separate sensitive approval |
| `GroupChatController_update` | `PUT` | `/api-v2/group-chats/{id}` | `write` | `UpdateGroupChatDto` | separate sensitive approval |
| `ProjectController_create` | `POST` | `/api-v2/projects` | `write` | `CreateProjectDto` | write approval |
| `ProjectController_update` | `PUT` | `/api-v2/projects/{id}` | `write` | `UpdateProjectDto` | write approval |
| `ProjectRolesController_create` | `POST` | `/api-v2/projects/{projectId}/roles` | `write` | `CreateProjectRoleDto` | separate sensitive approval |
| `ProjectRolesController_delete` | `DELETE` | `/api-v2/projects/{projectId}/roles/{id}` | `destructive` | — | separate sensitive + destructive approval |
| `ProjectRolesController_update` | `PUT` | `/api-v2/projects/{projectId}/roles/{id}` | `write` | `UpdateProjectRoleDto` | separate sensitive approval |
| `SprintStickerController_create` | `POST` | `/api-v2/sprint-stickers` | `write` | `CreateSprintStickerDto` | write approval |
| `SprintStickerController_update` | `PUT` | `/api-v2/sprint-stickers/{id}` | `write` | `UpdateSprintStickerDto` | write approval |
| `SprintStickerStateController_create` | `POST` | `/api-v2/sprint-stickers/{stickerId}/states` | `write` | `CreateSprintStickerStateDto` | write approval |
| `SprintStickerStateController_update` | `PUT` | `/api-v2/sprint-stickers/{stickerId}/states/{stickerStateId}` | `write` | `UpdateSprintStickerStateDto` | write approval |
| `StringStickerController_create` | `POST` | `/api-v2/string-stickers` | `write` | `CreateStringStickerDto` | write approval |
| `StringStickerController_update` | `PUT` | `/api-v2/string-stickers/{id}` | `write` | `UpdateStringStickerDto` | write approval |
| `StringStickerStateController_create` | `POST` | `/api-v2/string-stickers/{stickerId}/states` | `write` | `CreateStringStickerStateDto` | write approval |
| `StringStickerStateController_update` | `PUT` | `/api-v2/string-stickers/{stickerId}/states/{stickerStateId}` | `write` | `UpdateStringStickerStateDto` | write approval |
| `TaskController_create` | `POST` | `/api-v2/tasks` | `write` | `CreateTaskDto` | write approval |
| `TaskController_update` | `PUT` | `/api-v2/tasks/{id}` | `write` | `UpdateTaskDto` | write approval |
| `TaskController_updateChatSubscribers` | `PUT` | `/api-v2/tasks/{id}/chat-subscribers` | `write` | `TaskChatSubscribersDto` | separate sensitive approval |
| `UserController_clearCustomStatus` | `DELETE` | `/api-v2/users/me/custom-status` | `destructive` | — | separate sensitive + destructive approval |
| `UserController_create` | `POST` | `/api-v2/users` | `write` | `CreateUserDto` | separate sensitive approval |
| `UserController_delete` | `DELETE` | `/api-v2/users/{id}` | `destructive` | — | separate sensitive + destructive approval |
| `UserController_setCustomStatus` | `PUT` | `/api-v2/users/me/custom-status` | `write` | `UserCustomStatusDto` | separate sensitive approval |
| `UserController_update` | `PUT` | `/api-v2/users/{id}` | `write` | `UpdateUserDto` | separate sensitive approval |
| `WebhookController_create` | `POST` | `/api-v2/webhooks` | `write` | `CreateWebhookDto` | separate sensitive approval |
| `WebhookController_put` | `PUT` | `/api-v2/webhooks/{id}` | `write` | `UpdateWebhookDto` | separate sensitive approval |

## Runner safeguards

- Live plans stay outside the repository and contain no API credentials. The API key is loaded from the profile-local env file into the Python process.
- The company must match the authenticated company, and the operator must explicitly confirm the disposable-company scope.
- Every write target must be an ID in the plan allowlist or an ID returned by an earlier create in the same run. Create payloads without a path target require the unique `YOUGILE_MCP_E2E_…` marker.
- `--allow-writes` gates ordinary mutations; `--allow-destructive` additionally gates destructive operations; `--allow-sensitive` gates identity, messaging, permissions, CRM, upload and callback effects.
- Callback URLs must exactly match the plan allowlist. Upload content is limited to 256 KiB, `text/plain`, with the run marker.
- A write timeout is reported as `uncertain_write`; execution stops, and the operation is never retried.

Review required before creating an external plan or using any write flags. In particular, confirm the synthetic chat participant, webhook callback, file residue, CRM test IDs, and which destructive cleanup actions are allowed.

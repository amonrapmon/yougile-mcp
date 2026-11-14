# YouGile REST API v2: manual live observations (2026-11-14)

**Scope:** GEN-214, Draft PR #10. These are sanitized observations from the project owner's manually executed PowerShell 7 \`curl.exe\` commands against the YouGile cloud API on **2026-11-14** (HTTP response \`Date\` headers in UTC, approximately 11:09–11:25). This file is *evidence*, not an executable fixture, a production approval, or evidence that the Python SDK itself has called the live service.

**Source:** owner-supplied command/output transcript in the GEN-214 discussion. Vendor specification: [YouGile REST API v2 OpenAPI](https://ru.yougile.com/api-json), pinned snapshot SHA-256 \`9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406\`. Repository source metadata: \`src/yougile_mcp/api/openapi-source.json\`. Original evidence was manually redacted before documentation: no API key, cookies, actual user email/name/ID, company ID/title, webhook ID/callback URL, or uploaded file URL is included.

## Verification level

- **Observed via raw curl:** the HTTP method, tested URL form, status code and selected JSON response shape below.
- **Not verified via the Python SDK:** no live requests were executed by \`YouGileClient\`; do not set \`live_verified\` in the coverage matrix solely because of this document.
- **Not tested:** \`PUT /api-v2/companies\`, SDK compatibility overrides, large files, MIME restrictions, whether a bogus company ID is *always* ignored, and webhook delivery to the configured recipient.
- **Safety:** the only live mutations were upload of one tiny text file, creation of a deliberately test-scoped webhook and subsequent disabling of that same webhook. No existing company data was intentionally modified. The uploaded file was **not** confirmed removed. The test webhook was confirmed **disabled**, not deleted.

## Observed requests and sanitized responses

All calls used \`Authorization: Bearer <REDACTED>\` supplied from a local PowerShell environment variable. The authenticated account had rights sufficient for these operations. Responses may depend on deployment, permissions and server version.

| # | Operation | Method and request path | HTTP | Observed result |
|---|---|---|---|---|
| 1 | \`UserController_getMe\` | \`GET /api-v2/users/me\` | 200 | JSON user object, including \`id\`, \`email\`, \`isAdmin\`, \`messengerOnly\`, \`realName\`, \`status\`, \`lastActivity\` |
| 2 | \`CompanyController_get\` candidate | \`GET /api-v2/companies\` | 200 | JSON company object with \`title\`, \`timestamp\`, \`id\`, \`deleted: null\` |
| 3 | \`CompanyController_get\` candidate | \`GET /api-v2/companies/{OWN_COMPANY_ID}\` | 200 | Same company object as request 2 |
| 4 | \`CompanyController_get\` candidate | \`GET /api-v2/companies/00000000-0000-0000-0000-000000000000\` | 200 | Same company object as requests 2 and 3 |
| 5 | \`WebhookController_search\` | \`GET /api-v2/webhooks\` (before create) | 200 | Empty JSON **array** \`[]\` |
| 6 | \`WebhookController_search\` | \`GET /api-v2/webhooks?includeDeleted=true\` (before create) | 200 | Empty JSON **array** \`[]\` |
| 7 | \`FileController_uploadFile\` | \`POST /api-v2/upload-file\`, multipart field \`file\`, tiny \`text/plain\` | **201** | JSON object: \`result: "ok"\`, \`url\`, \`fullUrl\` |
| 8 | \`WebhookController_create\` | \`POST /api-v2/webhooks\` | **201** | JSON object: \`id\` |
| 9 | \`WebhookController_search\` | \`GET /api-v2/webhooks\` (after create) | 200 | Nonempty JSON **array**; one webhook with \`id\`, \`event\`, \`url\`, \`filters\`, \`failuresSinceLastSuccess: 0\` |
| 10 | \`WebhookController_put\` | \`PUT /api-v2/webhooks/{TEST_WEBHOOK_ID}\`, \`{"disabled":true}\` | 200 | JSON object: \`id\` |
| 11 | \`WebhookController_search\` | \`GET /api-v2/webhooks\` (after PUT) | 200 | Test webhook present; \`disabled: true\` confirmed by filtered PowerShell output |

### Company detail: do not infer PUT semantics

The pinned vendor path is \`/api-v2/companies{*companyId}\`, yet the endpoint declares **no path parameters**. The tested server returned the same current-company DTO for all three GET URL variants, **including an intentionally nonexistent UUID**. This supports using \`GET /api-v2/companies\` as a working read route in the observed environment. It does **not** prove that arbitrary IDs are always ignored, nor that \`PUT /api-v2/companies\` or \`PUT /api-v2/companies/{id}\` works. No company updates were performed.

Sanitized observed DTO shape:

~~~json
{
  "title": "<redacted>",
  "timestamp": 1791290508373,
  "id": "<redacted>",
  "deleted": null
}
~~~

### Webhooks: request/response schema drift

The original \`WebhookFilters\` schema declares \`name\` as an array whose \`items.type\` is \`location\` (not a valid OpenAPI/JSON Schema type); it declares \`value\` as an array of strings. In contrast, the live server accepted the following **string/string** request filter and returned that shape on subsequent GET:

~~~json
{
  "url": "<redacted HTTPS receiver>",
  "event": "task-created",
  "filters": [
    { "name": "title", "value": "^GEN214_TEST_ONLY$" }
  ]
}
~~~

\`POST /api-v2/webhooks\` returned **201** with \`{"id":"<redacted>"}\`. Follow-up \`GET /api-v2/webhooks\` returned **an array**, whereas the pinned OAS specifies one \`WebhookDto\` object for HTTP 200. A representative sanitized observed item was:

~~~json
{
  "id": "<redacted>",
  "event": "task-created",
  "url": "<redacted HTTPS receiver>",
  "filters": [
    { "name": "title", "value": "^GEN214_TEST_ONLY$" }
  ],
  "failuresSinceLastSuccess": 0
}
~~~

The owner's \`PUT /api-v2/webhooks/{TEST_WEBHOOK_ID}\` with \`{"disabled":true}\` returned **200** and an ID. A subsequent GET confirmed \`disabled: true\` for that same test webhook. Its \`deleted\` status was not established by the filtered PowerShell output; **disabled is not the same as deleted**. No event delivery was verified.

The live evidence establishes the \`title\` filter with string value. It does **not** establish all possible \`location\` and \`chat_message\` filter input/output variants; avoid claiming those are live-verified.

### File upload: malformed multipart reference and status drift

The vendor OAS declares \`POST /api-v2/upload-file\` with \`multipart/form-data\`, a binary \`file\` property, but also the invalid \`$ref: "#/components/schemas/"\` on its schema. The only specified successful status in the pinned document is **200**. Actual curl upload of a small \`text/plain\` file via multipart field \`file\` returned **201 Created** with:

~~~json
{
  "result": "ok",
  "url": "<redacted relative path>",
  "fullUrl": "<redacted absolute URL>"
}
~~~

Only a small text file was tested. No maximum file size, allowed MIME list, upload streaming semantics or remote deletion capability was established. Treat any client file-size/MIME restrictions as **our configurable policy**, not as a verified YouGile limit.

## Required integration work (not yet proven by this evidence)

1. Preserve the raw vendor snapshot and its checksum. Apply narrow, documented, version-pinned compatibility adaptations for the observed webhook filter/array response, malformed upload schema, \`201\` upload status, and proven company GET route.
2. Keep transport/auth, company-wide process-local rate limiter, no-secret logging and no retry after uncertain writes.
3. Add per-operation MockTransport contract tests for the six previously discovered operations. Test both positive and negative cases. For company PUT, keep the unverified semantics explicit.
4. Verify the adaptations *through the Python client* before marking any operation \`live_verified\`. User-run curl success should be documented as \`curl_observed\` or an equivalent distinct evidence category.
5. Avoid live company updates; perform additional mutations only with an explicitly authorized test company/object. Future webhook cleanup should target **only** the disposable test object.

## Related work

- [GEN-214](https://linear.app/amonrapmon/issue/GEN-214/polnoe-pokrytie-yougile-rest-api-v2-cherez-openapi)
- [Draft PR #10](https://github.com/amonrapmon/yougile-mcp/pull/10)
- Initial curl findings: [PR comment](https://github.com/amonrapmon/yougile-mcp/pull/10#issuecomment-6876482617)
- Nonempty webhook and company false-ID findings: [PR comment](https://github.com/amonrapmon/yougile-mcp/pull/10#issuecomment-6876571853)
- Confirmed disabled webhook state: [PR comment](https://github.com/amonrapmon/yougile-mcp/pull/10#issuecomment-6876623374)

> These observations are a point-in-time record of the owner's authorized manual tests. They do not imply permission to perform destructive live operations or verify any behavior beyond the listed requests.

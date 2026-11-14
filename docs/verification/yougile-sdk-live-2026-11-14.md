# YouGile SDK: sanitized live read-only verification (2026-11-14)

**Scope:** GEN-227 / GEN-228, owner-operated PowerShell 7 on Windows, 
`YouGileClient(Settings.from_env())`, authenticated to their YouGile environment.
This record preserves only operation names, HTTP status, sanitized error paths,
and Python type/rule names. No response bodies, account or company identifiers,
task content, user details, tokens, cookies or URL query values were recorded.

## What was observed

Initial SDK smoke test on `main` returned `upstream_failure` for all six 
read operations. Direct HTTPX with the same credentials successfully received
HTTP 200 from `GET /api-v2/users/me`, while the SDK emitted
`httpx.DecodingError` when consuming `aiter_bytes()` following HTTP 200.
Setting `Accept-Encoding: identity` in the HTTPX client made this single
SDK call pass (GEN-227).

After adding the identity header in the GEN-227 draft branch, the owner
executed six unmodified SDK GET calls:

| Operation ID | Live SDK observation |
| --- | --- |
| `UserController_getMe` | HTTP 200, passed response validation |
| `CompanyController_get` | HTTP 200, passed response validation |
| `WebhookController_search` | HTTP 200, passed response validation |
| `ProjectController_search` | HTTP 200, rejected by OAS response validation |
| `BoardController_search` | HTTP 200, rejected by OAS response validation |
| `TaskController_search` | HTTP 200, rejected by OAS response validation |

For each of the three failed operations: `Content-Type:
application/json; charset=utf-8`, no `Content-Encoding` response header.
The sanitized traceback ended at `_decode_response` ->
`spec.validate_schema`. The owner re-ran diagnosis with the same
`OAS30Validator` and pinned vendor schema without printing response values.

All three operations returned one or more identical validation failures:

- **Data path:** `content.[item].deleted`
- **Rule:** `type`
- **Expected schema type:** `boolean`
- **Actual Python type:** `NoneType`

## Narrow runtime compatibility decision

The pinned vendor OpenAPI schema specifies `deleted` as a boolean on
`ProjectListDtoBase`, `BoardListDtoBase` and `TaskListDtoBase`.
However, live list responses can contain `deleted: null` for records.
Runtime overlay `2026-11-14.3` therefore adds `nullable: true`
**only** to those three DTO property schemas. Boolean values remain valid;
other invalid types must still raise `UpstreamError`. `ProjectDto`,
`BoardDto` and `TaskDto` detail schemas are intentionally unchanged.

The vendor snapshot `openapi-v2.json` remains unmodified and SHA-256 pinned
at `9452cba3571607848de77fc12e68104cb454e403c35c7a6b97521ea6e0d1d406`.

## Scope and unverified behavior

This is owner-supplied live observation, not a test executed in GitHub CI.
The six operation results above are **before** the GEN-228 overlay fix.
A clean SDK re-run after applying GEN-228 is required before claiming
six-of-six live compatibility. Pagination beyond the first limited page,
writes, per-tenant access rights, and list detail/read equivalence
were not tested. Do not mark the entire 72-operation catalog live-verified.

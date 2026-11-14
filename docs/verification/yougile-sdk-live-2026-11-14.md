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

## Post-fix SDK confirmation: six of six read-only requests

After applying the GEN-227 identity header **and** GEN-228 nullable-list
overlay, the owner repeated all six calls through the Python SDK with
`Settings.from_env()`, **without monkeypatching or turning off validation**.
The owner reported the following sanitized local console output on
2026-11-14:

```text
PASS UserController_getMe: HTTP 200
PASS CompanyController_get: HTTP 200
PASS WebhookController_search: HTTP 200
PASS ProjectController_search: HTTP 200
PASS BoardController_search: HTTP 200
PASS TaskController_search: HTTP 200

LIVE RESULT: 6/6
```

All six operations succeeded on the specific authenticated account and
tested request variants; the last three search calls used
`limit=2`, `offset=0`. The results were supplied by the project owner and
**were not executed by GitHub CI**. This is sufficient evidence of a
point-in-time successful SDK invocation, not proof that every field, role,
pagination path, or deployment is compatible.

## Scope and unverified behavior

The 6/6 result concerns exactly six read-only GET operations, not the entire
72-operation OpenAPI catalog. Pagination beyond the first limited page,
mutating operations, per-tenant access rights, and detail-versus-list
response equivalence were not tested. No production data was changed by
these SDK smoke tests. The remaining operations need separate live evidence.

# GEN-231 · Historical 75 vs canonical 72

Source inventory is `catalog/tools-75.json` (only historical names,
no third-party implementation). Canonical runtime source remains compatible
YouGile REST v2 OpenAPI, 72 operations. The old 75 do NOT define 75 REST endpoints.

| Functional classification | Count | Implementation state |
|---|---:|---|
| Direct semantic aliases to verified REST operations | 66 | Available as canonical dynamic MCP tools, not as old alias names |
| Read-only smart/composed scenarios | 2 | Pending Smart Tool implementation and API semantic checks |
| Safe task update adapters | 5 | Backed by `TaskController_update`, convenience tools not yet implemented |
| Needs verified vendor comment semantics | 2 | Pending dedicated contract review, not claimed available |
| **Total** | **75** | **Names mapped, not 75 executable legacy tools** |

The explicit, inspectable matrix lives in
`catalog/legacy-75-parity.json`. CI asserts exact inventory coverage,
real operation references, and the classification totals.

Notable gaps: `get_tasks_by_date`, `decode_task_stickers` are composed
reads; `delete_task`, deadline/time-tracking/sticker mutation helpers are
semantic adapters; `get_task_comments` and `add_task_comment` have
no vendor-equivalence proof, so no unverified behavior is invented.

These are follow-ups for GEN-216/217. Every future Smart Tool must call the
same Policy + Dispatcher + canonical YouGile API client, not a new HTTP layer.

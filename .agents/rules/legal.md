# Licensing and source provenance

**When:** importing, porting, adapting, generating or reviewing third-party code.

- Original project source uses AGPL-3.0-only. Its license does not apply to
  third-party code without the relevant rights.
- Public source without a license is not automatically reusable.
  justrussian/yougile-mcp and DrSeedon PR #5 code require explicit permission
  or an independently implemented alternative. See GEN-211.
- Preserve MIT copyright notices when adapting licensed MIT implementations.
- Record source URL, immutable commit, author/license, which files were
  adapted, attribution, and obligations in docs/PROVENANCE.md and NOTICE.
- Do not paste code from an unlicensed fork into tests or generated docs
  as a workaround. Factual tool/API inventories are not source-code reuse.
- Changes to dependency licensing require review before publication.
- If provenance cannot be established, stop the code import and report the
  blocker instead of guessing.

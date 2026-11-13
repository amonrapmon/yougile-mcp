# Engineering rules

**When:** any source or packaging change.

- Inspect the existing module boundary before editing; don't create a
  parallel HTTP adapter, authorization path, DTO model, formatter or logger.
- Source architecture: config -> api/client -> mcp/domain or mcp/smart;
  security checks at the tool execution boundary and internal operations.
- Avoid a second implementation of the same API operation. Reuse tested
  components and keep module boundaries narrow and import direction explicit.
- Make smallest coherent changes; do not opportunistically refactor other
  subsystems or bundle unrelated changes into one PR.
- Prefer typed inputs/results and stable structured errors to prose blobs.
- Unresolved compatibility or security decisions need a draft contract rather
  than an assumption, including data migrations or public tool shape changes.
- Existing code proves observed behavior, not authority. Consult current
  specs and tests when behavior appears to conflict.
- Any new dependency needs a license check, pinned lockfile when runtime
  dependencies begin, dependency audit, and reproducible CI/install steps.
- Keep the public project free of private tenant identifiers, logs, API keys,
  credentials, production task content and local environment paths.

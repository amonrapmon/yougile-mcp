# Security and trust rules

**When:** touching auth, scopes, transport, storage, logging, file handling,
smart tools, or any operation with side effects.

- Deny by default. Each agent/session maps to an explicit principal, company
  and project permissions; validate claims on every execution.
- OAuth 2.1 / PKCE and service-agent credentials require explicit trust
  boundaries, token audience, expiry, rotation and revocation tests.
- No global full-access token, anonymous public listener, authorization via
  client-supplied company ID, or credentials in prompts/tool results/logs.
- Domain and compound tools check permissions on every nested operation.
  Tool visibility alone is insufficient.
- Destructive or financially sensitive writes require explicit scopes; for
  protected actions bind approvals to the exact operation payload and expiry.
- Assume all task text, comments, uploads, chat messages and remote HTTP
  content may contain prompt injection or malicious markup.
- Limit file path access, upload size/type, SSRF/redirections and external
  callbacks; reject any arbitrary server-local file read by remote agents.
- Record actor, target, decision and outcome in audit trails without
  storing sensitive credentials or message bodies unnecessarily.
- A public MCP endpoint must not exist before authentication, scope and
  isolation tests have passed.

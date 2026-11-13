# Operations and deployment

**When:** editing Docker, Compose, transport, config, CI or deployment docs.

- Every service runs least-privileged, without unnecessary filesystem access,
  Linux capabilities or privileged Docker sockets.
- No public HTTP exposure until remote authentication and policy enforcement
  pass security tests. Preserve fail-closed defaults.
- HTTPS termination at a configured trusted proxy; verify trusted-forwarded
  headers and do not accept untrusted Origins.
- Use environment/secrets injection; do not bake credentials into images,
  compose files, build args or public CI logs.
- Make health/readiness and migration behavior explicit; document restart and
  failure semantics, with an upgrade/rollback plan for data migrations.
- Keep per-company limits global across replicas where necessary; avoid a
  fresh limiter per container that multiplies YouGile API requests.
- Verify Compose and Docker image locally/in CI before claiming deployability.
- The foundation image is only a config checker; it is not a production MCP.

# GEN-231 · Secure local stdio launcher

The official MCP SDK already passes 72/72 in-memory wire mock contracts.
This stage makes `yougile-mcp serve` start a real **local stdio** server,
without enabling HTTP.

## How to launch

1. Provision one server-side YouGile API key for the intended company and set
   `YOUGILE_COMPANY_ID` and `YOUGILE_API_KEY` in the protected host environment.
2. Create an **absolute-path** identity JSON file owned by the process user
   with mode 0600 on POSIX. Example (replace sample project/scopes):

   ```json
   {
     "subject": "local-agent-1",
     "company_id": "company-test-id",
     "scopes": ["yougile.boards.read", "yougile.tasks.read"],
     "allowed_projects": ["project-test-id"],
     "company_wide": false
   }
   ```

3. Set `MCP_STDIO_IDENTITY_FILE=/absolute/path/agent.json` and
   `MCP_TRANSPORT=stdio`. Start `yougile-mcp serve` as the
   MCP host's child process; standard I/O is owned by the official SDK.
   No status text is written to stdout before protocol startup.

The per-process principal is never selected by a tool argument or protocol
request. The registry checks every scope and rejects unknown grants.
Company ownership is reverified using the canonical YouGile API client,
project ownership through the verified task/column/board lineage.

Security limitations: stdio is strictly **local**, one process per agent,
and uses OS file permissions as its local trust boundary. Process-local
permission files are not remote bearer tokens. Protected operations requiring
approval remain fail-closed until the durable approved workflow is connected.
Credential-requiring tools have no remote secret-vault adapter and remain
unavailable in the local launcher. This is not a public deployment.

`MCP_TRANSPORT=http` still exits with code 2; the container continues
to run `doctor` by default and exposes no ports.

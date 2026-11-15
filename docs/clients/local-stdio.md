# Local stdio installation

Use this mode for **trusted, locally launched MCP clients only**. It does not publish an HTTP endpoint and is not a replacement for OAuth on a remote host.

## 1. Install

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

~~~sh
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp
uv sync --locked --all-extras
uv run --locked yougile-mcp doctor
~~~

The repository's Dockerfile and `compose.yaml` currently run configuration verification, **not** a production MCP listener.

## 2. Provision an agent identity

Create a private JSON file with this exact structure (example is **read-only board discovery**, not every tool):

~~~json
{
  "subject": "my-local-agent",
  "company_id": "YOUR_COMPANY_ID",
  "scopes": ["yougile.boards.read"],
  "allowed_projects": [],
  "company_wide": true
}
~~~

The `company_id` must match `YOUGILE_COMPANY_ID`. Choose allowed scopes from the actual MCP policy manifest (`src/yougile_mcp/mcp/policy-manifest.json`); unknown scopes fail startup. When using `company_wide: false`, populate `allowed_projects` with authorized project IDs instead. Avoid unnecessarily broad scopes.

The identity path must be **absolute**. On POSIX, the file must be owned by the launching user, be a regular file and have owner-only permissions:

~~~sh
chmod 600 /absolute/private/path/yougile-agent.json
~~~

The loader rejects symlinks, oversized or incomplete identity files, mismatched company IDs and invalid grants.

## 3. Supply the private environment

The launched child process needs:

~~~text
MCP_TRANSPORT=stdio
MCP_AUTH_MODE=required
YOUGILE_COMPANY_ID=YOUR_COMPANY_ID
YOUGILE_API_KEY=<stored privately outside source control>
MCP_STDIO_IDENTITY_FILE=/absolute/private/path/yougile-agent.json
~~~

Use a trusted operating-system secret/environment mechanism or agent launcher to provide the API key. **Do not commit it to Git, agent configuration, JSON examples or shell history.** The `doctor` command checks configuration offline, but does not validate the identity file or contact YouGile.

## 4. Connect the local agent

Start the installed executable as a **stdio child process**, with the environment above:

~~~text
/absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp serve
~~~

On Windows the executable is under `.venv\\Scripts\\yougile-mcp.exe`. The client must own stdin/stdout of the process; do not use a shell command that writes debug output to stdout.

For concrete client configuration examples see [Codex](codex.md), [Claude Code](claude-code.md), [Cursor](cursor.md), or [VS Code](vscode.md).

## 5. Verify

Ask the client to list tools and perform a permitted read-only operation. A `permission_denied` result means the agent principal, YouGile account or resource policy did not authorize that call. Approval-gated tools require a separate trusted approval provider; the default stdio host does not install one.

[Back to client index](README.md)

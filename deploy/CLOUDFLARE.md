# DE5130: Cloudflare Tunnel ingress without touching Xray 443

Use this variant only when the MCP domain DNS is managed by Cloudflare.
DE5130 has Xray listening on host TCP 443 and no Traefik/Nginx/Caddy.
This Compose setup does not open ANY host TCP ports.

## 1. Cloudflare dashboard

In Networking > Tunnels create a remotely managed named tunnel.
Add a Published application route for the desired MCP hostname and
select Service type HTTP, URL http://mcp:8000.
Cloudflare creates the DNS tunnel record.

Do not enable an extra Cloudflare Access login, bot challenge, redirect
or caching rules on /mcp or OAuth endpoints until verified with real
ChatGPT/Codex DCR, PKCE and token exchange.

Cloudflared opens outbound connections to Cloudflare. Public HTTPS
runs on standard 443 at the edge and does not touch the Xray socket.

## 2. Secrets remain on DE

From the repository root:

    cp deploy/.env.example .env
    chmod 600 .env
    mkdir -p secrets
    chmod 700 secrets
    id -u
    id -g

Set MCP_DOMAIN and locally generated CLOUD_DB_PASSWORD,
CLOUD_JWT_SECRET and Fernet CLOUD_ENCRYPTION_KEYS (see README).
If your SSH UID/GID differ from 1000, set CLOUD_TUNNEL_UID
and CLOUD_TUNNEL_GID in .env to match the token file owner.

Use a text editor to create secrets/cloudflared-token and paste
ONLY the tunnel run token from the Cloudflare dashboard.
Do not put this secret on the shell command line or in chat.
Then run:

    chmod 600 secrets/cloudflared-token

Both .env and secrets/ are ignored by Git. Cloudflared reads this
file read-only as the matching non-root UID/GID.

## 3. Validate and start

    docker compose --env-file .env -f deploy/compose.tunnel.yml config -q
    docker compose --env-file .env -f deploy/compose.tunnel.yml build mcp
    docker compose --env-file .env -f deploy/compose.tunnel.yml up -d
    docker compose --env-file .env -f deploy/compose.tunnel.yml ps

Use ONE of compose.tunnel.yml and compose.yml (the Traefik variant).
Never run both at the same time; they share project name and volumes.

Postgres and Valkey join only storage (an internal Docker network).
MCP also joins edge for vendor API egress and cloudflared access.
Cloudflared joins edge but cannot access the database network.
No host ports are published; Xray and the existing bots are untouched.

## 4. Release verification

- External HTTPS hostname returns valid TLS and GET /healthz is 200.
- OAuth metadata is available; anonymous POST /mcp returns 401.
- Real YouGile admin login and cross-company blocks work.
- ChatGPT/Codex complete DCR, PKCE and receive exactly 72 tools.
- Run a harmless live vendor operation for separate company accounts.
- Check access/refresh revocation and disable/re-enable behavior.
- No passwords, API keys, tunnel token or JWTs in HTTP responses/logs.
- Back up DB volumes and Fernet keys together before public use.
- Assess durable failed vendor-key revocation retries and
  shared YouGile quotas before inviting multiple users.

If DNS is not hosted at Cloudflare, do not use this variant.
Do not move/replace Xray without a separate reversible plan.

# DE5130: direct HTTPS with Traefik, retaining existing bots

This is the preferred DE5130 setup **after confirming Xray is unused**.
It creates a separate Traefik stack on 80/443, a shared Docker
network called proxy, and the existing YouGile MCP stack (PostgreSQL,
Valkey, app) without any other published ports. No Cloudflare DNS needed.

## A. Identify the process owning TCP 443

On DE over SSH, run:

    sudo ss -lntp | grep ':443' || true
    systemctl status xray --no-pager || true
    systemctl list-units --type=service --all | grep -i xray || true
    systemctl list-unit-files | grep -i xray || true

Do not kill PID 1965 blindly. Verify which systemd unit owns it.
Only if this is the unused xray.service, stop and disable with:

    sudo systemctl stop xray
    sudo systemctl disable xray
    sudo ss -lntp | grep -E ':(80|443)\b' || true

If the process remains or Xray belongs to another service, STOP and
inspect. Do NOT stop Shadowbox, Amnezia, VPN or unrelated containers.

Rollback if necessary:

    sudo systemctl enable --now xray

## B. DNS and firewall

You need a hostname whose DNS A record points to DE public IPv4.
Before requesting certificates, verify:

    dig +short A YOUR_MCP_DOMAIN
    sudo ss -lntp | grep -E ':(80|443)\b' || true
    sudo ufw status

Port 80 and 443 must be reachable from the public Internet for
Let's Encrypt HTTP-01; Traefik will handle HTTP -> HTTPS.
Do not create an AAAA record unless IPv6 is configured for Traefik.
Do not enable ufw without reviewing existing SSH rules. Never expose
MCP port 8000, PostgreSQL 5432 or Valkey 6379 on the host.

## C. Checkout and private environment

From the DE SSH session:

    git clone https://github.com/amonrapmon/yougile-mcp.git
    cd yougile-mcp
    git fetch origin feat/gen-231-de-cloud-deployment
    git switch feat/gen-231-de-cloud-deployment
    cp deploy/.env.example .env
    chmod 600 .env

Edit .env with the chosen MCP_DOMAIN, an email address for ACME_EMAIL,
and random distinct DB password, JWT signing secret and Fernet key.
Generate those secrets locally:

    openssl rand -hex 24
    openssl rand -hex 48
    python3 -c 'import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'

Use outputs for CLOUD_DB_PASSWORD, CLOUD_JWT_SECRET and
CLOUD_ENCRYPTION_KEYS respectively. Never paste them in chat or Git.
Retain Fernet encryption keys in offsite backups alongside DB data.
Leave CLOUD_HOST_ADMIN_SUBJECTS empty until you verify your exact
YouGile company:user pair.

## D. Boot proxy first, then MCP

From the repository root, confirm both files are valid without
printing interpolated secrets:

    docker compose --env-file .env -f deploy/compose.edge.yml config -q
    docker compose --env-file .env -f deploy/compose.yml config -q

The first stack creates a named shared proxy network.
The second stack refers to that network as external.

    docker compose --env-file .env -f deploy/compose.edge.yml up -d
    docker compose --env-file .env -f deploy/compose.yml up -d --build

Inspect without exposing secrets:

    docker compose --env-file .env -f deploy/compose.edge.yml ps
    docker compose --env-file .env -f deploy/compose.yml ps
    docker compose --env-file .env -f deploy/compose.edge.yml logs --tail=70 traefik

Traefik exposes only 80/443. The Docker API is available to Traefik
ONLY through a read-only-restricted docker-socket-proxy on the private
socket network, not through a mounted Docker socket. The Traefik
dashboard is disabled. HTTPS certificates are stored in the separate
persistent yougile-edge_acme_data volume.

Never run compose down -v: that deletes database/certificate state.
Never apply both the Cloudflare Tunnel and Traefik ingress variants
to the same app at once.

## E. Acceptance testing before external users

Confirm all of the following:

- GET https://YOUR_MCP_DOMAIN/healthz succeeds with a valid cert.
- OAuth metadata endpoints work and anonymous POST /mcp gets 401.
- Indalo login /admin/login is accessible and rejects invalid CSRF.
- Real ChatGPT/Codex DCR + PKCE flows complete; tools/list has 72 tools.
- A harmless live YouGile read succeeds, and another company's
  access token cannot read the first company's data.
- Revoking tokens, disabling/re-enabling companies, and blocking a
  user invalidate grants as documented.
- Existing bots, VPN and their existing ports continue to work.
- Sensitive logs contain no passwords, tokens or company API keys.

Distributed YouGile API request budgeting and durable retries of
failed provider-key revocations need separate release review before
opening the instance to multiple real customers.

This deployment is a self-hosted staging launch until those checks
and offhost encrypted backup/restore are verified.

# DE5130: direct HTTPS with Traefik, retaining existing bots

This is the preferred DE5130 setup **after confirming Xray is unused**.
It creates a separate Traefik stack on 80/443, a shared Docker
network called proxy, and the existing YouGile MCP stack (PostgreSQL,
Valkey, app) without any other published ports. No Cloudflare DNS needed.

## A. Stop the confirmed unused Xray Docker container

The owner inspected PID 1965. This is **not** an xray.service:
- Docker container: `handshake-probe-xray`;
- Docker scope ID: `341358697a43ba9960e78c345bf611ff585269aabeaddbd5718a5925c9622790`;
- `network=host`, `restart=unless-stopped`;
- port 443 is held directly by that container.

After confirming Xray really is unused, disable Docker restart and
stop ONLY this named container:

    docker inspect handshake-probe-xray --format 'id={{.Id}} pid={{.State.Pid}} restart={{.HostConfig.RestartPolicy.Name}}'
    docker update --restart=no handshake-probe-xray
    docker stop handshake-probe-xray
    sudo ss -lntp | grep -E ':(80|443)\b' || echo "Ports 80 and 443 are free"

Do not delete the container or modify Amnezia/Shadowbox/bots.
If rollback is needed **after Traefik relinquishes 443**:

    docker update --restart=unless-stopped handshake-probe-xray
    docker start handshake-probe-xray

Never use the obsolete `systemctl stop xray` instructions here:
no matching systemd unit exists on this host.

## B. DNS and firewall

The owner added DNS A: yougile.ooouch.com -> 151.243.169.51.
Before requesting certificates, verify:

    getent ahostsv4 yougile.ooouch.com | awk '{print $1}' | sort -u
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

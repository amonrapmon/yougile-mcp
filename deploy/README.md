# DE deployment: private YouGile MCP behind existing Traefik

**Pre-release.** This Compose stack does not start a new reverse proxy.
The DE host must already have Traefik with a working HTTPS entrypoint,
certificate resolver and external Docker network.

## 1. Inspect the DE server without changing it

~~~sh
docker --version && docker compose version
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
sudo ss -lntp | grep -E ':(80|443|8000)\b' || true
docker network ls
free -h
df -h /
~~~

Check who owns ports 80/443 and verify the real Traefik network,
HTTPS entrypoint and certificate resolver. If Traefik is not present,
STOP before deploying: decide whether to reuse an existing proxy or
introduce a reviewed proxy stack, without creating port conflicts.

## 2. Domain, checkout and secrets

Create an A record for the selected hostname pointing at the DE host.
Verify with dig, then confirm that Traefik can issue a valid HTTPS cert.

~~~sh
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp
cp deploy/.env.example .env
chmod 600 .env
~~~

Fill in the real MCP_DOMAIN and Traefik variables.
Generate independent secrets ON the DE host, not in chat:

~~~sh
openssl rand -hex 24
openssl rand -hex 48
python3 -c 'import base64,secrets;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())'
~~~

First result: CLOUD_DB_PASSWORD (hex, safe in PostgreSQL URL).
Second: CLOUD_JWT_SECRET. Third: CLOUD_ENCRYPTION_KEYS (Fernet).
Keep .env out of Git and store encrypted off-host backups, including
the Fernet key and PostgreSQL data together. Losing the Fernet key
makes all stored vendor keys unreadable. To rotate it, retain
the old key until all encrypted records have been re-encrypted.

Leave CLOUD_HOST_ADMIN_SUBJECTS empty until the exact verified
companyId:yougileUserId identity of the host operator is known.

## 3. Validate and start

~~~sh
docker compose --env-file .env -f deploy/compose.yml config -q
docker compose --env-file .env -f deploy/compose.yml build mcp
docker compose --env-file .env -f deploy/compose.yml up -d
docker compose --env-file .env -f deploy/compose.yml ps
~~~

IMPORTANT: Running docker compose config *without -q* can reveal
the fully resolved database DSN and JWT encryption secrets.

The application listens on 0.0.0.0:8000 ONLY inside an unprivileged
Docker container, guarded by CLOUD_PRIVATE_CONTAINER_BIND=1. Compose
contains NO ports mapping for the app, PostgreSQL or Valkey.
The storage Docker network is internal, and Traefik connects to
the app over the separate external proxy Docker network.
Do not add host network mode or publicly publish port 8000.

## 4. Release checklist

- PostgreSQL and Valkey healthy; MCP app running, no public
  TCP 8000/5432/6379 listener
- Valid HTTPS certificate and GET /healthz returns 200
- OAuth authorization-server and protected-resource metadata accessible
- An unauthenticated POST /mcp returns 401 before hitting YouGile
- Real admin can sign in at /admin/login; wrong credentials,
  invalid CSRF and foreign-company actions are refused
- Real ChatGPT and Codex OAuth connect using DCR and PKCE;
  successful tools/list exposes exactly 72 direct operations
- At least one harmless real YouGile API read succeeds
- Token revocation, company disable/re-enable and block actions
  reject stale access; logs never print keys or passwords
- Validate distributed 50/min company rate budget and durable
  failed YouGile key revocation retries before broader public use

The existing CI fake-vendor tests do NOT prove real ChatGPT or YouGile
compatibility. Do not invite external users until these gates pass.

## 5. Backup, restoration and rollback

Back up the named postgres_data and valkey_data Docker volumes
with the private .env and Fernet encryption keys to off-host storage.
Test restore in an isolated environment. When rolling back application
code to a known-good commit, preserve volumes and respect any
irreversible migrations. NEVER use docker compose down -v on production.

AGPL network source availability and Indalo copyright attribution
must remain intact.

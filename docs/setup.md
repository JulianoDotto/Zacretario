# Setup

How to stand up Zacretário from zero on one VPS. Follow the sections in order. Each later section (WhatsApp, database, Google) is added as the project reaches it.

## VPS and n8n

What you get: a fresh Ubuntu server running four containers from [`infra/docker-compose.yml`](../infra/docker-compose.yml):

| Service | Reachable from | Purpose |
|---|---|---|
| `caddy` | the internet (80/443) | HTTPS certificate and reverse proxy to n8n |
| `n8n` | Caddy only | the workflows |
| `postgres` | containers only | one database each for n8n, Evolution API and Zacretário |
| `evolution` | the server itself (`127.0.0.1:8080`) | WhatsApp connection |

You need a VPS with Ubuntu 24.04 (1 vCPU and 4 GB of RAM are enough) and a domain whose DNS you control.

1. **DNS.** Create an `A` record for `@` pointing to the VPS IP, and a `CNAME` for `www` pointing to `@`. Wait until `nslookup <domain> 1.1.1.1` returns the VPS IP: Caddy can only get the certificate once the domain points to the server.
2. **Clean server.** Use a plain Ubuntu 24.04 image, not a provider template that already runs n8n or a proxy: two proxies fight over ports 80 and 443. After a reinstall, forget the old SSH identity on your PC with `ssh-keygen -R <IP>`.
3. **Docker and firewall** (on the server, as root):

   ```bash
   apt update && apt upgrade -y && apt install -y docker.io docker-compose-v2
   ufw allow OpenSSH && ufw allow 80,443/tcp && ufw --force enable
   mkdir -p /opt/zacretario
   ```

4. **Copy the infra folder** (from your PC, in the repository folder):

   ```bash
   scp -r infra root@<IP>:/opt/zacretario/
   ```

5. **Secrets** (on the server). This fills every empty value in `.env` with a random 64-character secret:

   ```bash
   cd /opt/zacretario/infra && cp .env.example .env
   for k in POSTGRES_PASSWORD N8N_DB_PASSWORD EVOLUTION_DB_PASSWORD ZACRETARIO_DB_PASSWORD N8N_ENCRYPTION_KEY EVOLUTION_API_KEY; do sed -i "s/^$k=$/$k=$(openssl rand -hex 32)/" .env; done
   chmod 600 .env && chmod +x postgres/init.sh
   ```

   Set `DOMAIN` in `.env` if it is not `dotton8n.com.br`. Save `N8N_ENCRYPTION_KEY` and `EVOLUTION_API_KEY` in a password manager: without the first, every credential stored in n8n is lost if the server is rebuilt; the second controls the WhatsApp number.

6. **Start:**

   ```bash
   docker compose up -d && docker compose ps
   ```

   All four services should be `Up` and Postgres `healthy`. `docker compose logs caddy` should show `certificate obtained successfully`. A few `502` errors right after the start are normal: n8n takes some seconds to boot.

7. **Create the n8n owner account right away.** Open `https://<domain>`: whoever fills in the "Set up owner account" form first owns the instance, and bots find new domains within seconds of the certificate being issued (certificates are published in public logs).

8. **Check from outside:**
   - `https://<domain>` opens n8n with a valid certificate; `https://www.<domain>` redirects to it.
   - `curl -X POST https://<domain>/webhook/whatsapp-entrada` returns `404`: the WhatsApp webhook only exists on the internal network.
   - `http://<IP>:8080` does not answer: Evolution API is not exposed.

Docker publishes ports past `ufw`, so the protection for Postgres and Evolution is that the compose file publishes no port for Postgres and binds Evolution to `127.0.0.1`. Keep it that way.

### Updating

Images are pinned. To update one, change its tag in `infra/docker-compose.yml`, copy the file to the server, and run `docker compose pull <service> && docker compose up -d <service>`. Read the release notes first, especially for Evolution API.

# Deploying to a VPS

This guide puts Zacretario on a Hostinger VPS KVM 1 running Ubuntu, as a systemd service behind Caddy (automatic HTTPS). Commands run on the server over SSH unless stated otherwise.

## Prerequisites

- A VPS with Ubuntu and SSH access (as `root` or a sudo user).
- A domain or subdomain pointing at the VPS public IP: follow [Domain & DNS](local-setup.md#domain--dns). Caddy cannot issue the certificate without it.
- The services from [local-setup.md](local-setup.md) already configured: [Neon](local-setup.md#neon-database), [Google Cloud](local-setup.md#google-cloud-calendar) and [Meta / WhatsApp](local-setup.md#meta--whatsapp).
- Ideally a dedicated WhatsApp number registered in Meta (see step 8).

In the commands below, replace `bot.yourdomain.com` with your domain.

## 1. Base packages, firewall and user

```bash
sudo apt update && sudo apt install -y git curl ufw tzdata debian-keyring debian-archive-keyring apt-transport-https gpg
```

`tzdata` provides the time zone database the app needs for `TIMEZONE` (usually already installed).

Firewall: allow only SSH and web traffic.

```bash
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw enable
```

Create an unprivileged user that owns the app and runs the service:

```bash
sudo useradd --system --create-home --home-dir /opt/zacretario --shell /usr/sbin/nologin zacretario
```

## 2. Install uv and Caddy

Install uv for the `zacretario` user (so the virtualenv and Python belong to it):

```bash
sudo -u zacretario -H bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
```

Install Caddy from its official apt repository (see https://caddyserver.com/docs/install#debian-ubuntu-raspbian if this changes):

```bash
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

## 3. Get the code and install dependencies

`/opt/zacretario` already exists (it is the home of the `zacretario` user). Clone into it:

```bash
sudo -u zacretario -H git clone <your-repo-url> /opt/zacretario/app-tmp
sudo -u zacretario -H bash -c 'shopt -s dotglob && mv /opt/zacretario/app-tmp/* /opt/zacretario/ && rmdir /opt/zacretario/app-tmp'
cd /opt/zacretario
sudo -u zacretario -H /opt/zacretario/.local/bin/uv sync --frozen
```

(If the repository is private, use a deploy key or a token in the clone URL.)

## 4. Create the `.env`

```bash
sudo -u zacretario -H cp /opt/zacretario/.env.example /opt/zacretario/.env
sudo -u zacretario -H nano /opt/zacretario/.env
sudo chmod 600 /opt/zacretario/.env
```

Fill in every value as described in [local-setup.md](local-setup.md) (`DATABASE_URL`, Anthropic key, Google, WhatsApp, `ALLOWED_USERS`, `TIMEZONE`). `.env` holds secrets: only the `zacretario` user should read it, and it must never be committed.

## 5. Run the migrations

```bash
cd /opt/zacretario
sudo -u zacretario -H /opt/zacretario/.local/bin/uv run alembic upgrade head
```

The Google Calendar authorization for each user is stored in the database, so if you already authorized users against the same Neon database during local setup, there is nothing more to do (see [Google Cloud (Calendar)](local-setup.md#google-cloud-calendar) otherwise).

## 6. Install the service and the Caddyfile

```bash
sudo cp /opt/zacretario/deploy/zacretario.service /etc/systemd/system/zacretario.service
sudo cp /opt/zacretario/deploy/Caddyfile /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile   # replace zacretario.example.com with your domain
```

## 7. Start everything

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now zacretario
sudo systemctl restart caddy
```

Check it:

```bash
systemctl status zacretario
curl https://bot.yourdomain.com/health
```

The health check must return `{"status":"ok"}`. If HTTPS fails, confirm DNS resolves to the VPS and ports 80/443 are open, then read `journalctl -u caddy`.

## 8. Point Meta at the server

Set the webhook Callback URL to `https://bot.yourdomain.com/webhook`, with the same verify token as `WHATSAPP_VERIFY_TOKEN`, and make sure the `messages` field is subscribed. The steps are in [Meta / WhatsApp](local-setup.md#meta--whatsapp), step 8 (replace the tunnel URL if you used one).

### Moving from the test number to a dedicated number

1. In Meta, add and verify your dedicated number under WhatsApp > API Setup (Meta's docs: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started).
2. Copy its **Phone number ID** into `WHATSAPP_PHONE_NUMBER_ID` in `/opt/zacretario/.env`.
3. Restart: `sudo systemctl restart zacretario`.
4. Confirm the webhook is subscribed to `messages` for the app, then repeat the [acceptance checklist](local-setup.md#acceptance-checklist) from a registered phone.

The permanent token and app secret stay the same as long as it is the same Meta app.

## Updating

```bash
cd /opt/zacretario
sudo -u zacretario -H git pull
sudo -u zacretario -H /opt/zacretario/.local/bin/uv sync --frozen
sudo -u zacretario -H /opt/zacretario/.local/bin/uv run alembic upgrade head
sudo systemctl restart zacretario
```

## Logs

```bash
journalctl -u zacretario -f
```

## Security basics

- The service runs as the unprivileged `zacretario` user, never as root.
- `.env` is `chmod 600` and owned by `zacretario`.
- `ufw` allows only ports 22, 80 and 443.
- uvicorn listens on `127.0.0.1:8000`, so it is reachable only through Caddy (HTTPS).

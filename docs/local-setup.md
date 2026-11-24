# Local setup

**Before you start.**

You need Python with uv (on Windows, if `uv` is not on PATH, use `python -m uv` everywhere this guide says `uv`), Docker, and a `.env` file copied from `.env.example`. Every variable mentioned below goes into that `.env`.

You also need an Anthropic API key: create one at https://console.anthropic.com/ (Settings, API keys) and put it in `ANTHROPIC_API_KEY`.

## Docker (test database)

Database tests run against Postgres in Docker. Start it from the project root:

```bash
docker compose up -d db
```

Then point the tests at it:

```bash
export TEST_DATABASE_URL=postgresql+psycopg://zacretario:zacretario@localhost:5433/zacretario_test
uv run pytest
```

Without `TEST_DATABASE_URL`, tests fall back to in-memory SQLite.

## Neon (database)

1. Sign up at https://neon.tech and create a project (any region close to you).
2. On the project dashboard click **Connect** and copy the connection string.
3. Change the scheme at the start from `postgresql://` to `postgresql+psycopg://` and paste it into `DATABASE_URL` in `.env`. Keep `?sslmode=require` at the end.
4. Create the tables:

   ```powershell
   python -m uv run alembic upgrade head
   ```

## Google Cloud (Calendar)

1. Go to https://console.cloud.google.com/ and create a project (for example `zacretario`).
2. **APIs & Services > Library**: search for "Google Calendar API" and click **Enable**.
3. **APIs & Services > OAuth consent screen** (called "Google Auth Platform" in the newer UI): choose user type **External**, fill in the app name and your e-mail, and save. The scope can be left empty here.
4. Publish the app: on the consent screen page click **Publish app** and confirm, so the status becomes **In production**. You do not need to submit it for verification. This step matters: while the app is in "Testing", refresh tokens expire after 7 days and the bot would silently lose calendar access.
5. **APIs & Services > Credentials > Create credentials > OAuth client ID**, application type **Desktop app**. Copy the client ID into `GOOGLE_CLIENT_ID` and the client secret into `GOOGLE_CLIENT_SECRET` in `.env`.
6. Authorize each user. The name must be one of the values in `ALLOWED_USERS` (for example `juliano`):

   ```powershell
   python -m uv run python scripts/authorize_google.py juliano
   ```

   A browser opens. Sign in with that person's Google account (each user runs this on a machine where they can log in, with the same `.env`/`DATABASE_URL`). Because the app is unverified, Google shows "Google hasn't verified this app": click **Advanced > Go to (app name) (unsafe)**, then allow the Calendar permission. This warning appears once per user. The script prints a confirmation when the token is saved; it never prints the token itself.

## Meta / WhatsApp

Official docs (screens change often): https://developers.facebook.com/docs/whatsapp/cloud-api/get-started

1. Go to https://developers.facebook.com/, log in and create an app: use case **Other**, app type **Business**.
2. On the app dashboard add the **WhatsApp** product. Meta creates a free **test phone number** for you; use it (no real number needed).
3. In **WhatsApp > API Setup**:
   - Copy the **Phone number ID** (not the number itself) into `WHATSAPP_PHONE_NUMBER_ID`.
   - In the "To" field, add each user's phone number as a recipient and confirm the code WhatsApp sends to it. Both users must be registered here, because the test number can only message registered recipients.
4. **App settings > Basic**: click **Show** next to App secret and copy it into `WHATSAPP_APP_SECRET`.
5. Create a permanent token. The temporary token shown in API Setup expires in 24 hours, so do not use it:
   1. Go to https://business.facebook.com/settings, **Users > System users**, and **Add** a system user with the Admin role.
   2. Click **Add assets**, choose **Apps**, select your app and grant **Full control**.
   3. Click **Generate token**, select your app, set expiration to **Never**, and tick `whatsapp_business_messaging` and `whatsapp_business_management`.
   4. Copy the token into `WHATSAPP_ACCESS_TOKEN`.
6. Choose any random string as `WHATSAPP_VERIFY_TOKEN` in `.env` (you will type the same string into Meta in the webhook step below).
7. Fill `ALLOWED_USERS` in `.env` with JSON mapping each phone (country code + number, digits only, no `+`) to a name, for example `{"5511900000000":"juliano","5511911111111":"maria"}`.
8. Configure the webhook after the server is reachable (see the next section). In **WhatsApp > Configuration**:
   1. Click **Edit** on Webhook. Callback URL: `https://<your-public-host>/webhook`. Verify token: the exact value of `WHATSAPP_VERIFY_TOKEN`. Click **Verify and save**.
   2. In **Webhook fields**, click **Subscribe** on the `messages` field.

## Running locally with a tunnel

Meta needs a public HTTPS URL to call your webhook, so expose your local server with a tunnel.

1. Start the server (leave this terminal open):

   ```powershell
   python -m uv run uvicorn zacretario.main:get_app --factory --port 8000
   ```

2. In a second terminal, start the tunnel. With Cloudflare (install `cloudflared` from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/):

   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```

   It prints a URL like `https://something.trycloudflare.com`. (ngrok works too: `ngrok http 8000`.)
3. Use `<that URL>/webhook` as the Callback URL in the Meta webhook step above. The free tunnel URL changes every time you restart it, so you must update it in Meta each time.
4. Quick check: opening `<that URL>/webhook` in a browser should not return a connection error (a 4xx response is fine, it means the server answered).

## Domain & DNS

Needed only for the permanent deployment on the VPS (Hostinger). Meta only delivers webhooks to an HTTPS URL with a valid certificate, and Caddy (the reverse proxy in this project) can only obtain that free certificate automatically if a domain name points at the server. So you need a domain or subdomain (for example `bot.yourdomain.com`).

1. Find the VPS public IPv4 address in the Hostinger panel (VPS > Overview).
2. Open the DNS settings of wherever the domain is managed: the Hostinger panel (Domains > your domain > DNS / Nameservers) or your registrar's DNS page.
3. Add a record: type **A**, name `bot` (the subdomain; use `@` for the bare domain), value the VPS IP, TTL default (or 300).
4. Wait a few minutes (up to an hour) and check from PowerShell: `nslookup bot.yourdomain.com` should return the VPS IP.
5. Make sure ports 80 and 443 are open on the VPS, since Caddy needs them to issue and serve the certificate.
6. Use `https://bot.yourdomain.com/webhook` as the Callback URL in Meta instead of the tunnel URL.

## Acceptance checklist

Send these messages to the bot on WhatsApp (from a registered number) and tick each one when the outcome matches.

- [ ] "Dentista, quinta-feira, 10h da manhã" creates a 1-hour event next Thursday and the bot confirms it.
- [ ] "Comprar ração dos gatos" creates a TODO.
- [ ] "o que tenho pra fazer?" lists the next 7 days of agenda plus the TODOs, in separate blocks.
- [ ] "comprei a ração" marks that TODO as done.
- [ ] "cancela o dentista" asks for confirmation and only cancels after you answer "sim".
- [ ] "preciso de 2h pra estudar essa semana" proposes time slots and only creates the event after you approve.
- [ ] "meu horário é das 7h às 23h" saves the preference.
- [ ] "escreve um poema" gets a polite refusal.
- [ ] An audio message gets the "text only" notice.

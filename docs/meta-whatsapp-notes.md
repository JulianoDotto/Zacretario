# Meta / WhatsApp: what actually happened

> **Historical.** These notes are from v1 (tag `v1-python`), which used Meta's official Cloud API. The project now uses Evolution API; [why-n8n-evolution.md](why-n8n-evolution.md) explains the switch, and these notes are the evidence behind it. Links to `local-setup.md` point to the v1 tag.

The steps in [local-setup.md](../../../blob/v1-python/docs/local-setup.md#meta--whatsapp) are the happy path. This page records what the first real setup ran into (November 2026), in the order it happened, so the next attempt (or the next reader) does not lose an afternoon to the same walls.

Each item has the **symptom**, the **cause** and the **fix**. Error codes are the ones the Graph API returned.

## How to see what Meta is really saying

Two things made every problem below diagnosable. Use them before guessing:

- **A `200 OK` from `POST /{phone-number-id}/messages` only means Meta *accepted* the message.** Delivery happens later and is reported in a `statuses` webhook (`sent` → `delivered` → `read`, or `failed` with an `errors` array). The bot ignores `statuses` today, so a failed delivery is silent unless you log those payloads.
- **A `400` on send carries a JSON body** with `error.code` and `error.message`. `httpx.raise_for_status()` hides it; log `response.text` to read it.

Logging both permanently is listed in [future-improvements.md](future-improvements.md).

## 1. Google OAuth: "Publish app" stays grey

- **Symptom:** in Google Auth Platform → Audience, the *Publish app* button is disabled.
- **Cause:** publishing to production requires a complete **Branding** page: app name, user support e-mail, home page URL and privacy policy URL (with their domain listed under *Authorized domains*).
- **Fix:** fill Branding and save. This repository's [`PRIVACY.md`](../PRIVACY.md) and the GitHub repo URL serve as privacy policy and home page. Until the app is published, add each user under *Test users*; tokens of apps in *Testing* expire after 7 days.

## 2. Webhook verification fails (403)

- **Symptom:** *"Não foi possível validar o URL de callback ou o token de verificação"*; the server log shows `GET /webhook … 403 Forbidden`.
- **Cause:** `WHATSAPP_VERIFY_TOKEN` was changed in `.env` **after** the server started. Settings are read once at startup.
- **Fix:** restart the server after any `.env` change, then click *Verify and save* again.

## 3. Messages never reach the webhook (app not published)

- **Symptom:** webhook verified and `messages` subscribed, but nothing arrives when you message the bot. The webhook page warns that unpublished apps only receive test webhooks from the dashboard.
- **Cause:** the Meta app was *Unpublished*.
- **Fix:** set a privacy policy URL under *App settings → Basic* and click **Publish**.

## 4. Messages still never reach the webhook (WABA not subscribed)

- **Symptom:** app published, still no `POST /webhook`.
- **Cause:** the WhatsApp Business Account (WABA) was subscribed only to Meta's internal *WA DevX Webhook Events* app, not to ours. Configuring the webhook on the app is not enough; the WABA must subscribe the app.
- **Check:** `GET /{waba-id}/subscribed_apps` must list your app.
- **Fix:** turn on **"Assinar webhooks" / "Subscribe webhooks"** next to the WABA in the phone-number setup step, or call `POST /{waba-id}/subscribed_apps` with the access token. Every new WABA needs this.

## 5. Replies "sent" but never delivered: error 130497

- **Symptom:** the bot replies, `POST /messages` returns `200`, nothing arrives on the phone. The `statuses` webhook says `failed`.
- **Error:** `130497 – Business account is restricted from messaging users in this country.`
- **Cause:** Meta's free **test number** (`+1 555 …`, created in *API Setup*) cannot message users in Brazil.
- **Fix:** register a production number for the business (next items). The recipient number format was *not* the problem.

## 6. Replies stop after a few messages: error 131037

- **Symptom:** a newly registered, Meta-provided number (`+1 555 …`, from *Etapa 2 → Registre seu número*) delivers the first ~5 replies, then every send returns `400`.
- **Error:** `131037 – WhatsApp provided number needs display name approval before message can be sent.`
- **Check:** `GET /{phone-number-id}?fields=name_status,new_name_status` showed `AVAILABLE_WITHOUT_REVIEW` / `NONE`: the display name was never submitted for review.
- **Cause:** numbers **provided by Meta** need an approved display name, and in WhatsApp Manager the *Edit* button for the name was disabled. For these numbers, name approval in practice depends on **business verification** of the Meta business portfolio, which requires real company registration data (CNPJ/NIRE/IE in Brazil) matching official records.
- **Fix (pick one):**
  - **Register your own number** (a SIM card that is not active in the WhatsApp app) via *Add phone number*. This specific block applies to Meta-provided numbers. **Recommended for a personal project.**
  - Complete **business verification** with genuine company data. Never invent registration numbers: it is false information, Meta checks it against official records, and it can get the whole business portfolio and app blocked.

## 7. Tokens and IDs that change between steps

- The **temporary access token** from *API Setup* lasts 24 hours and belongs to the test number's WABA. When you register a production number, generate the **permanent token** offered on that page (or a System User token) and put it in `WHATSAPP_ACCESS_TOKEN`.
- Each registered number has its own **Phone number ID**; update `WHATSAPP_PHONE_NUMBER_ID` and restart.
- The quick `cloudflared` tunnel URL changes on every restart; update the webhook callback URL in Meta when it does. A fixed domain on the VPS removes this ([deploy.md](../../../blob/v1-python/docs/deploy.md)).

## Things you do not need

- **Payment information** in *Etapa 2*: only required for business-initiated (template) messages. The bot only replies inside the 24-hour window opened by the user, which is free.
- **"Enviar mensagem" in *Etapa 2*:** a dashboard test, not part of the bot's flow.
- **App Review / Tech Provider:** not needed for an app that only serves its owner's own WhatsApp account.

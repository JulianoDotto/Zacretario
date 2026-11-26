# Learning log

One short entry per stage of moving Zacretário from Python to n8n: what was done, the n8n concept behind it, and what went wrong. The plan is in [`superpowers/plans/2026-11-25-n8n-migration.md`](superpowers/plans/2026-11-25-n8n-migration.md).

## Task 0 — Why n8n (2026-11-25)

Zacretário started as a Python/FastAPI app with a hand-written Claude agent. Learning Python through it was a convenience, not the goal: n8n fits where I want to go next, which is freelance automation work. The project's priorities are now (1) learning n8n, (2) a portfolio piece, and (3) later, a plug-and-play base I can adapt for each client.

The Python version is kept under the git tag `v1-python`. WhatsApp moves from Meta's Cloud API to Evolution API; see the [design](superpowers/specs/2026-11-25-n8n-migration-design.md) for why.

How we work: Claude navigates to the right page and explains each step; I perform every action myself.

## Task 1 — Reconnaissance (2026-11-25)

The VPS (Hostinger KVM 1: 1 vCPU, 4 GB RAM, 50 GB) was running Hostinger's "Ubuntu with n8n" template, plus leftovers from an older SetupOrion install: two Traefik proxies fighting over ports 80/443. The domain's root record pointed to Hostinger's parking page, not to the VPS.

What I did: reinstalled plain Ubuntu 24.04 (nothing was in use), pointed `@` to the VPS IP and removed the old `portainer` record.

Concepts: DNS records (`@` is the domain itself, `www` is a name under it, A points a name to an IP, CNAME points a name to another name); a fresh reinstall changes the server's SSH identity, so the old one must be forgotten with `ssh-keygen -R`.

What went wrong: a mistyped root password locked one SSH attempt; the browser kept showing the parking page for a while because of the local DNS cache.

## Task 2 — Caddy, Postgres and n8n (2026-11-25)

The whole server is one `docker compose` file in the repository: Caddy, n8n, Postgres and Evolution API, each image pinned to a version. Secrets live only in `infra/.env` on the server.

Concepts: a reverse proxy (Caddy) is the only thing facing the internet and gets the HTTPS certificate by itself; containers talk to each other by service name (`n8n:5678`, `postgres:5432`) on Docker's internal network; a port bound to `127.0.0.1` is reachable from the server but not from the internet; n8n stores its own data in Postgres and encrypts saved credentials with `N8N_ENCRYPTION_KEY`.

What went wrong: I ran a Linux command in my PC's PowerShell instead of the SSH session (same window, different machine; the prompt tells which is which). The SSH session also dropped after sitting idle; the containers kept running. Bots hit the new domain seconds after the certificate was issued, so the n8n owner account has to be created immediately.

## Task 3 — Evolution API and pairing (2026-11-25)

The dedicated number is paired with Evolution API as a linked device, and Evolution calls n8n at `http://n8n:5678/webhook/whatsapp-entrada` for every new message (`MESSAGES_UPSERT`). n8n has a Header Auth credential, `Evolution API`, to send replies.

Concepts: an SSH tunnel (`ssh -L`) reaches a service that is deliberately closed to the internet; a webhook is "call me at this URL when X happens"; least privilege: the n8n credential uses the instance token, which only controls this one number, instead of the global key that controls everything.

What went wrong: "Webhook by Events" got switched on when saving, which would have sent events to a different URL; reloading the page and checking every field caught it.

## Task 4 — First workflow: WhatsApp echo (2026-11-25)

Workflow `Entrada Whatsapp`: Webhook → `Normalizar mensagem` (Code) → `Deve Responder?` (If) → `É texto?` (If) → `Dividir mensagem` (Code) → `Enviar resposta` (HTTP Request to Evolution). Non-text messages go to `Avisar só texto`. The bot echoes text once, ignores its own messages and groups, and answers stickers/audio with a notice.

Concepts:
- Trigger nodes and the two webhook URLs: `/webhook-test/` only while listening in the editor, `/webhook/` only when the workflow is published.
- Pinned data: freeze a real execution's input on a node, so every test in the editor reuses it without sending a new WhatsApp message. "Copy to editor" (Debug in Editor) pins it for you; it needs the free registered Community Edition.
- Code node modes: *Run Once for Each Item* returns one item per input (`$json` is the current item); *Run Once for All Items* can return any number of items (`$input.all()`), which is what splitting a long reply needs.
- A normalising node turns a provider's big payload into a few fields of my own, so the rest of the workflow does not depend on Evolution's format.
- If nodes split the flow into true/false; an unconnected branch just ends. Filtering `fromMe` is what stops the bot from answering its own replies forever.
- HTTP Request "Using Fields Below": each row is a JSON name → value; the name is fixed, the value usually an expression.

What went wrong: I searched the node list for "on webhook call" (the search matches node names: "webhook"). The first send returned *Bad Request* because both expressions went into one body field (name = chatId, value = part) instead of two fields `number` and `text`.

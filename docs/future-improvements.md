# Future improvements

Ideas left out of the n8n version. Each one names the part of the system that absorbs it.

## Serving more people

In n8n a credential is fixed on a node, so per-person Google access means one node per person. That is isolated in **Google Agenda (por pessoa)**, so the rest of the system only passes `user_key` along. Three ways to grow:

| Path | How | Adding someone | Good for |
|---|---|---|---|
| **Switch per person** (current) | One rule and one HTTP Request node per person in *Google Agenda (por pessoa)* | Credential + branch + a row in `users` | Up to ~10 people |
| **One instance per client** | Each freelance client gets their own VPS (or n8n) from [infra/](../infra/) and the exported workflows, with one user | A new instance | Client work: isolated data and costs |
| **Tokens in the database** | A small OAuth flow of our own: a link, a webhook that stores each person's refresh token in `users`, and a Code node that refreshes it and calls Google | Send them a link | Dozens or hundreds of people on one bot |

Only *Google Agenda (por pessoa)* changes between these paths; the agent, the prompt and the WhatsApp side stay the same.

## Proactive reminders

Part: a new workflow with a **Schedule Trigger**.

With Evolution API there is no 24-hour window and no template approval, so a scheduled workflow can read upcoming events (through *Portão de agenda*) or a `reminders` table and send through the same Evolution request as `Enviar resposta`. A `create_reminder` tool would let the agent schedule them.

## More kinds of media

Part: **Ler mídia** and `readableMedia` in `Normalizar mensagem`.

Audio, images and PDFs are read today. Video, stickers, Word or spreadsheet files and locations still get the "text only" notice. Each new kind is one more case in `readableMedia` and one more branch in **Ler mídia** that ends in text.

## Shared household items (e.g. a shared shopping list)

Part: the `user_key` column.

A shared key such as `casa` next to the personal ones, plus tools that let the agent tell "my list" from "the house list" and a rule for who may read and write shared rows. Personal data must stay isolated.

## Other channels (Telegram)

Part: a new entry workflow.

*Agente Zacretário* takes text and returns text and knows nothing about WhatsApp. A Telegram Trigger workflow would normalise the update, look the person up in `users` (with a Telegram id column) and call the same agent.

## Housekeeping and concurrency

- **Pruning old rows.** `processed_messages` and `conversation` only grow. A daily Schedule Trigger with one SQL statement could delete deduplication rows older than a few days and conversation rows older than 24 hours.
- **Per-person ordering.** Two messages sent close together run as separate executions and can interleave (a "yes" racing the message it confirms). n8n's queue mode or a per-user lock row would serialise them. The same applies to an album of photos: each one is its own execution and its own question; grouping media that arrive together would give one answer.
- **Timed event back to all-day.** `update_event` can turn an all-day event into a timed one, but not the reverse; it needs an `all_day` input on the tool and a branch in the `Decidir` Code node.

## Observability

- **WhatsApp session health.** A Schedule Trigger calling Evolution's `GET /instance/connectionState/zacretario` and alerting the owner (through *Erros*' pattern) when it is not `open`, before anyone notices the bot is silent.
- **Code node tests in the repository.** The agenda Code nodes were tested with a throwaway Node.js harness (Luxon + a small `$`/`$json` stub). Committing it with a `package.json` would make the 20 cases re-runnable before every change.
- **Workflow exports.** Exporting is manual today (n8n CLI, then scrubbing pinned data). A small script, or n8n's source-control feature on a paid plan, would keep `workflows/*.json` in sync.

# Privacy Policy — Zacretário

Zacretário is a personal, non-commercial assistant used only by its author and a small set of people he authorizes. It is not offered to the public.

## What data it accesses

- **WhatsApp messages** sent by authorized phone numbers to the Zacretário number, to understand requests. The number is connected through a self-hosted Evolution API instance.
- **Google Calendar events** of each authorized user's own calendar, to list, create, update and delete events at that user's request. Each person connects their own Google account; the consent screen lists the exact calendar permissions requested by n8n's Google Calendar credential. The bot only uses the events endpoints of the calendar set for that person.
- **To-do items, preferences and the conversation text** (what the user wrote and what the bot answered, without tool calls) stored in the project's own database. Only the last 20 messages from the previous 24 hours are sent back to the model as context.

## How data is used

Data is used only to provide the assistant's features to the same user who sent the request. Message text and the recent conversation are sent to Anthropic's Claude API to interpret the request. Nothing is sold, shared for advertising, or used to train models by this project.

## Storage and retention

Everything runs on a private server controlled by the author: the n8n workflows, the Postgres database and the WhatsApp connection. Evolution API is configured not to store message history, contacts or chats. n8n keeps execution logs, which include message text, for 14 days. Messages from unauthorized numbers are not answered and their content is not stored beyond those execution logs. Conversation text and the ids of processed messages are kept until deleted; there is no automatic pruning yet. Users can ask the author to delete their data at any time, and can revoke Google access at https://myaccount.google.com/permissions.

## Contact

Open an issue at https://github.com/JulianoDotto/Zacretario/issues.

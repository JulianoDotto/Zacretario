# Privacy Policy — Zacretário

Zacretário is a personal, non-commercial assistant used only by its author and a small set of people he authorizes. It is not offered to the public.

## What data it accesses

- **WhatsApp messages** sent by authorized phone numbers to the Zacretário number, to understand requests. This includes voice messages, images and PDFs: they are read to extract dates, appointments and tasks, and the files themselves are not kept. The number is connected through a self-hosted Evolution API instance.
- **Google Calendar events** of each authorized user's own calendar, to list, create, update and delete events at that user's request. Each person connects their own Google account; the consent screen lists the exact calendar permissions requested by n8n's Google Calendar credential. The bot only uses the events endpoints of the calendar set for that person.
- **To-do items, preferences and the conversation text** (what the user wrote and what the bot answered, without tool calls) stored in the project's own database. Only the last 20 messages from the previous 24 hours are sent back to the model as context.

## How data is used

Data is used only to provide the assistant's features to the same user who sent the request. Message text and the recent conversation are sent to Anthropic's Claude API to interpret the request. If Claude is unavailable (for example, out of credits or overloaded), the same request is sent to Groq's API as a fallback, with Groq's Zero Data Retention enabled so inputs and outputs are not stored. Voice messages are transcribed by Groq's speech-to-text API (Whisper), under the same Zero Data Retention setting. Images and PDFs are sent to Anthropic's Claude API, which returns only the details relevant to the calendar and to-do list; that text, not the file, is what the assistant and the conversation history see. Nothing is sold, shared for advertising, or used to train models by this project.

## Storage and retention

Everything runs on a private server controlled by the author: the n8n workflows, the Postgres database and the WhatsApp connection. Evolution API is configured not to store message history, contacts or chats. n8n keeps execution logs, which include message text, for 14 days. For media, those logs hold what WhatsApp sends with the message: the keys that let the file be downloaded while WhatsApp still serves it, and a small low-resolution preview of images and of a PDF's first page. They do not hold the file itself when reading succeeds: Evolution API is configured not to send file contents in its webhook, and the workflow that downloads and reads media does not save its successful executions. When reading fails, that execution is kept for debugging, with the file, and is deleted with the other logs after 14 days. Messages from unauthorized numbers are not answered and their content is not stored beyond those execution logs. Conversation text and the ids of processed messages are kept until deleted; there is no automatic pruning yet. Users can ask the author to delete their data at any time, and can revoke Google access at https://myaccount.google.com/permissions.

## Contact

Open an issue at https://github.com/JulianoDotto/Zacretario/issues.
